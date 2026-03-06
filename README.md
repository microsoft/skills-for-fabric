# Agent Skills for Microsoft Fabric

## AI‑native skills to build, explore, and operate Microsoft Fabric

**Agent Skills for Microsoft Fabric** is the AI skills layer that connects modern AI coding assistants directly to **Microsoft Fabric**.

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

## Authoring Skills (Build & Automate)

These skills perform **write‑capable, authenticated operations** in Microsoft Fabric. Designed for developers, data engineers, and CI/CD automation.

| Area | What the Skill Enables |
|-----|-------------------------|
| **Spark** | Data engineering pipelines, medallion architectures, ETL / ELT workflows |
| **SQL / Warehouses** | Create and manage Warehouses, SQL Endpoints, Mirrored Databases |
| **Eventhouse (KQL)** | Create and manage KQL databases, ingestion, tables, policies, materialized views |
| **Power BI** | Create and deploy semantic models, manage metadata and refresh |
| **Automation** | Scripted Fabric operations for CI/CD and environment setup |

---

## Consumption Skills (Query & Explore)

These skills are **read‑only**, require **no SDKs or drivers**, and are optimized for analysts, demos, and exploration.

| Area | What the Skill Enables |
|-----|-------------------------|
| **Spark** | Query and analyze Lakehouse tables |
| **SQL / Warehouses** | Query Warehouses and Lakehouse SQL Endpoints |
| **Eventhouse (KQL)** | Run read‑only KQL queries for real‑time analytics |
| **Power BI** | Run DAX queries and inspect semantic model metadata |

---

## End‑to‑End & Utility Skills

These skills cut across workloads or improve the overall experience.

| Skill | Purpose |
|------|---------|
| **End‑to‑End Medallion Architecture** | Build a Bronze / Silver / Gold lakehouse architecture using Spark, Delta Lake, and Fabric Pipelines |
| **Check Updates** | Compare installed skills with the FabricSkills marketplace, show current version and changelog |


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
