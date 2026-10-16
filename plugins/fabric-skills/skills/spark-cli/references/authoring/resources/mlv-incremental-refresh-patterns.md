# MLV Incremental Refresh Patterns — Skill Resource

Skill resource for reviewing and improving **incremental refresh readiness** for
Microsoft Fabric Materialized Lake Views (MLVs). Contains user-facing guidance
and an agent routing section at the end of the file.

Use this resource when the task is about:

- creating a Spark SQL MLV intended for incremental refresh
- selecting or reviewing output keys for a `REFRESH_HINT`
- why an MLV may be doing a full refresh
- how to rewrite an MLV without changing business logic
- source-table readiness for incremental refresh
- which SQL patterns are safer for refresh-friendly MLV design

> **Note:** PySpark-authored MLVs always default to **full refresh** — incremental refresh
> applies only to Spark SQL MLV definitions. If the user's MLV is PySpark-based, the
> incremental readiness review does not apply.

## Refresh lifecycle and change patterns

Executing `CREATE MATERIALIZED LAKE VIEW` or `CREATE OR REPLACE MATERIALIZED LAKE VIEW`
performs a **Full refresh**, with or without `REFRESH_HINT`. This is the initial
materialization, not a failed attempt at incremental refresh. Only subsequent
refreshes of the existing MLV, including lineage refreshes, can be incremental.
Do not rerun creation/replacement on every refresh cycle.

With Optimal refresh enabled, use this decision table for subsequent refreshes:

| Condition | Expected behavior |
|---|---|
| Spark SQL definition, Delta sources, no new source delta commits | No refresh |
| Supported query, CDF on every source, append-only changes | Incremental eligible; a hint is not required for inserts alone |
| Supported query, CDF on every source, updates/deletes, compatible output key declared in `REFRESH_HINT` | Incremental eligible, including non-append changes |
| Updates/deletes without a compatible refresh hint | Full refresh, even with CDF and supported SQL |
| Source schema changes between cycles (added, removed, or renamed columns) | Full refresh **even with a refresh hint** |
| Missing CDF on any source Delta table | No refresh or Full, not Incremental |
| PySpark-decorated definition or any non-Delta source | Full refresh; Optimal refresh does not apply |
| Unsupported SQL, Optimal refresh disabled, or explicitly requested Full mode | Full refresh |

Eligibility is not a guarantee: the engine can choose Full when incremental
processing would cost more. Do not promise an incremental run based on the hint
or a successful job alone. SQL `REFRESH MATERIALIZED LAKE VIEW ... FULL` forces
Full; do not invent `REFRESH ... INCREMENTAL`.

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
| `COUNT(*)`, `SUM(col)`, `MIN(col)`, `MAX(col)` | `SELECT region, COUNT(*) AS cnt, MIN(amount) AS smallest FROM src GROUP BY region` | These aggregates, without `DISTINCT`, do not require source partitioning |
| `GROUP BY` with simple columns | `SELECT region, status, COUNT(*) FROM src GROUP BY region, status` | Project every grouping column in the SELECT list |
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

Separate undocumented query shapes from documented conditional support:

| Pattern | Guidance |
|---|---|
| `HAVING` | Aggregate filter — not listed as supported; test whether it affects refresh eligibility |
| `GROUP BY` with `CASE WHEN` expressions | Adds complexity; test carefully |
| `Multi-level INNER JOIN chains (3+)` | May work but adds risk; consider staged Silver MLVs |
| `Subqueries in SELECT or WHERE (scalar subqueries, EXISTS)` | Per docs, triggers full refresh if any referenced table has changes |
| `AVG()`, `STDDEV()`, and aggregates other than non-distinct `SUM` / `COUNT` / `MIN` / `MAX` | Documented conditional support: every source table must be partitioned and its partition column included in the MLV `GROUP BY`. Project all grouping columns. Without these conditions, Full refresh. |
| Mixing `SUM` / `COUNT` / `MIN` / `MAX` with another aggregate, such as `AVG` | The partitioning condition applies to the **whole query**. A refresh hint or output partitioning alone does not remove source-partition requirements. |

Keep the documented right-side-unchanged restriction for LEFT OUTER/SEMI JOIN
visible, including when proposing a refresh hint. Exact behavior for hinted joins
with right-side mutations remains a product-confirmation item; do not claim that
the hint overrides the restriction or reject all hinted supported queries.

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
| Change pattern and row identity | Conditional | Inserts alone do not require a hint. Updates/deletes need a compatible `REFRESH_HINT` on the MLV output |
| Optimal refresh | Required for automatic IR selection | Verify the lineage toggle or execution definition uses Optimal rather than Full |

---

## Refresh hints and output-key selection (preview)

Use the [deletes/updates reference](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/optimal-refresh-handling-deletes-updates)
for the hint syntax. A hint declares identity in the **final output schema**,
not a source-table primary key, an enforced constraint, or a request to force IR.
Fabric does not check uniqueness at runtime; duplicate declared keys can produce
inconsistent results without warnings.

### Identify, optionally validate, then ask for review

1. Establish the result grain and source change pattern. Identify candidate
   columns from the user's knowledge, an established output-key contract, or
   optional data validation. Validation is **one way** to identify keys, not a
   mandatory prerequisite. Do not assume a column named `id` is unique.
2. Explain the candidate single/composite key and why it identifies output rows.
   Offer **Validate candidate key** or **Skip validation and supply/confirm keys**.
   Do not run potentially expensive scans without the user's choice.
3. If validating, check the complete proposed query result, not just an input
   table or the old MLV when the proposed definition changes its grain. Account
   for joins, UNION ALL branches, projections, casts, and constraints. Report
   scope, duplicate groups, NULL-key count, and limitations. A sample, empty
   result, or current snapshot does not prove future uniqueness.
4. **Even after validation succeeds**, show the selected output columns and
   results and ask the user to review and approve the key before adding or
   deploying the hint. Passing validation is not deployment approval.
5. If validation is skipped, ask the user to supply/confirm the unique output
   column(s), show the risk, and obtain approval. Record **user-confirmed;
   uniqueness unverified**. Never invent a key to bypass this gate.
6. If validation is unavailable or errors, say **"I could not verify uniqueness"**
   and ask the user to provide the unique output column(s) to proceed. Do not
   silently switch to an inferred key. If validation finds duplicates or NULLs,
   report them and request corrected columns or an approved design change; do
   not deploy a known-invalid candidate.

Use `ask_user` when available. A generic "proceed" before the candidate key was
presented is not approval of that key. For offline code-only requests without
an approved key, provide a clearly labeled template or an append-only definition
without a hint and state the limitation; do not present a guessed key as ready
to deploy. Hint validation/selection is unnecessary for append-only IR without
a hint.

### Optional data checks

For a proposed composite key `(order_id, item_id)`, run these checks against the
**exact output**. For a new/changed definition, substitute its SELECT as the
`candidate_output` CTE instead of checking an outdated persisted definition:

```sql
WITH candidate_output AS (
    SELECT order_id, item_id FROM gold.order_items
)
SELECT order_id, item_id, COUNT(*) AS row_count
FROM candidate_output
GROUP BY order_id, item_id
HAVING COUNT(*) > 1;
```

```sql
WITH candidate_output AS (
    SELECT order_id, item_id FROM gold.order_items
)
SELECT COUNT(*) AS null_keys
FROM candidate_output
WHERE order_id IS NULL OR item_id IS NULL;
```

The duplicate query must return no groups. The NULL query always returns one
row: inspect the **numeric `null_keys` value**, which must be zero for this
candidate check. Check **every** component; do not concatenate columns to test
uniqueness. Reassess after definition/source changes and establish how the
output-key contract will remain valid as data changes.

### Authoring with an approved key

This example assumes the user reviewed and approved `(order_id, item_id)`:

```sql
ALTER TABLE silver.order_line_items
SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE MATERIALIZED LAKE VIEW gold.order_items
(
    REFRESH_HINT order_item_key UNIQUE (order_id, item_id)
)
PARTITIONED BY (order_date)
AS
SELECT order_id, item_id, order_date, quantity, unit_price,
       quantity * unit_price AS line_total
FROM silver.order_line_items;
```

The hint follows any constraint block and precedes `PARTITIONED BY`,
`TBLPROPERTIES`, and `AS`. Use output column aliases, not qualified source names.
Partitioning can improve efficiency but is not a substitute for row identity.
The CREATE OR REPLACE above is Full; subsequent eligible refreshes can be IR.
When replacing an existing MLV, preserve its business query, constraints,
partitioning, and table properties unless the user approves changing them.

### Key-design and mutation edge cases

- **Joins:** source uniqueness may be lost through fan-out. Select the key at
  the final grain; never add DISTINCT or change a join merely to pass validation.
- **UNION ALL:** validate across all branches, not each branch separately.
  Add a source discriminator only if it preserves the approved business model.
- **Aggregates:** evaluate the complete grouping tuple as output identity.
  Nullable groups, rollups, and global/empty aggregates need explicit review;
  do not fabricate keys or add GROUP BY columns that change the result grain.
- **Casts/projections:** lossy conversions or removed columns can collapse
  identity. Use final output values in the checks.
- **Mutation tests:** when the user requests live testing, cover inserts,
  updates, deletes, key changes, partition moves, filter/constraint transitions,
  deleting the last row in a group, and changes to multiple joined sources.
  Compare persisted output with a fresh evaluation of the intended query.
  These are test cases, not promises of undocumented engine behavior.
- **MLV chains:** each downstream definition needs its own key assessment and
  CDF on every direct dependency, including intermediate MLVs. An upstream hint
  does not declare a downstream key.

---

## Readiness workflow

When creating or reviewing an MLV for incremental refresh readiness:

### Step 1: Check source tables

Confirm each source's format, CDF status, change pattern, and schema stability.
Distinguish CREATE/replacement materialization from subsequent refreshes.

### Step 2: Compare the query against the IR-friendly patterns

Walk through the MLV SQL and check each clause against the tables above.
Identify which patterns are IR-friendly, which need caution, and which force full refresh.

### Step 3: Suggest rewrites using the IR-friendly alternatives

Only suggest changes that preserve the business meaning of the query.
Use the "IR-friendly alternative" column from the "force full refresh" table.
For updates/deletes, follow the output-key selection, optional validation, and
mandatory review workflow above before adding a refresh hint.

### Step 4: Produce the report

Use this structure:

```markdown
## IR Readiness Report

**Overall Assessment:** [IR-Eligible | Conditionally Eligible | Not IR-Eligible]

### Lifecycle: Initial Full or Subsequent Refresh
### Change Pattern and Refresh Hint
### Key Evidence: Validated | User-Confirmed/Unverified | Unknown | Invalid
### User Key Review: Approved | Pending | Declined
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

If users request averages, check the source-partitioning and grouping conditions
first. If proposing a totals/counts rewrite, preserve NULL handling and the
business denominator; `COUNT(*)` is not equivalent to `COUNT(amount)` when
`amount` can be NULL. Do not redesign a valid query solely to favor IR.

### Pattern 4: Keep presentation logic downstream

Avoid turning the MLV into a reporting layer. Prefer raw business measures inside the MLV and format later.

---

## Source-table readiness guidance

Enable CDF on all source tables before relying on incremental refresh:

```sql
ALTER TABLE bronze.orders SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
ALTER TABLE bronze.customers SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

- Append-only changes can qualify without a hint; **updates/deletes** can qualify
  with a compatible user-approved output key declared in `REFRESH_HINT`
- Verify the **Optimal refresh** toggle is enabled (default: On) in schedule settings
- For MLV chains, enable CDF on intermediate MLVs too
- CDF on an MLV enables its downstream consumers; it does not replace CDF on
  the sources used to refresh that MLV

### Routine refresh and recovery

Use Lakehouse lineage schedules with Optimal refresh for routine operation.
Automatic Full fallback is expected when needed, including source schema changes
with a hint. Do not mandate weekly Full refreshes, invent fixed IR cost savings,
or promise that periodic Full refresh corrects an invalid output-key contract.
Use one-time `REFRESH MATERIALIZED LAKE VIEW ... FULL` for approved troubleshooting
or reprocessing. After an outage or CDF-history gap, investigate the baseline
and available change history rather than repeatedly recreating the MLV.

---

## Example assessment language

- **IR-Eligible ✅** — known prerequisites met for subsequent refreshes; not a guarantee of the chosen strategy
- **Conditionally Eligible ⚠️** — source readiness, key evidence, user review, or a query-specific condition remains unresolved
- **Not IR-Eligible ❌** — one or more hard blockers present in the current definition

Report skipped validation as user-confirmed/unverified, never as validated.
If per-view refresh strategy is unavailable, report it as unobserved rather
than inferring IR from a completed lineage job.

---

## Routing guidance for the agent

Use this resource for IR-targeted creation, refresh hints, incremental refresh
readiness, full-refresh debugging, or refresh-friendly SQL rewrites. Pair with
`materialized-lake-view-patterns.md` for broader MLV design and `../../mlv.md`
for scheduling/monitoring. See the general patterns file's reference table for
the refresh and deletes/updates documentation.
