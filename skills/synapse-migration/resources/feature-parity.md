# Feature Parity Reference

Quick-reference summary of Synapse Spark features and their Fabric equivalents.

## Synapse → Fabric Feature Matrix

| Synapse Feature | Fabric Equivalent | Parity | Notes |
|---|---|---|---|
| Spark Pool (on-demand) | Starter Pool | ✅ Full | Auto-provisioned, no config needed |
| Spark Pool (custom) | Custom Pool / Environment | ✅ Full | Node family + size + autoscale via Environment |
| **Synapse Dedicated SQL Pool** | **Fabric Lakehouse** | ⚠️ **Partial; rewrite required** | Schema and executable code artifacts only; T-SQL semantics require explicit conversion and review. See [dedicated-pool-to-lakehouse.md](dedicated-pool-to-lakehouse.md). |
| Pool-level libraries | Environment (libraries section) | ✅ Full | PyPI, Conda, custom .whl/.jar |
| `mssparkutils.*` | `notebookutils.*` | ✅ Full | Namespace change only — see [utility-api-mapping.md](utility-api-mapping.md) |
| `mssparkutils.env` | `notebookutils.runtime` | ⚠️ Renamed | `.env.getWorkspaceName()` → `.runtime.context["workspaceName"]` |
| Linked Services | Data Connections / Shortcuts | ⚠️ Redesigned | No 1:1 mapping — see [connectivity-migration.md](connectivity-migration.md) |
| `spark.read.synapsesql()` | JDBC / OneLake shortcut | ⚠️ Replaced | Connector not available in Fabric |
| Lake Database (built-in HMS) | Lakehouse (managed Delta) | ✅ Full | Tables → shortcuts, schemas supported |
| External Hive Metastore | Lakehouse (via shortcuts) | ⚠️ Partial | HMS not natively supported — migrate tables as shortcuts |
| Notebook `%%configure` | `%%configure` | ✅ Full | Identical syntax |
| `spark.conf.set()` | `spark.conf.set()` | ✅ Full | Identical |
| Spark SQL (DDL/DML) | Spark SQL | ✅ Full | `CREATE SCHEMA`, `CREATE TABLE`, etc. |
| Notebook parameters | Notebook parameters | ✅ Full | Same `parameters` cell mechanism |
| Spark Job Definitions | Spark Job Definitions | ✅ Full | Same concept, different deployment API |
| Delta Lake read/write | Delta Lake read/write | ✅ Full | Native format in Fabric |
| Notebook scheduling | Job Scheduler / Pipelines | ✅ Full | REST API or Pipeline activity |
| Git integration | Git integration | ✅ Full | Workspace-level Git sync |
| `TokenLibrary` (OAuth) | Workspace Identity / `notebookutils.credentials` | ⚠️ Replaced | See [connector-refactoring.md](connector-refactoring.md) |
| Catalog API (`spark.catalog.*`) | Catalog API | ⚠️ Partial | `tableExists()`, `listTables()`, `listColumns()`, `cacheTable()`, `dropTempView()` work; database-level methods (`listDatabases()`, `currentDatabase()`, `getDatabase()`) and function-level methods need Spark SQL replacements — see [code-patterns.md](code-patterns.md) |
| Managed VNet / Private Endpoints | Managed Private Endpoints | ⚠️ Partial | Capacity-level config, portal only |
| Result set caching | Not available | ❌ Missing | Rely on query plan caching |
| Workload management (classifiers) | Not available | ❌ Missing | Use capacity management |
| PolyBase external tables | `COPY INTO` / Lakehouse shortcuts | ⚠️ Replaced | Rewrite required |
| `DISTRIBUTION = HASH(col)` | Auto-distributed | ⚠️ Removed | Remove hints — Fabric handles distribution |

**Legend**: ✅ Full parity — ⚠️ Partial / renamed / replaced — ❌ Not available

## T-SQL Surface Area Gaps

Fabric Warehouse supports a broad T-SQL surface, but some Dedicated SQL Pool features differ:

| Synapse Dedicated SQL Pool Feature | Fabric Warehouse Equivalent | Action Required |
|---|---|---|
| `CREATE EXTERNAL TABLE` (PolyBase) | `COPY INTO` or Lakehouse SQL Endpoint | Rewrite ingestion; use `COPY INTO` for bulk load from ADLS/OneLake |
| `DISTRIBUTION = HASH(col)` | Not applicable — Fabric auto-distributes | Remove distribution hints from DDL |
| `CLUSTERED COLUMNSTORE INDEX` (default) | Delta Lake (Lakehouse) or Fabric Warehouse DCI | Warehouse tables use Delta-backed storage automatically |
| Result set caching | Not available | Remove cache hints; rely on query plan caching |
| Workload management (classifiers) | Not available | Use workspace capacity management |
| `sp_rename` | Supported | No change needed |
| `MERGE` statement | Supported | No change needed |
| Temp tables (`#temp`) | Supported | No change needed |
| Window functions | Supported | No change needed |

> **Delegate to `sqldw-authoring-cli`** for all T-SQL DDL/DML authoring tasks after mapping the workload.

## Spark Configuration Differences

| Synapse Spark Concept | Fabric Spark Equivalent | Notes |
|---|---|---|
| **Spark Pool definition** (node type, autoscale min/max) | **Custom Pool** or **Starter Pool** | Starter Pool (auto-provisioned, no config needed) covers most dev workloads; Custom Pools for production SLAs |
| `%%configure` magic cell (session-level config) | `%%configure` magic — **identical syntax** | Supported in Fabric notebooks |
| `spark.conf.set(...)` | `spark.conf.set(...)` — **identical** | No change needed |
| Environment-scoped libraries (pool packages) | **Fabric Environment** attached to workspace/notebook | Replace pool-level library installs with a Fabric Environment item |
| Synapse-specific Spark versions | Fabric Runtime versions (1.1 = Spark 3.3, 1.2 = Spark 3.4, 1.3 = Spark 3.5) | Align runtime version; test deprecated API calls |
| `spark.read.synapsesql(...)` connector | **Not available** — use `notebookutils` + Lakehouse shortcuts or Warehouse JDBC | Replace with OneLake reads or SQL endpoint queries |
