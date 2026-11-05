# Service Principal and CI/CD Pipeline Templates

Reusable scripts for running the Fabric Git integration lifecycle headlessly (no
interactive login) from a CI/CD pipeline, driven by the Fabric CLI (`fab`).

These templates use the verified `fab` 1.6.1 output shape: `fab api <endpoint>`
prints `{"status_code": <code>, "text": <parsed body>}`, so response fields are
read with `jq -r '.text.<field>'`. Request bodies are passed with `-i` as either
a file path or an inline JSON string (`fab api` never reads a body from stdin).
Long-running operations return
`202`; capture `x-ms-operation-id` from `--show_headers`, poll `operations/{id}`
until `.text.status` is `Succeeded`, then read any response body from
`operations/{id}/result`.

Prerequisites for every template below:

- The service principal (or managed identity) is workspace **Admin** on the target
  workspace, and the workspace is assigned to a **capacity**.
- Install the Fabric CLI: `pip install -q ms-fabric-cli==1.6.1` (pin to keep `jq`
  output-shape parsing stable across CLI releases).
- Authenticate: `fab auth login -u "$CLIENT_ID" -p "$CLIENT_SECRET" --tenant
  "$TENANT_ID"` (or use `az login --service-principal` for the `az rest` fallback).
- For any provider driven by automation, `myGitCredentials` uses a
  `ConfiguredConnection` (a Fabric cloud connection holding the git credentials).
  See [SKILL.md § Create the Git provider connection (service principal)](../SKILL.md#create-the-git-provider-connection-service-principal).

## Shared helpers

Every template sources `fabric-git-helpers.sh`. Create it once in your repository
from the helper block in
[SKILL.md § Commit to Git](../SKILL.md#commit-to-git) (`hdr`, `fab_json`,
`wait_for_lro`, `git_status`, `build_commit_body`, `commit_to_git`). One copy
keeps HTTP-status checks, `Retry-After` handling, LRO result reads and the
comment-length dispatch consistent across scripts.

## Bash: service principal status check, then update

End-to-end headless sync: authenticate, read status, and update the workspace from
Git only when the branch is ahead.

```bash
#!/usr/bin/env bash
set -euo pipefail
# Prerequisites: install CLI and authenticate — see Prerequisites section above.
source ./fabric-git-helpers.sh
WORKSPACE_ID="${WORKSPACE_ID:?Set WORKSPACE_ID}"

STATUS=$(git_status "$WORKSPACE_ID")
REMOTE=$(jq -r '.remoteCommitHash' <<<"$STATUS")
HEAD=$(jq -r '.workspaceHead' <<<"$STATUS")
echo "workspaceHead=$HEAD remoteCommitHash=$REMOTE"

if [ "$REMOTE" != "$HEAD" ]; then
  cat > update.json <<JSON
{
  "workspaceHead": "${HEAD}",
  "remoteCommitHash": "${REMOTE}",
  "conflictResolution": { "conflictResolutionType": "Workspace", "conflictResolutionPolicy": "PreferRemote" },
  "options": { "allowOverrideItems": true }
}
JSON
  R=$(fab_json -X post "workspaces/${WORKSPACE_ID}/git/updateFromGit" -i update.json) || exit 1
  case "$(jq -r '.status_code' <<<"$R")" in
    200) ;;
    202) wait_for_lro "$(hdr x-ms-operation-id <<<"$R")" || exit 1 ;;
    *)   echo "updateFromGit: HTTP $(jq -r '.status_code' <<<"$R")" >&2; jq '.text' <<<"$R" >&2; exit 1 ;;
  esac
else
  echo "Workspace already in sync; nothing to update."
fi
```

## Bash: commit all workspace changes

```bash
#!/usr/bin/env bash
set -euo pipefail
# Assumes fab auth login already ran.
source ./fabric-git-helpers.sh
WORKSPACE_ID="${WORKSPACE_ID:?Set WORKSPACE_ID}"
COMMIT_MSG="${COMMIT_MSG:-Automated commit from CI/CD pipeline}"

STATUS=$(git_status "$WORKSPACE_ID")
if [ "$(jq '.changes | length' <<<"$STATUS")" -eq 0 ]; then
  echo "No workspace changes to commit."
  exit 0
fi

# A pipeline cannot safely summarize operator-supplied text: an oversized
# COMMIT_MSG stops here (exit 2) before any API call.
build_commit_body "$(jq -r '.workspaceHead' <<<"$STATUS")" "$COMMIT_MSG" > commit.json \
  || { rm -f commit.json; exit 2; }
rc=0; commit_to_git "$WORKSPACE_ID" commit.json || rc=$?
# rc 3: Fabric rejected the comment length; shorten COMMIT_MSG and rerun once.
exit "$rc"
```

## Azure DevOps pipeline (YAML)

```yaml
trigger:
  branches:
    include: [ main ]

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: fabric-credentials   # TENANT_ID, CLIENT_ID, CLIENT_SECRET, WORKSPACE_ID

steps:
  - task: Bash@3
    displayName: 'Update Fabric workspace from Git'
    inputs:
      targetType: inline
      script: |
        set -euo pipefail
        # Prerequisites: install CLI and authenticate — see Prerequisites section above.

        source ./fabric-git-helpers.sh

        STATUS=$(git_status "$(WORKSPACE_ID)")
        REMOTE=$(jq -r '.remoteCommitHash' <<<"$STATUS")
        HEAD=$(jq -r '.workspaceHead' <<<"$STATUS")

        cat > update.json <<JSON
        { "workspaceHead": "$HEAD", "remoteCommitHash": "$REMOTE",
          "conflictResolution": { "conflictResolutionType": "Workspace", "conflictResolutionPolicy": "PreferRemote" },
          "options": { "allowOverrideItems": true } }
        JSON

        R=$(fab_json -X post "workspaces/$(WORKSPACE_ID)/git/updateFromGit" -i update.json) || exit 1
        case "$(jq -r '.status_code' <<<"$R")" in
          200) ;;
          202) wait_for_lro "$(hdr x-ms-operation-id <<<"$R")" || exit 1 ;;
          *)   echo "updateFromGit: HTTP $(jq -r '.status_code' <<<"$R")" >&2; jq '.text' <<<"$R" >&2; exit 1 ;;
        esac
```

## GitHub Actions workflow

```yaml
name: Sync Fabric Workspace
on:
  push:
    branches: [ main ]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Prerequisites: install CLI and authenticate — see Prerequisites section above.

      - name: Update workspace from Git
        env:
          WS: ${{ secrets.WORKSPACE_ID }}
        run: |
          set -euo pipefail
          source ./fabric-git-helpers.sh
          STATUS=$(git_status "$WS")
          REMOTE=$(jq -r '.remoteCommitHash' <<<"$STATUS")
          HEAD=$(jq -r '.workspaceHead' <<<"$STATUS")

          cat > update.json <<JSON
          { "workspaceHead": "$HEAD", "remoteCommitHash": "$REMOTE",
            "conflictResolution": { "conflictResolutionType": "Workspace", "conflictResolutionPolicy": "PreferRemote" },
            "options": { "allowOverrideItems": true } }
          JSON

          R=$(fab_json -X post "workspaces/$WS/git/updateFromGit" -i update.json) || exit 1
          case "$(jq -r '.status_code' <<<"$R")" in
            200) ;;
            202) wait_for_lro "$(hdr x-ms-operation-id <<<"$R")" || exit 1 ;;
            *)   echo "updateFromGit: HTTP $(jq -r '.status_code' <<<"$R")" >&2; jq '.text' <<<"$R" >&2; exit 1 ;;
          esac
```

## Notes

- On the `az rest` fallback, drop `fab auth login` for `az login --service-principal
  -u <client-id> -p <client-secret> --tenant <tenant-id>` and translate each call as
  in [SKILL.md § Example 2](../SKILL.md#example-2-az-rest-fallback-equivalents).
- Promoting item **definitions** from a cloned repo into a workspace (`fab deploy`)
  is a deployment concern and is out of scope for this Git integration skill.
