# Performance Patterns

> **Scope**: Identify and resolve Spark performance bottlenecks in Microsoft Fabric — covering detection thresholds, anti-patterns, stage/task analysis, optimization recipes, and capacity diagnostics. All examples use `az rest` and PySpark via Livy sessions.

---

## Detection Thresholds

The diagnostic skill uses the following thresholds to flag performance issues:

| Metric | Threshold | Severity | Meaning |
|--------|-----------|----------|---------|
| `Max executorRunTime / Median` | > 3× | HIGH | Data skew |
| `diskBytesSpilled` | > 0 | MEDIUM | Memory insufficient for sort/join |
| `gcTime / executorRunTime` | > 20% | MEDIUM | GC pressure |
| `shuffleWriteBytes` per stage | > 1 GB | MEDIUM | Heavy shuffle |
| `coreEfficiency` | < 30% | HIGH | Severe underutilisation |
| `idleTime / duration` | > 40% | MEDIUM | High idle ratio |

---

## Anti-Patterns

These are the most common performance killers in Fabric Spark workloads. Each pattern includes detection methods and fixes.

### Shuffle Spill

**What it is**: When shuffle data exceeds available memory, Spark spills data to disk. Disk I/O is orders of magnitude slower than memory access.

**Detection** (via Livy PySpark statement):
```python
# Check for spill in the last completed job
from pyspark.sql import SparkSession
sc = spark.sparkContext

# Get status URL info
print("Spark UI available via Fabric Monitoring Hub")
print(f"Application ID: {sc.applicationId}")

# Check current Spark config for shuffle settings
for key in ['spark.sql.shuffle.partitions', 'spark.shuffle.spill.compress',
            'spark.sql.adaptive.enabled', 'spark.sql.adaptive.coalescePartitions.enabled']:
    print(f"{key} = {sc.getConf().get(key, 'not set')}")
```

**Fixes**:
| Approach | When to Use |
|---|---|
| Increase executor memory | Spill is small relative to data size |
| Reduce shuffle partition count | Too many partitions create overhead |
| Pre-filter data before joins/aggregations | Unnecessary data enters shuffle |
| Enable AQE coalescing | `spark.sql.adaptive.coalescePartitions.enabled=true` |

### Data Skew

**What it is**: Uneven distribution of data across partitions. A few partitions have vastly more data than others, causing some tasks to run much longer.

**Detection**:
```python
# Detect skew in a DataFrame
df = spark.table("your_table")

# Check partition sizes
from pyspark.sql.functions import spark_partition_id, count
partition_stats = df.groupBy(spark_partition_id().alias("partition")) \
    .agg(count("*").alias("row_count"))

stats = partition_stats.describe("row_count")
stats.show()

# Skew ratio: max / mean — values > 3x indicate significant skew
max_count = partition_stats.agg({"row_count": "max"}).collect()[0][0]
mean_count = partition_stats.agg({"row_count": "avg"}).collect()[0][0]
print(f"Skew ratio: {max_count / mean_count:.1f}x (>3x = significant skew)")
```

**Fixes**:
| Approach | When to Use |
|---|---|
| Salting join keys | Join on skewed key; add random salt to distribute |
| AQE skew join | `spark.sql.adaptive.skewJoin.enabled=true` (on by default in Fabric) |
| Pre-aggregate before join | Reduce cardinality of skewed dimension |
| Repartition by different column | Current partition key has low cardinality |

### Small File Problem

**What it is**: Too many small files in Delta tables cause excessive metadata overhead and slow reads.

**Detection**:
```python
# Check file sizes in a Delta table
from delta.tables import DeltaTable
dt = DeltaTable.forName(spark, "your_table")

# File count and sizes
files_df = spark.sql("DESCRIBE DETAIL your_table")
files_df.select("numFiles", "sizeInBytes").show()

# Rule of thumb: aim for 128MB-1GB per file
size_bytes = files_df.collect()[0]["sizeInBytes"]
num_files = files_df.collect()[0]["numFiles"]
avg_file_mb = (size_bytes / num_files) / (1024 * 1024) if num_files > 0 else 0
print(f"Average file size: {avg_file_mb:.1f} MB")
if avg_file_mb < 32:
    print("⚠️  Small file problem detected — consider OPTIMIZE")
```

**Fix**:
```python
# Compact small files
spark.sql("OPTIMIZE your_table")

# For partitioned tables, optimize specific partitions
spark.sql("OPTIMIZE your_table WHERE date = '2024-01-15'")

# Enable auto-optimize for future writes
spark.sql("ALTER TABLE your_table SET TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true')")
```

### Collect Misuse

**What it is**: Calling `.collect()`, `.toPandas()`, or `.show(n)` with large `n` on a large DataFrame pulls all data to the driver, causing OOM or extreme slowness.

**Detection**: Look for these patterns in notebook code:
- `df.collect()` on DataFrames with > 10K rows
- `df.toPandas()` without prior `.limit()`
- `df.show(1000000)` or similar large show calls

**Fixes**:
| Instead of | Use |
|---|---|
| `df.collect()` | `df.limit(100).collect()` or `df.write.saveAsTable()` |
| `df.toPandas()` | `df.limit(10000).toPandas()` |
| `df.show(n)` for large n | `df.show(20)` (default) or write to table and query |

### Cartesian Joins

**What it is**: A join without a proper join condition produces the Cartesian product — row count = left × right.

**Detection**: Check for cross joins in the query plan:
```python
df_result = df1.join(df2, ...)  # suspect join
df_result.explain(True)  # look for "CartesianProduct" or "BroadcastNestedLoopJoin"
```

**Fix**: Always specify explicit join conditions. If a cross join is intended, use `df1.crossJoin(df2)` to make intent clear and add a downstream filter.

### High GC Pressure

**What it is**: The JVM heap is filling up faster than garbage collection can free it. Executor CPU time is dominated by GC; throughput is much lower than raw CPU capacity suggests.

**Detection**: `gcTime / executorRunTime > 20%`

**Root Cause:**
- Python UDFs that create Python objects in every row
- String-heavy DataFrames with high cardinality
- Many small objects created by complex aggregation logic

**Fix:**
```python
# Option 1: Replace Python UDFs with native PySpark SQL functions
# BAD — UDF creates Python objects per row
from pyspark.sql.functions import udf
@udf("string")
def clean(s):
    return s.strip().lower() if s else ""

# GOOD — uses JVM-native function, no Python object creation
from pyspark.sql.functions import lower, trim
df = df.withColumn("cleaned", lower(trim(col("value"))))

# Option 2: Use Pandas UDFs (vectorized) when Python logic is mandatory
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf("double")
def compute_score(values: pd.Series) -> pd.Series:
    return values.apply(lambda x: x * 2.5)

# Option 3: Cache DataFrames that are used multiple times
df_expensive.cache()
df_expensive.count()  # trigger materialization

# Option 4: Use Parquet/Delta format (columnar, minimizes Java object count)
df.write.format("delta").save("Files/output/")
```

### Heavy Shuffle

**What it is**: Too much data is being shuffled across the network. Stage takes a long time; many "shuffle write" / "shuffle read" bytes visible in stage metrics.

**Detection**: `shuffleWriteBytes > 1 GB` in a stage

**Root Cause:**
- `groupBy` + aggregation on a high-cardinality column
- Multiple chained joins without caching intermediate results
- `repartition(N)` with N larger than needed

**Fix:**
```python
# Option 1: Cache intermediate DataFrames to avoid re-shuffling
df_joined = large1.join(large2, "key").cache()
df_joined.count()  # materialize
result1 = df_joined.groupBy("category").agg(...)
result2 = df_joined.filter(col("status") == "active")

# Option 2: Reduce join width — select only needed columns before join
df_slim = df.select("key", "value1", "value2")
df_slim.join(other_slim, "key")

# Option 3: Use bucket tables for repeated large-table joins (eliminates shuffle)
df.write.bucketBy(64, "user_id").sortBy("user_id").saveAsTable("events_bucketed")
events = spark.table("events_bucketed")
users  = spark.table("users_bucketed")
events.join(users, "user_id")  # no shuffle!

# Option 4: Tune shuffle partitions to match data volume
# Rule of thumb: each shuffle partition should be 100-200 MB
spark.conf.set("spark.sql.shuffle.partitions", "100")
# Or let AQE coalesce automatically:
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

### Too Many Small Partitions

**What it is**: High number of tasks but very short duration per task (< 100ms). Task scheduling overhead dominates actual compute time.

**Detection**: Stage shows 1000+ tasks but each completes in milliseconds.

**Root Cause:** `spark.sql.shuffle.partitions` is set too high relative to data volume, or source files are very small (many small Parquet files).

**Fix:**
```python
# Reduce shuffle partitions globally
spark.conf.set("spark.sql.shuffle.partitions", "50")  # tune to your data size

# Or let AQE coalesce small partitions automatically (recommended)
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB")

# For source files: coalesce small files before processing
df = spark.read.parquet("Files/raw/")
df = df.coalesce(20)  # reduce from 500 tiny partitions to 20 larger ones
```

### Driver Memory Bottleneck

**What it is**: Operations that run on the driver rather than executors. All executors idle while driver is computing.

**Detection**: Driver OOM (see [job-diagnostics.md pattern #1](job-diagnostics.md#1-out-of-memory--driver)) or very long "driver computation" phases with idle executors.

**Root Cause:**
- `df.collect()` — materializes entire DataFrame in driver memory
- `df.toPandas()` — same
- Schema inference on many files
- Building broadcast variables from large datasets

**Fix:**
```python
# Instead of collect(): write results
df.write.mode("overwrite").parquet("Files/output/")
display(df.limit(1000))  # paginate for visual inspection

# For schema inference on many files: provide schema explicitly
from pyspark.sql.types import StructType, StructField, StringType, LongType
schema = StructType([
    StructField("id", LongType(), True),
    StructField("name", StringType(), True),
])
df = spark.read.schema(schema).json("Files/data/")
```

### Missing Cache / Re-computation

**What it is**: A DataFrame that is used multiple times is not cached, so Spark re-executes the full lineage from the source each time an action is called. Same stage appears multiple times with identical input/output.

**Detection**: Multiple downstream actions re-trigger the same expensive computation (visible in stage repetition).

**Fix:**
```python
# BEFORE (expensive re-computation)
df_expensive = df.join(other, "key").groupBy("cat").agg(...)
result1 = df_expensive.filter(col("cat") == "A").count()
result2 = df_expensive.filter(col("cat") == "B").show()
# Both calls re-execute the join and aggregation

# AFTER (cache and reuse)
df_expensive = df.join(other, "key").groupBy("cat").agg(...).cache()
df_expensive.count()  # trigger materialisation

result1 = df_expensive.filter(col("cat") == "A").count()
result2 = df_expensive.filter(col("cat") == "B").show()

# ALWAYS unpersist when done
df_expensive.unpersist()
```

---

## Stage and Task Analysis

### Reading Spark Execution Metrics

In Fabric, the Spark UI is accessible through the Monitoring Hub. For programmatic access, use Livy to query runtime metrics.

```python
# Get active and completed job info
sc = spark.sparkContext
status_tracker = sc.statusTracker()

# Active jobs
active_jobs = status_tracker.getActiveJobIds()
print(f"Active jobs: {list(active_jobs)}")

# For each active job, get stage info
for job_id in active_jobs:
    job_info = status_tracker.getJobInfo(job_id)
    print(f"Job {job_id}: status={job_info.status()}, "
          f"stages={list(job_info.stageIds())}")
```

### Identify Slow Stages

```python
# Run a query and then analyze the plan
df = spark.sql("SELECT ... FROM ... JOIN ...")

# Physical plan shows shuffle boundaries and join strategies
df.explain("formatted")

# The plan reveals:
# - Exchange nodes = shuffle boundaries (expensive)
# - BroadcastHashJoin vs SortMergeJoin (broadcast = faster for small tables)
# - Filter pushdown (filters should appear as early as possible)
```

### Monitor Active Statements

```bash
# Check all statements in a session
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/statements" \
  --query "statements[].{id:id, state:state, progress:progress}" --output table
```

---

## Optimization Recipes

### Partition Tuning

```python
# Check current partition count
df = spark.table("your_table")
print(f"Current partitions: {df.rdd.getNumPartitions()}")

# Rule of thumb: 128MB per partition, 2-4x parallelism of cluster
# For a 10GB dataset on 8 cores: ~80-320 partitions
optimal = max(1, int(df.inputFiles().__len__() * 128 / 1024))  # rough estimate
print(f"Suggested partitions: {optimal}")

# Repartition if needed
df_optimized = df.repartition(optimal)
```

### Broadcast Join Optimization

```python
from pyspark.sql.functions import broadcast

# For small dimension tables (< 100MB), broadcast to avoid shuffle
dim_df = spark.table("small_dimension_table")
fact_df = spark.table("large_fact_table")

# Explicit broadcast hint
result = fact_df.join(broadcast(dim_df), "key_column")

# Check if broadcast was used
result.explain()  # Should show BroadcastHashJoin, not SortMergeJoin
```

### Caching Strategy

```python
# Cache intermediate results that are reused multiple times
intermediate_df = spark.sql("""
    SELECT customer_id, SUM(amount) as total
    FROM transactions
    GROUP BY customer_id
""")

# Cache only if the DataFrame is reused in multiple downstream operations
intermediate_df.cache()
intermediate_df.count()  # Materialize the cache

# Use in multiple downstream queries
top_customers = intermediate_df.filter("total > 10000")
segments = intermediate_df.join(dim_customers, "customer_id")

# ALWAYS unpersist when done
intermediate_df.unpersist()
```

### AQE (Adaptive Query Execution) Settings

AQE is enabled by default in Fabric. Verify and tune:

```python
# Check AQE settings
aqe_keys = [
    'spark.sql.adaptive.enabled',
    'spark.sql.adaptive.coalescePartitions.enabled',
    'spark.sql.adaptive.skewJoin.enabled',
    'spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes',
    'spark.sql.adaptive.advisoryPartitionSizeInBytes'
]
for key in aqe_keys:
    print(f"{key} = {spark.conf.get(key, 'not set')}")
```

### Predicate Pushdown Verification

```python
# Verify that filters are pushed down to the data source
df = spark.table("your_table").filter("date >= '2024-01-01'").filter("status = 'active'")

# Check the physical plan — filters should appear at the scan level
df.explain(True)
# Look for: PushedFilters: [IsNotNull(date), GreaterThanOrEqual(date,2024-01-01)]
# If filters appear ABOVE the scan, pushdown is not working
```

---

## Capacity and Resource Diagnostics

### Check Capacity Utilization

When jobs are slow across the board, the issue may be capacity-level, not job-level.

> **Per-Application Resource Metrics**: Use the [Resource Usage API](../../../../common/SPARK-MONITORING-CORE.md#resource-usage-api) for granular vCore allocation and utilization timelines per Spark application, including core efficiency and idle time metrics.

```bash
# List available capacities and their state
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/capacities" \
  --query "value[].{name:displayName, id:id, sku:sku, state:state}" \
  --output table
```

### Detect Throttling

Fabric throttles workloads when capacity utilization exceeds limits. Symptoms:
- Jobs take longer than usual to start
- Sessions stay in `starting` state
- API calls return 429 (Too Many Requests)

```bash
# Retrieve the first history page, retaining pagination metadata.
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances" \
  --output json
```

Follow `continuationToken` pages (or the service's continuation URI), with
`x-ms-fabric-skill: spark-cli` on every request. Only after combining the `value`
arrays, sort by `startTimeUtc` descending and select the latest five client-side
to inspect status and failure details. `limit` is not a documented query parameter.
An incomplete/filtered view cannot establish an empty retained history.

### Capacity Sizing Guide

| SKU | CU | Concurrent Spark Sessions (Typical) | Use Case |
|---|---|---|---|
| F2 | 2 | 1 | Dev/test |
| F4 | 4 | 1-2 | Small workloads |
| F8 | 8 | 2-3 | Light production |
| F16 | 16 | 3-5 | Medium production |
| F32 | 32 | 5-8 | Standard production |
| F64 | 64 | 8-15 | Large production |
| F128+ | 128+ | 15+ | Heavy production |

> Concurrent session counts are approximate and depend on session size (memory/cores). Starter Pool sessions consume fewer CUs than custom pool sessions.

### Resource Efficiency Check

Run this diagnostic in a Livy session to check for resource waste:

```python
# Check if executors are underutilized
sc = spark.sparkContext
conf = sc.getConf()

print("=== Resource Allocation ===")
print(f"Driver memory: {conf.get('spark.driver.memory', 'default')}")
print(f"Executor memory: {conf.get('spark.executor.memory', 'default')}")
print(f"Executor cores: {conf.get('spark.executor.cores', 'default')}")
print(f"Dynamic allocation: {conf.get('spark.dynamicAllocation.enabled', 'not set')}")
print(f"Min executors: {conf.get('spark.dynamicAllocation.minExecutors', 'not set')}")
print(f"Max executors: {conf.get('spark.dynamicAllocation.maxExecutors', 'not set')}")

active_execs = len(sc._jsc.sc().getExecutorMemoryStatus()) - 1  # subtract driver
print(f"\nActive executors: {active_execs}")
print(f"Default parallelism: {sc.defaultParallelism}")
print(f"Shuffle partitions: {spark.conf.get('spark.sql.shuffle.partitions', 'default')}")
```
