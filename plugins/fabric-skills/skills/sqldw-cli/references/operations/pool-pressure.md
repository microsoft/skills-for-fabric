<!-- Leaf reference linked directly from sqldw-cli/SKILL.md. -->

# SQL Pool Pressure Analysis

Use this workflow to identify event-bounded SQL pool pressure intervals and correlate them with requests in the same pool.

## Contents

- [Response contract](#response-contract)
- [Event model and timeframe](#event-model-and-timeframe)
- [Build pressure intervals](#build-pressure-intervals)
- [Correlate requests](#correlate-requests)
- [Interpretation](#interpretation)

## Response contract

Return exactly:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

## Event model and timeframe

`queryinsights.sql_pool_insights` is event-based. A row records a pressure, capacity, or configuration state change; a pressure-on state remains effective until the next event for that pool or the requested window end. Logging pauses while the warehouse is inactive, so disclose gaps.

Use the requested UTC `[start, end)` interval. Default to the last 24 hours only when absent.

## Build pressure intervals

```sql
DECLARE @window_end datetime2 = GETUTCDATE();
DECLARE @window_start datetime2 = DATEADD(HOUR, -24, @window_end);

WITH StateEvents AS (
    SELECT
        [timestamp],
        sql_pool_name,
        max_resource_percentage,
        is_pool_under_pressure,
        current_workspace_capacity,
        LEAD([timestamp], 1, @window_end) OVER (
            PARTITION BY sql_pool_name
            ORDER BY [timestamp]
        ) AS next_event_time
    FROM queryinsights.sql_pool_insights
    WHERE [timestamp] < @window_end
),
PressureIntervals AS (
    SELECT
        sql_pool_name,
        CASE WHEN [timestamp] < @window_start THEN @window_start ELSE [timestamp] END AS window_start,
        CASE WHEN next_event_time > @window_end THEN @window_end ELSE next_event_time END AS window_end,
        max_resource_percentage,
        current_workspace_capacity
    FROM StateEvents
    WHERE is_pool_under_pressure = 1
      AND next_event_time > @window_start
      AND [timestamp] < @window_end
)
SELECT
    sql_pool_name,
    ROW_NUMBER() OVER (PARTITION BY sql_pool_name ORDER BY window_start) AS window_id,
    window_start,
    window_end,
    DATEDIFF(SECOND, window_start, window_end) AS duration_seconds,
    max_resource_percentage,
    current_workspace_capacity
FROM PressureIntervals
WHERE window_end > window_start
ORDER BY window_start DESC, sql_pool_name
OPTION (LABEL = 'AGENTCLI_MONITOR_PRESSURE_INTERVALS');
```

Do not filter to pressure-on rows before calculating `LEAD`; doing so drops the pressure-off event that closes the interval.

## Correlate requests

For each returned interval, substitute its exact pool and bounds:

```sql
SELECT TOP 20
    distributed_statement_id,
    query_hash,
    login_name,
    program_name,
    sql_pool_name,
    status,
    start_time,
    end_time,
    total_elapsed_time_ms,
    allocated_cpu_time_ms,
    data_scanned_remote_storage_mb,
    data_scanned_memory_mb,
    data_scanned_disk_mb,
    command
FROM queryinsights.exec_requests_history
WHERE sql_pool_name = '<sql-pool-name>'
  AND start_time < '<window-end-utc>'
  AND (end_time IS NULL OR end_time > '<window-start-utc>')
  AND command IS NOT NULL
  AND command NOT LIKE '%queryinsights%'
ORDER BY allocated_cpu_time_ms DESC, total_elapsed_time_ms DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_PRESSURE_OVERLAP');
```

## Interpretation

- Time overlap alone is correlation, not causation. Identify a likely contributor only when its CPU, scans, or elapsed time is material relative to other overlapping requests.
- Report interval count, duration, first/latest interval, affected pool, maximum resource percentage, and capacity SKU from `queryinsights.sql_pool_insights`.
- High elapsed with low CPU can support contention; high CPU or scans can support a workload contributor.
- Under **Ruled out**, address read pressure, write pressure, a single dominant query, cache behavior, and capacity change only when each was tested.
- No returned intervals means no SQL pool pressure was observed in the window, not that no other performance issue existed.
