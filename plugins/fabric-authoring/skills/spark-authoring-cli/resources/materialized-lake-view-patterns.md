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

### MLV topology: count, consolidation, and redundancy

**How many MLVs per lakehouse?**

| Topology | When to use | Considerations |
|----------|-------------|---------------|
| 1–5 MLVs | Simple analytics (single team, one domain) | Easy to manage, single lineage schedule covers all |
| 5–20 MLVs | Multi-domain lakehouse (bronze/silver/gold layers) | Lineage refresh takes longer; Optimal Refresh handles ordering |
| 20–50 MLVs | Enterprise lakehouse (cross-team, many consumers) | Consider splitting into multiple lakehouses for independent scheduling |
| 50+ MLVs | Anti-pattern — split | Too many in one lineage = long refresh times, single-point-of-failure |

**Consolidating redundant MLVs:**
- If multiple MLVs query the same source with similar transforms → consolidate into one broader MLV
- If downstream consumers need different subsets → one MLV with broader scope + views/filters on top
- If refresh cadences differ → separate lakehouses (one schedule per lineage constraint)

**When to split across lakehouses:**
- Different refresh cadences needed (hourly vs daily)
- Different team ownership (RBAC boundaries)
- Independent failure isolation (one lineage failure shouldn't block another)
- Cross-lakehouse lineage (Extended lineage) can still chain them in dependency order

> **Rule of thumb**: If a single lineage refresh takes > 30 minutes, consider splitting. Each split allows independent scheduling and parallel execution.

### Avoid

1. **Window functions inside MLVs** — move them downstream.
2. **Non-deterministic functions inside MLVs** — stamp values during ingestion instead.
3. **`RIGHT JOIN`, `FULL OUTER JOIN`, `CROSS JOIN`** in MLVs intended for incremental refresh.
4. **`ORDER BY` and `LIMIT`** in MLV definitions.
5. **Standalone `SELECT DISTINCT`** as a default modeling pattern.
6. **Embedding moving time windows** like `date_sub(current_date(), 90)` directly in the MLV.
7. **Using MLVs as a substitute for orchestration** — non-MLV ingestion, validation, and cross-system workflows still belong in pipelines or notebooks. (Refresh ordering between MLVs themselves is the Lakehouse's job — see [Refresh and orchestration guidance](#refresh-and-orchestration-guidance) below.)

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
-- Enable CDF on the SOURCE so this MLV can incrementally refresh.
-- TBLPROPERTIES on the MLV itself only helps DOWNSTREAM MLVs that read from it.
ALTER TABLE bronze.orders SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.orders_clean
(
    CONSTRAINT valid_order_id CHECK (order_id IS NOT NULL) ON MISMATCH DROP,
    CONSTRAINT positive_amount CHECK (amount > 0) ON MISMATCH DROP
)
PARTITIONED BY (order_date)
TBLPROPERTIES (delta.enableChangeDataFeed = true)  -- for DOWNSTREAM IR consumers
AS
SELECT
    order_id,
    customer_id,
    product_id,
    order_date,
    CAST(amount AS DECIMAL(12,2)) AS amount
FROM bronze.orders;
```

### Pattern 2: Denormalized Silver MLV

Use a joined Silver MLV when Gold should aggregate over a clean, stable analytical grain.

```sql
-- All three sources must have CDF enabled for this MLV to incrementally refresh.
-- (silver.orders_clean already has CDF from Pattern 1; add it to the other two.)
ALTER TABLE silver.customers_clean SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
ALTER TABLE silver.products_clean  SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.order_details
PARTITIONED BY (order_date)
TBLPROPERTIES (delta.enableChangeDataFeed = true)  -- for DOWNSTREAM IR consumers
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

> If a workspace, lakehouse, or schema name contains spaces, wrap that part in backticks: `` `My Workspace`.LakehouseName.bronze.orders ``.

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

## SQL management commands

### List MLVs in a schema

```sql
SHOW MATERIALIZED LAKE VIEWS IN silver;
```

### Retrieve the original definition

```sql
SHOW CREATE MATERIALIZED LAKE VIEW silver.orders_clean;
```

### Update an MLV definition

You cannot alter an existing MLV definition in place. Use `CREATE OR REPLACE`
to overwrite the current definition:

```sql
CREATE OR REPLACE MATERIALIZED LAKE VIEW silver.orders_clean AS
SELECT order_id, customer_id, product_id, order_date,
       CAST(amount AS DECIMAL(12,2)) AS amount
FROM bronze.orders;
```

To rename an MLV without changing its definition:

```sql
ALTER MATERIALIZED LAKE VIEW silver.orders_clean RENAME TO silver.orders_clean_v2;
```

---

## Current limitations

These limitations apply to Spark SQL MLV definitions:

1. **Schema and MLV naming** — all-uppercase schema names (e.g., `MYSCHEMA`) are not supported; use mixed case or lowercase. MLV object names are case-insensitive and normalized to lowercase (`MyTestView` becomes `mytestview`).
2. **No DML statements** — `INSERT`, `UPDATE`, `DELETE` cannot target an MLV. Data comes only from the `SELECT` query.
3. **No time-travel queries** — `VERSION AS OF` and `TIMESTAMP AS OF` are not supported in the MLV definition.
4. **No user-defined functions** — UDFs are not supported in MLV definitions.
5. **`OR REPLACE` and `IF NOT EXISTS` cannot be combined** in the same statement.
6. **Temp views cannot be sources** — an MLV must select from persisted tables or other MLVs. Session-scoped temp views (`createOrReplaceTempView`) are not valid sources.
7. **Session Spark configs don't apply to scheduled refresh** — `spark.conf.set(...)` values set interactively are not carried into scheduled refresh runs. Set properties at the lakehouse or workspace level instead.

> See the [Spark SQL Reference](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/create-materialized-lake-view) for the complete and current list of limitations.

---

## PySpark MLVs (Preview)

PySpark-authored MLVs (defined with `import fmlv` and the `@fmlv.materialized_lake_view` decorator on a function that returns a DataFrame) are supported but have trade-offs:

- **No incremental refresh** — PySpark MLVs always use full refresh.
- **Lineage-schedule refresh only** — cannot refresh on-demand via notebook as with Spark SQL-based views.
- **Renaming** — the MLV object itself can be renamed via `ALTER MATERIALIZED LAKE VIEW ... RENAME TO ...` (see the SQL syntax above; applies to both SQL- and PySpark-authored MLVs). If you instead change the `@fmlv.materialized_lake_view` decorator name in code, you have to drop and recreate.
- Use PySpark when you need complex transformation logic, reusable functions, external Python libraries, or custom UDFs.

> Running `spark.sql("CREATE MATERIALIZED LAKE VIEW ...")` from a notebook cell is a **Spark SQL** MLV (it keeps optimal/incremental refresh), not a PySpark-authored MLV.

When incremental refresh matters, prefer Spark SQL notebooks over PySpark.

> See the [PySpark Reference](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/create-materialized-lake-view-pyspark) for notebook organization best practices and current limitations.

---

## Refresh and orchestration guidance

MLVs define durable data products. **Refresh orchestration belongs to the Lakehouse**, not to notebook or pipeline schedulers.

> [!TIP] **Manage MLV refresh from your Lakehouse, not notebooks**
>
> Once your MLVs are created, rely on the Lakehouse's built-in capabilities
> instead of orchestrating refresh from notebooks:
>
> - **[Lineage](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/view-lineage)** —
>   Fabric derives dependency order from MLV definitions automatically.
>   Open the Materialized lake views tab → Manage to view the graph and
>   follow a run in progress.
> - **[Scheduled refresh](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/schedule-lineage-run)** —
>   Create one or more schedules to refresh all MLVs or a selected subset.
>   Each schedule runs views in dependency order and retries transient failures.
>
> Use notebooks to *author and iterate* on MLV definitions; use Lakehouse
> lineage and schedules to handle ordering, refresh, and retries.

### Scheduled refresh

Use the Lakehouse **Materialized lake views** tab → **Manage** → **Schedules** to configure:

- Repeat cadence: minute, hourly, daily, weekly, or monthly
- **Optimal refresh** toggle (default On): Fabric automatically picks incremental or full refresh per view
- **Extended lineage**: refresh chains across multiple lakehouses in dependency order from a single schedule. When MLVs in Lakehouse B depend on tables in Lakehouse A, a single schedule on Lakehouse B refreshes Lakehouse A's MLVs first, then B's — no need for separate schedules per lakehouse. See [Manage lineage](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/view-lineage) for cross-lakehouse dependency visualization.

Key behaviors (per current Fabric documentation — confirm against the [refresh reference](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view) as platform limits may change):
- A refresh run fails if it exceeds **24 hours**
- If a new refresh starts while another is in progress, Fabric **skips** the later one

For programmatic schedule management (create/update/delete schedules, trigger on-demand refresh via code), use the [MLV Public REST API](https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/materialized-lake-views-public-api). For conversational schedule management via Copilot, see the [mlv-operations-cli](../../mlv-operations-cli/SKILL.md) skill.

### Manual refresh order

> Prefer the lakehouse **Materialized lake views → Manage** schedule/lineage view for routine refresh. The SQL below is the documented way to force a one-time full refresh of an individual MLV (for troubleshooting or after a correction); `FULL` is the only documented `REFRESH MATERIALIZED LAKE VIEW` form.

```sql
REFRESH MATERIALIZED LAKE VIEW silver.orders_clean FULL;
REFRESH MATERIALIZED LAKE VIEW silver.customers_clean FULL;
REFRESH MATERIALIZED LAKE VIEW silver.order_details FULL;
REFRESH MATERIALIZED LAKE VIEW gold.daily_revenue FULL;
```

Recommended sequence:

1. source-aligned Silver MLVs
2. denormalized Silver MLVs
3. Gold MLVs
4. maintenance steps on a slower cadence

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

---

## Official documentation references

| Topic | URL | Keywords |
|---|---|---|
| MLV overview | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/overview-materialized-lake-view | overview, capabilities, when to use, limitations |
| Get started | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/get-started-with-materialized-lake-views | quickstart, create MLV, first MLV, CDF setup |
| Medallion tutorial | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/tutorial | medallion architecture, bronze-silver-gold, sales analytics |
| Optimal refresh | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/refresh-materialized-lake-view | incremental refresh, full refresh, no refresh, optimal refresh, CDF |
| Spark SQL reference | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/create-materialized-lake-view | CREATE, DROP, SHOW, ALTER, syntax, limitations |
| PySpark reference | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/create-materialized-lake-view-pyspark | PySpark, full refresh, UDFs, complex transformations |
| Schedule refresh | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/schedule-lineage-run | schedule, lineage, cross-lakehouse, optimal refresh toggle |
| Manage lineage | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/view-lineage | lineage view, dependency graph, extended lineage |
| REST API management | https://learn.microsoft.com/en-us/fabric/data-engineering/materialized-lake-views/materialized-lake-views-public-api | REST API, on-demand refresh, schedule CRUD |
