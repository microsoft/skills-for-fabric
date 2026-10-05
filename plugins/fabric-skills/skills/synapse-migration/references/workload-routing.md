# Workload Routing, Examples, and Handoffs

Load this file when selecting a Fabric target, planning phase order, answering a quick migration-pattern question, or handing off post-migration work.

## Contents

- [Authentication Audiences](#authentication-audiences)
- [Migration Phase Order](#migration-phase-order)
- [Workload Map](#workload-map)
- [Quick Transformations](#quick-transformations)
- [Common Edge Cases](#common-edge-cases)
- [Post-Migration Handoff](#post-migration-handoff)

## Authentication Audiences

Use the token-acquisition recipe in `common/COMMON-CLI.md`.

| Target | Token audience |
|---|---|
| Synapse ARM | `https://management.azure.com` |
| Synapse data plane | `https://dev.azuresynapse.net` |
| Fabric REST API | `https://api.fabric.microsoft.com` |

## Migration Phase Order

| Phase | Synapse source | Fabric target | Resource |
|---|---|---|---|
| 0 | Spark Pool | Environment | `resources/spark-pool-migration.md` |
| 1 | Lake Database | Lakehouse | `resources/lake-database-migration.md` |
| 1 | External Hive Metastore | Lakehouse | `resources/external-hms-migration.md` |
| 1b | Ad-hoc `abfss://` paths | OneLake Shortcuts | `resources/migration-orchestrator.md` |
| 2 | Notebooks | Fabric Notebook | `resources/spark-item-migration.md` |
| 3 | Spark Job Definitions | Fabric SJD | `resources/spark-item-migration.md` |
| Conditional | Approved dependent procedure callers | Fabric Data Pipeline | `resources/dedicated-pool-dependent-pipelines.md` |
| Final | Validation | — | `resources/validation-testing.md` |
| Optional | Security/governance | — | `resources/security-governance.md` |

Environments must exist before notebook/SJD binding. Lakehouses must exist before notebook binding. Always report phase 1; if no Lake Database or HMS is found, use the literal heading `Phase 1 — Lake Database/HMS to Lakehouse: NotApplicable (none discovered)`.

## Workload Map

| Synapse component | Fabric target | Important distinction |
|---|---|---|
| Spark Pool | Environment plus Notebook or SJD | Migrate configuration, libraries, and code |
| Dedicated SQL Pool | Lakehouse or Warehouse | Lakehouse converts schema/code artifacts without rows; Warehouse authoring belongs to `sqldw-cli` |
| Serverless SQL Pool | Lakehouse SQL Endpoint | Read-only Delta/Parquet queries need no DDL migration |
| ADF/Synapse Pipeline | Fabric Data Pipeline | Standalone requests use `pipeline-migration`; only approved procedure callers remain internal |
| Synapse Link | Fabric Mirroring | Not covered by this skill |
| Linked Service | Data Connection or OneLake Shortcut | External service/database vs. storage |
| Integration Dataset | Pipeline source/sink configuration | Not covered by this skill |
| Managed VNet | Managed Private Endpoints | Configure in Fabric capacity settings |

For Spark workloads:

- Interactive exploration -> Fabric Notebook attached to a Lakehouse.
- Scheduled production job -> Spark Job Definition.
- T-SQL over files/Delta -> Lakehouse SQL Endpoint.
- Real-time ingestion -> Eventstream plus Lakehouse.

## Quick Transformations

Full examples are in `resources/code-patterns.md`.

### Runtime context

```python
# Synapse
workspace = mssparkutils.env.getWorkspaceName()
job_id = mssparkutils.env.getJobId()

# Fabric
context = notebookutils.runtime.context
workspace = context["currentWorkspaceName"]
job_id = context["activityId"]
```

### Linked Service credential

`mssparkutils.credentials.getConnectionStringOrCreds` is not available in Fabric. Distinguish Data Connections from OneLake Shortcuts before choosing a replacement. For a Key Vault-backed secret:

```python
conn = notebookutils.credentials.getSecret(
    "https://myvault.vault.azure.net/",
    "my-secret",
)
```

### Dedicated SQL Pool DDL

```sql
-- Synapse
CREATE TABLE dbo.Fact (...) WITH (
    DISTRIBUTION = HASH(id),
    CLUSTERED COLUMNSTORE INDEX
);

-- Fabric Warehouse
CREATE TABLE dbo.Fact (...);
```

For Lakehouse conversion, follow `resources/dedicated-pool-conversion.md` instead of applying this Warehouse example.

## Common Edge Cases

Use `resources/migration-gotchas.md` for full resolutions.

| Flag | Issue | Default resolution |
|---|---|---|
| `SYNAPSESQL_NO_EQUIVALENT` | `spark.read.synapsesql()` has no direct equivalent | OneLake Shortcut, Warehouse JDBC, or Data Pipeline |
| `LIBRARY_VERSION_CONFLICT` | Library conflicts with Fabric Runtime | Pin in an Environment or choose a Fabric-native alternative |
| `DELTA_PROTOCOL_MISMATCH` | Delta protocol incompatibility | `ManualReviewRequired`; use only an approved compatible new-target plan, never rewrite the source or an existing target |
| `SECURITY_MODEL_INCOMPATIBLE` | Managed identity/firewall model is not portable | Workspace Identity plus Managed Private Endpoints |
| `GPU_POOL_UNSUPPORTED` | GPU Spark pool | Keep in Synapse or move to Azure ML |
| `DOTNET_SPARK_UNSUPPORTED` | .NET for Spark | Rewrite in PySpark or keep in Synapse |
| `NULLABLE_POOL_REFERENCE` | `bigDataPool` is `null` | Use `(x.get("bigDataPool") or {}).get(...)` |
| `SESSION_CONFIG_IGNORED` | Unsupported `%%configure` keys | Remove them; use an Environment for pool-level settings |

## Post-Migration Handoff

The Dedicated Pool-to-Lakehouse workflow stops after artifact validation because it does not move data. Run data exploration only after a separately approved process loads data.

| Follow-up task | Skill |
|---|---|
| Lakehouse SQL exploration | `sqldw-cli` |
| PySpark exploration or new Notebook/SJD authoring | `spark-cli` |
| Bronze/Silver/Gold design | `e2e-medallion-architecture` |
| Semantic model creation | `semantic-model-authoring` |
| Report/semantic-model business questions | `fabriciq` |
| KQL analytics | `eventhouse-cli` |

For environment promotion, use a Fabric Variable Library instead of hardcoded IDs:

```python
lib = notebookutils.variableLibrary.getLibrary("MigrationConfig")
lakehouse_name = lib.lakehouse_name
workspace_id = lib.workspace_id
```

Use Value Sets for environments. Boolean values arrive as strings, and Data Pipelines reference library variables through `@pipeline().libraryVariables.<name>`.
