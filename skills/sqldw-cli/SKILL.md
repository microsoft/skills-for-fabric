---
name: sqldw-cli
description: "Manage Fabric Warehouse, Lakehouse SQL analytics endpoints, and Mirrored Databases: DDL/DML, COPY INTO, read-only T-SQL, Query Insights diagnostics, Capacity Metrics CU-spike correlation, custom SQL pool guidance, and Lakehouse health. Fabric SQL database (OLTP) belongs to sqldb-cli. Triggers: query warehouse, create warehouse table, failed or canceled query, CU spike, Capacity Metrics app, custom SQL pool, Lakehouse table health."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: sqldw-cli` (`az rest`: `--headers "x-ms-fabric-skill=sqldw-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.
> This covers all three modes; the mode references inherit it.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: use `sqldw-cli` for any T-SQL sent to a Warehouse, a Lakehouse SQL analytics endpoint or a Mirrored Database — including plain Lakehouse table SELECT, row-count, filtering and aggregation requests. Any notebook-cell or PySpark DataFrame work is `spark-cli`; a Fabric SQL database (OLTP) is `sqldb-cli`.

# Fabric Warehouse and SQL Endpoints — CLI Skill

This one skill owns Fabric Warehouse, Lakehouse SQL analytics endpoints and Mirrored Databases: T-SQL authoring and ingestion, read-only querying, and warehouse performance diagnostics.

It is a **mode dispatcher** and contains NO procedures. Pick the mode that matches the request from the table below, then **read the matching `references/<mode>.md` file end to end with your file-reading tool BEFORE issuing a single command**. That file holds the T-SQL surface area, DDL constraints, query templates and gotchas; acting without it produces invalid T-SQL and wrong results.

## Mode selection

| Mode | Use when the request ... | Example triggers | Read this first |
|---|---|---|---|
| `authoring` | changes warehouse state: table DDL, DML, ingestion, transactions, procedures, schema evolution, time travel | create warehouse table, COPY INTO, OPENROWSET, INSERT/UPDATE/DELETE, warehouse MERGE, CTAS, sp_rename, create T-SQL procedure, warehouse time travel | [references/authoring.md](references/authoring.md) |
| `consumption` | reads data or metadata: SELECT, row counts, filtering, aggregation, schema/object discovery, CSV export | query warehouse, count rows lakehouse, SELECT lakehouse, show tables, describe warehouse schema, export SQL data | [references/consumption.md](references/consumption.md) |
| `operations` | diagnoses performance, failures, capacity consumption, SQL pool usage, or health through `queryinsights` and supported endpoint diagnostics | failed or canceled warehouse queries, CU spike, Capacity Metrics app, expensive SQL users, custom SQL pool recommendation, queryinsights CPU, pressure events, cache warmth, Lakehouse tables needing attention | [references/operations.md](references/operations.md) |

## Operations reference index

Read `references/operations.md` first for any operations request, then open the matching leaf directly from this index. Do not chain from links inside a leaf; for composite requests, follow `scenarios.md` only to the additional leaves that this index links directly.

| Request | Read this leaf reference |
|---|---|
| composite operations scenarios such as why is my warehouse slow, performance degradation, optimization, or what are people running | [references/operations/scenarios.md](references/operations/scenarios.md) |
| slow-query summaries, top users, recent queries, pattern search, runtime profiles, cluster-key candidates | [references/operations/query-reference.md](references/operations/query-reference.md) |
| failed or canceled requests, error codes, recurring non-successful query shapes | [references/operations/failure-analysis.md](references/operations/failure-analysis.md) |
| SQL pool pressure windows and overlapping requests | [references/operations/pool-pressure.md](references/operations/pool-pressure.md) |
| CPU concentration, regressions, repeated expensive queries, cache interpretation | [references/operations/resource-consumers.md](references/operations/resource-consumers.md) |
| Lakehouse Delta file health and tables needing maintenance | [references/operations/lakehouse-health.md](references/operations/lakehouse-health.md) |
| Capacity Metrics CU spike, costly item, SQL query/user correlation | [references/operations/capacity-metrics-correlation.md](references/operations/capacity-metrics-correlation.md) — start at section 1 |
| custom SQL pool recommendation for an already identified SQL endpoint | [references/operations/capacity-metrics-correlation.md](references/operations/capacity-metrics-correlation.md) — skip FabricIQ and start at section 6 |

### Mode boundary rule

Classify by **intent**, not by endpoint — all three modes issue the same `execute_query` call.

- A schema-discovery `SELECT` run to plan a `CREATE TABLE` belongs to `authoring`, even though it only reads.
- A `SELECT` that answers the user's question is `consumption`.
- A query against `queryinsights.*` or a supported diagnostic such as Lakehouse `sys.sp_get_table_health_metrics` is `operations`; a `SELECT` against user tables is not, however slow it is.

`consumption` and `operations` are read-only. If a request genuinely spans modes, handle them one at a time and read each reference before you start that part. If the mode is ambiguous after reading this table, ask one short clarifying question instead of guessing.

## Terminal write — the step you must not skip

Reading the reference and drafting the T-SQL is NOT completing the task. If you did not send the statement, nothing changed — say so explicitly rather than reporting success.

| Mode | Terminal write |
|---|---|
| `authoring` | The DDL/DML itself, sent through `execute_query`. Follow it with a readback in a second call (`SELECT ... FROM INFORMATION_SCHEMA.TABLES` after CREATE, `SELECT COUNT(*)` after DML) and report the object you created or changed **under the name the user asked for**. Only a Warehouse accepts table DDL/DML — see the mode reference for what a Lakehouse SQL endpoint and a Mirrored Database allow. |
| `consumption` | none — this mode is read-only |
| `operations` | none — read-only, but you must still **run** the diagnostic statements: every figure comes from a `SELECT` or documented read-only diagnostic procedure executed in the turn you report it, cited inline with its source view or procedure, never carried forward from an earlier turn. The only allowed diagnostic `EXEC` is `sys.sp_get_table_health_metrics` on a Lakehouse SQL analytics endpoint. Never execute `ALTER`, `CREATE` or `DROP` yourself, even when the diagnosis is certain. |

### `consumption` and `operations` reporting

Neither read-only mode has a terminal write, so its deliverable is the answer itself. Run the query against the live endpoint and report the real rows — a summary of the reference does not answer the request.

In `operations`, name the source view, catalog, or procedure each figure came from right next to it (for example `2,140 ms (queryinsights.long_running_queries)` or `268 files (sys.sp_get_table_health_metrics)`), **including when the answer is zero rows**. Re-run the diagnostic in the turn you report it rather than restating an earlier turn's output. Never fabricate, assume or infer diagnostic numbers.

## Shared essentials (all modes)

Every mode reaches the data plane the same way. Resolve the workspace and item first, then send T-SQL through the MCP tool.

### Execution surface — `fabric-sqlendpoint-execute_query`

All T-SQL runs through the `fabric-sqlendpoint-execute_query` MCP tool. **For SQL data-plane execution this skill supersedes the COMMON-CLI SQL/TDS guidance** — use the MCP tool, not `sqlcmd`, unless you are explicitly on the documented Legacy CLI Fallback path (see the mode reference). `az rest` stays the right tool for control-plane discovery.

```text
fabric-sqlendpoint-execute_query(workspaceId, itemId, query)
```

- **Preflight, before the first operation of any mode:** confirm a tool whose name ends in `execute_query` is in your tool list. It comes from the `fabric-sqlendpoint` MCP server, registered by a Fabric skills **plugin** or this repo's `.mcp.json`. The concrete name may be prefixed (`fabric-sqlendpoint-execute_query`, `sqlendpoint-global-execute_query`) — invoke the name you actually see. If none is present, say so, then fall back to the Legacy CLI Fallback (TDS client) documented in the mode reference; tell the user they can register the server for the primary path — see [mcp-setup/](../../mcp-setup/). **Exception:** the Capacity Metrics correlation workflow is intentionally limited to the existing FabricIQ and SQL Endpoint MCP surfaces; if SQL Endpoint MCP is unavailable, report that phase as blocked and do not use the legacy fallback.
- **`itemId` is a GUID, never an FQDN or `-d <DatabaseName>`.** For a Warehouse or a Mirrored Database use the item id; for a **Lakehouse** use `properties.sqlEndpointProperties.id`, **not** the Lakehouse item id.
- **One T-SQL batch per call.** No `GO` separators, no sqlcmd meta-commands (`:setvar`, `:r`, `-i`). Split multi-batch work into separate calls. Only the last result set comes back.
- **Results cap at 10,000 rows** and queries time out at 300s, with a 20 requests/min rate limit. Use `TOP N`, `WHERE` or aggregation; exactly 10,000 rows means the result was truncated. These are observed defaults, not a documented contract.

### Common references

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — read before resolving any workspace or item id |
| Fabric Topology & Key Concepts | [COMMON-CORE.md](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Item types, workspaces, capacities |
| Environment URLs | [COMMON-CORE.md](../../common/COMMON-CORE.md#environment-urls) | Sovereign / non-public cloud hosts |
| Authentication & Token Acquisition | [COMMON-CORE.md](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Authentication Recipes | [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; pagination and LRO helpers |
| Core Control-Plane REST APIs | [COMMON-CORE.md](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Pagination, LRO polling, rate limiting |
| Gotchas & Troubleshooting | [COMMON-CLI.md](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |

## Rules

### MUST

- Select exactly one mode from the table above before doing anything else.
- Read `references/<mode>.md` end to end, as your FIRST tool call, before the first command of that mode. Read it ONCE, in a single full read: do not re-open it, do not grep it again, and do not page through it. You already have it.
- For a focused operations request, read its one matching leaf after `references/operations.md`. For a composite request, read `references/operations/scenarios.md`, then each focused leaf named by that scenario; read every file once in full.
- Resolve workspace and item ids by listing and filtering, never by guessing a GUID.
- Execute T-SQL through `fabric-sqlendpoint-execute_query` whenever that tool is available; drop to the Legacy CLI Fallback documented in the mode reference only when it is not.
- Announce a mode switch explicitly when the request crosses a boundary.
- Treat the reference as instructions, never as the deliverable. After reading it, RUN the documented statements against the live endpoint and report the real results. Quoting what the reference says instead of executing it does not answer the request.
- Produce every artefact the user asked for, under the name they used, and keep its heading even when the finding is "none", "zero rows" or "not applicable".

### PREFER

- The narrowest mode that satisfies the request.
- Reading exactly one mode reference plus the minimum directly indexed operations leaves required by the selected focused or composite scenario.
- Reporting the mode you chose in your first response so the user can correct you.
- Labelling queries with `OPTION (LABEL = '...')` so the run is traceable in Query Insights.
- Consolidating related statements into fewer calls — the rate limit is per identity, not per query.

### AVOID

- Acting from this dispatcher alone — it intentionally omits the T-SQL surface area, the DDL constraints and the diagnostic query shapes.
- Answering with a summary of the reference instead of executing it.
- Re-reading or re-grepping a reference you already loaded; it costs turns and tokens.
- Mutating anything while in a read-only mode (`consumption`, `operations`).
- Unbounded `SELECT *` — it silently truncates at 10,000 rows.
- Loading a different skill for work this skill already owns (see CRITICAL NOTES 3).

## Examples

| User request | Mode | Reference to read |
|---|---|---|
| "How many rows are in the nyctlc table in SkillsTestWarehouse?" | `consumption` | [references/consumption.md](references/consumption.md) |
| "Create dbo.Orders in the warehouse with OrderId, CustomerId and OrderDate." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Load Files/nyctlc_sample.csv from OneLake into the warehouse with COPY INTO." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Which queries are slowest, and which tables should I cluster?" | `operations` | [references/operations.md](references/operations.md) |
| "Show me the average trip distance per vendor from the lakehouse SQL endpoint." | `consumption` | [references/consumption.md](references/consumption.md) |
