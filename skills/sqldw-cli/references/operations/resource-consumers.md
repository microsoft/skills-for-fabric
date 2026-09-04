<!-- Leaf reference linked directly from sqldw-cli/SKILL.md. -->

# Resource Consumer Analysis

Use this workflow for top CPU consumers, workload concentration, regressions, repeated expensive queries, and cache interpretation.

## Contents

- [Response contract](#response-contract)
- [Measure concentration](#measure-concentration)
- [Compare with baseline](#compare-with-baseline)
- [Inspect individual executions](#inspect-individual-executions)
- [Cache interpretation](#cache-interpretation)
- [Recommendations](#recommendations)

## Response contract

Return exactly:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

## Measure concentration

```sql
WITH workload AS (
    SELECT
        query_hash,
        COALESCE(login_name, 'Unknown User') AS login_name,
        total_elapsed_time_ms,
        allocated_cpu_time_ms,
        data_scanned_remote_storage_mb,
        data_scanned_memory_mb,
        data_scanned_disk_mb,
        command
    FROM queryinsights.exec_requests_history
    WHERE status = 'Succeeded'
      AND query_hash IS NOT NULL
      AND is_distributed = 1
      AND start_time >= DATEADD(HOUR, -24, GETUTCDATE())
      AND command NOT LIKE '%queryinsights%'
      AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
),
shape_stats AS (
    SELECT
        query_hash,
        COUNT(*) AS execution_count,
        COUNT(DISTINCT login_name) AS user_count,
        SUM(allocated_cpu_time_ms) AS total_cpu_ms,
        AVG(CAST(allocated_cpu_time_ms AS float)) AS avg_cpu_ms,
        AVG(CAST(total_elapsed_time_ms AS float)) AS avg_elapsed_ms,
        SUM(CAST(data_scanned_remote_storage_mb AS float)) AS total_remote_mb,
        SUM(CAST(data_scanned_memory_mb + data_scanned_disk_mb AS float)) AS total_local_cache_mb,
        LEFT(MAX(command), 500) AS sample_command
    FROM workload
    GROUP BY query_hash
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY total_cpu_ms DESC, query_hash) AS cpu_rank,
        SUM(total_cpu_ms) OVER () AS workload_cpu_ms,
        SUM(total_cpu_ms) OVER (
            ORDER BY total_cpu_ms DESC, query_hash
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_cpu_ms
    FROM shape_stats
)
SELECT TOP 20
    cpu_rank,
    query_hash,
    execution_count,
    user_count,
    total_cpu_ms,
    CAST(100.0 * total_cpu_ms / NULLIF(workload_cpu_ms, 0) AS decimal(6,2)) AS cpu_share_pct,
    CAST(100.0 * cumulative_cpu_ms / NULLIF(workload_cpu_ms, 0) AS decimal(6,2)) AS cumulative_cpu_share_pct,
    avg_cpu_ms,
    avg_elapsed_ms,
    total_remote_mb,
    total_local_cache_mb,
    sample_command
FROM ranked
ORDER BY cpu_rank
OPTION (LABEL = 'AGENTCLI_MONITOR_RESOURCE_CONCENTRATION');
```

Select the smallest leading set reaching 50% cumulative CPU share, capped at five hashes. If five hashes do not reach 50%, report a distributed workload.

## Compare with baseline

Compare the selected current window with the immediately preceding representative baseline. Keep both windows explicit and non-overlapping. Classify a query hash as `new` when it has no baseline rows; calculate ratios only for nonzero baselines.

```sql
DECLARE @recent_end datetime2 = GETUTCDATE();
DECLARE @recent_start datetime2 = DATEADD(HOUR, -24, @recent_end);
DECLARE @baseline_start datetime2 = DATEADD(DAY, -7, @recent_start);

WITH recent AS (
    SELECT
        query_hash,
        COUNT(*) AS recent_runs,
        AVG(CAST(allocated_cpu_time_ms AS float)) AS recent_avg_cpu_ms,
        AVG(CAST(total_elapsed_time_ms AS float)) AS recent_avg_elapsed_ms,
        AVG(CAST(data_scanned_remote_storage_mb AS float)) AS recent_avg_remote_mb,
        SUM(allocated_cpu_time_ms) AS recent_total_cpu_ms
    FROM queryinsights.exec_requests_history
    WHERE status = 'Succeeded'
      AND query_hash IS NOT NULL
      AND is_distributed = 1
      AND start_time >= @recent_start
      AND start_time < @recent_end
      AND command NOT LIKE '%queryinsights%'
      AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
    GROUP BY query_hash
),
baseline AS (
    SELECT
        query_hash,
        COUNT(*) AS baseline_runs,
        AVG(CAST(allocated_cpu_time_ms AS float)) AS baseline_avg_cpu_ms,
        AVG(CAST(total_elapsed_time_ms AS float)) AS baseline_avg_elapsed_ms,
        AVG(CAST(data_scanned_remote_storage_mb AS float)) AS baseline_avg_remote_mb
    FROM queryinsights.exec_requests_history
    WHERE status = 'Succeeded'
      AND query_hash IS NOT NULL
      AND is_distributed = 1
      AND start_time >= @baseline_start
      AND start_time < @recent_start
      AND command NOT LIKE '%queryinsights%'
      AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
    GROUP BY query_hash
),
top_recent AS (
    SELECT TOP 10 *
    FROM recent
    ORDER BY recent_total_cpu_ms DESC
)
SELECT
    r.query_hash,
    r.recent_runs,
    b.baseline_runs,
    CAST(
        b.baseline_runs * 1.0 * DATEDIFF(SECOND, @recent_start, @recent_end)
        / NULLIF(DATEDIFF(SECOND, @baseline_start, @recent_start), 0)
        AS decimal(12,2)
    ) AS baseline_runs_scaled_to_recent_window,
    r.recent_avg_cpu_ms,
    b.baseline_avg_cpu_ms,
    CAST(r.recent_avg_cpu_ms / NULLIF(b.baseline_avg_cpu_ms, 0) AS decimal(12,2)) AS cpu_ratio_vs_baseline,
    r.recent_avg_elapsed_ms,
    b.baseline_avg_elapsed_ms,
    CAST(r.recent_avg_elapsed_ms / NULLIF(b.baseline_avg_elapsed_ms, 0) AS decimal(12,2)) AS elapsed_ratio_vs_baseline,
    r.recent_avg_remote_mb,
    b.baseline_avg_remote_mb,
    CASE WHEN b.query_hash IS NULL THEN 'new' ELSE 'existing' END AS baseline_status
FROM top_recent AS r
LEFT JOIN baseline AS b ON r.query_hash = b.query_hash
ORDER BY r.recent_total_cpu_ms DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_RESOURCE_BASELINE');
```

Report whether cost is driven by:

- More executions than `baseline_runs_scaled_to_recent_window`, with stable per-run cost.
- Higher per-run CPU, elapsed time, or remote scans.
- A one-off execution.
- Broad workload growth rather than a dominant query.

## Inspect individual executions

```sql
SELECT TOP 50
    distributed_statement_id,
    query_hash,
    login_name,
    program_name,
    sql_pool_name,
    start_time,
    end_time,
    total_elapsed_time_ms,
    allocated_cpu_time_ms,
    data_scanned_remote_storage_mb,
    data_scanned_memory_mb,
    data_scanned_disk_mb,
    result_cache_hit,
    command
FROM queryinsights.exec_requests_history
WHERE start_time >= DATEADD(HOUR, -24, GETUTCDATE())
  AND query_hash IN (<leading-query-hashes>)
ORDER BY allocated_cpu_time_ms DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_RESOURCE_RUNS');
```

## Cache interpretation

For repeated hashes, compare remote, memory, and disk scans. Guard zero-scan rows before calculating ratios:

- `result_cache_hit = 2`: historical result-cache hit.
- `result_cache_hit = 1`: historical result-cache entry creation.
- Total scanned MB = 0: no-scan.
- Remote share >80%: cold.
- Memory plus disk share >80%: warm.
- Otherwise: mixed.

Result set caching is currently disabled in Fabric Warehouse and SQL analytics endpoints due to a known issue. Use the fields for historical interpretation only. Do not recommend or execute `ALTER DATABASE ... SET RESULT_SET_CACHING` unless current Microsoft documentation confirms the limitation is resolved for the target.

## Recommendations

- High remote scans: reduce selected columns, improve predicates, and evaluate data layout or clustering.
- High CPU: simplify joins/aggregations and check repeated query shapes.
- High elapsed with low CPU: run the event-based pool-pressure workflow.
- Separate one-off query tuning from recurring workload or capacity recommendations.
- Never present Query Insights CPU share as total Fabric capacity CU share.
