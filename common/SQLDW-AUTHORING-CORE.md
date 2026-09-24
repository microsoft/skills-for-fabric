# SQLDW-AUTHORING-CORE.md

> **Scope**: Authoring T-SQL patterns — DDL, DML, ingestion, transactions, stored procedures, schema evolution, time travel, CI/CD — for **Fabric Data Warehouse (DW)** (primary), plus limited authoring on **Lakehouse** and **Mirrored Database SQL analytics endpoints**.
> Language-agnostic — no C#, Python, CLI, or SDK references.

---

## Authoring Capability Matrix

> **Relationship to SQLDW-CONSUMPTION-CORE.md**: Read-side topics (SELECT, data types, views/TVFs/procedures, temp tables, security, monitoring, performance) live in `SQLDW-CONSUMPTION-CORE.md`. This document covers authoring-exclusive topics: table DDL, DML, ingestion, transactions, stored-procedure patterns, schema evolution, IDENTITY columns, time travel/snapshots, source control/CI/CD, and authoring permissions.

| Capability | Lakehouse SQLEP | Mirrored DB SQLEP | Warehouse (DW) |
|---|---|---|---|
| CREATE TABLE / CTAS / SELECT INTO | ❌ | ❌ | ✅ |
| INSERT / UPDATE / DELETE | ❌ | ❌ | ✅ |
| MERGE (preview) | ❌ | ❌ | ✅ |
| TRUNCATE TABLE | ❌ | ❌ | ✅ |
| ALTER TABLE (limited) / DROP TABLE | ❌ | ❌ | ✅ |
| sp_rename (tables, columns) | ❌ | ❌ | ✅ |
| COPY INTO | ❌ | ❌ | ✅ |
| OPENROWSET | ✅ (read-only) | ✅ (read-only) | ✅ (read + ingest) |
| IDENTITY columns | ❌ | ❌ | ✅ (preview) |
| Constraints (PK, FK, UNIQUE) | ❌ | ❌ | ✅ (NOT ENFORCED only) |
| Transactions (BEGIN/COMMIT/ROLLBACK) | ❌ | ❌ | ✅ |
| Time travel (FOR TIMESTAMP AS OF) | ❌ | ❌ | ✅ |
| Warehouse snapshots | ❌ | ❌ | ✅ |
| CREATE VIEW / FUNCTION / PROCEDURE / SCHEMA | ✅ | ✅ | ✅ |
| Git integration / source control | ❌ | ❌ | ✅ (preview) |

**Summary**: Lakehouse and Mirrored DB SQL endpoints support authoring only for **programmability objects** (views, functions, procedures, schemas). All table-level DDL/DML is exclusive to Warehouse.

---

## Table DDL (DW Only)

### CREATE TABLE

```sql
CREATE TABLE dbo.FactSales (
    SaleID        bigint NOT NULL,
    ProductID     int NOT NULL,
    CustomerID    int NOT NULL,
    SaleDate      date NOT NULL,
    Amount        decimal(19,4) NOT NULL,
    Quantity      int NULL,
    Notes         varchar(500) NULL
);
```

**Rules**:
- Max 1,024 columns; table/column names max 128 chars; no `/` or `\` in schema/table names.
- 8,060-byte row limit (error 511/611 on violation).
- Default collation: `Latin1_General_100_BIN2_UTF8` (case-sensitive). Case-insensitive: `Latin1_General_100_CI_AS_KS_WS_SC_UTF8`.
- No default value constraints, no computed columns (use views instead).

### CREATE TABLE AS SELECT (CTAS)

CTAS is the **primary pattern** for creating and populating tables — fully parallel and most efficient.

```sql
CREATE TABLE dbo.FactSales_2024
AS
SELECT * FROM dbo.FactSales WHERE SaleDate >= '2024-01-01';

-- CTAS from external file
CREATE TABLE dbo.ExternalData
AS
SELECT * FROM OPENROWSET(
    BULK 'https://storage.dfs.core.windows.net/container/data.parquet'
) AS data;

-- CTAS with transformation and explicit types
CREATE TABLE dbo.MonthlySummary
AS
SELECT
    YEAR(SaleDate) AS SaleYear,
    MONTH(SaleDate) AS SaleMonth,
    ProductID,
    CAST(SUM(Amount) AS decimal(19,4)) AS TotalAmount,
    COUNT(*) AS TransactionCount
FROM dbo.FactSales
GROUP BY YEAR(SaleDate), MONTH(SaleDate), ProductID;
```

**CTAS rules (differs from Synapse)**:
- `WITH (DISTRIBUTION = ...)` — **not supported**; distribution is engine-managed.
- `CLUSTERED COLUMNSTORE INDEX` hints — **not supported**; indexing is automatic.
- `WITH (CLUSTER BY (...))` — **supported** (max 4 columns; preview).
- Explicit column definitions — **not allowed**; types inferred from SELECT.
- Variables in CTAS — **not allowed** (use `sp_executesql` to wrap).
- Use explicit `CAST()` to control inferred types.

### SELECT INTO

```sql
SELECT * INTO dbo.FactSales_Backup
FROM dbo.FactSales WHERE SaleDate < '2023-01-01';
```

Functionally similar to CTAS but without `WITH` clause options (no CLUSTER BY).

### ALTER TABLE (Limited Subset)

```sql
-- ADD nullable columns
ALTER TABLE dbo.FactSales ADD DiscountPct decimal(5,2) NULL;

-- DROP COLUMN (April 2025+)
ALTER TABLE dbo.FactSales DROP COLUMN Comments;

-- ADD constraints (NOT ENFORCED only)
ALTER TABLE dbo.FactSales
ADD CONSTRAINT PK_FactSales PRIMARY KEY NONCLUSTERED (SaleID) NOT ENFORCED;

ALTER TABLE dbo.FactSales
ADD CONSTRAINT FK_FactSales_Product
FOREIGN KEY (ProductID) REFERENCES dbo.DimProduct (ProductID) NOT ENFORCED;

-- DROP constraints
ALTER TABLE dbo.FactSales DROP CONSTRAINT FK_FactSales_Product;
```

**Not supported**: ALTER COLUMN (change type/nullability), ADD NOT NULL columns, ADD columns with defaults, enforced constraints.

### sp_rename

```sql
EXEC sp_rename 'dbo.FactSales_Old', 'FactSales_Archive';           -- table
EXEC sp_rename 'dbo.FactSales.OldCol', 'NewCol', 'COLUMN';         -- column (April 2025+)
EXEC sp_rename 'dbo.sp_OldName', 'sp_NewName';                     -- procedure/view/function
```

Works for tables, columns, procedures, views, and functions on DW. **Not available** on Lakehouse/Mirrored DB SQL endpoints.

### DROP TABLE

```sql
DROP TABLE IF EXISTS dbo.StagingTable;
```

**Warning**: Dropping a table destroys its time-travel history. Use `TRUNCATE TABLE` instead of drop + recreate to preserve history.

### Constraints Reference

| Constraint | Supported? | Requirement |
|---|---|---|
| PRIMARY KEY | ✅ | NONCLUSTERED + NOT ENFORCED |
| UNIQUE | ✅ | NONCLUSTERED + NOT ENFORCED |
| FOREIGN KEY | ✅ | NOT ENFORCED |
| DEFAULT / CHECK | ❌ | — |
| NOT NULL | ✅ | CREATE TABLE only (not via ALTER) |

Constraints are **metadata-only** (NOT ENFORCED) — the engine does not enforce them at DML time. They serve as optimizer hints and BI tool metadata (Power BI uses FK relationships for automatic relationship detection).

### Schema Evolution

| Operation | Syntax | Notes |
|---|---|---|
| Add nullable column | `ALTER TABLE t ADD col type NULL` | Fast metadata operation |
| Drop column | `ALTER TABLE t DROP COLUMN col` | April 2025+; metadata-only |
| Rename column | `EXEC sp_rename 't.old', 'new', 'COLUMN'` | April 2025+ |
| Rename table | `EXEC sp_rename 'old', 'new'` | |
| Change type / nullability / Add NOT NULL | Not supported | CTAS workaround below |

**CTAS Workaround for Unsupported Schema Changes**:

```sql
-- Step 1: Create new table with desired schema
CREATE TABLE dbo.FactSales_V2 AS
SELECT SaleID, ProductID, CustomerID, SaleDate,
       CAST(Amount AS decimal(19,2)) AS Amount,   -- changed type
       ISNULL(Quantity, 0) AS Quantity             -- now non-nullable
FROM dbo.FactSales;

-- Step 2: Swap
DROP TABLE dbo.FactSales;
EXEC sp_rename 'dbo.FactSales_V2', 'FactSales';

-- Step 3: Re-add constraints and security (GRANT/DENY)
ALTER TABLE dbo.FactSales
ADD CONSTRAINT PK_FactSales PRIMARY KEY NONCLUSTERED (SaleID) NOT ENFORCED;
```

**Warning**: Loses time-travel history and security on the original table.

### IDENTITY Columns (Preview)

IDENTITY columns generate automatic surrogate keys.

```sql
CREATE TABLE dbo.DimProduct (
    ProductKey bigint IDENTITY,
    ProductName varchar(100),
    Category varchar(50)
);

-- Insert without specifying IDENTITY column
INSERT INTO dbo.DimProduct (ProductName, Category) VALUES ('Widget', 'Electronics');
```

**Rules**:
- Data type must be `bigint`. Cannot be added via ALTER TABLE — use CTAS.
- Values are not guaranteed sequential (gaps after failed transactions). Use for surrogate keys only.
- `SET IDENTITY_INSERT` is supported for explicit value insertion.
- CTAS and SELECT INTO preserve the IDENTITY property.

---

## DML Operations (DW Only)

### INSERT

```sql
-- INSERT ... SELECT (preferred for bulk)
INSERT INTO dbo.FactSales (SaleID, ProductID, CustomerID, SaleDate, Amount)
SELECT SaleID, ProductID, CustomerID, SaleDate, Amount
FROM dbo.StagingTable
WHERE IsValid = 1;

-- INSERT from cross-database source
INSERT INTO dbo.DimCustomer (CustomerID, CustomerName)
SELECT CustomerID, CustomerName
FROM CRMLakehouse.dbo.Customers;
```

**Critical**: Avoid singleton `INSERT ... VALUES` for bulk loading — each creates a separate Parquet file, causing fragmentation and poor performance. Use `INSERT ... SELECT`, CTAS, or `COPY INTO`.

**Remediation** for existing fragmentation: `CREATE TABLE dbo.T_Clean AS SELECT * FROM dbo.T; DROP TABLE dbo.T; EXEC sp_rename 'dbo.T_Clean', 'T';`

### UPDATE

```sql
UPDATE dbo.FactSales SET Amount = Amount * 1.10
WHERE SaleDate >= '2025-01-01' AND ProductID = 42;

-- UPDATE with JOIN
UPDATE fs SET fs.Category = dp.Category
FROM dbo.FactSales AS fs
INNER JOIN dbo.DimProduct AS dp ON fs.ProductID = dp.ProductID
WHERE fs.Category IS NULL;
```

### DELETE

```sql
DELETE FROM dbo.FactSales WHERE SaleDate < '2020-01-01';

-- DELETE with JOIN
DELETE fs FROM dbo.FactSales AS fs
INNER JOIN dbo.DeletedOrders AS d ON fs.SaleID = d.SaleID;
```

### TRUNCATE TABLE

```sql
TRUNCATE TABLE dbo.StagingTable;
```

Removes all rows but preserves table structure, constraints, and time-travel history. Faster than `DELETE FROM table` (metadata operation).

### MERGE (Preview)

```sql
MERGE INTO dbo.DimProduct AS target
USING dbo.StagingProduct AS source
ON target.ProductID = source.ProductID
WHEN MATCHED THEN
    UPDATE SET target.ProductName = source.ProductName,
               target.Category = source.Category,
               target.Price = source.Price
WHEN NOT MATCHED THEN
    INSERT (ProductID, ProductName, Category, Price)
    VALUES (source.ProductID, source.ProductName, source.Category, source.Price);
```

**MERGE gotchas**: Preview feature — test before production. Even append-only MERGE triggers **table-level** write-write conflict detection. For production workloads with concurrency, prefer the DELETE + INSERT pattern (see Upsert Without MERGE).

---

## Data Ingestion (DW Only)

### COPY INTO (Recommended for External Files)

Highest-throughput method for loading from external storage.

```sql
-- Parquet (auto-schema inference)
COPY INTO dbo.FactSales
FROM 'https://storageaccount.dfs.core.windows.net/container/sales/*.parquet'
WITH (FILE_TYPE = 'PARQUET');

-- CSV with options
COPY INTO dbo.FactSales
FROM 'https://storageaccount.dfs.core.windows.net/container/sales/*.csv'
WITH (
    FILE_TYPE = 'CSV', FIRSTROW = 2,
    FIELDTERMINATOR = ',', ROWTERMINATOR = '\n', FIELDQUOTE = '"'
);

-- OneLake source (preview)
COPY INTO dbo.FactSales
FROM 'abfss://<workspaceID>@onelake.dfs.fabric.microsoft.com/<lakehouseID>/Files/sales/'
WITH (FILE_TYPE = 'PARQUET');
```

**Rules**:
- Formats: **PARQUET**, **CSV**. Sources: **ADLS Gen2**, **Azure Blob Storage**, **OneLake** (preview).
- Authenticates as the executing Entra ID user by default. Alternatives: SAS token in CREDENTIAL clause, or workspace identity for firewall-protected storage.
- Files ≥ 4 MB for optimal performance. ADLS Gen2 preferred over legacy Blob Storage.

### OPENROWSET (Read + Transform + Ingest)

Reads external files as rows, enabling transformation before ingestion.

```sql
-- Browse file content
SELECT TOP 10 * FROM OPENROWSET(
    BULK 'https://storage.dfs.core.windows.net/container/data.parquet'
) AS data;

-- Ingest with transformation via CTAS
CREATE TABLE dbo.CleanData AS
SELECT id, UPPER(country) AS Country,
       CAST(amount AS decimal(19,4)) AS Amount,
       CAST(sale_date AS date) AS SaleDate
FROM OPENROWSET(
    BULK 'https://storage.dfs.core.windows.net/container/raw/*.parquet'
) AS raw
WHERE amount > 0;

-- CSV with explicit schema
SELECT * FROM OPENROWSET(
    BULK 'https://storage.dfs.core.windows.net/container/data.csv',
    FORMAT = 'CSV', HEADER_ROW = TRUE
) WITH (
    id int, name varchar(100), amount decimal(19,4), created date
) AS data;

-- Wildcards and Hive-partitioned paths
SELECT * FROM OPENROWSET(
    BULK 'https://storage.dfs.core.windows.net/container/year=*/month=*/*.parquet'
) AS partitioned_data;
```

**Key details**:
- Formats: Parquet, CSV, TSV, JSONL. Available on DW (read + ingest) and SQL endpoints (read-only).
- Complex Parquet types (maps, lists) returned as JSON text — use JSON_VALUE/OPENJSON.
- Slower than materialized tables; ingest data for repeated access.

### Ingestion Method Comparison

| Method | Best For | Throughput | Transforms | Source |
|---|---|---|---|---|
| COPY INTO | Bulk loads from storage | Highest | No | ADLS Gen2, Blob, OneLake |
| OPENROWSET + INSERT/CTAS | Load with transformations | Medium | Yes (T-SQL) | ADLS Gen2, Blob, OneLake |
| INSERT...SELECT / CTAS (cross-DB) | Ingest from other Fabric items | Medium–High | Yes (T-SQL) | Lakehouse, Warehouse, Mirrored DB |
| Pipelines / Dataflows | Scheduled, multi-source ETL | Varies | Yes | 100+ connectors |

### V-Order and Automatic Optimization

All data ingested into Warehouse is automatically optimized with **V-Order** (write-time Parquet optimization for fast reads). Do not disable. Automatic **data compaction** merges small Parquet files in the background (asynchronous, not manually triggerable).

---

## Transactions (DW Only)

### Fundamentals

Fabric DW supports ACID transactions using **snapshot isolation exclusively** (`SET TRANSACTION ISOLATION LEVEL` is ignored).

```sql
BEGIN TRANSACTION;
    INSERT INTO dbo.FactSales (SaleID, ProductID, Amount, SaleDate)
    SELECT SaleID, ProductID, Amount, SaleDate FROM dbo.StagingTable;
    DELETE FROM dbo.StagingTable;
COMMIT TRANSACTION;
```

**Key behaviors**:
- Atomic: all succeed or all fail. Reads see a consistent snapshot from transaction start.
- DDL (CREATE TABLE) is allowed inside transactions.
- Cross-database transactions supported within the same workspace.
- Rollbacks are fast — revert to previous Parquet file versions (metadata operation).

### Error Handling

```sql
BEGIN TRY
    BEGIN TRANSACTION;
    TRUNCATE TABLE dbo.TargetTable;
    INSERT INTO dbo.TargetTable SELECT * FROM dbo.StagingClean;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    DECLARE @ErrorMsg varchar(4000) = ERROR_MESSAGE();
    RAISERROR(@ErrorMsg, 16, 1);
END CATCH;
```

### Write-Write Conflicts (Snapshot Isolation)

Conflicts are tracked at the **table level**, not row level. Two transactions touching the **same table** conflict even if modifying different rows.

| Scenario | Outcome |
|---|---|
| INSERT vs. INSERT (same table) | Usually safe (appends new Parquet files) |
| UPDATE/DELETE vs. UPDATE/DELETE | First committer wins; others fail (error 24556/24706) |
| MERGE vs. any DML | Always conflicts (even append-only MERGE) |
| DML vs. background compaction | Compaction can trigger conflicts if it commits first |

**Error**: `Snapshot isolation transaction aborted due to update conflict. You cannot use snapshot isolation to access table '...'` (error 24556 or 24706).

### Conflict Mitigation

```sql
-- Retry pattern for single-statement DML
DECLARE @retryCount int = 0, @maxRetries int = 3;
WHILE @retryCount < @maxRetries
BEGIN
    BEGIN TRY
        UPDATE dbo.FactSales SET Status = 'Processed' WHERE BatchID = @currentBatch;
        BREAK;
    END TRY
    BEGIN CATCH
        SET @retryCount += 1;
        IF @retryCount >= @maxRetries THROW;
        WAITFOR DELAY '00:00:02'; -- use exponential backoff in production
    END CATCH;
END;
```

**Strategies**: Serialize writes to the same table. Use INSERT-only patterns (append then reconcile). Keep transactions short. For large-scale updates, prefer CTAS + table swap over in-place UPDATE.

### Transaction Limitations

| Feature | Supported? |
|---|---|
| Explicit transactions (BEGIN/COMMIT/ROLLBACK) | ✅ |
| Auto-commit transactions | ✅ |
| Cross-database transactions (same workspace) | ✅ |
| DDL inside transactions | ✅ |
| Savepoints / Named transactions / Distributed / Nested | ❌ |

---

## Stored Procedures (Authoring Patterns)

Stored procedures on DW can perform full DDL/DML. On Lakehouse/Mirrored DB SQLEPs, procedures are read-only.

### ETL Procedure Pattern (DW)

```sql
CREATE PROCEDURE dbo.sp_LoadFactSales
    @BatchDate date
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE tgt
        FROM dbo.FactSales AS tgt
        INNER JOIN dbo.StagingFactSales AS src ON tgt.SaleID = src.SaleID
        WHERE src.LoadDate = @BatchDate;

        INSERT INTO dbo.FactSales
        SELECT * FROM dbo.StagingFactSales WHERE LoadDate = @BatchDate;

        DELETE FROM dbo.StagingFactSales WHERE LoadDate = @BatchDate;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
```

### Upsert Without MERGE (DW — Production-Safe Pattern)

When MERGE is unavailable or risky due to concurrency, use DELETE + INSERT:

```sql
CREATE PROCEDURE dbo.sp_UpsertDimProduct
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE tgt FROM dbo.DimProduct AS tgt
        WHERE EXISTS (SELECT 1 FROM dbo.StagingProduct AS src WHERE src.ProductID = tgt.ProductID);

        INSERT INTO dbo.DimProduct SELECT * FROM dbo.StagingProduct;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
```

### CTAS-Based Table Swap Pattern

For large-scale transforms where UPDATE would be slow or conflict-prone:

```sql
CREATE PROCEDURE dbo.sp_RebuildFactSales
AS
BEGIN
    CREATE TABLE dbo.FactSales_New AS
    SELECT SaleID, ProductID, CustomerID, SaleDate,
           Amount * 1.10 AS Amount, Quantity
    FROM dbo.FactSales;

    EXEC sp_rename 'dbo.FactSales', 'FactSales_Old';
    EXEC sp_rename 'dbo.FactSales_New', 'FactSales';
    DROP TABLE IF EXISTS dbo.FactSales_Old;
END;
GO
```

**Warning**: Destroys time-travel history and security (GRANT/DENY) on the original table. Re-apply after swap. Use in-place UPDATE or TRUNCATE + INSERT if history must be preserved.

### Cursor Replacement Pattern

Cursors are **not supported** in Fabric DW. Replace with WHILE + ROW_NUMBER():

```sql
CREATE PROCEDURE dbo.sp_ProcessRows
AS
BEGIN
    SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS RowNum,
           SaleID, Amount
    INTO #work
    FROM dbo.FactSales WHERE NeedsProcessing = 1;

    DECLARE @rowCount int = (SELECT COUNT(*) FROM #work);
    DECLARE @current int = 1;
    DECLARE @saleID bigint, @amount decimal(19,4);

    WHILE @current <= @rowCount
    BEGIN
        SELECT @saleID = SaleID, @amount = Amount FROM #work WHERE RowNum = @current;
        -- Row-level logic (prefer set-based operations when possible)
        SET @current += 1;
    END;

    DROP TABLE #work;
END;
GO
```

### Procedure Capabilities Reference

| Feature | DW | Lakehouse/Mirrored DB SQLEP |
|---|---|---|
| Parameters, Variables, Control flow, TRY/CATCH | ✅ | ✅ |
| Dynamic SQL (sp_executesql) | ✅ | ✅ |
| DDL / DML / Transactions inside procedures | ✅ | ❌ (read-only) |
| Temp tables, RETURN, Result sets | ✅ | ✅ |
| Cursors | ❌ | ❌ |

### Running Procedures from Pipelines

- **DW**: Invoke via **Script activity** in Fabric Data Pipelines (select Warehouse connection). The Stored Procedure activity supports only Azure SQL / SQL MI — **not** Fabric Warehouse.
- **Lakehouse SQLEP**: Not directly callable from pipeline activities. Workaround: Notebook activity with `pyodbc` to call `EXEC`.

---

## Time Travel and Warehouse Snapshots (DW Only)

### Time Travel (FOR TIMESTAMP AS OF)

Warehouse retains historical versions for **30 calendar days** at no extra cost (Delta Lake versioning).

```sql
-- Query a table at a specific point in time (UTC)
SELECT * FROM dbo.FactSales
OPTION (FOR TIMESTAMP AS OF '2025-06-01T08:00:00.000');

-- Recover deleted data via CTAS
CREATE TABLE dbo.RecoveredSales AS
SELECT * FROM dbo.FactSales
OPTION (FOR TIMESTAMP AS OF '2025-06-15T10:30:00.000');
```

**Rules**:
- Timestamp must be UTC. `FOR TIMESTAMP AS OF` appears **once** per SELECT — all tables see the same point in time.
- Cannot be used in CREATE VIEW definitions. Can be used when querying views.
- Returns the **current schema** — dropped columns won't appear in time-travel results.
- Dropping and recreating a table resets its history.
- Works in stored procedures via dynamic SQL (sp_executesql).

### Warehouse Snapshots (GA)

Named, read-only, point-in-time views of the entire warehouse.

```sql
-- Snapshots created via REST API or portal (not T-SQL)
-- Query a snapshot
SELECT * FROM MonthEnd_Sept2025.dbo.FactSales;
```

**Use cases**: Financial close (lock KPIs), audit (compare two points in time), stable reporting (point Power BI to snapshot during ETL), data recovery.

**Behaviors**: User-created, retained up to 30 days, read-only, zero-copy (reference existing Parquet files), can be refreshed to a new point in time atomically.

---

## Source Control and CI/CD (DW Only — Preview)

### Git Integration

Fabric DW supports Git with Azure DevOps and GitHub. Schema is exported as a **SQL database project** — each object becomes a `.sql` file.

```
WarehouseName/
├── .platform
├── WarehouseName.SQLDatabase/
│   ├── dbo/
│   │   ├── Tables/FactSales.sql
│   │   ├── Views/vw_SalesReport.sql
│   │   ├── StoredProcedures/sp_LoadFactSales.sql
│   │   └── Functions/fn_SalesByRegion.sql
```

### SQL Database Projects (VS Code)

Develop schema locally using the SQL Database Projects extension: build/validate `.dacpac` files, schema comparison, incremental publish, cross-warehouse references via SQLCMD variables.

### Deployment Pipelines

Fabric Deployment Pipelines promote code across environments (Dev → Test → Prod). Schema only — **no data**. Triggered manually or via Fabric REST APIs.

### CI/CD Limitations

| Limitation | Workaround |
|---|---|
| ALTER TABLE via deploy causes table drop + recreate (data loss) | Apply schema changes manually or via migration scripts |
| Lakehouse SQLEP not in Git integration | Manage objects via external scripts |
| DataflowsStagingWarehouse blocks Git sync | Don't create Dataflow Gen2 with warehouse output while Git-connected |
| Cross-item dependencies not fully resolved | Plan item sequencing; use SQLCMD variables |

---

## Authoring Permission Model

| Operation | Minimum Workspace Role | Notes |
|---|---|---|
| CREATE/ALTER/DROP TABLE, DML | Contributor | |
| COPY INTO | Contributor | Also needs source storage access |
| CREATE VIEW/PROCEDURE/FUNCTION | Contributor | Also on Lakehouse/Mirrored DB SQLEP |
| GRANT / DENY / REVOKE | Admin | |
| KILL sessions | Admin | |
| Git operations | Contributor | Must have Git repo access |

**COPY INTO authentication**: By default uses the executing user's Entra ID credentials. User needs **Storage Blob Data Reader** (or higher) on ADLS Gen2, or SAS token in CREDENTIAL clause, or workspace identity for firewall-protected storage. OneLake sources require appropriate Fabric permissions on the source item.

---

## Authoring Gotchas and Troubleshooting

| # | Issue | Cause | Resolution |
|---|---|---|---|
| 1 | Singleton INSERT causes poor performance | Each INSERT creates a tiny Parquet file | Use INSERT...SELECT, CTAS, or COPY INTO. Remediate: CTAS + drop + rename |
| 2 | ALTER COLUMN not supported | Limited ALTER TABLE surface | CTAS workaround (see Schema Evolution) |
| 3 | Snapshot conflict (error 24556/24706) | Concurrent UPDATE/DELETE/MERGE on same table | Serialize writes; retry with exponential backoff |
| 4 | MERGE fails intermittently | Preview + table-level conflict detection | Use DELETE + INSERT for production |
| 5 | DROP + CREATE loses time travel | Drop destroys history | Use TRUNCATE + INSERT to preserve history |
| 6 | CTAS produces unexpected types | Type inference from SELECT | Use explicit `CAST()` |
| 7 | Variables in CTAS fail | Not supported | Wrap in `sp_executesql` |
| 8 | Constraints not enforced at DML | All constraints require NOT ENFORCED | Validate data in ETL logic |
| 9 | IDENTITY gaps after rollback | By design — values consumed on attempt | Don't rely on gapless IDENTITY |
| 10 | sp_rename on SQLEP fails | Not supported on SQL analytics endpoints | Only on DW; use Spark for lakehouse |
| 11 | Deploy drops/recreates table | ALTER TABLE in DB project triggers recreate | Apply schema changes manually |
| 12 | Compaction conflicts with transactions | Background compaction commits between DML ops | Keep transactions short; retry |
| 13 | COPY INTO auth error | Missing storage permissions | Grant Storage Blob Data Reader or use SAS |
| 14 | CTAS + rename loses security | GRANT/DENY on original object which was dropped | Re-apply security after swap |
| 15 | Time travel returns current schema | FOR TIMESTAMP AS OF uses latest schema | Dropped columns won't appear |
| 16 | WHILE loop in procedure is slow | Row-by-row on distributed engine | Rewrite as set-based operations |
| 17 | Cursors not available | Not supported in Fabric DW | WHILE + ROW_NUMBER(); prefer set-based |

---

## Common Authoring Patterns (End-to-End Examples)

### Incremental Load (Delete + Insert)

```sql
CREATE PROCEDURE dbo.sp_IncrementalLoad @CutoffDate date
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;
        DELETE FROM dbo.FactSales WHERE SaleDate >= @CutoffDate;
        INSERT INTO dbo.FactSales
        SELECT * FROM SalesLakehouse.dbo.ProcessedSales WHERE SaleDate >= @CutoffDate;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
```

### Dimension SCD Type 1 (Overwrite)

```sql
CREATE PROCEDURE dbo.sp_UpdateDimCustomer
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE tgt SET tgt.CustomerName = src.CustomerName,
                       tgt.Email = src.Email, tgt.Region = src.Region
        FROM dbo.DimCustomer AS tgt
        INNER JOIN dbo.Staging_Customer AS src ON tgt.CustomerID = src.CustomerID
        WHERE tgt.CustomerName <> src.CustomerName
           OR tgt.Email <> src.Email
           OR tgt.Region <> src.Region;

        INSERT INTO dbo.DimCustomer (CustomerID, CustomerName, Email, Region)
        SELECT src.CustomerID, src.CustomerName, src.Email, src.Region
        FROM dbo.Staging_Customer AS src
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.DimCustomer AS tgt WHERE tgt.CustomerID = src.CustomerID
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
```

### View Layer on Lakehouse SQLEP

```sql
-- Only authoring available on Lakehouse/Mirrored DB SQL endpoints
CREATE SCHEMA gold;
GO

CREATE VIEW gold.vw_DailySales AS
SELECT CAST(SaleTimestamp AS date) AS SaleDate, ProductCategory,
       SUM(Amount) AS TotalSales, COUNT(*) AS TransactionCount
FROM dbo.RawSales
GROUP BY CAST(SaleTimestamp AS date), ProductCategory;
GO

CREATE FUNCTION gold.fn_SalesByCategory(@Category varchar(50))
RETURNS TABLE
AS RETURN (
    SELECT SaleDate, TotalSales, TransactionCount
    FROM gold.vw_DailySales WHERE ProductCategory = @Category
);
GO
```

---

## Quick Reference: Authoring Decision Guide

| Scenario | Recommended Approach |
|---|---|
| Bulk load from ADLS Gen2 | `COPY INTO` |
| Load with transformations | OPENROWSET + CTAS or INSERT...SELECT |
| Ingest from another Fabric item | CTAS or INSERT...SELECT (3-part naming) |
| Upsert (production, concurrent) | DELETE + INSERT in transaction + retry |
| Upsert (low concurrency) | MERGE (preview) |
| Large-scale column transform | CTAS + sp_rename (table swap) |
| Add a nullable column | `ALTER TABLE ADD col type NULL` |
| Change column data type | CTAS workaround |
| Rename table or column | sp_rename |
| Recover deleted data (< 30 days) | Time travel: FOR TIMESTAMP AS OF + CTAS |
| Stable reporting during ETL | Warehouse snapshots |
| Version control schema | Git integration + SQL database project |
| Consumption layer on lakehouse | CREATE VIEW/FUNCTION/PROCEDURE on SQLEP |
| Automate ETL with T-SQL | Stored procedures + pipeline Script activity |
| Handle concurrent writes | Serialize by table; retry on conflict |
