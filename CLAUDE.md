# Microsoft Fabric Development Instructions

> **Update Check**: At session start, check for skills-for-fabric updates by reading the remote `package.json` version from `https://github.com/microsoft/skills-for-fabric` (via `git fetch origin main --quiet && git show origin/main:package.json` or GitHub API with authentication) and comparing with the local `package.json` version. Show changelog if update available.

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
  - Authoring skill: `skills/spark-authoring-cli/SKILL.md` — notebook authoring, Lakehouse authoring, Materialized Lake Views, and refresh-friendly Spark patterns.
- **Notebooks**: PySpark notebooks with mssparkutils
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- **Spark Jobs**: Production Spark workloads
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/spark-job-definition
  - Operations skill: `skills/spark-operations-cli/SKILL.md` — read-only triage for failed jobs, stuck sessions, performance bottlenecks

### Data Warehouse
- **Warehouse**: T-SQL data warehouse
  - Docs: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-warehousing
  - Note: Limited T-SQL surface area - check supported features
  - Authoring skill: `skills/sqldw-authoring-cli/SKILL.md` — DDL, DML, ingestion, schema changes
  - Consumption skill: `skills/sqldw-consumption-cli/SKILL.md` — read-only T-SQL queries
  - Operations skill: `skills/sqldw-operations-cli/SKILL.md` — performance diagnostics, slow queries, query insights

### Data Integration
- **Pipelines**: Orchestration and data movement
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/data-factory-overview
- **Dataflows Gen2**: Low-code transformations with Power Query
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-overview
  - Authoring skill: `skills/dataflows-authoring-cli/SKILL.md` — dataflow lifecycle management, Power Query M mashup authoring
  - Consumption skill: `skills/dataflows-consumption-cli/SKILL.md` — read-only dataflow exploration, monitoring, status queries
  - Primary CLI tool: `az rest` via Fabric REST API

### Real-Time Intelligence
- **Eventstreams**: Real-time data ingestion
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview
  - Authoring skill: `skills/eventstream-authoring-cli/SKILL.md` — create, configure, deploy Eventstream topologies (sources, operators, destinations)
  - Consumption skill: `skills/eventstream-consumption-cli/SKILL.md` — list, inspect, monitor Eventstreams
  - Primary CLI tool: `az rest` via Fabric REST API
- **Activator**: Alerts, notifications, and automated actions over Fabric data/events
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction
  - Authoring skill: `skills/activator-authoring-cli/SKILL.md` — create Activator items, sources, rules, conditions, and actions
  - Consumption skill: `skills/activator-consumption-cli/SKILL.md` — inspect Activator definitions, rules, sources, and actions
  - Primary CLI tool: `az rest` via Fabric REST API
- **KQL Database / Eventhouse**: Time-series queries with Kusto
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database
  - Authoring skill: `skills/eventhouse-authoring-cli/SKILL.md` — table management, ingestion, policies, materialized views
  - Consumption skill: `skills/eventhouse-consumption-cli/SKILL.md` — read-only KQL queries, schema discovery
  - Primary CLI tool: `az rest` via Kusto REST API (`/v1/rest/query` and `/v1/rest/mgmt`)
  - Token audience: `https://kusto.kusto.windows.net/.default`

### OneLake Catalog Search
- **Catalog Search API**: Cross-workspace item discovery
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search
  - Consumption skill: `skills/search-consumption-cli/SKILL.md` — find items by name, description, workspace name, or type
  - Primary CLI tool: `az rest` via `POST /v1/catalog/search`
  - Token audience: `https://api.fabric.microsoft.com/.default`

### Business Intelligence
- **Semantic Models**: DAX, XMLA, Power BI integration, TMDL
  - Docs: https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand
  - Authoring skill: `skills/semantic-model-authoring/SKILL.md` — semantic model authoring
  - Consumption skill: `skills/semantic-model-consumption/SKILL.md` — raw DAX queries against semantic models via MCP ExecuteQuery tool
  - FabricIQ skill: `skills/fabriciq/SKILL.md` — multi-step Power BI data analysis (discover, inspect, resolve, generate, execute)
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
