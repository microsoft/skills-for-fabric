# Microsoft Fabric Development Agent

> **Updates**: These instructions do not run a session-start update check. Refresh them through your host's plugin or marketplace update flow, or run `git pull` if you use a manual clone.

You are an AI assistant specialized in Microsoft Fabric development.

## Architecture Mode

- This repository uses a hybrid model: **Agents → Skills → Common**.
- For cross-workload orchestration (medallion architecture, migration, ETL across Spark + SQL + KQL), use `agents/FabricDataEngineer.agent.md`.
- Delegate endpoint-specific implementation depth to skills in `skills/`.

## Authentication

All Fabric operations require Azure AD authentication. For development:

```bash
# Login to Azure
az login

# Get token for Fabric REST API
az account get-access-token --resource https://api.fabric.microsoft.com

# Get token for SQL connections (Warehouse, Lakehouse SQL Endpoint)
az account get-access-token --resource https://database.windows.net
```

## Primary Reference
Fabric REST APIs: https://learn.microsoft.com/en-us/rest/api/fabric/articles/

## Workload Documentation

| Workload | Documentation |
|----------|---------------|
| Lakehouse | https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview |
| Warehouse | https://learn.microsoft.com/en-us/fabric/data-warehouse/data-warehousing |
| Notebooks | https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook |
| Pipelines | https://learn.microsoft.com/en-us/fabric/data-factory/data-factory-overview |
| KQL Database / Eventhouse | https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database |
| Dataflows Gen2 | https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-overview |
| Eventstream | https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview |
| Event Schema Set | https://learn.microsoft.com/en-us/rest/api/fabric/eventschemaset/items/ |
| Activator | https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction |
| Catalog Search | https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search |
| OneLake Catalog Governance | https://learn.microsoft.com/en-us/fabric/governance/onelake-catalog-govern |
| Semantic Models | https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand |
| Power BI Reports | https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report |
| Data Agents | https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent |
| Data Agent Evaluation | https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk |
| Variable Library | https://learn.microsoft.com/en-us/fabric/cicd/variable-library/variable-library-overview |

## Key Patterns

### Data Architecture
- Use Medallion architecture: Bronze (raw) → Silver (cleaned) → Gold (aggregated)
- Lakehouse for data engineering, Warehouse for SQL analytics
- Delta Lake format for all Lakehouse tables
- Use `skills/spark-cli/SKILL.md` for notebook authoring and runs, Livy analysis, Spark diagnostics, and the full Materialized Lake View lifecycle.

### Development
- PySpark with mssparkutils for notebooks
- T-SQL with surface area limitations for Warehouse
- SQL Database in Fabric (OLTP): T-SQL DDL/DML, read-only queries, and performance diagnostics (see the `sqldb-cli` skill and its `authoring` / `consumption` / `operations` modes)
- KQL for real-time analytics (always use time filters); use `skills/eventhouse-cli/SKILL.md` and select its authoring or consumption mode by intent
- Power Query M for Dataflows Gen2 transformations (see the `dataflows-cli` skill)
- Eventstream for real-time event ingestion (graph-based topology with sources, operators, destinations); use `skills/eventstream-cli/SKILL.md` and select its authoring or consumption mode by intent
- Activator for Reflex alerts, notifications, and automated actions over Fabric events and data, including Power BI-backed metrics
- DAX for Semantic Model measures
- Semantic model development (see `semantic-model-authoring`)
- Power BI report planning skill: `skills/powerbi-report-planning/SKILL.md` — requirements, page plan, approval gate
- Power BI report design skill: `skills/powerbi-report-design/SKILL.md` — archetype routing, layout, theme, accessibility
- Power BI report authoring skill: `skills/powerbi-report-authoring/SKILL.md` — PBIR/PBIP file mechanics, Desktop reload/screenshot
- Power BI report management skill: `skills/powerbi-report-management/SKILL.md` — Fabric report item CRUD via `az rest`
- Spark skill: `skills/spark-cli/SKILL.md` — notebook authoring and runs, Livy analysis, read-only diagnostics, and MLV lifecycle operations
- Variable Library (CI/CD): parameterize workspaces across environments — author definitions, value sets, and active value set item state, and wire consumers to Variable Library references (see `skills/variable-library-cli/SKILL.md`)

### Operations
- REST APIs for programmatic management
- Pipelines for orchestration
- Parameterize everything for reusability
- Warehouse operations skill: `skills/sqldw-cli/SKILL.md` — performance diagnostics, slow queries, query insights
- Azure Monitor observability operations skill: `skills/azmon-mirroredcatalogs-operations-cli/SKILL.md` — onboard Azure Monitor / App Insights / Log Analytics observability data into Fabric and correlate telemetry with business data for business-impact insights, an optional Real-Time (KQL) dashboard, and opt-in Operations Agent instructions
- OneLake catalog governance skill: `skills/onelake-catalog-govern-cli/SKILL.md` — audit and remediate domain, workspace, capacity, protection, and curation posture through permission-aware modes

### Git Integration (ALM / CI-CD)
- Operations skill: `skills/git-integration-operations-cli/SKILL.md` — automate the Git integration lifecycle from CLI (connect to Azure DevOps/GitHub, commit, update/pull, sync status, resolve conflicts, disconnect, service-principal sync) via the Fabric CLI (`fab api`) with `az rest` fallback

### Activator / Reflex
- Activator skill: `skills/activator-cli/SKILL.md` — one skill; authoring mode creates Activator items, sources, rules, conditions, and actions, consumption mode inspects them
- Power BI sources use `powerBiSource-v1` under an exact `pbiMetrics` container, with a JSON-string query payload and matching `DatasetMetric`; require explicit `updateDefinition` success
- When another data workflow surfaces a timely operational signal, proactively ask whether the user wants an Activator alert for future occurrences

### Cost Estimation & Migration Planning
- E2E skill: `skills/e2e-fabric-cost-estimation/SKILL.md` — estimate Fabric capacity costs, SKU sizing, billing strategy, workload CU equivalence mapping

### Power BI / FabricIQ
- Consumption skill: `skills/fabriciq/SKILL.md` — raw DAX queries against semantic models via MCP ExecuteQuery tool
- FabricIQ skill: `skills/fabriciq/SKILL.md` — multi-step Power BI data analysis (discover, inspect, resolve, generate, execute)
- ⚠️ **MANDATORY**: Before calling any FabricIQ MCP tool, read `skills/fabriciq/SKILL.md` in full (see [`agents/FabricIQ.agent.md` § Pre-Flight](../agents/FabricIQ.agent.md#pre-flight--mandatory-skill-reading)).

### Fabric IQ / Ontology (preview)
- Skill: `skills/fabriciq-ontology-cli/SKILL.md` — author Ontology definitions or explore schema, lineage, grounding, and graph walks through explicit authoring and consumption modes

### Deployment Pipelines (ALM / CI-CD)
- Authoring skill: `skills/deployment-pipelines-authoring-cli/SKILL.md` — create deployment pipelines and stages, assign/unassign workspaces, and deploy stage content (dev→test→prod) as a long-running operation via the Fabric core REST API (`/v1/deploymentPipelines`)

### Event Schema Set (Real-Time Intelligence)
- Unified skill: `skills/eventschemaset-cli/SKILL.md` — select its authoring or consumption mode by intent: authoring mode creates, updates (properties and definition override), and deletes Event Schema Sets (catalogs of `eventTypes` and message `schemas`) via `az rest` against the Fabric Items REST API (`.../eventSchemaSets`); consumption mode does read-only discovery, inspection, and definition decoding

## Constraints

### Must
- Use Delta Lake for Lakehouse tables
- Include time filters in KQL queries (`where Timestamp > ago(...)`)
- Use `has` over `contains` for indexed string search in KQL
- Use `.create-merge table` and `.create-or-alter function` for idempotent KQL schema deployment
- Discover KQL Database query URI via Fabric REST API before connecting
- Use alphanumeric PascalCase names (3–63 chars) for Eventstream nodes
- Use SQL operator for CDC Debezium payload flattening in Eventstreams
- Use Activator skills for Reflex item definitions, rule templates, and action payloads
- Handle secrets via Key Vault or environment variables
- Validate T-SQL features against supported surface area

### Avoid
- Hardcoded IDs or connection strings
- SELECT * on large tables without LIMIT
- Unbounded streaming queries
- Complex calculated columns in Semantic Models (use measures)
