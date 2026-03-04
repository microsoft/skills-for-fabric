# Skills for Microsoft Fabric

## AI‑native skills to build, explore, and operate Microsoft Fabric

**Skills for Microsoft Fabric** is the AI skills layer that connects modern AI coding assistants directly to **Microsoft Fabric**.

From a single natural‑language interface, developers and data consumers can build Spark pipelines, query Warehouses, run KQL on Eventhouse, and inspect Power BI semantic models — securely, predictably, and in real time.

Built for Github Copilot, Visual Studio Code, Claude Code and other Agentic CLI and Extensions. Skills for Microsoft Fabric delivers one consistent AI experience across Fabric engines.

> One AI experience. Multiple engines. Enterprise‑ready.

---

## Why Skills for Microsoft Fabric

Modern analytics workflows don’t live in a single engine:

- Spark for data engineering
- SQL for warehousing and analytics
- KQL for real‑time and operational data
- Power BI for semantic models and insights

Microsoft Fabric unifies these engines. **Skills for Microsoft Fabric makes them conversational.**

With Skills, AI assistants translate intent into secure Fabric operations using Azure AD identity, built‑in guardrails, and deterministic execution.

---

## What You Can Do

### Analyze Data
- Query Lakehouse tables using Spark or SQL
- Explore Fabric data conversationally
- Generate summaries, insights, and analytics‑ready outputs

### Build Real Workloads
- Create and manage Lakehouses and Warehouses
- Author Spark ETL / ELT workflows
- Execute KQL management and query operations on Eventhouse
- Create and manage Power BI semantic models

---

## Demo‑Ready Scenarios

Designed to land clearly in a live keynote or recorded demo:

### NYC Taxi Medallion Project
- Download a public dataset
- Build Bronze and Silver layers in Fabric
- Expose SQL views for analytics and BI

### Analytics Report Generation
- Analyze Fabric data
- Generate a polished PDF analytics report

### Dashboard Creation
- Generate interactive dashboards
- Connect directly to Fabric data

### Workspace Exploration
- Inspect workspaces, items, schemas, and metadata
- Fully conversational, no setup

---

## Skills at a Glance

### Developer Skills — Authoring
For engineers building and operating Fabric workloads:

- **Spark** – Data engineering pipelines, medallion architectures
- **SQL / Warehouses** – Warehouses, SQL Endpoints, Mirrored Databases
- **Eventhouse (KQL)** – Databases, ingestion, tables, policies
- **Power BI** – Semantic models, metadata, deployments
- **Automation** – CI/CD, scripted Fabric operations

### Consumer Skills — Consumption
For analysts, demo users, and data consumers:

| Engine | What You Can Do |
|------|----------------|
| Spark | Query and analyze Lakehouse tables |
| SQL | Query Warehouses and SQL Endpoints |
| Eventhouse | Run read‑only KQL queries |
| Power BI | Run DAX, inspect model metadata |

---

## Supported AI Tools

One skills layer. Multiple AI assistants.

- **GitHub Copilot CLI**
- **VS Code Copilot**
- **Claude Code**
- **Cursor**
- **OpenAI Codex**

Install once. Use everywhere.

---

## Installation

### Recommended: GitHub Copilot CLI

```bash
plugin marketplace add gim/FabricSkills
plugin install fabric
```

Install by persona or engine:

```bash
plugin install fabric --filter spark
plugin install fabric --filter powerbi
plugin install fabric --filter eventhouse
```

---

## Authentication

All Fabric operations use **Azure Active Directory authentication**.

- No secrets
- No embedded credentials
- Tokens scoped to:

```
https://api.fabric.microsoft.com
```

---

## Agents (Preview)

Higher‑level agents orchestrate multiple skills end‑to‑end:

### FabricDataEngineer
- Medallion architectures
- ETL / ELT pipelines
- Data quality workflows

### FabricAdmin
- Capacity planning
- Governance and security
- Cost optimization
- Observability

Agents compose skills to execute complete Fabric workflows.

---

## Security & Responsible AI

Built with enterprise security and Responsible AI principles:

- No arbitrary code execution
- Clear separation of system instructions and user input
- Secret redaction in outputs
- Azure AD–based authentication
- Prompt‑injection resistance
- No data sent to third parties

See `SECURITY.md` for vulnerability reporting.

---

## Contributing

Contributions are welcome.

- Follow `CONTRIBUTING.md`
- PRs must pass security and quality checks
- Adhere to Responsible AI requirements

---

## License

MIT License

---

**Skills for Microsoft Fabric**  
AI‑native building blocks for the modern Fabric developer.
