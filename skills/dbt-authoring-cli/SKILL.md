---
name: dbt-authoring-cli
description: >
  Create, update, delete, and run Fabric dbt jobs (DataBuildToolJob) via CLI (az rest / curl).
  Uses az rest against the Fabric REST API to manage dbt job definitions containing project settings,
  profile (adapter type, schema, connection), and command (operation, model selection, arguments).
  Supports Fabric Warehouse, Snowflake, PostgreSQL, and Azure SQL Server adapters. Use when the
  user wants to: (1) create a new dbt job in a Fabric workspace, (2) update dbt job settings
  (project type, profile adapter, command operation), (3) trigger a dbt job run, (4) connect a
  dbt job to a Fabric Warehouse or external database via connection ID, (5) manage dbt job
  definitions for CI/CD, (6) delete a dbt job.
  Triggers: "create dbt job", "dbt job", "dbt run", "dbt build", "dbt test", "dbt models fabric",
  "DataBuildToolJob", "dbt warehouse", "dbt transformation fabric", "dbt CI/CD fabric".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare it against the remote version via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If the remote version is newer, show the changelog and update instructions.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# dbt Jobs — Authoring via CLI

> **When to use this skill vs. alternatives** — use dbt (DataBuildToolJob) for **versioned, multi-model SQL transformations** into a Fabric Warehouse, with lineage, dependency ordering, and built-in tests. For ad-hoc DDL/DML, ingestion (`COPY INTO`), and one-off warehouse operations, prefer the **`sqldw-authoring-cli`** skill (raw `sqlcmd` T-SQL). For Lakehouse/PySpark/Delta transformations, prefer the **`spark-authoring-cli`** skill. For an end-to-end Bronze→Silver→Gold build, see the **`e2e-medallion-architecture`** skill, which can orchestrate dbt or Spark per layer.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Definition Envelope | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Definition payload structure |
| Per-Item-Type Definitions | [ITEM-DEFINITIONS-CORE.md § Per-Item-Type Definitions](../../common/ITEM-DEFINITIONS-CORE.md#per-item-type-definitions) | DataBuildToolJob: live part is `dbt-content.json` (docs say `dbtjob-content.json` — discover via `getDefinition`) |
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) ||
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes pagination and LRO helpers |
| Item CRUD Operations | [COMMON-CLI.md § Item CRUD Operations](../../common/COMMON-CLI.md#item-crud-operations) | Create, get/update definition, delete patterns |
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
| `az` CLI | **Primary**: Auth (`az login`), REST API calls (`az rest`), token acquisition | Pre-installed in most dev environments |
| `jq` | Parse and manipulate JSON responses and definition payloads | Pre-installed or trivial |
| `base64` | Encode/decode definition parts for the REST API | Built into bash / `[Convert]::ToBase64String()` in PowerShell |
| `curl` | Alternative to `az rest` when raw HTTP control is needed | Pre-installed |

> **Agent check** — verify before first operation:
> ```bash
> az --version 2>/dev/null || echo "INSTALL: https://aka.ms/install-azure-cli"
> jq --version 2>/dev/null || echo "INSTALL: apt-get install jq OR brew install jq"
> ```

---

## dbt Job Definition Structure

A dbt job is a `DataBuildToolJob` item. Its definition contains:

1. **A content part** describing project + profile + command settings.
2. **The dbt project files** themselves (`dbt_project.yml`, `models/`, `macros/`, …), stored under `Code/dbt/` and surfaced as definition parts `Code/dbt/...`.
3. **`.platform`** — common item metadata.

> ⚠️ **VERIFIED PART NAME** — The official docs list the content part as `dbtjob-content.json`, but the **live Fabric API uses `dbt-content.json`** (this is the name returned by `getDefinition` and auto-seeded when you create the item). **Always discover the actual part name with `getDefinition` first; never hardcode it.** Examples below read the path dynamically.

### Content part schema (`dbt-content.json`)

```json
{
  "project": {
    "projectType": "OneLake",
    "folderPath": "dbt"
  },
  "profile": {
    "profileType": "DataWarehouse",
    "schema": "<target schema name>",
    "connectionSettings": {
      "name": "<connection / warehouse display name>",
      "properties": {
        "type": "DataWarehouse",
        "typeProperties": {
          "workspaceId": "<guid of workspace holding the warehouse>",
          "artifactId": "<guid of the target warehouse>",
          "endPoint": "<fqdn>.datawarehouse.fabric.microsoft.com"
        }
      }
    }
  },
  "command": {
    "operation": "build",
    "arguments": {
      "select": "<comma-separated model names>",
      "exclude": "<comma-separated model names>",
      "fullRefresh": false,
      "failFast": false,
      "threads": 4,
      "selectorName": "<dbt selector name>"
    }
  }
}
```

> ⚠️ **VERIFIED CONNECTION SHAPE (Fabric Warehouse)** — The docs show a *flat* shape
> (`connectionSettings.type` + `connectionSettings.properties.workspaceId`). That shape
> **fails at runtime** with `The data source type is not supported`. The shape that
> actually works nests the connection like a Fabric linked service:
> `connectionSettings.name` + `connectionSettings.properties.type` +
> `connectionSettings.properties.typeProperties.{workspaceId, artifactId, endPoint}`.
> The `endPoint` (the warehouse `…datawarehouse.fabric.microsoft.com` FQDN) is the key
> missing piece — include it. Get the FQDN from the warehouse item's
> `properties.connectionString`.

- `project.folderPath` is the dbt project folder **relative to the item's `Code/` folder**, so `"dbt"` means the project lives at `Code/dbt/`.
- The connection is **absolute** (workspaceId + artifactId), so the dbt item can live in *any* workspace and still write to the referenced warehouse (see [Cross-Workspace & Cross-Database](#cross-workspace--cross-database)).

### Profile types and connection patterns

| Adapter | `profileType` | Connection approach |
|---|---|---|
| Fabric Warehouse | `DataWarehouse` | `connectionSettings` with the nested `properties.typeProperties` shape above (workspaceId + artifactId + endPoint) |
| Snowflake | `Snowflake` | `externalReferences.connection` (connection GUID) |
| PostgreSQL | `PostgreSql` | `externalReferences.connection` (connection GUID) |
| Azure SQL Server | `AzureSql` | `externalReferences.connection` (connection GUID) |

For non-Fabric adapters, replace `connectionSettings` with:

```json
"externalReferences": { "connection": "<connection GUID>" }
```

### Project types

| Type | When to use |
|---|---|
| `OneLake` | dbt project stored in the dbt item's own OneLake `Code/dbt/` folder (default) |
| `Lakehouse` | dbt project stored in a specific Fabric Lakehouse |

### Supported commands (`operation` values)

| Operation | Description |
|---|---|
| `run` | Runs all SQL models in dependency order |
| `build` | Runs models + seeds + tests in one pass (recommended default) |
| `seed` | Loads CSV files from the `seeds/` directory as managed tables |
| `test` | Runs schema and data tests defined in `schema.yml` |
| `compile` | Generates compiled SQL without executing transformations |
| `snapshot` | Captures and tracks slowly changing dimensions over time |
| `show` | Previews model results without persisting |

### Expected dbt project layout (under `Code/dbt/`)

```
Code/dbt/
├── dbt_project.yml      # name, profile, model-paths, materialization config
├── models/
│   ├── sources.yml      # source() definitions (add database: for cross-DB reads)
│   ├── staging/         # or bronze/silver
│   └── marts/           # or gold
├── macros/              # optional reusable Jinja/SQL macros
├── seeds/               # optional CSV files loaded via the seed command
└── schema.yml           # optional tests/descriptions (can also live per-folder)
```

- `dbt_project.yml` — the `profile:` value here is cosmetic for Fabric (the real connection comes from `dbt-content.json`); set `name:` to match the top key under `models:`.
- Each `.sql` file under `models/` is one model; subfolders map to schema paths unless overridden.
- `sources.yml` — add a `database: <OtherDatabase>` to a source to emit cross-database 3-part names `[Other].[schema].[table]` (see [Cross-Workspace & Cross-Database](#cross-workspace--cross-database)).

---

## Connection

### Discover Workspace and Item IDs

Per [COMMON-CLI.md](../../common/COMMON-CLI.md) Finding Workspaces and Items in Fabric:

```bash
# List workspaces — find workspace ID by name
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='MyWorkspace'].id" --output tsv

# List dbt jobs in workspace — find item ID by name
WS_ID="<workspaceId>"
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items?type=DataBuildToolJob" \
  --query "value[?displayName=='MyDbtJob'].id" --output tsv

# Find Fabric Warehouse ID (for profile connectionSettings)
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items?type=Warehouse" \
  --query "value[?displayName=='MyWarehouse'].id" --output tsv
```

### Reusable Connection Variables

```bash
WS_ID="<workspaceId>"
JOB_ID="<dbtJobItemId>"
WH_ID="<warehouseItemId>"
API="https://api.fabric.microsoft.com/v1"
RESOURCE="https://api.fabric.microsoft.com"
```

---

## Agentic Workflows

### Discover → Formulate → Execute → Verify

1. **Discover** → List workspaces/items, get the warehouse FQDN, `getDefinition` to read the current content part (and its real path).
2. **Formulate** → Write the dbt project files locally and build the content part (`project`, `profile`, `command`).
3. **Execute** → Create the item (dedicated endpoint), upload project files to `Code/dbt/`, then `updateDefinition` with **all** parts.
4. **Verify** → Trigger the run (`jobType=Execute`) and poll until `Completed`; inspect `failureReason` on failure.

```bash
# 1. CREATE the item — use the dedicated dataBuildToolJobs endpoint (body = name + description).
#    NOTE: POST /items with a full definition often returns InvalidDefinitionFormat for dbt — use this instead.
JOB_ID=$(az rest --method post \
  --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/dataBuildToolJobs" \
  --headers "Content-Type=application/json" \
  --body '{"displayName":"MyDbtJob","description":"SilverLake -> Gold warehouse"}' \
  --query "id" -o tsv)

# 2. DISCOVER the warehouse FQDN (endPoint) and the live content-part name.
WH_FQDN=$(az rest --method get --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$WH_ID" \
  --query "properties.connectionString" -o tsv)

LOCATION=$(az rest --method post --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID/getDefinition" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')
DEF=$(az rest --method get --url "$LOCATION" --resource "$RESOURCE")
# Live API names this "dbt-content.json" (docs say "dbtjob-content.json") — read it, don't assume:
CONTENT_PART=$(echo "$DEF" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
echo "content part = $CONTENT_PART"

# 3. UPLOAD the dbt project files to OneLake under Code/dbt/ (see "Uploading Project Files" section).

# 4. FORMULATE the content part (verified Warehouse connection shape — note properties.typeProperties + endPoint).
cat > dbt-content.json <<EOF
{
  "project": { "projectType": "OneLake", "folderPath": "dbt" },
  "profile": {
    "profileType": "DataWarehouse",
    "schema": "gold",
    "connectionSettings": {
      "name": "MyWarehouse",
      "properties": {
        "type": "DataWarehouse",
        "typeProperties": {
          "workspaceId": "$WS_ID",
          "artifactId": "$WH_ID",
          "endPoint": "$WH_FQDN"
        }
      }
    }
  },
  "command": { "operation": "build", "arguments": { "exclude": "", "threads": 4 } }
}
EOF

# 5. EXECUTE updateDefinition — resend EVERY part (content + all Code/dbt/* files + .platform),
#    otherwise updateDefinition drops the model files. See build_parts() in the Examples section.

# 6. VERIFY — trigger the run. jobType MUST be "Execute" (DataBuildToolJob/Run/DbtJob all 400).
LOCATION=$(az rest --method post --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID/jobs/instances?jobType=Execute" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

while true; do
  RESULT=$(az rest --method get --url "$LOCATION" --resource "$RESOURCE")
  STATUS=$(echo "$RESULT" | jq -r '.status')
  echo "$(date -u '+%H:%M:%S') Status: $STATUS"
  [[ "$STATUS" == "Completed" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" ]] && break
  sleep 15
done
[[ "$STATUS" == "Failed" ]] && echo "$RESULT" | jq '.failureReason'
```

---

## Uploading Project Files to OneLake

The dbt project files live under the item's OneLake path `…/{itemId}/Code/dbt/`. Upload them with the
OneLake DFS API (token audience **`https://storage.azure.com`**), then register them as definition parts.

```bash
# Storage-scoped token for OneLake DFS (different audience than the control plane!)
STG_TOKEN=$(az account get-access-token --resource "https://storage.azure.com" --query accessToken -o tsv)
ONELAKE="https://onelake.dfs.fabric.microsoft.com"

upload_file() {  # $1 = local path, $2 = relative path under Code/dbt/
  local rel="$2"
  local url="$ONELAKE/$WS_ID/$JOB_ID/Code/dbt/$rel"
  local len; len=$(wc -c < "$1")
  curl -s -X PUT   -H "Authorization: Bearer $STG_TOKEN" "$url?resource=file" >/dev/null
  curl -s -X PATCH -H "Authorization: Bearer $STG_TOKEN" --data-binary "@$1" "$url?action=append&position=0" >/dev/null
  curl -s -X PATCH -H "Authorization: Bearer $STG_TOKEN" "$url?action=flush&position=$len" >/dev/null
  echo "uploaded Code/dbt/$rel ($len bytes)"
}

upload_file ./dbt/dbt_project.yml          dbt_project.yml
upload_file ./dbt/models/sources.yml       models/sources.yml
upload_file ./dbt/models/gold/dim_x.sql    models/gold/dim_x.sql
# … repeat for every model/macro/seed file …
```

> The files also become part of the item **definition** as `Code/dbt/...` parts. Whether you upload via
> DFS or include them in `updateDefinition`, you must keep both views consistent — the safest pattern is to
> upload via DFS **and** resend every file in `updateDefinition` (read-modify-write).

---

## Cross-Workspace & Cross-Database

- **Cross-workspace**: the `profile.connectionSettings` points to an absolute `workspaceId` + `artifactId`. The dbt item therefore runs from *any* workspace and writes to the referenced warehouse regardless of where the item lives — useful for separating orchestration from storage. (Verified: a copied dbt item in a different workspace wrote to the original warehouse.)
- **Cross-database sources**: dbt-fabric resolves a `source()` to a 3-part name when the `sources.yml` entry has a `database:` property:

  ```yaml
  version: 2
  sources:
    - name: silver
      database: SilverLake     # emits [SilverLake].[dbo].[table]
      schema: dbo
      tables:
        - name: salesorderheader
  ```

  This lets gold models in the warehouse read directly from a Lakehouse/warehouse in the **same workspace SQL scope** without copying data. The executing identity needs read access to the source.

---

## Fabric Warehouse T-SQL Surface Limits (for dbt models)

Fabric Data Warehouse has a reduced T-SQL surface. dbt `table` materialization runs `CREATE TABLE AS SELECT`, so any unsupported type/expression in a model's `SELECT` fails the run. Verified gotchas:

- **No `nvarchar`** — functions like `DATENAME()` (and `CONCAT()` over Unicode inputs) emit `nvarchar`, which the warehouse rejects (`The data type 'nvarchar(N)' … is not supported in this edition of SQL Server`). Wrap them: `CAST(DATENAME(MONTH, d) AS VARCHAR(20))`.
- **Computed source columns may not exist** — e.g. AdventureWorks `SalesOrderNumber`, `TotalDue`, `LineTotal` are computed columns that are often absent in the raw landed table. Verify with `sys.columns` and derive them in SQL (`CONCAT('SO', SalesOrderID)`, `SubTotal + TaxAmt + Freight`).
- **Validate before running** — a quick `sqlcmd -S <fqdn> -d <db> -G -Q "SELECT TOP 1 …"` against the source confirms column names and types and avoids a failed dbt run.
- Adapter facts: **dbt-fabric** (Fabric Warehouse adapter), dbt Core 1.9 / dbt-fabric 1.9.0, Python 3.12, **Microsoft Entra OAuth** — the run authenticates as the job's identity, so no password is stored.

---

## Gotchas, Rules, Troubleshooting

### MUST DO

- **`az login` first** — all `az rest` calls use the active session. No session → 401.
- **Always `--resource "https://api.fabric.microsoft.com"`** — wrong audience = 401.
- **Discover the content-part name via `getDefinition`** — it is `dbt-content.json` on the live API (docs say `dbtjob-content.json`). Never hardcode.
- **Use the verified Warehouse connection shape** — `connectionSettings.properties.{type, typeProperties:{workspaceId, artifactId, endPoint}}`. Omitting `endPoint` / using the flat doc shape → `data source type is not supported`.
- **Create the item via `POST …/dataBuildToolJobs`** (body = `displayName` + `description`). The generic `/items` create with a full definition can return `InvalidDefinitionFormat`.
- **Trigger runs with `jobType=Execute`** — `DataBuildToolJob`/`Run`/`DbtJob` return 400. (`POST …/dataBuildToolJobs/{id}/jobs/execute/instances` also works.)
- **Resend ALL parts in `updateDefinition`** — sending only the content part silently drops the `Code/dbt/*` model files. Read-modify-write, preserving `.platform`.
- **Base64-encode every part** — REST API expects `payloadType: "InlineBase64"`.
- **Handle LRO polling** — `getDefinition`, `updateDefinition`, and job execution return 202; poll via `Location` header.
- **Enable dbt jobs preview in Fabric tenant settings** — the feature requires admin opt-in under Tenant Settings → dbt jobs (preview).
- **Use `externalReferences.connection` for non-Fabric adapters** (Snowflake, PostgreSQL, AzureSQL).
- **Contributor role or higher required** — in the workspace and on the target Warehouse (and read access on cross-database sources).

### AVOID

- **Hardcoded GUIDs or the content-part name** — discover both via REST API.
- **The flat doc connection shape** for Fabric Warehouse — it fails at runtime; use the nested `typeProperties` + `endPoint` shape.
- **Partial `updateDefinition`** — always resend the full part list, or model files disappear.
- **`nvarchar`-producing expressions in warehouse models** — `CAST(... AS VARCHAR(n))`.
- **Skipping base64 encoding** — payloads will be rejected.
- **Using `connectionSettings` for Snowflake/PostgreSQL/AzureSQL** — use `externalReferences.connection` instead.
- **Constructing operation URLs manually** — always use the `Location` header from 202 responses.
- **Running without a valid dbt project under `Code/dbt/`** — the job fails at runtime with a project-not-found error.

### PREFER

- **`az rest` over raw `curl`** for the control plane — handles tokens; use `curl` only for OneLake DFS uploads (storage audience).
- **`getDefinition` before `updateDefinition`** — read-modify-write prevents accidental overwrites and discovers the part name.
- **`jq` for JSON manipulation** — build and inspect definition payloads programmatically.
- **Validate source schema with `sqlcmd`** before authoring models — catches missing/renamed columns early.
- **Env vars** (`WS_ID`, `JOB_ID`, `WH_ID`, `WH_FQDN`, `API`, `RESOURCE`) for script reuse.
- **`threads: 4`** as a safe default; increase only for large model graphs with sufficient warehouse capacity.
- **`build` over `run`** when you also want seeds and tests in one command.
- **`{{ ref() }}` between models, `{{ source() }}` for raw inputs** — let dbt order the DAG; cross-DB reads via source `database:`.
- **Staged model layout** (`staging/`→`marts/` or `bronze/`→`silver/`→`gold/`) — aligns with medallion architecture.
- **`selectorName` or `select`/`exclude`** for targeted runs during development.
- **`sqldw-authoring-cli` for non-dbt warehouse work, `spark-authoring-cli` for Lakehouse transformations** — don't force ad-hoc DDL/ingestion or PySpark logic into dbt models; reach for the matching skill instead.

### TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Token expired or wrong audience | `az login`; `--resource "https://api.fabric.microsoft.com"` (or `https://storage.azure.com` for OneLake DFS) |
| 403 Forbidden on create/update | Insufficient workspace role | Requires Contributor or higher |
| 404 on getDefinition | Wrong workspace or item ID | Re-discover via list items with `type=DataBuildToolJob` |
| `InvalidDefinitionFormat` on create | Created via `/items` with full definition | Create with `POST …/dataBuildToolJobs` (name + description), then `updateDefinition` |
| 400 on run trigger | Wrong `jobType` | Use `jobType=Execute` (not `DataBuildToolJob`) |
| Run fails: `The data source type is not supported` | Flat doc connection shape / missing `endPoint` | Use nested `properties.typeProperties` with `workspaceId`+`artifactId`+`endPoint` |
| Run fails: `nvarchar(N) … not supported` | Warehouse rejects nvarchar from `DATENAME`/`CONCAT` | `CAST(... AS VARCHAR(n))` |
| Run fails: `Invalid column name '…'` | Computed source column absent (e.g. SalesOrderNumber) | Verify with `sys.columns`; derive the value in SQL |
| Model files vanished after edit | Partial `updateDefinition` | Resend every part (content + all `Code/dbt/*` + `.platform`) |
| Run fails: "dbt project not found" | Wrong `folderPath` or missing files | `folderPath` is relative to `Code/`; ensure files exist under `Code/dbt/` |
| Run fails: "connection not found" | Invalid `artifactId`/`connection` GUID | Re-discover Warehouse ID or Fabric connection GUID |
| 400 on create: feature not enabled | dbt jobs preview not enabled | Admin enables under Tenant Settings → dbt jobs (preview) |
| `429 TooManyRequests` | Rate limited | Respect `Retry-After`; exponential backoff |

---

## Examples

Shared setup for the examples:

```bash
WS_ID="<workspaceId>"
WH_ID="<warehouseItemId>"
RESOURCE="https://api.fabric.microsoft.com"
API="https://api.fabric.microsoft.com/v1"
```

### Example 1: Create a dbt Job end-to-end (Fabric Warehouse adapter)

```bash
# 1. Create the item (dedicated endpoint — NOT /items with a full definition).
JOB_ID=$(az rest --method post --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/dataBuildToolJobs" \
  --headers "Content-Type=application/json" \
  --body '{"displayName":"MyDbtJob","description":"Silver -> Gold warehouse"}' \
  --query "id" -o tsv)

# 2. Discover the warehouse FQDN (the endPoint value).
WH_FQDN=$(az rest --method get --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$WH_ID" \
  --query "properties.connectionString" -o tsv)

# 3. Upload project files to Code/dbt/ (see "Uploading Project Files to OneLake").

# 4. Build the content part (verified nested Warehouse connection shape).
cat > dbt-content.json <<EOF
{
  "project": { "projectType": "OneLake", "folderPath": "dbt" },
  "profile": {
    "profileType": "DataWarehouse",
    "schema": "gold",
    "connectionSettings": {
      "name": "MyWarehouse",
      "properties": {
        "type": "DataWarehouse",
        "typeProperties": {
          "workspaceId": "$WS_ID",
          "artifactId": "$WH_ID",
          "endPoint": "$WH_FQDN"
        }
      }
    }
  },
  "command": { "operation": "build", "arguments": { "exclude": "", "threads": 4 } }
}
EOF

# 5. updateDefinition with ALL parts — see build_and_update() in Example 3.
```

### Example 2: Create a dbt Job (Snowflake / PostgreSQL / Azure SQL adapter)

Non-Fabric adapters use a pre-created Fabric **connection** GUID via `externalReferences`:

```bash
CONN_ID="<connectionGuid>"   # create under Manage connections in Fabric first

cat > dbt-content.json <<EOF
{
  "project": { "projectType": "OneLake", "folderPath": "dbt" },
  "profile": {
    "profileType": "Snowflake",
    "schema": "analytics",
    "externalReferences": { "connection": "$CONN_ID" }
  },
  "command": { "operation": "build", "arguments": { "fullRefresh": true, "failFast": true, "threads": 8 } }
}
EOF
# Then upload project files + updateDefinition as in Example 1/3.
```

### Example 3: updateDefinition with ALL parts (the safe read-modify-write)

`updateDefinition` **replaces** the part list, so you must resend the content part, every
`Code/dbt/*` file, and `.platform` together. This helper rebuilds the full payload from the
local project folder.

```bash
build_and_update() {
  local local_root="./dbt"        # local folder mirroring Code/dbt/
  local parts="[]"

  add_part() {  # $1 = part path, $2 = local file
    local b64; b64=$(base64 -w0 < "$2")
    parts=$(echo "$parts" | jq --arg p "$1" --arg pl "$b64" \
      '. + [{path:$p, payload:$pl, payloadType:"InlineBase64"}]')
  }

  # content part — discover the live name (dbt-content.json), fall back if absent
  add_part "dbt-content.json" "dbt-content.json"

  # every project file under Code/dbt/
  while IFS= read -r f; do
    rel="${f#"$local_root"/}"
    add_part "Code/dbt/$rel" "$f"
  done < <(find "$local_root" -type f)

  # preserve .platform from the current definition
  LOCATION=$(az rest --method post --resource "$RESOURCE" \
    --url "$API/workspaces/$WS_ID/items/$JOB_ID/getDefinition" \
    --headers "Content-Length=0" \
    --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')
  PLATFORM=$(az rest --method get --url "$LOCATION" --resource "$RESOURCE" \
    | jq -r '.definition.parts[] | select(.path==".platform") | .payload')
  [ -n "$PLATFORM" ] && parts=$(echo "$parts" | jq --arg pl "$PLATFORM" \
    '. + [{path:".platform", payload:$pl, payloadType:"InlineBase64"}]')

  az rest --method post --resource "$RESOURCE" \
    --url "$API/workspaces/$WS_ID/items/$JOB_ID/updateDefinition" \
    --headers "Content-Type=application/json" \
    --body "$(jq -n --argjson parts "$parts" '{definition:{parts:$parts}}')"
}

build_and_update
```

### Example 4: Trigger a dbt Job Run and Poll for Completion

```bash
# jobType MUST be "Execute" — DataBuildToolJob/Run/DbtJob return 400.
LOCATION=$(az rest --method post --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID/jobs/instances?jobType=Execute" \
  --headers "Content-Length=0" \
  --output none --include-response-headers 2>&1 | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

while true; do
  RESULT=$(az rest --method get --url "$LOCATION" --resource "$RESOURCE")
  STATUS=$(echo "$RESULT" | jq -r '.status')
  echo "$(date -u '+%H:%M:%S') Status: $STATUS"   # NotStarted -> InProgress -> Completed/Failed
  [[ "$STATUS" == "Completed" || "$STATUS" == "Failed" || "$STATUS" == "Cancelled" ]] && break
  sleep 15
done
echo "Final status: $STATUS"
[[ "$STATUS" == "Failed" ]] && echo "$RESULT" | jq '.failureReason'
```

### Example 5: Change command (operation / model selection) only

```bash
# Read-modify-write just the content part, then resend ALL parts via build_and_update.
jq '.command.operation = "run"
    | .command.arguments.select = "gold"
    | .command.arguments.threads = 8' dbt-content.json > dbt-content.tmp && mv dbt-content.tmp dbt-content.json
build_and_update   # from Example 3 — never send the content part alone
```

### Example 6: Cross-database source model (read a Lakehouse from a Warehouse gold model)

`models/sources.yml`:

```yaml
version: 2
sources:
  - name: silver
    database: SilverLake     # different item in the same workspace SQL scope
    schema: dbo
    tables:
      - name: salesorderheader
```

`models/gold/dim_orderdate.sql` (note the `CAST(... AS VARCHAR)` to dodge the nvarchar limit):

```sql
{{ config(materialized='table') }}
SELECT DISTINCT
    (YEAR(OrderDate)*10000 + MONTH(OrderDate)*100 + DAY(OrderDate)) AS DateKey,
    CAST(OrderDate AS DATE)                          AS DateValue,
    YEAR(OrderDate)                                  AS [Year],
    CAST(DATENAME(MONTH, OrderDate) AS VARCHAR(20))  AS MonthName
FROM {{ source('silver', 'salesorderheader') }}
WHERE OrderDate IS NOT NULL
```

### Example 7: Delete a dbt Job

```bash
az rest --method delete --resource "$RESOURCE" \
  --url "$API/workspaces/$WS_ID/items/$JOB_ID"
```
