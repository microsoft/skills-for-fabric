<!-- Composite operations scenarios linked directly from sqldw-cli/SKILL.md. -->

# SQL DW Operations Scenarios

Use this guide when the request spans more than one focused operations workflow. It restores the original operations scenarios while keeping corrected SQL and endpoint rules in the directly indexed focused references.

## Contents

- [Response contract](#response-contract)
- [Analyze failed or canceled queries](#1-analyze-failed-or-canceled-queries)
- [Analyze SQL pool pressure](#2-analyze-sql-pool-pressure)
- [Analyze top resource consumers](#3-analyze-top-resource-consumers)
- [Analyze Lakehouse tables needing attention](#4-analyze-lakehouse-tables-needing-attention)
- [Explain why a warehouse is slow](#5-explain-why-a-warehouse-is-slow)
- [Determine whether performance degraded](#6-determine-whether-performance-degraded)
- [Find evidence-backed optimization targets](#7-find-evidence-backed-optimization-targets)
- [Explain what people are running](#8-explain-what-people-are-running)
- [Correlate a Capacity Metrics CU spike](#9-correlate-a-capacity-metrics-cu-spike)
- [Assess custom SQL pools](#10-assess-custom-sql-pools)
- [Examples](#examples)

## Response contract

Return exactly these headings in order:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

Every figure must come from a diagnostic run in the current turn and cite its source view or procedure. Treat zero rows and not-applicable results as valid findings.

**Follow-ups are for the user operating the investigated environment.** Give concrete next actions on the target workload, SQL item, capacity, or report window and say what to remeasure. Keep retention, lag, timezone, and correlation-confidence caveats in Evidence or Ruled out. Do not propose changes to the skill, PR, tests, documentation, or analysis implementation unless the user explicitly requested development work. If no action is warranted, say so and name the signal that should trigger reinvestigation.

## 1. Analyze failed or canceled queries

Use for failure history, cancellation, error-code, and recurring non-successful-query questions.

1. Read the directly indexed `failure-analysis.md` reference.
2. Establish failed, canceled, and combined scope for the requested UTC interval.
3. Resolve observed failed error codes through `sys.messages`; do not resolve cancellations as engine errors.
4. Identify recurring query shapes, users, programs, pools, and individual requests.
5. Test pressure or cache explanations only when the evidence makes them relevant.

## 2. Analyze SQL pool pressure

Use for pressure incidents and requests asking what competed for SQL pool resources.

1. Read the directly indexed `pool-pressure.md` reference.
2. Build intervals from all state events, retaining the pressure-off event as the closing boundary.
3. Summarize affected pools, interval count and duration, peak resource percentage, and capacity SKU.
4. Correlate requests using both strict time overlap and exact `sql_pool_name`.
5. Describe overlap as correlation, not proof.

## 3. Analyze top resource consumers

Use for dominant compute, repeated expensive queries, and regressions.

1. Read the directly indexed `resource-consumers.md` reference.
2. Measure allocated-CPU concentration and select the smallest leading set reaching 50%, capped at five query hashes.
3. Compare the recent window with the immediately preceding normalized baseline.
4. Separate execution-volume growth, per-run regression, one-off cost, and distributed workload.
5. Inspect individual executions and interpret historical cache fields without recommending unavailable result-set caching.

## 4. Analyze Lakehouse tables needing attention

Use only for a Lakehouse SQL analytics endpoint.

1. Read the directly indexed `lakehouse-health.md` reference.
2. Reject Warehouse and Mirrored Database targets as not applicable.
3. Enumerate every user table.
4. Run `sys.sp_get_table_health_metrics` once per fully qualified table, respecting rate limits.
5. Report Delta file sizes, row counts, deleted rows, checkpoints, and procedure-reported anomalies without substituting SQL optimizer statistics.

## 5. Explain why a warehouse is slow

1. Read `pool-pressure.md` and check the requested interval for contention.
2. Read `resource-consumers.md` and identify CPU concentration, expensive executions, and cache/storage behavior.
3. Read `query-reference.md` only when long-running summaries or runtime profiles are also needed.
4. Distinguish pressure, query cost, remote scans, cold starts, and distributed workload; do not list untested tuning knobs.

## 6. Determine whether performance degraded

1. Read `resource-consumers.md` and compare the requested recent window with a non-overlapping normalized baseline.
2. Read `query-reference.md` for long-running summaries and top-user patterns when needed.
3. Classify new query shapes separately from existing-query regressions.
4. Report the underlying recent and baseline values with every ratio.

## 7. Find evidence-backed optimization targets

1. Read `resource-consumers.md` to identify repeated CPU, elapsed-time, and scan cost.
2. Read `query-reference.md` for cluster-key candidates derived from filter predicates and table usage.
3. Read `pool-pressure.md` when elapsed time is high relative to CPU.
4. Recommend only actions supported by the observed evidence. Operations mode never applies CTAS, clustering, cache, or capacity changes.

## 8. Explain what people are running

1. Read the **Recent Warehouse Activity** section in `query-reference.md`.
2. Run its bounded request query and summarize users, programs, statement types, query shapes, and pools.
3. Search query text only for a user-supplied table, column, label, or keyword.
4. Bound every query and exclude agent monitoring statements.

## 9. Correlate a Capacity Metrics CU spike

1. Read `capacity-metrics-correlation.md` from section 1.
2. Discover the installed Capacity Metrics model through the existing FabricIQ MCP.
3. Inspect the live schema and choose its timestamped item/hour or fixed-window capacity-health branch.
4. Keep fixed-window health separate from broader non-timestamped item totals; treat empty drillthrough tables as unavailable evidence.
5. Resolve a Warehouse or Lakehouse SQL endpoint only when same-timeframe evidence identifies it as a costly contributor. Otherwise stop spike correlation and offer Query Insights as a separately scoped investigation.
6. Use the overall Capacity Metrics spike window to retrieve all overlapping Query Insights requests for the resolved SQL item, then analyze their users, applications, query shapes, CPU, elapsed time, scans, status, and pool pressure.
7. Treat those requests as best-effort time correlation. Capacity Metrics Operation Id is not Query Insights `distributed_statement_id` and must not be joined to it.
8. Keep CU seconds and Query Insights CPU milliseconds as separate signals.
9. Turn evidence gaps into user actions only when actionable: confirm the report timezone, inspect non-SQL operations for unexplained intervals, or add and refresh missing Warehouse sources in the user's correlation model. Otherwise keep the gap as a stated limitation.

## 10. Assess custom SQL pools

1. Read `capacity-metrics-correlation.md` starting at section 6; skip FabricIQ when the SQL endpoint is already identified.
2. Use one anchored historical interval across workload and pressure queries.
3. Group by stable `program_name`, pool, statement type, and day.
4. Recommend preview custom pools only for recurring contention and stable application classifiers.
5. Do not infer pool percentages from CU seconds or CPU milliseconds and do not configure pools.
6. Tell the user which classifier to pilot, which workload it isolates, and which pressure, CPU, scan, latency, and failure measures to compare after the pilot.

## Examples

### Find slow queries

**User:** “What are the slowest queries in my warehouse?”

Run the long-running summary from `query-reference.md`, cite the live Query Insights values, and separate repeated slowness from a single expensive execution.

### Diagnose performance degradation

**User:** “Is my warehouse slower than last week?”

Run the normalized recent-versus-baseline workflow from `resource-consumers.md`, then check pressure and top-user evidence only when needed to explain the change.

### Get clustering recommendations

**User:** “Which tables should I cluster and on what columns?”

Use current Query Insights filter and scan evidence from `query-reference.md`. Recommend supported CTAS with `CLUSTER BY` for an authoring follow-up, but do not execute it in operations mode.
