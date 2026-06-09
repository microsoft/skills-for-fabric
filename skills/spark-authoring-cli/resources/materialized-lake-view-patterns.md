# Materialized Lake View Patterns — Skill Resource

Public-facing authoring patterns for Microsoft Fabric Materialized Lake Views (MLVs).
Use this resource when the task is about **writing, reviewing, or restructuring MLV SQL**,
not when the task is about Spark job triage or broad cross-workload orchestration.

---

## Recommended patterns

### Must

1. **Use deterministic SQL in MLV definitions** — keep transformations stable across refreshes.
2. **Prefer Delta sources with Change Data Feed (CDF) enabled** for source tables that feed MLVs.
3. **Use Materialized Lake Views for durable layer outputs**, not for transient notebook-only logic.
4. **Apply data quality checks close to the source-aligned layer** using `CONSTRAINT ... CHECK ... ON MISMATCH DROP` where appropriate.
5. **Separate Bronze, Silver, and Gold responsibilities clearly**:
   - Bronze: raw landing / source-aligned tables
   - Silver: cleaned and conformed datasets
   - Gold: business-facing aggregates
6. **Keep MLVs business-stable** — preserve query semantics unless the user explicitly asks for a redesign.
7. **Use documented syntax only** — avoid undocumented or implementation-specific features by default.

### Prefer

1. **Source-aligned Silver MLVs first, denormalized Silver MLVs second** — then aggregate in Gold.
2. **`COUNT` and `SUM` for Gold metrics** when they satisfy the business requirement.
3. **Downstream notebooks or BI logic** for ranking, moving windows, and presentation formatting.
4. **Cross-lakehouse 4-part naming** when reading from another workspace/lakehouse.
5. **Partitioned outputs** when downstream reads are heavily filtered by date or a small set of dimensions.
6. **Thin Gold MLVs** that serve reusable business outputs instead of embedding every downstream convenience calculation.

### Avoid

1. **Window functions inside MLVs** — move them downstream.
2. **Non-deterministic functions inside MLVs** — stamp values during ingestion instead.
3. **`RIGHT JOIN`, `FULL OUTER JOIN`, `CROSS JOIN`** in MLVs intended for incremental refresh.
4. **`ORDER BY` and `LIMIT`** in MLV definitions.
5. **Standalone `SELECT DISTINCT`** as a default modeling pattern.
6. **Embedding moving time windows** like `date_sub(current_date(), 90)` directly in the MLV.
7. **Using MLVs as a substitute for orchestration** — pipelines and notebooks still own sequencing and validation.

---

## When to use Materialized Lake Views

Choose an MLV when the user needs one or more of the following:

- a durable curated table in a Lakehouse
- repeatable cleansing or conformance logic
- pre-joined analytical detail tables
- reusable aggregate outputs for BI or downstream notebooks
- a Bronze → Silver → Gold layer implemented directly in Fabric Lakehouse

Do **not** default to MLVs when the task is primarily:

- ad-hoc notebook exploration
- one-off data movement
- streaming/event processing
- Spark job debugging or performance triage

---

## Layering patterns

### Pattern 1: Source-aligned Silver MLV

Use one MLV per important Bronze source when you need:

- type cleanup
- validation
- null/range checks
- basic derived columns
- a stable foundation for downstream joins

```sql
CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.orders_clean
(
    CONSTRAINT valid_order_id CHECK (order_id IS NOT NULL) ON MISMATCH DROP,
    CONSTRAINT positive_amount CHECK (amount > 0) ON MISMATCH DROP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
PARTITIONED BY (order_date)
AS
SELECT
    order_id,
    customer_id,
    order_date,
    CAST(amount AS DECIMAL(12,2)) AS amount
FROM bronze.orders;
```

### Pattern 2: Denormalized Silver MLV

Use a joined Silver MLV when Gold should aggregate over a clean, stable analytical grain.

```sql
CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.order_details
TBLPROPERTIES (delta.enableChangeDataFeed = true)
PARTITIONED BY (order_date)
AS
SELECT
    o.order_id,
    o.order_date,
    o.amount,
    c.customer_name,
    c.region,
    p.category
FROM silver.orders_clean o
INNER JOIN silver.customers_clean c ON o.customer_id = c.customer_id
INNER JOIN silver.products_clean p ON o.product_id = p.product_id;
```

### Pattern 3: Gold aggregate MLV

Use Gold MLVs for business-facing metrics and reusable summary tables.

```sql
CREATE OR REPLACE MATERIALIZED LAKE VIEW gold.daily_revenue
AS
SELECT
    order_date,
    region,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue
FROM silver.order_details
GROUP BY order_date, region;
```

---

## Data quality patterns

Use constraints for deterministic row-level checks.

```sql
CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.customers_clean
(
    CONSTRAINT valid_customer_id CHECK (customer_id IS NOT NULL) ON MISMATCH DROP,
    CONSTRAINT valid_email CHECK (email LIKE '%@%') ON MISMATCH DROP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
AS
SELECT customer_id, customer_name, email, region
FROM bronze.customers;
```

Prefer simple expressions. Keep the logic auditable and easy to explain.

---

## Cross-lakehouse and schema organization

### Cross-lakehouse reads

Use documented 4-part naming when needed:

```sql
SELECT *
FROM WorkspaceName.LakehouseName.bronze.orders;
```

### Schema organization

For medallion-style design, organize tables and MLVs into schemas such as:

```sql
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
```

Keep naming predictable:

- `bronze.orders`
- `silver.orders_clean`
- `silver.order_details`
- `gold.daily_revenue`

---

## Refresh and orchestration guidance

MLVs define durable data products; notebooks and pipelines define execution order.

Recommended refresh order:

1. source-aligned Silver MLVs
2. denormalized Silver MLVs
3. Gold MLVs
4. maintenance steps on a slower cadence

```sql
REFRESH MATERIALIZED LAKE VIEW silver.orders_clean;
REFRESH MATERIALIZED LAKE VIEW silver.customers_clean;
REFRESH MATERIALIZED LAKE VIEW silver.order_details;
REFRESH MATERIALIZED LAKE VIEW gold.daily_revenue;
```

---

## Modeling tradeoffs

### Exact distinct counts

If the user requests exact distinct counts, explain that:

- the requirement is valid
- the design may be less refresh-friendly
- one option is to pre-deduplicate earlier in the flow
- another option is to accept that this MLV may not be the most incremental-refresh-friendly shape

### Rankings and moving windows

If the user requests ranking, lag/lead, or moving windows:

- keep the base curated dataset in an MLV
- move the ranking/window logic to a notebook or consuming layer

### Presentation logic

If the user requests rounding, formatting, or report-only columns:

- store raw business measures in the MLV
- apply presentation formatting downstream

---

## Routing guidance for the agent

Use this resource when the user asks about:

- materialized lake views
- MLV authoring
- designing Silver/Gold tables with MLVs
- MLV constraints
- `CREATE MATERIALIZED LAKE VIEW`
- refresh ordering for MLV-based layers
- medallion design implemented directly with MLVs

Escalate to `e2e-medallion-architecture` or `FabricDataEngineer` when the request becomes:

- multi-workspace architecture
- end-to-end Bronze → Silver → Gold orchestration
- pipeline design across multiple workloads
- Power BI + Spark + pipeline coordinated rollout
