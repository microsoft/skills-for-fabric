# Skills for Fabric

### Agent Skills for Microsoft Fabric

**AI agent skills for Microsoft Fabric developers, data engineers, admins, and consumers.**

Optimized for **GitHub Copilot CLI**, with cross‑tool compatibility for **VS Code Copilot, Claude Code, Cursor, Codex/Jules, and Windsurf**.

[📘 Documentation](https://learn.microsoft.com/fabric) • [🔐 Security](SECURITY.md) • [🤝 Contributing](CONTRIBUTING.md) • [🐞 Report a Bug](https://github.com/microsoft/skills-for-fabric/issues/new?template=bug_report.md)

---

## Why Skills for Fabric?

Skills for Fabric bridges the gap between AI coding assistants and Microsoft Fabric's enterprise data platform. We provide **first-party, production-ready agent skills** that enable AI tools to safely author, query, and operate complex Fabric workloads—from Spark pipelines to semantic models—while maintaining enterprise security and governance standards.

---

## ✨ What are Skills for Fabric?

**Skills for Fabric** (also referred to as **Agent Skills**) provide a standardized, secure, and extensible way for AI coding agents to **author, query, operate, and govern Microsoft Fabric workloads**.

These skills allow AI tools to act as **Fabric‑aware agents**—capable of understanding workspaces, Lakehouses, Warehouses, Eventhouses, semantic models, and capacity settings—while respecting Microsoft security, governance, and Responsible AI requirements.

The project follows the same design principles used across other **Microsoft‑hosted skill repositories**:

- ✅ Explicit authentication and authorization
- ✅ Clear separation of instructions vs user content
- ✅ No arbitrary code execution
- ✅ Enterprise‑grade security and compliance
- ✅ Tool‑agnostic agent compatibility

---

## 🆚 Skills vs Prompt‑Only Approaches

Unlike prompt‑only workflows, **Skills for Fabric**:

- Use authenticated Microsoft Fabric APIs
- Enforce safe, validated operations
- Understand Fabric resource types and boundaries
- Prevent prompt injection and unsafe execution
- Produce deterministic, auditable actions

This makes agent interactions reliable, repeatable, and enterprise‑ready.

---

## 🧱 Skills vs Agents

| Concept | Description |
|---|---|
| Skill | A single, focused capability (for example: run Spark, query SQL, manage KQL) |
| Agent | An orchestrator that combines multiple skills to achieve a goal |

Agents are built *on top of* skills.

---

## 🧠 Supported Personas & Scenarios

Skills are organized by **persona** and **intent**, enabling both focused and end‑to‑end workflows.

### 👩‍💻 Developers & Data Engineers (Authoring)

- Create and manage Fabric resources
- Build Spark ETL / ELT pipelines
- Author SQL objects and KQL assets
- Automate deployments and CI/CD flows

### 📊 Consumers & Analysts (Consumption)

- Query Lakehouse tables interactively
- Run SQL, DAX, and KQL without drivers
- Explore metadata and monitor usage

### 🛡️ Admins & Platform Owners

- Capacity planning and optimization
- Governance and security validation
- Cost, performance, and usage analysis

### 🤖 Cross‑Workload Agents

- Medallion architectures (Bronze → Silver → Gold)
- Migration and modernization
- Data quality checks and observability

---

## 🚀 Example Use Cases

| Scenario | What the Agent Does |
|---|---|
| Analytics PDF Report | Analyzes Fabric data and generates a production‑ready PDF report |
| Document My Workspace | Inspects Fabric workspaces and produces structured documentation |
| NYC Taxi Medallion Project | Ingests public data, builds Spark pipelines, and exposes SQL views |
| Dashboard App | Creates an interactive dashboard connected to Fabric data |

---

## 📦 Installation

### GitHub Copilot CLI (Recommended)

Always start by connecting to the **Skills for Fabric** marketplace

```bash
/plugin marketplace add microsoft/skills-for-fabric
```

#### Install all skills

```bash
/plugin install skills-for-fabric@fabric-collection
```

#### Install by persona

```bash
# Authoring (developers, automation, CI/CD)
/plugin install fabric-authoring@fabric-collection

# Consumption (interactive analytics)
/plugin install fabric-consumption@fabric-collection
```

#### Filter by engine or endpoint

```bash
/plugin install skills-for-fabric@fabric-collection --filter "spark-*"
/plugin install skills-for-fabric@fabric-collection --filter "sqldw-*"
/plugin install skills-for-fabric@fabric-collection --filter "eventhouse-*"
```

---

### Manual Installation

```bash
git clone https://github.com/microsoft/skills-for-fabric.git
cd skills-for-fabric
```

```bash
# Windows
.\\install.ps1

# macOS / Linux
./install.sh
```

---

## 🔐 Authentication

All Fabric operations require **Azure AD authentication**:

```bash
az login
az account get-access-token --resource https://api.fabric.microsoft.com
```

No secrets or tokens are stored by the skills.

---

## 🧩 Skill Catalog

### ✍️ Authoring Skills

| Skill | Purpose |
|---|---|
| sqldw-authoring-cli | Author Warehouses, Lakehouse SQL Endpoints, Mirrored Databases |
| spark-authoring-cli | Build Fabric Spark and Data Engineering workflows |
| eventhouse-authoring-cli | Manage KQL tables, ingestion, policies, and functions |
| powerbi-authoring-cli | Create and deploy Power BI semantic models |

---

### 📈 Consumption Skills

| Skill | Description |
|---|---|
| sqldw-consumption-cli | Query Warehouses and SQL Endpoints |
| spark-consumption-cli | Analyze Lakehouse tables interactively |
| eventhouse-consumption-cli | Run read‑only KQL queries |
| powerbi-consumption-cli | Query semantic models and execute DAX |

---

### 🧰 Utility Skills

| Skill | Description |
|---|---|
| check-updates | Automatically checks for marketplace updates |

```bash
/skills-for-fabric:check-updates
```

---

## 🤖 Agents

Agents orchestrate **multiple skills across workloads**.

| Agent | Purpose |
|---|---|
| FabricDataEngineer | Medallion architectures, ETL/ELT, migration, data quality |
| FabricAdmin | Capacity, governance, security, cost, observability |

Agent definitions live in `agents/`.

---

## 🔄 Automatic Updates

At the start of each session, the first invoked skill:

- Checks GitHub releases
- Compares against the installed version
- Displays changelog and update instructions

This check runs **once per session** and is **non‑blocking**.

---

## 🧩 Cross‑Tool Compatibility

| Tool | Setup |
|---|---|
| GitHub Copilot CLI | Automatic via plugin system |
| VS Code Copilot | `.github/skills/` |
| Claude Code | `compatibility/CLAUDE.md` |
| Cursor | `compatibility/.cursorrules` |
| Codex / Jules | `compatibility/AGENTS.md` |
| Windsurf | `compatibility/.windsurfrules` |

Install scripts configure this automatically.

---

## 🔗 MCP Server Registration

```bash
# Windows
.\\mcp-setup\\register-fabric-mcp.ps1

# macOS / Linux
./mcp-setup/register-fabric-mcp.sh
```

See `mcp-setup/README.md` for details.

---

## 🔒 Security & Responsible AI

### Security

- ✅ Secret scanning (TruffleHog, Gitleaks)
- ✅ Prompt‑injection protection
- ✅ No arbitrary code execution

Report vulnerabilities via **SECURITY.md**.

### Responsible AI

- Clear instruction / data separation
- Input validation and sanitization
- Secret redaction in outputs
- Tested against **OWASP LLM Top 10**

---

## 📊 Data Handling & Privacy

- Data processed locally or via authenticated Fabric APIs
- No data sent to third‑party services
- Azure AD + GitHub Secrets for credentials
- Audit logging for executions

---

## 🐞 Reporting Issues

Please file structured issues via GitHub Issues.

Do not include secrets or tokens.

---

## 🤝 Contributing

We welcome community contributions.

All pull requests must:
- ✅ Pass tests
- ✅ Pass security scans
- ✅ Have CODEOWNER approval
- ✅ Contain no secrets

---

## 📚 Repository Structure

```text
skills-for-fabric/
├── agents/
├── skills/
├── compatibility/
├── docs/
│   ├── compliance/
│   └── assets/
├── mcp-setup/
├── install.ps1
├── install.sh
└── README.md
```

---

## 📜 License

This project is licensed under the **MIT License**.

---

**Built with ❤️ for the Microsoft Fabric community**
