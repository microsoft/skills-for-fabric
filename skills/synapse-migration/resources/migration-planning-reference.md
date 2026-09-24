# Migration Planning Reference

Load this reference only for cross-workload planning, target comparison, capacity planning, feature-parity review, troubleshooting, post-migration handoff, or the detailed Dedicated Pool contracts routed here from `SKILL.md`. Do not load it for a path-specific execution request whose focused resource already supplies the required contract.

## Detailed Dedicated Pool Contracts

### Live, Partially Specified, and Offline Artifact Contract

Before generating live or partially specified Dedicated Pool artifacts, read both [dedicated-pool-to-lakehouse.md](dedicated-pool-to-lakehouse.md) and [dedicated-pool-conversion.md](dedicated-pool-conversion.md). A complete offline request that already supplies inventory, target binding, approvals, exact artifact schemas, and validation contracts is the exception: follow the [Offline Lakehouse Artifact Fast Path](dedicated-pool-to-lakehouse.md#offline-lakehouse-artifact-fast-path). Transcribe every requested property name, value, and executable predicate exactly; do not substitute aliases. In `expected-schema.json`, the table discriminator is `objectType` and its identity is `sourceStableId`; do not emit `type` or `sourceIdentifier`. Character length remains part of `sourceType` and is not numeric precision: for every `NVARCHAR(n)` to `STRING` mapping, set `precision` and `scale` to JSON `null`, never to `n`. In manifest `parameterMappings`, the parameter identity property is `sourceParameter`; do not emit `parameterName` there. In a parameterized notebook, make `conf` one flat JSON object whose direct property names are the fully qualified configuration keys; each value is an object with `parameterName` and `defaultValue`, never emit `conf` as an array. Parameterless notebooks have no `%%configure`. Every code-cell source must begin with its executable magic: bare `%%configure` for the first parameterized code cell and `%%sql` for every validation or transformation code cell. Use `try_cast` for pre-mutation type validation, but immediate `CAST` in transformation predicates, including `CAST('${...IncludeInactive}' AS BOOLEAN)` directly without `LOWER`. The verifier must assert every supplied property and reject aliases, plus validate notebook cells, typed substitutions, hashes, and contract cases rather than sampling representative fields. If verification fails, fix the generator and rerun generation and verification; never patch artifacts. For a completed offline Lakehouse conversion, start the response `Fabric Lakehouse <name> migration: generated notebooks contain executable translated Spark SQL in %%sql cells; no source rows were moved.`

### Feature-Risk Assessment and Workspace Projection Contract

For Dedicated Pool feature-risk assessments, address every material feature named in the request or discovered catalogs; when present, give distribution, multi-statement transactions, row-level security, workload management, and shared staging logic their own representative risk rows rather than collapsing them into generic categories. Record unsupported, redesign, and unknown dispositions instead of silently omitting a feature. Explicitly state that the Phase 2 approval gate in Note 5 blocks conversion until the customer approves the complete stored-procedure mapping. Before approval, compare candidate mapping scenarios and always calculate and state `1:1 projected notebook count = discovered procedure count`; do not defer that projection because the final mapping or workspace placement is unknown. For `N:1` and `N:N`, count distinct proposed target notebook components when supplied, otherwise mark those candidate counts unknown. Calculate each target workspace's projected total as current items plus planned non-notebook items, assigned notebooks, and reserved operational headroom; compare it with the documented 1,000-item limit and block an over-limit or unknown-capacity design until it is repartitioned or clarified.

Every feature-risk response must state: `Conversion remains blocked until the customer approves the complete stored-procedure mapping.` Spell out `multi-statement transaction`; do not abbreviate it as `txn`. Keep these statements explicit even when a risk matrix or closing approval sentence conveys the same meaning.

### Lakehouse Publication and Hash Contract

For Dedicated Pool-to-Lakehouse outputs, explicitly narrate the migration to the Fabric Lakehouse target, publish notebook definitions with `format: "ipynb"`, and compute each manifest `contentHash` from the final notebook bytes only after all writes are complete. Any later notebook change requires recomputing the hash before validation or publication.

## API-Driven Migration Workflow

This skill supports programmatic migration of Synapse Spark items via REST APIs (no UI-based Migration Assistant required).

### Authentication

| Target | Token Audience |
|---|---|
| Synapse ARM (management plane) | `https://management.azure.com` |
| Synapse Data Plane | `https://dev.azuresynapse.net` |
| Fabric REST API | `https://api.fabric.microsoft.com` |

> Use the token-acquisition recipe in [COMMON-CLI § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes) with the audiences above.

### Migration Phases (Execute in Order)

| Phase | Synapse Source | Fabric Target | Resource |
|---|---|---|---|
| Phase 0 | Spark Pool | Environment | [spark-pool-migration.md](spark-pool-migration.md) |
| Phase 1 | Lake Database (built-in HMS) | Lakehouse | [lake-database-migration.md](lake-database-migration.md) |
| Phase 1 | External Hive Metastore | Lakehouse | [external-hms-migration.md](external-hms-migration.md) |
| Phase 1b | Ad-hoc `abfss://` storage paths | OneLake Shortcuts | [migration-orchestrator.md](migration-orchestrator.md) (migrate-and-modernize only) |
| Phase 2 | Notebooks | Notebook | [spark-item-migration.md](spark-item-migration.md) |
| Phase 3 | Spark Job Definitions | SJD | [spark-item-migration.md](spark-item-migration.md) |
| Final | Validation & Testing | — | [validation-testing.md](validation-testing.md) |
| Optional | Security & Governance | — | [security-governance.md](security-governance.md) |

> **Phase order matters**: Environments (Phase 0) must exist before notebooks/SJDs can bind to them. Lakehouses (Phase 1) must exist before notebooks can bind to them (Phase 2).

> For the full execution flow with sub-steps, decision points, lift-and-shift vs. modernize paths, and error recovery, see [migration-orchestrator.md](migration-orchestrator.md).

### REST API Quick Reference

All Synapse and Fabric API endpoints with request/response examples are in [migration-orchestrator.md](migration-orchestrator.md) (Steps 2a–2e). Authentication tokens:

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
| **Dedicated SQL Pool** | **Fabric Lakehouse** (stored procedures → Spark SQL notebooks; tables/views → Lakehouse objects) or **Fabric Warehouse** | **Lakehouse path**: extract metadata with SqlPackage/catalog queries, assess projected workspace item demand, require the user to provide and approve a `1:1`, `N:1`, or `N:N` procedure-notebook mapping (applies ONLY to stored procedures, NOT views), then convert schema and code artifacts. Tables and views are deployed as Lakehouse schema objects via Livy; only stored procedures convert to notebooks. Source table rows are not migrated; see [dedicated-pool-to-lakehouse.md](dedicated-pool-to-lakehouse.md). **Warehouse migration path**: use the `dw-*` resources in this skill; delegate only unrelated general Warehouse authoring to `sqldw-cli`. |
| **Serverless SQL Pool** | **Lakehouse SQL Endpoint** | Read-only Delta/Parquet queries; no DDL required |
| **Synapse Pipelines** | **Fabric Data Pipelines** | Activity types, triggers, and expressions are broadly compatible. *Pipeline migration resource not yet available — separate migration track.* |
| **Synapse Link for Cosmos DB / SQL** | **Fabric Mirroring** | Native mirroring replaces the Synapse Link connector pattern. *Not covered by this skill.* |
| **Linked Services** | **Data Connections** (external) / **OneLake Shortcuts** (storage) | See [connectivity-migration.md](connectivity-migration.md) |
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

For Spark-oriented T-SQL surface gaps and Spark configuration mappings, see [feature-parity.md](feature-parity.md). For a dedicated SQL pool migration assessment, use [dw-ddl-compatibility.md](dw-ddl-compatibility.md).

> **Key actions**: Replace PolyBase `CREATE EXTERNAL TABLE` with `COPY INTO`, and show an unmistakable OneLake/Fabric source such as `https://onelake.dfs.fabric.microsoft.com/<workspace>/<item>.Lakehouse/Files/...` when giving the replacement example. Replace `spark.read.synapsesql()` with OneLake shortcuts or JDBC. For Dedicated Pool-to-Warehouse migration, follow the `dw-*` resources in this skill; delegate only general Warehouse authoring outside that migration path to `sqldw-cli`.

---

## Capacity Sizing Reference

For Synapse pool → Fabric SKU mapping tables, sizing decision guide, and cost model comparison, see [capacity-sizing.md](capacity-sizing.md).

> **Quick guide**: Dev/test = F8–F16 with Starter Pool; standard production = F32–F64; enterprise = F128+. Use Fabric Trial (free F64, 60 days) for migration validation.

---

## Feature Parity Reference

Full Synapse → Fabric feature matrix (28 features), T-SQL surface area gaps, and Spark configuration differences are in [feature-parity.md](feature-parity.md).

> **Key gaps** (⚠️/❌): `spark.read.synapsesql()` replaced by JDBC/shortcuts · Linked Services redesigned as Data Connections/Shortcuts · External HMS partial (migrate as shortcuts) · `mssparkutils.env` renamed to `notebookutils.runtime` · Result set caching ❌ · Workload management ❌ · PolyBase → `COPY INTO`

---

## Migration Gotchas — Quick Reference

The full troubleshooting guide with code examples and multi-option resolutions is in [migration-gotchas.md](migration-gotchas.md). This summary surfaces the key issues for quick scanning during migration:

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

After completing Spark Phases 0–3 or the dedicated SQL pool steps and validation, hand off to these companion skills for ongoing operations:

### Agentic Exploration Workflow

Use this sequence only after a separately approved process has loaded data into Fabric Lakehouses. The Dedicated Pool to Lakehouse pattern in this skill migrates schema and code artifacts only, so it must stop after artifact validation and must not run this workflow.

For migrations that explicitly include approved data movement and data validation:

1. **Discover** → List schemas, tables, and row counts via Lakehouse SQL Endpoint (`sqldw-cli`)
2. **Sample** → `SELECT TOP 5` on migrated tables to verify data integrity
3. **Validate** → Run validation checks from [validation-testing.md](validation-testing.md) (V1–V6)
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
- Full Variable Library patterns → see [common/notebook-authoring/context-and-params.md § Variable Library](../../../common/notebook-authoring/context-and-params.md#variable-library)
