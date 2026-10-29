---
name: pipeline-migration
description: "Migrates Synapse Data Factory pipelines to Fabric Data Factory, turning linked services into Fabric connections, inlining datasets into activities, converting global parameters to Variable Libraries, and mapping SynapseNotebook to TridentNotebook. Use for pipeline JSON. For Synapse Spark notebook code use synapse-migration."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: pipeline-migration` (`az rest`: `--headers "x-ms-fabric-skill=pipeline-migration"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find workspace details (including its ID) from a workspace name: list all workspaces, then use JMESPath filtering
> 2. To find item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace, then use JMESPath filtering
> 3. Fabric does NOT have a "Dataset" item type — all dataset properties are **inlined** into activity `typeProperties`
> 4. Linked Services map to Fabric **Connections** — in pipeline activity JSON, `referenceName` on the activity's `linkedService` block uses the Fabric connection **display name** (not the connection GUID); the connection GUID is used only on Fabric REST API calls
> 5. Notebook activities change from `SynapseNotebook` to `TridentNotebook` and reference notebooks by **GUID**, not by name
> 6. Synapse global parameters become a **Variable Library** item in Fabric, referenced as `@pipeline().libraryVariables.<name>`. Variable Library `Number` types are not consumable in pipelines — Synapse `Float`/`Double` are mapped to `String` for runtime compatibility
> 7. The `Validation` activity type does not exist in Fabric — it must be rewritten as `GetMetadata` + `IfCondition`
> 8. **Triggers are intentionally excluded** from this skill — recreate schedules manually in Fabric after migration
> 9. SSIS package execution, SHIR-exclusive connectors, and Databricks activities are **parked** — see [pipeline-gotchas.md](resources/pipeline-gotchas.md)

# Synapse Pipelines → Microsoft Fabric Data Factory Migration

## Prerequisite Knowledge

These companion documents provide general Fabric REST patterns. **Do NOT read them upfront** — reference only when a specific phase requires a pattern not already covered in this skill's resource files:

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — General Fabric REST API patterns, authentication & token audiences, item discovery via JMESPath
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — `az rest` / `az login` CLI patterns, authentication recipes, pipeline run/schedule operations
- [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md) — `DataPipeline` and `VariableLibrary` item definition structures (pipeline-content.json, variables.json)
- [SPARK-AUTHORING-CORE.md](../../common/SPARK-AUTHORING-CORE.md) — Fabric notebook item creation (needed when notebook items don't exist yet in Fabric)

> For the notebook side of the migration (the notebooks that pipeline activities call), use the companion **synapse-migration** skill to migrate the notebook content itself.

---

## Table of Contents

| Topic | Reference |
|---|---|
| **Pre-Migration Assessment** (run first) | [pipeline-assessment.md](resources/pipeline-assessment.md) |
| **Migration Orchestrator** | [pipeline-orchestrator.md](resources/pipeline-orchestrator.md) |
| API-Driven Migration Workflow | [§ API-Driven Migration Workflow](#api-driven-migration-workflow) |
| Activity Type Mapping | [activity-mapping.md](resources/activity-mapping.md) |
| **Notebook Activity Migration** (primary focus) | [notebook-activity-migration.md](resources/notebook-activity-migration.md) |
| Linked Services → Connections | [linked-service-to-connection.md](resources/linked-service-to-connection.md) |
| Dataset Inlining | [dataset-inlining.md](resources/dataset-inlining.md) |
| Global Parameters → Variable Library | [global-parameters-to-variable-library.md](resources/global-parameters-to-variable-library.md) |
| Pipeline Gotchas & Parked Activities | [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| Validation & Testing | [validation-testing.md](resources/validation-testing.md) |
| Migration Report | [migration-report.md](resources/migration-report.md) |

### Context Loading Guide

> **IMPORTANT — Load only what you need.** Do NOT read all resource files upfront.

| When | Read This File |
|---|---|
| User asks for an assessment, scope, or plan **before** migrating | [pipeline-assessment.md](resources/pipeline-assessment.md) |
| User asks to migrate a full pipeline workspace | [pipeline-orchestrator.md](resources/pipeline-orchestrator.md) |
| User asks about activity type mapping or unsupported activities | [activity-mapping.md](resources/activity-mapping.md) |
| User has SynapseNotebook activities (most common) | [notebook-activity-migration.md](resources/notebook-activity-migration.md) |
| User asks about linked services or connections | [linked-service-to-connection.md](resources/linked-service-to-connection.md) |
| User asks about Copy, Lookup, or GetMetadata with datasets | [dataset-inlining.md](resources/dataset-inlining.md) |
| User has global parameters to convert | [global-parameters-to-variable-library.md](resources/global-parameters-to-variable-library.md) |
| User hits SSIS, SHIR, Databricks, or other blockers | [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| Post-migration verification | [validation-testing.md](resources/validation-testing.md) |
| Generating a migration summary | [migration-report.md](resources/migration-report.md) |

---

## API-Driven Migration Workflow

### Authentication

| Target | Token Audience |
|---|---|
| Synapse Data Plane (pipelines, datasets, linked services) | `https://dev.azuresynapse.net` |
| Synapse ARM (global parameters, workspace properties) | `https://management.azure.com` |
| Fabric REST API (create pipelines, connections, Variable Libraries) | `https://api.fabric.microsoft.com` |

> Use `az account get-access-token --resource <audience> --query accessToken -o tsv` to acquire tokens.

### Synapse Data-Plane API Reference

| Operation | Endpoint |
|---|---|
| List all pipelines | `GET https://{ws}.dev.azuresynapse.net/pipelines?api-version=2020-12-01` |
| Get pipeline definition | `GET https://{ws}.dev.azuresynapse.net/pipelines/{name}?api-version=2020-12-01` |
| List all datasets | `GET https://{ws}.dev.azuresynapse.net/datasets?api-version=2020-12-01` |
| Get dataset definition | `GET https://{ws}.dev.azuresynapse.net/datasets/{name}?api-version=2020-12-01` |
| List all linked services | `GET https://{ws}.dev.azuresynapse.net/linkedservices?api-version=2020-12-01` |
| Get linked service | `GET https://{ws}.dev.azuresynapse.net/linkedservices/{name}?api-version=2020-12-01` |
| Get workspace (global parameters) | `GET https://management.azure.com/subscriptions/{subId}/resourceGroups/{rg}/providers/Microsoft.Synapse/workspaces/{ws}?api-version=2021-06-01` |

### Fabric API Reference

| Operation | Endpoint |
|---|---|
| List connections | `GET https://api.fabric.microsoft.com/v1/connections` |
| Create connection | `POST https://api.fabric.microsoft.com/v1/connections` |
| Create pipeline item | `POST https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items` |
| Update pipeline definition | `POST https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items/{id}/updateDefinition` |
| Get pipeline definition | `POST https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items/{id}/getDefinition` |
| Create Variable Library | `POST https://api.fabric.microsoft.com/v1/workspaces/{wsId}/items` (type: `VariableLibrary`) |
| List notebooks in workspace | `GET https://api.fabric.microsoft.com/v1/workspaces/{wsId}/notebooks` |

---

## Assessment Mode (Optional but Recommended)

Before creating any items in Fabric, run the **pipeline assessment** to understand scope, complexity, and blockers. The assessment is read-only — it queries Synapse APIs only and produces a markdown report.

**Copilot workflow — no Python script file needed:**
1. Ask the user: *"What is the name of your Synapse workspace?"*
2. Auto-discover subscription ID and resource group via `az account show` and `az synapse workspace show`
3. Run the assessment code inline from the terminal
4. Print the full report output directly in the chat

| When to Use | Action |
|---|---|
| User wants to understand migration scope before committing | Ask for workspace name → load [pipeline-assessment.md](resources/pipeline-assessment.md) → run inline |
| User asks "what will and won't migrate?" | Run assessment, present the Executive Summary section |
| User asks for a migration plan or scoping document | Run assessment, print report in chat |
| User has already decided to migrate | Skip assessment — go straight to Migration Phases below |

> To also save the report to disk, pass `output_path=f"pipeline-assessment-{SYNAPSE_WS}.md"` to `generate_assessment_report()`. The `PipelineAssessment` objects it produces feed directly into the migration scripts in [pipeline-orchestrator.md](resources/pipeline-orchestrator.md).

---

## Migration Mode (Inline — No Script File Required)

Copilot performs the migration directly from the terminal. No Python files to save or run manually.

**Ask the user for:**
1. Synapse workspace name (reuse from assessment if already run)
2. Fabric workspace name
3. Which pipelines to migrate — specific names, or `*` for all
4. Optional name suffix to append to each pipeline in Fabric (e.g. `_migrated`) — leave blank to keep the original name

**Everything else is auto-discovered:**
- Subscription ID and resource group via `az account show` + `az synapse workspace show`
- Fabric workspace ID via `GET /v1/workspaces` filtered by display name
- Notebook GUIDs in Fabric via `GET /v1/workspaces/{wsId}/notebooks` (required for `SynapseNotebook → TridentNotebook`)
- Connection names in Fabric via `GET /v1/connections` (when datasets reference linked services)

**What is fully automated inline:**
- ✅ `SynapseNotebook` → `TridentNotebook` — type rename, GUID lookup, remove `sparkPool`/`sessionConfiguration`, fix timeout to 12h max
- ✅ All compatible activity types — pass through with minor property adjustments
- ✅ Dataset inlining into activity `typeProperties`
- ✅ Global parameter expressions rewritten to `@pipeline().libraryVariables.<name>`
- ✅ Pipeline JSON assembly and deployment to Fabric via REST

**Copilot checks before starting — will pause and report if:**
- A notebook referenced by a `SynapseNotebook` activity does not exist in the Fabric workspace yet
- A Fabric Connection is missing for a linked service referenced by dataset activities

> Load [pipeline-orchestrator.md](resources/pipeline-orchestrator.md) for the complete inline runner.

---

## Migration Phases (Execute in Order)

| Phase | Source | Target | Resource |
|---|---|---|---|
| Phase 0 | Synapse notebooks (referenced by pipeline activities) | Fabric Notebooks | **synapse-migration** skill |
| Phase 1 | Synapse global parameters | Fabric Variable Library | [global-parameters-to-variable-library.md](resources/global-parameters-to-variable-library.md) |
| Phase 2 | Synapse linked services | Fabric Connections | [linked-service-to-connection.md](resources/linked-service-to-connection.md) |
| Phase 3 | Synapse datasets | Inlined into activities | [dataset-inlining.md](resources/dataset-inlining.md) |
| Phase 4 | Synapse pipeline activities | Fabric pipeline activities | [activity-mapping.md](resources/activity-mapping.md) + [notebook-activity-migration.md](resources/notebook-activity-migration.md) |
| Phase 5 | Assembled pipeline JSON | Fabric DataPipeline item | [pipeline-orchestrator.md](resources/pipeline-orchestrator.md) |
| Final | — | Validation | [validation-testing.md](resources/validation-testing.md) |

> **Phase 0 must precede Phase 4**: Fabric Notebook GUIDs are needed before TridentNotebook activities can be written.
> **Phase 2 must precede Phase 3**: Connection names must exist before they can be referenced in inlined datasets.

---

## Activity Type Quick Reference

Full mapping table, before/after examples, and parking decisions are in [activity-mapping.md](resources/activity-mapping.md).

| Synapse Activity | Fabric Equivalent | Status |
|---|---|---|
| `SynapseNotebook` | `TridentNotebook` | ✅ Migrated — see [notebook-activity-migration.md](resources/notebook-activity-migration.md) |
| `Copy` | `Copy` | ✅ Migrated — datasets inlined |
| `Lookup` | `Lookup` | ✅ Migrated — datasets inlined |
| `GetMetadata` | `GetMetadata` | ✅ Migrated — datasets inlined |
| `Validation` | `GetMetadata` + `IfCondition` | ✅ Migrated — split into 2 activities |
| `ForEach` | `ForEach` | ✅ Compatible |
| `IfCondition` | `IfCondition` | ✅ Compatible |
| `Switch` | `Switch` | ✅ Compatible |
| `Until` | `Until` | ✅ Compatible |
| `Wait` | `Wait` | ✅ Compatible |
| `Fail` | `Fail` | ✅ Compatible |
| `SetVariable` | `SetVariable` | ✅ Compatible |
| `AppendVariable` | `AppendVariable` | ✅ Compatible |
| `ExecutePipeline` | `ExecutePipeline` | ✅ Compatible — add `workspaceId` |
| `WebActivity` | `WebActivity` | ✅ Compatible |
| `Script` | `Script` | ✅ Compatible — update connection refs |
| `Delete` | `Delete` | ✅ Migrated — datasets inlined |
| `Filter` | `Filter` | ✅ Compatible |
| `SparkJobDefinition` (Synapse SJD) | `SparkJobDefinition` | ✅ Update GUID refs |
| `HDInsightSpark` | `TridentNotebook` or `SparkJobDefinition` | ⚠️ Rewrite required |
| `AzureMLBatchExecution` | `WebActivity` | ⚠️ Rewrite as REST call |
| `AzureFunctionActivity` | `WebActivity` | ⚠️ Rewrite — use function URL + key |
| `DatabricksNotebook` | ⛔ Parked | See [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| `DatabricksSparkJar` | ⛔ Parked | See [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| `DatabricksSparkPython` | ⛔ Parked | See [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| `ExecuteSSISPackage` | ⛔ Parked | See [pipeline-gotchas.md](resources/pipeline-gotchas.md) |
| `AzureBatch` | ⛔ Parked | No Fabric equivalent |
| `Custom` | ⛔ Parked | No Fabric equivalent |

---

## Must / Prefer / Avoid

### MUST DO
- **Migrate notebooks before pipelines** — Fabric TridentNotebook activities require notebook GUIDs, not names. Use the **synapse-migration** skill first
- **Create Fabric Connections before building pipeline JSON** — linked service names in Synapse become connection references in Fabric; you need the connection names before inlining datasets
- **Inline all dataset definitions** — Fabric Data Factory has no Dataset item type; all `inputs`/`outputs` dataset properties must be embedded in each activity
- **Replace `@pipeline().globalParameters.<name>`** with `@pipeline().libraryVariables.<name>` after creating the Variable Library
- **Replace Validation activities** with a `GetMetadata` + `IfCondition` pair — `Validation` does not exist as an activity type in Fabric
- **Remove `sparkPool` and `sessionConfiguration`** from migrated notebook activities — pool selection and session config belong in the Fabric Environment attached to the notebook

### PREFER
- **Variable Library with Value Sets** for dev/test/prod environments — use `@pipeline().libraryVariables.<name>` with environment-specific Value Sets instead of pipeline-level parameters for environment promotion
- **Parameterized `parameters`** over hardcoded values in TridentNotebook activities — mirrors Synapse parameterized notebook pattern
- **Test notebook activities individually** before running the full migrated pipeline — notebook GUIDs are the most common source of failure
- **OneLake Lakehouse sources/sinks** for Copy activities where applicable — eliminates the need for external connections for data already in OneLake

### AVOID
- **Do not reference notebooks by name** in `TridentNotebook` activities — use the GUID from the Fabric workspace notebook list
- **Do not carry over Synapse triggers** — they are not migrated by this skill; recreate schedules in Fabric after validating the pipeline
- **Do not attempt to migrate SSIS, Databricks, or AzureBatch activities** without reading [pipeline-gotchas.md](resources/pipeline-gotchas.md) first — these require manual intervention
- **Do not hardcode workspace/item GUIDs** in pipeline JSON — use Variable Library entries or pipeline parameters so environments can be promoted without editing pipeline JSON
- **Do not use `@pipeline().globalParameters`** syntax after migration — this expression path does not exist in Fabric; all migrated global parameters must be accessed via `@pipeline().libraryVariables`

---

## Migration Gotchas — Quick Reference

Full troubleshooting guide is in [pipeline-gotchas.md](resources/pipeline-gotchas.md).

| # | Flag ID | Issue | Severity | Resolution Summary |
|---|---|---|---|---|
| PG1 | `NOTEBOOK_GUID_NOT_FOUND` | Notebook not yet migrated to Fabric when building TridentNotebook activity | High | Run synapse-migration skill first; get GUID from `GET /v1/workspaces/{wsId}/notebooks` |
| PG2 | `DATASET_NOT_INLINED` | Activity still references a named dataset (not valid in Fabric) | High | Apply dataset-inlining.md patterns to embed dataset properties into activity source/sink |
| PG3 | `GLOBAL_PARAM_EXPRESSION` | `@pipeline().globalParameters.<name>` expression left in migrated pipeline | High | Replace with `@pipeline().libraryVariables.<name>` after creating Variable Library |
| PG4 | `VALIDATION_ACTIVITY_UNSUPPORTED` | `Validation` activity type left in pipeline JSON | High | Rewrite as `GetMetadata` + `IfCondition` — see activity-mapping.md |
| PG5 | `SHIR_CONNECTOR_PARKED` | Activity uses a linked service backed by a Self-Hosted Integration Runtime | Medium | Must set up on-premises data gateway in Fabric; see pipeline-gotchas.md |
| PG6 | `SSIS_ACTIVITY_PARKED` | `ExecuteSSISPackage` activity cannot be migrated | High | Parked — no Fabric equivalent; see pipeline-gotchas.md for alternatives |
| PG7 | `DATABRICKS_ACTIVITY_PARKED` | Databricks activity type has no Fabric native equivalent | High | Parked — use Databricks REST API via WebActivity as workaround; see pipeline-gotchas.md |
| PG8 | `SPARKPOOL_REF_ORPHANED` | `sparkPool` / `targetBigDataPool` reference left in TridentNotebook activity | Medium | Remove `sparkPool` and `sessionConfiguration` blocks; pool config belongs in Fabric Environment |
| PG9 | `EXECUTE_PIPELINE_NO_WORKSPACE` | `ExecutePipeline` activity missing `workspaceId` for referenced pipeline | Medium | Add `workspaceId` to `typeProperties`; required even for same-workspace child pipelines — omitting it causes runtime failures |
| PG10 | `LINKED_SERVICE_NO_CONNECTION` | Linked service has no matching Fabric Connection | High | Create connection manually or via API; update connection reference in inlined dataset |

---

## Post-Migration: What's Next

After pipeline migration, hand off to these companion skills and tools:

| Task | Skill / Tool |
|---|---|
| Migrate notebook content (mssparkutils → notebookutils, linked services) | **synapse-migration** skill |
| Schedule migrated pipelines | [COMMON-CLI.md § Job Scheduling](../../common/COMMON-CLI.md) |
| Monitor pipeline runs | Fabric workspace → Monitor hub |
| Build new Fabric pipelines | Refer to [ITEM-DEFINITIONS-CORE.md § DataPipeline](../../common/ITEM-DEFINITIONS-CORE.md) |
| Explore migrated Lakehouse data post-pipeline run | `spark-cli` or `sqldw-cli` skill |

---

## Examples

**SynapseNotebook → TridentNotebook activity (before/after)**

```json
{
  "name": "Run_Notebook",
  "type": "SynapseNotebook",
  "typeProperties": {
    "notebook": {"referenceName": "MyNotebook", "type": "NotebookReference"},
    "sparkPool": {"referenceName": "BigPool", "type": "BigDataPoolReference"}
  }
}
```

After migration (GUID from `GET /v1/workspaces/{wsId}/notebooks`):

```json
{
  "name": "Run_Notebook",
  "type": "TridentNotebook",
  "typeProperties": {
    "notebookId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "workspaceId": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
  }
}
```

**Global parameter expression rewrite**

```text
Before (Synapse):  @pipeline().globalParameters.batchDate
After (Fabric):    @pipeline().libraryVariables.batchDate
```

**Dataset inlining: Copy activity — dataset reference → connection display name**

Synapse dataset `InputBlobDataset` (will be inlined and removed):
```json
{
  "type": "AzureBlob",
  "linkedServiceName": {"referenceName": "AzureBlobLinkedService"},
  "typeProperties": {"folderPath": "input/", "fileName": "data.csv"}
}
```

Synapse Copy activity (before — references dataset by name):
```json
{
  "name": "CopyData", "type": "Copy",
  "inputs": [{"referenceName": "InputBlobDataset", "type": "DatasetReference"}],
  "typeProperties": {"source": {"type": "BlobSource"}, "sink": {"type": "BlobSink"}}
}
```

After migration (connection display name for `AzureBlobLinkedService` is `My ADLS Connection`):
```json
{
  "name": "CopyData", "type": "Copy",
  "typeProperties": {
    "source": {"type": "BlobSource", "storeSettings": {"type": "AzureBlobStorageReadSettings"}},
    "sink":   {"type": "BlobSink",   "storeSettings": {"type": "AzureBlobStorageWriteSettings"}}
  },
  "linkedService": {"referenceName": "My ADLS Connection", "type": "LinkedServiceReference"}
}
```

See [activity-mapping.md](resources/activity-mapping.md) and [notebook-activity-migration.md](resources/notebook-activity-migration.md) for full before/after examples.
