# Automated Diagnostic Workflow — Reference

Companion to the compact summary in [SKILL.md § Automated Diagnostic Workflow](../../SKILL.md#automated-diagnostic-workflow). This reference holds the verbose procedure, edge-case fallbacks, retention details, and report templates.

---

## Step 1 — Resolve & Discover (full)

```bash
# Resolve workspace — list all matches, disambiguate if needed
workspaceMatches=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces" \
  --query "value[?displayName=='<UserWorkspaceName>'].{id:id, displayName:displayName}" --output json)
matchCount=$(echo "$workspaceMatches" | jq length)
if [ "$matchCount" -eq 0 ]; then
  echo "ERROR: No workspace found with name '<UserWorkspaceName>'. Verify the name and retry."
  exit 1
elif [ "$matchCount" -gt 1 ]; then
  echo "Multiple workspaces match '<UserWorkspaceName>':"
  echo "$workspaceMatches" | jq -r '.[] | "  - \(.id)  \(.displayName)"'
  echo "Please specify the workspace ID directly."
  exit 1
fi
workspaceId=$(echo "$workspaceMatches" | jq -r '.[0].id')

# Resolve item (notebook, SJD, or lakehouse) — list all matches, disambiguate if needed
itemMatches=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items?type=Notebook" \
  --query "value[?displayName=='<UserItemName>'].{id:id, displayName:displayName}" --output json)
itemCount=$(echo "$itemMatches" | jq length)
if [ "$itemCount" -eq 0 ]; then
  echo "Item '<UserItemName>' not found as Notebook. Trying SparkJobDefinition, then Lakehouse..."
  # Retry with ?type=SparkJobDefinition, then ?type=Lakehouse
elif [ "$itemCount" -gt 1 ]; then
  echo "Multiple items match '<UserItemName>':"
  echo "$itemMatches" | jq -r '.[] | "  - \(.id)  \(.displayName)"'
  echo "Please specify the item ID directly."
  exit 1
fi
itemId=$(echo "$itemMatches" | jq -r '.[0].id')

# List recent Livy sessions (sorted newest first)
# Use the correct item-type path:
#   /notebooks/{itemId}/livySessions
#   /sparkJobDefinitions/{itemId}/livySessions
#   /lakehouses/{itemId}/livySessions
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/<itemTypePath>/$itemId/livySessions" \
  --output json
```

> **Disambiguation**: The resolve snippets above check match count before proceeding. If zero matches are found, an error is reported. If multiple workspaces or items share the same `displayName`, all matches are listed and the user is asked to specify the exact ID.

**Item-type API paths:**

| Item Type | Livy Sessions Path | Job Instances Path | Job Types |
|---|---|---|---|
| Notebook | `/notebooks/{id}/livySessions` | `/items/{id}/jobs/instances` | `PipelineRunNotebook`, `SparkSession` |
| Spark Job Definition | `/sparkJobDefinitions/{id}/livySessions` | `/items/{id}/jobs/instances` | `SparkJob` |
| Lakehouse | `/lakehouses/{id}/livySessions` | `/lakehouses/{id}/jobs/instances` | `TableLoad`, `TableMaintenance` |

> **Lakehouse note**: Lakehouse Spark sessions are typically short-lived (table loads, maintenance). If `livySessions` returns empty, check `jobs/instances` for `TableLoad`/`TableMaintenance` job history. Lakehouse jobs do not have a Notebook Snapshot — use Spark Advisor and driver logs for diagnostics.

**Present a session summary table** to the user (most recent 10):

```markdown
## Recent Sessions for <notebook name>

| # | Session ID | State | Submitted | Duration | App ID |
|---|------------|-------|-----------|----------|--------|
| 1 | abc-1234…  | Failed    | 2h ago  | 5m 23s  | app_…001 |
| 2 | def-5678…  | Succeeded | 4h ago  | 12m 10s | app_…002 |
| 3 | ghi-9012…  | Failed    | 1d ago  | 0s      | —        |
```

**Session selection logic:**
- **Auto-pick** if unambiguous — e.g., user said "why did it fail" and exactly 1 recent session has `state == Failed` → select it automatically and proceed
- **Ask the user** if ambiguous — multiple sessions match the user's intent (e.g., 2+ recent Failed sessions, or user said "diagnose" without specifying failed/slow) → present the table and ask which session to diagnose
- **User provided session/app ID** → skip the table entirely, use the ID directly

Extract `livyId`, `sparkApplicationId`, and `state` from the selected session.

---

## Step 1b — Fallback: Session Not Found / Data Expired

If the user provided a Livy session ID but it is **not found** in any session listing (workspace-level or item-level) and Spark Monitoring APIs return 404:

> **Why this happens**: Spark Monitoring API data (jobs, stages, executor logs, driver stderr) has **limited retention** after session completion — typically minutes to hours. Diagnose failures as soon as possible after they occur for the richest data.

**1. Determine the notebook ID** — ask the user if unknown:
```text
I found no active data for session `<livyId>` via Spark Monitoring APIs (data retention expired).

To diagnose this session, I need the **notebook name or ID** it belongs to.
- If this was from a **pipeline run**, provide the pipeline name + run ID — `queryActivityRuns` may still have error details.
- If you know the **notebook name**, provide it and I'll construct a direct link to the Fabric UI snapshot.
```

**2. Search pipeline runs** (if user confirms pipeline origin or workspace has pipelines):
Iterate pipelines → `GET /items/$pipelineId/jobs/instances` → follow all
`continuationToken` pages (or the service's continuation URI), carrying the skill
telemetry header on every request. Combine `value` arrays, sort by `startTimeUtc`
descending, and select recent Failed runs client-side before using
`queryActivityRuns` to find a sessionId match. Returns
`output.result.error.{ename, evalue, traceback[]}` — richest error data available.

**3. Check Job Instance API** — `GET /items/$notebookId/jobs/instances` for high-level
`failureReason` (longer retention than Spark Monitoring APIs). Collect continuation
pages before sorting/filtering or selecting the latest five client-side. The API
does not document `limit`; a partial/latest-N view cannot prove no history exists.

**4. Construct Notebook Snapshot URL** for manual cell-level inspection:
```text
https://app.powerbi.com/workloads/de-ds/sparkmonitor/{notebookId}/{livyId}?trident=1&experience=power-bi&ctid={tenantId}&tab=related
```
The Fabric UI retains notebook snapshots **much longer** than Spark Monitoring APIs (shows failed cell, traceback, cell execution times, and source code).

**5. Present report** with all available data:
```markdown
## Diagnostic Summary

**Session**: <livyId> | **Notebook**: <notebook name> | **State**: API data expired

### Error Details

[If queryActivityRuns returned data]:
**Exception**: <ename>: <evalue>
**Cell**: Cell In[<N>], line <M>
**Traceback**: <traceback lines>

[If only Job Instance data]:
**Failure Reason**: <failureReason from Job Instance API>

### Notebook Snapshot (cell-level details)
**Open Notebook Snapshot in Fabric UI**: `<constructed URL>`
↑ Click to view the exact failed cell, error output, and source code in the Fabric UI.

### Suggested Next Steps
1. Open the Notebook Snapshot link above to identify the exact failed cell and error
2. Fix the identified issue and re-run the notebook
3. For future failures, diagnose within 1 hour for full Spark Monitoring API data
4. For recurring failures, set up [proactive event log copy](jobinsight-api.md) to OneLake
```

> **Key principle**: Exhaust all public APIs (queryActivityRuns → Job Instance → Spark Monitoring) before falling back to the manual Notebook Snapshot URL. Always present the snapshot link — it has the longest retention.

---

## Step 2 — Auto-Route by Session State

| State | Automatic actions |
|---|---|
| `Failed` | Run **Step 3** (failure) + **Step 4** (performance) + **Step 5** (resource) |
| `Succeeded` | Run **Step 4** (performance) + **Step 5** (resource) |
| `InProgress` | Run **Step 4** (performance — partial snapshot) + **Step 5** (resource) |
| `Cancelled` | Check Livy log for cancellation reason, then **Step 3** |
| `idle` / `busy` / `starting` | Run **Step 6** (session health) |
| `dead` / `killed` / `error` | Run **Step 3** (failure) + **Step 6** (session health) |

---

## Step 3 — Failure Analysis

**Error API priority** — query in this order and stop at the first specific root cause:
1. **Job Instance** (`/jobs/instances/{id}`) — use the `failureReason` already retrieved during discovery when it is non-empty and actionable
2. **Spark Advisor** (`/advice`) — use when the job-instance reason is absent or generic
3. **Driver stderr** (`/logs?type=driver&fileName=stderr&isDownload=true`) — use only when both earlier sources remain inconclusive
4. **Executor logs** (`/logs?type=executor&meta=true`) — per-executor OOM / `ExecutorLostFailure`
5. **Livy log** (`/logs?type=livy`) — startup errors, library packaging failures
6. **Resource Usage** (`/resourceUsage`) — `capacityExceeded`, task limit exhaustion
7. **Notebook Snapshot URL** (manual) — all APIs expired, see [Step 1b](#step-1b--fallback-session-not-found--data-expired)

Request each documented log URL once. Do not try alternate escaping, download formats,
or gzip/deflate/ZIP decoding when a log request fails; report the unavailable source and
continue with the next documented evidence source.

> For **pipeline runs**, `queryActivityRuns` (Step P2 in [pipeline-diagnosis.md](pipeline-diagnosis.md)) is the richest single source — returns `output.result.error.{ename, evalue, traceback[]}` with cell/line numbers.

All API paths follow the pattern: `$FABRIC_API_URL/workspaces/$workspaceId/<itemTypePath>/$itemId/livySessions/$livyId/applications/$appId/<endpoint>` — see [SPARK-MONITORING-CORE.md](../../../../common/SPARK-MONITORING-CORE.md) for full specs.

**Auto-classify** errors by matching log content against the [Quick Reference Table](job-diagnostics.md#quick-reference-table).

---

## Step 4 — Performance Analysis

Query `/stages` and `/allexecutors` endpoints (see [SPARK-MONITORING-CORE.md § Open-Source Spark History Server APIs](../../../../common/SPARK-MONITORING-CORE.md#open-source-spark-history-server-apis)).

**Auto-flag** using [Detection Thresholds](performance-patterns.md#detection-thresholds):
- Data skew: `max/median task duration > 3×`
- Disk spill: `diskBytesSpilled > 0`
- GC pressure: `jvmGcTime/executorRunTime > 20%`
- Heavy shuffle: `shuffleWriteBytes > 1 GB`
- Small partitions: high task count, < 100 ms each

---

## Step 5 — Resource Utilization

Query `/resourceUsage` endpoint (see [SPARK-MONITORING-CORE.md § Resource Usage API](../../../../common/SPARK-MONITORING-CORE.md#resource-usage-api)). Extract `coreEfficiency`, `idleTime`, `duration`.

**Auto-flag:**
- `coreEfficiency < 0.3` → HIGH (underutilized)
- `idleTime / duration > 0.4` → MEDIUM (high idle)

---

## Step 6 — Session Health

List all sessions via `GET /workspaces/$workspaceId/spark/livySessions`. **Auto-flag:**
- `idle` with no recent statements → zombie
- `starting` beyond expected duration → capacity issue
- many concurrent sessions → capacity pressure

---

## Step 7 — Compile & Present Report

After running the applicable steps, present a structured report:

```markdown
## Diagnostic Summary

**Application**: <notebook name> | **Session**: <livyId> | **State**: <state>

### Findings (ordered by severity)

| # | Severity | Category | Finding | Recommended Fix |
|---|----------|----------|---------|-----------------|
| 1 | HIGH     | Failure  | Driver OOM from collect() on line 45 | Replace with df.write.parquet() |
| 2 | HIGH     | Perf     | Data skew in stage 12 (8.2× ratio) | Enable AQE skew join |
| 3 | MEDIUM   | Perf     | Disk spill in stage 8 (2.1 GB) | Increase shuffle partitions |
| 4 | MEDIUM   | Resource | Core efficiency 22% | Reduce executor count |

### Links
- **Notebook Snapshot**: `https://app.powerbi.com/workloads/de-ds/sparkmonitor/{notebookId}/{livyId}?trident=1&experience=power-bi&ctid={tenantId}&tab=related`
- **Spark Monitor**: `https://app.powerbi.com/workloads/de-ds/sparkmonitor/{notebookId}/{livyId}?trident=1&experience=power-bi&ctid={tenantId}`

### Suggested Next Steps
1. [Most impactful fix first]
2. [Second fix]
3. [Optional: escalate to Tier 2 if needed]
```

**Notebook Snapshot URL host**: Use `app.powerbi.com` for production, `msit.powerbi.com` for MSIT.

> **Tier 2 escalation**: If any step returns truncated data, HTTP 408/504, or the user asks for DAG/SQL plan visualization, suggest the [offline workflow](spark-history-server.md).

---

## Data Retention Summary

Public API retention windows for diagnostics:

| API | Approximate retention | Error detail level |
|-----|----------------------|-------------------|
| Spark Monitoring (Advisor, logs, jobs, stages) | Minutes–hours | Full (stack traces, metrics) |
| `queryActivityRuns` (pipeline path) | ~1 hour | Full (ename, evalue, traceback, cell/line) |
| Job Instance `failureReason` | Days | High-level summary only |
| Notebook Snapshot URL (Fabric UI) | Days–weeks | Full cell-level (manual) |

**Implication**: Diagnose failures as soon as possible. For recurring failures, configure [proactive event log copy](jobinsight-api.md) to OneLake for permanent retention.
