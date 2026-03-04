# Skills for Microsoft Fabric

AI coding assistant skills to build, explore, and operate **Microsoft Fabric** using natural language from modern AI coding tools.

Skills for Microsoft Fabric provides AI‑native building blocks that let developers and data consumers interact with Fabric workloads across **Spark, SQL, Power BI, and Eventhouse** from tools like **GitHub Copilot CLI**, **VS Code Copilot**, **Claude Code**, and **Cursor**.

This repository is optimized for:
- Product announcements
- Demo and keynote videos
- Tutorials and hands‑on labs
- Real production‑ready workflows

---

## Why Skills for Microsoft Fabric

Microsoft Fabric brings together data engineering, analytics, and BI—but real workflows span multiple engines and tools.

Skills for Microsoft Fabric closes that gap by enabling:
- Natural‑language interaction with Fabric workloads
- Cross‑engine workflows (Spark, SQL, KQL, Power BI)
- Zero‑setup exploration for consumers (no SDKs or drivers)
- Automation‑ready authoring for developers and CI/CD
- A consistent AI experience across popular coding assistants

Build faster. Explore deeper. Operate Fabric safely and predictably.

---

## What You Can Do

### Analyze Data
- Query Lakehouse tables using Spark or SQL
- Explore Fabric data conversationally
- Generate insights, summaries, and analytics‑ready outputs

### Build Real Workloads
- Create and manage Lakehouses and Warehouses
- Author Spark‑based data engineering workflows
- Execute KQL management and query operations on Eventhouse
- Create and manage Power BI semantic models

### Demo‑Ready Scenarios

Perfect for demos, tutorials, and announcement videos:

- **NYC Taxi Medallion Project**  
  Download a public dataset, build Bronze/Silver layers in Fabric, and expose SQL views for analytics and BI.

- **Analytics Report Generation**  
  Analyze Fabric data and generate a PDF analytics report.

- **Dashboard Creation**  
  Generate interactive dashboards connected directly to Fabric data.

- **Workspace Exploration**  
  Inspect workspaces, items, schemas, and metadata conversationally.

---

## Installation

### Recommended: GitHub Copilot CLI

Connect to the Fabric Skills marketplace and install the full skills bundle:

```bash
plugin marketplace add gim/FabricSkills
plugin install fabric
```

### Install by Persona

- **Developers (Authoring, Automation, CI/CD)**
- **Consumers (Querying, Exploration, Monitoring)**

Filter skills by engine or workload:

```bash
plugin install fabric --filter spark
plugin install fabric --filter powerbi
plugin install fabric --filter eventhouse
```

---

## Authentication

All Fabric operations use **Azure Active Directory authentication**.

- No secrets required
- No embedded credentials
- Access tokens scoped to:

```
https://api.fabric.microsoft.com
```

---

## Skill Categories

### Developer Skills (Authoring)
For engineers building and managing Fabric workloads:

- **spark‑authoring** – Build Spark data engineering workflows
- **sqldw‑authoring** – Manage Warehouses, SQL Endpoints, Mirrored Databases
- **eventhouse‑authoring** – Manage KQL databases and Eventhouse resources
- **powerbi‑authoring** – Create and manage Power BI semantic models
- Automation scripting and CI/CD support

### Consumer Skills (Consumption)
For interactive exploration without drivers or SDKs:

- **spark‑consumption** – Query and analyze Lakehouse tables
- **sql‑consumption** – Query Warehouses and SQL Endpoints
- **eventhouse‑consumption** – Run read‑only KQL queries
- **powerbi‑consumption** – Run DAX and inspect model metadata

---

## Tool Compatibility

Skills for Microsoft Fabric works across multiple AI coding tools:

- **GitHub Copilot CLI** (plugin‑based, automatic updates)
- **VS Code Copilot**
- **Claude Code** (see `CLAUDE.md`)
- **Cursor** (see `.cursorrules`)
- **OpenAI Codex** (see `AGENTS.md`)

Install scripts are included to automate setup.

---

## Agents (Preview)

This repository includes higher‑level agent definitions that orchestrate multiple skills end‑to‑end:

### FabricDataEngineer
- Medallion architecture workflows
- ETL / ELT pipelines
- Data quality and transformation workflows

### FabricAdmin
- Capacity planning
- Governance and security
- Cost optimization
- Observability and operations

Agents compose multiple skills to execute complete Fabric workflows.

---

## Security & Responsible AI

Skills for Microsoft Fabric is built with security and Responsible AI principles:

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

- Follow guidelines in `CONTRIBUTING.md`
- Pull requests must pass security and quality checks
- Adhere to Responsible AI requirements
- Report security issues via `SECURITY.md`

---

## Learn More

- Microsoft Fabric Documentation
- Fabric REST APIs

---

## License

MIT License

---

**Skills for Microsoft Fabric** — AI‑native building blocks for the modern Fabric developer.
