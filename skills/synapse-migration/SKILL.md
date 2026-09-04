---
name: synapse-migration
description: "Ports Azure Synapse workloads to Microsoft Fabric: Spark pools/notebooks, Lake Databases, Linked Services, and Dedicated SQL Pool schema and stored procedure code to Lakehouse Spark SQL from live or offline DACPAC/SQL-project artifacts, without moving source rows. Use for 'Dedicated SQL Pool schema and code to Lakehouse' and Synapse-to-Fabric migration. For pipelines use pipeline-migration."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: synapse-migration` (`az rest`: `--headers "x-ms-fabric-skill=synapse-migration"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find workspace details (including its ID) from a workspace name: list all workspaces, then use JMESPath filtering
> 2. To find item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace, then use JMESPath filtering
> 3. `mssparkutils` and `notebookutils` share the same API surface in most cases — the namespace is the primary change
> 4. Linked Services have no direct REST API equivalent in Fabric — they are replaced by Data Connections (for external sources) and OneLake Shortcuts (for storage mounts)
> 5. The Dedicated SQL Pool-to-Fabric-Lakehouse path is source- and feature-driven. **You MUST complete these phases in strict order:**
>    1. **Gap Assessment (MANDATORY FIRST)**: Run compatibility assessment using `dedicated-pool-gap-assessment.md` to identify unsupported features, blockers, and migration risks BEFORE attempting any conversion.
>    2. **User Approval (REQUIRED)**: After assessment, present `1:1`, `N:1`, and `N:N` stored-procedure-to-notebook mapping strategies and require the user to explicitly approve the complete mapping, target names, dependency grouping, and workspace placement. Wait for explicit approval before proceeding.
>    3. **Manifest Creation (REQUIRED)**: Create `migration-manifest.json` to track all objects, approved mappings, conversion status, and deployment checkpoints. Update manifest atomically after every phase.
>    4. **Conversion**: Generate artifacts only after approval is recorded in manifest.
>    **The `1:1`, `N:1`, and `N:N` mapping applies ONLY to stored procedures, NOT to views. Views are schema objects like tables and are deployed via Livy as SQL view definitions; they never convert to notebooks.** Preserve every procedure as an independently traceable source decision under any approved strategy. Stored-procedure transformation logic must use readable Spark SQL `%%sql` cells, not PySpark or the DataFrame API. Generated notebooks are outputs, not orchestration dependencies.
> 6. Treat the source Dedicated Pool as read-only. Never create sample or synthetic data, schemas, tables, views, procedures, users, roles, or grants in the source. Do not run source DDL, DML, or stored procedures. Source operations in this workflow are limited to metadata discovery and metadata-based validation; route any requested source mutation to a separate, explicitly scoped workflow.
> 7. Dedicated Pool data migration is out of scope. Never export, stage, copy, upload, shortcut, transfer, or load source table rows, and never run row-level or business-result equivalence queries. This skill migrates schema and executable code artifacts only.
> 8. Print regular migration status. Announce every step before it starts, report each object or checkpoint as it completes or fails, emit a concise heartbeat at least every 30-60 seconds during long-running operations, and close every phase with completed/failed/skipped/pending counts. Include the phase, step, object, state, elapsed time, and next action. Status output must exclude credentials, tokens, connection strings, and sensitive data values.
> 9. For large or complex stored procedures, prove conversion coverage with a deterministic source-block ledger and publish only from a hash-verified immutable deployment package. Every block must be converted, explicitly excluded with approval, or manually reviewed and approved; notebook syntax success alone is insufficient.
> 10. Before generating Dedicated Pool artifacts, read both `resources/dedicated-pool-to-lakehouse.md` and `resources/dedicated-pool-conversion.md`. In manifest `parameterMappings`, use `sourceParameter` for the discovered source name; `parameterName` is reserved for object-valued `conf` entries inside notebook `%%configure`.
> 11. A local or offline Dedicated Pool artifact request still requires this skill. For a large or complex procedure, also read `resources/dedicated-pool-large-procedure-audit.md` before generating artifacts.

# Synapse Analytics → Microsoft Fabric Migration

## Prerequisite Knowledge

These companion documents provide general Fabric REST patterns. **Do NOT read them upfront** — reference only when a specific phase requires a pattern not already covered in this skill's resource files:

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — General Fabric REST API patterns, authentication & token audiences, item discovery via JMESPath
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — `az rest` / `az login` CLI patterns, authentication recipes
- [SPARK-AUTHORING-CORE.md](../../common/SPARK-AUTHORING-CORE.md) — Notebook/lakehouse creation (already covered in [spark-item-migration.md](resources/spark-item-migration.md) and [lake-database-migration.md](resources/lake-database-migration.md))
- [SQLDW-AUTHORING-CORE.md](../../common/SQLDW-AUTHORING-CORE.md) — Fabric Warehouse T-SQL (delegate to `sqldw-cli` skill)

> **Auth, API endpoints, and item payloads are fully documented in this skill's own files.** The common docs above are fallback references only.

---

## Table of Contents

| Topic | Reference |
|---|---|
| **Migration Orchestrator** | [migration-orchestrator.md](resources/migration-orchestrator.md) |
| **Dedicated Pool → Lakehouse Migration** | [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) |
| Dedicated Pool Discovery | [dedicated-pool-discovery.md](resources/dedicated-pool-discovery.md) |
| Dedicated Pool Gap Assessment | [dedicated-pool-gap-assessment.md](resources/dedicated-pool-gap-assessment.md) |
| Dedicated Pool Conversion | [dedicated-pool-conversion.md](resources/dedicated-pool-conversion.md) |
| Dedicated Pool Large-Procedure Audit | [dedicated-pool-large-procedure-audit.md](resources/dedicated-pool-large-procedure-audit.md) |
| Dedicated Pool Deployment | [dedicated-pool-deployment.md](resources/dedicated-pool-deployment.md) |
| Dedicated Pool Validation | [dedicated-pool-validation.md](resources/dedicated-pool-validation.md) |
| API-Driven Migration Workflow | [§ API-Driven Migration Workflow](#api-driven-migration-workflow) |
| Migration Workload Map | [§ Migration Workload Map](#migration-workload-map) |
| Spark Pool → Environment Migration | [spark-pool-migration.md](resources/spark-pool-migration.md) |
| Lake Database → Lakehouse Migration | [lake-database-migration.md](resources/lake-database-migration.md) |
| External Hive Metastore → Lakehouse Migration | [external-hms-migration.md](resources/external-hms-migration.md) |
| Notebook & SJD Migration | [spark-item-migration.md](resources/spark-item-migration.md) |
| Library Compatibility (Synapse vs. Fabric RT 1.3) | [library-compatibility.md](resources/library-compatibility.md) |
| Connector Refactoring (Kusto, Cosmos DB, ADLS OAuth) | [connector-refactoring.md](resources/connector-refactoring.md) |
| `mssparkutils` → `notebookutils` API Mapping | [utility-api-mapping.md](resources/utility-api-mapping.md) |
| Linked Services → Data Connections / Shortcuts | [connectivity-migration.md](resources/connectivity-migration.md) |
| Before/After Code Patterns (incl. Catalog API gaps) | [code-patterns.md](resources/code-patterns.md) |
| Migration Report (with Fabric portal links) | [migration-report.md](resources/migration-report.md) |
| Migration Troubleshooting Guide | [migration-gotchas.md](resources/migration-gotchas.md) |
| Validation & Testing | [validation-testing.md](resources/validation-testing.md) |
| Security & Governance (Production Readiness) | [security-governance.md](resources/security-governance.md) |
| T-SQL & Spark Configuration Differences | [§ T-SQL & Spark Configuration Differences](#t-sql--spark-configuration-differences) |
| Capacity Sizing Reference | [§ Capacity Sizing Reference](#capacity-sizing-reference) |
| Must / Prefer / Avoid | [§ Must / Prefer / Avoid](#must--prefer--avoid) |
| Feature Parity Reference | [§ Feature Parity Reference](#feature-parity-reference) |
| Migration Gotchas — Quick Reference | [§ Migration Gotchas](#migration-gotchas--quick-reference) + [migration-gotchas.md](resources/migration-gotchas.md) |
| Post-Migration: What's Next | [§ Post-Migration: What's Next](#post-migration-whats-next) |

### Context Loading Guide

> **IMPORTANT — Load only what you need.** Do NOT read all resource files upfront. Load the specific file for the phase you are executing:

| When | Read This File | Lines |
|---|---|---|
| User asks to migrate a workspace (full orchestration) | [migration-orchestrator.md](resources/migration-orchestrator.md) | ~1264 |
| **User asks to migrate Dedicated SQL Pool → Lakehouse** | **[dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) + [dedicated-pool-conversion.md](resources/dedicated-pool-conversion.md)** | **~190** |
| Post-discovery Dedicated Pool risk report or target-design approval | [dedicated-pool-gap-assessment.md](resources/dedicated-pool-gap-assessment.md) | ~180 |
| Large or complex stored-procedure conversion | [dedicated-pool-large-procedure-audit.md](resources/dedicated-pool-large-procedure-audit.md) | ~130 |
| Phase 0: Spark Pools → Environments | [spark-pool-migration.md](resources/spark-pool-migration.md) | ~290 |
| Phase 1: Databases → Lakehouses (built-in HMS) | [lake-database-migration.md](resources/lake-database-migration.md) | ~574 |
| Phase 1: Databases → Lakehouses (external HMS) | [external-hms-migration.md](resources/external-hms-migration.md) | ~388 |
| Phase 2–3: Notebooks & SJDs | [spark-item-migration.md](resources/spark-item-migration.md) | ~326 |
| Code refactoring (mssparkutils, connectors) | [utility-api-mapping.md](resources/utility-api-mapping.md) + [connector-refactoring.md](resources/connector-refactoring.md) + [code-patterns.md](resources/code-patterns.md) | ~588 |
| Post-migration validation | [validation-testing.md](resources/validation-testing.md) | ~487 |
| Troubleshooting failures | [migration-gotchas.md](resources/migration-gotchas.md) | ~225 |
| Production security setup | [security-governance.md](resources/security-governance.md) | ~926 |
| Library version gaps | [library-compatibility.md](resources/library-compatibility.md) | ~106 |
| Generating migration report | [migration-report.md](resources/migration-report.md) | ~360 |
| Capacity sizing & SKU planning | [capacity-sizing.md](resources/capacity-sizing.md) | ~85 |
| Feature parity matrix | [feature-parity.md](resources/feature-parity.md) | ~65 |

---

## API-Driven Migration Workflow

This skill supports programmatic migration of Synapse Spark items via REST APIs (no UI-based Migration Assistant required).

### Authentication

| Target | Token Audience |
|---|---|
| Synapse ARM (management plane) | `https://management.azure.com` |
| Synapse Data Plane | `https://dev.azuresynapse.net` |
| Fabric REST API | `https://api.fabric.microsoft.com` |

> Use the token-acquisition recipe in [COMMON-CLI § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) with the audiences above.

### Migration Phases (Execute in Order)

| Phase | Synapse Source | Fabric Target | Resource |
|---|---|---|---|
| Phase 0 | Spark Pool | Environment | [spark-pool-migration.md](resources/spark-pool-migration.md) |
| Phase 1 | Lake Database (built-in HMS) | Lakehouse | [lake-database-migration.md](resources/lake-database-migration.md) |
| Phase 1 | External Hive Metastore | Lakehouse | [external-hms-migration.md](resources/external-hms-migration.md) |
| Phase 1b | Ad-hoc `abfss://` storage paths | OneLake Shortcuts | [migration-orchestrator.md](resources/migration-orchestrator.md) (migrate-and-modernize only) |
| Phase 2 | Notebooks | Notebook | [spark-item-migration.md](resources/spark-item-migration.md) |
| Phase 3 | Spark Job Definitions | SJD | [spark-item-migration.md](resources/spark-item-migration.md) |
| Final | Validation & Testing | — | [validation-testing.md](resources/validation-testing.md) |
| Optional | Security & Governance | — | [security-governance.md](resources/security-governance.md) |

> **Phase order matters**: Environments (Phase 0) must exist before notebooks/SJDs can bind to them. Lakehouses (Phase 1) must exist before notebooks can bind to them (Phase 2).

> For the full execution flow with sub-steps, decision points, lift-and-shift vs. modernize paths, and error recovery, see [migration-orchestrator.md](resources/migration-orchestrator.md).

### REST API Quick Reference

All Synapse and Fabric API endpoints with request/response examples are in [migration-orchestrator.md](resources/migration-orchestrator.md) (Steps 2a–2e). Authentication tokens:

| Target | Token Audience |
|---|---|
| Synapse ARM | `https://management.azure.com` |
| Synapse Data Plane | `https://dev.azuresynapse.net` |
| Fabric REST API | `https://api.fabric.microsoft.com` |

> **API docs**: [Synapse ARM](https://learn.microsoft.com/en-us/rest/api/synapse) · [Synapse Data Plane](https://learn.microsoft.com/en-us/rest/api/synapse/data-plane) · [Fabric Items](https://learn.microsoft.com/en-us/rest/api/fabric/core/items) · [Fabric Shortcuts](https://learn.microsoft.com/en-us/rest/api/fabric/core/onelake-shortcuts) · [Fabric Connections](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections) · [Fabric Environments](https://learn.microsoft.com/en-us/rest/api/fabric/environment)

---

## Migration Workload Map

Use this table to determine the correct Fabric target for each Synapse component:

| Synapse Component | Fabric Target | Notes |
|---|---|---|
| **Spark Pool** (notebooks, jobs) | **Fabric Environment + Notebook or Spark Job Definition** | Migrate Spark configuration, libraries, and code using the Spark-specific resources in this skill. |
| **Dedicated SQL Pool** | **Fabric Lakehouse** (stored procedures → Spark SQL notebooks; tables/views → Lakehouse objects) or **Fabric Warehouse** | **Lakehouse path**: extract metadata with SqlPackage/catalog queries, assess projected workspace item demand, require the user to provide and approve a `1:1`, `N:1`, or `N:N` procedure-notebook mapping (applies ONLY to stored procedures, NOT views), then convert schema and code artifacts. Tables and views are deployed as Lakehouse schema objects via Livy; only stored procedures convert to notebooks. Source table rows are not migrated; see [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md). **Warehouse path**: delegate T-SQL authoring to `sqldw-cli`. |
| **Serverless SQL Pool** | **Lakehouse SQL Endpoint** | Read-only Delta/Parquet queries; no DDL required |
| **Synapse Pipelines** | **Fabric Data Pipelines** | Activity types, triggers, and expressions are broadly compatible. *Pipeline migration resource not yet available — separate migration track.* |
| **Synapse Link for Cosmos DB / SQL** | **Fabric Mirroring** | Native mirroring replaces the Synapse Link connector pattern. *Not covered by this skill.* |
| **Linked Services** | **Data Connections** (external) / **OneLake Shortcuts** (storage) | See [connectivity-migration.md](resources/connectivity-migration.md) |
| **Integration Datasets** | **Fabric Pipeline source/sink config** | Dataset definitions are inlined into pipeline activities in Fabric. *Not covered by this skill.* |
| **Managed Virtual Networks** | **Fabric Managed Private Endpoints** | Configure in Fabric capacity settings |
| **Synapse Studio** | **Fabric workspace** | All artifact types live in a single workspace with Git integration |

### Decision Tree: Which Fabric Spark Workload?

```text
Synapse Spark workload
├── Interactive notebook with data exploration → Fabric Notebook (attached to Lakehouse)
├── Scheduled/production job → Spark Job Definition (SJD)
├── T-SQL over files/Delta → Lakehouse SQL Endpoint (no migration needed — just point to OneLake)
└── Real-time ingest → Fabric Eventstream + Lakehouse
```

---

## T-SQL & Spark Configuration Differences

For detailed T-SQL surface area gaps (PolyBase → `COPY INTO`, distribution hints, result set caching) and Spark configuration mappings (pools, `%%configure`, runtime versions), see [feature-parity.md](resources/feature-parity.md).

> **Key actions**: Remove `DISTRIBUTION = HASH(col)` hints, replace `CREATE EXTERNAL TABLE` with `COPY INTO`, replace `spark.read.synapsesql()` with OneLake shortcuts or JDBC. Delegate T-SQL authoring to `sqldw-cli`.

---

## Capacity Sizing Reference

For Synapse pool → Fabric SKU mapping tables, sizing decision guide, and cost model comparison, see [capacity-sizing.md](resources/capacity-sizing.md).

> **Quick guide**: Dev/test = F8–F16 with Starter Pool; standard production = F32–F64; enterprise = F128+. Use Fabric Trial (free F64, 60 days) for migration validation.

---

## Must / Prefer / Avoid

### MUST DO
- **Preserve stored-procedure input contracts** — keep every supported source input externally overridable through the Fabric Notebook Activity parameter mapped in first-cell `%%configure`; preserve a source default only as `defaultValue`, never replace a parameter use with a literal or invent a preview default, and block automatic publication when a required input has no source default
- **Approve stored-procedure notebook cardinality after discovery** — calculate projected workspace item demand, present `1:1`, `N:1`, and `N:N` choices, and block conversion until the user provides and approves a complete mapping, target names, dependency grouping, and workspace placement; preserve per-procedure source decisions and source-block provenance under every strategy
- **Audit large-procedure conversion by source block** — generate deterministic per-run ledger/verifier scripts, require 100% non-overlapping source-byte coverage and a deployable disposition for every block, retry only failed blocks within the declared limit, retain audit/logging behavior by default, and publish only the exact bytes in a hash-verified `ReadyForPublication` package
- **Use direct APIs for non-procedural phases** — use SqlPackage/DMVs for discovery, Fabric REST for item management, and Fabric Livy statements for schema and Delta execution
- **Replace all `mssparkutils` imports with `notebookutils`** — see [utility-api-mapping.md](resources/utility-api-mapping.md) for the complete namespace table
- **Replace all Linked Services** with Fabric Data Connections (for external databases/services) or OneLake Shortcuts (for ADLS Gen2 / Blob storage mounts) — see [connectivity-migration.md](resources/connectivity-migration.md)
- **Replace `spark.read.synapsesql()`** with Lakehouse shortcut reads or JDBC connections to the Fabric Warehouse SQL endpoint
- **Re-test all notebooks** after migration against the target Fabric Runtime version — Spark minor version differences can surface deprecated API warnings
- **Externalize all workspace/item IDs** — never hardcode; use pipeline parameters or [Variable Libraries](#variable-library-for-environment-promotion)
- **Replace pool-level library installs** with Fabric Environments attached at the workspace or notebook level

### PREFER
- **OneLake Shortcuts over full data copies** — mount existing ADLS Gen2 containers as shortcuts rather than re-ingesting data during migration
- **Fabric Starter Pool** for dev/test migrations — eliminates pool warm-up wait time inherent in Synapse on-demand pools
- **Lakehouse SQL Endpoint** as a drop-in for Serverless SQL Pool reads — point existing consumers at the endpoint with minimal query changes
- **Medallion architecture** for migrated data — align with Bronze/Silver/Gold patterns (see `e2e-medallion-architecture` skill)
- **Incremental migration** — migrate and validate workload by workload rather than performing a big-bang cutover
- **Parameterized notebooks** to allow environment promotion (dev → test → prod) without code changes

### AVOID
- **Do not use target notebooks as migration orchestration dependencies** — generated notebooks are required outputs and are published without execution
- **Do not copy-paste PolyBase `CREATE EXTERNAL TABLE` DDL** into Fabric Warehouse — rewrite as `COPY INTO` or use Lakehouse for external data access
- **Do not assume Synapse Linked Service connection strings are reusable** — credentials and endpoints must be reconfigured as Fabric Data Connections
- **Do not install libraries in notebook cells** (`%pip install` at runtime) for production workloads — use Fabric Environments for reproducible, versioned library management
- **Do not migrate Dedicated SQL Pool distribution hints** (`HASH`, `ROUND_ROBIN`, `REPLICATE`) verbatim — remove them; Fabric Warehouse handles distribution automatically
- **Do not use `wasb://` or `abfss://container@storageaccount.dfs.core.windows.net/` paths** as primary data paths — migrate data access to OneLake `abfss://workspace@onelake.dfs.fabric.microsoft.com/` paths

---

## Examples

See [code-patterns.md](resources/code-patterns.md) for full before/after examples. Key quick references:

**`mssparkutils.env` → `notebookutils.runtime`**

```python
# Synapse
workspace = mssparkutils.env.getWorkspaceName()

# Fabric
workspace = notebookutils.runtime.context["currentWorkspaceName"]
```

**Linked Service credential → Key Vault secret**

```python
# Synapse
conn = mssparkutils.credentials.getConnectionStringOrCreds("MyLinkedService")

# Fabric
conn = notebookutils.credentials.getSecret("https://myvault.vault.azure.net/", "my-secret")
```

**Dedicated SQL Pool DDL → Fabric Warehouse DDL**

```sql
-- Synapse (remove distribution hints)
CREATE TABLE dbo.Fact (...) WITH (DISTRIBUTION = HASH(id), CLUSTERED COLUMNSTORE INDEX);

-- Fabric Warehouse
CREATE TABLE dbo.Fact (...);
```

---

## Feature Parity Reference

Full Synapse → Fabric feature matrix (28 features), T-SQL surface area gaps, and Spark configuration differences are in [feature-parity.md](resources/feature-parity.md).

> **Key gaps** (⚠️/❌): `spark.read.synapsesql()` replaced by JDBC/shortcuts · Linked Services redesigned as Data Connections/Shortcuts · External HMS partial (migrate as shortcuts) · `mssparkutils.env` renamed to `notebookutils.runtime` · Result set caching ❌ · Workload management ❌ · PolyBase → `COPY INTO`

---

## Migration Gotchas — Quick Reference

The full troubleshooting guide with code examples and multi-option resolutions is in [migration-gotchas.md](resources/migration-gotchas.md). This summary surfaces the key issues for quick scanning during migration:

| # | Flag ID | Issue | Severity | Blocks? | Resolution Summary |
|---|---|---|---|---|---|
| G1 | `SYNAPSESQL_NO_EQUIVALENT` | `spark.read.synapsesql()` has no Fabric equivalent | High | Yes | Replace with OneLake shortcut read, Warehouse JDBC, or Data Pipeline |
| G2 | `LIBRARY_VERSION_CONFLICT` | Custom library version conflicts with Fabric Runtime | Medium | Maybe | Pin compatible version in Environment, or find Fabric-native alternative |
| G3 | `DELTA_PROTOCOL_MISMATCH` | Delta protocol version incompatibility | High | Yes | Rewrite table with matching protocol (`delta.minReaderVersion`/`minWriterVersion`) |
| G4 | `SECURITY_MODEL_INCOMPATIBLE` | Synapse managed identity / IP firewall not portable | Medium | Yes | Reconfigure as Workspace Identity + Fabric Managed Private Endpoints |
| G5 | `GPU_POOL_UNSUPPORTED` | GPU-accelerated Spark pools not available in Fabric | High | Yes | Migration blocker — keep workload in Synapse or use Azure ML |
| G6 | `DOTNET_SPARK_UNSUPPORTED` | .NET for Spark (C#/F# SJDs) not supported | High | Yes | Migration blocker — rewrite in PySpark or keep in Synapse |
| G7 | `NULLABLE_POOL_REFERENCE` | `bigDataPool`/`targetBigDataPool` field is `null` (not missing) — causes `NoneType` crash | Medium | No | Use `(x.get("bigDataPool") or {}).get(...)` pattern |
| G8 | `SESSION_CONFIG_IGNORED` | Some `%%configure` keys silently ignored in Fabric | Low | No | Remove unsupported keys; use Environment for pool-level config |
| G9 | `SHORTCUT_CONNECTION_FAILED` | ADLS shortcut creation fails (connection/permission) | High | Partial | Verify connection credential type (Key > WorkspaceIdentity > OAuth2) and RBAC |

---

## Post-Migration: What's Next

After completing Phases 0–3 and validation, hand off to these companion skills for ongoing operations:

### Agentic Exploration Workflow

Use this sequence only after a separately approved process has loaded data into Fabric Lakehouses. The Dedicated Pool to Lakehouse pattern in this skill migrates schema and code artifacts only, so it must stop after artifact validation and must not run this workflow.

For migrations that explicitly include approved data movement and data validation:

1. **Discover** → List schemas, tables, and row counts via Lakehouse SQL Endpoint (`sqldw-cli`)
2. **Sample** → `SELECT TOP 5` on migrated tables to verify data integrity
3. **Validate** → Run validation checks from [validation-testing.md](resources/validation-testing.md) (V1–V6)
4. **Explore** → Write Spark or T-SQL queries against migrated data using `spark-cli` or `sqldw-cli`
5. **Build** → Create Gold-layer aggregations with `e2e-medallion-architecture` (Bronze → Silver → Gold)
6. **Consume** → Build semantic models and reports with `semantic-model-authoring`

### Companion Skill Cross-References

| Post-Migration Task | Skill | When to Use |
|---|---|---|
| Interactive Lakehouse SQL queries | `sqldw-cli` | Exploring migrated data via SQL Endpoint |
| Interactive PySpark exploration | `spark-cli` | Ad-hoc Spark queries on migrated Lakehouses |
| Notebook & SJD authoring (new) | `spark-cli` | Creating new Spark items post-migration |
| Medallion architecture build-out | `e2e-medallion-architecture` | Structuring Bronze/Silver/Gold after lift-and-shift |
| Warehouse performance monitoring | `sqldw-cli` | Diagnosing slow queries on Fabric Warehouse |
| Semantic model creation | `semantic-model-authoring` | Building Power BI models over migrated data |
| Report consumption & DAX | `fabriciq` | Querying existing semantic models |
| KQL analytics | `eventhouse-cli` | If migrating real-time workloads to Eventhouse |

### Variable Library for Environment Promotion

After migration, avoid hardcoded workspace/item IDs by centralizing configuration in a **Variable Library** item:

```python
# Read config from Variable Library — works in notebooks
lib = notebookutils.variableLibrary.getLibrary("MigrationConfig")
lakehouse_name = lib.lakehouse_name
workspace_id = lib.workspace_id

# ❌ WRONG — .get() does not exist
# notebookutils.variableLibrary.get("MigrationConfig", "lakehouse_name")
```

- Use **Value Sets** (`valueSets/dev.json`, `valueSets/prod.json`) to promote across environments without code changes
- Boolean values are returned as strings — compare with `.lower() == "true"`, not `bool()`
- In Data Pipelines, reference via `@pipeline().libraryVariables.<name>` (not `@variables()`)
- Full Variable Library patterns → see [common/notebook-authoring/context-and-params.md § Variable Library](../../common/notebook-authoring/context-and-params.md#variable-library)
