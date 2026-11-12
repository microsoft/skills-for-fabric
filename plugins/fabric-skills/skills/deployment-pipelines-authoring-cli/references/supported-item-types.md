# Supported item types for Fabric deployment pipelines

Reference list of the Fabric item types that deployment pipelines can copy from one
stage to another. **This list changes over time** as workloads onboard to CI/CD and
graduate items out of preview — treat it as a living document.

- **Canonical source (source of truth):** [Introduction to deployment pipelines § Supported items](https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#supported-items)
  on Microsoft Learn. Reconcile this table against that page.
- **How to keep this current:** re-fetch the docs page above and reconcile this table
  (add/remove rows, update the `Status` / preview flags). An item is **supported** when
  the docs list it under *Supported items*. Do not hand-edit from memory.
- **Status scope:** support in the canonical list, a feature-specific preview, GA,
  and production readiness are different claims. An absent preview marker in the
  list is not proof of GA or release readiness. Attribute a preview qualification
  to the specific document and feature that states it.
- **Last reconciled:** 2026-07-20 (against the public docs page, `updated_at` 2026-07-17).
- **Warehouse-only correction:** checked 2026-11-09 against the canonical list
  (`updated_at` 2026-11-06), which lists Warehouse **without** a preview marker.
  The separate [Warehouse development and deployment overview](https://learn.microsoft.com/en-us/fabric/data-warehouse/development-deployment)
  (`updated_at` 2026-09-22) explicitly labels its feature preview. Do not attribute
  that marker to the supported-items list. Other rows retain the earlier snapshot.

> **Retirement note:** Beginning **February 12, 2026**, deployment pipelines retire
> support for semantic models that have **not** been upgraded to Enhanced Metadata.
> See [Retirement of semantic model support](https://learn.microsoft.com/fabric/cicd/troubleshoot-cicd#retirement-of-semantic-model-support-for-deployment-pipelines).

## How to use this list

- Only items in this list are copied during a deploy; unsupported items in a source
  workspace are simply skipped (not an error).
- For a **selective** deploy, each entry in the deploy `items` array is
  `{ "sourceItemId", "itemType" }`. The `itemType` is the Fabric REST **item type name**
  (e.g. `SemanticModel`, `Report`, `Notebook`, `Lakehouse`, `SparkJobDefinition`,
  `DataPipeline`, `Eventhouse`, `KQLQueryset`, `Dataflow`). The display names below come
  from the docs and may differ from the REST enum value — **read the exact `itemType`
  back from `GET .../stages/{stageId}/items`** rather than guessing it.
- `preview` items may behave differently or require the item's own preview to be enabled.

## Supported items (by category)

| Category | Item | Status |
|---|---|---|
| Data Engineering | Environment | GA |
| Data Engineering | GraphQL API | GA |
| Data Engineering | Lakehouse | GA |
| Data Engineering | Notebook | GA |
| Data Engineering | Spark Job Definition | GA |
| Data Engineering | User Data Functions | GA |
| Data Science | Machine Learning Experiment | preview |
| Data Science | Machine Learning Model | preview |
| Data Science | Data Agent | GA |
| Data Factory | Copy Job | GA |
| Data Factory | Dataflow Gen2 | GA |
| Data Factory | Data Pipeline | GA |
| Data Factory | Mirrored Database | GA |
| Data Factory | Mount ADF (Azure Data Factory) | GA |
| Data Factory | Mirrored Snowflake | preview |
| Data Factory | Apache Airflow Job | preview |
| Data Factory | dbt Job | preview |
| Data Factory | Operations Agent | preview |
| Real-Time Intelligence | Activator | GA |
| Real-Time Intelligence | Digital Twin Builder | preview |
| Real-Time Intelligence | Eventhouse [^kqldb] | GA |
| Real-Time Intelligence | Eventstream | GA |
| Real-Time Intelligence | KQL Queryset | GA |
| Real-Time Intelligence | Real-Time Dashboard | GA |
| Real-Time Intelligence | Maps | GA |
| Real-Time Intelligence | Event Schema Set | preview |
| Real-Time Intelligence | Anomaly Detection | preview |
| Data Warehouse | Warehouse | Listed; no preview marker in supported-items list |
| Data Warehouse | Mirrored Azure Databricks Catalog | GA |
| Power BI | Dashboard | preview |
| Power BI | Dataflow (Power BI) | preview |
| Power BI | Org App | preview |
| Power BI | Paginated Report | preview |
| Power BI | Report | preview |
| Power BI | Semantic Model | preview |
| Database | SQL Database | GA |
| Database | Cosmos DB Database | preview |
| Graph | Graph Model | GA |
| Graph | Graph Queryset | GA |
| CI/CD | Variable Library | GA |
| Industry solutions | Healthcare | preview |
| Industry solutions | HealthCare Cohort | preview |
| IQ | Ontology | preview |
| IQ | Plan | preview |

[^kqldb]: **KQL databases** are deployed as part of their parent **Eventhouse** rather
    than as a standalone entry. In a selective deploy the KQL database still surfaces as
    its own `itemType` in the stage-items list; read the exact value back from
    `GET .../stages/{stageId}/items`.
