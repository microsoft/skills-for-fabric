<!-- Cross-skill workflow for sqldw-cli operations mode. Capacity discovery and DAX stay with fabriciq; SQL diagnostics stay with sqldw-cli. -->

# Capacity Metrics to SQL Query Correlation

For a Capacity Metrics investigation, run sections 1-7. For pool assessment on an already identified SQL item, skip FabricIQ and start at section 6.

## Contents

- [Boundaries](#existing-tool-and-authentication-boundary)
- [Limits](#timeframe-and-correlation-limits)
- [Capacity workflow](#1-discover-the-installed-capacity-metrics-model)
- [SQL correlation](#5-find-expensive-sql-users-and-queries)
- [Pool assessment](#6-profile-historical-workload-for-custom-sql-pools)
- [Response](#response-contract)

## Existing Tool and Authentication Boundary

Use only Fabric skill surfaces already present in the `fabric-skills` plugin:

- For the Capacity Metrics entry point, `fabriciq` with the existing FabricIQ MCP connection for artifact discovery, metadata/schema inspection, and DAX execution.
- `sqldw-cli` operations mode with `fabric-sqlendpoint-execute_query` for Query Insights.
- Existing Fabric control-plane discovery from `COMMON-CLI.md` only when an item identity must be resolved.

Do not introduce a new sign-in, token flow, app registration, secret, MCP server, raw REST DAX call, or SQL client. A custom-pool-only request does not require FabricIQ. If a required MCP surface is unavailable, report which phase is blocked and what was still established.

## Timeframe and Correlation Limits

Establish one requested UTC half-open interval, `[start, end)`, and repeat it in the final answer. Apply it to every query that supports arbitrary timestamps and always to Query Insights. When Capacity Metrics exposes only a named fixed-window table, report that window separately instead of pretending the requested bounds were applied.

- Capacity Metrics model versions differ. Some expose a timestamped item/hour table; others expose fixed-window capacity tables such as `Usage Summary (Last 24 hours)` and broader, non-hourly item totals such as `Metrics By Item`.
- For a timestamped hourly table, query the containing hour buckets but retain and disclose the user's exact requested interval.
- A fixed-window table is valid only for its named model-defined window. Do not present it as an exact arbitrary interval or combine it with broader item totals as if they share a timeframe.
- Report timestamps are not necessarily documented as UTC. If the model does not expose timezone metadata, identify them as report timestamps rather than asserting a timezone.
- Query Insights retains 30 days and completed requests can take up to 15 minutes to appear.
- The usable period is the intersection of Capacity Metrics history and Query Insights history. Never silently widen, shift, or compare different windows.
- Capacity Metrics CU seconds and Query Insights CPU milliseconds are complementary signals, not interchangeable units.
- Capacity Metrics Operation Id and Query Insights `distributed_statement_id` are different identifiers. Never compare, normalize, or join them.
- The cross-system handoff is the Capacity Metrics spike time range plus the resolved Fabric item. Query every Query Insights request that overlaps that range, then analyze those candidates.
- SQL statement correlation is best-effort because Capacity Metrics does not provide an authoritative cross-system statement key.

## 1. Discover the Installed Capacity Metrics Model

Invoke `fabriciq` and follow its workflow rather than reproducing Power BI authentication:

1. Call `DiscoverArtifacts` with `Fabric Capacity Metrics` or `Capacity Metrics`.
2. Prefer the installed report when present. If several plausible reports/models exist, show the candidates and ask the user to select one.
3. For a report, call `GetReportMetadata` and use its semantic model GUID for later calls.
4. Call `GetSemanticModelSchema` in full and obey its CustomInstructions and VerifiedAnswers rules before generating DAX.
5. Build a capability map from the live schema before choosing a query:
   - Capacity inventory: `Capacities`.
   - Fixed-window health: tables named like `Usage Summary (...)`, `Usage Summary By Capacities (...)`, `Usage Operation (...)`, or equivalent.
   - Timestamped item history: a table with item/workspace identity, CU, and an hour/timestamp column, either directly or through a documented relationship.
   - Broader item totals: tables such as `Metrics By Item` that have item identity and CU but no timestamp.
   - Drillthrough operations: timepoint or operation-detail tables with Capacity Metrics Operation Id and start/end columns.

Report the resolved report/model and workspace before continuing.

## 2. Resolve the Capacity and Rank Costly Items

Resolve the capacity dynamically from the model. If the user did not name one and multiple capacities exist, list name, ID, SKU, and state and ask them to choose.

Capacity Metrics DirectQuery tables can require the `CapacitiesList` M parameter. Pass only IDs returned by the live `Capacities` table. Some item tables accept one capacity at a time even when fixed-window health tables accept several; retry item ranking once with a single selected capacity when a multi-capacity query returns a data-location error.

Choose one branch from the schema:

### Timestamped item/hour branch

Use this branch only when the schema exposes item/workspace identity, CU, and an hourly timestamp in one filter path.

1. Calculate `capacity_bucket_start` by flooring the requested start to the hour and `capacity_bucket_end` by ceiling the requested end to the next hour.
2. Generate a schema-valid query equivalent to the former `Metrics By Item And Hour` query: group by item ID, name, kind, workspace ID/name; filter the live timestamp column to `[capacity_bucket_start, capacity_bucket_end)`; aggregate CU, duration, operations, and rejections; rank by CU.
3. Report both the exact requested interval and expanded hourly bounds. DAX has no `DATETIME()` literal function; use `DATE(...) + TIME(...)`.

### Fixed-window health branch

Use this branch when the model exposes named windows such as `Usage Summary (Last 24 hours)` but no timestamped item/hour path.

1. Use the fixed-window table only when it matches the requested duration or the user accepts that model-defined scope.
2. Group by capacity and report average and peak CU percentage, minimum utilization, variance, delay/rejection seconds, and cumulative debt when those live columns exist.
3. Use the corresponding `Usage Operation (...)` table for hourly failures, cancellations, rejections, and throttling.
4. Identify a spike from peak-versus-average variation and absolute utilization. High CU alone is not pressure; check delay, rejection, throttling, and debt.
5. If the user requested another interval, report that exact attribution is unavailable in this model shape. Do not relabel the fixed window as the requested interval.

### Broader item-total fallback

If only a non-hourly table such as `Metrics By Item` returns item totals:

1. Query one selected capacity at a time and rank item name, kind, workspace, CU, operations, failures, rejections, and throttling.
2. Label the results **broader item-history leads** unless the model explicitly documents the same interval as the capacity result.
3. Never use a disagreement between fixed-window capacity totals and broader item totals as exact attribution.

Report the ranking, item kind, workspace, CU seconds, and each item's share of the returned total.

- Continue automatically only when one confirmed Warehouse or SQL analytics endpoint is a clear costly target in the same timeframe.
- If multiple SQL items materially contribute, ask which one to investigate first.
- If the highest-cost item is not SQL, report its actual kind. Do not attribute its CU to a lower-ranked SQL item. You may offer the highest-ranked SQL item as a separate candidate, but require confirmation.
- If only broader item-history leads are available, stop the spike-correlation workflow before opening a SQL endpoint. You may offer a separately scoped Query Insights investigation, but keep its timeframe and conclusions independent and do not attribute its SQL activity to the capacity spike.

## 3. Resolve Operation-Level Evidence When Available

After selecting the SQL item, inspect the Capacity Metrics semantic-model schema for an operation-level table that exposes:

- The selected item name or ID.
- A Capacity Metrics Operation Id.
- Operation start/end or timestamp.
- CU or duration evidence.

Do not assume a table name because Capacity Metrics model versions differ and some timepoint-detail tables can return no rows outside report drillthrough context. If the live schema exposes all required columns, generate a schema-valid DAX query filtered to the selected item and expanded hourly bounds and retrieve the top operations by CU. Preserve Capacity Metrics Operation Ids only as capacity-side evidence.

An empty drillthrough/timepoint result means operation evidence is **unavailable without report context**, not zero operations. Continue only for an item tied to the same interval; otherwise stop before SQL correlation. Never imply that item totals produced operation identifiers. Capture the Capacity Metrics window start/end for the Query Insights search.

## 4. Resolve the Correct SQL Endpoint Item

Confirm the selected item's kind and identity before querying it.

- Warehouse: pass its workspace and Warehouse item IDs to `fabric-sqlendpoint-execute_query`.
- Lakehouse SQL analytics endpoint: resolve and pass `properties.sqlEndpointProperties.id`, not the Lakehouse item ID.
- Other item kind: stop SQL correlation as not applicable.

For cross-database SQL, Query Insights records the request in the item used as the connection context. Query the item identified by Capacity Metrics rather than a referenced downstream database.

## 5. Find Expensive SQL Users and Queries

Set `capacity_window_start` and `capacity_window_end` from the Capacity Metrics evidence:

- For hourly item evidence, use the complete containing Capacity Metrics hour range.
- For operation/timepoint evidence, use the overall reported window containing the costly activity, not an Operation Id.
- Preserve the user's narrower requested interval separately when the Capacity Metrics range is expanded.

Aggregate the complete overlapping request set on the server before selecting details:

```sql
WITH CandidateRequests AS (
    SELECT *
    FROM queryinsights.exec_requests_history
    WHERE start_time < '<capacity-window-end-utc>'
      AND (end_time IS NULL OR end_time > '<capacity-window-start-utc>')
      AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
)
SELECT
    query_hash,
    COUNT(*) AS execution_count,
    SUM(CAST(allocated_cpu_time_ms AS bigint)) AS total_cpu_ms,
    SUM(CAST(total_elapsed_time_ms AS bigint)) AS total_elapsed_ms,
    SUM(data_scanned_remote_storage_mb) AS remote_scan_mb,
    SUM(data_scanned_memory_mb) AS memory_scan_mb,
    SUM(data_scanned_disk_mb) AS disk_scan_mb,
    SUM(CASE WHEN status IN ('Failed', 'Canceled') THEN 1 ELSE 0 END) AS non_successful_count,
    MIN(start_time) AS first_start_time,
    MAX(end_time) AS last_end_time,
    MAX(command) AS sample_command
FROM CandidateRequests
GROUP BY query_hash
ORDER BY total_cpu_ms DESC, total_elapsed_ms DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_CAPACITY_CORRELATION');
```

This aggregation includes every overlapping request, including rows without command text. After ranking query shapes, use the same bounded set and selected `query_hash` values for:

1. An attribution aggregate grouped by `query_hash`, `login_name`, `program_name`, `sql_pool_name`, and `statement_type`.
2. Individual executions containing `distributed_statement_id`, status, start/end, metrics, and complete SQL text.
3. Pressure intervals from `sql_pool_insights` overlapping the same Capacity Metrics window and exact `sql_pool_name`.

Compare execution count, total and per-run CPU, elapsed time, all scan tiers, and failed or canceled status. Separate high query cost from pressure, concurrency, repeated execution, and remote-scan behavior.

Query Insights `distributed_statement_id` remains useful for distinguishing and reporting Query Insights requests, but it must not be matched to a Capacity Metrics Operation Id.

Report the complete SQL text for the most expensive relevant statements, plus `login_name`, `program_name`, `sql_pool_name`, status, start/end, CPU, elapsed time, and scans. Distinguish direct Capacity Metrics item attribution from **best-effort SQL statement candidates within the Capacity Metrics time range**. Never call the statement-level correlation exact or authoritative.

## 6. Profile Historical Workload for Custom SQL Pools

Custom SQL pools are a preview, workspace-scoped feature. They classify requests by application/program name and cap the resource percentage available to each pool. This read-only skill recommends configurations but never changes them.

Resolve one history interval once. For a 30-day request, capture one `history_end` and derive `history_start`; apply both bounds to workload and pressure evidence. Bucket by day and count distinct pressure intervals so recurring contention is distinguishable from one incident:

```sql
DECLARE @history_end datetime2 = GETUTCDATE();
DECLARE @history_start datetime2 = DATEADD(DAY, -30, @history_end);

WITH StateEvents AS (
    SELECT
        [timestamp],
        sql_pool_name,
        is_pool_under_pressure,
        LEAD([timestamp], 1, @history_end) OVER (
            PARTITION BY sql_pool_name
            ORDER BY [timestamp]
        ) AS next_event_time
    FROM queryinsights.sql_pool_insights
    WHERE [timestamp] < @history_end
),
PressureIntervals AS (
    SELECT
        sql_pool_name,
        CASE WHEN [timestamp] < @history_start THEN @history_start ELSE [timestamp] END AS pressure_start,
        CASE WHEN next_event_time > @history_end THEN @history_end ELSE next_event_time END AS pressure_end
    FROM StateEvents
    WHERE is_pool_under_pressure = 1
      AND next_event_time > @history_start
      AND [timestamp] < @history_end
),
ExecutionRows AS (
    SELECT
        CAST(start_time AS date) AS workload_date,
        COALESCE(program_name, '<unknown>') AS program_name,
        COALESCE(sql_pool_name, '<unknown>') AS sql_pool_name,
        COALESCE(statement_type, '<unknown>') AS statement_type,
        query_hash,
        start_time,
        end_time,
        allocated_cpu_time_ms,
        total_elapsed_time_ms,
        data_scanned_remote_storage_mb,
        status
    FROM queryinsights.exec_requests_history
    WHERE start_time >= @history_start
      AND start_time < @history_end
      AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
),
WorkloadAgg AS (
    SELECT
        workload_date,
        program_name,
        sql_pool_name,
        statement_type,
        COUNT(*) AS execution_count,
        COUNT(DISTINCT query_hash) AS query_shapes,
        SUM(CAST(allocated_cpu_time_ms AS bigint)) AS total_cpu_ms,
        SUM(CAST(total_elapsed_time_ms AS bigint)) AS total_elapsed_ms,
        SUM(data_scanned_remote_storage_mb) AS remote_scan_mb,
        SUM(CASE WHEN status IN ('Failed', 'Canceled') THEN 1 ELSE 0 END) AS non_successful_count
    FROM ExecutionRows
    GROUP BY workload_date, program_name, sql_pool_name, statement_type
),
PressureOverlapAgg AS (
    SELECT
        e.workload_date,
        e.program_name,
        e.sql_pool_name,
        e.statement_type,
        COUNT(DISTINCT CONVERT(varchar(33), p.pressure_start, 126)) AS overlapping_pressure_intervals
    FROM ExecutionRows AS e
    INNER JOIN PressureIntervals AS p
      ON p.sql_pool_name = e.sql_pool_name
     AND e.start_time < p.pressure_end
     AND (e.end_time IS NULL OR e.end_time > p.pressure_start)
    GROUP BY e.workload_date, e.program_name, e.sql_pool_name, e.statement_type
)
SELECT
    w.*,
    COALESCE(p.overlapping_pressure_intervals, 0) AS overlapping_pressure_intervals
FROM WorkloadAgg AS w
LEFT JOIN PressureOverlapAgg AS p
  ON p.workload_date = w.workload_date
 AND p.program_name = w.program_name
 AND p.sql_pool_name = w.sql_pool_name
 AND p.statement_type = w.statement_type
ORDER BY w.workload_date DESC, w.total_cpu_ms DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_POOL_WORKLOAD_HISTORY');
```

Use the event-bounded pressure query in the `pool-pressure.md` leaf reference when interval-level evidence is also needed. Reuse the same resolved history bounds.

## 7. Recommend Pool Usage from Evidence

Retain autonomous workload management when pressure is absent or isolated, costly statements are one-offs, query tuning explains the incident, or `program_name` values are too unstable to classify.

Consider custom SQL pools when:

- Recurring workloads compete during repeated pressure intervals.
- Business-critical and ad-hoc workloads have stable, distinguishable `program_name` values.
- A high-consumption application needs a ceiling to reduce its effect on capacity throttling.
- Reporting, ingestion, and ad-hoc workloads need more isolation than the default SELECT/non-SELECT split.

Recommendation rules:

- Build classifiers from observed `program_name`; prefer exact matching for stable names and regex only for variable names.
- Warn that overlapping regex classifiers can route unpredictably and must be mutually exclusive.
- Recommend **Optimize for reads** only for a historically SELECT-dominant pool.
- Do not convert CU seconds or CPU milliseconds directly into a compute percentage. If suggesting an initial range, call it a hypothesis based on recurring share and pressure, preserve headroom, and require remeasurement.
- State that custom pools are preview, workspace-scoped, require Workspace Administrator permissions, and support up to eight pools.
- Separate pool isolation from query tuning, workload scheduling, or capacity scaling; custom pools cannot remove total demand.

References:

- <https://learn.microsoft.com/en-us/fabric/data-warehouse/custom-sql-pools>
- <https://learn.microsoft.com/en-us/fabric/data-warehouse/configure-custom-sql-pools-portal>
- <https://learn.microsoft.com/en-us/fabric/data-warehouse/workload-management>

## Response Contract

Use the operations-mode headings exactly:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

Always include the resolved capacity/model, requested UTC window, capacity evidence, correlation confidence, and timeframe limitations.

- When same-timeframe evidence establishes a costly SQL item, also include the selected SQL item, users, full query text, and historical pool evidence gathered from Query Insights.
- When only fixed-window health or broader non-timestamped item leads are available, state that exact item attribution is unavailable, omit SQL-user/query claims, and offer a separately scoped Query Insights follow-up.
- Put retention, refresh lag, timezone uncertainty, and confidence limits under **Evidence** or **Ruled out**.
- Make **Follow-ups** actions for the user on the investigated environment, not skill, PR, test, or documentation work. Name the target and validation signal: for example, confirm report timezone before log comparison; inspect Capacity Metrics operation detail for an unexplained interval; add and refresh a missing Warehouse source; or tune, reschedule, or pool an identified workload and remeasure pressure, CPU, scans, latency, and failures.
- If no action is justified, write `No immediate follow-up is required` and name the signal that should trigger reinvestigation.
