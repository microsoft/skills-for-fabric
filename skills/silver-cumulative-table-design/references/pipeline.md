# CTD — pipeline mode

## Purpose

Produce the daily incremental PySpark notebook cell(s) that update the cumulative table. This reference is the single source of truth for the full-outer-join logic, write strategy, pruning, and validation steps.

## Pipeline parameters (always parameterize, never hardcode)

```python
# Cell 1 — parameters (Fabric notebook parameter cell: tag as "parameters")
processing_date = "2024-01-15"   # override at runtime; default to yesterday
retention_days  = 365            # rolling window; match the DDL comment
entity_id_col   = "entity_id"    # business key column name in source table
source_table    = "bronze.events_raw"          # Bronze source table (fully qualified)
target_table    = "silver.user_cumulative"     # Silver CTD target table

# Scalar state columns: list of column names from Bronze that become top-level state fields
# on the CTD table. These are coalesced today-preferred, yesterday-fallback.
# Replace with the actual column names for this entity.
STATE_COLS = ["subscription_plan", "country", "is_premium"]

# History metric columns: list of column names from Bronze to aggregate per day.
# These become fields inside the history ARRAY<STRUCT<...>>.
# Replace with the actual column names for this entity.
METRIC_COLS = ["sessions", "revenue_usd", "pages_viewed"]
```

---

## Write strategy decision

Choose ONE strategy based on table size and partitioning:

| Condition | Strategy | When to use |
|---|---|---|
| Table has NO partition column | Full table overwrite (Option A) | Entity count < 5 M; simple and safe |
| Table is PARTITIONED BY month of `first_seen_date` | `replaceWhere` per entity-cohort partition (Option B) | Entity count >= 5 M; see partition note below |
| Table is very large and only a known subset of entities is active today | MERGE by entity_id (Option C) | Use only when overwrite is too expensive; MERGE is slower per row but avoids full rewrite |

**Default for new tables: full table overwrite (Option A)** — it is idempotent, avoids MERGE lock contention, and is simplest to debug.

> **Partition note for Option B**: The CTD table is partitioned by `first_seen_date` month (the month the entity first appeared), NOT by `activity_date`. An entity active today but first seen in 2022 lives in the 2022 partition. Option B must therefore overwrite ALL partitions that contain entities active today — which requires loading the cumulative table to find which `first_seen_date` months those entities belong to, not just looking at `today_activity.date`. Use Option A unless you have a measured performance reason to use Option B.

---

## Cell 2 — today's activity preparation

```python
from pyspark.sql.functions import col, to_date, lit, coalesce, current_timestamp, sum as spark_sum, last
from datetime import datetime

proc_date = datetime.strptime(processing_date, "%Y-%m-%d").date()

# Read today's raw events from Bronze, filtered to processing_date
raw_today = (
    spark.table(source_table)
    .filter(col("event_date") == lit(proc_date))
)

# Build aggregation expressions:
# - For scalar STATE_COLS: take the last non-null value observed today (e.g., most recent plan)
# - For METRIC_COLS: sum all events for that entity today
# Adapt these aggregations to the actual semantics of your columns.
state_agg  = [last(c, ignorenulls=True).alias(c) for c in STATE_COLS]
metric_agg = [spark_sum(c).alias(c) for c in METRIC_COLS]

today_activity = (
    raw_today
    .groupBy(entity_id_col)
    .agg(*(state_agg + metric_agg))
    .withColumn("date", lit(proc_date).cast("date"))
)

today_count = today_activity.count()
assert today_count >= 0, "today_activity aggregation returned negative count — check source table"
print(f"[INFO] today_activity row count: {today_count} (processing_date={proc_date})")
```

Adapt the aggregation strategy per column:
- `last(col, ignorenulls=True)` for categorical state (plan, status, country)
- `spark_sum(col)` for additive metrics (sessions, revenue, page views)
- `max(col)` for high-watermarks (max_level_reached)
- Do NOT use `first()` — ordering is not guaranteed without explicit sort

---

## Cell 3 — load yesterday's cumulative table

```python
from pyspark.sql.utils import AnalysisException

# Read the current cumulative table (yesterday's state).
# On first run the table does not exist yet — create an empty DataFrame
# with the correct schema by reading the DDL schema from the target table definition
# (which must have been created first via spark-cli authoring / Livy DDL).
first_run = False
try:
    yesterday_cumulative = spark.table(target_table)
    yesterday_count = yesterday_cumulative.count()
    print(f"[INFO] yesterday_cumulative row count: {yesterday_count}")
except AnalysisException:
    # Table does not exist: this is the first pipeline run.
    # Create an empty DataFrame with the same schema as today_activity extended with CTD columns.
    # WARNING: do NOT guess the schema here — deploy the DDL first via spark-cli authoring,
    # then re-run this pipeline. The schema must match the DDL exactly.
    raise RuntimeError(
        f"Target table '{target_table}' does not exist. "
        "Deploy the DDL first using spark-cli authoring (CREATE TABLE via Livy), "
        "then re-run this pipeline. On the very first run after DDL creation, "
        "the table exists but is empty — the pipeline will handle that correctly."
    )
```

> **First run handling**: After the DDL is deployed, the table exists but is empty. The `FULL OUTER JOIN` with an empty left side will produce a result containing only today's entities with `null` history — this is correct. The `coalesce(col("y.history"), array())` in Cell 4 handles this case.

---

## Cell 4 — full outer join and history accumulation

```python
from pyspark.sql.functions import (
    array, array_union, struct, col, coalesce,
    filter as array_filter, datediff, current_date, current_timestamp,
    size, when, transform, array_distinct
)

# Aliases to disambiguate join columns
y = yesterday_cumulative.alias("y")
t = today_activity.alias("t")

# FULL OUTER JOIN: captures new entities (only in t) AND dormant entities (only in y)
joined = y.join(t, on=entity_id_col, how="full_outer")

# Build the today struct for history insertion (only when entity was active today)
today_struct = struct(
    col(f"t.date").alias("date"),
    *[col(f"t.{m}").alias(m) for m in METRIC_COLS]
)

# Build scalar state coalesce expressions (today preferred, yesterday fallback)
state_exprs = [
    coalesce(col(f"t.{c}"), col(f"y.{c}")).alias(c)
    for c in STATE_COLS
]

cumulative_new = joined.select(
    # Identity: COALESCE from both sides — either can be null in a full outer join
    coalesce(col(f"t.{entity_id_col}"), col(f"y.{entity_id_col}")).alias(entity_id_col),

    # Scalar state: today preferred, yesterday as fallback
    *state_exprs,

    # History accumulation:
    # - If entity was active today (t side not null): append today_struct to yesterday's history
    # - If entity was dormant today (t side null): carry forward yesterday's history unchanged
    when(
        col(f"t.{entity_id_col}").isNotNull(),
        array_union(
            coalesce(col("y.history"), array()),   # yesterday's history (empty array on first run)
            array(today_struct)                     # append today as a new struct element
        )
    ).otherwise(col("y.history")).alias("history"),

    # Lifecycle metadata
    coalesce(col("y.first_seen_date"), col(f"t.date")).alias("first_seen_date"),
    coalesce(col(f"t.date"), col("y.last_active_date")).alias("last_active_date"),
    current_timestamp().alias("updated_at")
)

# Pruning: remove history entries older than retention_days
cumulative_pruned = cumulative_new.withColumn(
    "history",
    array_filter("history", lambda x: datediff(current_date(), x["date"]) <= retention_days)
)

# Deduplication guard: assert at most one struct per date per entity
# Uses TRANSFORM to extract the date field, then ARRAY_DISTINCT to deduplicate dates only
dupe_check = (
    cumulative_pruned
    .select(
        col(entity_id_col),
        size("history").alias("total"),
        size(array_distinct(transform("history", lambda x: x["date"]))).alias("distinct_dates")
    )
    .filter(col("total") != col("distinct_dates"))
)
dupe_count = dupe_check.count()
if dupe_count > 0:
    raise ValueError(
        f"[ABORT] Duplicate dates detected in history array for {dupe_count} entities. "
        "Root cause is in today_activity aggregation (Cell 2) or Bronze source. "
        "Fix the aggregation to produce one row per (entity, date) before re-running."
    )

cumulative_count = cumulative_pruned.count()
print(f"[INFO] cumulative_pruned row count: {cumulative_count}")
assert cumulative_count >= today_count, \
    f"Row count decreased ({cumulative_count} < {today_count}): FULL OUTER JOIN likely lost rows"
```

---

## Cell 5 — write to Delta

### Option A — full table overwrite (default, recommended for < 5 M entities)

```python
(
    cumulative_pruned
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "false")   # fail on schema change — use "true" ONLY during explicit migration
    .saveAsTable(target_table)
)
print(f"[OK] Written to {target_table} — full overwrite, {cumulative_count} rows")
```

### Option B — replaceWhere by first_seen_date cohort partition (>= 5 M entities)

> **Important**: `replaceWhere` overwrites the partitions that contain the rows being written.
> Because the CTD table is partitioned by `first_seen_date` month (not activity date),
> we must identify which `first_seen_date` partitions are occupied by entities active today.
> This requires a lookup into the existing cumulative table.

```python
# Find the first_seen_date partition months for entities active today
active_entity_ids = today_activity.select(entity_id_col)

affected_partitions = (
    yesterday_cumulative
    .join(active_entity_ids, on=entity_id_col, how="inner")
    .selectExpr(f"DATE_FORMAT(first_seen_date, 'yyyy-MM') AS cohort_month")
    .distinct()
    .rdd.flatMap(lambda x: x).collect()
)

if not affected_partitions:
    print("[SKIP] No active entities found in cumulative table — nothing to replaceWhere")
else:
    replace_condition = " OR ".join(
        [f"DATE_FORMAT(first_seen_date, 'yyyy-MM') = '{m}'" for m in affected_partitions]
    )
    (
        cumulative_pruned
        .filter(replace_condition)
        .write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", replace_condition)
        .option("overwriteSchema", "false")
        .saveAsTable(target_table)
    )
    print(f"[OK] replaceWhere on cohort_months: {affected_partitions}")
```

### Option C — MERGE by entity_id (use only when overwrite is too expensive)

```python
from delta.tables import DeltaTable

# Idempotency guard: if today's date is already in any history entry, the pipeline already ran
already_processed = (
    spark.table(target_table)
    .filter(f"array_contains(transform(history, x -> x.date), DATE('{proc_date}'))")
    .limit(1)
    .count()
)
if already_processed > 0:
    print(f"[SKIP] processing_date={proc_date} already present in cumulative table. Pipeline is a no-op (idempotent).")
    dbutils.notebook.exit("ALREADY_PROCESSED")  # Fabric-only: use only in interactive/pipeline notebooks

delta_table = DeltaTable.forName(spark, target_table)

(
    delta_table.alias("target")
    .merge(
        cumulative_pruned.alias("source"),
        f"target.{entity_id_col} = source.{entity_id_col}"
    )
    .whenMatchedUpdateAll()
    .whenNotMatchedInsertAll()
    .execute()
)
print(f"[OK] MERGE complete on {target_table}")
```

---

## Cell 6 — post-write optimization and validation

```python
from pyspark.sql.functions import size, array_filter, datediff, current_date

# Optimize and ZORDER for entity_id predicate pushdown on future reads
spark.sql(f"OPTIMIZE {target_table} ZORDER BY ({entity_id_col})")

# Final row count — should match or exceed cumulative_count (MERGE may differ)
final_count = spark.table(target_table).count()
print(f"[VALIDATION] {target_table} final row count: {final_count}")

# Warn on entities with an empty history array (can indicate Bronze coverage gap)
empty_history_count = spark.table(target_table).filter(size("history") == 0).count()
if empty_history_count > 0:
    print(f"[WARN] {empty_history_count} entities have empty history arrays — investigate Bronze for {proc_date}")

# Assert pruning was applied correctly: no history entry older than retention_days
stale_count = (
    spark.table(target_table)
    .select(
        col(entity_id_col),
        array_filter("history", lambda x: datediff(current_date(), x["date"]) > retention_days).alias("stale")
    )
    .filter(size("stale") > 0)
    .count()
)
if stale_count > 0:
    raise ValueError(
        f"[ERROR] {stale_count} entities have history entries beyond retention_days={retention_days}. "
        "Pruning in Cell 4 did not apply. Do NOT proceed — investigate before next run."
    )

print("[OK] All post-write validations passed.")
```

---

## Idempotency contract

The pipeline MUST be idempotent for a given `processing_date`. Strategy determines the guarantee:

| Strategy | Idempotency guarantee | Notes |
|---|---|---|
| Option A (full overwrite) | Inherent — overwrite replaces the entire table | Safest; rerunning is always correct |
| Option B (replaceWhere) | Inherent within affected partitions | Correct if affected_partitions computation is deterministic |
| Option C (MERGE) | Conditional — depends on the idempotency guard in Cell 5 | Guard must run before MERGE; `dbutils.notebook.exit()` is Fabric-specific |

---

## Scheduling

Hand off scheduling to `spark-cli` mlv mode or Fabric Data Pipeline:

- Daily schedule: run at `02:00 UTC` (after Bronze ingestion completes)
- Pass `processing_date` as pipeline parameter: `@formatDateTime(addDays(utcNow(), -1), 'yyyy-MM-dd')`
- Retry: 2 retries with 5-minute backoff for transient Spark failures
- Alert: on failure, notify via Activator or Data Factory email activity
