<!-- Mode reference for the `spark-cli` skill. Loaded on demand from `skills/spark-cli/SKILL.md` when the request matches the `mlv` mode. -->

# MLV Operations — CLI Skill

## Terminology Mapping

Fabric has **three** materialized view concepts. Disambiguate by context:

| User context | User says | Actually means | Route to |
|-------------|-----------|----------------|----------|
| Spark / Lakehouse | "materialized view" | **Materialized Lake View (MLV)** | This skill (`the `mlv` mode`) |
| Spark / Lakehouse | "materialized lake view" | MLV | This skill |
| Spark / Lakehouse | "spark materialized view" | MLV | This skill |
| Spark / Lakehouse | "MV" or "MLV" | MLV | This skill |
| Spark / Lakehouse | "CREATE MATERIALIZED LAKE VIEW" | MLV DDL (authoring) | `the `authoring` mode` |
| Spark / Lakehouse | "schedule my materialized view" | MLV scheduling | This skill |
| Spark / Lakehouse | "refresh my views" | MLV on-demand refresh | This skill |
| **KQL / Eventhouse** | "materialized view" | **KQL Materialized View** | `eventhouse-cli` |
| **SQL DW / Warehouse** | "materialized view" | **Not supported in Fabric** | Explain unsupported |

**Disambiguation rule**: If the user mentions lakehouse, notebook, Spark, Delta, or MLV → it's a **Materialized Lake View** (this skill). If they mention KQL, Eventhouse, or Kusto → it's a KQL Materialized View (different skill). If they mention Warehouse or SQL DW → explain it's not supported.

**Default**: If context is unclear (no mention of lakehouse, Spark, KQL, or Warehouse), ask the user: "Are you working with a Lakehouse (Materialized Lake View) or an Eventhouse (KQL Materialized View)?" before proceeding.

**Interactive recurring refresh (no API or CI/CD)**: Direct users to **Lakehouse → Materialized lake views → Manage → Schedules**. Do not substitute notebook, pipeline, or generic **Refresh → Schedule refresh** navigation.

Manage MLV refresh scheduling, execution definitions, and monitoring using Fabric REST APIs. This skill provides **public API coverage (Preview)** for scheduling, subset refresh configuration, and monitoring operations, enabling automation of MLV refresh workflows.

## What This Skill Can Do

### ✅ Fully Supported (14 REST APIs)

1. **Schedule Management** (per lakehouse — refreshes entire MLV lineage by default)
   - Create refresh schedules (Cron interval, Daily, Weekly, Monthly)
   - List schedules for a lakehouse
   - Get schedule details by ID
   - Update existing schedules (change frequency, enabled state)
   - Delete schedules
   - Attach an `executionData.mlvExecutionDefinitionId` to refresh a subset of the lineage

2. **Job Execution**
   - Trigger on-demand refresh (immediate execution)
   - List job run history with filtering
   - Get job status and progress
   - Cancel running jobs
   - Attach an `executionData.mlvExecutionDefinitionId` to refresh a subset of the lineage on demand

3. **MLV Execution Definitions**
   - Create reusable execution definitions for selected MLVs, selected upstream lakehouses, refresh mode, and Spark environment
   - List execution definitions
   - Get execution definition details
   - Patch execution definitions (partial update; omitted fields retain existing values)
   - Delete execution definitions; linked schedules are removed by the API

4. **Safety & UX**
   - Human-in-the-loop confirmations before creating schedules or triggering refreshes
   - Step-by-step planning for complex multi-MLV operations
   - Iterative error handling with helpful suggestions
   - Preview schedule impact before execution

### ❌ Not Supported through REST APIs

- **REST MLV Discovery**: `GET /materializedLakeViews` returns 404; use Spark SQL discovery instead
- **Visual Lineage Inspection**: Cannot fetch the portal dependency graph directly
- **Data Quality Metrics**: Cannot retrieve DQ metrics (API returns 404)
- **Schema Verification**: Cannot check if schemas are enabled (property missing)

**Discovery fallback**: Resolve the lakehouse, then run
`SHOW MATERIALIZED LAKE VIEWS IN <schema>` through a Lakehouse Livy session
(`consumption` mode) or Fabric notebook (`authoring` mode). Ask the user for MLV
names only when no Spark execution surface is available. Then encode the
selected MLV names and upstream lakehouses in an MLV execution definition.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| RULES — Read these first, follow them always | [SKILL.md § Must](#must) | **MUST read** — 6 rules for this skill |
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Job Scheduling | [COMMON-CLI.md § Job Scheduling](../../../common/COMMON-CLI.md#job-scheduling) | URL is `/jobs/{jobType}/schedules`; `endDateTime` required |
| Job Execution | [COMMON-CLI.md § Job Execution](../../../common/COMMON-CLI.md#job-execution) ||
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** or `az rest` fails |
| Pagination Pattern | [COMMON-CLI.md § Pagination Pattern](../../../common/COMMON-CLI.md#pagination-pattern) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference: `az rest` Template | [COMMON-CLI.md § Quick Reference: az rest Template](../../../common/COMMON-CLI.md#quick-reference-az-rest-template) ||
| MLV Public API Reference | [MS Learn: Manage Fabric materialized lake views with public APIs](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/materialized-lake-views-public-api) | Official documentation for schedules, on-demand refresh, job instances, and MLV execution definitions |

> **Eval mode**: When the user prompt contains "I pre-approve" or "proceed without confirmation",
> skip the human-in-the-loop gate and execute directly. This allows automated testing.

## Must

### 1. Human-in-the-loop confirmations

**Before executing any operation, show a preview and ask for confirmation:**

- **Creating schedules**: Show schedule type, interval/times, lakehouse ID, start/end time, and full-lineage or execution-definition scope
- **Creating execution definitions**: Show selected MLVs, selected upstream lakehouses, refresh mode, and Spark environment
- **Triggering refreshes**: Show lakehouse ID and whether this refreshes the full lineage or a named execution definition subset
- **Deleting schedules**: Show schedule ID and confirm deletion
- **Deleting execution definitions**: Show definition ID and warn that linked schedules are also removed

**Confirmation options**:
- `Allow` — Execute this single operation
- `Decline` — Skip this operation
- `Allow in this thread` — Auto-allow all operations in current conversation

**Example**:
```
I'm about to create a refresh schedule:

  Lakehouse ID: abc-123-def
  Type: Daily
  Time: 02:00 UTC
  Start: 2026-06-20
  End: 2027-06-20
  Scope: Full MLV lineage (default)

Proceed? [Allow / Decline / Allow in this thread]
```

### 2. Use REST APIs exactly as documented

**Base URL**: `https://api.fabric.microsoft.com/v1`

**Deterministic PowerShell execution:**
- Workspace list objects use `displayName`, not `name`. List once, filter `displayName` by exact equality, and require exactly one match instead of retrying alternate fields or filters.
- For every non-empty JSON body, serialize once, write it with `[IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))`, then pass `--headers "Content-Type=application/json"` and `--body "@$path"` to `az rest`. Do not pass inline JSON or a JSON variable on Windows.
- Submit each mutation once. Treat a 4xx response with `isRetriable: false` as final: report it and do not retry the POST with another encoding.

**IMPORTANT**: Schedule, on-demand trigger, execution-definition, and history-list endpoints are **workspace + lakehouse scoped**. An on-demand trigger returns an **item-scoped** `Location` URL for status polling and cancellation. A schedule or on-demand run refreshes the **entire MLV lineage by default**. To refresh selected MLVs or selected upstream lakehouses, create an MLV execution definition and pass its `mlvExecutionDefinitionId` in `executionData`.

**Schedule endpoints:**
- `POST   /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules` — Create schedule
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules` — List schedules
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Get schedule
- `PATCH  /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Update schedule
- `DELETE /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Delete schedule

**Job instance endpoints:**
- `POST   /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances` — Trigger on-demand refresh (optional `executionData`; returns 202 + Location header with job ID)
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances` — List job history
- `GET    /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}` — Get job status from the trigger `Location`
- `POST   /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}/cancel` — Cancel the running job

**MLV execution definition endpoints:**
- `POST   /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions` — Create selected-lineage execution definition
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions` — List execution definitions
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions/{mlvExecutionDefinitionId}` — Get execution definition
- `PATCH  /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions/{mlvExecutionDefinitionId}` — Partially update execution definition
- `DELETE /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions/{mlvExecutionDefinitionId}` — Delete execution definition and any linked schedules

**Job type mismatch trap**: Job history can expose scheduled MLV runs as `jobType: "MaterializedLakeViews"`, but the public job scheduler path uses `refreshMaterializedLakeViews`. Do **not** copy the history value into `POST /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances?jobType=MaterializedLakeViews`; that item-level call returns `InvalidJobType`.

**See**: [MS Learn: MLV Background Jobs](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/background-jobs/create-refresh-materialized-lake-views-schedule)

### 3. Authentication

All scheduling operations (create/update/delete, trigger, status, cancel) support both **User identity** (`az login`) and **Service Principal / Managed Identity**. Requires **Workspace Contributor or Admin role**.

### 4. Lakehouse schedule limits and execution-definition scopes

The [Preview REST scheduler](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/background-jobs/create-refresh-materialized-lake-views-schedule#limitations) supports refresh schedules at lakehouse scope. A lakehouse can have at most **20 schedules**, and an MLV lineage can have only **one active refresh schedule**. If the user asks for a subset schedule, create an **MLV execution definition** with selected MLVs/upstream lakehouses and pass its `mlvExecutionDefinitionId` in schedule or on-demand `executionData`. Execution definitions scope a refresh; they don't bypass scheduler limits.

### 5. MLV discovery through Spark SQL

`GET /materializedLakeViews` returns 404, but that REST limitation does not make
discovery impossible. Resolve the lakehouse and run:

```sql
SHOW MATERIALIZED LAKE VIEWS IN <schema>;
```

Execute it through a Lakehouse Livy session (`consumption` mode) or notebook
cell (`authoring` mode). See
[Materialized Lake View Patterns — SQL management commands](authoring/resources/materialized-lake-view-patterns.md#sql-management-commands).
Ask the user for MLV names only when a Spark session is unavailable.

### 6. Run History diagnostic workflow

When a user asks "why did my refresh fail?" or "show me run history", follow this sequence:

1. **List recent runs**: `GET /instances` — returns job instances with status, start/end times
2. **Show run summary**: Display table with run ID, status, start/end time, duration
3. **Select failed run**: If multiple, ask user which one to investigate
4. **Read error code**: Extract `failureReason.errorCode` and `failureReason.message` from the failed instance
5. **Suggest next steps**: Based on error code:
   - `MLV_SPARK_SESSION_REQUEST_SUBMISSION_FAILED` → Check capacity availability, Spark pool config
   - `MLV_SELECTED_NOT_FOUND` → MLV table was deleted or renamed, verify it exists
   - Other Spark errors → Route to `the `operations` mode` for OOM, skew, shuffle spill diagnosis
6. **Per-view details**: The API returns lineage-level status only. Per-view status (which individual MLVs failed) is available in the UI Recent runs page — direct the user there for view-level breakdown

**Run statuses** (from API): `NotStarted`, `InProgress`, `Completed`, `Failed`, `Cancelled`, `Deduped`

> **Note**: Run history retention may be limited. If older runs are missing, check the Recent runs page in the Lakehouse UI.

### Successful run but Full instead of Incremental

A completed lineage job is not evidence of per-MLV incremental execution.
For "why Full?" or "did the hint work?", read the
[IR readiness resource](authoring/resources/mlv-incremental-refresh-patterns.md)
and distinguish the following before recommending changes:

- **Creation/replacement:** executing CREATE or CREATE OR REPLACE performs Full,
  regardless of a hint. This is expected materialization, not a hint failure.
  Diagnose a subsequent refresh of the existing MLV; do not recreate it again.
- **Configuration:** verify Optimal rather than Full mode, Spark SQL rather
  than PySpark decorators, Delta sources, and CDF on every direct dependency.
- **Changes:** inserts can qualify without a hint; updates/deletes need a
  compatible REFRESH_HINT identifying output rows. Source schema changes
  cause Full **even with a hint**. No new Delta commits can mean No refresh.
- **Query/efficiency:** check supported constructs, aggregate partition/grouping
  requirements, the documented LEFT OUTER/SEMI JOIN right-side caveat, and
  engine cost-based Full fallback. A hint is not a guarantee of IR.
- **Evidence:** use per-view Recent runs details in the Lakehouse UI when the
  API exposes only lineage-level completion. Report strategy as unobserved
  if no per-view evidence is available; do not infer it from duration or status.

Route definition/hint changes to authoring and follow its key-selection,
optional-validation, and mandatory user-review workflow. Do not silently add
a hint, choose a key, or change the user's business query while diagnosing.

## Prefer

- **Daily/Weekly types** for precise time-of-day scheduling (e.g., "2 AM daily")
- **Cron type with interval** only for sub-daily frequencies (e.g., "every 60 minutes")
- **Step-by-step planning** — clarify intent, propose schedule, show preview, execute on approval
- **Iterative error handling** — on failure, explain what went wrong and suggest actionable fixes
- **Explicit timezone** in every schedule (`localTimeZoneId`)
- **Cross-lakehouse scheduling from extended lineage** — when MLVs span multiple lakehouses, schedule from the downstream lakehouse's lineage view. Extended lineage refreshes upstream dependencies automatically in dependency order. Prefer this over creating separate schedules on each lakehouse individually.

## Avoid

- **Per-table scheduling claims without an execution definition** — full-lineage is the default; selected subsets require a saved execution definition
- **Cron string expressions** (e.g., `0 2 * * *`) — the API uses structured types, not cron strings
- **Assuming JSON response from on-demand refresh** — returns 202 with job ID in Location header only
- **Silent failures** — always explain errors
- **Scheduling from notebooks or pipelines** — recurring MLV refresh belongs to Lakehouse schedules. SQL `REFRESH ... FULL` is for one-time manual troubleshooting only.

## Schedule Payload Structure

### Create Schedule (POST /schedules)

**Endpoint**: `POST /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules`

```json
{
  "enabled": true,
  "configuration": {
    "type": "Cron",
    "interval": 60,
    "startDateTime": "2026-06-20T00:00:00",
    "endDateTime": "2027-06-20T23:59:59",
    "localTimeZoneId": "UTC"
  }
}
```

**Subset lineage schedule**: include `executionData` when the user wants to refresh only the MLVs/upstream lakehouses captured in an execution definition:
```json
{
  "enabled": true,
  "configuration": {
    "type": "Cron",
    "interval": 60,
    "startDateTime": "2026-06-20T00:00:00",
    "endDateTime": "2027-06-20T23:59:59",
    "localTimeZoneId": "UTC"
  },
  "executionData": {
    "mlvExecutionDefinitionId": "<mlvExecutionDefinitionId>"
  }
}
```

**Key fields:**
- `enabled`: `true` to enable schedule on creation
- `type`: One of `"Cron"`, `"Daily"`, `"Weekly"`, `"Monthly"`
- `interval`: (Cron only) Refresh interval in minutes (e.g., `60` = hourly, `120` = every 2 hours)
- `times`: (Daily/Weekly/Monthly) Array of times in `"HH:MM"` format, e.g., `["02:00"]`
- `weekdays`: (Weekly only) e.g., `["Monday", "Wednesday", "Friday"]` — PascalCase day names
- `recurrence`: (Monthly only) Recurrence interval, e.g., `1` (every month)
- `occurrence`: (Monthly only) e.g., `{"occurrenceType": "DayOfMonth", "dayOfMonth": 1}`
- `localTimeZoneId`: Windows time zone names — `"UTC"`, `"Central Standard Time"`, `"India Standard Time"`, etc.
- `startDateTime`: When schedule becomes active (ISO 8601 local time; `localTimeZoneId` supplies the time zone)
- `endDateTime`: **REQUIRED** — When schedule expires
- `executionData.mlvExecutionDefinitionId`: Optional; refreshes only the selected lineage captured in that execution definition

**Daily example** (preferred for "2 AM every day"):
```json
{ "enabled": true, "configuration": { "type": "Daily", "times": ["02:00"], "startDateTime": "2026-06-20T00:00:00", "endDateTime": "2027-06-20T23:59:59", "localTimeZoneId": "UTC" } }
```

**Weekly example** (weekdays at 6 AM):
```json
{ "enabled": true, "configuration": { "type": "Weekly", "times": ["06:00"], "weekdays": ["Monday", "Friday"], "startDateTime": "2026-06-20T00:00:00", "endDateTime": "2027-06-20T23:59:59", "localTimeZoneId": "UTC" } }
```

**Monthly example** (1st of each month at midnight):
```json
{ "enabled": true, "configuration": { "type": "Monthly", "recurrence": 1, "occurrence": {"occurrenceType": "DayOfMonth", "dayOfMonth": 1}, "times": ["00:00"], "startDateTime": "2026-06-20T00:00:00", "endDateTime": "2027-06-20T23:59:59", "localTimeZoneId": "UTC" } }
```

> **WARNING**: Do NOT use `"days": [1, 15]` for Monthly — this returns `400 InvalidConfiguration`. Use `recurrence` + `occurrence` as shown above.

### Update Schedule (PATCH /schedules/{id})

**Endpoint**: `PATCH /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}`

```json
{
  "enabled": true,
  "configuration": {
    "type": "Cron",
    "interval": 120,
    "startDateTime": "2026-06-20T00:00:00",
    "endDateTime": "2027-06-20T23:59:59",
    "localTimeZoneId": "UTC"
  }
}
```

**Note**: The update API requires both `enabled` and a **complete** `configuration` (full replacement, not partial patch). Always send all fields.

## MLV Execution Definitions

Use execution definitions when the user wants to refresh **specific MLVs**, include **selected upstream lakehouses**, pin a **Spark environment**, or choose a **refresh mode** independently from the default full-lineage refresh.

### Create MLV Execution Definition

**Endpoint**: `POST /workspaces/{workspaceId}/lakehouses/{lakehouseId}/mlvexecutiondefinitions`

```json
{
  "displayName": "Gold Chain - Sales",
  "description": "Nightly refresh for selected gold-layer MLVs",
  "settings": {
    "environment": {
      "referenceType": "ById",
      "itemId": "<environmentId>",
      "workspaceId": "<environmentWorkspaceId>"
    },
    "refreshMode": "Optimal"
  },
  "currentLakehouseExecutionContext": {
    "mode": "Selected",
    "selectedMlvs": [
      "dbo.gold_sales_summary",
      "dbo.gold_sales_daily"
    ]
  },
  "extendedLineageExecutionContext": {
    "mode": "All"
  }
}
```

**Execution context modes:**
- `currentLakehouseExecutionContext.mode`: `"All"` or `"Selected"`; when `"Selected"`, provide `selectedMlvs` as fully qualified MLV names.
- `extendedLineageExecutionContext.mode`: `"All"` or `"Selected"`; when `"Selected"`, provide `selectedLakehouses` objects with `referenceType`, `itemId`, and `workspaceId`.
- `settings.refreshMode`: `"Optimal"` or `"Full"`.
- `settings.environment`: Optional Spark environment reference by ID.

**Update semantics**: `PATCH /mlvexecutiondefinitions/{id}` is a partial update. Only provided fields change; omitted fields retain their existing values. This differs from schedule PATCH, which requires `enabled` and a complete `configuration`.

**Delete semantics**: `DELETE /mlvexecutiondefinitions/{id}` also removes schedules linked to that execution definition. Warn before deleting.

## Trigger On-Demand Refresh (POST /instances)

**Endpoint**: `POST /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances`

**Request body**: None for full-lineage refresh. Refreshes the entire MLV lineage in dependency order.

**Subset refresh body**:
```json
{
  "executionData": {
    "mlvExecutionDefinitionId": "<mlvExecutionDefinitionId>"
  }
}
```

**Do not use job history as the trigger contract**: recent runs may list `jobType: "MaterializedLakeViews"`, but that value is only a history/status label. For on-demand refresh, always call this lakehouse-scoped endpoint. Reusing the history label with the generic item job API (`POST /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances?jobType=MaterializedLakeViews`) is a known `InvalidJobType` dead end.

The trigger response returns an item-scoped `Location` URL (`/items/{lakehouseId}/jobs/instances/{jobInstanceId}`). Use it as-is for polling and cancellation. The lakehouse-scoped GET (`/lakehouses/{lakehouseId}/jobs/instances/{jobInstanceId}`) is documented as an alternative and returns the same instance, but the service does not return that shape in the `Location` header today.

**Response**: `202 Accepted` — job instance ID is in the `Location` response header:
```
Location: https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}
Retry-After: 60
```

**Poll for status** using the URL from the `Location` header (or its lakehouse-scoped equivalent):
```
GET /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}
```

**Job instance status values:**

| Status | Meaning |
|--------|---------|
| `NotStarted` | Job is queued but hasn't begun |
| `InProgress` | Job is actively running |
| `Completed` | Job finished successfully |
| `Failed` | Job failed (check `failureReason`) |
| `Cancelled` | Job was cancelled by user |
| `Deduped` | Skipped because another refresh was already in progress |

**Note**: Job instances returned by public `GET /lakehouses/{id}/jobs/refreshMaterializedLakeViews/instances` use `jobType: "RefreshMaterializedLakeViews"` per MS Learn. Some item-level history surfaces have returned `jobType: "MaterializedLakeViews"` in live testing; filter on either value when diagnosing legacy history, but never use `MaterializedLakeViews` as an on-demand trigger `jobType`.

**Status display limitation**: job instance status reflects Monitor hub status and can differ from the MLV run-history UI. For example, an MLV run-history **Skipped** status can appear as **Cancelled/Canceled** in Monitor hub APIs.

**Schedule settings** (additional options via UI or API):
- **Optimal Refresh** (default: On) — Fabric picks incremental or full refresh per MLV automatically
- **Extended lineage** — refreshes chains across multiple lakehouses in dependency order from a single schedule

## Example Workflows

### Workflow 1: Schedule Nightly Refresh

**User prompt**: "Schedule `sales_monthly` MLV in `CustomerVoice` lakehouse to refresh at 2 AM daily"

**Agent steps**:
1. Find workspace ID for "CustomerVoice" via `GET /workspaces` + JMESPath
2. Find lakehouse ID via `GET /workspaces/{id}/lakehouses` + JMESPath
3. Clarify scope: "Do you want the default full-lineage schedule, or should I create an MLV execution definition for only `sales_monthly`?"
4. If the user chooses subset scope, create an execution definition with `currentLakehouseExecutionContext.mode = "Selected"` and `selectedMlvs = ["dbo.sales_monthly"]` (or the user's actual fully qualified MLV name), then include its `mlvExecutionDefinitionId` in schedule `executionData`.
5. Show preview:
   ```
   Creating schedule:
     Lakehouse: CustomerVoice (ID: xyz-456-ghi)
     Scope: Full lineage OR execution definition <id>
     Type: Daily, Time: 02:00 UTC
     Start: Now
     End: 1 year from now
   
   Proceed? [Allow / Decline]
   ```
6. On "Allow": POST schedule payload, return schedule ID
7. Report: "Schedule created (ID: sched-789). Scope: full lineage OR execution definition <id>."

### Workflow 2: Trigger Immediate Refresh

**User prompt**: "Refresh `inventory_daily` MLV now in lakehouse `xyz-456-ghi`"

**Agent steps**:
1. Confirm lakehouse ID is valid (GET /lakehouses/{id})
2. Clarify scope and show preview:
   ```
   Triggering on-demand refresh:
     Lakehouse ID: xyz-456-ghi
     Scope: Full lineage OR execution definition <id>
   
   Do you want the default full-lineage refresh, or only `inventory_daily` through an execution definition? Proceed? [Allow / Decline]
   ```
3. If the user chooses a subset, create or reuse an execution definition for `inventory_daily` and send its ID in `executionData`; otherwise POST `/instances` with no body. Capture the job ID from the Location header.
4. Poll using the item-scoped URL returned in the `Location` header, or its documented lakehouse-scoped equivalent `GET /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/instances/{jobId}`, and show progress.
5. Report: "✅ Refresh completed in 2m 34s" or "❌ Refresh failed: [error message]"

### Workflow 3: User Asks for Per-MLV Scheduling (Explain Limitation)

**User prompt**: "Schedule `bronze_sales`, `silver_sales`, `gold_sales` to refresh at 2 AM, 3 AM, 4 AM respectively"

**Agent steps**:
1. Explain limitation:
   ```
   These views are a dependency chain, so schedule them as one lineage refresh
   rather than at separate times. Lakehouse scheduling refreshes dependencies in
   the required order.

   Options:
     1. Single Daily schedule at 2 AM (refreshes all 3 in order)
     2. If the MLVs are independent, create separate execution definitions and
        schedules within the lakehouse's 20-schedule limit
     3. If they're in separate lakehouses, create one schedule per lakehouse
   
   Which would you prefer?
   ```
2. If user picks option 1: Create one Daily schedule with `"times": ["02:00"]`
3. If user picks option 2: Confirm the MLVs are independent, then create the execution definitions and schedules
4. If user picks option 3: Confirm lakehouse IDs for each, then create schedules

### Workflow 4: List and Delete Schedules

**User prompt**: "Show my schedule and delete it if it's outdated"

**Agent steps**:
1. Ask user for workspace and lakehouse (cannot list schedules globally)
2. `GET /workspaces/{wsId}/lakehouses/{lhId}/jobs/refreshMaterializedLakeViews/schedules`
3. Parse response (usually 1 schedule per lineage), show details:
   ```
   Active schedule on lakehouse 'CustomerVoice':
     - ID: sched-111 (created 2025-10-15, type: Daily, time: 02:00)
   
   Delete this schedule? [Allow / Decline]
   ```
4. On "Allow": DELETE /schedules/{id}, confirm
5. Report: "✅ Schedule deleted"

## Common Errors & Fixes

### Error: `400 Bad Request` — Invalid Interval

**Message**: `"The interval '0' is invalid. Interval must be between 1 and 5270400 (10 years in minutes)."`

**Fix**:
```
Interval must be a valid number of minutes between 1 and 5,270,400 (10 years).

Common intervals:
  60 = hourly
  1440 = daily (24 hours)
  10080 = weekly (7 days)

Would you like me to adjust the interval to a valid value?
```

### Error: `409 Conflict` — Schedule Already Exists

**Message**: `"A schedule already exists for this lakehouse"`

**Fix**:
```
A schedule is already active for this lakehouse. Options:
  1. Update existing schedule (change interval/time)
  2. Delete and recreate (replaces schedule)
  3. Leave as-is (no change)

Which would you prefer?
```

### Error: `404 Not Found` — Lakehouse ID Invalid

**Message**: `"Lakehouse 'wrong-id-123' not found in workspace 'abc-456'"`

**Fix**:
```
The lakehouse ID you provided doesn't exist. Let me list available lakehouses:

[Call GET /workspaces/{id}/lakehouses, show table]

Which lakehouse should I use?
```

### Error: `403 Forbidden` — Permission Denied

**Message**: `"User does not have permission to create schedules in this workspace"`

**Fix**:
```
You need Workspace Contributor or Admin role to create schedules.

Current permissions: Viewer (read-only)
Required: Contributor or Admin

Contact your workspace admin to request elevated permissions.
```

## Tips for Users

### 1. Find Your Lakehouse ID

**Option A: Via REST API**
```bash
az rest --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/lakehouses" \
  --method GET
```

Extract `id` from the response for your lakehouse.

**Option B: Via Fabric UI**
1. Open lakehouse in Fabric portal
2. Click Settings (gear icon)
3. Copy "Lakehouse ID" from properties

### 2. Common Schedule Configurations

| Need | Type | Key field |
|------|------|-----------|
| Every hour | Cron | `"interval": 60` |
| Daily at 2 AM | Daily | `"times": ["02:00"]` |
| Weekdays at 6 AM | Weekly | `"times": ["06:00"], "weekdays": ["Monday","Friday"]` |
| 1st of each month | Monthly | `"recurrence": 1, "occurrence": {"occurrenceType": "DayOfMonth", "dayOfMonth": 1}` |

### 3. Monitor Job History

List recent refresh jobs (authenticate per [COMMON-CLI.md § Quick Reference: az rest Template](../../../common/COMMON-CLI.md#quick-reference-az-rest-template)):
```bash
# See COMMON-CLI.md for authentication setup
az rest --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances" \
  --method GET
```

> **Note**: The list instances API does not support OData query parameters (`$top`, `$orderby`, `$filter`). Sort and filter results client-side after retrieval. Use `continuationToken` for pagination.

### 4. Time Zone Considerations

**Default**: Schedules use UTC unless specified.

**Best practice**: Always specify timezone explicitly to avoid confusion:
```json
{
  "configuration": {
    "localTimeZoneId": "Central Standard Time"
  }
}
```

Valid time zones: Windows time zone names (e.g., `"Central Standard Time"`, `"Pacific Standard Time"`, `"India Standard Time"`). Use the [Windows Default Time Zones](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-time-zones) registry.

## Related Skills

- **the `authoring` mode**: Create MLVs in Fabric Notebooks (authoring side)

## Limitations & Future Roadmap

### Current Limitations (as of 2026-06-18)

| Feature | Status | Workaround |
|---------|--------|------------|
| List MLVs through REST | ❌ API returns 404 | Run `SHOW MATERIALIZED LAKE VIEWS IN <schema>` through Livy or a notebook; ask for names only if Spark execution is unavailable |
| Refresh selected MLVs / subset lineage | ✅ Use MLV execution definitions | Create `/mlvexecutiondefinitions`, then pass `executionData.mlvExecutionDefinitionId` |
| Get visual lineage graph | ❌ No public graph API | Use Fabric Lakehouse UI |
| Check data quality metrics | ❌ API returns 404 | Use Fabric Lakehouse UI |
| Verify schema support | ❌ Property missing | Assume schemas enabled if MLVs work |

### What Works Today (public MLV API coverage (Preview))

- ✅ Create/list/update/delete schedules (5 APIs)
- ✅ Trigger/monitor/cancel refresh jobs (4 APIs)
- ✅ Create/list/get/update/delete MLV execution definitions (5 APIs)
- ✅ Full-lineage or selected-lineage refresh via `executionData.mlvExecutionDefinitionId`
- ✅ Full automation of refresh workflows
- ✅ Human-in-the-loop safety confirmations
- ✅ Iterative error handling

### Planned (When REST APIs Ship)

- **REST MLV Discovery**: Auto-list MLVs without a Spark session
- **Visual Lineage Tracing**: Show dependency graphs
- **Data Quality**: Fetch DQ metrics programmatically
- **Schema Verification**: Check `enableSchemas` property

**Agent design is forward-compatible**: When APIs become available, add discovery capabilities without changing scheduling logic.

## Conclusion

This skill provides **validated automation** for MLV refresh scheduling, execution definitions, and monitoring using public REST APIs. While MLV discovery and visual lineage inspection still require UI workarounds today, scheduling, selected-lineage execution definitions, and job execution work as documented.

**Design philosophy** (inspired by Databricks Data Engineering Agent):
- Human-in-the-loop confirmations for safety
- Step-by-step planning for complex tasks
- Iterative error handling with helpful suggestions
- Transparent about limitations (no speculative workarounds)

**Next steps**: Use this skill to automate MLV refresh workflows. When discovery APIs ship, we'll extend the skill to eliminate manual lakehouse ID + table name input.
