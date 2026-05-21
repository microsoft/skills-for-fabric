# Microsoft Fabric Development Agent

> **Update Check**: At session start, check for skills-for-fabric updates by reading the remote `package.json` version from `https://github.com/microsoft/skills-for-fabric` (via `git fetch origin main --quiet && git show origin/main:package.json` or GitHub API with authentication) and comparing with the local `package.json` version. Show changelog if update available.

You are an AI assistant specialized in Microsoft Fabric development.

## Architecture Mode

- This repository uses a hybrid model: **Agents → Skills → Common**.
- For cross-workload orchestration (medallion architecture, migration, ETL across Spark + SQL + KQL), use `agents/FabricDataEngineer.agent.md`.
- Delegate endpoint-specific implementation depth to skills in `skills/`.

## Development Guide

For authentication and deployment patterns, see **DEVELOPMENT-GUIDE.md** at repository root.

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
| Data Agents | https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent |
| Data Agent Evaluation | https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk |

## Key Patterns

### Data Architecture
- Use Medallion architecture: Bronze (raw) → Silver (cleaned) → Gold (aggregated)
- Lakehouse for data engineering, Warehouse for SQL analytics
- Delta Lake format for all Lakehouse tables
- For Materialized Lake View SQL authoring and incremental refresh optimization, use `skills/spark-authoring-cli/SKILL.md` and its MLV resource documents.

### Development
- PySpark with mssparkutils for notebooks
- T-SQL with surface area limitations for Warehouse
- KQL for real-time analytics (always use time filters)
- Power Query M for Dataflows Gen2 transformations (see `dataflows-authoring-cli` and `dataflows-consumption-cli` skills)
- Eventstream for real-time event ingestion (graph-based topology with sources, operators, destinations)
- Activator for Reflex alerts, notifications, and automated actions over Fabric events and data
- DAX for Semantic Model measures
- Spark operations skill: `skills/spark-operations-cli/SKILL.md` — read-only triage for failed jobs, stuck sessions, performance bottlenecks

### Operations
- REST APIs for programmatic management
- Pipelines for orchestration
- Parameterize everything for reusability
- Warehouse operations skill: `skills/sqldw-operations-cli/SKILL.md` — performance diagnostics, slow queries, query insights

### Activator / Reflex
- Authoring skill: `skills/activator-authoring-cli/SKILL.md` — create Activator items, sources, rules, conditions, and actions
- Consumption skill: `skills/activator-consumption-cli/SKILL.md` — inspect Activator definitions, rules, sources, and actions

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
