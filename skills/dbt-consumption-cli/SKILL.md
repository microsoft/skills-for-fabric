---
name: dbt-consumption-cli
description: >
  List, inspect, monitor, and trigger Fabric dbt jobs (DataBuildToolJob) via read-only and
  run-focused CLI operations (az rest / curl). Enumerate dbt jobs across workspaces, decode
  the dbt content part (live name `dbt-content.json`) to inspect project, profile, and command
  settings, list the dbt project files (`Code/dbt/*`), check run history and status, poll active
  job instances, and trigger dbt job runs. Use when the
  user wants to: (1) list dbt jobs in a workspace, (2) inspect a dbt job definition (project
  type, adapter, command operation, model selection), (3) check job run history and status,
  (4) trigger a dbt job run, (5) monitor a running dbt job, (6) compare dbt job configurations
  across workspaces.
  Triggers: "dbt job status", "dbt run history", "list dbt jobs", "dbt job monitor", "check dbt
  run", "inspect dbt job", "dbt job definition", "trigger dbt job", "dbt job fabric".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare it against the remote version via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If the remote version is newer, show the changelog and update instructions.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# dbt Jobs — Consumption via CLI

> **Related skills** — this skill lists, inspects, monitors, and triggers dbt job runs. To author/create dbt jobs, use **`dbt-authoring-cli`**. To query or validate the **resulting Warehouse tables** a dbt run produced (row counts, sampling, schema checks), use **`sqldw-consumption-cli`**.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) | LRO polling patterns |
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes pagination and LRO helpers |
| Job Execution (CLI) | [COMMON-CLI.md § Job Execution](../../common/COMMON-CLI.md#job-execution) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference | [COMMON-CLI.md § Quick Reference](../../common/COMMON-CLI.md#quick-reference) | `az rest` template + token audience/tool matrix |
| dbt Job REST API Spec | [Microsoft Docs](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/dbtjob-definition) | Official definition spec |
| dbt Job Overview | [Microsoft Docs](https://learn.microsoft.com/en-us/fabric/data-factory/dbt-job-overview) | Feature overview, supported adapters, runtime |
| dbt Job How-To | [Microsoft Docs](https://learn.microsoft.com/en-us/fabric/data-factory/dbt-job-how-to) | Supported commands, create, schedule, monitor |
| dbt Job Configure | [Microsoft Docs](https://learn.microsoft.com/en-us/fabric/data-factory/dbt-job-configure) | Profile settings, adapter change, advanced settings |

---

## Tool Stack

| Tool | Role | Install |
|---|---|---|
| `az` CLI | **Primary**: Auth (`az login`), Fabric REST API via `az rest` | Pre-installed in most dev environments |
| `curl` | Alternative HTTP client for REST calls | Pre-installed |
| `jq` | Parse JSON responses, extract fields, format output | Pre-installed or trivial |
| `base64` | Decode definition parts from base64 | Built into bash; PowerShell uses `[Convert]::FromBase64String` |
| `bash`/`pwsh` | Script execution | Pre-installed |

> **Agent check** — verify before first operation:
> ```bash
> az account show >/dev/null 2>&1 || echo "RUN: az login"
> command -v jq >/dev/null 2>&1 || echo "INSTALL: apt-get install jq OR brew install jq"
> ```

---

## Connection

### Resolve Workspace ID and Job ID

Per [COMMON-CLI.md](../../common/COMMON-CLI.md) Finding Workspaces and Items in Fabric:

```bash
# Find workspace ID by name
WS_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='My Workspace'].id" --output tsv)

# Find dbt job ID by name within workspace
JOB_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items?type=DataBuildToolJob" \
  --query "value[?displayName=='MyDbtJob'].id" --output tsv)
```

### Reusable Connection Variables

```bash
WS_ID="<workspaceId>"
JOB_ID="<dbtJobItemId>"
API="https://api.fabric.microsoft.com/v1"
RESOURCE="https://api.fabric.microsoft.com"
```

---

## Agentic Exploration ("Explore My dbt Jobs")

### Supported Commands Reference

| Operation | What it does |
|---|---|
| `run` | Runs all SQL models in dependency order |
| `build` | Builds models + seeds + tests in a single pass |
| `seed` | Loads CSV files from `seeds/` directory as managed tables |
| `test` | Runs schema and data tests defined in `schema.yml` |
| `compile` | Generates compiled SQL without executing transformations |
| `snapshot` | Captures slowly changing dimensions over time |

### Discovery Sequence

Run these in order to fully explore dbt jobs in a workspace.

```bash
# 1. List workspaces → find target
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces" --query "value[].{name:displayName, id:id}" -o table

# 2. List all dbt jobs in workspace
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/items?type=DataBuildToolJob" \
  --query "value[].{name:displayName, id:id, desc:description}" -o table

# 3. Get dbt job properties
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID"

# 4. Get definition → decode the dbt content part (live name: dbt-content.json; docs say dbtjob-content.json)
LOCATION=$(az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID/getDefinition" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

DEF=$(az rest --method get --url "$LOCATION" --resource "https://api.fabric.microsoft.com")
# Discover the content part dynamically, then decode it:
CONTENT_PART=$(echo "$DEF" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
echo "$DEF" | jq -r --arg p "$CONTENT_PART" '.definition.parts[] | select(.path==$p) | .payload' | base64 -d | jq .

# List the dbt project files that ship with the item (under Code/dbt/)
echo "$DEF" | jq -r '.definition.parts[].path | select(startswith("Code/dbt/"))'

# 5. Check job run history
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID/jobs/instances" \
  --query "value[].{status:status, type:jobType, start:startTimeUtc, end:endTimeUtc, error:failureReason}" -o table
```

### Agentic Workflow

1. **Discover** → Steps 1–3 to list and identify dbt jobs.
2. **Inspect** → Step 4 to understand project type, adapter, command, and model selection.
3. **Monitor** → Step 5 for run history and error patterns.
4. **Iterate** → Drill into specific failures or configuration details.
5. **Present** → Summarize findings or generate a comparison table across jobs.
> **Monitoring note**: The Fabric UI provides a Lineage View (model dependency graph), Compiled SQL View (rendered SQL per model), and a Run Results Panel (per-model success/failure/timing). Via CLI, the equivalent is the job instance status and `failureReason` field from the polling response.
---

## Gotchas, Rules, Troubleshooting

### MUST DO

- **Always `az login` first** — `az rest` uses the active session. No session → cryptic failure.
- **Always `--resource "https://api.fabric.microsoft.com"`** — wrong audience = 401.
- **Handle pagination** — repeat requests with `continuationToken` until absent/null.
- **Handle LRO for `getDefinition`** — returns `202 Accepted` with `Location` header; poll until complete.
- **Discover the content-part name** — it is `dbt-content.json` on the live API (docs say `dbtjob-content.json`); decode whatever `getDefinition` returns rather than hardcoding.
- **Decode base64 before inspecting** — the content part is base64-encoded in the definition.
- **Use POST for `getDefinition`** — it is NOT a GET endpoint.
- **Trigger runs with `jobType=Execute`** — `DataBuildToolJob`/`Run`/`DbtJob` return 400.

### AVOID

- **Hardcoded GUIDs** — always discover via list-then-filter pattern.
- **Assuming `getDefinition` is GET** — it is POST (common mistake; GET returns 405).
- **Ignoring pagination** — list endpoints may return partial results.
- **Polling too aggressively** — respect `Retry-After` headers on 429s.

### PREFER

- **`az rest` over raw `curl`** — handles auth automatically.
- **List-then-filter pattern** — no server-side name filter for items; filter client-side by `displayName`.
- **Exponential backoff** for job polling — 15s → 30s → 60s cap.
- **`jq` for response parsing** — cleaner than shell string manipulation.
- **JMESPath `--query`** for simple field extraction directly in `az rest`.
- **Env vars** (`WS_ID`, `JOB_ID`, `API`, `RESOURCE`) for script reuse.

### TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token expired or wrong audience | `az login`; ensure `--resource "https://api.fabric.microsoft.com"` |
| `403 Forbidden` on `getDefinition` | Insufficient role | Requires Contributor role or higher |
| `404 Not Found` | Wrong workspace or item ID | Re-discover via list items with `type=DataBuildToolJob` |
| `getDefinition` returns `202` | LRO pattern | Poll the `Location` header URL until operation completes |
| Empty job list | No dbt jobs in workspace, or feature not enabled | Check tenant setting; feature requires admin opt-in |
| Base64 decode shows invalid JSON | Content encoding issue | Try `base64 -d` (Linux) or `[Convert]::FromBase64String` (PowerShell) |
| `429 TooManyRequests` | Rate limited | Respect `Retry-After` header; implement exponential backoff |
| Job history shows no entries | Job never triggered | Trigger via `jobs/instances?jobType=Execute` |
| 400 on run trigger | Wrong `jobType` value | Use `jobType=Execute` (not `DataBuildToolJob`) |
| Content part not found by name | Hardcoded `dbtjob-content.json` | Discover dynamically by matching part paths against the regex `dbt.?content\.json` |

---

## Examples

### Example 1: List All dbt Jobs in a Workspace

```bash
az rest --method get \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items?type=DataBuildToolJob" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[].{Name:displayName, Id:id}" -o table
```

### Example 2: Inspect a dbt Job Definition

```bash
# Step 1: Request definition (POST — may return 202 with Location header)
LOCATION=$(az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${JOB_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

# Step 2: Poll until definition is ready
DEF=$(az rest --method get --url "${LOCATION}" \
  --resource "https://api.fabric.microsoft.com")

# Step 3: Decode the dbt content part and display all settings (discover the part name first)
CONTENT_PART=$(echo "$DEF" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
echo "$DEF" | jq -r --arg p "$CONTENT_PART" '.definition.parts[] | select(.path==$p) | .payload' \
  | base64 -d | jq '{
      projectType: .project.projectType,
      folderPath: .project.folderPath,
      adapter: .profile.profileType,
      schema: .profile.schema,
      endPoint: .profile.connectionSettings.properties.typeProperties.endPoint,
      operation: .command.operation,
      select: .command.arguments.select,
      threads: .command.arguments.threads,
      fullRefresh: .command.arguments.fullRefresh
    }'
```

### Example 3: Check dbt Job Run History

```bash
# Get recent job instances with status and timing
az rest --method get \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${JOB_ID}/jobs/instances" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[].{Status:status, Start:startTimeUtc, End:endTimeUtc, Error:failureReason}" -o table
```

### Example 4: Trigger a dbt Job Run and Monitor

```bash
# Trigger run — jobType MUST be "Execute" (DataBuildToolJob/Run/DbtJob return 400)
LOCATION=$(az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${JOB_ID}/jobs/instances?jobType=Execute" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

echo "Polling job at: $LOCATION"

# Poll for completion
while true; do
  RESULT=$(az rest --method get --url "$LOCATION" --resource "https://api.fabric.microsoft.com")
  STATUS=$(echo "$RESULT" | jq -r '.status')
  echo "$(date -u '+%H:%M:%S') → $STATUS"
  [[ "$STATUS" == "Completed" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" ]] && break
  sleep 15
done

# Show failure reason if failed
if [[ "$STATUS" == "Failed" ]]; then
  echo "Failure reason:"
  echo "$RESULT" | jq '.failureReason'
fi
```

### Example 5: Compare dbt Job Configurations Across Workspaces

```bash
# Collect and compare definitions from two workspaces
for WS in "$WS_ID_1" "$WS_ID_2"; do
  echo "=== Workspace: $WS ==="
  az rest --method get \
    --url "https://api.fabric.microsoft.com/v1/workspaces/$WS/items?type=DataBuildToolJob" \
    --resource "https://api.fabric.microsoft.com" \
    --query "value[].{Name:displayName, Id:id}" -o table
done
```
