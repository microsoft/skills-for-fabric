# Microsoft Fabric Development Agent

> **Update Check**: At session start, check for skills-for-fabric updates by reading the remote `package.json` version from `https://github.com/microsoft/skills-for-fabric` (via `git fetch origin main --quiet && git show origin/main:package.json` or GitHub API with authentication) and comparing with the local `package.json` version. Show changelog if update available.

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
| Activator | https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction |
| Catalog Search | https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search |
| Semantic Models | https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand |
| Power BI Reports | https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report |
| Data Agents | https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent |
| Data Agent Evaluation | https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk |

## Key Patterns

### Data Architecture
- Use Medallion architecture: Bronze (raw) → Silver (cleaned) → Gold (aggregated)
- Lakehouse for data engineering, Warehouse for SQL analytics
- Delta Lake format for all Lakehouse tables
- For Materialized Lake View SQL authoring and incremental refresh optimization, use `skills/spark-authoring-cli/SKILL.md` and its MLV resource documents.
- For MLV refresh scheduling, job monitoring, and cancellation, use `skills/mlv-operations-cli/SKILL.md`.

### Development
- PySpark with mssparkutils for notebooks
- T-SQL with surface area limitations for Warehouse
- KQL for real-time analytics (always use time filters)
- Power Query M for Dataflows Gen2 transformations (see `dataflows-authoring-cli` and `dataflows-consumption-cli` skills)
- Eventstream for real-time event ingestion (graph-based topology with sources, operators, destinations)
- Activator for Reflex alerts, notifications, and automated actions over Fabric events and data
- DAX for Semantic Model measures
- Semantic model development (see `semantic-model-authoring`)
- Power BI report planning skill: `skills/powerbi-report-planning/SKILL.md` — requirements, page plan, approval gate
- Power BI report design skill: `skills/powerbi-report-design/SKILL.md` — archetype routing, layout, theme, accessibility
- Power BI report authoring skill: `skills/powerbi-report-authoring/SKILL.md` — PBIR/PBIP file mechanics, Desktop reload/screenshot
- Power BI report management skill: `skills/powerbi-report-management/SKILL.md` — Fabric report item CRUD via `az rest`
- Spark operations skill: `skills/spark-operations-cli/SKILL.md` — read-only triage for failed jobs, stuck sessions, performance bottlenecks

### Operations
- REST APIs for programmatic management
- Pipelines for orchestration
- Parameterize everything for reusability
- Warehouse operations skill: `skills/sqldw-operations-cli/SKILL.md` — performance diagnostics, slow queries, query insights

### Activator / Reflex
- Authoring skill: `skills/activator-authoring-cli/SKILL.md` — create Activator items, sources, rules, conditions, and actions
- Consumption skill: `skills/activator-consumption-cli/SKILL.md` — inspect Activator definitions, rules, sources, and actions

### Power BI / FabricIQ
- Consumption skill: `skills/semantic-model-consumption/SKILL.md` — raw DAX queries against semantic models via MCP ExecuteQuery tool
- FabricIQ skill: `skills/fabriciq/SKILL.md` — multi-step Power BI data analysis (discover, inspect, resolve, generate, execute)
- ⚠️ **MANDATORY**: Before calling any FabricIQ MCP tool, read `skills/fabriciq/SKILL.md` in full (see [`agents/FabricIQ.agent.md` § Pre-Flight](../agents/FabricIQ.agent.md#pre-flight--mandatory-skill-reading)).

### Fabric IQ / Ontology (preview)
- Authoring skill: `skills/fabriciq-ontology-authoring-cli/SKILL.md` — define entity types, properties (incl. timeseries), relationship types, and bind them to lakehouse/Eventhouse tables via the item-definition REST API
- Consumption skill: `skills/fabriciq-ontology-consumption-cli/SKILL.md` — read ontology items for agent grounding context and route ontology-backed queries to the matching per-datasource consumption skill

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
