---
name: git-integration-operations-cli
description: "Runs the Fabric Git integration lifecycle through fab api or az rest, including connecting a workspace to Azure DevOps or GitHub, committing, updating from Git, reading sync status, resolving conflicts, disconnecting a connected workspace, and automating sync with a service principal. For stage promotion use deployment-pipelines-authoring-cli. Branch switching, fab deploy, fabric-cicd and cross-workspace rebinding are out of scope."
metadata:
  maturity: experimental
  owner: yaron
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: git-integration-operations-cli` (`az rest`: `--headers "x-ms-fabric-skill=git-integration-operations-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find a workspace ID from its name: list all workspaces, then filter by
>    `displayName` with JMESPath. To find an item ID: list items of that type in the
>    workspace, then filter by `displayName`.
> 2. All Git operations are **control plane** calls against
>    `https://api.fabric.microsoft.com`. Run `fab auth login` once and `fab api`
>    sets the base URL and Fabric token audience automatically. With the `az rest`
>    fallback you must pass the matching `--resource` yourself, or you get a 401.
> 3. `commitToGit`, `updateFromGit`, and even `git/status` can return **HTTP 202
>    (long-running operation)**, not just a synchronous body. On `202`, poll the
>    operation: with `fab`, read `x-ms-operation-id` from `--show_headers` and poll
>    `fab api operations/{id}` until `status` is `Succeeded`; with the `az rest`
>    fallback, poll the `Location` / `x-ms-operation-id` header (see COMMON-CORE
>    long-running operation polling). When a `202` came from `git/status` itself,
>    read its body from `operations/{id}/result` (the `git_status` helper does
>    this); calling `git/status` again can just return another `202`. After a
>    `commitToGit` / `updateFromGit` operation succeeds, read status with
>    `git_status` to confirm `workspaceHead == remoteCommitHash`, and do not act
>    on its `changes` until the heads match. (Learn: rest/api/fabric/core/git and
>    fabric/cicd/git-integration/git-automation.)
> 4. `updateFromGit` requires the workspace's **current** `workspaceHead`; a stale
>    value returns `400 WorkspaceHeadMismatch`. Always read `git/status` first.
> 5. **Prerequisites for every Git operation:** the workspace must be assigned to a
>    **capacity** (an unassigned workspace fails with `WorkspaceHasNoCapacityAssigned`),
>    and the caller (user or service principal) must hold the right workspace
>    role: **connect and disconnect require Admin**; **commit and update require at
>    least Contributor** with write permission on all items; **branch switching
>    requires Admin** (or Contributor when the workspace opt-in setting *Allow users
>    with at least Contributor role to change Git branch* is on). Only one Git
>    operation may run against a workspace at a time.
> 6. **Tenant admin switches** gate Git integration and are a common cause of an
>    unexplained failure. The **GitHub** sync switch is **off by default** (enable it
>    before any GitHub connect); Azure DevOps sync is on by default. Cross-region
>    workspace-to-*Azure*-repo needs the **cross-geo export** switch (GitHub does not
>    enforce it). See [references/git-integration-concepts.md § Tenant admin prerequisites](references/git-integration-concepts.md#tenant-admin-prerequisites).

# Git Integration Operations — CLI Skill

Automate the Fabric Git integration lifecycle (connect, commit, update, status,
disconnect) from CLI environments. Whether cross-workspace item references rebind
after promotion is a separate concern, determined by the item definition format
(logical vs object IDs) rather than the Git lifecycle itself.

## Prerequisite Knowledge

Read these shared references first (paths assume this skill lives under
`skills/git-integration-operations-cli/` in `skills-for-fabric`; adjust when drafting
outside the repo):

- [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) — **Mandatory** for resolving workspace/item IDs by name.
- [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) — wrong audience = 401; read before any auth issue.
- [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) — `az login` flows and token acquisition for CLI.
- [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) — the `az rest` **fallback** path (**always pass `--resource`**); includes LRO polling helpers.
- [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) — pagination, long-running-operation polling, rate limiting.

## Table of Contents

| Task | Reference |
|---|---|
| Pre-flight checks before connecting | [SKILL.md § Pre-Flight (before you connect)](#pre-flight-before-you-connect) |
| Connect a workspace to Git | [SKILL.md § Connect a Workspace to Git](#connect-a-workspace-to-git) |
| Create a git connection (service principal) | [SKILL.md § Create the Git provider connection (service principal)](#create-the-git-provider-connection-service-principal) |
| Commit workspace items to Git | [SKILL.md § Commit to Git](#commit-to-git) |
| Update a workspace from Git | [SKILL.md § Update from Git](#update-from-git) |
| Check sync status | [SKILL.md § Check Sync Status](#check-sync-status) |
| Resolve update conflicts | [SKILL.md § Resolve Conflicts](#resolve-conflicts) |
| Disconnect from Git | [SKILL.md § Disconnect from Git](#disconnect-from-git) |
| Link a branch workspace to its base (workspace relations) | [SKILL.md § Link a Branch Workspace to its Base (Workspace Relations)](#link-a-branch-workspace-to-its-base-workspace-relations) |
| Git integration concepts (sync model, status, permissions) | [references/git-integration-concepts.md § Concepts](references/git-integration-concepts.md#concepts) |
| Tenant admin prerequisites (switches) | [references/git-integration-concepts.md § Tenant admin prerequisites](references/git-integration-concepts.md#tenant-admin-prerequisites) |
| Supported Git providers | [references/git-integration-concepts.md § Supported Git providers](references/git-integration-concepts.md#supported-git-providers) |
| Supported item types | [references/git-integration-concepts.md § Supported item types](references/git-integration-concepts.md#supported-item-types) |
| Avoiding formatting-only diffs (trailing newline / line endings) | [references/git-integration-concepts.md § Avoiding formatting-only diffs](references/git-integration-concepts.md#avoiding-formatting-only-diffs) |
| Service principal / CI-CD pipeline templates | [references/automation-templates.md](references/automation-templates.md) |
| Gotchas, Rules, Troubleshooting | [SKILL.md § Gotchas, Rules, Troubleshooting](#gotchas-rules-troubleshooting) |

## Must/Prefer/Avoid

### MUST DO
- Read `git/status` and pass the current `workspaceHead` into every `commitToGit`
  and `updateFromGit` call.
- Generate a meaningful `commitToGit` comment of at most 300 characters. If the
  requested text is longer, rewrite it concisely before the API call while
  preserving intent; do not silently cut it mid-sentence. Retry once, with a
  rewritten comment strictly shorter than the rejected one, only when Fabric
  explicitly reports a comment-length validation error.
- Poll `git/status` after each async operation until
  `workspaceHead == remoteCommitHash` **and** the `changes` array is empty. A
  `202`/`Succeeded` status is not proof of a correct sync — validate the state.
- Deploy an item together with the items it references in the same commit, so
  logical IDs can resolve inside the target workspace.

### MUST NEVER
- Never run two Git operations concurrently on the same workspace — a second
  `commitToGit`/`updateFromGit` while one is still `Running` corrupts head
  tracking. Serialize: poll the first to `Succeeded` before starting the next.
- Never treat a workspace as both a source of truth **and** a CI/CD push target
  on the same branch. Pick one writer per branch: either humans commit from the
  workspace, or automation pushes to Git — not both at once.

### PREFER
- `fab api` (after `fab auth login`) as the **primary** driver: it sets the base
  URL and Fabric token audience automatically, avoiding the 401 wrong-audience
  trap. Use `az rest` with `--resource "https://api.fabric.microsoft.com"` as the
  **fallback** when `fab` is unavailable or you need fine-grained header control.
- `PreferRemote` conflict resolution for a clean "pull latest from Git" into a
  downstream/target workspace.

### AVOID
- Reusing a stale `workspaceHead` (causes `400 WorkspaceHeadMismatch`).
- Passing request bodies via stdin to `fab api` (use `-i <file.json>` or `-i '<inline JSON>'`).

---

## CLI: `fab` primary, `az rest` fallback

Every operation below is shown with `fab api`. Run `fab auth login` once (it
supports service principals for automation); `fab` then handles the base URL and
token audience for you. The identical call on the `az rest` fallback is a
mechanical translation:

**Authenticate `fab` for the identity you are running as:**

```bash
fab auth login                                              # interactive user (SSO)
fab auth login -u <client-id> -p <client-secret> --tenant <tenant-id>   # service principal (CI/CD)
fab auth login --identity                                   # managed identity (Azure compute)
```

A service principal or managed identity must be workspace **Admin** to connect or
disconnect (at least **Contributor** with write on all items is enough for
commit/update) and (for the `ConfiguredConnection` path) hold the git provider
credentials. See
[references/automation-templates.md](references/automation-templates.md) for full
pipeline scripts.

- `fab api <endpoint>` becomes `az rest --method GET --url "https://api.fabric.microsoft.com/v1/<endpoint>" --resource "https://api.fabric.microsoft.com"`.
- `fab api -X post <endpoint> -i body.json` adds `--method POST --headers "Content-Type=application/json" --body @body.json`.

`fab api` reads a request body via `-i` from either a file path or an inline JSON
string (e.g. `-i '{"displayName":"..."}'`) — never from stdin. It prints
`{"status_code": <code>, "text": <parsed body>}` (add `--show_headers` for a
top-level `headers` object), so read response fields with `jq -r '.text.<field>'`
and the LRO id with `jq -r '.headers["x-ms-operation-id"]'`. See
[Example 2](#example-2-az-rest-fallback-equivalents) for a full `az rest` pair.

---

## Pre-Flight (before you connect)

Run these Git-relevant checks in order before `git/connect`. Each failure has a
specific fix — resolving them up front avoids the most common connect-time errors.

| Check | Command | Pass = proceed / Fail = fix |
|---|---|---|
| Auth + Fabric token | `fab auth login` then `fab api workspaces` | `401` → re-login (`fab` sets the correct audience automatically) |
| Caller is workspace Admin | `fab api "workspaces/${WORKSPACE_ID}/roleAssignments"` | Connect/disconnect require the **Admin** role |
| Workspace has capacity | `fab api "workspaces/${WORKSPACE_ID}"` → check `capacityId` | `WorkspaceHasNoCapacityAssigned` → assign a capacity (Git requires one) |
| Git credential for the SP path | `fab api connections` (reuse if one already fits) | SP connect needs a `ConfiguredConnection`. If none exists, the skill **creates** it from your ADO org/project/repo + SP tenant/client/secret — see [Create the Git provider connection](#create-the-git-provider-connection-service-principal) (needs the tenant toggle "service principals can create connections"). The interactive-user SSO path uses `Automatic` and needs no connection. |
| Target `directoryName` exists on the branch | GitHub: `curl -fsS -H "Authorization: Bearer $PAT" "https://api.github.com/repos/$OWNER/$REPO/contents/$DIR?ref=$BRANCH"` — ADO: Items API on the repo | The API (unlike the portal) does **not** create a missing folder — connecting to a `directoryName` that doesn't exist fails with `404 GitProviderResourceNotFound`. If the folder is new, pre-create it first (see the note under [Connect a Workspace to Git](#connect-a-workspace-to-git)). |

## Connect a Workspace to Git

Connect a workspace to an Azure DevOps or GitHub repo, then initialize the
connection to establish the sync direction.

```bash
# 1. Connect (Azure DevOps example). Body goes in a file, passed with -i.
cat > connect.json <<'JSON'
{
  "gitProviderDetails": {
    "gitProviderType": "AzureDevOps",
    "organizationName": "myorg",
    "projectName": "MyProject",
    "repositoryName": "fabric",
    "branchName": "main",
    "directoryName": "/workspace-a"
  }
}
JSON
fab api -X post "workspaces/${WORKSPACE_ID}/git/connect" -i connect.json

# 2. Initialize the connection (choose which side wins on first sync)
printf '{"initializationStrategy":"PreferWorkspace"}' > init.json
fab api -X post "workspaces/${WORKSPACE_ID}/git/initializeConnection" -i init.json
```

Use `PreferWorkspace` when the workspace already has the authoritative items;
`PreferRemote` when the Git branch is authoritative.

> **The target `directoryName` must already exist on the branch.** Unlike the Fabric
> portal — which silently creates a missing folder by committing a `README.md`
> placeholder into it — the `git/connect` **API does not create the folder**.
> Connecting to a `directoryName` that does not exist on the branch fails with
> `404 GitProviderResourceNotFound`. The repo and branch must exist too (connect
> never creates a branch). If the folder is new, create it first by committing a
> placeholder file to the branch **through the Git provider's API** (not a Fabric
> API), then connect. Match the portal's convention with a `README.md` whose body is
> `This is an auto-created file via Fabric skills for <workspace-name>`.
>
> ```bash
> # GitHub: create <DIR>/README.md on <BRANCH> (reuse the PAT behind the Git connection)
> DIR="workspace-a"; WS_NAME="My Workspace"
> CONTENT=$(printf 'This is an auto-created file via Fabric skills for %s\n' "$WS_NAME" | base64)
> cat > mkfolder.json <<JSON
> { "message": "Create ${DIR} folder for Fabric Git connect", "branch": "${BRANCH}", "content": "${CONTENT}" }
> JSON
> curl -fsS -X PUT -H "Authorization: Bearer ${GITHUB_PAT}" \
>   "https://api.github.com/repos/${OWNER}/${REPO}/contents/${DIR}/README.md" -d @mkfolder.json
> # Azure DevOps equivalent: POST .../_apis/git/repositories/${REPO}/pushes with an
> # "add" change for "/${DIR}/README.md" on refs/heads/${BRANCH} (same body content).
> ```

> **Two authentication modes (both providers use `myGitCredentials` for automation).**
> A workspace authenticates to git in one of two ways:
> - **Automatic git credential** (Azure DevOps only): the connecting user's SSO
>   identity, established from workspace settings. Secondary contributors with at
>   least Contributor reuse it. Not available for GitHub, and not usable for
>   headless / service-principal automation.
> - **Configured credential** (Azure DevOps *and* GitHub): a Fabric cloud connection
>   referenced in the connect body. This is the required path for any service
>   principal or unattended run:
>   ```json
>   "myGitCredentials": { "source": "ConfiguredConnection", "connectionId": "<connection-guid>" }
>   ```
>   For **Azure DevOps**, the connection's `credentialType` can be either
>   `ServicePrincipal` (headless automation) or `OAuth2` (a stored delegated user
>   token); both are valid ConfiguredConnection credentials per the Create Connection
>   API and both support multitenant scenarios.
>   For **GitHub**, connecting a workspace **requires a Personal Access Token (PAT)**:
>   the cloud connection stores a fine-grained token with Contents Read (plus Write
>   to commit), or a classic token with the `repo` scope. GitHub has no automatic
>   credential mode, so a PAT is mandatory even for an interactive user connect.
> The distinction is not "GitHub needs credentials, ADO does not". ADO *also*
> requires a ConfiguredConnection whenever a service principal drives the connect;
> the automatic mode only covers interactive user SSO. (Learn:
> fabric/cicd/git-integration/automate-git-integration-with-service-principal;
> rest/api/fabric/core/git/connect.)

> **Handle the initialize response.** `initializeConnection` returns
> `requiredAction` (`UpdateFromGit`, `CommitToGit`, or `None`) plus `workspaceHead`
> and `remoteCommitHash`, and can itself return `202`. After it settles, call the
> sync operation named by `requiredAction` with the returned hashes, or the
> workspace stays connected but not fully synced. (Learn:
> rest/api/fabric/core/git/initialize-connection.)

### Create the Git provider connection (service principal)

For unattended automation, first create a Fabric cloud connection that stores the
git provider credentials, then pass its `id` as the `connectionId` in the
`myGitCredentials` block above. Use the
[Create Connection API](https://learn.microsoft.com/rest/api/fabric/core/connections/create-connection)
(`POST /v1/connections`, delegated scope `Connection.ReadWrite.All`). A service
principal can create the connection only if the Fabric admin setting "service
principals can create workspaces, connections, and deployment pipelines" is on.

**Information you must supply (Azure DevOps):**
- ADO **organization**, **project**, and **repository** names, combined into one
  `url` parameter: `https://dev.azure.com/<org>/<project>/_git/<repo>/`
- The service principal's **tenant ID**, **client (application) ID**, and
  **client secret**
- A connection **display name** (max 200 chars, must be unique in the tenant)

**Prerequisites before the connection will work:** grant the service principal
(a) access to that **Azure DevOps organization and project** (git access is
enforced by ADO itself, not only by Fabric), and (b) **Admin** on the target
Fabric workspace.

```bash
# Create an Azure DevOps source-control connection using a service principal.
# The body holds a cleartext SP secret, so restrict perms and delete it on exit
# (a leftover connection.json can be captured by a later CI step or artifact upload).
trap 'rm -f connection.json' EXIT
umask 077
cat > connection.json <<'JSON'
{
  "displayName": "ado-sp-fabric-cicd",
  "connectivityType": "ShareableCloud",
  "connectionDetails": {
    "type": "AzureDevOpsSourceControl",
    "creationMethod": "AzureDevOpsSourceControl.Contents",
    "parameters": [
      { "dataType": "Text", "name": "url",
        "value": "https://dev.azure.com/<org>/<project>/_git/<repo>/" }
    ]
  },
  "credentialDetails": {
    "credentials": {
      "credentialType": "ServicePrincipal",
      "tenantId": "<tenant-id>",
      "servicePrincipalClientId": "<client-id>",
      "servicePrincipalSecret": "<client-secret>"
    }
  }
}
JSON
fab api -X post "connections" -i connection.json
```

The `201` response returns the connection `id`; use it as `connectionId` in the
`myGitCredentials` block of the connect call. For a fully secret-free variant,
pass the body inline with `-i '{...}'` (no file on disk) or reference a Key Vault
secret via `servicePrincipalSecretReference` instead of the raw
`servicePrincipalSecret`. The example above uses
`credentialType: "ServicePrincipal"`; Azure DevOps connections also accept
`credentialType: "OAuth2"` (a stored delegated user token), and both credential
types support multitenant scenarios. To switch an *existing* user-connected
workspace to a service principal, add the SP as workspace Admin, share or recreate
this connection, then
`PATCH /workspaces/{id}/git/myGitCredentials` with the same ConfiguredConnection
body. (Learn:
fabric/cicd/git-integration/automate-git-integration-with-service-principal;
rest/api/fabric/core/connections/create-connection.)

## Commit to Git

Push workspace items to the connected branch. Read the head first, then commit.
The optional `comment` becomes the Git commit message and has a 300-character
maximum. Generate or semantically condense it to fit before the first request.
If there is no useful comment, omit the field and let the Git provider supply
its default.

These helpers are the canonical pattern for every snippet in this skill and in
[references/automation-templates.md](references/automation-templates.md):

```bash
# Read one response header case-insensitively from a `fab api --show_headers` result.
hdr() { jq -r --arg h "$1" '[(.headers // {}) | to_entries[]
  | select(.key | ascii_downcase == $h) | .value][0] // empty'; }

# Run `fab api` and require a parseable {status_code,text} envelope.
fab_json() {
  local r
  r=$(fab api "$@" -H "x-ms-fabric-skill=git-integration-operations-cli" --show_headers 2>/dev/null) || true
  jq -e 'has("status_code")' >/dev/null 2>&1 <<<"$r" \
    || { echo "fab api $*: no parseable response" >&2; return 1; }
  printf '%s\n' "$r"
}

# Poll an LRO (~10 min bound). Check the HTTP status before the body, honour
# Retry-After on 429/503, and fail on any other non-200. With "result", print the
# completed operation's body from operations/{id}/result.
wait_for_lro() {
  local op="$1" want="${2:-}" r sc st="" delay i
  [ -n "$op" ] && [ "$op" != "null" ] \
    || { echo "wait_for_lro: missing x-ms-operation-id" >&2; return 1; }
  for i in $(seq 1 120); do
    r=$(fab_json "operations/${op}") || return 1
    sc=$(jq -r '.status_code' <<<"$r")
    delay=$(hdr retry-after <<<"$r"); [[ "$delay" =~ ^[0-9]+$ ]] || delay=5
    case "$sc" in
      200) ;;
      429|503) sleep "$delay"; continue ;;
      *) echo "LRO ${op}: HTTP ${sc}" >&2; jq '.text' <<<"$r" >&2; return 1 ;;
    esac
    st=$(jq -r '.text.status' <<<"$r")
    case "$st" in
      Succeeded)
        [ "$want" = "result" ] || return 0
        r=$(fab_json "operations/${op}/result") || return 1
        [ "$(jq -r '.status_code' <<<"$r")" = "200" ] \
          || { echo "LRO ${op}: result HTTP $(jq -r '.status_code' <<<"$r")" >&2; return 1; }
        jq -c '.text' <<<"$r"; return 0 ;;
      Failed|Undefined) echo "LRO ${op}: ${st}" >&2; jq '.text.error' <<<"$r" >&2; return 1 ;;
    esac
    sleep "$delay"
  done
  echo "LRO ${op}: timed out (last status: ${st:-unknown})" >&2; return 1
}

# Print the git/status body. A 202 is resolved from the LRO result, never by
# calling git/status again (which can return another 202).
git_status() {
  local r sc
  r=$(fab_json "workspaces/$1/git/status") || return 1
  sc=$(jq -r '.status_code' <<<"$r")
  case "$sc" in
    200) jq -c '.text' <<<"$r" ;;
    202) wait_for_lro "$(hdr x-ms-operation-id <<<"$r")" result ;;
    *)   echo "git/status: HTTP ${sc}" >&2; jq '.text' <<<"$r" >&2; return 1 ;;
  esac
}

# Write a commit body to stdout. Fails on a missing head or a comment over 300
# UTF-16 code units (the service count; jq `length` undercounts emoji).
build_commit_body() {
  jq -en --arg head "$1" --arg msg "$2" '
    def u16: [explode[] | if . > 65535 then 2 else 1 end] | add // 0;
    if ($head | length) == 0 or $head == "null" then
      error("workspaceHead must be non-empty and non-null.")
    elif ($msg | u16) > 300 then
      error("Commit comment must be 300 characters or fewer.")
    else
      {mode:"All", workspaceHead:$head}
      + if ($msg | length) > 0 then {comment:$msg} else {} end
    end'
}

# Returns 0 committed, 3 service rejected the comment length, 1 any other failure.
commit_to_git() {
  local r sc
  r=$(fab_json -X post "workspaces/$1/git/commitToGit" -i "$2") || return 1
  sc=$(jq -r '.status_code' <<<"$r")
  case "$sc" in
    200) return 0 ;;
    202) wait_for_lro "$(hdr x-ms-operation-id <<<"$r")"; return ;;
    400)
      if jq -e '.text | tostring | ascii_downcase
          | test("comment") and test("300|length")' >/dev/null <<<"$r"; then
        echo "commitToGit: comment too long" >&2; return 3
      fi ;;
  esac
  echo "commitToGit: HTTP ${sc}" >&2; jq '.text' <<<"$r" >&2; return 1
}
```

Commit all pending changes:

```bash
STATUS=$(git_status "$WORKSPACE_ID") || exit 1
HEAD=$(jq -r '.workspaceHead' <<<"$STATUS")
COMMIT_MSG="Author items"
build_commit_body "$HEAD" "$COMMIT_MSG" > commit.json || { rm -f commit.json; exit 2; }
rc=0; commit_to_git "$WORKSPACE_ID" commit.json || rc=$?
exit "$rc"
```

Exit `2` means the request was never sent: fix the head or condense the comment.
Exit `3` means Fabric rejected the comment length: rewrite it strictly shorter
than the rejected comment (resending the same text gets the same `400`) and run
the commit once more. Treat any other non-zero exit as a failure and do not retry it
as a length problem. Use `"mode": "Selective"` with an `items` array to commit a
subset.

## Update from Git

Pull committed items into a workspace (for example, a downstream or target
workspace connected to the same branch/folder).

```bash
# Read both hashes from the target workspace (git_status: see Commit to Git)
STATUS=$(git_status "$TARGET_WS") || exit 1
TH=$(jq -r '.workspaceHead' <<<"$STATUS")
REMOTE=$(jq -r '.remoteCommitHash' <<<"$STATUS")

cat > update.json <<JSON
{
  "workspaceHead": "${TH}",
  "remoteCommitHash": "${REMOTE}",
  "conflictResolution": {
    "conflictResolutionType": "Workspace",
    "conflictResolutionPolicy": "PreferRemote"
  },
  "options": { "allowOverrideItems": true }
}
JSON
fab api -X post "workspaces/${TARGET_WS}/git/updateFromGit" -i update.json
```

## Check Sync Status

Poll until the workspace and remote heads match. Both `commitToGit` and
`updateFromGit` are asynchronous, so this loop is how you know they finished.

```bash
for i in $(seq 1 30); do
  S=$(git_status "$WORKSPACE_ID") || exit 1
  WH=$(jq -r '.workspaceHead' <<<"$S")
  RC=$(jq -r '.remoteCommitHash' <<<"$S")
  CH=$(jq -r '.changes | length' <<<"$S")
  # Success = heads match AND no residual changes. Heads matching alone can still
  # leave uncommitted/unapplied diffs; validate both before declaring "synced".
  [ "$WH" = "$RC" ] && [ "$CH" = "0" ] && { echo "synced at $WH"; break; }
  sleep 8
done
```

For an operation still in flight, dispatch on the response code before polling.
`commit_to_git` from [Commit to Git](#commit-to-git) already does this: `200`
returns at once, `202` polls the `x-ms-operation-id` it returned, and anything
else fails without polling. For `updateFromGit`, use the same pattern:

```bash
R=$(fab_json -X post "workspaces/${WORKSPACE_ID}/git/updateFromGit" -i update.json) || exit 1
case "$(jq -r '.status_code' <<<"$R")" in
  200) ;;
  202) wait_for_lro "$(hdr x-ms-operation-id <<<"$R")" || exit 1 ;;
  *)   echo "updateFromGit: HTTP $(jq -r '.status_code' <<<"$R")" >&2; jq '.text' <<<"$R" >&2; exit 1 ;;
esac
```

`git/status` also returns a `changes` array — a non-empty array means there are
uncommitted (workspace) or unapplied (remote) differences.

## Resolve Conflicts

A genuine conflict is *changed-on-both-sides*: after the last sync, the **same
item** was modified in the workspace (an uncommitted local edit) **and** on the
branch (a new commit). `git/status` flags that item in its `changes` array with
`conflictType: "Conflict"` (both `workspaceChange` and `remoteChange` show
`Modified`). This is distinct from a one-sided diff, where only `updateFromGit`
(remote-only change) or `commitToGit` (workspace-only change) is needed with no
policy.

When both sides changed an item, `updateFromGit` **requires** a conflict policy —
calling it without a `conflictResolution` block returns
`400 MissingWorkspaceConflictResolution`:

- `conflictResolutionPolicy: "PreferRemote"` — the Git branch wins (typical for
  pull-into-target deployment); the local edit is discarded.
- `conflictResolutionPolicy: "PreferWorkspace"` — the live workspace wins; to
  push the workspace version to Git instead use `commitToGit`, which does not
  take a conflict policy.

Set `options.allowOverrideItems: true` to let the update overwrite items that
already exist in the target workspace (required whenever the conflicting item is
already present in the workspace, which it is by definition in a both-sides
conflict).

**Which policy to pick:**

| Scenario | Policy |
|---|---|
| Downstream/target workspace pulls the latest from Git | `PreferRemote` |
| The authoring workspace is the source of truth | `PreferWorkspace` (or `commitToGit` to push the workspace version to Git) |
| Genuine two-sided edits on the same item | Inspect each `changes` entry's `conflictType` in `git/status` and resolve deliberately per item |

## Disconnect from Git

```bash
fab api -X post "workspaces/${WORKSPACE_ID}/git/disconnect"
```

---

## Link a Branch Workspace to its Base (Workspace Relations)

> **Preview.** The **Git workspace relations** APIs are part of the Fabric Git
> surface and are in preview. They record a lineage link between a **branch**
> workspace and the **base** workspace it was branched from, so the base↔branch
> relationship is visible in the Fabric portal. Use them when a branch workspace
> was created **before** the built-in branch-out feature shipped, or when branch
> workspaces are provisioned by your own **automation** (not the portal branch-out
> UX) and you still want that lineage to show in the UI. Creating a relation does
> **not** connect either workspace to Git, move items, or start a sync — it only
> records the link.

**Precondition — both workspaces must point at the same Git root.** Create fails
with `WorkspaceRelationRootDirectoryMismatch` unless the base and branch workspaces
are connected to the **same repository root**, differing only by branch:

- **Azure DevOps:** same `organizationName`, `projectName`, `repositoryName`, and
  `directoryName` — only `branchName` differs.
- **GitHub:** same repository URL and `directoryName` — only `branchName` differs.

So connect (and initialize) both workspaces to Git first; the relation just makes
the existing branch/base pair visible.

### Create a relation (link branch ↔ base)

The relation is **bidirectional**, so you create it **once**. Read the body
carefully — the workspace you POST to and the `relationType` are two different
things:

- The **URL** workspace (`workspaces/{workspaceId}/...`) is the side you call *from*.
- `relatedWorkspaceId` is the **other** workspace.
- `relationType` describes the role of that **other** (`relatedWorkspaceId`)
  workspace, **not** the workspace in the URL. Only `Base` and `Branch` are valid
  when creating.

So the same single link has two equivalent ways to create it:

| Call from (URL workspace) | `relatedWorkspaceId` | `relationType` |
|---|---|---|
| the **branch** workspace | the **base** | `Base` |
| the **base** workspace | the **branch** | `Branch` |

Do **not** run both — once one direction exists, creating the other fails with
`WorkspaceRelationBidirectionalExists`. Whichever side you call from, the
permission requirement is the same: **Admin on the branch workspace and Contributor
(or higher) on the base workspace.** The recommended (and most intuitive) form is
to call from the branch and point at the base:

```bash
# From the BRANCH workspace, declare that the related workspace is its Base.
printf '{"relatedWorkspaceId":"%s","relationType":"Base"}' "${BASE_WS}" > relation.json
fab api -X post "workspaces/${BRANCH_WS}/git/workspaceRelations" -i relation.json
```

Returns `201`. Service principals and managed identities are supported.

### List relations

Any **Viewer or higher** can list a workspace's relations (paginate via
`continuationToken`). `relationType` in responses can be `Base`, `Branch`, or
`RelatedWorkspace`.

```bash
fab api "workspaces/${WORKSPACE_ID}/git/workspaceRelations"
```

### Delete a relation

Removes the lineage link only — it does **not** delete either workspace or its
items. The caller must be **Admin** on the workspace named in the path (either the
base or the branch side). Only a `Branch` relation is deletable — otherwise the API
returns `WorkspaceRelationTypeNotBranch`.

```bash
fab api -X delete "workspaces/${WORKSPACE_ID}/git/workspaceRelations/${RELATION_ID}"
```

(Learn: rest/api/fabric/core/workspace-relations.)

---

## Related: cross-workspace item binding

Updating a target workspace from the same branch promotes items into it. Whether
each item-to-item reference rebinds automatically (logical IDs) or breaks (object
IDs / hardcoded endpoints) is a property of the item definition format, not of the
Git lifecycle, and applies equally to fabric-cicd and the Bulk Import API. To
predict a specific dependency's verdict, read the evidence-tagged compatibility
matrix, or empirically validate an uncertain reference, use the
**cross-workspace-item-binding** skill (a planned companion skill, not yet
available in this repo) — it is a distinct concern from the
connect/commit/update lifecycle this skill drives.

## Related: Terraform (infrastructure as code)

To manage the **connect** side declaratively (infrastructure as code) instead of
with imperative `fab api` calls, use the **git-integration-terraform** skill (a
planned companion skill, not yet available in this repo). It
covers the `microsoft/fabric` provider's `fabric_connection` and
`fabric_workspace_git` resources (Azure DevOps service principal or automatic,
GitHub PAT, init strategy, plan/apply/import). In that pattern Terraform owns the
connection, while the commit / update-from-git / status operations in this skill
remain the imperative runtime path — so a common setup is Terraform for the
connection plus a CLI step for update-from-git.

## Related: Variable Library (environment parameterization)

Git integration moves item *definitions* across workspaces, but it does not by
itself parameterize values that must differ per stage (dev/test/prod) — connection
strings, endpoints, capacity IDs, feature flags. That per-environment
parameterization is the job of a **Variable Library**: define the variables once,
provide a value set per stage, and have items resolve the stage-appropriate value.
When a Git-synced workspace needs values that vary by environment, use the
`variable-library-cli` companion skill for the variable/value-set
modeling instead of hardcoding or duplicating that logic here — this skill owns
the source-control lifecycle, the Variable Library skill owns the
parameterization it feeds.

## Gotchas, Rules, Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `400 WorkspaceHeadMismatch` | Stale `workspaceHead` | Re-read `git/status`, retry with the current head |
| `400 MissingWorkspaceConflictResolution` | Both sides changed the same item, but `updateFromGit` was sent without a `conflictResolution` | Add `conflictResolution` (policy `PreferRemote` or `PreferWorkspace`) + `options.allowOverrideItems: true`; check `git/status` for `conflictType: "Conflict"` first |
| `WorkspaceHasNoCapacityAssigned` | Workspace not on a capacity (Git needs one) | Assign a capacity to the workspace, then retry |
| `404 GitProviderResourceNotFound` on `git/connect` | The repo, branch, or `directoryName` does not exist on the provider — the API, unlike the portal, does **not** auto-create the folder | Verify the repo/branch names; if the **folder** is new, pre-create it by committing a `README.md` placeholder to the branch via the Git provider API (see [Connect a Workspace to Git](#connect-a-workspace-to-git)), then retry |
| `WorkspaceAlreadyConnectedToGit` | Workspace is already linked to a repo | Disconnect first, then connect to the new repo |
| `InsufficientPrivileges` / `403` | Caller lacks the role the operation needs (connect/disconnect need **Admin**; commit/update need at least **Contributor** with write on all items) | Grant the caller the required role: Admin to connect/disconnect, or Contributor with write on all items to commit/update |
| `PrincipalTypeNotSupported` | Service principal using automatic credentials (or GitHub) | Switch to a `ConfiguredConnection` in `myGitCredentials` |
| `commitToGitRequest is required` (with `fab api`) | Body piped via stdin | Write the body to a file, pass `-i body.json` |
| Operation returns `202` then nothing changes | Async not yet complete | Poll `operations/{id}` (from `--show_headers`) with `wait_for_lro`; then check heads with `git_status`, which resolves a `202` from `operations/{id}/result` |
| Operation stuck in `Running` for a long time | Large workspace or a second Git op is queued | Keep polling with a sane timeout (about 10 min); never start a second Git op concurrently |
| `401 Unauthorized` | Wrong token audience | Run `fab auth login` (fab sets the audience automatically); on the `az rest` fallback pass `--resource https://api.fabric.microsoft.com` |
| `WorkspaceRelationRootDirectoryMismatch` on `git/workspaceRelations` | Base and branch workspaces are connected to different Git roots | Connect both to the SAME repo/org/project/directory (Azure DevOps) or repo URL/directory (GitHub), differing only by `branchName`, then retry |
| `WorkspaceRelationAlreadyExists` / `WorkspaceRelationBidirectionalExists` | The base↔branch relation is already recorded (it is bidirectional) | Nothing to do — `GET git/workspaceRelations` to confirm; do not also create the reverse direction |
| `WorkspaceRelationTypeNotBranch` on delete | Tried to delete a relation that is not a `Branch` relation | Only `Branch` relations are deletable — use the correct `workspaceRelationId` and delete from the branch side |
| Every sync reports an uncommitted change you did not make (one removed blank line, or a CRLF/LF flip) | In affected workspaces, an editor or AI agent authored the item source (`notebook-content.py`, `pipeline-content.json`, `.platform`) with a trailing final newline or CRLF, then Fabric re-serialized it to the observed export form (LF, **no** trailing newline) | Confirm the behavior with a representative round trip, then match the observed export at authoring time: no trailing newline, LF endings. Pin it in the synced repo with `.editorconfig` + `.gitattributes`, and tell your AI agent not to add a final newline. See [git-integration-concepts.md § Avoiding formatting-only diffs](references/git-integration-concepts.md#avoiding-formatting-only-diffs) |

## Examples

### Example 1: Commit source, then deploy into a target workspace

```bash
# Uses the helpers from "Commit to Git".
SRC_STATUS=$(git_status "$SRC_WS") || exit 1
build_commit_body "$(jq -r '.workspaceHead' <<<"$SRC_STATUS")" "Deploy v1" > commit.json \
  || { rm -f commit.json; exit 2; }
commit_to_git "$SRC_WS" commit.json || exit $?
# ...check sync status of ${SRC_WS}, then updateFromGit into ${TARGET_WS} (see above)
```

### Example 2: `az rest` fallback equivalents

When `fab` is unavailable, the same REST endpoints work through `az rest`. Always
pass `--resource`; a body can be inline (`--body '{...}'`) or from a file
(`--body @file.json`):

```bash
# status
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/git/status" \
  --resource "https://api.fabric.microsoft.com"

# commit (body from build_commit_body in "Commit to Git"). az rest prints only
# the body and exits non-zero on 4xx/5xx; it does not expose x-ms-operation-id,
# so confirm completion with the "Check Sync Status" loop.
build_commit_body "$HEAD" "Author items" > commit.json || { rm -f commit.json; exit 2; }
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/git/commitToGit" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body @commit.json
```
