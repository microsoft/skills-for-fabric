# MLV Incremental Refresh Patterns — Skill Resource

Public-facing guidance for reviewing and improving **incremental refresh readiness** for
Microsoft Fabric Materialized Lake Views (MLVs).

Use this resource when the task is about:

- why an MLV may be doing a full refresh
- how to rewrite an MLV without changing business logic
- source-table readiness for incremental refresh
- which SQL patterns are safer for refresh-friendly MLV design

---

## Recommended patterns

### Must

1. **Start from the actual MLV definition** — review the `CREATE MATERIALIZED LAKE VIEW` SQL before suggesting changes.
2. **Preserve business meaning** — optimize refresh behavior without silently changing the result set.
3. **Check source prerequisites first**:
   - Delta or non-Delta
   - CDF enabled or unknown
   - append-only or updates/deletes
4. **Flag hard blockers clearly** before discussing optimization ideas.
5. **End with a structured readiness report** so the user knows what must change first.

### Prefer

1. **Deterministic SQL only** in MLV definitions.
2. **Simpler aggregate shapes** such as `COUNT` and `SUM`.
3. **Stable time filters downstream** instead of moving date windows in the MLV.
4. **Flatter query shapes** over very deep nesting.
5. **Downstream handling for ranking, windows, and presentation formatting**.

### Avoid

1. **Window functions** such as `ROW_NUMBER`, `RANK`, `LAG`, `LEAD`.
2. **Non-deterministic functions** such as `current_timestamp()`, `current_date()`, `rand()`, `uuid()`.
3. **Unsupported joins** such as `RIGHT JOIN`, `FULL OUTER JOIN`, and `CROSS JOIN`.
4. **Standalone `SELECT DISTINCT`** when the goal is refresh-friendly design.
5. **`COUNT(DISTINCT ...)` as the default Gold pattern**.
6. **Moving date boundaries** such as `date_sub(current_date(), 90)` embedded in the MLV.
7. **`ORDER BY` and `LIMIT`** in MLV definitions.

---

## Readiness workflow

### Step 1: Identify every source

Capture:

- table name
- Delta or non-Delta
- CDF enabled: `✅`, `❌`, or `❓`
- append-only or updates/deletes

### Step 2: Check hard blockers

Treat the following as strong full-refresh signals:

| Blocker | Examples |
|---|---|
| Window functions | `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()` |
| Unsupported joins | `RIGHT JOIN`, `FULL OUTER JOIN`, `CROSS JOIN` |
| Ordering and limiting | `ORDER BY`, `LIMIT` |
| Standalone DISTINCT | `SELECT DISTINCT ...` |
| DISTINCT aggregates | `COUNT(DISTINCT customer_id)` |
| Non-deterministic functions | `current_timestamp()`, `current_date()`, `now()`, `rand()`, `uuid()` |
| Rolling date windows | `date_sub(current_date(), 90)` |
| Non-Delta sources | CSV, Parquet, JSON, or unmanaged files |

### Step 3: Check caution areas

| Pattern | Public-facing guidance |
|---|---|
| `LEFT JOIN` | Review carefully, especially if the right side changes often |
| `AVG`, `MIN`, `MAX` | Often less refresh-friendly than `COUNT` and `SUM` |
| Deep nesting | Consider staged Silver MLVs instead of one large all-in-one query |
| Filter subqueries | Prefer simpler shapes when possible |

### Step 4: Suggest the smallest safe rewrite

Only suggest changes that preserve semantics.

### Step 5: Produce the report

Use this exact structure:

```markdown
## IR Readiness Report

**Overall Assessment:** [IR-Ready ✅ | Partially Ready ⚠️ | Not IR-Eligible ❌]

### 🚫 Blockers
### ⚠️ Warnings
### ✅ Good Practices Detected
### 📋 Source Table Checklist
### 💡 Top Recommendations
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

### Prefer Delta + CDF

```sql
ALTER TABLE bronze.orders SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
ALTER TABLE bronze.customers SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

### Prefer stable ingestion behavior

- Fact-like sources: append where practical
- Dimension-like sources: targeted upserts or merges instead of repeated full overwrites

### For MLV chains

If an MLV feeds another MLV and downstream incremental refresh depends on that chain, enable CDF on the intermediate MLV.

```sql
CREATE MATERIALIZED LAKE VIEW silver.clean_orders
TBLPROPERTIES (delta.enableChangeDataFeed = true)
AS
SELECT order_id, customer_id, amount
FROM bronze.orders;
```

---

## Example assessment language

### IR-Ready ✅

Use when:

- no hard blockers are present
- source prerequisites appear to be satisfied
- the query shape is deterministic and stable

### Partially Ready ⚠️

Use when:

- no hard blockers are obvious
- but source readiness is unknown, or
- caution areas remain that need validation

### Not IR-Eligible ❌

Use when:

- one or more hard blockers are present in the current definition

---

## Routing guidance for the agent

Use this resource when the user asks:

- “Why is my MLV doing a full refresh?”
- “Can this MLV use incremental refresh?”
- “How can I optimize this MLV without changing business logic?”
- “Is this SQL refresh-friendly?”
- “What blockers are forcing full refresh?”

Pair it with `materialized-lake-view-patterns.md` when the user is also designing or restructuring the overall Bronze/Silver/Gold MLV flow.
