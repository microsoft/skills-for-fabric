<!-- Mode reference for the `sqldw-cli` skill. Loaded on demand from `skills/sqldw-cli/SKILL.md` when the request matches the `operations` mode. -->

> **MODE-CRITICAL NOTES (operations mode)**
> 1. `queryinsights.*` views exist on **both a Warehouse and a Lakehouse SQL analytics endpoint**, and reading them needs **Contributor or higher** on the workspace. Query Insights is always on — there is no setting to enable. A completed query lands in the `queryinsights` of the item it ran against.
> 2. **Every figure comes from a query you ran in the turn you report it, cited inline** — `2,140 ms (queryinsights.long_running_queries)`. Do not carry numbers forward from an earlier turn: re-run the query. "I already ran the diagnostics" is not a source, and an uncited number reads as invented. Zero rows is a valid finding; never fill the gap from this reference.
> 3. **Read-only:** use `SELECT` diagnostics. The only allowed non-`SELECT` statement is `EXEC sys.sp_get_table_health_metrics` on a Lakehouse SQL analytics endpoint. Do not issue `ALTER`, `CREATE`, `DROP`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, or a `SET` that changes warehouse configuration — including `ALTER DATABASE ... SET RESULT_SET_CACHING ON`.
> 4. **A vague optimisation request ("just make my warehouse faster") is a new diagnostic question, not a summary request.** Re-run the queries backing the levers you are about to name — in that same turn — then **ask which target to pursue**. Recommend only what those queries showed; never answer from earlier turns' output, and never list every knob that could be tuned.

# sqldw-cli operations mode — Fabric SQL Endpoint Performance and Diagnostics

This skill provides performance analysis, deep diagnostics, and optimization guidance for Fabric Warehouse and Lakehouse SQL analytics endpoints via the **`fabric-sqlendpoint-execute_query` MCP tool** and built-in diagnostics. All queries are read-only.

## Prerequisites

For workspace/item discovery via `az rest`, see [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest). For legacy `sqlcmd` reference (fallback only), see [COMMON-CLI.md § SQL / TDS Data-Plane Access](../../../common/COMMON-CLI.md#sql--tds-data-plane-access).

> **⚠️ SQL Execution Override:** For SQL data-plane execution, this skill supersedes COMMON-CLI SQL/TDS guidance. Use MCP `fabric-sqlendpoint-execute_query` (see [Tool Stack](#tool-stack)) unless explicitly using Legacy CLI Fallback.

**Monitoring-specific requirements:**
- **Workspace role**: Contributor or higher on the target workspace (required for `queryinsights` views)
- **A Warehouse or Lakehouse SQL analytics endpoint must exist** with recent query activity (`queryinsights` views retain 30 days; data appears with up to 15 min delay)
- **Lakehouse table health only**: `VIEW DEFINITION` on the target SQL analytics endpoint

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Connection Fundamentals | [SQLDW-CONSUMPTION-CORE.md § Connection Fundamentals](../../../common/SQLDW-CONSUMPTION-CORE.md#connection-fundamentals) | TDS, port 1433, Entra-only, no MARS |
| Monitoring and Diagnostics | [SQLDW-CONSUMPTION-CORE.md § Monitoring and Diagnostics](../../../common/SQLDW-CONSUMPTION-CORE.md#monitoring-and-diagnostics) | Query labels; DMVs (live) + `queryinsights.*` (30-day history) |
| Performance: Best Practices and Troubleshooting | [SQLDW-CONSUMPTION-CORE.md § Performance: Best Practices and Troubleshooting](../../../common/SQLDW-CONSUMPTION-CORE.md#performance-best-practices-and-troubleshooting) | Statistics, caching, clustering, query tips |
| Gotchas and Troubleshooting (Consumption) | [SQLDW-CONSUMPTION-CORE.md § Gotchas and Troubleshooting Reference](../../../common/SQLDW-CONSUMPTION-CORE.md#gotchas-and-troubleshooting-reference) | 18 numbered issues with cause + resolution |
| Data Ingestion (DW Only) | [SQLDW-AUTHORING-CORE.md § Data Ingestion (DW Only)](../../../common/SQLDW-AUTHORING-CORE.md#data-ingestion-dw-only) | COPY INTO, OPENROWSET, method comparison |
| Query Reference | [query-reference.md](operations/query-reference.md) | T-SQL queries, parameters, and example output for all analyses |
| Composite Recipes | [COMMON-CLI.md § Composite Recipes](../../../common/COMMON-CLI.md#composite-recipes) ||
| Item-Type Capability Matrix | [SQLDW-CONSUMPTION-CORE.md § Item-Type Capability Matrix](../../../common/SQLDW-CONSUMPTION-CORE.md#item-type-capability-matrix) | Read-vs-write scope by item type; `queryinsights` itself is available on both Warehouse and SQLEP |
| Prerequisites | [SKILL.md § Prerequisites](#prerequisites) | Tools, auth, workspace role |
| Tool Stack | [SKILL.md § Tool Stack](#tool-stack) ||
| Connection | [SKILL.md § Connection](#connection) ||
| Performance Analysis | [SKILL.md § Performance Analysis](#performance-analysis) | Long-running queries, resource consumers, user insights, baselines |
| Deep Diagnostics | [SKILL.md § Deep Diagnostics](#deep-diagnostics) | Pressure windows, cache warmth, cluster keys |
| Fabric DW Constraints | [SKILL.md § Fabric DW Constraints](#fabric-dw-constraints) | **NEVER recommend unsupported features** |
| Best Practices | [SKILL.md § Best Practices](#best-practices) | Monitoring-specific guidance |
| Gotchas, Rules, Troubleshooting | [SKILL.md § Gotchas, Rules, Troubleshooting](#gotchas-rules-troubleshooting) | **MUST DO / AVOID / PREFER** checklists |

---

## Tool Stack

For installation and setup, see [Prerequisites](#prerequisites).

| Tool | Role |
|---|---|
| `fabric-sqlendpoint-execute_query` MCP tool | **Primary**: Execute monitoring T-SQL queries against Fabric SQL Endpoints. Auth handled by MCP protocol. |
| `az` CLI | Token acquisition, Fabric REST for workspace/item discovery |
| `jq` | Parse JSON from `az rest` |

> **IMPORTANT — MCP vs sqlcmd:**
> This skill uses the `fabric-sqlendpoint-execute_query` MCP tool for all T-SQL execution. Do **not** use COMMON-CLI SQL/TDS/sqlcmd sections for query execution.

> **Agent preflight** — verify before first operation:
> 1. Confirm the `fabric-sqlendpoint-execute_query` tool is available in your tool list. This tool is provided by the `fabric-sqlendpoint` MCP server, which is registered either by installing a Fabric skills **plugin** (the path for end users) or via this repo's `.mcp.json` — other MCP clients may register it through their own configuration.
> 2. If no matching tool is found, the user must register the Fabric SQL Endpoint MCP server.
>    - **Global URL**: `https://api.fabric.microsoft.com/v1/mcp/dataPlane/sqlEndpoint`
>    - **Item-scoped URL**: `https://api.fabric.microsoft.com/v1/mcp/dataPlane/workspaces/{workspaceId}/items/{itemId}/sqlEndpoint`

### MCP Tool Signature

```text
fabric-sqlendpoint-execute_query(workspaceId, itemId, query)
```

> **Tool name may differ:** `execute_query` is the logical operation. Depending on how the server is
> registered, the concrete tool name in your tool list may be prefixed (e.g.
> `fabric-sqlendpoint-execute_query` or `sqlendpoint-global-execute_query`). Invoke the concrete name
> shown in your tool list, always passing `workspaceId`, `itemId`, and `query`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `workspaceId` | string (UUID) | The workspace GUID containing the target SQL endpoint item |
| `itemId` | string (UUID) | Warehouse/Mirrored Database item ID, or a Lakehouse's `properties.sqlEndpointProperties.id` |
| `query` | string | T-SQL query text (single batch — no `GO` separators) |

**Returns:** CSV resource (RFC 4180) with tabular results + metadata text.

**Limits:** 10,000 rows max | 300s timeout | 20 req/min rate limit _(observed defaults, not a documented contract — the service can change them; verify against live 429/timeout/truncation responses)_

---

## Connection

### Discover workspaceId and itemId

You need the workspace GUID and target SQL endpoint item GUID to call `fabric-sqlendpoint-execute_query`. For a Lakehouse, use `properties.sqlEndpointProperties.id`, not the Lakehouse item ID:

```bash
# 1. Find workspace ID by name (capture into WS_ID for the next call)
WS_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='MyWorkspace'].id" --output tsv)
echo "Workspace ID: $WS_ID"

# 2. Find warehouse item ID by name
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/warehouses" \
  --query "value[?displayName=='MyWarehouse'].id" --output tsv
```

### Execute a Monitoring Query

```text
fabric-sqlendpoint-execute_query(
  workspaceId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  itemId: "11111111-2222-3333-4444-555555555555",
  query: "SELECT TOP 5 * FROM queryinsights.long_running_queries ORDER BY last_run_total_elapsed_time_ms DESC"
)
```

**No additional connection setup needed** — authentication is handled transparently by the MCP protocol.

---

## Performance Analysis

General-purpose SQL queries remain in [query-reference.md](operations/query-reference.md). Focused workflows use the leaf selected by the dispatcher, including `queryinsights.exec_requests_history` for request evidence and `queryinsights.sql_pool_insights` for pressure state events.

### Long-Running Queries Summary

Find the slowest queries from `queryinsights.long_running_queries`. See [query-reference.md § Long-Running Queries Summary](operations/query-reference.md#long-running-queries-summary) for SQL and formatting.

### Top Resource Consumers

Use the directly indexed `references/operations/resource-consumers.md` leaf for CPU concentration, baseline comparison, expensive executions, and cache interpretation.

### Top Users Insights

Analyze user activity and query patterns. See [query-reference.md § Top Users Insights](operations/query-reference.md#top-users-insights) for SQL and classification logic.

### Compare Recent vs Baseline

Detect performance regressions by comparing recent window against historical baseline. See [query-reference.md § Compare Recent vs Baseline](operations/query-reference.md#compare-recent-vs-baseline) for SQL and formatting.

### Recent Queries

Retrieve the most recently executed queries. See [query-reference.md § Recent Queries](operations/query-reference.md#recent-queries) for SQL.

### Search Query Patterns

Search historical query patterns by table name, column, or keyword. See [query-reference.md § Search Query Patterns](operations/query-reference.md#search-query-patterns) for SQL.

---

## Deep Diagnostics

Use the focused leaf selected by the dispatcher when one exists; use [query-reference.md](operations/query-reference.md) only for the remaining general diagnostics.

### Analyze Long-Running Query Runtime Profile

See [query-reference.md § Long-Running Query Analysis](operations/query-reference.md#long-running-query-analysis) for SQL.

Query Insights supplies runtime metrics, not an operator-level actual plan. Analyze a separate plan artifact only when the user supplies one.

**Analysis guidance** — when reviewing slow queries, check:
- High `data_scanned_remote_storage_mb` → data layout issues (run OPTIMIZE, consider clustering)
- High `allocated_cpu_time_ms` relative to elapsed → CPU-bound (simplify joins, reduce columns)
- High elapsed but low CPU → waiting on resources (check for pressure windows)

### Analyze Pressure Window Queries

Read the directly indexed `references/operations/pool-pressure.md` leaf. It builds intervals from all state events with `LEAD`, preserves the pressure-off boundary, and correlates requests by both time and `sql_pool_name`.

### Analyze Query Cache Warmth

Read the directly indexed `references/operations/resource-consumers.md` leaf. It handles zero-scan rows before ratios and records `result_cache_hit` values correctly. Result set caching is currently disabled due to a known issue, so use those fields only for historical interpretation and do not recommend enabling it unless current Microsoft documentation confirms the limitation is resolved.

### Recommend Cluster Keys

See [query-reference.md § Cluster Key Recommendations](operations/query-reference.md#cluster-key-recommendations) for SQL.

**Key rules:**
- Only `WHERE` predicates benefit from clustering — equality `JOIN ON` conditions do **not**
- Prefer mid-to-high cardinality columns (many distinct values)
- Maximum 4 clustering columns
- Use CTAS with `WITH (CLUSTER BY (...))` — `ALTER TABLE` is not supported

**To apply clustering** — see [query-reference.md § Cluster Key Recommendations](operations/query-reference.md#cluster-key-recommendations) for CTAS creation, `sp_rename` table swap, and verification SQL.

> **Note:** Fabric does not support `ALTER TABLE SET DATA_CLUSTERING_KEY` or `RENAME OBJECT`. Always use CTAS with `WITH (CLUSTER BY (...))` and `sp_rename` for table swaps.

---

## Fabric DW Constraints

**NEVER recommend features not supported in Fabric Data Warehouse.** Always consult this list before making optimization suggestions.

| Do NOT Recommend | Why | Recommend Instead |
|------------------|-----|-------------------|
| Nonclustered indexes | Not supported | V-Order, column pruning, predicate pushdown |
| Materialized views | Not supported | Standard views; result set caching is currently unavailable |
| Index hints (FORCESEEK/FORCESCAN) | Not supported | Simplify query structure |
| Multi-column statistics | Not supported | Single-column statistics on key columns |
| `ALTER TABLE SET DATA_CLUSTERING_KEY` | Not supported | CTAS with `WITH (CLUSTER BY (...))` |
| `RENAME OBJECT` | Not supported | `EXEC sp_rename 'schema.old', 'new'` |
| Change isolation level | Snapshot only | Fabric uses snapshot isolation exclusively |
| CREATE USER | Not supported | Manage users via Fabric workspace |
| Triggers | Not supported | Application logic or Fabric pipelines |
| Recursive CTEs | Not supported | Iterative approach |
| "Enable Query Insights" setting | Query Insights is always on — there is no setting | If access is denied, the user needs Contributor or higher on the workspace |

---

## Agentic Workflows

Start with the dispatcher-selected leaf, run only evidence required by the question, and expand to another directly indexed workflow only when the first result establishes that dependency.

---

## Best Practices

For comprehensive Fabric DW best practices, see [SQLDW-CONSUMPTION-CORE.md § Performance: Best Practices and Troubleshooting](../../../common/SQLDW-CONSUMPTION-CORE.md#performance-best-practices-and-troubleshooting) and the [Fabric guidelines](https://learn.microsoft.com/fabric/data-warehouse/guidelines-warehouse-performance).

**Monitoring-specific best practices:**

- **Start broad, then drill down** — begin with long-running queries summary and baseline comparison before deep diagnostics
- **Use pressure window analysis** for root-cause analysis rather than guessing at bottlenecks
- **Label all agent queries** with `OPTION (LABEL = 'AGENTCLI_MONITOR_...')` for tracing in Query Insights
- **Prefer mid-to-high cardinality columns** for clustering keys — low cardinality columns offer limited file-skipping benefit
- **Use `WHERE` predicates** to identify cluster key candidates — equality `JOIN ON` conditions do not benefit from clustering
- **Always verify clustering** after CTAS by querying `sys.index_columns.data_clustering_ordinal`
- **Check cold vs warm cache** before concluding a query is inherently slow — first execution may be a cold start
- **Adjust time windows** (`DATEADD` parameters) to match user's investigation scope — don't default to arbitrary windows

---

## Gotchas, Rules, Troubleshooting

For generic CLI gotchas (connection, auth, shell escaping): see [COMMON-CLI.md § Gotchas & Troubleshooting](../../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific).
For T-SQL/platform gotchas: see [SQLDW-CONSUMPTION-CORE.md § Gotchas and Troubleshooting Reference](../../../common/SQLDW-CONSUMPTION-CORE.md#gotchas-and-troubleshooting-reference).

### MUST DO
- Always check [Fabric DW Constraints](#fabric-dw-constraints) before recommending optimizations
- When recommending clustering, instruct users to use CTAS with `WITH (CLUSTER BY (...))` — not ALTER TABLE
- Report actual query output — do not fabricate or assume results
- **Label queries** with `OPTION (LABEL = 'AGENTCLI_MONITOR_...')` for Query Insights tracing
- **Verify `fabric-sqlendpoint-execute_query` MCP tool availability** before first operation

### PREFER
- Start with high-level queries (long-running summary, baseline comparison) before drilling into diagnostics
- Use the pressure window analysis for root-cause analysis rather than guessing at bottlenecks
- Adjust time windows (`DATEADD` parameters) based on what the user asks for
- Consolidate related diagnostic queries into fewer calls to respect rate limits

### AVOID
- Recommending Fabric-unsupported features (nonclustered indexes, materialized views, index hints, triggers)
- Suggesting that Query Insights needs to be "enabled" or "turned on" — `queryinsights` views are always available; permission errors indicate insufficient workspace role (Contributor or higher required)
- Running monitoring queries without confirming workspaceId and itemId
- Guessing at performance root causes without running the diagnostic queries
- Using `SELECT *` in monitoring queries — always select specific columns
- Using `GO` separators or sqlcmd meta-commands in queries (MCP tool accepts single batches only)
- Unbounded queries without `TOP N` — 10,000 row limit applies

### TROUBLESHOOTING (Monitoring-Specific)

For generic connection/auth troubleshooting, see [COMMON-CLI.md § Gotchas & Troubleshooting](../../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific).

| Symptom | Cause | Fix |
|---|---|---|
| `Invalid object name 'queryinsights...'` | New warehouse < 2 min old | Wait ~2 minutes |
| Permission errors on `queryinsights.*` | Insufficient workspace role | Requires Contributor or higher |
| No data in queryinsights views | No recent query activity or < 15 min delay | Wait 15 min after query completion |
| No rows but data exists | RLS filtering | Check `USER_NAME()`, verify RLS policies |
| `fabric-sqlendpoint-execute_query` tool not available | MCP server not registered | User must add Fabric SQL Endpoint MCP server |
| HTTP 429 rate limit | Too many calls in 1 min | Wait 60s; consolidate queries |
| Query timeout (300s) | Complex diagnostics | Narrow time window with tighter DATEADD |
