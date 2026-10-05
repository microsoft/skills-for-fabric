# CTD — access mode

## Purpose

Produce Spark SQL / PySpark patterns to query the cumulative table, explode history to flat rows, compute date-spine metrics, or create a Gold-layer view that downstream consumers (Power BI, SQL endpoint, Fabric notebooks) can use without handling arrays directly.

---

## Pattern 1 — Point-in-time lookup (what was the entity state on a given date?)

Use this when the consumer asks: "what was user X's state on date D?"

```python
from pyspark.sql.functions import col, filter as array_filter, to_date, lit, element_at

target_date = "2024-01-10"
entity      = "user_42"

result = (
    spark.table("silver.user_cumulative")
    .filter(col("entity_id") == entity)
    .select(
        "entity_id",
        # Extract the history struct for the exact target date
        element_at(
            array_filter("history", lambda x: x["date"] == to_date(lit(target_date))),
            1
        ).alias("snapshot")
    )
    .select("entity_id", "snapshot.*")
)
result.show()
```

---

## Pattern 2 — Explode to flat rows (all entities, all history days)

Use this to build a Gold table or for analytics that need one row per (entity, date):

```sql
-- Spark SQL — explode history array to flat rows
CREATE OR REPLACE VIEW gold.user_activity_daily AS
SELECT
  c.entity_id,
  c.<current_field_1>,
  c.<current_field_2>,
  h.date                AS activity_date,
  h.<metric_1>          AS <metric_1>,
  h.<metric_2>          AS <metric_2>,
  c.first_seen_date,
  c.last_active_date
FROM silver.user_cumulative c
LATERAL VIEW OUTER EXPLODE(c.history) AS h
WHERE h.date IS NOT NULL
;
```

Or in PySpark:

```python
from pyspark.sql.functions import explode_outer, col

flat = (
    spark.table("silver.user_cumulative")
    .select(
        "entity_id",
        "<current_field_1>",
        "first_seen_date",
        "last_active_date",
        explode_outer("history").alias("h")
    )
    .select(
        "entity_id",
        "<current_field_1>",
        "first_seen_date",
        "last_active_date",
        col("h.date").alias("activity_date"),
        col("h.<metric_1>").alias("<metric_1>"),
        col("h.<metric_2>").alias("<metric_2>")
    )
)
```

---

## Pattern 3 — Date-spine join (fill gaps for inactive days)

Use when the consumer needs a complete daily series per entity, including days with no activity:

```python
from pyspark.sql.functions import sequence, explode, to_date, lit, col, coalesce, lit as spark_lit
from pyspark.sql import functions as F

# Generate a date spine for the last N days
spine = spark.range(1).select(
    explode(sequence(
        to_date(lit("2024-01-01")),
        to_date(lit("2024-01-31"))
    )).alias("date")
)

entities = spark.table("silver.user_cumulative").select("entity_id").distinct()

# Cross-join entities x date-spine, then left-join to exploded history
date_spine = entities.crossJoin(spine)

flat = (
    spark.table("silver.user_cumulative")
    .select("entity_id", explode_outer("history").alias("h"))
    .select("entity_id", col("h.date").alias("date"), col("h.<metric_1>").alias("<metric_1>"))
)

result = (
    date_spine
    .join(flat, on=["entity_id", "date"], how="left")
    .withColumn("<metric_1>", coalesce(col("<metric_1>"), spark_lit(0)))  # fill gaps with 0
    .orderBy("entity_id", "date")
)
```

---

## Pattern 4 — Rolling window aggregation over the history array

Use for "how many sessions did this user have in the last 7 days?" without exploding:

```sql
-- Spark SQL — aggregate over history array in-place
SELECT
  entity_id,
  AGGREGATE(
    FILTER(history, x -> datediff(current_date(), x.date) <= 7),
    0L,
    (acc, x) -> acc + COALESCE(x.<metric_1>, 0)
  ) AS metric_1_last_7d,
  AGGREGATE(
    FILTER(history, x -> datediff(current_date(), x.date) <= 30),
    0L,
    (acc, x) -> acc + COALESCE(x.<metric_1>, 0)
  ) AS metric_1_last_30d
FROM silver.user_cumulative
;
```

---

## Pattern 5 — Gold table for Power BI Direct Lake

Explode to flat rows, write as a Delta table in the Gold lakehouse, ZORDER for scan performance.

```python
# Gold write — delegate full Gold setup to e2e-medallion-architecture
from pyspark.sql.functions import explode_outer, col

flat_gold = (
    spark.table("silver.user_cumulative")
    .select("entity_id", "<current_field_1>", "last_active_date", explode_outer("history").alias("h"))
    .select(
        "entity_id",
        "<current_field_1>",
        "last_active_date",
        col("h.date").alias("activity_date"),
        col("h.<metric_1>").alias("<metric_1>"),
        col("h.<metric_2>").alias("<metric_2>")
    )
    .filter(col("activity_date").isNotNull())
)

(
    flat_gold.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "false")
    .saveAsTable("gold.user_activity_daily")
)

spark.sql("OPTIMIZE gold.user_activity_daily ZORDER BY (entity_id, activity_date)")
print("[OK] Gold table written and optimized")
```

**After writing the Gold table**, hand off to:
- `semantic-model-authoring` for Direct Lake semantic model creation
- `e2e-medallion-architecture` for pipeline orchestration

---

## SQL endpoint consumers (no Spark)

If the downstream consumer uses the Lakehouse SQL endpoint (e.g., Power BI Import or Fabric SQL query editor), the array column is **not directly queryable** in T-SQL. Provide the exploded Gold view instead:

```sql
-- Exposed via SQL endpoint as gold.user_activity_daily
-- Consumer can query without any array handling:
SELECT entity_id, activity_date, <metric_1>
FROM gold.user_activity_daily
WHERE activity_date >= DATEADD(day, -30, GETDATE())
```

State explicitly: "The Silver CTD table requires Spark to query arrays. Use the Gold exploded view for SQL endpoint access."

---

## Performance notes

| Pattern | Recommended for | Caution |
|---|---|---|
| Point-in-time (Pattern 1) | Interactive, single-entity lookups | Inefficient on large tables without entity_id predicate pushdown — always filter on entity_id first |
| Explode (Pattern 2) | Batch Gold writes | Can be expensive for large history arrays; partition the Gold write by activity_date month |
| Date-spine (Pattern 3) | Reporting requiring complete series | Cross-join can explode if entity count x date range is very large — limit to active entities or bounded windows |
| In-array aggregation (Pattern 4) | Real-time dashboards on Silver directly | Requires Spark; not available via SQL endpoint |
| Gold table (Pattern 5) | Power BI, SQL consumers | Preferred path for all downstream consumers |
