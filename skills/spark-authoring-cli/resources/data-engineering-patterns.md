# Data Engineering Patterns — Skill Resource

Essential patterns and principles for PySpark data engineering in Microsoft Fabric.
## Recommended patterns

### Must

1. **Always define explicit schemas** for production data ingestion — avoid `inferSchema=true` which adds overhead and inconsistency
2. **Use Delta Lake format** for all managed tables — provides ACID guarantees, time travel, and optimized reads
3. **Validate data quality** at ingestion boundaries — check nulls, data types, and business rules before persisting
4. **Add metadata columns** to track lineage — `ingestion_timestamp`, `source_system`, `pipeline_run_id` for debugging
5. **Handle errors gracefully** — wrap ingestion/transformation logic in try-except with proper logging and recovery
6. **Use MERGE for upserts** — leverage Delta Lake's `MERGE INTO` for incremental updates based on merge keys
7. **Partition large tables** — use date or category columns for partition pruning to improve query performance
8. **If a real public source URL is provided, ingest from that source** — download/copy into lakehouse `Files/` first, then load with Spark from lakehouse paths (do not replace with synthetic inline rows)

### Prefer

1. **Batch processing over streaming** unless real-time requirements exist — simpler to debug and monitor
2. **Read-optimized writes** for analytical workloads — use `.coalesce()` or `.repartition()` to right-size output files
3. **Window functions over self-joins** — more efficient for ranking, running totals, and lag/lead operations
4. **Broadcast joins for small dimensions** — use `.broadcast()` hint when one table fits in memory (<100MB)
5. **Columnar operations over row-wise** — leverage DataFrame/SQL API instead of UDFs when possible
6. **Lazy evaluation mindset** — build transformation chains, then execute with actions (`.write()`, `.count()`)

### Avoid

1. **Don't use `.collect()` on large DataFrames** — brings all data to driver, causes OOM errors
2. **Don't chain multiple `.count()` calls** — each triggers a full scan; cache DataFrame if needed
3. **Don't ignore skew** — salting keys or adaptive query execution prevents straggler tasks
4. **Don't skip Delta optimization** — run `OPTIMIZE` and `VACUUM` regularly to prevent small file problem
5. **Don't hardcode paths or credentials** — use parameters and secure configuration patterns
6. **Don't mix append and overwrite** carelessly — understand partition scope for `.mode("overwrite")`

---

## Data Ingestion Principles

### Schema Management
Guide LLM to define explicit schemas with nullable constraints, data type validation, and business context comments.

> **Note**: This section refers to **data schemas** (DataFrame structure). For **lakehouse schemas** (databases/namespaces for organizing tables), see SPARK-AUTHORING-CORE.md Lakehouse Schema Organization.

### Source Format Handling
- **CSV/TSV**: Explicit schema, header option
- **Parquet/ORC**: Columnar formats with embedded schema
- **JSON**: multiLine option for nested objects
- **ADLS Gen2**: `abfss://container@storage.dfs.core.windows.net/path`
- **OneLake**: `abfss://workspace@onelake.dfs.fabric.microsoft.com/lakehouse.Lakehouse/Files/path`
- **Public HTTP/HTTPS datasets**: Download/copy to lakehouse `Files/...` first, then `spark.read` from lakehouse paths for stable runtime behavior

### Validation Patterns
- **Completeness**: Filter nulls in required fields
- **Referential integrity**: Join with dimensions, flag orphans
- **Business rules**: Domain-specific checks (amount > 0, date ranges)
- **Duplicates**: dropDuplicates or groupBy to identify

### Error Handling Strategy
- Try-except blocks with specific exceptions
- Contextual logging
- Dead letter queues for invalid records
- Retry logic for transient failures

---

## Transformation Patterns

This section helps you choose the right transformation approach for your data pipeline. Each pattern follows a consistent structure: **WHAT** (definition), **WHY** (benefits/trade-offs), **WHEN** (decision criteria), and **HOW** (examples).

---

### Pattern 1: Aggregations (GROUP BY + Aggregate Functions)

**WHAT:**  
Summarize data by grouping rows and applying aggregate functions (`SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `COLLECT_LIST`).

**WHY:**
- ✅ Single-pass computation (efficient)
- ✅ Built-in Spark optimization (adaptive query execution)
- ✅ Can combine multiple aggregates in one `.agg()` call
- ⚠️ Large cardinality GROUP BY (millions of unique keys) may cause memory pressure

**WHEN to use:**
- Summarizing metrics by dimension (e.g., revenue by region, counts by product)
- Calculating totals, averages, or other statistical measures
- Creating reporting tables or dashboards
- Preparing data for visualization

**Examples:**

```python
from pyspark.sql import functions as F

# Daily sales summary
df.groupBy("order_date") \
  .agg(
    F.sum("amount").alias("total_sales"),
    F.count("order_id").alias("order_count"),
    F.countDistinct("customer_id").alias("unique_customers")
  )

# Multi-dimensional aggregation
df.groupBy("product_category", "region", "order_date") \
  .agg(F.avg("discount_percent").alias("avg_discount"))
```

**Alternative:** If aggregation + periodic refresh → consider **Materialized Lake View** (see Pattern 4 below).

---

### Pattern 2: Window Functions (Partitioned Analytics)

**WHAT:**  
Perform calculations across rows related to the current row without collapsing them into groups. Common functions: `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()`, `SUM() OVER (...)`, `AVG() OVER (...)`.

**WHY:**
- ✅ More efficient than self-joins for ranking/running totals
- ✅ Preserves row-level detail while adding analytical columns
- ✅ Supports complex ordering and partitioning logic
- ⚠️ Large partitions can cause shuffle overhead (consider repartitioning by partition key first)

**WHEN to use:**
- **Ranking**: Top N per category, percentile ranks
- **Running calculations**: Cumulative sums, moving averages
- **Lag/Lead comparisons**: Month-over-month change, previous transaction
- **Deduplication**: `ROW_NUMBER()` + `filter(rank == 1)` to pick most recent (note: QUALIFY **and window functions** block MLV incremental refresh — keep window functions OUT of MLV; apply ranking in downstream notebook for IR-eligible pipelines. See [mlv-incremental-refresh-patterns.md § Pattern 1](mlv-incremental-refresh-patterns.md))

**Examples:**

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Top 3 products per category by sales
window_spec = Window.partitionBy("category").orderBy(F.desc("sales"))
df.withColumn("rank", F.row_number().over(window_spec)) \
  .filter(F.col("rank") <= 3)

# Running total and previous value
window_running = Window.partitionBy("customer_id").orderBy("order_date") \
                       .rowsBetween(Window.unboundedPreceding, Window.currentRow)
df.withColumn("cumulative_spent", F.sum("amount").over(window_running)) \
  .withColumn("previous_order", F.lag("order_date", 1).over(window_running))
```

**Alternative:** Self-joins are less efficient but sometimes unavoidable for complex multi-step logic.

---

### Pattern 3: Joins (Combining Datasets)

**WHAT:**  
Merge two DataFrames based on a common key. Types: `inner`, `left` (left outer), `right`, `full` (full outer), `cross`, `left_semi`, `left_anti`.

**WHY:**
- ✅ Standard relational operation for combining data
- ✅ Broadcast joins (<100MB dimension table) avoid shuffle — very fast
- ⚠️ Large-to-large joins can cause shuffle and spill to disk
- ⚠️ Skewed keys (one key with millions of rows) create straggler tasks

**WHEN to use:**

| Join Type | When to Use | Example |
|---|---|---|
| **Inner** | Only matching rows needed | Transactions + valid customers |
| **Left (left outer)** | Keep all left rows, add right columns where match exists | Orders + optional shipping details |
| **Broadcast** | One table <100MB, other is large | Fact table + dimension table |
| **Left Semi** | Filter left table by existence in right (like `IN` subquery) | Customers who placed orders |
| **Left Anti** | Find rows in left NOT in right (like `NOT IN`) | Customers who never placed orders |

**Examples:**

```python
# Inner join: transactions + customer details
transactions.join(customers, on="customer_id", how="inner")

# Broadcast join: large fact table + small dimension
from pyspark.sql.functions import broadcast
fact_table.join(broadcast(dim_table), on="product_id")

# Left join: keep all orders, add customer name if exists
orders.join(customers, on="customer_id", how="left") \
      .select("order_id", "amount", "customer_name")
```

**Tips:**
- For skewed joins, use salting (add random suffix to key)
- Use `df.explain()` to verify broadcast join actually happened
- Consider pre-filtering both DataFrames before joining to reduce shuffle

---

### Pattern 4: Materialized Lake Views (Declarative Transformations)

**WHAT:**  
A Fabric-native feature that materializes transformation results as Delta tables with automatic refresh, data quality constraints, and query optimization. Two authoring modes: Spark SQL (with incremental refresh) or PySpark (full refresh only).

**WHY:**
- ✅ **Declarative**: Define WHAT to compute, not HOW (Fabric handles refresh scheduling)
- ✅ **Auto-refresh**: Spark SQL MLVs support incremental refresh; PySpark MLVs use full refresh
- ✅ **Query-optimized**: Pre-aggregated, indexed, faster than querying raw tables
- ✅ **Data quality**: Built-in `CHECK` constraints with `ON MISMATCH DROP|FAIL`
- ⚠️ **Spark SQL MLVs**: No Python UDFs, but support incremental refresh
- ⚠️ **PySpark MLVs**: Support UDFs and complex logic, but full refresh only (no incremental)
- ⚠️ **Batch-only**: Not suitable for real-time streaming
- ⚠️ **Incremental limitations**: Some SQL patterns block incremental refresh (see [mlv-incremental-refresh-patterns.md](mlv-incremental-refresh-patterns.md))

**WHEN to use:**

Use this decision tree to choose between MLVs and PySpark notebooks:

```
┌─ Is transformation logic pure SQL (SELECT/WHERE/JOIN/GROUP BY)?
│
├─ YES ─┐
│       ├─ Does it need periodic refresh (not real-time)?
│       │
│       ├─ YES ─┐
│       │       ├─ Would incremental refresh save cost (source is append-only + CDF enabled + query uses supported SQL constructs)?
│       │       │
│       │       ├─ YES → ✅ **Use Materialized Lake View**
│       │       │          (Declarative, auto-incremental, query-optimized)
│       │       │
│       │       └─ NO  → ⚠️  **MLV or Notebook**
│       │                   (Small tables: MLV. Large full-refresh: consider notebook with optimizations)
│       │
│       └─ NO (real-time) → ❌ **Use Structured Streaming Notebook/Job Definition + Eventstream**
│                               (MLVs are batch-only; use Spark Structured Streaming for real-time ingestion)
│
└─ NO (Python/complex logic) → ❌ **Use PySpark Notebook**
                                   (UDFs, iterative algorithms, external APIs, custom validation)
```

**Concrete examples:**

| Use Case | Transformation | Best Choice | Rationale |
|---|---|---|---|
| **Daily sales aggregation** | `SELECT date, SUM(amount) FROM transactions GROUP BY date` | **MLV** | Pure SQL, periodic refresh, incremental on `date` |
| **Customer lifetime value** | DataFrame with complex Python UDFs, external API calls | **Notebook** | Python logic, not SQL-expressible |
| **Bronze→Silver dedup** | `SELECT * FROM bronze.orders WHERE date > watermark` (then filter duplicates in notebook OR use Delta MERGE for upsert) | **Notebook or MERGE statement** | MERGE provides idempotent dedup; easier in notebook than MLV |
| **ML feature engineering** | Complex PySpark with pandas UDFs, statistics, outlier detection | **Notebook** | Iterative logic, scikit-learn integration |
| **Real-time KPI dashboard** | Streaming aggregation over 5-minute windows | **Eventstream** | Real-time requirement; MLVs are batch |
| **Gold layer metrics** | `SELECT product_id, AVG(rating), COUNT(*) FROM reviews GROUP BY product_id` | **MLV** | Read-optimized, frequently queried, periodic refresh |

**Cost/performance considerations:**

| Factor | MLV | Notebook |
|---|---|---|
| **Development time** | Fast (SQL-only) | Moderate (PySpark code + testing) |
| **Refresh overhead** | Low (auto-incremental) | High (manual watermark logic) |
| **Query performance** | Optimized (pre-aggregated) | Depends on Delta optimization |
| **Debugging** | Limited (SQL errors only) | Full (logs, breakpoints, print statements) |
| **Flexibility** | Low (SQL-only) | High (any Python/Spark API) |

**When to switch from MLV to Notebook:**
- MLV hits SQL limitations (no UDFs, complex Python logic needed)
- Incremental refresh blockers appear (see [mlv-incremental-refresh-patterns.md](mlv-incremental-refresh-patterns.md))
- Debugging requires inspecting intermediate steps (MLV is declarative, no step-by-step visibility)

**When to switch from Notebook to MLV:**
- Notebook logic simplifies to pure SQL after refactoring
- Manual watermark/incremental logic becomes complex — let MLV handle it
- Transformation is stable and needs less frequent iteration

**See also:**
- [Materialized Lake View patterns](materialized-lake-view-patterns.md) — design patterns, scheduling, when to use vs Delta tables
- [MLV incremental refresh patterns](mlv-incremental-refresh-patterns.md) — IR blocker catalog, safe rewrites, CDF prerequisites
- [mlv-operations-cli](../../mlv-operations-cli/SKILL.md) — schedule, trigger, monitor, and cancel MLV refreshes via REST API (use when user asks to automate refresh, not author SQL)

---

### Quick Decision Matrix

| Need | Use This |
|---|---|
| Summarize metrics by dimension | Aggregations (Pattern 1) |
| Rank/running totals preserving row detail | Window Functions (Pattern 2) |
| Combine data from two tables | Joins (Pattern 3) |
| SQL transformation with scheduled refresh + DQ | **Materialized Lake View (Pattern 4)** |
| Python logic / UDFs / complex algorithms | PySpark Notebook |
| Real-time streaming | Eventstream → Lakehouse |

---

### Example Approaches
**Customer Segmentation:** Use window functions for lifetime metrics, when().otherwise() for classification, temporal dimensions for recency

**Product Analytics:** Join with dimensions, aggregate by category, rank with row_number(), compute percentiles

---

## Delta Lake Best Practices

### MERGE Operations (Upserts)
When to use:
- Incremental loads where source sends changed/new records
- Slowly changing dimensions (SCD Type 1 or Type 2)
- Deduplication scenarios

Guide LLM to generate MERGE with:
- `.merge(source_df, "target.id = source.id")` on unique key
- `.whenMatchedUpdateAll()` to update existing records
- `.whenNotMatchedInsertAll()` to insert new records
- Optional: `.whenMatchedDelete()` for hard deletes based on condition

### Optimization Strategies
Tell LLM to include:
- **Z-Ordering**: `OPTIMIZE table_name ZORDER BY (frequently_filtered_column)` improves query speed
- **VACUUM**: `VACUUM table_name RETAIN 168 HOURS` cleans up old file versions after retention period
- **Partition pruning**: Query with partition columns in WHERE clause to skip irrelevant data
- **File compaction**: Run `OPTIMIZE` to combine small files into right-sized files (128MB-1GB)

### Time Travel
Use cases:
- **Point-in-time queries**: `spark.read.format("delta").option("versionAsOf", 5).load(path)`
- **Rollback bad writes**: Restore to previous version with `RESTORE TABLE table_name TO VERSION AS OF 10`
- **Audit trail**: Query historical data for compliance, debugging

### Spark Session Configurations for Performance

Guide LLM to configure Spark sessions based on workload type:

**Write-Heavy Workloads (Bronze Layer - High-Volume Ingestion):**
- `spark.microsoft.delta.parquet.vorder.enabled = false` — Disable V-Order for faster writes
- `spark.databricks.delta.optimizeWrite.binSize = 1073741824` — Target 1GB file size for fewer small files
- `spark.databricks.delta.autoCompact.enabled = true` — Automatic compaction during writes
- `spark.microsoft.delta.optimize.fast.enabled = true` — Fast optimization algorithms
- `spark.databricks.delta.properties.defaults.enableDeletionVectors = true` — Efficient delete tracking
- `spark.microsoft.delta.targetFileSize.adaptive.enabled = true` — Adaptive file sizing
- `spark.native.enabled = true` — Use native execution engine (Velox)
- `spark.gluten.delta.columnMapping.name.enabled = true` — Column mapping for schema evolution

**Balanced Workloads (Silver Layer - Mixed Read/Write):**
- `spark.microsoft.delta.parquet.vorder.enabled = true` — Enable V-Order for better read performance
- `spark.databricks.delta.optimizeWrite.enabled = true` — Balance write optimization with read efficiency
- `spark.microsoft.delta.snapshot.driverMode.enabled = true` — Faster snapshot reads
- `spark.sql.adaptive.enabled = true` — Adaptive query execution
- `spark.sql.adaptive.coalescePartitions.enabled = true` — Dynamic partition coalescing

**Read-Heavy Workloads (Gold Layer - Analytics & Reporting):**
- `spark.microsoft.delta.parquet.vorder.enabled = true` — V-Order for maximum read performance
- `spark.databricks.delta.optimizeWrite.enabled = false` — No write optimization overhead
- `spark.sql.parquet.enableVectorizedReader = true` — Vectorized Parquet reads
- `spark.sql.files.maxPartitionBytes = 134217728` — 128MB partition size for optimal parallelism
- `spark.sql.adaptive.enabled = true` — Optimize query plans based on runtime stats
- `spark.databricks.delta.stalenessLimit = 0` — Always use latest snapshot

**When to apply these configs:**
- Pass during Livy session creation: `"conf": {"spark.config.key": "value"}`
- Set in notebook first cell before any Spark operations
- Configure at workspace level for consistent defaults
- Override per-job for specific workload requirements

---

## Quality Assurance Strategies

### Testing Levels
Guide LLM to implement:

**Unit Testing** (local Spark):
- Test transformation logic with small sample DataFrames
- Use `pytest` fixtures to create test Spark session
- Assert row counts, column values, schema correctness
- Focus on business logic in isolation

**Integration Testing** (Fabric API):
- Validate workspace/lakehouse creation succeeded
- Test notebook deployment via REST API
- Verify Livy session creation and code execution
- Check end-to-end data flow through bronze → silver → gold

**Data Quality Checks** (production):
- Row count validation: compare source vs target
- Schema validation: ensure expected columns exist with correct types
- Null checks: flag unexpected nulls in required fields
- Range checks: validate numeric values within expected bounds
- Freshness checks: ensure data updated within SLA timeframe

### Quality Gates
Define when pipelines should fail:
- **Critical failures**: schema mismatch, zero rows ingested, primary key violations
- **Warnings**: elevated null rate, data volume anomaly (>20% change), late arrival
- **Monitoring**: track ingestion lag, transformation duration, error rates over time

### Logging and Observability
Prompt LLM to generate:
- **Structured logging**: JSON-formatted logs with timestamp, severity, context
- **Metrics emission**: log key counts (rows processed, errors, duration) for monitoring
- **Error context**: capture input values, stack traces, environment details for debugging
