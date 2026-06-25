# MLV Incremental Refresh Patterns — Skill Resource

Skill resource for reviewing and improving **incremental refresh readiness** for
Microsoft Fabric Materialized Lake Views (MLVs). Contains user-facing guidance
and an agent routing section at the end of the file.

Use this resource when the task is about:

- why an MLV may be doing a full refresh
- how to rewrite an MLV without changing business logic
- source-table readiness for incremental refresh
- which SQL patterns are safer for refresh-friendly MLV design

> **Note:** PySpark-authored MLVs always default to **full refresh** — incremental refresh
> applies only to Spark SQL MLV definitions. If the user's MLV is PySpark-based, the
> incremental readiness review does not apply.

---

## IR-friendly syntax guide

> **Goal:** Help users write MLV queries that qualify for incremental refresh from the start.
> The authoritative Must/Prefer/Avoid for MLV authoring is in
> [`materialized-lake-view-patterns.md`](materialized-lake-view-patterns.md).
> The rules below are the **incremental-refresh-specific subset** — follow both.

### IR-friendly SQL patterns (use these)

These SQL patterns are compatible with incremental refresh per the
[official supported constructs list](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view#sql-constructs-supported-by-incremental-refresh):

| Pattern | Example | Notes |
|---|---|---|
| Simple SELECT with filters | `SELECT col1, col2 FROM src WHERE col1 IS NOT NULL` | Best case — flat projection + deterministic filter |
| `COUNT(*)`, `SUM(col)` | `SELECT region, COUNT(*) AS cnt, SUM(amount) AS total FROM src GROUP BY region` | Preferred aggregates for IR |
| `GROUP BY` with simple columns | `SELECT region, status, COUNT(*) FROM src GROUP BY region, status` | Keep grouping keys simple |
| `INNER JOIN` | `SELECT a.id, b.name FROM src_a a INNER JOIN src_b b ON a.id = b.id` | Safest join type for IR |
| `LEFT OUTER JOIN` | `SELECT a.*, b.name FROM src_a a LEFT JOIN src_b b ON a.id = b.id` | Supported — IR works only if the right-side table remains unchanged during the refresh cycle ([MS Learn](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view#sql-constructs-supported-by-incremental-refresh)) |
| `LEFT SEMI JOIN` | `SELECT a.* FROM src_a a LEFT SEMI JOIN src_b b ON a.id = b.id` | Same right-side-unchanged constraint as LEFT OUTER JOIN; returns only left-side columns (right-side columns are not projected) |
| `UNION ALL` | `SELECT * FROM src_a UNION ALL SELECT * FROM src_b` | Supported for combining multiple sources |
| `CAST` / type conversions | `SELECT CAST(amount AS DOUBLE) FROM src` | Schema reshaping is fine |
| `CASE WHEN` in SELECT | `SELECT CASE WHEN amount > 100 THEN 'High' ELSE 'Low' END AS tier FROM src` | Deterministic expressions are safe |
| `CONSTRAINT ... ON MISMATCH DROP` | See data quality patterns in materialized-lake-view-patterns.md | Row-level data quality constraints with deterministic functions |
| Subquery alias (inline view) | `SELECT sub.col FROM (SELECT col FROM src WHERE ...) sub` | Subqueries and CTEs work if they use only supported clauses |
| Non-recursive `WITH ... AS` (CTE) | `WITH clean AS (SELECT ... FROM src WHERE ...) SELECT * FROM clean` | Keep CTEs simple; avoid nesting blockers inside |

### Caution patterns (test before relying on IR)

These are not explicitly listed as supported in the official docs. They may work in
some cases but deserve extra validation:

| Pattern | Guidance |
|---|---|
| `HAVING` | Aggregate filter — not listed as supported; test whether it affects refresh eligibility |
| `GROUP BY` with `CASE WHEN` expressions | Adds complexity; test carefully |
| `Multi-level INNER JOIN chains (3+)` | May work but adds risk; consider staged Silver MLVs |
| `Subqueries in SELECT or WHERE (scalar subqueries, EXISTS)` | Per docs, triggers full refresh if any referenced table has changes |
| `AVG()`, `MIN()`, `MAX()`, `STDDEV()` (and similar aggregates other than `SUM` / `COUNT`) | IR-eligible **only when every source table is partitioned AND the partition column is included in the MLV `GROUP BY`**. Without that, falls back to full refresh. `SUM()` and `COUNT()` (without `DISTINCT`) are the special case that don't need partitioning. |

### Patterns that force full refresh (rewrite these)

If you need incremental refresh, rewrite queries that use these patterns:

| Pattern | Why it blocks IR | IR-friendly alternative |
|---|---|---|
| `SELECT DISTINCT` | Non-incremental by nature | Use `GROUP BY` instead, or move DISTINCT to a downstream view |
| `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()` | Window functions require full recomputation | Keep the MLV flat; apply windowing in a downstream query |
| `RIGHT JOIN`, `FULL OUTER JOIN`, `CROSS JOIN` | Not eligible for incremental refresh | Rewrite as `INNER JOIN` or `LEFT JOIN` where semantics allow |
| `ORDER BY`, `LIMIT` | Not on the IR-supported constructs list — forces full refresh (and adds unnecessary sort cost since materialized output ordering is not guaranteed to consumers) | Remove from the MLV; apply ordering in the consuming query |
| `current_timestamp()`, `current_date()`, `rand()` | Non-deterministic — result changes each refresh | Remove or move to a downstream view |
| `COUNT(DISTINCT col)` | DISTINCT forces full refresh | Use `COUNT(*)` on a pre-deduplicated Silver MLV |
| `date_sub(current_date(), 90)` | Rolling window changes each refresh | Use a fixed filter; manage the window in a pipeline parameter |
| `EXCEPT`, `INTERSECT` | Set operations (other than `UNION ALL`) | Rewrite as `LEFT JOIN ... WHERE ... IS NULL` or `INNER JOIN` |
| `QUALIFY`, `LATERAL VIEW`, `TABLESAMPLE` | Advanced clauses not IR-compatible | Simplify to basic SELECT/JOIN/GROUP BY |
| `WITH RECURSIVE` | Recursive CTEs | Break recursion into staged MLVs |
| User-defined functions (UDFs) | Non-deterministic or unsupported | Use built-in Spark SQL functions |

### Source table prerequisites

Before any syntax review, confirm the source tables are IR-ready:

| Prerequisite | Required | How to check |
|---|---|---|
| Delta format | Yes | Non-Delta sources (CSV, Parquet, JSON) force full refresh |
| Change Data Feed (CDF) enabled | Required for IR | `ALTER TABLE src SET TBLPROPERTIES (delta.enableChangeDataFeed = true)` |
| Append-only pattern | Required (per cycle) | Updates/deletes on sources fall back to full refresh for that cycle, even with CDF enabled |

---

## Readiness workflow

When reviewing an MLV for incremental refresh readiness:

### Step 1: Check source tables

Confirm each source meets the prerequisites above (Delta format, CDF, append-only).

### Step 2: Compare the query against the IR-friendly patterns

Walk through the MLV SQL and check each clause against the tables above.
Identify which patterns are IR-friendly, which need caution, and which force full refresh.

### Step 3: Suggest rewrites using the IR-friendly alternatives

Only suggest changes that preserve the business meaning of the query.
Use the "IR-friendly alternative" column from the "force full refresh" table.

### Step 4: Produce the report

Use this structure:

```markdown
## IR Readiness Report

**Overall Assessment:** [IR-Ready | Partially Ready | Not IR-Eligible]

### Blockers
### Warnings
### Good Practices Detected
### Source Table Checklist
### Top Recommendations
```

---

## Safe rewrite patterns

### Pattern 1: Move ranking downstream

❌ Avoid in the MLV:

```sql
CREATE MATERIALIZED LAKE VIEW gold.latest_orders AS
SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
FROM silver.orders;
```

✅ Keep the MLV deterministic:

```sql
CREATE MATERIALIZED LAKE VIEW gold.orders_base AS
SELECT customer_id, order_date, amount
FROM silver.orders;
```

Then apply ranking in a notebook or consuming query.

### Pattern 2: Remove moving time windows from the MLV

❌ Avoid:

```sql
CREATE MATERIALIZED LAKE VIEW gold.recent_sales AS
SELECT product_id, sale_date, amount
FROM silver.sales
WHERE sale_date >= date_sub(current_date(), 90);
```

✅ Prefer:

```sql
CREATE MATERIALIZED LAKE VIEW gold.sales_base AS
SELECT product_id, sale_date, amount
FROM silver.sales;
```

Then filter for “last 90 days” in the BI or notebook layer.

### Pattern 3: Prefer simpler aggregates

✅ Good refresh-friendly shape:

```sql
CREATE MATERIALIZED LAKE VIEW gold.daily_sales AS
SELECT
    order_date,
    region,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue
FROM silver.orders
GROUP BY order_date, region;
```

If users request averages, explain the tradeoff and prefer storing totals and counts when that still meets the business need.

### Pattern 4: Keep presentation logic downstream

Avoid turning the MLV into a reporting layer. Prefer raw business measures inside the MLV and format later.

---

## Source-table readiness guidance

Enable CDF on all source tables before relying on incremental refresh:

```sql
ALTER TABLE bronze.orders SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
ALTER TABLE bronze.customers SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

- Prefer append-only ingestion for fact tables
- **Deletes or updates** on source data cause fallback to full refresh for that cycle
- Verify the **Optimal refresh** toggle is enabled (default: On) in schedule settings
- For MLV chains, enable CDF on intermediate MLVs too

### Sweeping refresh cadence: incremental daily + full weekly

The most cost-effective production pattern for MLVs with CDF-enabled sources:

| Cadence | Method | Purpose |
|---------|--------|---------|
| Daily (scheduled) | Automatic (optimal refresh) | Incremental refresh via CDF — fast, low-cost, processes only new/changed rows |
| Weekly (manual or scheduled) | `REFRESH MATERIALIZED LAKE VIEW schema.view_name FULL` | Full rebuild — catches edge cases IR misses (schema drift, orphaned deletes, compaction) |

**When to use this pattern:**
- Source tables are append-heavy with occasional updates/deletes
- MLVs serve dashboards that need daily freshness
- You want cost control (IR = ~5% of full refresh cost) with weekly safety net

**Setup:**
1. Enable CDF on all source tables: `ALTER TABLE src SET TBLPROPERTIES (delta.enableChangeDataFeed = true)`
2. Create a Daily schedule via REST API or Lakehouse UI (Optimal Refresh = On)
3. Run `REFRESH MATERIALIZED LAKE VIEW ... FULL` weekly via notebook pipeline or manual trigger

**Why the weekly FULL matters:**
- Incremental refresh cannot detect: schema changes in sources, vacuum/compaction side effects, or changes that bypass CDF (e.g., direct file manipulation)
- FULL rebuild guarantees consistency — catches anything IR missed during the week
- Cost: one FULL per week ≈ same as 7 incremental refreshes (~14% overhead for 100% correctness guarantee)

> **Tip**: Schedule the weekly FULL on a low-traffic window (e.g., Sunday 3 AM) to avoid capacity contention with dashboards.

---

## Example assessment language

- **IR-Ready ✅** — no hard blockers, source prerequisites satisfied, deterministic query shape
- **Partially Ready ⚠️** — no obvious blockers but source readiness unknown or caution areas remain
- **Not IR-Eligible ❌** — one or more hard blockers present in the current definition

---

## Routing guidance for the agent

Use this resource when the user asks about incremental refresh readiness, full-refresh debugging,
or refresh-friendly SQL rewrites. Pair with `materialized-lake-view-patterns.md` for broader
MLV design guidance. See that file's reference table for full documentation links.
