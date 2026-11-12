# CTD — design mode

## Purpose

Produce the Delta table DDL and schema rationale for a new Cumulative Table Design in the Silver layer. No Fabric API calls are made in this mode — output is schema DDL and design guidance only.

## Pre-conditions

Before writing any DDL, confirm all of the following with the user or from context. If any item is missing, ask in a single message listing all gaps — do not ask one at a time:

1. **Entity key** — the stable, non-null business key (e.g., `user_id`, `device_id`). Must be a single column or a deterministic composite key expressed as a single string via SHA2/MD5 if composite.
2. **Scalar state columns** — the current-state fields preserved as top-level columns (e.g., `subscription_plan`, `country`, `is_premium`). These are coalesced today-preferred; if today's value is null, yesterday's value is kept.
3. **History metric columns** — what is observed per period (e.g., `sessions`, `revenue_usd`, `pages_viewed`). These live inside the `history ARRAY<STRUCT<...>>`.
4. **Aggregation semantics per metric** — how each metric is collapsed to one value per (entity, day): sum, max, last non-null, etc. This determines Cell 2 of the pipeline.
5. **Observation cadence** — daily assumed unless stated otherwise.
6. **Retention window** — how many days of history to retain. Default to 365 if unspecified; always declare it explicitly in the DDL comment.
7. **Partitioning intent** — entity cardinality: < 5 M (no partition), >= 5 M (PARTITIONED BY month of `first_seen_date`).

---

## Schema DDL template

Produce a Spark SQL DDL block using this template. Annotate every column with a comment. Do NOT skip comments — they are part of the deliverable.

```sql
-- ===========================================================================
-- Silver: <entity>_cumulative
-- Pattern : Cumulative Table Design (CTD)
-- Cadence : daily (processing_date = business date of the snapshot)
-- Retention: <N> days of history retained per entity
-- Key      : <entity_id> (stable, non-null business key)
-- Write    : full table overwrite each run (or replaceWhere by first_seen_date month for >= 5 M entities)
-- ===========================================================================
CREATE TABLE IF NOT EXISTS silver.<entity>_cumulative (

  -- ── Identity ──────────────────────────────────────────────────────────────
  entity_id           STRING        NOT NULL  COMMENT 'Stable business key. Never null. Natural or surrogate key.',

  -- ── Current state (coalesced: today preferred, yesterday as fallback) ─────
  <current_field_1>   <TYPE>                  COMMENT '<description>. Null if never observed. Updated daily via COALESCE(today, yesterday).',
  <current_field_2>   <TYPE>                  COMMENT '<description>.',

  -- ── Activity history ──────────────────────────────────────────────────────
  history             ARRAY<STRUCT<
    date              DATE,                   -- Observation date (UTC). Exactly one entry per day maximum.
    <metric_1>        <TYPE>,                 -- <description>, unit: <unit>. Null if entity had no activity on this date.
    <metric_2>        <TYPE>                  -- <description>, unit: <unit>.
  >>                                          COMMENT 'Rolling <N>-day history. Ordered descending by date (latest first). One struct per day maximum.',

  -- ── Lifecycle metadata ────────────────────────────────────────────────────
  first_seen_date     DATE                    COMMENT 'Earliest date this entity appeared in Bronze. Set on first insert; never updated.',
  last_active_date    DATE                    COMMENT 'Most recent date with non-null activity. Updated each pipeline run. Used for zombie-entity pruning.',
  updated_at          TIMESTAMP               COMMENT 'Pipeline write timestamp (UTC). Monotone increasing.'

)
USING DELTA
-- PARTITIONED BY (DATE_FORMAT(first_seen_date, 'yyyy-MM'))
-- Uncomment the line above ONLY for entity count >= 5 M.
-- WARNING: once partitioned, replaceWhere in the pipeline must identify partitions
-- by first_seen_date month (not activity date). See pipeline.md Option B.
COMMENT 'Silver cumulative table for <entity>. One row per entity. History retained for <N> days.'
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.minReaderVersion'           = '1',
  'delta.minWriterVersion'           = '2'
);
```

---

## Design decisions to document in the output

For every schema you produce, include a brief rationale section covering all five decisions:

| Decision | What to state |
|---|---|
| Why CTD over SCD2 | CTD: O(entities) rows, no `is_current` filter scan, Direct Lake friendly. SCD2: O(entities × changes) rows, requires filter pushdown on every read. |
| Why CTD over daily snapshots | Snapshots: storage = entity_count × days × row_size. CTD: storage = entity_count × 1 row, history embedded. No partition scan over date ranges. |
| Partitioning choice | None for < 5 M entities (full overwrite is fast enough). PARTITIONED BY month of `first_seen_date` for >= 5 M — enables `replaceWhere` to avoid full rewrites. Note the partition key is `first_seen_date`, not activity date. |
| Array ordering | Descending by date (latest first) — most queries need recent history; avoids full-array scan for recent-window aggregations (Pattern 4 in access.md). |
| Retention choice | State the `retention_days` value and justify it. If compliance-driven, note that Delta time travel (7-day default, configurable) supplements the array for point-in-time audit. For regulatory needs > 365 days, do not extend the array — use Delta time travel or a separate audit table. |

---

## Migration from SCD2

If the user is migrating from an existing SCD2 table, produce a two-step backfill.

**Step 1** — Create the CTD table DDL (using the template above).

**Step 2** — Backfill using PySpark (not Spark SQL — `COLLECT_LIST` is not a window function in Spark SQL and cannot be mixed with `GROUP BY`):

```python
from pyspark.sql.functions import (
    col, collect_list, struct, to_date, min as spark_min, max as spark_max,
    last, current_timestamp, sort_array
)

# Read the SCD2 source table
scd2 = spark.table("silver.<entity>_scd2")

# Group all SCD2 rows per entity into a history array
# Adapt column names to match the actual SCD2 schema
backfill = (
    scd2
    .groupBy("entity_id")
    .agg(
        # Scalar state: take the value from the most recent SCD2 row
        last("current_field_1", ignorenulls=True).alias("current_field_1"),
        last("current_field_2", ignorenulls=True).alias("current_field_2"),
        # History: one struct per SCD2 row, ordered by effective_from
        sort_array(
            collect_list(struct(
                to_date(col("effective_from")).alias("date"),
                col("<metric_from_scd2>").alias("metric_1")
            )),
            asc=True  # ascending; pipeline will sort descending on read
        ).alias("history"),
        spark_min("effective_from").cast("date").alias("first_seen_date"),
        spark_max("effective_from").cast("date").alias("last_active_date"),
        current_timestamp().alias("updated_at")
    )
)

(
    backfill
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")  # true on backfill only — schema is being established
    .saveAsTable("silver.<entity>_cumulative")
)

print(f"[OK] SCD2 backfill complete: {backfill.count()} entities migrated")
```

Notes:
- `last()` with `ignorenulls=True` requires the SCD2 rows to be ordered correctly — add `.orderBy("effective_from")` before the `groupBy` if Spark's ordering is not guaranteed.
- Apply the retention window filter to the `history` array after the backfill if the SCD2 spans more than `retention_days`.
- This is a one-time operation; run only once. After backfill, the daily pipeline takes over.

---

## Output checklist

Before finishing the `design` mode response, confirm every item:

- [ ] Entity key stated and confirmed non-null
- [ ] All scalar state columns listed with coalesce semantics and aggregation strategy documented
- [ ] History struct fields listed with types, units, nullability, and per-metric aggregation (sum / max / last)
- [ ] Retention window stated in DDL comment and in rationale
- [ ] Partitioning decision stated with the 5 M threshold and the `first_seen_date` vs activity date distinction
- [ ] TBLPROPERTIES include `autoOptimize` flags
- [ ] Rationale table included covering all 5 decisions
- [ ] Explicit callout: "Deploy this DDL via `spark-cli authoring` (Livy CREATE TABLE or notebook cell) before running the pipeline"
- [ ] If migration from SCD2: PySpark backfill provided (not Spark SQL COLLECT_LIST OVER)
