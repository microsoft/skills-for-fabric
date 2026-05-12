---
name: dataflows-authoring-cli
description: >
  Create, update, delete, and manage Fabric Dataflows Gen2 artifacts with Power Query M mashup definitions
  via CLI (az rest / curl). Uses az rest and curl against the Fabric REST API to author definitions containing
  base64-encoded mashup.pq, queryMetadata.json, and .platform parts. Supports creating dataflows with
  inline definitions, modifying mashup queries, binding connections, triggering Execute refresh jobs
  with typed parameter overrides, and exporting definitions for CI/CD. Use when the user wants to:
  (1) create a new Dataflow Gen2 with Power Query M queries, (2) update a dataflow mashup definition,
  (3) trigger a dataflow refresh job, (4) bind or manage dataflow connections, (5) set up CI/CD via
  definition export and import, (6) delete a dataflow, (7) configure staging destinations.
  Triggers: "create dataflow", "author dataflow", "Power Query M", "mashup document", "update dataflow
  definition", "refresh dataflow", "dataflow connection", "ETL dataflow", "dataflow CI/CD".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# Dataflows Gen2 — Authoring via CLI

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Definition Envelope | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Definition payload structure |
| Per-Item-Type Definitions | [ITEM-DEFINITIONS-CORE.md § Per-Item-Type Definitions](../../common/ITEM-DEFINITIONS-CORE.md#per-item-type-definitions) | Support matrix, decoded content, part paths — [REST specs](../../common/COMMON-CORE.md#item-creation), [CLI recipes](../../common/COMMON-CLI.md#item-crud-operations) |
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) ||
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes pagination and LRO helpers |
| Item CRUD Operations | [COMMON-CLI.md § Item CRUD Operations](../../common/COMMON-CLI.md#item-crud-operations) | Create, get/update definition, delete patterns |
| Job Execution (CLI) | [COMMON-CLI.md § Job Execution](../../common/COMMON-CLI.md#job-execution) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference | [COMMON-CLI.md § Quick Reference](../../common/COMMON-CLI.md#quick-reference) | `az rest` template + token audience/tool matrix |
| Authoring Capability Matrix | [DATAFLOWS-AUTHORING-CORE.md § Authoring Capability Matrix](../../common/DATAFLOWS-AUTHORING-CORE.md#authoring-capability-matrix) | Full CRUD lifecycle, parameterized refresh, Git CI/CD |
| Dataflow Definition Structure | [DATAFLOWS-AUTHORING-CORE.md § Dataflow Definition Structure](../../common/DATAFLOWS-AUTHORING-CORE.md#dataflow-definition-structure) | **Read first** — 3-part definition: queryMetadata.json, mashup.pq, .platform |
| REST API Surface (Authoring) | [DATAFLOWS-AUTHORING-CORE.md § REST API Surface](../../common/DATAFLOWS-AUTHORING-CORE.md#rest-api-surface-authoring) | Create, getDefinition, updateDefinition, delete, run job |
| Power Query M Code Structure | [DATAFLOWS-AUTHORING-CORE.md § Power Query M Code Structure](../../common/DATAFLOWS-AUTHORING-CORE.md#power-query-m-code-structure) | Section documents, multiple queries, parameters, fast copy |
| Connection Model | [DATAFLOWS-AUTHORING-CORE.md § Connection Model](../../common/DATAFLOWS-AUTHORING-CORE.md#connection-model) | Connection kinds, path patterns, connectionId requirements |
| Job Execution Patterns | [DATAFLOWS-AUTHORING-CORE.md § Job Execution Patterns](../../common/DATAFLOWS-AUTHORING-CORE.md#job-execution-patterns) | Trigger refresh, LRO polling, parameterized refresh |
| ALM / Git Integration | [DATAFLOWS-AUTHORING-CORE.md § ALM / Git Integration](../../common/DATAFLOWS-AUTHORING-CORE.md#alm--git-integration) | Export/import, CI/CD pipeline, cross-environment overrides |
| Gotchas and Troubleshooting | [DATAFLOWS-AUTHORING-CORE.md § Gotchas and Troubleshooting](../../common/DATAFLOWS-AUTHORING-CORE.md#gotchas-and-troubleshooting) | 15-row issue/cause/resolution table |
| Quick Reference: Authoring Decision Guide | [DATAFLOWS-AUTHORING-CORE.md § Quick Reference](../../common/DATAFLOWS-AUTHORING-CORE.md#quick-reference-authoring-decision-guide) | Scenario → recommended approach lookup |
| Core Authoring via CLI | [authoring-cli-quickref.md § Core Authoring via CLI](references/authoring-cli-quickref.md#core-authoring-via-cli) | Create, get/update definition, delete, refresh `az rest` one-liners |
| Base64 Encoding Helpers | [authoring-cli-quickref.md § Base64 Encoding Helpers](references/authoring-cli-quickref.md#base64-encoding-helpers) | Encode/decode definition parts in bash and PowerShell |
| Definition Manipulation | [authoring-cli-quickref.md § Definition Manipulation Patterns](references/authoring-cli-quickref.md#definition-manipulation-patterns) | Read-modify-write workflow for definitions |
| Bash Templates | [authoring-script-templates.md § Bash Templates](references/authoring-script-templates.md#bash-templates) | Create dataflow, read-modify-write, refresh with LRO, CI/CD export/import |
| PowerShell Templates | [authoring-script-templates.md § PowerShell Templates](references/authoring-script-templates.md#powershell-templates) | Create dataflow, trigger refresh with polling |
| Tool Stack | [SKILL.md § Tool Stack](#tool-stack) | `az` CLI + `jq` + `base64`; verify before first op |
| Connection | [SKILL.md § Connection](#connection) | Workspace/dataflow ID discovery via REST |
| Agentic Workflows | [SKILL.md § Agentic Workflows](#agentic-workflows) | **Start here** — discover→formulate→execute→verify |
| Gotchas, Rules, Troubleshooting | [SKILL.md § Gotchas, Rules, Troubleshooting](#gotchas-rules-troubleshooting) | **MUST DO / AVOID / PREFER** checklists |
| Agent Integration Notes | [authoring-cli-quickref.md § Agent Integration Notes](references/authoring-cli-quickref.md#agent-integration-notes) | Platform-specific tips (Copilot CLI, Claude Code) |

---

## Tool Stack

| Tool | Role | Install |
|---|---|---|
| `az` CLI | **Primary**: Auth (`az login`), REST API calls (`az rest`), token acquisition. | Pre-installed in most dev environments |
| `jq` | Parse and manipulate JSON responses and definition payloads. | Pre-installed or trivial |
| `base64` | Encode/decode definition parts for the REST API. | Built into bash / `[Convert]::ToBase64String()` in PowerShell |
| `curl` | Alternative to `az rest` when raw HTTP control is needed. | Pre-installed |

> **Agent check** — verify before first operation:
> ```bash
> az --version 2>/dev/null || echo "INSTALL: https://aka.ms/install-azure-cli"
> jq --version 2>/dev/null || echo "INSTALL: apt-get install jq OR brew install jq"
> ```

---

## Connection

### Discover Workspace and Dataflow IDs

Per [COMMON-CLI.md](../../common/COMMON-CLI.md) Finding Workspaces and Items in Fabric:

```bash
# List workspaces — find workspace ID by name
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='MyWorkspace'].id" --output tsv

# List dataflows in workspace — find dataflow ID by name
WS_ID="<workspaceId>"
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/dataflows" \
  --query "value[?displayName=='MyDataflow'].id" --output tsv
```

### Reusable Connection Variables

```bash
WS_ID="<workspaceId>"
DF_ID="<dataflowId>"
API="https://api.fabric.microsoft.com/v1"
RESOURCE="https://api.fabric.microsoft.com"
```

---

## Agentic Workflows

### Discover → Formulate → Execute → Verify

1. **Discover** → List workspaces, list dataflows, get definition (decode to inspect M code and metadata).
2. **Formulate** → Create or modify M code (`mashup.pq`), update `queriesMetadata`, prepare all 3 definition parts.
3. **Execute** → Create or update dataflow via REST API, optionally trigger refresh.
4. **Verify** → Poll LRO for completion, get definition again to confirm changes, check refresh status.

```bash
# 1. Discover — get current definition
RESULT=$(az rest --method post \
  --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition")

# Decode mashup.pq to inspect current queries
echo "$RESULT" | jq -r '.definition.parts[] | select(.path=="mashup.pq") | .payload' | base64 -d

# 2. Formulate — edit M code, prepare new definition parts
# (modify the decoded mashup, re-encode, build JSON payload)

# 3. Execute — update definition
az rest --method post \
  --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/updateDefinition?updateMetadata=true" \
  --body @definition.json

# 4. Verify — trigger refresh and poll
LOCATION=$(az rest --method post \
  --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$DF_ID/jobs/Execute/instances" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')
```

---

## Gotchas, Rules, Troubleshooting

For full authoring gotchas: [DATAFLOWS-AUTHORING-CORE.md](../../common/DATAFLOWS-AUTHORING-CORE.md) Gotchas and Troubleshooting.
For CLI-specific issues: [COMMON-CLI.md](../../common/COMMON-CLI.md) Gotchas & Troubleshooting (CLI-Specific).

### MUST DO

- **`az login` first** — all `az rest` calls use the active session. No session → 401.
- **Always `--resource "https://api.fabric.microsoft.com"`** — wrong audience = 401.
- **Base64-encode all definition parts** — REST API expects `payloadType: "InlineBase64"`.
- **Send all 3 parts in updateDefinition** — it's a full replacement, not incremental.
- **Handle LRO polling** — `getDefinition`, `updateDefinition` (with def), and job execution return 202; poll via `Location` header.
- **Verify workspace has capacity** — `GET /v1/workspaces/{id}` and check `capacityId`.
- **Set `formatVersion` to `"202502"`** in `queryMetadata.json`.
- **Set `loadEnabled: true`** for queries that should write output on refresh.

### AVOID

- **Hardcoded GUIDs** — discover workspace/dataflow IDs via REST API (Connection section).
- **Skipping base64 encoding** — payloads will be rejected or corrupted.
- **Partial definition updates** — sending 1 or 2 parts silently drops queries.
- **Creating dataflows with unbound connections** — queries referencing nonexistent `connectionId` will fail at refresh.
- **Using GET for `getDefinition`** — it's a POST endpoint; GET returns 405.
- **Constructing operation URLs manually** — always use the `Location` header from 202 responses.
- **Duplicate `displayName`** values — not enforced but causes confusion.

### PREFER

- **`az rest` over raw `curl`** — handles token acquisition and refresh automatically.
- **`getDefinition` before `updateDefinition`** — read-modify-write prevents accidental data loss.
- **Validate M code before creating dataflow** — syntax errors won't surface until refresh.
- **`jq` for JSON manipulation** — build definition payloads programmatically.
- **`"Automatic"` for parameter type in job execution** — lets engine infer from definition.
- **`?updateMetadata=true`** on `updateDefinition` — ensures `.platform` changes (display name) are applied.
- **Env vars** (`WS_ID`, `DF_ID`, `API`, `RESOURCE`) for script reuse.

### TROUBLESHOOTING

| Symptom | Fix |
|---|---|
| 401 Unauthorized | Verify `az login` is active; check `--resource "https://api.fabric.microsoft.com"` |
| 405 Method Not Allowed on getDefinition | Use POST, not GET — `getDefinition` follows LRO pattern |
| updateDefinition silently drops queries | Send all 3 parts (queryMetadata.json, mashup.pq, .platform) |
| Refresh fails on new dataflow | Ensure `connectionId` values exist in user's Fabric connection store |
| formatVersion mismatch error | Set `formatVersion` to `"202502"` in queryMetadata.json |
| Query doesn't produce output | Set `loadEnabled: true` in `queriesMetadata` |
| Fast copy not engaged | Add `[StagingDefinition = [Kind = "FastCopy"]]` before `section` in mashup.pq |
| LRO polling returns 404 | Use `Location` header URL — don't construct operation URLs manually |
| 429 Too Many Requests | Respect `Retry-After` header; implement exponential backoff |
| base64 decode produces garbage | Ensure no trailing newlines; use `base64 -w0` (Linux) for encoding |

---

## Examples

### Example 1: Create a Dataflow Gen2 with Inline Definition

```bash
# 1. Prepare mashup.pq
MASHUP='section Section1;
shared Output = let
    Source = #table(type table [Name = text, Value = number],
        {{"Alpha", 100}, {"Beta", 200}, {"Gamma", 300}})
in Source;'

# 2. Prepare queryMetadata.json
QUERY_META='{
  "formatVersion": "202502",
  "queriesMetadata": {
    "Output": { "queryId": "00000000-0000-0000-0000-000000000001",
                "queryName": "Output", "loadEnabled": true }
  }
}'

# 3. Prepare .platform
PLATFORM='{"$schema":"https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json","metadata":{"type":"Dataflow","displayName":"MyDataflow"},"config":{"version":"2.0","logicalId":"00000000-0000-0000-0000-000000000001"}}'

# 4. Base64-encode all parts
MASHUP_B64=$(echo -n "$MASHUP" | base64 -w0)
META_B64=$(echo -n "$QUERY_META" | base64 -w0)
PLAT_B64=$(echo -n "$PLATFORM" | base64 -w0)

# 5. Create the dataflow
az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body "{
    \"displayName\": \"MyDataflow\",
    \"type\": \"Dataflow\",
    \"definition\": {
      \"parts\": [
        {\"path\": \"mashup.pq\",          \"payload\": \"${MASHUP_B64}\", \"payloadType\": \"InlineBase64\"},
        {\"path\": \"queryMetadata.json\", \"payload\": \"${META_B64}\",   \"payloadType\": \"InlineBase64\"},
        {\"path\": \".platform\",          \"payload\": \"${PLAT_B64}\",   \"payloadType\": \"InlineBase64\"}
      ]
    }
  }"
```

### Example 2: Trigger a Refresh Job

```bash
# Trigger refresh (returns 202 + Location header for polling)
LOCATION=$(az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${DF_ID}/jobs/Execute/instances" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

# Poll until complete
while true; do
  STATUS=$(az rest --method get --url "$LOCATION" \
    --resource "https://api.fabric.microsoft.com" --query "status" -o tsv)
  echo "Status: $STATUS"
  [[ "$STATUS" == "Completed" || "$STATUS" == "Failed" ]] && break
  sleep 10
done
```

### Example 3: Update a Dataflow Definition

```bash
# Get current definition (POST, not GET — returns 202)
LOCATION=$(az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${DF_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

# Poll for the definition
DEF=$(az rest --method get --url "${LOCATION}" \
  --resource "https://api.fabric.microsoft.com")

# Decode, modify, re-encode, then updateDefinition with all 3 parts
az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${DF_ID}/updateDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body "{\"definition\": {\"parts\": [ ... ]}}"
```
