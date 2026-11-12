# Job Diagnostics

> **Scope**: Classify Spark job failures, retrieve logs via Fabric REST APIs, analyze job instance history, and follow a systematic triage workflow. All examples use `az rest` against the Fabric API.

---

## Failure Classification

Spark job failures in Fabric fall into distinct categories. Identify the category first — it determines the remediation path.

### 1. Out of Memory — Driver

**Signature:** `java.lang.OutOfMemoryError: Java heap space` in driver stderr
**Also matches:** `OutOfMemoryError: GC overhead limit exceeded`

**Root Cause:**
The Spark Driver JVM ran out of heap memory. Most commonly caused by collecting large amounts of data to the driver with `collect()`, `toPandas()`, or `show()` on a large DataFrame.

**Common Causes**:
| Cause | Indicator | Fix |
|---|---|---|
| `collect()` on large DataFrame | Error in driver logs after `.collect()` call | Replace with `.limit(N).toPandas()` or write to table |
| `toPandas()` on large DataFrame | Large DataFrame converted to Pandas | Use `.limit()` or process in Spark |
| `show(n)` with large n | Materializes rows in driver | Use `display(df)` which is paginated |
| Broadcast join on large table | OOM during broadcast | Set `spark.sql.autoBroadcastJoinThreshold=-1` |

**Fix:**
```python
# Instead of collect: write to storage
df.write.mode("overwrite").parquet("Files/output/")

# Instead of toPandas on large data: sample first
df.sample(0.01).toPandas()

# Instead of show: use display() which is paginated
display(df)

# If you must collect: always check count first
count = df.count()
if count < 100_000:
    df.collect()
else:
    raise ValueError(f"Too many rows to collect: {count}")
```

**Spark Config Fix (if driver must process large data):**
```python
spark.conf.set("spark.driver.memory", "8g")  # set in notebook config, not at runtime
```

### 2. Out of Memory — Executor

**Signature:** `java.lang.OutOfMemoryError` in executor stderr
**Also matches:** `Container killed by YARN for exceeding memory limits`, `ExecutorLostFailure (executor N exited caused by one of the running tasks)`

**Root Cause:**
An executor exceeded its JVM heap + overhead memory budget. Caused by large shuffle aggregations, wide transformations with many columns, or UDFs that create large intermediate objects.

**Common Causes**:
| Cause | Indicator | Fix |
|---|---|---|
| Executor OOM from wide transforms | Error during `shuffle`, `join`, or `groupBy` | Increase executor memory or repartition input |
| Skewed partition | Single executor OOM while others are fine | Enable AQE skew join: `spark.sql.adaptive.skewJoin.enabled=true` |
| Python UDFs creating large objects | OOM during UDF execution | Use Pandas UDFs (vectorized) or native PySpark functions |

**Fix:**
```python
# Increase executor memory in Fabric notebook Spark settings (spark pool config)
# spark.executor.memory = 4g (default varies by pool size)

# Reduce data per partition
df = df.repartition(200)

# Avoid collecting broadcast data larger than spark.broadcast.blockSize
# Use SortMergeJoin instead of BroadcastHashJoin for large tables
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")  # disable auto-broadcast

# Enable off-heap memory for Tungsten
spark.conf.set("spark.memory.offHeap.enabled", "true")
spark.conf.set("spark.memory.offHeap.size", "2g")
```

**Diagnostic Query** (run in Livy session):
```python
# Check for skewed partitions (large variance = skew)
df = spark.table("your_table")
partition_sizes = df.groupBy(spark.sparkContext.partitionId().alias("pid")).count()
partition_sizes.describe("count").show()
# If max >> mean, you have data skew
```

### 3. Shuffle Fetch Failed

**Signature:** `org.apache.spark.shuffle.FetchFailedException`
**Also matches:** `Failed to get broadcast_N`, `ShuffleMapTask failed with FetchFailed`

**Root Cause:**
An executor tried to fetch shuffle data (map output) from another executor, but that executor died or the shuffle block was lost. Often a secondary symptom of OOM killing the producer executor.

**Common Causes**:
| Cause | Indicator | Fix |
|---|---|---|
| Executor lost during shuffle | `FetchFailedException` after executor OOM | Increase memory or reduce shuffle partition count |
| Network timeout | `Connection timed out` in shuffle fetch | Increase `spark.network.timeout` (default 120s) |
| Excessive shuffle data | Shuffle write > available disk | Reduce data before shuffle, add pre-filters |
| Too many shuffle partitions | Thousands of small tasks | Set `spark.sql.shuffle.partitions` to 2-4x core count |

**Fix:**
```python
# Increase executor memory to prevent the producer from dying
# Enable AQE to handle skew that might overload one executor
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Reduce shuffle data by filtering early
df = df.filter(col("date") >= "2024-01-01")  # push filter before shuffle

# Increase shuffle retry tolerance
spark.conf.set("spark.shuffle.maxRetriesOnNetIssue", "10")
spark.conf.set("spark.shuffle.retryWait", "5s")
```

### 4. Executor Lost

**Signature:** `ExecutorLostFailure (executor N exited caused by one of the running tasks)`
**Also matches:** `Lost executor N on host`

**Root Cause:**
The executor process was killed by the OS or resource manager, typically due to memory overuse (container eviction) or a JVM crash.

**Fix:**
- Check if OOM errors precede this in the log (see pattern #2)
- Reduce memory pressure: smaller partitions, less data per task
- Enable speculative execution to tolerate slow executors:

```python
spark.conf.set("spark.speculation", "true")
spark.conf.set("spark.speculation.multiplier", "1.5")
```

### 5. Analysis Exception (SQL / Schema Error)

**Signature:** `org.apache.spark.sql.AnalysisException`
**Also matches:** `cannot resolve column`, `cannot up cast`, `Column 'X' does not exist`

**Root Cause:**
Spark cannot resolve a column name, function, or data type at query planning time. Caused by typos in column names, schema mismatches, or using a column that was dropped/renamed earlier.

**Fix:**
```python
# Print schema to verify column names
df.printSchema()

# Check available columns
print(df.columns)

# Use backticks for column names with spaces or special chars
df.select("`my column`")

# Verify the column exists before using it
assert "user_id" in df.columns, "user_id column missing"
```

### 6. File Not Found / Path Error

**Signature:** `java.io.FileNotFoundException`
**Also matches:** `Path does not exist`, `No such file or directory`

**Root Cause:**
A file or directory path referenced in the code does not exist in the Lakehouse or ABFSS storage. Common causes: wrong path prefix, file was deleted, or a previous write step failed.

**Fix:**
```python
# Use the correct Fabric Lakehouse path format
df = spark.read.parquet("abfss://<workspace>@<storage>.dfs.core.windows.net/<path>")

# Or use the Files shortcut in Fabric notebooks
df = spark.read.parquet("Files/my_folder/my_file.parquet")

# Check existence before reading
from pyspark.sql import SparkSession
fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
path = spark._jvm.org.apache.hadoop.fs.Path("Files/my_folder")
if not fs.exists(path):
    raise FileNotFoundError(f"Path does not exist: {path}")
```

### 7. Task Killed — Speculative Execution (Informational)

**Signature:** `TaskKilled (another attempt succeeded)`

**Root Cause:**
This is **normal behavior** from Spark's speculative execution. When a task runs slower than peers, Spark launches a duplicate. The slower duplicate is killed when the faster one completes.

**Action:**
None required. If these appear frequently (many tasks killed per stage), the cluster may be over-provisioned or data is skewed — see [performance-patterns.md](performance-patterns.md#data-skew) for skew detection.

### 8. Library Packaging Error

**Signature:** `library packaging error` in Livy log
**Also matches:** `Failed to install`, `pip install failed`

**Root Cause:**
A custom Python library or wheel file specified in the session environment failed to install — usually due to a version conflict, missing dependency, or network issue.

**Fix:**
1. Verify the library version exists for the Fabric runtime's Python version
2. Check for conflicting dependencies:
   ```bash
   pip install <lib> --dry-run
   ```
3. Upload the wheel file directly to Lakehouse Files and install inline:
   ```python
   %pip install /lakehouse/default/Files/mylib-1.0-py3-none-any.whl
   ```

### 9. Spark SQL Parse Exception

**Signature:** `org.apache.spark.sql.catalyst.parser.ParseException`

**Root Cause:**
Invalid SQL syntax in a `spark.sql("...")` call or SQL magic cell.

**Fix:**
```python
# Use triple quotes and test the SQL separately
query = """
    SELECT
        user_id,
        COUNT(*) AS event_count
    FROM events
    WHERE date >= '2024-01-01'
    GROUP BY user_id
"""
spark.sql(query).show(5)
```

### 10. Broadcast Timeout

**Signature:** `SparkException: Could not execute broadcast in N secs`
**Also matches:** `org.apache.spark.SparkException: Broadcast timeout`

**Root Cause:**
The driver took too long to broadcast a table to all executors, usually because the "small" table is actually too large for broadcast.

**Fix:**
```python
# Increase timeout (default 300s)
spark.conf.set("spark.sql.broadcastTimeout", "600")

# Or disable auto-broadcast and switch to SortMergeJoin
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "-1")

# Or explicitly hint the join type instead
from pyspark.sql.functions import broadcast
df_large.join(broadcast(df_truly_small), "key")
```

### Timeout Failures

**Symptoms**:
- `Job cancelled because SparkContext was shut down`
- `Task not serializable`
- Session transitions to `dead` state after long idle
- `Livy session has expired`

**Common Causes**:
| Cause | Indicator | Fix |
|---|---|---|
| Livy session timeout | Session `dead` after inactivity | Increase `spark.livy.server.session.timeout` or keep-alive |
| Long-running task | Single task runs for hours | Check for data skew or Cartesian join |
| Spark context shutdown | Context killed by Fabric | Check capacity throttling; retry with smaller dataset |

---

## Quick Reference Table

| Error Signature | Pattern # | Severity | Most Likely Fix |
|----------------|-----------|----------|----------------|
| `OutOfMemoryError: Java heap space` (driver) | 1 | HIGH | Replace `collect()` / `toPandas()` with `write` |
| `OutOfMemoryError` (executor) | 2 | HIGH | Increase executor memory, repartition |
| `FetchFailedException` | 3 | HIGH | Fix OOM upstream, enable AQE |
| `ExecutorLostFailure` | 4 | HIGH | Reduce memory pressure, check OOM |
| `AnalysisException` | 5 | MEDIUM | Fix column names / schema |
| `FileNotFoundException` | 6 | MEDIUM | Verify file paths |
| `TaskKilled (another attempt succeeded)` | 7 | INFO | Normal — no action needed |
| `library packaging error` | 8 | MEDIUM | Fix library version / upload wheel manually |
| `ParseException` | 9 | LOW | Fix SQL syntax |
| `Could not execute broadcast` | 10 | MEDIUM | Increase timeout or disable auto-broadcast |

---

## Reading Spark Logs via REST

> **Tip**: For completed or failed Spark applications, the [Driver and Executor Log APIs](../../../../common/SPARK-MONITORING-CORE.md#driver-and-executor-log-apis) provide direct REST access to logs without requiring an active Livy session. The [Livy Log API](../../../../common/SPARK-MONITORING-CORE.md#livy-log-api) offers byte-offset pagination for large logs.

### Retrieve Livy Session Logs

Livy exposes driver logs through the session API. This is the primary way to get Spark logs in Fabric without accessing the cluster directly.

```bash
# Get the last 100 lines of driver output
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/log?from=0&size=100" \
  --query "log" --output tsv
```

**Pagination for large logs**:
```bash
# Get total log lines first
total=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/log?from=0&size=1" \
  --query "total" --output tsv)

# Get the last 200 lines (where errors usually are)
from=$((total - 200))
[ $from -lt 0 ] && from=0
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/log?from=$from&size=200" \
  --query "log" --output tsv
```

### Retrieve Statement Output for Errors

When a Livy statement fails, the error is in the statement output:

```bash
# Get statement result (includes traceback for failed statements)
statementId="<statement-id>"
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/lakehouses/$lakehouseId/$LIVY_API_PATH/sessions/$sessionId/statements/$statementId" \
  --query "{state:state, output:output}" --output json
```

The `output` object contains:
- `status`: `"ok"` or `"error"`
- `evalue`: Error message text
- `traceback`: Full Python/Java traceback as array of strings

---

## Job Instance History

### Query Recent Job Runs

Use job instance APIs to compare runs over time and detect regressions.

The [List Item Job Instances API](https://learn.microsoft.com/en-us/rest/api/fabric/core/job-scheduler/list-item-job-instances)
documents only `continuationToken` as a query parameter, not `limit` or OData
sorting/filtering. Start with the queryless endpoint, preserve the full response,
and collect every `value` page before selecting recent runs client-side.
The service retains a limited history (for most items, the 100 most recently
completed instances); even complete pagination is not an unlimited historical audit.
Prefer the service's continuation URI after validating the exact original
endpoint and query prefix, preserving its encoding. Only URL-encode a raw
continuation token when no URI is supplied.

```bash
# Collect the retained history, including all continuation pages.
base="$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances"
next="$base"
jobInstances='[]'
while [ -n "$next" ]; do
  page=$(az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
    --headers "x-ms-fabric-skill=spark-cli" --url "$next" --output json) || exit 1
  jobInstances=$(jq -cn --argjson runs "$jobInstances" --argjson page "$page" \
    '$runs + ($page.value | if type == "array" then . else error("Missing value array") end)') || exit 1
  token=$(printf '%s' "$page" | jq -r '.continuationToken // empty') || exit 1
  uri=$(printf '%s' "$page" | jq -r '.continuationUri // empty') || exit 1
  next=''
  if [ -n "$uri" ]; then
    case "$uri" in
      "$base?continuationToken="?*) next="$uri" ;;
      *) printf '%s\n' 'Unexpected continuation URI; history is incomplete.' >&2; exit 1 ;;
    esac
  elif [ -n "$token" ]; then
    encoded=$(jq -rn --arg token "$token" '$token | @uri') || exit 1
    next="$base?continuationToken=$encoded"
  fi
done
# Select latest 10 only after pagination, not by an unsupported server-side limit.
printf '%s' "$jobInstances" | jq 'sort_by(.startTimeUtc) | reverse | .[:10] |
  map({id, status, start: .startTimeUtc, end: .endTimeUtc, failureReason})'
```

For an empty-history claim, retain the unfiltered responses and establish that no
continuation page remains. A filtered/latest-N view, an incomplete page sequence,
or a failed request cannot prove the item has no retained job history.

### Compare Job Durations

Using the fully collected `jobInstances` array above, filter and sort client-side:

```bash
# Select the latest 20 completed instances for trend analysis.
printf '%s' "$jobInstances" | jq '[.[] | select(.status=="Completed")] |
  sort_by(.startTimeUtc) | reverse | .[:20] | map({start: .startTimeUtc, end: .endTimeUtc})'
```

For duration calculations, keep the same client-side ordering and selection:

```bash
printf '%s' "$jobInstances" | jq '[.[] | select(.status=="Completed")] |
  sort_by(.startTimeUtc) | reverse | .[:20][] |
  {start: .startTimeUtc, end: .endTimeUtc, status: .status}'
```

### Detect Regressions

A job is regressing if the latest successful run is significantly slower than the median of the previous runs. Compare the last run's duration against the median of the 5 runs before it. If the ratio exceeds 2x, investigate data volume changes first, then Spark configuration drift.

---

## Failure Triage Workflow

Follow this decision tree when a Spark job fails in Fabric.

### Step 1: Get the Job Status

```bash
# What is the job's current state?
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances/$jobInstanceId" \
  --query "{status:status, failureReason:failureReason}" --output json
```

| Status | Next Step |
|---|---|
| `Failed` | Go to Step 2 — read the failure reason |
| `Cancelled` | Check if user-cancelled or timeout-killed (Step 3) |
| `InProgress` | Job is still running — check elapsed time vs historical average |
| `Completed` | Job succeeded — if performance concern, go to [performance-patterns.md](performance-patterns.md) |
| `Deduped` | Another instance was already running — check that instance instead |

### Step 2: Classify the Failure

Read `failureReason` from the job instance response. Match against the categories in [Failure Classification](#failure-classification):

1. **Contains `OutOfMemoryError`** → OOM category
2. **Contains `FetchFailedException` or `ShuffleMapTask`** → Shuffle failure
3. **Contains `timeout` or `expired`** → Timeout category
4. **Contains `ClassNotFoundException` or `AnalysisException`** → Dependency/config error
5. **None of the above** → Read the full Livy session log (Step 4)

### Step 3: Check for Cancellation Cause

```bash
# Was the job cancelled by the user or by the system?
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/items/$notebookId/jobs/instances/$jobInstanceId" \
  --query "{status:status, invokeType:invokeType, failureReason:failureReason}" --output json
```

- `invokeType: "Manual"` + cancelled → user cancelled
- System cancellation → check capacity throttling or session timeout

### Step 4: Read the Logs

If `failureReason` is not descriptive enough, retrieve the Livy session logs using the patterns in [Reading Spark Logs via REST](#reading-spark-logs-via-rest). Search for:
- `ERROR` or `FATAL` log lines
- Java exception stack traces (lines starting with `at `)
- Python tracebacks (lines starting with `Traceback` or `File "`)

> **Alternative**: Use the [Driver Log API](../../../../common/SPARK-MONITORING-CORE.md#driver-and-executor-log-apis) to access driver stderr directly, or the [Executor Log API](../../../../common/SPARK-MONITORING-CORE.md#driver-and-executor-log-apis) for per-executor logs. These APIs work on completed applications without an active session.

### Step 4b: Check Spark Advisor

Before manual analysis, check if the Spark Advisor has already identified the issue:

```bash
az rest --method get --resource "$FABRIC_RESOURCE_SCOPE" \
  --url "$FABRIC_API_URL/workspaces/$workspaceId/notebooks/$notebookId/livySessions/$livyId/applications/$appId/advice" \
  --output json
```

The Advisor automatically detects data skew, time skew, and task errors. See [Spark Advisor API](../../../../common/SPARK-MONITORING-CORE.md#spark-advisor-api).

### Step 5: Apply the Fix

Once classified, apply the remediation from the corresponding category in [Failure Classification](#failure-classification). After applying, re-run the job and monitor using the [Job Instance History](#job-instance-history) patterns to confirm the fix.
