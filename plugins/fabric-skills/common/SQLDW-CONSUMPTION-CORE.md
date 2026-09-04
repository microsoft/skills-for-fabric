# SQLDW-CONSUMPTION-CORE.md

> **Scope**: Read-only / consumption-oriented T-SQL patterns for **Lakehouse SQL analytics endpoints**, **Mirrored Database SQL analytics endpoints**, and **Fabric Data Warehouse (DW)**.
> This document is *language-agnostic* — no C#, Python, CLI, or SDK references. It covers T-SQL syntax, DDL for read-side objects, system views, security, performance, monitoring, and troubleshooting.

---

## Item-Type Capability Matrix

| Capability | Lakehouse SQLEP | Mirrored DB SQLEP | Warehouse (DW) |
|---|---|---|---|
| SELECT on auto-generated tables | ✅ | ✅ | ✅ |
| CREATE/ALTER/DROP **base tables** | ❌ (read-only) | ❌ (read-only) | ✅ |
| INSERT / UPDATE / DELETE on base tables | ❌ | ❌ | ✅ |
| CREATE VIEW | ✅ | ✅ | ✅ |
| CREATE FUNCTION (inline TVF, scalar¹) | ✅ | ✅ | ✅ |
| CREATE PROCEDURE | ✅ | ✅ | ✅ |
| CREATE SCHEMA | ✅ | ✅ | ✅ |
| Session-scoped #temp tables | ✅² | ✅² | ✅ |
| Cross-database queries (3-part names) | ✅ | ✅ | ✅ |
| GRANT / DENY / REVOKE (security) | ✅ | ✅ | ✅ |
| Row-Level Security (RLS) | ✅ | ✅ | ✅ |
| Column-Level Security (CLS) | ✅ | ✅ | ✅ |
| Dynamic Data Masking (DDM) | ✅ | ✅ | ✅ |
| Query Insights views | ✅ | ✅ | ✅ |
| DMVs (exec_requests, exec_sessions) | ✅ | ✅ | ✅ |
| TRUNCATE TABLE | ❌ | ❌ | ✅ |
| Data Clustering (CLUSTER BY) | ❌ | ❌ | ✅ (preview) |
| varchar(max) support | ❌ (8 KB truncation)³ | ✅ (post-Nov 2025) | ✅ (16 MB limit) |

¹ Scalar UDFs must be inlineable.
² Temp tables in SQL analytics endpoints follow the same syntax as in DW.
³ Lakehouse SQLEP maps Delta `string` → `varchar(8000)`. Mirrored items created after Nov 2025 get `varchar(max)`.

---

## Connection Fundamentals

### TDS Endpoint

All three item types expose a **TDS (Tabular Data Stream)** endpoint.

| Parameter | Value |
|---|---|
| **Server** | **(retrieve via API or passed by context)** |
| **Port** | 1433 (TCP, must be open outbound) |
| **Database** | Display name of the Warehouse/Lakehouse (NOT the FQDN) |
| **Authentication** | Microsoft Entra ID only (no SQL auth) |
| **Encryption** | Required (`Encrypt=Yes`) |
| **Token audience** | `https://database.windows.net/.default` |

**Critical system constraints**:

- Always specify the **database name** (warehouse or SQLEP name) as `Initial Catalog` or `Database` in the connection string. The FQDN alone is insufficient.
- **MARS (Multiple Active Result Sets) is not supported**. Remove `MultipleActiveResultSets` from connection strings or set it to `false`.
- Cross-database queries supported within the same workspace.

### System Token Size Limit

If a workspace contains many warehouses/SQLEPs, or the user belongs to many Entra groups, the system token can exceed limits, producing:

```
Couldn't complete the operation because we reached a system limit
```

**Mitigation**: Limit warehouses + SQLEPs to ≤ 40 per workspace.

---

## Supported T-SQL Surface Area (Consumption Focus)

### Querying

```sql
-- Basic SELECT
SELECT col1, col2 FROM dbo.MyTable WHERE col1 > 100;

-- CTEs (standard, sequential, nested)
WITH cte AS (
    SELECT col1, SUM(col2) AS total
    FROM dbo.FactSales
    GROUP BY col1
)
SELECT * FROM cte WHERE total > 1000;

-- Cross-database query (3-part naming)
SELECT a.*, b.CategoryName
FROM Lakehouse1.dbo.Sales AS a
INNER JOIN Warehouse1.dbo.DimCategory AS b
    ON a.CategoryID = b.CategoryID;

-- Aggregate functions, window functions, CASE, subqueries — all supported
SELECT
    ProductID,
    SaleDate,
    Amount,
    SUM(Amount) OVER (PARTITION BY ProductID ORDER BY SaleDate) AS RunningTotal
FROM dbo.Sales;
```

### Supported Query Features

- Standard and nested CTEs (nested CTEs in preview)
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG, LEAD, SUM/AVG/MIN/MAX OVER)
- CASE expressions
- Subqueries (correlated and non-correlated)
- UNION / UNION ALL / INTERSECT / EXCEPT
- EXISTS / NOT EXISTS
- TOP / OFFSET-FETCH
- CROSS APPLY / OUTER APPLY
- A subset of query and join hints
- FOR JSON (only as the last operator; not allowed inside subqueries)
- PIVOT / UNPIVOT
- COALESCE, NULLIF, IIF, CHOOSE

### NOT Supported (Consumption Context)

| Feature | Status |
|---|---|
| `FOR XML` | Not supported |
| `SET ROWCOUNT` | Not supported |
| `SET TRANSACTION ISOLATION LEVEL` | Not supported |
| Recursive CTEs | Not supported |
| `PREDICT` | Not supported |
| Materialized views | Not supported |
| `BULK LOAD` / `OPENROWSET` (from SQLEP) | Not in SQLEP; DW supports OPENROWSET for external files |
| `CREATE USER` | Not supported (users are auto-created on GRANT/DENY) |
| Multi-column statistics (manual) | Not supported |
| Triggers | Not supported |
| Schema/table names with `/` or `\` | Not allowed |

### Data Types

**Supported Types**

| Category | Types |
|---|---|
| Exact numeric | `bigint`, `int`, `smallint`, `bit`, `decimal`/`numeric` |
| Approximate numeric | `float`, `real` |
| Date/Time | `date`, `time(n)`, `datetime2(n)` — precision limited to 6 fractional digits |
| Character | `char(n)`, `varchar(n)`, `varchar(max)` |
| Binary | `varbinary(n)`, `varbinary(max)` — max limit 16 MB in DW |
| Other | `uniqueidentifier` |

**NOT Supported Types — Use These Alternatives**

| Unsupported Type | Alternative | Notes |
|---|---|---|
| `nvarchar` / `nchar` | `varchar` / `char` | UTF-8 collation handles Unicode. May use more storage for multi-byte chars |
| `money` / `smallmoney` | `decimal(19,4)` | No monetary unit stored |
| `datetime` / `smalldatetime` | `datetime2(6)` | |
| `datetimeoffset` | `datetime2(6)` | Timezone offset is lost |
| `xml` | `varchar(max)` | XML structure and functions lost |
| `ntext` / `text` | `varchar(max)` | |
| `image` | `varbinary(max)` | |
| `geometry` / `geography` | `varbinary` (WKB) or `varchar` (WKT) | Cast as needed |
| `sql_variant` | No equivalent | |
| `hierarchyid` | No equivalent | |
| `tinyint` | `smallint` | |

**Delta-to-SQL Type Mapping (SQLEP Auto-Generated Tables)**

| Delta / Parquet Type | SQL Type in SQLEP |
|---|---|
| `string` | `varchar(8000)` in Lakehouse; `varchar(max)` in mirrored items (post-Nov 2025) |
| `int` / `long` | `int` / `bigint` |
| `double` / `float` | `float` / `real` |
| `boolean` | `bit` |
| `date` | `date` |
| `timestamp` | `datetime2(6)` |
| `decimal(p,s)` | `decimal(p,s)` |
| `binary` | `varbinary(8000)` |

**Collation**

- Default collation: `Latin1_General_100_BIN2_UTF8`
- Case-insensitive collation is available: `Latin1_General_100_CI_AS_KS_WS_SC_UTF8`
- Case-insensitive collation for SQL analytics endpoints is coming (announced Jul 2025)
- Row size limit: **8,060 bytes** per row (same as SQL Server). Exceeding produces error 511 or 611.

**varchar(max) Gotcha — Cross-Item Joins**

When joining tables across items where one has `varchar(max)` and the other has `varchar(8000)` on the same column, results may differ due to data truncation on the 8000-byte side. Cast explicitly to align:

```sql
SELECT *
FROM MirroredDB.dbo.Orders AS m
INNER JOIN Lakehouse1.dbo.Orders AS lh
    ON CAST(m.Description AS varchar(8000)) = lh.Description;
```

---

## Read-Side Objects You Can Create

Even on read-only SQL analytics endpoints, you can create views, functions, and stored procedures to build a consumption layer.

### Views

```sql
CREATE VIEW dbo.vw_ActiveCustomers
AS
SELECT CustomerID, CustomerName, Region
FROM dbo.Customers
WHERE IsActive = 1;
GO
```

### Inline Table-Valued Functions

```sql
CREATE FUNCTION dbo.fn_SalesByRegion(@Region varchar(50))
RETURNS TABLE
AS
RETURN
(
    SELECT ProductID, SUM(Amount) AS TotalSales
    FROM dbo.FactSales
    WHERE Region = @Region
    GROUP BY ProductID
);
GO

-- Usage
SELECT * FROM dbo.fn_SalesByRegion('EMEA');
```

### Scalar UDFs (Must Be Inlineable)

```sql
CREATE FUNCTION dbo.fn_FullName(@First varchar(50), @Last varchar(50))
RETURNS varchar(101)
AS
BEGIN
    RETURN @First + ' ' + @Last;
END;
GO
```

### Stored Procedures

```sql
CREATE PROCEDURE dbo.sp_TopProducts
    @TopN int = 10
AS
BEGIN
    SELECT TOP(@TopN) ProductID, SUM(Amount) AS Revenue
    FROM dbo.FactSales
    GROUP BY ProductID
    ORDER BY Revenue DESC;
END;
GO
```

On SQL analytics endpoints (Lakehouse, Mirrored DB), procedures are read-only — they cannot INSERT/UPDATE/DELETE base tables.

---

## Temporary Tables

### Two Types

| Type | Default? | Backed By | Max Size | INSERT INTO ... SELECT | Distribution |
|---|---|---|---|---|---|
| Non-distributed `#temp` | ✅ Yes (default) | MDF | Limited | ❌ Not supported | N/A |
| Distributed `#temp` | Must request | Parquet | Unlimited | ✅ Supported | ROUND_ROBIN |

### Syntax

```sql
-- Non-distributed (default)
CREATE TABLE #staging (
    ID int,
    Name varchar(100)
);

-- Distributed (preferred for large data, DML compatibility)
CREATE TABLE #staging_dist (
    ID int,
    Name varchar(100)
)
WITH (DISTRIBUTION = ROUND_ROBIN);

-- CTAS into distributed temp table
CREATE TABLE #results
WITH (DISTRIBUTION = ROUND_ROBIN)
AS
SELECT ProductID, SUM(Quantity) AS TotalQty
FROM dbo.FactSales
GROUP BY ProductID;
```

### Temp Table Guidelines

- **Prefer distributed temp tables** for consumption queries that stage intermediate results. They fully align with warehouse user tables.
- Non-distributed temp tables exist for tool compatibility (SSMS uses them internally).
- `INSERT INTO #temp SELECT ...` is **only supported for distributed temp tables**.
- Global temp tables (`##`) are **not supported**.
- Views cannot be created on temp tables.
- Temp tables are session-scoped — auto-dropped on disconnect.
- No explicit indexes on temp tables.

---

## Cross-Database Queries

A major consumption pattern: joining data across Lakehouses, Mirrored DBs, and Warehouses within the **same workspace**.

### Three-Part Naming

```sql
-- Pattern: [DatabaseName].[SchemaName].[ObjectName]
SELECT
    s.OrderID,
    s.Amount,
    c.CustomerName
FROM SalesWarehouse.dbo.Orders AS s
INNER JOIN CRMLakehouse.dbo.Customers AS c
    ON s.CustomerID = c.CustomerID;
```

### Rules and Limitations

- All items must be in the **same workspace**.
- All items must be in the **same region**.
- The query runs in the context of the item you are connected to. Query Insights records it in that item's `queryinsights` schema.
- INSERT across databases is supported only from DW (e.g., `INSERT INTO MyWarehouse.dbo.T SELECT * FROM MyLakehouse.dbo.T`).
- Cross-database views are allowed:

```sql
CREATE VIEW dbo.vw_UnifiedSales
AS
SELECT 'Warehouse' AS Source, OrderID, Amount FROM SalesWarehouse.dbo.Orders
UNION ALL
SELECT 'Lakehouse' AS Source, OrderID, Amount FROM SalesLakehouse.dbo.Orders;
GO
```

---

## Security for Consumption

### Permission Model Overview

Fabric uses a layered security model:

1. **Workspace roles** (Admin, Member, Contributor, Viewer) — broadest scope
2. **Item-level permissions** (Read, ReadData, ReadAll) — per-item sharing
3. **SQL granular permissions** (GRANT/DENY/REVOKE) — finest grain

**Key principle**: Workspace roles Admin/Member/Contributor grant full data read. Use Viewer role + SQL granular permissions for least-privilege consumption access.

### Sharing and ReadData

When sharing a warehouse/SQLEP with a user:

- **No additional permissions selected** → user gets CONNECT only. Cannot read any tables until GRANT SELECT is issued via T-SQL.
- **"Read all data using SQL" (ReadData)** → equivalent to `db_datareader`. User can SELECT all tables/views.
- **"Read all data using Apache Spark" (ReadAll)** → grants OneLake file-level access. Does not affect SQL permissions.

Best practice for controlled consumption: share with no extra permissions, then use T-SQL GRANT for granular access.

### Object-Level Security (GRANT / DENY)

```sql
-- Grant SELECT on specific tables only
GRANT SELECT ON dbo.FactSales TO [analyst@contoso.com];
GRANT SELECT ON dbo.DimProduct TO [analyst@contoso.com];

-- Deny access to sensitive table
DENY SELECT ON dbo.EmployeeSalary TO [analyst@contoso.com];

-- Grant EXECUTE on a stored procedure
GRANT EXECUTE ON dbo.sp_TopProducts TO [analyst@contoso.com];
```

Users are auto-created on first GRANT/DENY — `CREATE USER` is not needed (nor supported).

### Column-Level Security (CLS)

```sql
-- Grant SELECT on only specific columns
GRANT SELECT ON dbo.Customers (CustomerID, CustomerName, Region) TO [viewer@contoso.com];

-- Or deny specific sensitive columns
DENY SELECT ON dbo.Customers (SSN, CreditCardNumber) TO [viewer@contoso.com];
```

Prefer assigning permissions to roles rather than individual users for manageability.

### Row-Level Security (RLS)

```sql
-- Step 1: Create a schema for security objects
CREATE SCHEMA rls;
GO

-- Step 2: Create a predicate function
CREATE FUNCTION rls.fn_securitypredicate(@SalesRep AS varchar(60))
RETURNS TABLE
WITH SCHEMABINDING
AS
    RETURN SELECT 1 AS result WHERE @SalesRep = USER_NAME()
        OR USER_NAME() = 'manager@contoso.com';
GO

-- Step 3: Create a security policy
CREATE SECURITY POLICY dbo.SalesFilter
ADD FILTER PREDICATE rls.fn_securitypredicate(SalesRep)
ON dbo.Sales
WITH (STATE = ON);
GO
```

**Important**: RLS/CLS is enforced on the SQL analytics endpoint only. Users with Spark/OneLake access (ReadAll) can bypass these controls. Ensure workspace roles and item permissions are set accordingly.

### Dynamic Data Masking (DDM)

```sql
-- Create table with masking (DW only — SQLEP tables are auto-generated)
CREATE TABLE dbo.Customers (
    CustomerID int NOT NULL,
    FullName varchar(100) MASKED WITH (FUNCTION = 'partial(1,"XXXXX",1)') NULL,
    Email varchar(100) MASKED WITH (FUNCTION = 'email()') NULL,
    Phone varchar(20) MASKED WITH (FUNCTION = 'default()') NULL,
    SSN varchar(11) MASKED WITH (FUNCTION = 'partial(0,"XXX-XX-",4)') NULL
);

-- Grant UNMASK to privileged user
GRANT UNMASK ON dbo.Customers TO [finance_team@contoso.com];
```

Workspace Admin/Member/Contributor roles see unmasked data by default. DDM primarily protects Viewer-role users who receive SQL-level grants.

### Security Do and Don't

| Do | Don't |
|---|---|
| Use Viewer role + SQL GRANT for consumers | Give Contributor/Member to report consumers |
| Use roles (CREATE ROLE) for permission management | GRANT to individual users at scale |
| Set RLS/CLS on SQLEP if any data is sensitive | Assume SQLEP security covers Spark/OneLake access |
| Test security by connecting as the target user | Rely on owner-testing (owners bypass RLS/CLS) |
| Use DDM for dev/test scenarios with real data shapes | Treat DDM as encryption — it is a viewing restriction only |
| Audit with queryinsights `login_name` column | Ignore the `login_name` field in monitoring views |

---

## Monitoring and Diagnostics

### Query Labels

Label your queries to enable tracking, diagnostics, and workload management.

```sql
SELECT ProductID, SUM(Amount)
FROM dbo.FactSales
WHERE SaleDate >= '2025-01-01'
GROUP BY ProductID
OPTION (LABEL = 'REPORT_MonthlySales_2025');
```

**Naming conventions**:

```
OPTION (LABEL = 'PROJECT_ModuleName_Description')
OPTION (LABEL = 'DASHBOARD_DailySales')
OPTION (LABEL = 'ADHOC_analyst_exploration')
```

Labels appear in `queryinsights.exec_requests_history.label` and can be used for filtering:

```sql
SELECT distributed_statement_id, label, total_elapsed_time_ms,
       allocated_cpu_time_ms, data_scanned_remote_storage_mb
FROM queryinsights.exec_requests_history
WHERE label LIKE 'REPORT_%'
ORDER BY total_elapsed_time_ms DESC;
```

### Dynamic Management Views (DMVs) — Live State

| DMV | Shows | Min Role |
|---|---|---|
| `sys.dm_exec_connections` | Active connections (session_id, client_address, protocol) | Admin only |
| `sys.dm_exec_sessions` | Authenticated sessions (login_name, login_time, status) | All roles (own sessions) |
| `sys.dm_exec_requests` | Active requests (command, start_time, total_elapsed_time, status) | All roles (own requests) |

**Identify long-running queries**:

```sql
SELECT
    request_id,
    session_id,
    command,
    start_time,
    total_elapsed_time,
    status
FROM sys.dm_exec_requests
WHERE status = 'running'
ORDER BY total_elapsed_time DESC;
```

**Find who is running the long query**:

```sql
SELECT login_name
FROM sys.dm_exec_sessions
WHERE session_id = <long_running_session_id>;
```

**Kill a runaway query** (Admin only):

```sql
KILL '<session_id>';
```

Only workspace Admin can execute KILL and query `sys.dm_exec_connections`.

### Query Insights — Historical Analytics (30-Day Retention)

Query Insights provides four views under the `queryinsights` schema:

| View | Purpose |
|---|---|
| `queryinsights.exec_requests_history` | Every completed query: status, duration, CPU, data scanned, cache hits, row counts |
| `queryinsights.exec_sessions_history` | Session history: login info, start/end times |
| `queryinsights.long_running_queries` | Aggregated: median vs. last-run time, avg/min/max execution times |
| `queryinsights.frequently_run_queries` | Run counts, execution times for recurring query shapes |

**Top 10 most expensive queries** (sort by `allocated_cpu_time_ms` or `data_scanned_remote_storage_mb`):

```sql
SELECT TOP 10
    distributed_statement_id, query_hash, label,
    total_elapsed_time_ms, allocated_cpu_time_ms,
    data_scanned_remote_storage_mb, result_cache_hit, command
FROM queryinsights.exec_requests_history
ORDER BY allocated_cpu_time_ms DESC;   -- or ORDER BY data_scanned_remote_storage_mb DESC
```

**Aggregate by query_hash** (find recurring expensive patterns):

```sql
SELECT query_hash, COUNT(*) AS runs,
    AVG(total_elapsed_time_ms) AS avg_ms, AVG(allocated_cpu_time_ms) AS avg_cpu_ms,
    SUM(data_scanned_remote_storage_mb) AS total_scanned_mb
FROM queryinsights.exec_requests_history
WHERE start_time >= DATEADD(DAY, -7, GETUTCDATE())
GROUP BY query_hash
ORDER BY total_scanned_mb DESC;
```

**Check result set cache status**: query `result_cache_hit` in `exec_requests_history` — `2` = cache hit, `1` = this execution created a cache entry, `0` = not applicable for cache creation or use.

### Query Activity & Capacity Metrics

- **Query Activity** (portal, Admin only): no-code view of running/historical queries. Warehouse context menu → "Query activity".
- **Capacity Metrics app** (AppSource): CU utilization data. `distributed_statement_id` correlates across `sys.dm_exec_requests`, `queryinsights.exec_requests_history`, and the app's Operation Id. Status values: `Success`, `InProgress`, `Cancelled`, `Failure`, `Invalid`, `Rejected`.

### Diagnostics Gotchas

- Query Insights data appears with **up to 15 minutes delay** after query completion.
- After creating a new warehouse, `queryinsights.exec_requests_history` may return "Invalid object name" — wait ~2 minutes.
- Query Insights shows only **user-context** queries; system queries are excluded.
- Query Insights retains **30 days** of data. For longer retention, archive to a warehouse table using `INSERT INTO ... SELECT FROM queryinsights.*`.
- Cross-database queries are recorded in the Query Insights of the item you are **connected to**, not the item being referenced.

---

## Performance: Best Practices and Troubleshooting

### Statistics

Statistics are **automatically maintained** by the Fabric engine for:
- Single-column histogram statistics
- Average column length statistics
- Table cardinality statistics

Manual statistics commands:
```sql
-- Create single-column histogram statistics
CREATE STATISTICS stat_SaleDate ON dbo.FactSales (SaleDate);

-- Update statistics
UPDATE STATISTICS dbo.FactSales (stat_SaleDate);

-- View statistics
DBCC SHOW_STATISTICS ('dbo.FactSales', 'stat_SaleDate');
```

**Gotcha**: If a SELECT within a transaction follows a large INSERT, and the transaction is rolled back, auto-generated statistics can be inaccurate. Manually `UPDATE STATISTICS` on affected columns after rollbacks.

### Result Set Caching (Preview)

Caches results of eligible queries; auto-invalidated when underlying data changes. Non-deterministic functions (`GETDATE()`, `NEWID()`) prevent caching.

**Check cache status**:
```sql
SELECT
    distributed_statement_id,
    result_cache_hit,
    command
FROM queryinsights.exec_requests_history
WHERE label = 'MY_REPORT_QUERY'
ORDER BY submit_time DESC;
```

`result_cache_hit = 2` means cache hit; `1` means this execution created a cache entry; `0` means the query was not applicable for cache creation or use.

### Data Clustering (DW Only — Preview)

Data Clustering physically organizes rows so that similar values in clustering columns are stored together, enabling file skipping (pruning).

```sql
-- Create clustered table via CTAS
CREATE TABLE dbo.FactSales_Clustered
WITH (CLUSTER BY (SaleDate, Region))
AS
SELECT * FROM dbo.FactSales;

-- Query benefits from clustering on WHERE predicates
SELECT SUM(Amount)
FROM dbo.FactSales_Clustered
WHERE SaleDate BETWEEN '2025-01-01' AND '2025-03-31'
  AND Region = 'EMEA'
OPTION (LABEL = 'PERF_Clustered_Test');
```

**Clustering column selection guidelines**:
- Choose columns frequently used in `WHERE` clauses (range predicates)
- Mid-to-high cardinality columns yield best results
- Maximum 4 columns
- Equality join conditions do NOT benefit from clustering
- Ingestion takes longer on clustered tables (the engine reorders data)

**Verify clustering metadata**:
```sql
SELECT
    t.name AS table_name,
    c.name AS column_name,
    ic.key_ordinal
FROM sys.index_columns AS ic
INNER JOIN sys.columns AS c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
INNER JOIN sys.tables AS t ON ic.object_id = t.object_id
WHERE ic.index_id > 0;
```

### Lakehouse-Specific Performance

For Lakehouse SQL analytics endpoints, the underlying Delta tables must be well-maintained:

- **Run OPTIMIZE regularly** on lakehouse tables (via Spark) to compact small files into larger ones (target 128 MB – 1 GB)
- **Run VACUUM** to remove unreferenced files
- **Use V-Order** write optimization (default in Fabric) — do not disable
- Avoid high-cardinality partition columns; aim for partitions ≥ 1 GB
- Apache Spark 3.5.0+ generates rowgroup-level stats for timestamp columns — upgrade runtime if filtering on timestamps is slow

**Metadata sync lag**: Normally < 1 minute. Increases with: many lakehouses per workspace, small-file fragmentation, large ETL change volume, or SQLEP idle > 15 min (sync halts; resumes on next query).

### Query Writing Best Practices

| Practice | Why |
|---|---|
| `SELECT` only needed columns | Reduces data scanned and network transfer |
| Filter early with `WHERE` | Pushes predicates to storage; enables file/rowgroup skipping |
| Avoid `SELECT *` | Scans all columns; wastes CUs |
| Use `TOP` / `OFFSET-FETCH` for exploration | Limits data returned for ad hoc queries |
| Use query labels (`OPTION (LABEL = ...)`) | Enables tracking and performance analysis |
| Prefer `EXISTS` over `IN` for large subqueries | Generally more efficient execution |
| Avoid unnecessary `DISTINCT` | Forces deduplication pass on entire result |
| Use appropriate data types in predicates | Avoid implicit conversions (e.g., comparing varchar to int) |
| Batch complex logic into views/procedures | Encapsulation, reuse, easier security management |
| Use `UNION ALL` instead of `UNION` when duplicates are acceptable | Skips deduplication sort |

### First-Query Latency ("Cold Start")

The first execution of a query against a Fabric DW or SQLEP can be slower than subsequent runs due to:
- Metadata loading and compilation
- Cache warming (data not yet in memory)

This is expected behavior. Subsequent runs of the same or similar queries benefit from cached metadata, compiled plans, and result set caching.

### Performance Troubleshooting Checklist

| Symptom | Investigation | Action |
|---|---|---|
| Query runs longer than expected | Check `queryinsights.exec_requests_history` for `total_elapsed_time_ms` and `data_scanned_remote_storage_mb` | Reduce columns selected; add WHERE predicates; check statistics |
| High `data_scanned_remote_storage_mb` | Query is scanning too many files | Optimize Delta tables (OPTIMIZE/VACUUM in Spark); consider data clustering (DW); improve WHERE predicates |
| `result_cache_hit = 0` on repeated queries | Query is not eligible for result-cache creation/use, or its inputs prevent reuse | Check eligibility; remove non-deterministic functions such as `GETDATE()` where appropriate; check whether underlying data changes between runs |
| Query rejected (status = `Rejected`) | Capacity resource limits reached | Reduce concurrent load; upgrade capacity SKU; stagger workloads |
| Token size limit error | Too many warehouses/SQLEPs in workspace or too many Entra groups | Reduce items to ≤ 40 per workspace; consolidate Entra group memberships |

---

## REST API: Refresh SQL Endpoint Metadata

This is the one control-plane API specific to SQLEP consumption not covered in COMMON-CORE.md/COMMON-CLI.md. It forces an on-demand metadata sync for the SQL analytics endpoint.

### Endpoint

```
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/sqlEndpoints/{sqlEndpointId}/refreshMetadata
```

### Request

**Headers**:
```
Authorization: Bearer <fabric_api_token>
Content-Type: application/json
```

**Body** (optional):
```json
{
  "timeout": {
    "timeUnit": "Minutes",
    "value": 2
  }
}
```

### Responses

| Code | Meaning |
|---|---|
| `200 OK` | Sync completed. Body contains per-table sync status. |
| `202 Accepted` | Long-running operation started. Poll `Location` header URL. |

**200 Response**: JSON with `value` array of objects, each containing `tableName`, `status`, `startTime`, `endTime`, `lastSuccessfulSyncTime`. Status values: `Success` (synced new data), `NotRun` (no changes detected), `Failed`.

### When to Use

- After a pipeline/notebook writes to a lakehouse, before a downstream Power BI refresh
- When data appears in Lakehouse explorer but not in SQLEP
- As a step in CI/CD or automated testing workflows
- When sync lag exceeds tolerance (normally < 1 minute)

---

## System Catalog Queries (Metadata Exploration)

### List All Tables and Schemas

```sql
SELECT s.name AS schema_name, t.name AS table_name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON t.schema_id = s.schema_id
ORDER BY s.name, t.name;
```

### Column Metadata (with varchar(max) Detection)

```sql
SELECT
    OBJECT_SCHEMA_NAME(c.object_id) AS schema_name,
    OBJECT_NAME(c.object_id) AS table_name,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable
FROM sys.columns AS c
INNER JOIN sys.objects AS o ON c.object_id = o.object_id
WHERE o.type = 'U'
ORDER BY schema_name, table_name, c.column_id;
```

**Detect varchar(max) columns** (`max_length = -1`):
```sql
SELECT
    OBJECT_NAME(c.object_id) AS table_name,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length
FROM sys.columns AS c
INNER JOIN sys.objects AS o ON c.object_id = o.object_id
WHERE c.max_length = -1
  AND TYPE_NAME(c.user_type_id) IN ('varchar', 'varbinary');
```

### List Views, Functions, Procedures

```sql
SELECT s.name AS schema_name, o.name AS object_name, o.type_desc
FROM sys.objects AS o
INNER JOIN sys.schemas AS s ON o.schema_id = s.schema_id
WHERE o.type IN ('V', 'IF', 'FN', 'TF', 'P')  -- V=view, IF=inline TVF, FN=scalar, TF=TVF, P=proc
ORDER BY o.type_desc, s.name, o.name;
```

### Check Statistics

```sql
SELECT
    OBJECT_NAME(s.object_id) AS table_name,
    s.name AS stats_name,
    s.auto_created,
    s.user_created,
    sp.last_updated,
    sp.rows,
    sp.rows_sampled
FROM sys.stats AS s
CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) AS sp
WHERE OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
ORDER BY table_name, stats_name;
```

---

## Common Consumption Patterns (End-to-End Examples)

### Build a Reporting View Layer on a Lakehouse

```sql
-- Create schema + denormalized view for Power BI, then grant access
CREATE SCHEMA reporting;
GO
CREATE VIEW reporting.vw_SalesReport AS
SELECT s.OrderID, s.OrderDate, s.Quantity, s.Amount,
       p.ProductName, p.Category, c.CustomerName, c.Region
FROM dbo.FactSales AS s
INNER JOIN dbo.DimProduct AS p ON s.ProductID = p.ProductID
INNER JOIN dbo.DimCustomer AS c ON s.CustomerID = c.CustomerID;
GO
GRANT SELECT ON SCHEMA::reporting TO [powerbi_readers@contoso.com];
GO
```

### Cross-Database Analytics Across Lakehouse and Warehouse

```sql
-- Connected to Warehouse in same workspace
SELECT
    lh.EventDate,
    lh.EventType,
    lh.UserID,
    wh.UserName,
    wh.Department
FROM EventsLakehouse.dbo.UserEvents AS lh
INNER JOIN UsersWarehouse.dbo.DimUser AS wh
    ON lh.UserID = wh.UserID
WHERE lh.EventDate >= '2025-01-01'
OPTION (LABEL = 'XQUERY_EventsWithUsers');
```

### Exploratory Query with Temp Table Staging

```sql
-- Stage filtered data into distributed temp table
CREATE TABLE #recent_orders
WITH (DISTRIBUTION = ROUND_ROBIN)
AS
SELECT OrderID, CustomerID, Amount, OrderDate
FROM dbo.FactSales
WHERE OrderDate >= DATEADD(DAY, -30, GETUTCDATE());

-- Analyze staged data (multiple queries without rescanning)
SELECT CustomerID, COUNT(*) AS OrderCount, SUM(Amount) AS TotalSpend
FROM #recent_orders
GROUP BY CustomerID
ORDER BY TotalSpend DESC;

SELECT
    CAST(OrderDate AS date) AS Day,
    SUM(Amount) AS DailyRevenue
FROM #recent_orders
GROUP BY CAST(OrderDate AS date)
ORDER BY Day;

-- Cleanup (optional — auto-dropped on disconnect)
DROP TABLE #recent_orders;
```

---

## Gotchas and Troubleshooting Reference

| # | Issue | Cause | Resolution |
|---|---|---|---|
| 1 | `FOR XML` in subquery | Only allowed as last operator | Restructure query; use FOR JSON instead or move to outer query |
| 2 | Table not visible in SQLEP | Delta table outside `/tables` folder, or metadata sync lag | Move data to `/tables`; force Refresh (portal or REST API) |
| 3 | `uniqueidentifier` cross-join mismatch | Stored as binary in Delta; doesn't round-trip through Spark | Avoid cross-joining on uniqueidentifier between DW and Lakehouse |
| 4 | `INSERT INTO #temp SELECT` fails | Using non-distributed temp table | Add `WITH (DISTRIBUTION = ROUND_ROBIN)` to CREATE TABLE |
| 5 | Foreign key on SQLEP blocks schema updates | FK constraint prevents auto-schema changes | Drop the FK constraint to allow new Delta columns to sync |
| 6 | RLS bypassed for some users | User has Admin/Member/Contributor workspace role | Use Viewer role for consumers; test as the actual target user |
| 7 | DDM shows unmasked data | User has workspace Admin/Member/Contributor role, or UNMASK grant | Check role assignments; only Viewer-role users see masks (unless granted UNMASK) |
| 8 | `NVARCHAR` type not found | Not supported in Fabric | Use `varchar` with UTF-8 collation |
| 9 | Error 511 / 611 on INSERT | Row exceeds 8,060 byte limit | Reduce column sizes; split wide tables |
| 10 | `SET TRANSACTION ISOLATION LEVEL` fails | Not supported | Remove from scripts; Fabric uses snapshot isolation internally |
| 11 | Query killed after failover | Session-scoped #temp tables lost on front-end failover | Re-create temp tables; design for session transience |
| 12 | `queryinsights` views empty after warehouse creation | System views not yet generated | Wait ~2 minutes and refresh |
| 13 | Slow queries on Lakehouse SQLEP | Small-file problem; unoptimized Delta tables | Run `OPTIMIZE` and `VACUUM` on lakehouse tables via Spark |
| 14 | BIN2 collation causes unexpected string comparisons | Default collation is `Latin1_General_100_BIN2_UTF8` (case-sensitive, binary) | Use explicit `COLLATE` in comparisons if needed; or use CI collation on DW |
| 15 | `sp_showspaceused` not available | Not supported in Fabric | Use Capacity Metrics app for space and usage tracking |
| 16 | OPENROWSET on SQLEP | Not available on SQL analytics endpoints | Use Spark for file-level access; or use DW with OPENROWSET for external files |
| 17 | Cross-region connection fails | Source and target items in different regions | Ensure all items share the same region |
| 18 | Queries on Delta timestamp columns slow | Missing rowgroup-level stats (Spark runtime < 3.5.0) | Upgrade to Spark 3.5.0+; recreate and re-ingest table |

---

## Quick Reference: Consumption Capabilities by Scenario

| Scenario | Recommended Approach |
|---|---|
| Power BI report on lakehouse data | Connect to SQLEP; build views in `reporting` schema; use DirectQuery or Import |
| Ad hoc SQL exploration | Connect via SSMS 19+ or VS Code mssql extension; use TOP/OFFSET for pagination |
| Cross-source analytics | Use 3-part naming across items in same workspace |
| Secure data access for consumers | Share item with Read-only; use SQL GRANT/DENY for fine-grained access |
| Monitor report query performance | Use query labels + `queryinsights.exec_requests_history` |
| Identify expensive queries | Sort by `allocated_cpu_time_ms` or `data_scanned_remote_storage_mb` in Query Insights |
| Ensure fresh data in SQLEP | Call Refresh Metadata REST API after ETL pipeline completes |
| Stage intermediate results | Use distributed `#temp` tables with `ROUND_ROBIN` |
| Kill a runaway query | Admin: `KILL '<session_id>'` via DMV |
| Audit who accessed what | `queryinsights.exec_requests_history.login_name` + `exec_sessions_history` |
