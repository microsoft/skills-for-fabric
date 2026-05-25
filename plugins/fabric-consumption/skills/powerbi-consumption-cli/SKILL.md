---
name: powerbi-consumption-cli
description: >
  The ONLY supported path for read-only Microsoft Fabric Power BI semantic model (formerly "Power BI dataset") query interactions.
  Execute DAX queries via the MCP server ExecuteQuery tool to: (1) discover semantic model metadata
  (tables, columns, measures, relationships, hierarchies, etc.) and their properties,
  (2) retrieve data from a semantic model.
  Triggers: "DAX query", "semantic model metadata", "list semantic model tables", "run EVALUATE", "get measure expression".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# Power BI Semantic Model Consumption — CLI Skill

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Hierarchy; Finding Things in Fabric |
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) | Production (Public Cloud) |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; covers token audiences, delegated vs app permissions, OAuth flows, identity types, and Entra app registration |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes workspace/item CRUD, resolve-by-name, pagination, LRO polling, and rate-limiting patterns |
| OneLake Data Access | [COMMON-CORE.md § OneLake Data Access](../../common/COMMON-CORE.md#onelake-data-access) | Requires `storage.azure.com` token, not Fabric token; covers URL structure, ADLS Gen2 parity, and shortcuts |
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) | Run On-Demand Job; Get / Cancel Job |
| Capacity Management | [COMMON-CORE.md § Capacity Management](../../common/COMMON-CORE.md#capacity-management) | List Capacities; Assign Workspace to Capacity |
| Gotchas, Best Practices & Troubleshooting | [COMMON-CORE.md § Gotchas, Best Practices & Troubleshooting](../../common/COMMON-CORE.md#gotchas-best-practices--troubleshooting) | Common Errors; Best Practices |
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows, environment detection, token acquisition, and debugging |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via `az rest`](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes workspace/item operations, pagination, and LRO patterns |
| OneLake Data Access via `curl` | [COMMON-CLI.md § OneLake Data Access via `curl`](../../common/COMMON-CLI.md#onelake-data-access-via-curl) | Use `curl` not `az rest` (different token audience); file list/read/upload/delete and directory creation |
| SQL / TDS Data-Plane Access | [COMMON-CLI.md § SQL / TDS Data-Plane Access](../../common/COMMON-CLI.md#sql--tds-data-plane-access) | `sqlcmd` (Go) connect, query, CSV export, service principal auth, and connection parameter discovery |
| Job Execution (CLI) | [COMMON-CLI.md § Job Execution](../../common/COMMON-CLI.md#job-execution) | Run notebooks/pipelines, refresh semantic models, check/cancel jobs |
| OneLake Shortcuts | [COMMON-CLI.md § OneLake Shortcuts](../../common/COMMON-CLI.md#onelake-shortcuts) | Create a Shortcut; List Shortcuts; Delete a Shortcut |
| Capacity Management (CLI) | [COMMON-CLI.md § Capacity Management](../../common/COMMON-CLI.md#capacity-management) | List Capacities; Assign Workspace to Capacity |
| Composite Recipes | [COMMON-CLI.md § Composite Recipes](../../common/COMMON-CLI.md#composite-recipes) | End-to-end workspace→lakehouse→file, SQL endpoint→query, and notebook execution recipes |
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) ||
| Quick Reference | [COMMON-CLI.md § Quick Reference](../../common/COMMON-CLI.md#quick-reference) | `az rest` Template; Token Audience ↔ CLI Tool Matrix |
| Prerequisites | [SKILL.md § Prerequisites](#prerequisites) ||
| Must/Prefer/Avoid | [SKILL.md § Must/Prefer/Avoid](#mustpreferavoid) | Guardrails for read-only semantic model usage. MUST DO; PREFER; AVOID |
| Metadata Discovery | [SKILL.md § Metadata Discovery](#metadata-discovery) | INFO.VIEW.* and INFO.* functions. |
| Recommended Discovery Order | [SKILL.md § Recommended Discovery Order](#recommended-discovery-order) | Preferred order for metadata exploration |
| Frequently Used INFO Functions | [SKILL.md § Frequently Used INFO Functions](#frequently-used-info-functions) | High-usage function list for first-pass discovery |
| Complete INFO Function Catalog (Dynamic) | [discovery-queries.md § Complete INFO Function Catalog (Dynamic)](./references/discovery-queries.md#complete-info-function-catalog-dynamic) ||
| Metadata Object → INFO Function Map | [SKILL.md § Metadata Object → INFO Function Map](#metadata-object--info-function-map) | Inlined mapping for object-focused discovery |
| Query Execution | [SKILL.md § Query Execution](#query-execution) | ExecuteQuery usage shape |
| Troubleshooting | [SKILL.md § Troubleshooting](#troubleshooting) | Resolve common execution and metadata issues |
| Examples | [SKILL.md § Examples](#examples) | Sample Metadata Query; Sample Data Query |
| Scope Estimation Queries | [discovery-queries.md § Scope Estimation Queries](./references/discovery-queries.md#scope-estimation-queries) ||
| INFO Output Columns | [discovery-queries.md § INFO Output Columns](./references/discovery-queries.md#info-output-columns) | INFO.VIEW.* (preferred first-pass metadata); Critical INFO.* (deep metadata / diagnostics) |
| Narrowing Results (Projection + Filtering) | [discovery-queries.md § Narrowing Results (Projection + Filtering)](./references/discovery-queries.md#narrowing-results-projection--filtering) ||
| Deep Metadata Queries | [discovery-queries.md § Deep Metadata Queries](./references/discovery-queries.md#deep-metadata-queries) ||
| Dependency Discovery | [discovery-queries.md § Dependency Discovery](./references/discovery-queries.md#dependency-discovery) | Dependency rowset for a DAX query; Dependency rows scoped to a measure; Reverse dependencies (what references a measure) |

## Prerequisites

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — Fabric concepts, authentication, and control-plane API context.
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — CLI-oriented discovery and token/audience patterns.

## Must/Prefer/Avoid

### MUST DO

- Keep this skill read-only: metadata discovery and analytical DAX queries only.
- Treat DAX data queries and `INFO.VIEW.*` as available to any user with read access to the semantic model; assume other `INFO.*` functions may require elevated permissions.
- Resolve workspace and semantic model item identity dynamically; do not hardcode IDs.
- Resolve the semantic model GUID before calling `ExecuteQuery`; do not pass a friendly semantic model name as `artifactId`.
- Use DAX `INFO.VIEW.*` / `INFO.*` for metadata discovery before writing data queries.

### PREFER

- Validate semantic model scope early (`artifactId` must be a semantic model GUID) before iterative query refinement.
- Discover semantic model schema progressively: use filtered and projected `INFO.VIEW.*` / `INFO.*` calls (e.g., `SELECTCOLUMNS` + `FILTER`) to fetch only the information directly relevant to the current task instead of retrieving the full schema up front. See [discovery-queries.md § Narrowing Results (Projection + Filtering)](./references/discovery-queries.md#narrowing-results-projection--filtering).
- Keep guidance provider-agnostic so tool endpoint migration is low risk.

### AVOID

- Model-change operations in this skill.

## Recommended Discovery Order

1. Run the [discovery-queries.md § Scope Estimation Queries](./references/discovery-queries.md#scope-estimation-queries) to estimate metadata scope (table, column, measure, and relationship counts) before deep discovery.
2. Start with `INFO.VIEW.TABLES()` for a fast table inventory.
3. Expand to `INFO.VIEW.COLUMNS()` and `INFO.VIEW.MEASURES()` for semantic details.
4. Use `INFO.VIEW.RELATIONSHIPS()` to validate joins and filter behavior.
5. Use the full query catalog in [discovery-queries.md](./references/discovery-queries.md) for deeper patterns.

## Frequently Used INFO Functions

- `INFO.VIEW.TABLES`
- `INFO.VIEW.MEASURES`
- `INFO.VIEW.COLUMNS`
- `INFO.VIEW.RELATIONSHIPS`
- `INFO.PARTITIONS`
- `INFO.MODEL`
- `INFO.STORAGETABLECOLUMNSEGMENTS`
- `INFO.DEPENDENCIES`
- `INFO.EXPRESSIONS`
- `INFO.ROLES`
- `INFO.STORAGETABLECOLUMNS`
- `INFO.CALCULATIONGROUPS`
- `INFO.CALCULATIONITEMS`
- `INFO.CULTURES`
- `INFO.OBJECTTRANSLATIONS`
- `INFO.USERDEFINEDFUNCTIONS`
- `INFO.REFRESHPOLICIES`
- `INFO.ATTRIBUTEHIERARCHYSTORAGES`
- `INFO.COLUMNPARTITIONSTORAGES`
- `INFO.COLUMNSTORAGES`
- `INFO.DICTIONARYSTORAGES`
- `INFO.HIERARCHYSTORAGES`
- `INFO.PARTITIONSTORAGES`
- `INFO.RELATIONSHIPINDEXSTORAGES`
- `INFO.RELATIONSHIPSTORAGES`
- `INFO.SEGMENTMAPSTORAGES`
- `INFO.SEGMENTSTORAGES`
- `INFO.STORAGEFOLDERS`
- `INFO.STORAGEFILES`
- `INFO.TABLESTORAGES`
- `INFO.GENERALSEGMENTMAPSEGMENTMETADATASTORAGES`
- `INFO.DELTATABLEMETADATASTORAGES`
- `INFO.PARQUETFILESTORAGES`
- `INFO.STORAGETABLES`

## Metadata Object → INFO Function Map

| Metadata Object | Primary INFO functions |
|---|---|
| Model | `INFO.MODEL` |
| Tables | `INFO.VIEW.TABLES` |
| Columns | `INFO.VIEW.COLUMNS`, `INFO.GROUPBYCOLUMNS`, `INFO.RELATEDCOLUMNDETAILS` |
| Measures | `INFO.VIEW.MEASURES`, `INFO.FORMATSTRINGDEFINITIONS`, `INFO.DETAILROWSDEFINITIONS` |
| Relationships | `INFO.VIEW.RELATIONSHIPS` |
| Partitions | `INFO.PARTITIONS`, `INFO.EXPRESSIONS`, `INFO.QUERYGROUPS`, `INFO.REFRESHPOLICIES`, `INFO.DATACOVERAGEDEFINITIONS` |
| Security roles & permissions | `INFO.ROLES`, `INFO.TABLEPERMISSIONS`, `INFO.COLUMNPERMISSIONS` |
| Hierarchies | `INFO.HIERARCHIES`, `INFO.LEVELS`, `INFO.ATTRIBUTEHIERARCHIES`, `INFO.VARIATIONS` |
| Calculation groups/items | `INFO.CALCULATIONGROUPS`, `INFO.CALCULATIONITEMS`, `INFO.CALCULATIONEXPRESSIONS` |
| Perspectives | `INFO.PERSPECTIVES`, `INFO.PERSPECTIVETABLES`, `INFO.PERSPECTIVECOLUMNS`, `INFO.PERSPECTIVEHIERARCHIES`, `INFO.PERSPECTIVEMEASURES` |
| Calendars | `INFO.CALENDARS`, `INFO.CALENDARCOLUMNGROUPS`, `INFO.CALENDARCOLUMNREFERENCES` |
| Cultures | `INFO.CULTURES` |
| Object translations | `INFO.OBJECTTRANSLATIONS` |
| Functions | `INFO.USERDEFINEDFUNCTIONS` |
| Dependencies / lineage | `INFO.DEPENDENCIES`, `INFO.CHANGEDPROPERTIES`, `INFO.EXCLUDEDARTIFACTS` |
| Storage internals / size | `INFO.STORAGEFOLDERS`, `INFO.STORAGEFILES`, `INFO.TABLESTORAGES`, `INFO.COLUMNSTORAGES`, `INFO.PARTITIONSTORAGES`, `INFO.SEGMENTMAPSTORAGES`, `INFO.DICTIONARYSTORAGES`, `INFO.COLUMNPARTITIONSTORAGES`, `INFO.SEGMENTSTORAGES`, `INFO.RELATIONSHIPSTORAGES`, `INFO.RELATIONSHIPINDEXSTORAGES`, `INFO.ATTRIBUTEHIERARCHYSTORAGES`, `INFO.HIERARCHYSTORAGES`, `INFO.GENERALSEGMENTMAPSEGMENTMETADATASTORAGES`, `INFO.DELTATABLEMETADATASTORAGES`, `INFO.PARQUETFILESTORAGES`, `INFO.STORAGETABLES`, `INFO.STORAGETABLECOLUMNS`, `INFO.STORAGETABLECOLUMNSEGMENTS` |

## Query Execution

Use a single `ExecuteQuery` capability with payload concepts:

- `artifactId`: GUID of the target semantic model, for example `1975b5f0-69e2-47a8-ae5f-c891b15934f4`. Do not pass the friendly semantic model name. Resolve the GUID from [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) first.
- `daxQuery`: direct DAX query text.

> Temporary implementation note: current query integration is expected to be replaced before release by a public HTTP endpoint exposing `ExecuteQuery`.

## Troubleshooting

- **ExecuteQuery capability is unavailable in the MCP server**
  - **Issue:** Query execution cannot start because `ExecuteQuery` is not available in the active tool list.
  - **Cause:** The Fabric MCP server is not registered, not loaded, or the current client session has stale tool metadata.
  - **Fix:** Verify the active MCP server/tool inventory and confirm `ExecuteQuery` is exposed.
- **ExecuteQuery fails with invalid arguments for `artifactId`**
  - **Issue:** Query execution fails with `MCP error -32602: Tool invoked with invalid arguments`.
  - **Cause:** `artifactId` was likely passed as a friendly semantic model name instead of a GUID.
  - **Fix:** Resolve the semantic model item first and retry with its GUID as `artifactId`.
- **Advanced INFO functions return permission errors**
  - **Issue:** Queries against `INFO.*` fail with authorization or privilege-related errors.
  - **Cause:** Many `INFO.*` functions require elevated semantic model permissions beyond standard read access.
  - **Fix:** Start with `INFO.VIEW.*` functions for read-oriented discovery.
- **Metadata output volume is too large for focused analysis**
  - **Issue:** Returning full metadata rowsets introduces too many properties and crowds the working context.
  - **Cause:** Unbounded `INFO.VIEW.*` and `INFO.*` queries return broad object/property surfaces that are often unnecessary for the current task.
  - **Fix:** Use the scope estimation queries in [discovery-queries.md § Scope Estimation Queries](./references/discovery-queries.md#scope-estimation-queries) to estimate scope and inspect output schemas, then narrow results with projection and filtering as shown in [discovery-queries.md § Narrowing Results (Projection + Filtering)](./references/discovery-queries.md#narrowing-results-projection--filtering).
- **Do not use `INFO` DAX functions to retrieve role memberships**
  - **Issue:** `INFO.ROLEMEMBERSHIPS()` returns empty or incomplete results.
  - **Cause:** Role members are assigned at the service level (Entra ID) after deployment, not in the model definition — so DAX `INFO` functions cannot reliably surface them.
  - **Fix:** Use the Power BI REST API instead. See [powerbi-authoring-cli § Security Role Memberships](../powerbi-authoring-cli/SKILL.md#security-role-memberships).

## Examples

For the full query catalog (including dependency patterns), see [discovery-queries.md](./references/discovery-queries.md).

### Sample Metadata Query

```dax
EVALUATE
INFO.VIEW.TABLES()
ORDER BY [Name]
```

### Sample Data Query

```dax
DEFINE
MEASURE 'Sales'[Total Sales] = SUM('Sales'[Amount])
EVALUATE
SUMMARIZECOLUMNS(
    'Customer'[Customer Name],
    "Total Sales", [Total Sales]
)
ORDER BY [Total Sales] DESC
```
