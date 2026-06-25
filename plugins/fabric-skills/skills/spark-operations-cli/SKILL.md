---
name: spark-operations-cli
description: >
  Diagnose failed Spark jobs, unhealthy Livy sessions,
  and performance bottlenecks in Microsoft Fabric via read-only CLI triage.
  Use when the user wants to: (1) diagnose why a Spark job, notebook run, or Lakehouse job failed,
  (2) triage stuck or dead Livy sessions, (3) identify OOM, shuffle spill, or data skew,
  (4) retrieve driver and executor logs or Spark Advisor findings,
  (5) copy event logs and start a local Spark History Server,
  (6) diagnose all Spark activities within a failed pipeline run.
  Triggers: "diagnose my failed notebook", "why did my spark job fail",
  "triage spark failure", "diagnose pipeline run failure", "why did my pipeline fail",
  "livy session stuck in starting", "spark executor OOM",
  "check spark advisor findings", "shuffle spill diagnosis",
  "why did my lakehouse job fail", "diagnose lakehouse table load",
  "data skew diagnosis", "open spark history server locally",
  "analyze spark failure logs", "spark job triage".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: `spark-operations-cli` is for **read-only triage and diagnosis** of existing jobs and sessions. For creating notebooks, running new jobs, or Spark development, use `spark-authoring-cli`. For interactive PySpark analysis and Livy session creation, use `spark-consumption-cli`.

# Spark Operations — CLI Skill

This skill provides diagnostics for Microsoft Fabric Spark job failures, Livy session health, and performance bottlenecks using Fabric REST APIs and CLI tools (`az rest`). All diagnostic operations are read-only; session cleanup (e.g., stopping zombie sessions) requires explicit user confirmation. For Spark development and notebook authoring, use `spark-authoring-cli`. For interactive PySpark analysis, use `spark-consumption-cli`.

## Table of Contents

The TOC is grouped by purpose. Start at **Diagnostic Workflows** when triaging an active failure; the earlier sections are foundational references.

### 1. Fabric Foundations (concepts)

| Task | Reference | Notes |
|---|---|---|
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) ||
| Pagination | [COMMON-CORE.md § Pagination](../../common/COMMON-CORE.md#pagination) ||
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro) ||
| Rate Limiting & Throttling | [COMMON-CORE.md § Rate Limiting & Throttling](../../common/COMMON-CORE.md#rate-limiting--throttling) ||
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) ||
| Capacity Management | [COMMON-CORE.md § Capacity Management](../../common/COMMON-CORE.md#capacity-management) ||
| Gotchas & Troubleshooting | [COMMON-CORE.md § Gotchas & Troubleshooting](../../common/COMMON-CORE.md#gotchas--troubleshooting) ||
| Best Practices | [COMMON-CORE.md § Best Practices](../../common/COMMON-CORE.md#best-practices) ||

### 2. CLI Setup & Authentication

| Task | Reference | Notes |
|---|---|---|
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** or `az rest` fails |
| Pagination Pattern | [COMMON-CLI.md § Pagination Pattern](../../common/COMMON-CLI.md#pagination-pattern) ||
| Long-Running Operations (LRO) Pattern | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference: `az rest` Template | [COMMON-CLI.md § Quick Reference: az rest Template](../../common/COMMON-CLI.md#az-rest-template) ||
| Quick Reference: Token Audience / CLI Tool Matrix | [COMMON-CLI.md § Quick Reference: Token Audience ↔ CLI Tool Matrix](../../common/COMMON-CLI.md#token-audience--cli-tool-matrix) | Which `--resource` + tool for each service |

### 3. Spark Sessions, Notebooks & Jobs (background)

| Task | Reference | Notes |
|---|---|---|
| Livy Session Management | [SPARK-CONSUMPTION-CORE.md § Livy Session Management](../../common/SPARK-CONSUMPTION-CORE.md#livy-session-management) | Session creation, states, lifecycle, termination |
| Interactive Data Exploration | [SPARK-CONSUMPTION-CORE.md § Interactive Data Exploration](../../common/SPARK-CONSUMPTION-CORE.md#interactive-data-exploration) | Statement execution, output retrieval, data discovery |
| Notebook Execution & Job Management | [SPARK-AUTHORING-CORE.md § Notebook Execution & Job Management](../../common/SPARK-AUTHORING-CORE.md#notebook-execution--job-management) ||

### 4. Spark Monitoring APIs (primary triage surface)

| Task | Reference | Notes |
|---|---|---|
| Spark Monitoring API Overview | [SPARK-MONITORING-CORE.md § Overview](../../common/SPARK-MONITORING-CORE.md#overview) | GA monitoring APIs — no active session required |
| Workspace & Item Session Listing | [SPARK-MONITORING-CORE.md § Workspace and Item-Level Session Listing](../../common/SPARK-MONITORING-CORE.md#workspace-and-item-level-session-listing) | List Spark apps across workspace with filtering |
| Spark Advisor API | [SPARK-MONITORING-CORE.md § Spark Advisor API](../../common/SPARK-MONITORING-CORE.md#spark-advisor-api) | **Key** — automated skew detection, task errors, recommendations |
| Open-Source Spark History Server APIs | [SPARK-MONITORING-CORE.md § Open-Source Spark History Server APIs](../../common/SPARK-MONITORING-CORE.md#open-source-spark-history-server-apis) | Jobs, stages, executors, SQL queries via REST |
| Driver and Executor Log APIs | [SPARK-MONITORING-CORE.md § Driver and Executor Log APIs](../../common/SPARK-MONITORING-CORE.md#driver-and-executor-log-apis) | Direct log retrieval without active session |
| Livy Log API | [SPARK-MONITORING-CORE.md § Livy Log API](../../common/SPARK-MONITORING-CORE.md#livy-log-api) | Session-level log with byte-offset pagination |
| Resource Usage API | [SPARK-MONITORING-CORE.md § Resource Usage API](../../common/SPARK-MONITORING-CORE.md#resource-usage-api) | vCore timeline, idle/running cores, efficiency metrics |
| Monitoring Diagnostic Workflow | [SPARK-MONITORING-CORE.md § Diagnostic Workflow Using Monitoring APIs](../../common/SPARK-MONITORING-CORE.md#diagnostic-workflow-using-monitoring-apis) | Step-by-step triage using monitoring APIs |

### 5. Diagnostic Workflows (start here for active triage)

| Task | Reference | Notes |
|---|---|---|
| Automated Diagnostic Workflow (full) | [automated-diagnostic-workflow.md](references/automated-diagnostic-workflow.md) | Steps 1–7: resolve → route by state → failure/perf/resource/health → report. Includes Step 1b expired-data fallback and report templates |
| Diagnostic Tiers | [diagnostic-workflow.md § Diagnostic Tiers](references/diagnostic-workflow.md#diagnostic-tiers) | Tier 1 (online REST) vs Tier 2 (local SHS) |
| Key Diagnostic Patterns | [diagnostic-workflow.md § Key Diagnostic Patterns](references/diagnostic-workflow.md#key-diagnostic-patterns) | Symptom → first check → likely cause lookup |
| Severity Thresholds | [diagnostic-workflow.md § Severity Thresholds](references/diagnostic-workflow.md#severity-thresholds) | Metric thresholds for classifying findings |
| Manual CLI Recipes | [diagnostic-workflow.md § Manual CLI Recipes](references/diagnostic-workflow.md#manual-cli-recipes) | Ad-hoc diagnostic commands for manual use |
| Pipeline Run Diagnosis | [pipeline-diagnosis.md](references/pipeline-diagnosis.md) | Diagnose all Spark activities within a pipeline run (Steps P1–P6) |

### 6. Job Failure Diagnostics

| Task | Reference | Notes |
|---|---|---|
| Failure Triage Workflow | [job-diagnostics.md § Failure Triage Workflow](references/job-diagnostics.md#failure-triage-workflow) | Step-by-step decision tree for diagnosing failures |
| Job Failure Classification | [job-diagnostics.md § Failure Classification](references/job-diagnostics.md#failure-classification) | OOM, shuffle, timeout, dependency, configuration errors |
| Reading Spark Logs via REST | [job-diagnostics.md § Reading Spark Logs via REST](references/job-diagnostics.md#reading-spark-logs-via-rest) | Driver/executor log retrieval from Livy |
| Job Instance History | [job-diagnostics.md § Job Instance History](references/job-diagnostics.md#job-instance-history) | Query recent runs, compare durations, detect regressions |

### 7. Livy Session Health

| Task | Reference | Notes |
|---|---|---|
| Session Health Assessment | [session-health.md § Livy Session Lifecycle](references/session-health.md#livy-session-lifecycle) | Session states, transitions, expected durations |
| Idle and Zombie Session Detection | [session-health.md § Idle and Zombie Session Detection](references/session-health.md#idle-and-zombie-session-detection) | Find and clean up leaked sessions |
| Session Resource Monitoring | [session-health.md § Session Resource Monitoring](references/session-health.md#session-resource-monitoring) | Memory and executor usage via Livy |
| Session Recovery Patterns | [session-health.md § Session Recovery Patterns](references/session-health.md#session-recovery-patterns) | Restart strategies and session replacement |

### 8. Performance Diagnostics

| Task | Reference | Notes |
|---|---|---|
| Performance Anti-Patterns | [performance-patterns.md § Anti-Patterns](references/performance-patterns.md#anti-patterns) | Spill, shuffle, skew, small files, collect misuse |
| Stage and Task Analysis | [performance-patterns.md § Stage and Task Analysis](references/performance-patterns.md#stage-and-task-analysis) | Reading Spark UI metrics via REST |
| Optimization Recipes | [performance-patterns.md § Optimization Recipes](references/performance-patterns.md#optimization-recipes) | Partition tuning, broadcast joins, caching |
| Capacity and Resource Diagnostics | [performance-patterns.md § Capacity and Resource Diagnostics](references/performance-patterns.md#capacity-and-resource-diagnostics) | CU consumption, throttling detection |

### 9. Offline / Deep-Dive Tools

| Task | Reference | Notes |
|---|---|---|
| JobInsight Event Log Copy | [jobinsight-api.md § LogUtils.copyEventLog](references/jobinsight-api.md#logutilscopyeventlog) | Copy event logs from Fabric to OneLake for offline analysis |
| Local Spark History Server | [spark-history-server.md § Overview](references/spark-history-server.md#overview) | Start local SHS for full Spark UI (DAG, tasks, SQL plans) |

---

## Must/Prefer/Avoid

### MUST DO

- Always retrieve job/session status before attempting remediation
- Use workspace and item discovery from [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) — never hardcode IDs
- Check Livy session state before submitting diagnostic statements
- Follow the [Failure Triage Workflow](references/job-diagnostics.md#failure-triage-workflow) for systematic diagnosis
- Always check the Spark Advisor API before reading raw logs — it often identifies the root cause immediately
- Use monitoring APIs (no active session required) before attempting Livy-based diagnostics
- Poll job/session status with 10–30 second intervals; timeout diagnostics after 30 minutes
- Always include the Notebook Snapshot URL in diagnostic output — it has the longest retention and enables cell-level inspection in the Fabric UI

### PREFER

- Querying job instance history to establish baseline before declaring a regression
- Reusing existing idle sessions for diagnostic queries instead of creating new ones
- Checking capacity utilization when jobs are slow before blaming the Spark code
- Using `az rest` with JMESPath filtering to extract specific fields from large API responses
- The Spark Advisor API over manual log parsing for skew, task errors, and timeout detection
- Resource Usage API `coreEfficiency` metric to quantify cluster utilization before recommending scaling
- Job instance history comparison (last 5 runs) to detect regressions before deep-diving
- For MLV refresh scheduling, monitoring, or run-history, use [mlv-operations-cli](../mlv-operations-cli/SKILL.md). For diagnosing the underlying Spark job failure (OOM, skew, shuffle spill), continue with this skill — MLV refreshes execute as Spark jobs and their logs are accessible via the same monitoring APIs.
- **MLV failure classification** — when diagnosing a failed MLV refresh, classify the error before deep-diving:

  | Error Pattern | Category | Diagnosis Path |
  |--------------|----------|----------------|
  | `MLV_SPARK_SESSION_REQUEST_SUBMISSION_FAILED` | Infrastructure | Capacity paused/unavailable, Spark pool misconfigured. Check capacity state first. |
  | `MLV_SELECTED_NOT_FOUND` | Configuration | MLV table was deleted/renamed. Verify table exists via `SHOW MATERIALIZED LAKE VIEWS IN schema`. |
  | `OutOfMemoryError` / `SparkOutOfMemory` | Resource | Source data grew beyond cluster capacity. Check Spark Advisor for memory pressure. |
  | `ShuffleBlockFetchFailed` / data skew | Performance | Uneven data distribution. Use Resource Usage API to identify skewed partitions. |
  | `DeltaTableVersionNotFound` | Dependency | Source table was vacuumed below retention threshold. Extend `delta.logRetentionDuration`. |
  | `ConstraintViolationException` / `ON MISMATCH` | Data Quality | DQ constraint dropped/failed rows. Check source data quality upstream. |
  | Timeout (run > 24 hours) | Scale | Lineage too large for single run. Split into smaller lineage groups across lakehouses. |

### AVOID

- Killing sessions without checking if they have active statements
- Creating new sessions for every diagnostic query (reuse idle sessions)
- Assuming OOM without checking actual memory metrics from Livy
- Hardcoded workspace or item IDs in diagnostic scripts
- Diagnosing performance without first checking capacity throttling via the Admin API
- Submitting diagnostic statements to sessions in `busy` state

---

## Examples

### Example 1: Diagnose a Failed Notebook

User prompt: *"Why did my notebook ETL_Daily fail in workspace Production?"*

Agent workflow:
1. Resolves workspace → `workspaceId`, item → `itemId` (Notebook)
2. Lists recent Livy sessions, auto-picks the Failed session
3. Queries Spark Advisor → finds `TaskError: OutOfMemoryError` on executor
4. Queries `/stages` → confirms data skew (12× max/median ratio in stage 5)
5. Presents report with HIGH findings + fix recommendations

### Example 2: Triage Stuck Livy Session

User prompt: *"My Livy session abc-1234 is stuck in starting state"*

Agent workflow:
1. Uses session ID directly, queries session state
2. Lists all workspace sessions → detects 8 concurrent sessions (capacity pressure)
3. Checks Livy log → no errors, just queued
4. Reports: capacity contention, recommends waiting or cancelling idle sessions

### Example 3: Pipeline Failure Root Cause

User prompt: *"Diagnose pipeline run 5678 in workspace Analytics"*

Agent workflow:
1. Resolves pipeline, calls `queryActivityRuns` for run 5678
2. Finds 2 Notebook activities: one Succeeded, one Failed
3. Extracts `output.result.error.{ename, evalue, traceback}` from failed activity
4. Constructs Notebook Snapshot URL for cell-level inspection
5. Presents error details + snapshot link + suggested fix

---

## Quick Start

### Environment Setup

Apply environment detection from [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes) to set:
- `$FABRIC_API_BASE` and `$FABRIC_RESOURCE_SCOPE`
- `$FABRIC_API_URL` and `$LIVY_API_PATH` for Livy operations

**Authentication**: Use token acquisition from [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes).

---

## Automated Diagnostic Workflow

When the user provides a simple prompt (e.g., *"Diagnose my notebook ETL_Pipeline"*, *"What's wrong with Spark application abc-123"*, *"Check workspace Production for issues"*), follow this **fast-path** summary. For full procedure, edge cases (expired data, pipeline-only sessions), report templates, and retention details, see [references/automated-diagnostic-workflow.md](references/automated-diagnostic-workflow.md).

### Entry Points (what the user provides)

| User provides | Agent resolves |
|---|---|
| Workspace name | → `workspaceId` (via workspace list + name filter) |
| Notebook / SJD / Lakehouse name | → `itemId` (via item list + name/type filter) |
| Pipeline name + run ID | → child Spark activities → see [pipeline-diagnosis.md](references/pipeline-diagnosis.md) |
| Livy session ID or Spark app ID | → Use directly |
| Nothing specific | → Ask for workspace name + item name |

### Item-Type API Paths

| Item Type | Livy Sessions Path | Job Instances Path |
|---|---|---|
| Notebook | `/notebooks/{id}/livySessions` | `/items/{id}/jobs/instances` |
| Spark Job Definition | `/sparkJobDefinitions/{id}/livySessions` | `/items/{id}/jobs/instances` |
| Lakehouse | `/lakehouses/{id}/livySessions` | `/lakehouses/{id}/jobs/instances` |

All session API paths follow: `$FABRIC_API_URL/workspaces/$workspaceId/<itemTypePath>/$itemId/livySessions/$livyId/applications/$appId/<endpoint>` — see [SPARK-MONITORING-CORE.md](../../common/SPARK-MONITORING-CORE.md).

### Steps at a Glance

| Step | When | Action | Auto-flag rule |
|---|---|---|---|
| **1. Resolve & Discover** | Always | Resolve workspace → item → list recent Livy sessions; auto-pick if unambiguous, else prompt user | — |
| **1b. Fallback** | Session 404 / Spark Monitoring data expired | Try `queryActivityRuns` (pipeline) → Job Instance `failureReason` → construct Notebook Snapshot URL | See [reference § Step 1b](references/automated-diagnostic-workflow.md#step-1b--fallback-session-not-found--data-expired) |
| **2. Route by state** | After Step 1 | `Failed` → 3+4+5 · `Succeeded`/`InProgress` → 4+5 · `Cancelled` → log+3 · `idle`/`busy`/`starting` → 6 · `dead`/`killed`/`error` → 3+6 | — |
| **3. Failure analysis** | Failed / Cancelled / dead | Query in order: Spark Advisor → driver stderr → Job Instance → executor logs → Livy log → Resource Usage. Stop when root cause clear. | Match against [job-diagnostics.md § Quick Reference Table](references/job-diagnostics.md#quick-reference-table) |
| **4. Performance** | Always (except 1b path) | `/stages`, `/allexecutors` | skew `max/median > 3×` · spill `diskBytesSpilled > 0` · GC `jvmGcTime/executorRunTime > 20%` · shuffle `> 1 GB` · tasks `< 100ms` |
| **5. Resource utilization** | Always (except 1b path) | `/resourceUsage` | `coreEfficiency < 0.3` → HIGH · `idleTime/duration > 0.4` → MEDIUM |
| **6. Session health** | Idle/zombie checks | `GET /workspaces/$workspaceId/spark/livySessions` | `idle` + no recent statements → zombie · `starting` beyond expected → capacity |
| **7. Compile report** | Final | Severity-ordered findings table + Notebook Snapshot link + suggested fixes | See [reference § Step 7](references/automated-diagnostic-workflow.md#step-7--compile--present-report) for template |

> **Key principle**: Always check **Spark Advisor first** — it's pre-computed and identifies most root causes without log parsing. Pipeline runs have the richest error data via `queryActivityRuns` (`ename`, `evalue`, `traceback`, cell/line) — see [pipeline-diagnosis.md](references/pipeline-diagnosis.md).

> **Data retention warning**: Spark Monitoring API data (logs, stages, advisor) typically expires in **minutes to hours** after session end. Diagnose failures promptly. If APIs return 404, jump to Step 1b in the [reference](references/automated-diagnostic-workflow.md#step-1b--fallback-session-not-found--data-expired).

> **Tier 2 escalation**: For truncated data, HTTP 408/504, or DAG/SQL plan visualization, suggest the [offline Spark History Server workflow](references/spark-history-server.md).
