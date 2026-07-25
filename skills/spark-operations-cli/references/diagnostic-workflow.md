# Diagnostic Workflow Guide

## Manual CLI Recipes

The following recipes are for ad-hoc manual use. The [automated workflow](../SKILL.md#automated-diagnostic-workflow) is preferred for most users.

### Diagnose a Failed Notebook Run

```bash
# 1. Discover workspace and notebook
workspaceId=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces" \
  --query "value[?displayName=='MyWorkspace'].id" --output tsv)

notebookId=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items?type=Notebook" \
  --query "value[?displayName=='MyNotebook'].id" --output tsv)

# 2. Get recent job instances
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances?limit=5" \
  --query "value[].{id:id, status:status, start:startTimeUtc, end:endTimeUtc, failureReason:failureReason}" \
  --output table

# 3. Get details of the failed instance
jobInstanceId="<from-above>"
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances/$jobInstanceId" \
  --output json
```

### Check Livy Session Health

```bash
# List all sessions for a lakehouse
lakehouseId="<lakehouse-id>"
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions" \
  --query "sessions[].{id:id, state:state, name:name, appId:appId}" \
  --output table

# Get detailed session info (includes memory, executors)
sessionId="<session-id>"
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId" \
  --output json
```

### Quick Performance Check via Livy Statement

```bash
# Run a diagnostic PySpark snippet in an existing idle session
cat > /tmp/body.json << 'DIAG'
{
  "code": "sc = spark.sparkContext\nprint('Active executors:', len(sc._jsc.sc().getExecutorMemoryStatus()))\nprint('Default parallelism:', sc.defaultParallelism)\nprint('Spark config:')\nfor k, v in sorted(spark.sparkContext.getConf().getAll()):\n    if any(x in k for x in ['memory', 'cores', 'parallelism', 'shuffle', 'dynamic']):\n        print(f'  {k} = {v}')",
  "kind": "pyspark"
}
DIAG
az rest --method post --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/statements" \
  --body @/tmp/body.json --output json
```

---

## Key Diagnostic Patterns

| Symptom | First Check | Likely Cause | Reference |
|---|---|---|---|
| Job failed with error | Job instance `failureReason` | See failure classification | [job-diagnostics.md](job-diagnostics.md#failure-classification) |
| Session stuck in `starting` | Session state + elapsed time | Capacity pressure or pool misconfiguration | [session-health.md](session-health.md#livy-session-lifecycle) |
| Job runs but is very slow | Stage metrics + executor count | Shuffle spill, data skew, under-provisioning | [performance-patterns.md](performance-patterns.md#anti-patterns) |
| `OutOfMemoryError` in logs | Driver vs executor OOM | Wrong memory config or data explosion | [job-diagnostics.md](job-diagnostics.md#failure-classification) |
| Many idle sessions | Session list with state filter | Session leak — clean up | [session-health.md](session-health.md#idle-and-zombie-session-detection) |
| Job slower than yesterday | Job history duration comparison | Regression or data volume growth | [job-diagnostics.md](job-diagnostics.md#job-instance-history) |

---

## Diagnostic Tiers

This skill provides two diagnostic tiers. Always start with **Tier 1**. Escalate to **Tier 2** only when Tier 1 is insufficient.

### Tier 1 — Online (Primary)

Uses Fabric Spark Monitoring REST APIs (via `az rest`) to pull session data, failed jobs, slowest stages, Spark Advisor findings, and driver logs. Fast; no download; no active session required.

**Workflow:**
1. **Find the session** — List Livy sessions for the notebook/SJD (see [Monitoring Workflow](../../../common/SPARK-MONITORING-CORE.md#diagnostic-workflow-using-monitoring-apis))
2. **Check Advisor** — Query the Spark Advisor API for automated root-cause detection
3. **Failure analysis** — If job failed, inspect failed jobs/stages, read driver/executor logs
4. **Performance analysis** — Check stage metrics, executor utilization, resource usage
5. **Interpret and report** — Classify findings using the severity thresholds below

### Tier 2 — Offline Fallback (Local Spark History Server)

Copies the full Spark event log from Fabric to a OneLake lakehouse via the [JobInsight API](jobinsight-api.md), downloads it locally, and starts the OSS Spark History Server on `http://localhost:18080` for the full Spark UI (DAG, task-level detail, SQL plan visualizations).

**When to escalate to Tier 2:**

| Condition | How to detect |
|-----------|---------------|
| API timeout / truncated data | HTTP 408/504 from Monitoring API, or partial stage data |
| Event log too large | Stage detail incomplete or >100 stages to analyze |
| User needs full Spark UI | User asks for "DAG", "task details", "SQL plan visualization", or "Spark UI" |
| Managed History Server slow | User reports Fabric's monitoring hub is unresponsive |

**Offline workflow:**
1. Copy event logs via JobInsight `LogUtils.copyEventLog()` — see [jobinsight-api.md](jobinsight-api.md)
2. Download event files from OneLake DFS to local disk
3. Start local Spark History Server — see [spark-history-server.md](spark-history-server.md)
4. Open browser to `http://localhost:18080` for the full Spark UI

---

## Severity Thresholds

Use these thresholds when interpreting stage metrics and resource usage to classify issues:

| Metric | Threshold | Severity | Meaning |
|--------|-----------|----------|---------|
| `maxExecutorRunTime / median` | > 3× | HIGH | Data skew — one task dominates stage duration |
| `diskBytesSpilled` | > 0 | MEDIUM | Memory insufficient for sort/join — spilling to disk |
| `gcTime / executorRunTime` | > 20% | MEDIUM | GC pressure — JVM heap filling faster than GC can free it |
| `shuffleWriteBytes` per stage | > 1 GB | MEDIUM | Heavy shuffle — consider pre-filtering or caching |
| `coreEfficiency` | < 0.3 | HIGH | Severe underutilization — over-provisioned or idle executors |
| `idleTime / duration` | > 40% | MEDIUM | High idle ratio — reduce executor count or session timeout |
| Any job with `numFailedTasks > 0` | — | HIGH | Failure flagged — run failure triage workflow |

### Stage Detail Selection Logic

When analyzing performance, select stages for detailed task-level inspection:
1. If Spark Advisor identifies affected stages/jobs/SQL executions — use those first
2. If Advisor has no findings, select fallback candidates: slowest 10 stages, shuffle-heavy top 10, spill top 10
3. Union candidates and cap at 20 stages total
4. For each selected stage, query `/stages/{stageId}/{attemptId}/taskSummary?quantiles=0.25,0.5,0.75,0.95,1.0`

### Presenting Results

1. Lead with a **one-line severity summary** (e.g., "Found 2 job failures and 3 performance issues")
2. Classify each finding by severity (HIGH/MEDIUM/LOW)
3. Highlight the **most impactful fix first**
4. Offer to drill into any specific failure or bottleneck
