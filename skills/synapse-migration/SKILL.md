---
name: synapse-migration
description: "Converts Azure Synapse workloads to Fabric: Dedicated SQL Pool schemas and procedures to Lakehouse Spark SQL artifacts or Warehouse targets, plus Spark, Lake Database, and Linked Service migration. Excludes standalone Fabric Warehouse administration, Databricks source code, and pipelines. Triggers: Dedicated SQL Pool to Lakehouse, Dedicated SQL Pool to Fabric Warehouse, convert Synapse stored procedure, offline Synapse artifacts."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: synapse-migration` (`az rest`: `--headers "x-ms-fabric-skill=synapse-migration"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **OFFLINE LAKEHOUSE ARTIFACT FAST PATH — DECIDE FIRST.** For a no-live-call request with complete supplied inputs and contracts, load only the [fast path](resources/dedicated-pool-to-lakehouse.md#offline-lakehouse-artifact-fast-path); do not load `migration-planning-reference.md`, `dedicated-pool-conversion.md`, or implementation scripts. Use one generator for `expected-schema.json`, artifacts, and final-byte hashes, then one verifier. Do not manually edit artifacts or reread resources. Do not inspect generated files or run post-pass spot checks. Stop when verification passes or fails. Do not use this path for a Warehouse target; incomplete and large-procedure requests use their own routes.

> **CRITICAL NOTES**
> 1. To find workspace details (including its ID) from a workspace name: list all workspaces, then use JMESPath filtering
> 2. To find item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace, then use JMESPath filtering
> 3. `mssparkutils` and `notebookutils` share the same API surface in most cases — the namespace is the primary change
> 4. Linked Services have no direct REST API equivalent in Fabric — name both replacement categories when explaining the migration: Fabric Data Connections for external databases/services and OneLake Shortcuts for storage mounts. `mssparkutils.credentials.getConnectionStringOrCreds` is unavailable in Fabric; for a Key Vault-backed secret, show `notebookutils.credentials.getSecret(keyVaultUrl, secretName)`.
> 5. The Dedicated SQL Pool-to-Fabric-Lakehouse path is source- and feature-driven. **You MUST complete these phases in strict order:**
>    1. **Gap Assessment (MANDATORY FIRST)**: Run compatibility assessment using `dedicated-pool-gap-assessment.md` to identify unsupported features, blockers, and migration risks BEFORE attempting any conversion.
>    2. **User Approval (REQUIRED)**: After assessment, present `1:1`, `N:1`, and `N:N` stored-procedure-to-notebook mapping strategies and require the user to explicitly approve the complete mapping, target names, dependency grouping, and workspace placement. Wait for explicit approval before proceeding.
>    3. **Manifest Creation (REQUIRED)**: Create `migration-manifest.json` to track all objects, approved mappings, conversion status, and deployment checkpoints. Update manifest atomically after every phase.
>    4. **Conversion**: Generate artifacts only after approval is recorded in manifest.
>    **The `1:1`, `N:1`, and `N:N` mapping applies ONLY to stored procedures, NOT to views. Views are schema objects like tables and are deployed via Livy as SQL view definitions; they never convert to notebooks.** Preserve every procedure as an independently traceable source decision under any approved strategy. Stored-procedure transformation logic must use readable Spark SQL `%%sql` cells, not PySpark or the DataFrame API. Generated notebooks are outputs, not orchestration dependencies.
> 6. Treat the original production Dedicated Pool as read-only. Never create sample or synthetic data, schemas, tables, views, procedures, users, roles, or grants there, and never run its DDL, DML, or stored procedures. Source operations against the original are limited to metadata discovery and metadata-based validation. The Warehouse data path may run narrowly scoped setup DDL and CETAS only against the separately approved restored export copy after its identity is validated as different from the original; cleanup remains separately reviewed and user-run.
> 7. Dedicated Pool data migration is out of scope only for the Lakehouse artifact-conversion path. That path must never export, stage, copy, upload, shortcut, transfer, or load source table rows, and must not run row-level or business-result equivalence queries. The Warehouse path has its own explicit post-DDL data consent gate and restored-source requirement.
> 8. Print regular migration status. Announce every step before it starts, report each object or checkpoint as it completes or fails, emit a concise heartbeat at least every 30-60 seconds during long-running operations, and close every phase with completed/failed/skipped/pending counts. Include the phase, step, object, state, elapsed time, and next action. Status output must exclude credentials, tokens, connection strings, and sensitive data values.
> 9. For large or complex stored procedures, prove conversion coverage with a deterministic source-block ledger and publish only from a hash-verified immutable deployment package. Every block must be converted, explicitly excluded with approval, or manually reviewed and approved; notebook syntax success alone is insufficient.
> 10. Before generating live or partially specified Dedicated Pool-to-Lakehouse artifacts, follow the exact [Live, Partially Specified, and Offline Artifact Contract](resources/migration-planning-reference.md#live-partially-specified-and-offline-artifact-contract). For a complete offline fixture, use only the [Offline Lakehouse artifact fast path](resources/dedicated-pool-to-lakehouse.md#offline-lakehouse-artifact-fast-path).
> 11. An offline Dedicated Pool artifact request still requires this skill. For a complete large-procedure audit request, read `resources/dedicated-pool-large-procedure-audit.md` exactly once, then use one cwd-relative generator and the required generated verifier; do not load the standard conversion resources too. In generated JSON, store artifact-root-relative POSIX paths exactly as requested, never filesystem paths that include the output root. Keep separate constants for recorded relative paths and disk locations. Compute full deterministic block IDs before writing notebook markers or ledger mappings, and package attempt evidence for `Converted` blocks only.
> 12. Keep Spark, Dedicated Pool-to-Lakehouse, and Dedicated Pool-to-Warehouse execution paths separate. If the target is not explicit, ask the user to choose it before loading path-specific resources. For a Fabric Warehouse target, explicitly state that the complete `DISTRIBUTION` and `CLUSTERED COLUMNSTORE INDEX` declarations are removed because Fabric manages distribution, storage, and indexing; a bare mention of either source clause is insufficient.
> 13. For Spark workspace migration plans, preserve the canonical phase labels from this skill: Phase 0 Spark Pools to Environments, Phase 1 databases/storage to Lakehouses or shortcuts, Phase 2 notebooks, and Phase 3 Spark Job Definitions. Do not renumber discovery as Phase 0.
> 14. For Dedicated Pool feature-risk assessments and workspace item projections, follow the exact [Feature-Risk Assessment and Workspace Projection Contract](resources/migration-planning-reference.md#feature-risk-assessment-and-workspace-projection-contract) and load `resources/dedicated-pool-gap-assessment.md`; the Phase 2 approval gate in Note 5 remains blocking.
> 15. For Dedicated Pool-to-Lakehouse publication and hashes, follow the exact [Lakehouse Publication and Hash Contract](resources/migration-planning-reference.md#lakehouse-publication-and-hash-contract).

# Synapse Analytics → Microsoft Fabric Migration

## Prerequisite Knowledge

These companion documents provide general Fabric REST patterns. **Do NOT read them upfront** — reference only when a specific phase requires a pattern not already covered in this skill's resource files:

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — General Fabric REST API patterns, authentication & token audiences, item discovery via JMESPath
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — `az rest` / `az login` CLI patterns, authentication recipes
- [SPARK-AUTHORING-CORE.md](../../common/SPARK-AUTHORING-CORE.md) — Notebook/lakehouse creation (already covered in [spark-item-migration.md](resources/spark-item-migration.md) and [lake-database-migration.md](resources/lake-database-migration.md))
- [SQLDW-AUTHORING-CORE.md](../../common/SQLDW-AUTHORING-CORE.md) — Fabric Warehouse T-SQL; use it directly within the Dedicated Pool migration workflow, and delegate standalone Warehouse work to `sqldw-cli`

> **Auth, API endpoints, and item payloads are fully documented in this skill's own files.** The common docs above are fallback references only.

---

## Resource Routing

> **Load only the selected path.** Do not read all resources upfront.

| Request | Load |
|---|---|
| Full workspace migration | [migration-orchestrator.md](resources/migration-orchestrator.md) |
| Cross-workload planning, sizing, parity, troubleshooting, or handoff | [migration-planning-reference.md](resources/migration-planning-reference.md) |
| Complete offline Dedicated Pool to Lakehouse fixture | [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) fast path only |
| Live or incomplete Dedicated Pool to Lakehouse | [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) and [dedicated-pool-conversion.md](resources/dedicated-pool-conversion.md) |
| Dedicated Pool risk report or target-design approval | [dedicated-pool-gap-assessment.md](resources/dedicated-pool-gap-assessment.md) |
| Large-procedure audit | [dedicated-pool-large-procedure-audit.md](resources/dedicated-pool-large-procedure-audit.md) only |
| Publishing, updating, or verifying generated Dedicated Pool notebooks | [dedicated-pool-deployment.md](resources/dedicated-pool-deployment.md) |
| Dedicated Pool to Warehouse | The matching `dw-*` resource selected in the Warehouse route below |
| Spark Pool, Lake Database, external HMS, Notebook, or SJD phase | [spark-pool-migration.md](resources/spark-pool-migration.md), [lake-database-migration.md](resources/lake-database-migration.md), [external-hms-migration.md](resources/external-hms-migration.md), or [spark-item-migration.md](resources/spark-item-migration.md) |
| API/code/connectivity refactoring | [utility-api-mapping.md](resources/utility-api-mapping.md), [connector-refactoring.md](resources/connector-refactoring.md), [connectivity-migration.md](resources/connectivity-migration.md), or [code-patterns.md](resources/code-patterns.md) |
| Validation, security, reporting, or runtime compatibility | [validation-testing.md](resources/validation-testing.md), [security-governance.md](resources/security-governance.md), [migration-report.md](resources/migration-report.md), or [library-compatibility.md](resources/library-compatibility.md) |

---

## Choose Migration Path

Identify the workload before loading implementation resources:

| Source workload | Target | Route |
|---|---|---|
| Spark Pools, notebooks, Spark Job Definitions, Lake Databases, external HMS, Linked Services | Fabric Spark, Lakehouse, Environment, Data Connections, Shortcuts | Use [migration-planning-reference.md](resources/migration-planning-reference.md) and [migration-orchestrator.md](resources/migration-orchestrator.md) |
| Dedicated SQL pool schema and code artifacts | Fabric Lakehouse and Spark SQL notebooks, without source rows | Use [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) and its phase resources |
| Dedicated SQL pool in a Synapse workspace or standalone dedicated SQL pool | Fabric Warehouse, with optional separately approved data migration | Use the Warehouse steps below and load only the matching `dw-*` resource |
| Mixed Synapse workspace | Multiple Fabric targets | Inventory workloads first, then run the selected Spark, Lakehouse-artifact, and Warehouse paths independently; preserve each path's dependencies, consent gates, and validation |

If the user requests a dedicated SQL pool migration without naming Lakehouse or Warehouse as the target, explain the two outcomes and ask which path to use before conversion or provisioning.

For a dedicated SQL pool to Fabric Warehouse migration, execute this route without loading the Spark or Lakehouse-artifact orchestrators:

1. Resolve the Synapse workspace pool or standalone server/database, select metadata scope, and extract objects with [dw-source-and-extraction.md](resources/dw-source-and-extraction.md).
2. Convert DDL/DML and generate the compatibility assessment with [dw-ddl-compatibility.md](resources/dw-ddl-compatibility.md).
3. Present the assessment and obtain explicit consent before provisioning or reusing a Fabric Warehouse.
4. Resolve capacity, collation, Warehouse naming/collisions, deploy metadata, and ask separately whether to migrate table data using [dw-security-validation.md](resources/dw-security-validation.md).
5. If data is approved, use a user-managed restored source copy and follow [dw-data-migration.md](resources/dw-data-migration.md) for scoped CETAS export and COPY INTO ingestion.
6. Deploy security at the approved point and validate metadata/data with [dw-security-validation.md](resources/dw-security-validation.md).

If data migration is declined, finish the metadata and security path, print its completion summary, and do not create CETAS resources.

---

## Spark Migration Summary

For Spark workload planning, API audiences, target mapping, capacity sizing, feature parity, troubleshooting, and post-migration handoff, load [migration-planning-reference.md](resources/migration-planning-reference.md). For execution, load only the phase resource selected by the Resource Routing table. Preserve the canonical phase order: Phase 0 Environments, Phase 1 Lakehouses/shortcuts, Phase 2 Notebooks, Phase 3 Spark Job Definitions, then validation.

---

## Must / Prefer / Avoid

### MUST DO
- **Preserve stored-procedure input contracts** — keep every supported source input externally overridable through the Fabric Notebook Activity parameter mapped in first-cell `%%configure`; preserve a source default only as `defaultValue`, never replace a parameter use with a literal or invent a preview default, and block automatic publication when a required input has no source default
- **Approve stored-procedure notebook cardinality after discovery** — calculate projected workspace item demand, present `1:1`, `N:1`, and `N:N` choices, and block conversion until the user provides and approves a complete mapping, target names, dependency grouping, and workspace placement; preserve per-procedure source decisions and source-block provenance under every strategy
- **Audit large-procedure conversion by source block** — generate deterministic per-run ledger/verifier scripts, require 100% non-overlapping source-byte coverage and a deployable disposition for every block, retry only failed blocks within the declared limit, retain audit/logging behavior by default, and publish only the exact bytes in a hash-verified `ReadyForPublication` package
- **Use direct APIs for non-procedural phases** — use SqlPackage/DMVs for discovery, Fabric REST for item management, and Fabric Livy statements for schema and Delta execution
- **Choose the target route before loading resources** — do not apply Spark phases or Lakehouse artifact-conversion rules to Warehouse migration, and do not apply Warehouse data-movement steps to the Lakehouse path
- **Keep Warehouse SQL execution paths separate** — use `sqlcmd` only for the external Synapse source; use the SQL Endpoint MCP `execute_query` operation for Fabric Warehouse DDL, `COPY INTO`, security, and validation
- **Replace all `mssparkutils` imports with `notebookutils`** — see [utility-api-mapping.md](resources/utility-api-mapping.md) for the complete namespace table
- **Replace all Linked Services** with Fabric Data Connections (for external databases/services) or OneLake Shortcuts (for ADLS Gen2 / Blob storage mounts) — see [connectivity-migration.md](resources/connectivity-migration.md)
- **Replace `spark.read.synapsesql()`** with Lakehouse shortcut reads or JDBC connections to the Fabric Warehouse SQL endpoint
- **Re-test all notebooks** after migration against the target Fabric Runtime version — Spark minor version differences can surface deprecated API warnings
- **Externalize all workspace/item IDs** — never hardcode; use pipeline parameters or [migration-planning-reference.md](resources/migration-planning-reference.md)
- **Replace pool-level library installs** with Fabric Environments attached at the workspace or notebook level

### PREFER
- **Independent validation for mixed workspaces** — complete and report Spark and dedicated SQL paths separately
- **OneLake Shortcuts over full data copies** — mount existing ADLS Gen2 containers as shortcuts rather than re-ingesting data during migration
- **Fabric Starter Pool** for dev/test migrations — eliminates pool warm-up wait time inherent in Synapse on-demand pools
- **Lakehouse SQL Endpoint** as a drop-in for Serverless SQL Pool reads — point existing consumers at the endpoint with minimal query changes
- **Medallion architecture** for migrated data — align with Bronze/Silver/Gold patterns (see `e2e-medallion-architecture` skill)
- **Incremental migration** — migrate and validate workload by workload rather than performing a big-bang cutover
- **Parameterized notebooks** to allow environment promotion (dev → test → prod) without code changes

### AVOID
- **Do not use target notebooks as migration orchestration dependencies** — generated notebooks are required outputs and are published without execution
- **Do not load all Spark and DW resources upfront** — follow the Resource Routing table for the selected path
- **Do not use `sqlcmd` against the target Fabric Warehouse** — invoke the concrete MCP tool name exposed by the registered `fabric-sqlendpoint` server
- **Do not copy-paste PolyBase `CREATE EXTERNAL TABLE` DDL** into Fabric Warehouse — show `COPY INTO` with a `https://onelake.dfs.fabric.microsoft.com/...` source, or use Lakehouse for external data access
- **Do not assume Synapse Linked Service connection strings are reusable** — credentials and endpoints must be reconfigured as Fabric Data Connections
- **Do not install libraries in notebook cells** (`%pip install` at runtime) for production workloads — use Fabric Environments for reproducible, versioned library management
- **Do not use `wasb://` or `abfss://container@storageaccount.dfs.core.windows.net/` paths** as primary data paths — migrate data access to OneLake `abfss://workspace@onelake.dfs.fabric.microsoft.com/` paths

---

## Examples

See [code-patterns.md](resources/code-patterns.md) for full before/after examples. Key quick references:

**`mssparkutils.env` → `notebookutils.runtime`**

```python
# Synapse
workspace = mssparkutils.env.getWorkspaceName()
job_id = mssparkutils.env.getJobId()

# Fabric
context = notebookutils.runtime.context
workspace = context["currentWorkspaceName"]
job_id = context["activityId"]
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
For additional before/after examples, load [code-patterns.md](resources/code-patterns.md).

