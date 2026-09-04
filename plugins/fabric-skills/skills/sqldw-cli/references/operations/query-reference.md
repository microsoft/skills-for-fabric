# Query Reference — sqldw-cli operations mode

Detailed T-SQL queries for all monitoring and diagnostic analyses. All queries target the built-in `queryinsights` schema and system DMVs available in Fabric Data Warehouse.

> **Execution method:** All queries in this file are executed via the `fabric-sqlendpoint-execute_query` MCP tool:
> ```text
> fabric-sqlendpoint-execute_query(workspaceId, itemId, "<query from this file>")
> ```
> No `GO` separators or sqlcmd flags are needed — just pass the T-SQL text directly.

> **Data source:** `queryinsights` views retain 30 days of history. Data appears with up to 15 minutes delay after query completion.

---

## Performance Analysis Queries

> **MCP parameter substitution:** The queries below are **ready-to-use literals** with defaults already applied (e.g. `SELECT TOP 5`, `DATEADD(HOUR, -1, ...)`); the parameter table beneath each query shows which value to change. The MCP `fabric-sqlendpoint-execute_query` tool does not support sqlcmd-style external parameter substitution (no `-v`, `:setvar`, or separate parameter binding), so to parameterize a query either **edit the literal value in place** before calling **or declare the variables inside the batch** with ordinary T-SQL: `DECLARE @limit int = 5; DECLARE @hours int = 24;` at the start of the query. In-batch T-SQL variables are fully supported; only external/sqlcmd-style parameterization is not.
>
> In the parameter tables below, `N` is a **positive** integer and the leading minus is already part of the template — e.g. with the template `DATEADD(HOUR, -N, ...)` and `N = 24` you get `DATEADD(HOUR, -24, ...)`.

### Long-Running Queries Summary

**Purpose:** Find the slowest queries from `queryinsights.long_running_queries`.

```sql
-- Ready-to-use (defaults applied):
SELECT TOP 5
    last_run_command,
    last_run_total_elapsed_time_ms,
    median_total_elapsed_time_ms,
    number_of_runs
FROM queryinsights.long_running_queries
ORDER BY last_run_total_elapsed_time_ms DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 5 | Max queries to return (replace the number) |

**Return fields:**

| Field | Type | Description |
|-------|------|-------------|
| `last_run_command` | string | SQL query text |
| `last_run_total_elapsed_time_ms` | integer | Last execution time (ms) |
| `median_total_elapsed_time_ms` | integer | Median execution time across all runs (ms) |
| `number_of_runs` | integer | Total executions |

**Response formatting** — present each result as:
> Query '{first 50 chars}...' ran {number_of_runs} times, last took {last_run_total_elapsed_time_ms} ms (median {median_total_elapsed_time_ms} ms).

---

### Most Frequently Run Queries

**Purpose:** Rank the most-repeated queries from `queryinsights.frequently_run_queries` to spot hot paths worth caching or tuning.

```sql
-- Ready-to-use (defaults applied):
SELECT TOP 10
    query_hash,
    number_of_runs,
    avg_total_elapsed_time_ms,
    last_run_command
FROM queryinsights.frequently_run_queries
ORDER BY number_of_runs DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 10 | Max queries to return (replace the number) |

**Return fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query_hash` | varchar(200) | Hash identifying the normalized query shape |
| `number_of_runs` | integer | How many times the query ran |
| `avg_total_elapsed_time_ms` | integer | Average execution time across runs (ms) |
| `last_run_command` | string | SQL query text of the most recent run |

---

### Top Resource Consumers

**Purpose:** Identify CPU- and storage-heavy queries with performance recommendations.

```sql
-- Ready-to-use (defaults: top 5, last 1 hour):
SELECT TOP 5
    command,
    total_elapsed_time_ms,
    allocated_cpu_time_ms,
    data_scanned_remote_storage_mb,
    data_scanned_memory_mb,
    data_scanned_disk_mb
FROM queryinsights.exec_requests_history
WHERE start_time > DATEADD(HOUR, -1, GETUTCDATE())
ORDER BY allocated_cpu_time_ms DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 5 | Max results (replace the number) |
| `DATEADD(HOUR, -N, ...)` | 1 | Time window in hours (replace N) |

**Return fields:**

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | SQL query text |
| `total_elapsed_time_ms` | integer | Execution time (ms) |
| `allocated_cpu_time_ms` | integer | CPU time consumed (ms) |
| `data_scanned_remote_storage_mb` | float | Data from OneLake (cold) |
| `data_scanned_memory_mb` | float | Data from memory cache |
| `data_scanned_disk_mb` | float | Data from disk cache |

**Recommendation thresholds:**

| Condition | Recommendation |
|-----------|----------------|
| Remote scans > 1,000 MB | Review data layout; consider OPTIMIZE/clustering |
| CPU > 5,000,000 ms | Review query logic; reduce joins/aggregations |
| Elapsed > 300,000 ms (5 min) | Check joins, filters, and statistics |

---

### Top Users Insights

**Purpose:** Analyze user activity and query patterns using a ranked CTE.

```sql
-- Ready-to-use (defaults: top 5, last 24 hours, min 1 query):
WITH UserStats AS (
    SELECT
        COALESCE(login_name, 'Unknown User') AS user_name,
        COUNT(*) AS total_queries,
        AVG(total_elapsed_time_ms) AS avg_elapsed_time_ms,
        MAX(total_elapsed_time_ms) AS max_elapsed_time_ms,
        AVG(allocated_cpu_time_ms) AS avg_cpu_time_ms,
        SUM(allocated_cpu_time_ms) AS total_cpu_time_ms,
        AVG(data_scanned_remote_storage_mb + data_scanned_memory_mb + data_scanned_disk_mb) AS avg_data_scanned_mb,
        SUM(data_scanned_remote_storage_mb + data_scanned_memory_mb + data_scanned_disk_mb) AS total_data_scanned_mb,
        COUNT(CASE WHEN status = 'Failed' THEN 1 END) AS failed_queries,
        COUNT(DISTINCT CONVERT(DATE, start_time)) AS active_days,
        MIN(start_time) AS first_query_time,
        MAX(start_time) AS last_query_time
    FROM queryinsights.exec_requests_history
    WHERE start_time > DATEADD(HOUR, -24, GETUTCDATE())
    GROUP BY login_name
    HAVING COUNT(*) >= 1
),
RankedUsers AS (
    SELECT *,
        ROW_NUMBER() OVER (ORDER BY total_queries DESC, total_cpu_time_ms DESC) AS user_rank
    FROM UserStats
)
SELECT TOP 5
    user_name, total_queries, avg_elapsed_time_ms, max_elapsed_time_ms,
    avg_cpu_time_ms, total_cpu_time_ms, avg_data_scanned_mb,
    total_data_scanned_mb, failed_queries, active_days,
    first_query_time, last_query_time, user_rank
FROM RankedUsers
ORDER BY user_rank;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 5 | Max users to analyze (replace the number) |
| `DATEADD(HOUR, -N, ...)` | 24 | Time window in hours (replace N) |
| `HAVING COUNT(*) >= N` | 1 | Minimum query count for inclusion (replace N) |

**Return fields:**

| Field | Type | Description |
|-------|------|-------------|
| `user_name` | string | Login name (or 'Unknown User') |
| `total_queries` | integer | Total query count |
| `avg_elapsed_time_ms` | float | Average execution time |
| `max_elapsed_time_ms` | integer | Slowest single query |
| `avg_cpu_time_ms` | float | Average CPU per query |
| `total_cpu_time_ms` | bigint | Total CPU consumed |
| `avg_data_scanned_mb` | float | Avg data scanned per query |
| `total_data_scanned_mb` | float | Total data scanned |
| `failed_queries` | integer | Count of failed queries |
| `active_days` | integer | Distinct days with activity |
| `first_query_time` | datetime | First query timestamp |
| `last_query_time` | datetime | Most recent query timestamp |
| `user_rank` | integer | Rank by total_queries then CPU |

**Response formatting:**
- **User summary**: "{user_name} executed {total_queries} queries over {active_days} days, with {success_rate}% success rate."
- **Query pattern**: Classify as "Long-running analytical" (avg > 60s), "High-frequency operational" (>100/day), "Data-intensive" (avg > 1GB scanned), or "Mixed"
- **CPU intensity**: Low (<1s), Medium (1–10s), High (>10s avg)

---

### Recent Warehouse Activity

**Purpose:** Explain who is running which query shapes, through which applications and SQL pools, while excluding prior agent monitoring statements.

```sql
-- Ready-to-use (defaults: top 100, last 24 hours):
SELECT TOP 100
    start_time,
    login_name,
    program_name,
    statement_type,
    query_hash,
    sql_pool_name,
    status,
    total_elapsed_time_ms,
    allocated_cpu_time_ms,
    command
FROM queryinsights.exec_requests_history
WHERE start_time >= DATEADD(HOUR, -24, GETUTCDATE())
  AND command NOT LIKE '%queryinsights%'
  AND (label IS NULL OR label NOT LIKE 'AGENTCLI_MONITOR_%')
ORDER BY start_time DESC
OPTION (LABEL = 'AGENTCLI_MONITOR_ACTIVITY');
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 100 | Max requests to return (replace the number) |
| `DATEADD(HOUR, -N, ...)` | 24 | Time window in hours (replace N) |

Group the results by `login_name`, `program_name`, `statement_type`, `query_hash`, and `sql_pool_name`. Report execution count and resource concentration separately; do not identify a user or application as expensive from request count alone.

---

### Compare Recent vs Baseline

**Purpose:** Detect performance regressions by comparing recent window against historical baseline.

```sql
-- Ready-to-use (defaults: recent = 1 hour, baseline = 7 days back):
WITH recent AS (
    SELECT
        AVG(total_elapsed_time_ms) AS avg_recent_elapsed_ms,
        AVG(allocated_cpu_time_ms) AS avg_recent_cpu_ms,
        AVG(data_scanned_remote_storage_mb + data_scanned_memory_mb + data_scanned_disk_mb) AS avg_recent_data_scanned_mb
    FROM queryinsights.exec_requests_history
    WHERE start_time > DATEADD(HOUR, -1, GETUTCDATE())
      AND status = 'Succeeded'
),
baseline AS (
    SELECT
        AVG(total_elapsed_time_ms) AS avg_baseline_elapsed_ms,
        AVG(allocated_cpu_time_ms) AS avg_baseline_cpu_ms,
        AVG(data_scanned_remote_storage_mb + data_scanned_memory_mb + data_scanned_disk_mb) AS avg_baseline_data_scanned_mb
    FROM queryinsights.exec_requests_history
    WHERE start_time > DATEADD(DAY, -7, GETUTCDATE())
      AND start_time <= DATEADD(HOUR, -1, GETUTCDATE())
      AND status = 'Succeeded'
)
SELECT
    r.avg_recent_elapsed_ms,
    b.avg_baseline_elapsed_ms,
    r.avg_recent_cpu_ms,
    b.avg_baseline_cpu_ms,
    r.avg_recent_data_scanned_mb,
    b.avg_baseline_data_scanned_mb
FROM recent r
CROSS JOIN baseline b;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DATEADD(HOUR, -N, ...)` in recent CTE | 1 | Size of the recent analysis window (hours) |
| `DATEADD(DAY, -N, ...)` in baseline CTE | 7 | Days back for baseline comparison |

**Return fields:**

| Field | Description |
|-------|-------------|
| `avg_recent_elapsed_ms` | Recent window average elapsed time |
| `avg_baseline_elapsed_ms` | Baseline period average elapsed time |
| `avg_recent_cpu_ms` | Recent window average CPU time |
| `avg_baseline_cpu_ms` | Baseline period average CPU time |
| `avg_recent_data_scanned_mb` | Recent window average data scanned |
| `avg_baseline_data_scanned_mb` | Baseline period average data scanned |

**Response formatting** — compute percent change for each metric. Flag regressions > 20% with a warning.

---

### Recent Queries

**Purpose:** Retrieve the most recently executed queries.

```sql
-- Ready-to-use (default: 10 most recent):
SELECT TOP 10
    distributed_statement_id,
    login_name,
    command,
    start_time,
    total_elapsed_time_ms,
    status
FROM queryinsights.exec_requests_history
ORDER BY start_time DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 10 | Max queries to return (replace the number) |

---

### Search Query Patterns

**Purpose:** Search historical query patterns by table name, column, or keyword.

```sql
-- Ready-to-use (replace 'FactSales' with your search term):
SELECT TOP 10
    query_hash,
    COUNT(*) AS execution_count,
    AVG(total_elapsed_time_ms) AS avg_elapsed_ms,
    MIN(total_elapsed_time_ms) AS min_elapsed_ms,
    MAX(total_elapsed_time_ms) AS max_elapsed_ms,
    MAX(command) AS sample_command
FROM queryinsights.exec_requests_history
WHERE command LIKE '%FactSales%'
  AND command NOT LIKE '%queryinsights%'
GROUP BY query_hash
HAVING COUNT(*) >= 1
ORDER BY execution_count DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LIKE '%...%'` | _(required)_ | Replace `FactSales` with your search term |
| `HAVING COUNT(*) >= N` | 1 | Minimum pattern execution count |
| `TOP N` | 10 | Max patterns to return |

---

## Deep Diagnostics Queries

### Long-Running Query Analysis

**Purpose:** Identify queries exceeding a duration threshold for deeper investigation.

```sql
-- Ready-to-use (defaults: top 3, min 30 seconds):
SELECT TOP 3
    distributed_statement_id,
    command,
    total_elapsed_time_ms,
    allocated_cpu_time_ms,
    data_scanned_remote_storage_mb,
    data_scanned_memory_mb,
    result_cache_hit
FROM queryinsights.exec_requests_history
WHERE total_elapsed_time_ms >= 30000
  AND status = 'Succeeded'
ORDER BY total_elapsed_time_ms DESC;
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TOP N` | 3 | Max queries to analyze (replace the number) |
| `>= N` (WHERE clause) | 30000 | Minimum duration threshold in ms |

**Analysis checklist:**
- High `data_scanned_remote_storage_mb` → data layout issues
- High `allocated_cpu_time_ms` relative to elapsed → CPU-bound query
- High elapsed but low CPU → resource contention (check pressure windows)
- `result_cache_hit = 0` on repeated queries → no result-cache creation or use; check eligibility before calling it a miss

---

### Pressure Window Analysis

The event-based pressure query is now isolated in the directly indexed `references/operations/pool-pressure.md` leaf. Use that version; it calculates `LEAD` across all state events and matches overlapping requests by both interval and `sql_pool_name`.

---

### Cache Warmth Analysis

Use the directly indexed `references/operations/resource-consumers.md` leaf. It preserves the distinct meanings of `result_cache_hit = 1` (entry creation) and `result_cache_hit = 2` (cache hit), handles zero-scan rows before ratios, and records the current result-set-caching limitation.

---

### Cluster Key Recommendations

**Purpose:** Use a two-phase approach to identify tables that would benefit from data clustering.

**Phase 1 (data-volume)**: Aggregate query_hash groups to find the highest total data scanned.

```sql
SELECT
    query_hash,
    COUNT(*) AS exec_count,
    AVG(total_elapsed_time_ms) AS avg_elapsed_ms,
    AVG(allocated_cpu_time_ms) AS avg_cpu_ms,
    SUM(CAST(data_scanned_remote_storage_mb AS BIGINT)) AS total_remote_mb,
    AVG(data_scanned_remote_storage_mb) AS avg_remote_mb,
    MAX(command) AS sample_command
FROM queryinsights.exec_requests_history
WHERE status = 'Succeeded'
  AND command IS NOT NULL
  AND LEN(command) > 20
  AND start_time > DATEADD(HOUR, -168, GETUTCDATE())  -- 7 days
  AND command NOT LIKE '%queryinsights%'
  AND command NOT LIKE '%INFORMATION_SCHEMA%'
  AND command NOT LIKE '%sys.%'
GROUP BY query_hash
HAVING COUNT(*) >= 3
ORDER BY SUM(CAST(data_scanned_remote_storage_mb AS BIGINT)) DESC;
```

**Phase 2 (predicate-parsing)**: Examine `sample_command` for each hash to identify:
1. Tables in `FROM` / `JOIN` clauses (handles 3-part, 2-part, and 1-part names)
2. Columns in `WHERE` predicates (range filters, `IN`, `BETWEEN`, comparisons) — these are cluster key candidates
3. Score columns by: predicate usage count + cardinality + data type suitability

> **Important:** Equality `JOIN ON` conditions do **NOT** benefit from data clustering. Only `WHERE` filter predicates benefit.

**Cardinality guidance** — prefer mid-to-high cardinality columns:
- High cardinality (many distinct values, e.g., date, ID) → best candidates — enables efficient file skipping
- Low cardinality (few distinct values, e.g., gender, region) → poor candidates — limited pruning benefit

**Fallback heuristic** — when predicates can't be parsed, use column metadata:
- Date/time columns with mid-to-high cardinality → strong cluster key candidates (score 50)
- Columns ending in `_sk`, `_id`, `_key`, `Date`, `Time` → moderate candidates (score 30)
- Integer columns → weak candidates (score 15)

**Row count verification** — use `sys.partitions` with `COUNT` fallback:

```sql
-- Try sys.partitions first
SELECT SUM(p.rows) AS row_count
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0, 1)
WHERE s.name = 'dbo' AND t.name = 'FactSales';

-- If 0, use COUNT fallback
SELECT SUM(CAST(1 AS BIGINT)) AS rc FROM [dbo].[FactSales];
```

**Ranking**: Primary = total data scanned (I/O impact). Secondary = query_count * row_count.

**To apply clustering** — use CTAS (ALTER TABLE not supported in Fabric):

```sql
-- Step 1: Create clustered copy
CREATE TABLE dbo.FactSales_clustered
WITH (CLUSTER BY (SaleDate, Region))
AS SELECT * FROM dbo.FactSales;
```

**Post-CTAS table swap** — replace the original table using `sp_rename`:

```sql
-- Step 2: Rename original table
EXEC sp_rename 'dbo.FactSales', 'FactSales_old';

-- Step 3: Rename clustered table to original name
EXEC sp_rename 'dbo.FactSales_clustered', 'FactSales';

-- Step 4: Verify, then drop old table
-- DROP TABLE IF EXISTS dbo.FactSales_old;
```

**Verify clustering columns** after swap:

```sql
SELECT
    t.name AS table_name,
    c.name AS column_name,
    ic.data_clustering_ordinal AS clustering_ordinal
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.index_columns ic ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE ic.data_clustering_ordinal > 0 AND t.name = 'FactSales'
ORDER BY ic.data_clustering_ordinal;
```

> **Note:** Fabric does not support `ALTER TABLE SET DATA_CLUSTERING_KEY` or `RENAME OBJECT`. Always use CTAS with `WITH (CLUSTER BY (...))` and `sp_rename` for table swaps.
