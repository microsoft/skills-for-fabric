---
name: mlv-operations-cli
description: >
  Manage Microsoft Fabric Materialized Lake View (MLV) refresh schedules and job execution
  via REST APIs. Create, update, and delete refresh schedules (interval-based: hourly, daily, weekly).
  Trigger on-demand refreshes, monitor job status, and cancel running jobs. Uses human-in-the-loop
  confirmations for safety. Materialized Lake Views are also known as Spark Materialized Views,
  MLVs, or lakehouse materialized views in Fabric documentation.
  Note: MLV discovery (list MLVs, lineage, data quality) requires UI as REST APIs are not yet available.
  Triggers: "schedule MLV refresh", "manage MLV", "MLV refresh schedule",
  "schedule materialized lake view", "schedule materialized view",
  "automate MLV refresh", "trigger MLV refresh", "monitor MLV refresh",
  "MLV job status", "cancel MLV refresh", "refresh schedule",
  "MLV automation", "manage materialized lake view", "manage materialized view",
  "materialized view refresh", "spark materialized view schedule",
  "lakehouse materialized view", "refresh my materialized views"
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the lakehouse details (including its ID) from workspace ID and lakehouse name: list all lakehouses in that workspace and, then, use JMESPath filtering
> 3. **MLV Discovery Gap**: REST APIs for listing MLVs in a lakehouse do not exist yet (GET /materializedLakeViews returns 404). For schedule CRUD/trigger/status, only workspace ID and lakehouse ID are needed (scheduling operates on the full lakehouse lineage). MLV table names are only needed if the user asks about specific view definitions.

# MLV Operations — CLI Skill

## Terminology Mapping

Fabric has **three** materialized view concepts. Disambiguate by context:

| User context | User says | Actually means | Route to |
|-------------|-----------|----------------|----------|
| Spark / Lakehouse | "materialized view" | **Materialized Lake View (MLV)** | This skill (`mlv-operations-cli`) |
| Spark / Lakehouse | "materialized lake view" | MLV | This skill |
| Spark / Lakehouse | "spark materialized view" | MLV | This skill |
| Spark / Lakehouse | "MV" or "MLV" | MLV | This skill |
| Spark / Lakehouse | "CREATE MATERIALIZED LAKE VIEW" | MLV DDL (authoring) | `spark-authoring-cli` |
| Spark / Lakehouse | "schedule my materialized view" | MLV scheduling | This skill |
| Spark / Lakehouse | "refresh my views" | MLV on-demand refresh | This skill |
| **KQL / Eventhouse** | "materialized view" | **KQL Materialized View** | `eventhouse-authoring-cli` |
| **SQL DW / Warehouse** | "materialized view" | **Not supported in Fabric** | Explain unsupported |

**Disambiguation rule**: If the user mentions lakehouse, notebook, Spark, Delta, or MLV → it's a **Materialized Lake View** (this skill). If they mention KQL, Eventhouse, or Kusto → it's a KQL Materialized View (different skill). If they mention Warehouse or SQL DW → explain it's not supported.

**Default**: If context is unclear (no mention of lakehouse, Spark, KQL, or Warehouse), ask the user: "Are you working with a Lakehouse (Materialized Lake View) or an Eventhouse (KQL Materialized View)?" before proceeding.

Manage MLV refresh scheduling and monitoring using Fabric REST APIs. This skill provides **full scheduling API coverage (Preview)** for scheduling and monitoring operations, enabling full automation of MLV refresh workflows.

## What This Skill Can Do

### ✅ Fully Supported (9 REST APIs)

1. **Schedule Management** (per lakehouse — refreshes entire MLV lineage)
   - Create refresh schedules (Cron interval, Daily, Weekly, Monthly)
   - List schedules for a lakehouse
   - Get schedule details by ID
   - Update existing schedules (change frequency, enabled state)
   - Delete schedules

2. **Job Execution**
   - Trigger on-demand refresh (immediate execution)
   - List job run history with filtering
   - Get job status and progress
   - Cancel running jobs

3. **Safety & UX**
   - Human-in-the-loop confirmations before creating schedules or triggering refreshes
   - Step-by-step planning for complex multi-MLV operations
   - Iterative error handling with helpful suggestions
   - Preview schedule impact before execution

### ❌ Not Supported (Requires UI — No REST APIs)

- **MLV Discovery**: Cannot list MLVs in a lakehouse (API returns 404)
- **Lineage Inspection**: Cannot fetch dependency graphs (API returns 404)
- **Data Quality Metrics**: Cannot retrieve DQ metrics (API returns 404)
- **Schema Verification**: Cannot check if schemas are enabled (property missing)

**Workaround**: User provides lakehouse ID and MLV table names explicitly. Use Fabric Lakehouse UI for discovery tasks.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| RULES — Read these first, follow them always | [SKILL.md § Must](#must) | **MUST read** — 6 rules for this skill |
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Job Scheduling | [COMMON-CLI.md § Job Scheduling](../../common/COMMON-CLI.md#job-scheduling) | URL is `/jobs/{jobType}/schedules`; `endDateTime` required |
| Job Execution | [COMMON-CLI.md § Job Execution](../../common/COMMON-CLI.md#job-execution) ||
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** or `az rest` fails |
| Pagination Pattern | [COMMON-CLI.md § Pagination Pattern](../../common/COMMON-CLI.md#pagination-pattern) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference: `az rest` Template | [COMMON-CLI.md § Quick Reference: az rest Template](../../common/COMMON-CLI.md#quick-reference-az-rest-template) ||
| MLV Refresh API Reference | [MS Learn: Refresh Materialized Lake View](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view) | Official documentation for refresh mechanics |

> **Eval mode**: When the user prompt contains "I pre-approve" or "proceed without confirmation",
> skip the human-in-the-loop gate and execute directly. This allows automated testing.

## Must

### 1. Human-in-the-loop confirmations

**Before executing any operation, show a preview and ask for confirmation:**

- **Creating schedules**: Show schedule type, interval/times, lakehouse ID, start/end time
- **Triggering refreshes**: Show lakehouse ID, confirm "this refreshes the entire MLV lineage"
- **Deleting schedules**: Show schedule ID and confirm deletion

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
  Scope: Entire MLV lineage

Proceed? [Allow / Decline / Allow in this thread]
```

### 2. Use REST APIs exactly as documented

**Base URL**: `https://api.fabric.microsoft.com/v1`

**IMPORTANT**: All endpoints are **workspace + lakehouse scoped**. A schedule refreshes the **entire MLV lineage** — you cannot schedule individual tables.

**Schedule endpoints:**
- `POST   /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules` — Create schedule
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules` — List schedules
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Get schedule
- `PATCH  /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Update schedule
- `DELETE /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/schedules/{id}` — Delete schedule

**Job instance endpoints:**
- `POST   /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances` — Trigger on-demand refresh (no body; returns 202 + Location header with job ID)
- `GET    /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances` — List job history
- `GET    /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}` — Get job status
- `POST   /workspaces/{workspaceId}/items/{lakehouseId}/jobs/instances/{jobInstanceId}/cancel` — Cancel running job

**See**: [MS Learn: MLV Background Jobs](https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/background-jobs/create-refresh-materialized-lake-views-schedule)

### 3. Authentication

All scheduling operations (create/update/delete, trigger, status, cancel) support both **User identity** (`az login`) and **Service Principal / Managed Identity**. Requires **Workspace Contributor or Admin role**.

### 4. One schedule per lineage

The API supports **one active refresh schedule per lakehouse lineage**. If the user asks for per-table scheduling, explain this limitation.

### 5. MLV Discovery — User must provide names

`GET /materializedLakeViews` returns 404. Ask user for lakehouse ID and table names upfront.

### 6. Run History diagnostic workflow

When a user asks "why did my refresh fail?" or "show me run history", follow this sequence:

1. **List recent runs**: `GET /instances` — returns job instances with status, start/end times
2. **Show run summary**: Display table with run ID, status, start/end time, duration
3. **Select failed run**: If multiple, ask user which one to investigate
4. **Read error code**: Extract `failureReason.errorCode` and `failureReason.message` from the failed instance
5. **Suggest next steps**: Based on error code:
   - `MLV_SPARK_SESSION_REQUEST_SUBMISSION_FAILED` → Check capacity availability, Spark pool config
   - `MLV_SELECTED_NOT_FOUND` → MLV table was deleted or renamed, verify it exists
   - Other Spark errors → Route to `spark-operations-cli` for OOM, skew, shuffle spill diagnosis
6. **Per-view details**: The API returns lineage-level status only. Per-view status (which individual MLVs failed) is available in the UI Recent runs page — direct the user there for view-level breakdown

**Run statuses** (from API): `NotStarted`, `InProgress`, `Completed`, `Failed`, `Cancelled`, `Deduped`

> **Note**: Run history retention may be limited. If older runs are missing, check the Recent runs page in the Lakehouse UI.

## Prefer

- **Daily/Weekly types** for precise time-of-day scheduling (e.g., "2 AM daily")
- **Cron type with interval** only for sub-daily frequencies (e.g., "every 60 minutes")
- **Step-by-step planning** — clarify intent, propose schedule, show preview, execute on approval
- **Iterative error handling** — on failure, explain what went wrong and suggest actionable fixes
- **Explicit timezone** in every schedule (`localTimeZoneId`)
- **Cross-lakehouse scheduling from extended lineage** — when MLVs span multiple lakehouses, schedule from the downstream lakehouse's lineage view. Extended lineage refreshes upstream dependencies automatically in dependency order. Prefer this over creating separate schedules on each lakehouse individually.

## Avoid

- **Per-table scheduling claims** — the API refreshes the entire lineage
- **Cron string expressions** (e.g., `0 2 * * *`) — the API uses structured types, not cron strings
- **Assuming JSON response from on-demand refresh** — returns 202 with job ID in Location header only
- **Silent failures** — always explain errors
- **Scheduling from notebooks** — route users here; SQL `REFRESH ... FULL` is for one-time manual use only

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

**Key fields:**
- `enabled`: `true` to enable schedule on creation
- `type`: One of `"Cron"`, `"Daily"`, `"Weekly"`, `"Monthly"`
- `interval`: (Cron only) Refresh interval in minutes (e.g., `60` = hourly, `120` = every 2 hours)
- `times`: (Daily/Weekly/Monthly) Array of times in `"HH:MM"` format, e.g., `["02:00"]`
- `weekdays`: (Weekly only) e.g., `["Monday", "Wednesday", "Friday"]` — PascalCase day names
- `recurrence`: (Monthly only) Recurrence interval, e.g., `1` (every month)
- `occurrence`: (Monthly only) e.g., `{"occurrenceType": "DayOfMonth", "dayOfMonth": 1}`
- `localTimeZoneId`: Windows time zone names — `"UTC"`, `"Central Standard Time"`, `"India Standard Time"`, etc.
- `startDateTime`: When schedule becomes active (ISO 8601 format, no Z suffix)
- `endDateTime`: **REQUIRED** — When schedule expires

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

## Trigger On-Demand Refresh (POST /instances)

**Endpoint**: `POST /workspaces/{workspaceId}/lakehouses/{lakehouseId}/jobs/refreshMaterializedLakeViews/instances`

**Request body**: None (empty POST). Refreshes the entire MLV lineage in dependency order.

**Response**: `202 Accepted` — job instance ID is in the `Location` response header:
```
Location: https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items/{lhId}/jobs/instances/{jobInstanceId}
Retry-After: 60
```

**Poll for status** using the URL from the `Location` header:
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

**Note**: Job instances returned by `GET /items/{id}/jobs/instances` use `jobType: "MaterializedLakeViews"` (live-tested) or `jobType: "RefreshMaterializedLakeViews"` (per MS Learn docs). Filter on either value when listing instances.

**Schedule settings** (additional options via UI or API):
- **Optimal Refresh** (default: On) — Fabric picks incremental or full refresh per MLV automatically
- **Extended lineage** — refreshes chains across multiple lakehouses in dependency order from a single schedule

## Example Workflows

### Workflow 1: Schedule Nightly Refresh

**User prompt**: "Schedule `sales_monthly` MLV in `CustomerVoice` lakehouse to refresh at 2 AM daily"

**Agent steps**:
1. Find workspace ID for "CustomerVoice" via `GET /workspaces` + JMESPath
2. Find lakehouse ID via `GET /workspaces/{id}/lakehouses` + JMESPath
3. Clarify scope: "Note: the schedule refreshes the **entire MLV lineage** in this lakehouse, not just `sales_monthly`."
4. Show preview:
   ```
   Creating schedule:
     Lakehouse: CustomerVoice (ID: xyz-456-ghi)
     Scope: Entire MLV lineage (all materialized lake views)
     Type: Daily, Time: 02:00 UTC
     Start: Now
     End: 1 year from now
   
   Proceed? [Allow / Decline]
   ```
5. On "Allow": POST schedule payload, return schedule ID
6. Report: "✅ Schedule created (ID: sched-789). Entire lineage will refresh daily at 2 AM UTC."

### Workflow 2: Trigger Immediate Refresh

**User prompt**: "Refresh `inventory_daily` MLV now in lakehouse `xyz-456-ghi`"

**Agent steps**:
1. Confirm lakehouse ID is valid (GET /lakehouses/{id})
2. Clarify scope and show preview:
   ```
   Triggering on-demand refresh:
     Lakehouse ID: xyz-456-ghi
     Scope: Entire MLV lineage (includes inventory_daily and all other MLVs)
   
   This refreshes ALL MLVs in dependency order. Proceed? [Allow / Decline]
   ```
3. On "Allow": POST /instances (no body), capture job ID from Location header
4. Poll GET /items/{id}/jobs/instances/{jobId}, show progress
5. Report: "✅ Refresh completed in 2m 34s" or "❌ Refresh failed: [error message]"

### Workflow 3: User Asks for Per-MLV Scheduling (Explain Limitation)

**User prompt**: "Schedule `bronze_sales`, `silver_sales`, `gold_sales` to refresh at 2 AM, 3 AM, 4 AM respectively"

**Agent steps**:
1. Explain limitation:
   ```
   I can't schedule individual MLVs on different times — the API supports
   one schedule per lakehouse lineage, and it refreshes ALL MLVs together
   in dependency order.
   
   Options:
     1. Single Daily schedule at 2 AM (refreshes all 3 in order)
     2. If they're in separate lakehouses, I can create one schedule per lakehouse
   
   Which would you prefer?
   ```
2. If user picks option 1: Create one Daily schedule with `"times": ["02:00"]`
3. If user picks option 2: Confirm lakehouse IDs for each, create schedules

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

List recent refresh jobs (authenticate per [COMMON-CLI.md § Quick Reference: az rest Template](../../common/COMMON-CLI.md#quick-reference-az-rest-template)):
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

- **spark-authoring-cli**: Create MLVs in Fabric Notebooks (authoring side)
- **check-updates**: Verify skill package is up-to-date (run once per session)

## Limitations & Future Roadmap

### Current Limitations (as of 2026-06-18)

| Feature | Status | Workaround |
|---------|--------|------------|
| List MLVs in lakehouse | ❌ API returns 404 | User provides table names manually |
| Get MLV lineage graph | ❌ API returns 404 | Use Fabric Lakehouse UI |
| Check data quality metrics | ❌ API returns 404 | Use Fabric Lakehouse UI |
| Verify schema support | ❌ Property missing | Assume schemas enabled if MLVs work |

### What Works Today (full scheduling API coverage (Preview))

- ✅ Create/list/update/delete schedules (5 APIs)
- ✅ Trigger/monitor/cancel refresh jobs (4 APIs)
- ✅ Full automation of refresh workflows
- ✅ Human-in-the-loop safety confirmations
- ✅ Iterative error handling

### Planned (When REST APIs Ship)

- **MLV Discovery**: Auto-list MLVs in a lakehouse
- **Lineage Tracing**: Show dependency graphs
- **Data Quality**: Fetch DQ metrics programmatically
- **Schema Verification**: Check `enableSchemas` property

**Agent design is forward-compatible**: When APIs become available, add discovery capabilities without changing scheduling logic.

## Conclusion

This skill provides **validated automation** for MLV refresh scheduling and monitoring using 100% REST API coverage. While MLV discovery requires UI workarounds today, scheduling and job execution work as documented.

**Design philosophy** (inspired by Databricks Data Engineering Agent):
- Human-in-the-loop confirmations for safety
- Step-by-step planning for complex tasks
- Iterative error handling with helpful suggestions
- Transparent about limitations (no speculative workarounds)

**Next steps**: Use this skill to automate MLV refresh workflows. When discovery APIs ship, we'll extend the skill to eliminate manual lakehouse ID + table name input.
