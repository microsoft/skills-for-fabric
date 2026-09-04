# Microsoft Fabric Development Instructions

> **Updates**: `fabric-collection` is a third-party marketplace, so enable auto-update once: run `/plugin`, open **Marketplaces**, select `fabric-collection`, and choose **Enable auto-update**. Administrators can instead set `"autoUpdate": true` on its `extraKnownMarketplaces` entry in managed settings. To update on demand, run `claude plugin update <plugin>@fabric-collection`. If these files were copied in loosely rather than installed as a plugin, compare the local `package.json` version against the remote (`git fetch origin main --quiet && git show origin/main:package.json`) and re-copy if it is newer.

This project uses Microsoft Fabric for data engineering, warehousing, and analytics.

## Architecture Mode

- Use the hybrid layering model: **Agents → Skills → Common**.
- For cross-workload orchestration, start with `agents/FabricDataEngineer.agent.md`.
- Delegate deep endpoint implementation to relevant skills under `skills/`.

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

## Fabric REST APIs

All Fabric operations use the REST APIs documented at:
https://learn.microsoft.com/en-us/rest/api/fabric/articles/

## Developer vs Consumer Patterns

### Developers
- Use **REST APIs** to create/manage artifacts (workspaces, warehouses, lakehouses)
- Use **protocol-specific** connections to access data:
  - ODBC/JDBC for Warehouse queries
  - Spark/PySpark for Lakehouse data
  - XMLA/DAX for Semantic Models
  - KQL for Real-Time Intelligence

### Consumers
- Use **MCP servers** for natural language queries
- Limited to: Semantic Models, Warehouses, Lakehouse SQL Endpoints
- No ODBC/JDBC setup needed - MCP handles connections

## Workloads

### Data Engineering
- **Lakehouse**: Delta tables, Spark, file management
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview
  - Spark skill: `skills/spark-cli/SKILL.md` — notebook authoring and runs, Livy analysis, Spark diagnostics, and the full Materialized Lake View lifecycle.
- **Notebooks**: PySpark notebooks with mssparkutils
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- **Spark Jobs**: Production Spark workloads
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/spark-job-definition
  - Spark diagnostics: `skills/spark-cli/SKILL.md` — read-only triage for failed jobs, stuck sessions, and performance bottlenecks

### Data Warehouse
- **Warehouse**: T-SQL data warehouse
  - Docs: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-warehousing
  - Note: Limited T-SQL surface area - check supported features
  - Skill: `skills/sqldw-cli/SKILL.md` — one skill, three modes: authoring (DDL, DML, ingestion, schema changes), consumption (read-only T-SQL queries), operations (performance diagnostics, slow queries, query insights)

### Application Lifecycle Management (ALM)
- **Deployment Pipelines**: Promote Fabric content across dev/test/prod stages
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/deployment-pipelines
  - Authoring skill: `skills/deployment-pipelines-authoring-cli/SKILL.md` — create pipelines/stages, assign/unassign workspaces, deploy stage content (LRO)
  - Primary CLI tool: `az rest` via `/v1/deploymentPipelines`
  - Token audience: `https://api.fabric.microsoft.com`

### SQL Database (in Fabric)
- **SQL database**: OLTP database with an enforced T-SQL surface, Query Store, and DMVs (distinct from the Warehouse)
  - Docs: https://learn.microsoft.com/en-us/fabric/database/sql/overview
  - Skill: `skills/sqldb-cli/SKILL.md` — one mode dispatcher: `authoring` (DDL/DML, constraints, indexes, source control, SqlPackage deploy, GraphQL), `consumption` (read-only T-SQL exploration, vector similarity, JSON, temporal queries), `operations` (performance diagnostics via Query Store, DMVs, Extended Events)

### Data Integration
- **Pipelines**: Orchestration and data movement
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/data-factory-overview
- **Dataflows Gen2**: Low-code transformations with Power Query
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-overview
  - Dataflows skill: `skills/dataflows-cli/SKILL.md` -- one skill covering the whole Dataflows item; it selects a mode and reads the matching reference
    - Authoring mode: `references/authoring.md` -- dataflow lifecycle management, Power Query M mashup authoring
    - Consumption mode: `references/consumption.md` -- read-only dataflow exploration, monitoring, status queries
  - Primary CLI tool: `az rest` via Fabric REST API

### Real-Time Intelligence
- **Eventstreams**: Real-time data ingestion
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview
  - Eventstream skill: `skills/eventstream-cli/SKILL.md` -- one skill covering the whole Eventstream item
    - Authoring mode: create, configure and deploy Eventstream topologies
    - Consumption mode: list, inspect and monitor Eventstreams
  - Primary CLI tool: `az rest` via Fabric REST API
- **Event Schema Sets**: Catalogs of event types and message schemas
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/eventschemaset/items/
  - Unified skill: `skills/eventschemaset-cli/SKILL.md` — authoring mode to create, update (properties and definition), and delete Event Schema Sets (`eventTypes`, `schemas`); consumption mode to list, inspect, and decode Event Schema Set definitions read-only
  - Primary CLI tool: `az rest` via Fabric REST API (`.../eventSchemaSets`)
- **Activator**: Alerts, notifications, and automated actions over Fabric data/events
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction
  - Activator skill: `skills/activator-cli/SKILL.md` -- one skill covering the whole Activator / Reflex item
    - Authoring mode: create Activator items, sources, rules, conditions, and actions
    - Consumption mode: inspect Activator definitions, rules, sources, and actions
  - Primary CLI tool: `az rest` via Fabric REST API
  - Power BI-backed alerts use exact `pbiMetrics` containers plus `powerBiSource-v1`, a JSON-string `query.queryString`, and a matching `DatasetMetric`; require explicit `updateDefinition` success
  - When another data workflow surfaces a timely operational signal, proactively ask whether the user wants an Activator alert for future occurrences
- **Fabric IQ / Ontology (preview)**: Semantic model of entity types, properties, and relationships over Fabric data
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/articles/
  - Skill: `skills/fabriciq-ontology-cli/SKILL.md` — select authoring or consumption mode for definition changes, grounding, lineage, and graph walks
  - Primary CLI tool: `az rest` via Fabric REST API
- **KQL Database / Eventhouse**: Time-series queries with Kusto
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database
  - Unified skill: `skills/eventhouse-cli/SKILL.md` — authoring mode for table management, ingestion, policies, and materialized views; consumption mode for read-only KQL queries and schema discovery
  - Primary CLI tool: `az rest` via Kusto REST API (`/v1/rest/query` and `/v1/rest/mgmt`)
  - Token audience: `https://kusto.kusto.windows.net/.default`
- **Azure Monitor Observability (into Fabric)**: Onboard Azure Monitor / Application Insights / Log Analytics telemetry into Fabric and correlate it with business data for business-impact insights
  - Docs: https://learn.microsoft.com/en-us/azure/azure-monitor/overview
  - Operations skill: `skills/azmon-mirroredcatalogs-operations-cli/SKILL.md` — onboard Azure Monitor / App Insights / Log Analytics observability data into Fabric, correlate telemetry with business data, optionally build a Real-Time (KQL) dashboard, and generate opt-in Operations Agent instructions

### OneLake Catalog Search
- **Catalog Search API**: Cross-workspace item discovery
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search
  - Consumption skill: `skills/search-consumption-cli/SKILL.md` — find items by name, description, workspace name, or type
  - Primary CLI tool: `az rest` via `POST /v1/catalog/search`
  - Token audience: `https://api.fabric.microsoft.com/.default`

### OneLake Catalog Governance
- **Governance posture**: Tenant-admin and data-owner audits plus guarded remediation for domains, workspace assignment, capacity, sensitivity labels, tags, descriptions, refresh, and item identity
  - Docs: https://learn.microsoft.com/en-us/fabric/governance/onelake-catalog-govern
  - Skill: `skills/onelake-catalog-govern-cli/SKILL.md` — select admin-audit, admin-remediate, dataowner-audit, or dataowner-remediate by API surface and intent
  - Primary CLI tool: `az rest` against Fabric Admin/Core and Power BI REST APIs

### Business Intelligence
- **Semantic Models**: DAX, XMLA, Power BI integration, TMDL
  - Docs: https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand
  - Authoring skill: `skills/semantic-model-authoring/SKILL.md` — semantic model authoring
  - Consumption skill: `skills/fabriciq/SKILL.md` — raw DAX queries against semantic models via MCP ExecuteQuery tool
  - FabricIQ skill: `skills/fabriciq/SKILL.md` — multi-step Power BI data analysis (discover, inspect, resolve, generate, execute)
  - ⚠️ **MANDATORY**: Before calling any FabricIQ MCP tool, read `skills/fabriciq/SKILL.md` in full (see [`agents/FabricIQ.agent.md` § Pre-Flight](../agents/FabricIQ.agent.md#pre-flight--mandatory-skill-reading)).
- **Power BI Reports**: PBIR/PBIP report projects, visual design, Desktop validation, and Fabric report item management
  - Docs: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
  - Skill docs: https://aka.ms/Report_Authoring_skill_LearnDocs
  - Planning skill: `skills/powerbi-report-planning/SKILL.md` — requirements, page plan, approval gate
  - Design skill: `skills/powerbi-report-design/SKILL.md` — archetype routing, layout, theme, accessibility
  - Authoring skill: `skills/powerbi-report-authoring/SKILL.md` — PBIR/PBIP file mechanics, Desktop reload/screenshot
  - Management skill: `skills/powerbi-report-management/SKILL.md` — Fabric report item CRUD via `az rest`

### Data Science
- **Data Agents**: Conversational AI over Fabric data sources
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
- **Data Agent Evaluation**: Testing and validating Data Agent accuracy
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk

### Variable Library (CI/CD)
- **Variable Library**: parameterize workspaces across environments (dev/test/prod) via named variables and value sets
  - Authoring skill: `skills/variable-library-cli/SKILL.md` — definitions, value sets, active value set item state, and VL-side consumer wiring via the item-definition REST API
  - Docs: https://learn.microsoft.com/en-us/fabric/cicd/variable-library/variable-library-overview

### Git Integration (ALM / CI-CD)
- **Git Integration**: Bind a workspace to source control (Azure DevOps / GitHub) and sync items
  - Operations skill: `skills/git-integration-operations-cli/SKILL.md` — drive the Git lifecycle from CLI (connect, commit, update/pull, sync status, resolve conflicts, disconnect, service-principal sync) via `fab api` with `az rest` fallback

### Cost Estimation & Migration Planning
- **Fabric Cost Estimation**: E2E skill for capacity sizing, billing mode strategy, workload CU equivalence
  - Skill: `skills/e2e-fabric-cost-estimation/SKILL.md` — estimate Fabric capacity costs, SKU sizing, RI analysis
  - Uses Azure Retail Prices API (public) and Cost Management API (auth required)

## Best Practices

### Must
- Use Delta Lake format for Lakehouse tables
- Include time filters in KQL queries (`where Timestamp > ago(...)`)
- Use `has` over `contains` for indexed string search in KQL
- Use idempotent KQL commands (`.create-merge table`, `.create-or-alter function`)
- Handle credentials via environment variables or Key Vault
- Use parameterized notebooks and pipelines

### Prefer
- Medallion architecture (Bronze/Silver/Gold) for data organization
- REST APIs for programmatic management
- Incremental processing over full refreshes
- mssparkutils for Fabric-specific notebook operations

### Avoid
- Hardcoded workspace/item IDs
- SELECT * without LIMIT on large tables
- Long-running transactions in Warehouse
- Unbounded streaming queries
