# CTD — ops mode

## Purpose

Diagnose and remediate operational problems with an existing Cumulative Table Design pipeline or table. This mode is read-only unless a remediation command is explicitly recommended and confirmed. All remediations must be stated as advisory unless the user explicitly asks to apply them.

---

## Symptom → diagnosis → remediation table

| Symptom | Root cause | Remediation |
|---|---|---|
| History array has duplicate dates | ARRAY_UNION on structs with non-identical fields for the same date (e.g., two Bronze events on the same day with different values) | Add pre-aggregation step in Cell 2 (pipeline mode) to collapse to one struct per (entity, date) before the union |
| Cumulative table row count growing daily | Pipeline is using `mode("append")` instead of overwrite | Switch to full overwrite or replaceWhere (see pipeline mode Option A/B) |
| MERGE is failing with "schema mismatch" | Bronze schema changed; cumulative table schema not updated | Run schema evolution procedure (see below) |
| History arrays contain entries beyond retention_days | Pruning step is missing or filter condition is wrong | Add or fix the array_filter pruning step in Cell 4; then run VACUUM |
| Pipeline is slow (> 30 min for < 5 M entities) | Partition skew on entity_id, missing ZORDER, or large shuffle | Run diagnosis procedure (see below) |
| Table has "zombie" entities (last_active_date > 365 days ago) | Retention filter on last_active_date not applied at row level | Add row-level filter: `WHERE datediff(current_date(), last_active_date) <= retention_days * 2` |
| history column shows null for active entities | COALESCE order in the join is wrong (yesterday preferred over today) | Swap coalesce args: `coalesce(today_val, yesterday_val)` not the inverse |
| OPTIMIZE / ZORDER is timing out | Table has too many small files from repeated overwrites | Run `VACUUM` first, then `OPTIMIZE` with a shorter ZORDER key list |
| Gold exploded view is returning duplicates | Source CTD has duplicate date entries in the history array | Run duplicate detection query (see below) |

---

## Procedure: detect duplicate dates in history arrays

Run this against the Silver cumulative table to identify affected entities:

```sql
SELECT
  entity_id,
  SIZE(history)                                       AS total_entries,
  SIZE(ARRAY_DISTINCT(TRANSFORM(history, x -> x.date))) AS distinct_dates,
  SIZE(history) - SIZE(ARRAY_DISTINCT(TRANSFORM(history, x -> x.date))) AS duplicates
FROM silver.<entity>_cumulative
HAVING duplicates > 0
ORDER BY duplicates DESC
LIMIT 100;
```

If duplicates are found, the fix is in the pipeline source (Bronze aggregation), not in the CTD table itself. Remediate the Bronze-to-Silver aggregation and re-run the pipeline with `first_run = True` to rebuild from scratch, or:

```python
# One-shot deduplication of existing table (keep the last struct for each date)
from pyspark.sql.functions import col, sort_array, array_distinct, transform, struct

fixed = (
    spark.table("silver.<entity>_cumulative")
    .withColumn(
        "history",
        # Sort descending, then deduplicate by date (keep first occurrence = most recent struct)
        # Note: this approach keeps the first occurrence after sorting; for true dedup, use a UDF
        array_distinct(
            sort_array(col("history"), asc=False)
        )
    )
)
fixed.write.format("delta").mode("overwrite").option("overwriteSchema", "false").saveAsTable("silver.<entity>_cumulative")
print("[WARN] array_distinct deduplicates by full struct equality only. If two structs for the same date differ on any field, both are kept. Review Bronze aggregation to prevent recurrence.")
```

---

## Procedure: schema evolution after Bronze schema change

When a new metric column is added to Bronze and must be added to the history struct:

**Step 1** — Add the new field to the CTD DDL:

```sql
-- Alter the history struct to add the new field (requires Delta schema evolution)
ALTER TABLE silver.<entity>_cumulative
SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

-- Then update the table definition via spark.sql with mergeSchema:
```

```python
# Rewrite with new schema using mergeSchema
(
    updated_df  # DataFrame with new history struct including the new field
    .write
    .format("delta")
    .mode("overwrite")
    .option("mergeSchema", "true")
    .saveAsTable("silver.<entity>_cumulative")
)
```

**Step 2** — Backfill historical struct entries with `null` for the new field (existing entries will be null automatically with mergeSchema).

**Step 3** — Update the pipeline Cell 2 to include the new field in the today_struct.

**Step 4** — Update the Gold view DDL to expose the new column.

State explicitly: "Schema evolution with mergeSchema is a one-time operation. After the first successful write, the table schema is updated. Validate with `DESCRIBE TABLE silver.<entity>_cumulative`."

---

## Procedure: pipeline performance diagnosis

Run these queries to identify the bottleneck:

```python
# Check file count and size distribution
spark.sql(f"DESCRIBE DETAIL silver.<entity>_cumulative").select("numFiles", "sizeInBytes").show()

# Check partition stats (if partitioned)
spark.sql(f"SELECT DATE_FORMAT(first_seen_date, 'yyyy-MM') AS month, COUNT(*) AS entities FROM silver.<entity>_cumulative GROUP BY 1 ORDER BY 2 DESC").show(20)

# Check Spark UI for skew: look for tasks with 10x the median duration
# Run OPTIMIZE to fix small files
spark.sql(f"OPTIMIZE silver.<entity>_cumulative ZORDER BY (entity_id)")
```

Common fixes:

| Finding | Fix |
|---|---|
| > 10,000 files in the table | Run OPTIMIZE; set `delta.autoOptimize.optimizeWrite=true` in TBLPROPERTIES |
| One partition has 80%+ of rows | Repartition before write: `.repartition(200, col("entity_id"))` |
| FULL OUTER JOIN shuffle is slow | Repartition both sides on the join key before the join (see below) |
| ARRAY_UNION on very large arrays | Reduce retention_days or apply pruning before the union, not after |

> **Do NOT use `broadcast()` on a `full_outer` join.** Spark does not support broadcast hash join for full outer joins — the hint is silently ignored and Spark falls back to sort-merge join anyway, adding planning overhead with no benefit.

To reduce full outer join shuffle cost, pre-partition both DataFrames on the join key:

```python
# Pre-partition both sides on entity_id to co-locate matching keys
# Use the same number of partitions for both sides
num_partitions = 200  # tune based on entity count and cluster size

y_repartitioned = yesterday_cumulative.repartition(num_partitions, col(entity_id_col))
t_repartitioned = today_activity.repartition(num_partitions, col(entity_id_col))

joined = y_repartitioned.alias("y").join(
    t_repartitioned.alias("t"),
    on=entity_id_col,
    how="full_outer"
)

---

## Procedure: validate pipeline idempotency

Run the pipeline twice for the same `processing_date` on a test table and compare:

```python
count_run1 = spark.table("silver.<entity>_cumulative_test").count()
# Re-run pipeline...
count_run2 = spark.table("silver.<entity>_cumulative_test").count()

history_sizes_run1 = spark.table("silver.<entity>_cumulative_test").selectExpr("SIZE(history) as h").agg({"h": "sum"}).collect()[0][0]
# Re-run pipeline...
history_sizes_run2 = spark.table("silver.<entity>_cumulative_test").selectExpr("SIZE(history) as h").agg({"h": "sum"}).collect()[0][0]

assert count_run1 == count_run2, f"Row count changed: {count_run1} -> {count_run2}"
assert history_sizes_run1 == history_sizes_run2, f"History total size changed: {history_sizes_run1} -> {history_sizes_run2}"
print("[OK] Pipeline is idempotent for this processing_date.")
```

---

## VACUUM guidance

Run VACUUM after schema changes or after switching write strategies to reclaim storage:

```sql
-- Check what VACUUM would delete (dry run)
VACUUM silver.<entity>_cumulative RETAIN 168 HOURS DRY RUN;

-- Apply (minimum 168 hours / 7 days to preserve Delta time travel for audit)
VACUUM silver.<entity>_cumulative RETAIN 168 HOURS;
```

Do NOT run VACUUM with retention < 168 hours unless Delta time travel is explicitly not required downstream.
