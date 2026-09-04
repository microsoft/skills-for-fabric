<!-- Leaf reference linked directly from sqldw-cli/SKILL.md. -->

# Failed and Canceled Query Analysis

Use this workflow for failed-query, canceled-query, error-code, and recurring non-successful request investigations. All diagnostics are read-only and execute through the SQL Endpoint MCP.

## Contents

- [Response contract](#response-contract)
- [Time range](#time-range)
- [Failure and cancellation summary](#failure-and-cancellation-summary)
- [Error-code evidence](#error-code-evidence)
- [Recurring patterns](#recurring-patterns)
- [Individual requests](#individual-requests)
- [Interpretation rules](#interpretation-rules)

## Response contract

Return exactly:

```text
## Diagnosis
## Evidence
## Ruled out
## Recommendations
## Follow-ups
```

Every figure must cite `queryinsights.exec_requests_history` or `sys.messages`. Zero rows is a valid healthy result.

## Time range

Use the user's requested UTC `[start, end)` interval. Default to the last 24 hours only when no range is supplied. Query Insights retains 30 days and can lag by 15 minutes.

The templates below show the maximum 30-day retained interval. Replace both anchored bounds for any explicit user interval; when none is supplied, change `@window_start` to `DATEADD(HOUR, -24, @window_end)`.

## Failure and cancellation summary

```sql
DECLARE @window_end datetime2 = GETUTCDATE();
DECLARE @window_start datetime2 = DATEADD(DAY, -30, @window_end);

WITH non_successful AS (
    SELECT
        start_time,
        status,
        error_code,
        COALESCE(login_name, 'Unknown User') AS login_name,
        CASE
            WHEN status = 'Canceled' THEN 'Canceled'
            WHEN error_code IN (24556, 24706) THEN 'Transaction conflict'
            WHEN error_code IN (2601, 2627, 547) THEN 'Constraint or data integrity'
            WHEN error_code IN (511, 611, 8152, 2628, 8115, 8134) THEN 'Data type or row shape'
            WHEN error_code IN (102, 156, 207, 208, 2812) THEN 'SQL authoring or schema'
            WHEN error_code IN (229, 916, 18456) THEN 'Access or authentication'
            ELSE 'Other or unclassified'
        END AS category
    FROM queryinsights.exec_requests_history
    WHERE status IN ('Failed', 'Canceled')
      AND start_time >= @window_start
      AND start_time < @window_end
)
SELECT
    COALESCE(SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END), 0) AS failed_queries,
    COALESCE(SUM(CASE WHEN status = 'Canceled' THEN 1 ELSE 0 END), 0) AS canceled_queries,
    COUNT(*) AS non_successful_queries,
    COUNT(DISTINCT login_name) AS affected_users,
    MIN(start_time) AS first_non_successful_time,
    MAX(start_time) AS latest_non_successful_time
FROM non_successful
OPTION (LABEL = 'AGENTCLI_MONITOR_FAILURE_SUMMARY');
```

If the combined count is zero, report `No failed or canceled queries · <window>` and stop.

## Error-code evidence

Rank failures and cancellations separately:

```sql
DECLARE @window_end datetime2 = GETUTCDATE();
DECLARE @window_start datetime2 = DATEADD(DAY, -30, @window_end);

SELECT TOP 20
    status,
    error_code,
    COUNT(*) AS request_count,
    COUNT(DISTINCT COALESCE(login_name, 'Unknown User')) AS affected_users,
    COUNT(DISTINCT query_hash) AS affected_query_shapes,
    MIN(start_time) AS first_seen_utc,
    MAX(start_time) AS last_seen_utc
FROM queryinsights.exec_requests_history
WHERE status IN ('Failed', 'Canceled')
  AND start_time >= @window_start
  AND start_time < @window_end
GROUP BY status, error_code
ORDER BY request_count DESC, last_seen_utc DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_FAILURE_BUCKETS');
```

Resolve only error codes from `status = 'Failed'` through `sys.messages`:

```sql
SELECT
    message_id AS error_code,
    severity,
    is_event_logged,
    text AS error_message_template
FROM sys.messages
WHERE language_id = 1033
  AND message_id IN (<observed-failed-error-codes>)
ORDER BY message_id;
```

`sys.messages.text` is authoritative. If a code has no row, report `Description unavailable from sys.messages`; never invent a message. Keep cancellations separate because they may reflect user cancellation, timeout, or pressure without a resolvable engine error.

## Recurring patterns

```sql
DECLARE @window_end datetime2 = GETUTCDATE();
DECLARE @window_start datetime2 = DATEADD(DAY, -30, @window_end);

WITH affected_hashes AS (
    SELECT DISTINCT query_hash
    FROM queryinsights.exec_requests_history
    WHERE status IN ('Failed', 'Canceled')
      AND query_hash IS NOT NULL
      AND start_time >= @window_start
      AND start_time < @window_end
)
SELECT TOP 20
    e.query_hash,
    SUM(CASE WHEN e.status = 'Failed' THEN 1 ELSE 0 END) AS failed_runs,
    SUM(CASE WHEN e.status = 'Canceled' THEN 1 ELSE 0 END) AS canceled_runs,
    SUM(CASE WHEN e.status = 'Succeeded' THEN 1 ELSE 0 END) AS successful_runs,
    COUNT(DISTINCT CASE WHEN e.status IN ('Failed', 'Canceled') THEN COALESCE(e.login_name, 'Unknown User') END) AS affected_users,
    COUNT(DISTINCT CASE WHEN e.status IN ('Failed', 'Canceled') THEN COALESCE(e.program_name, 'Unknown Program') END) AS affected_programs,
    COUNT(DISTINCT CASE WHEN e.status IN ('Failed', 'Canceled') THEN COALESCE(e.sql_pool_name, 'Unknown Pool') END) AS affected_pools,
    MIN(CASE WHEN e.status IN ('Failed', 'Canceled') THEN e.start_time END) AS first_seen_utc,
    MAX(CASE WHEN e.status IN ('Failed', 'Canceled') THEN e.start_time END) AS last_seen_utc,
    LEFT(MAX(CASE WHEN e.status IN ('Failed', 'Canceled') THEN e.command END), 500) AS sample_command
FROM queryinsights.exec_requests_history AS e
INNER JOIN affected_hashes AS h ON e.query_hash = h.query_hash
WHERE e.start_time >= @window_start
  AND e.start_time < @window_end
GROUP BY e.query_hash
ORDER BY
    SUM(CASE WHEN e.status IN ('Failed', 'Canceled') THEN 1 ELSE 0 END) DESC,
    last_seen_utc DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_FAILURE_PATTERNS');
```

## Individual requests

```sql
DECLARE @window_end datetime2 = GETUTCDATE();
DECLARE @window_start datetime2 = DATEADD(DAY, -30, @window_end);

SELECT TOP 50
    distributed_statement_id,
    query_hash,
    status,
    error_code,
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
    command
FROM queryinsights.exec_requests_history
WHERE status IN ('Failed', 'Canceled')
  AND start_time >= @window_start
  AND start_time < @window_end
ORDER BY start_time DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_NON_SUCCESSFUL_RUNS');
```

## Interpretation rules

- Deterministic failures with no successful runs suggest authoring, schema, permission, or data issues.
- Cancellations require correlation with timestamps, pool pressure, and program/user evidence before assigning a cause.
- Pressure overlap is contributing evidence only when both time and `sql_pool_name` align.
- Query Insights supplies runtime metrics, not an operator-level actual plan. Analyze a plan only when the user provides one.
- Under **Ruled out**, say `Not evaluated` for any plausible cause that was not tested.
