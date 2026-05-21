# Microsoft Fabric Skills

Microsoft Fabric Skills are reusable AI assistant instructions for working with Microsoft Fabric. They help GitHub Copilot CLI and compatible AI coding tools understand Fabric workloads, APIs, query patterns, and operational best practices.

## Install with GitHub Copilot CLI

Add the public marketplace:

```bash
/plugin marketplace add microsoft/skills-for-fabric
```

Install the full bundle:

```bash
/plugin install fabric-skills@fabric-collection
```

Or install a focused bundle:

```bash
# Authoring: APIs, automation, notebooks, schemas, ingestion, and deployment
/plugin install fabric-authoring@fabric-collection

# Consumption: interactive querying, discovery, exploration, and monitoring
/plugin install fabric-consumption@fabric-collection

# Operations: diagnostics and performance investigation
/plugin install fabric-operations@fabric-collection
```

You can also filter the full bundle by workload:

```bash
/plugin install fabric-skills@fabric-collection --filter "sqldw-*"
/plugin install fabric-skills@fabric-collection --filter "spark-*"
/plugin install fabric-skills@fabric-collection --filter "eventhouse-*"
```

## What is included

| Bundle | Use it for |
|--------|------------|
| `fabric-skills` | Complete Microsoft Fabric skill bundle, including authoring, consumption, operations, migration, and end-to-end architecture skills. |
| `fabric-authoring` | Creating and managing Fabric items through REST APIs, CLI automation, notebooks, T-SQL, KQL, Dataflows Gen2, Eventstreams, and semantic models. |
| `fabric-consumption` | Read-only exploration and query workflows across Warehouses, Lakehouses, Power BI semantic models, Eventhouse/KQL databases, Eventstreams, Dataflows Gen2, and catalog search. |
| `fabric-operations` | Performance and health diagnostics, including warehouse query insights and slow-query investigation. |

The full bundle includes skills for SQL data warehouse, Spark and Lakehouse (including Materialized Lake Views), Power BI semantic models, Eventhouse and KQL, Eventstreams, Dataflows Gen2, catalog search, migration scenarios, and medallion architecture workflows.

See [CHANGELOG.md](CHANGELOG.md) for public release notes.

## Try an example prompt

- [Analytics PDF report](prompt_examples/NYC_AnalyzeExistingDataCreatePDF.txt)
- [Document my workspace](prompt_examples/DocumentMyWorkspace.txt)
- [NYC Taxi medallion architecture](prompt_examples/NYCTaxi_MedallionArchitecture.txt)
- [Dashboard app](prompt_examples/DashboardApp.txt)

After installing a bundle, open Copilot CLI in a project folder and ask for the Fabric task you want to perform, for example:

```text
Use Microsoft Fabric skills to design a medallion architecture for NYC taxi data.
```

```text
Use Microsoft Fabric skills to design a Bronze/Silver/Gold flow with Materialized Lake Views.
```

```text
Review this CREATE MATERIALIZED LAKE VIEW statement for incremental refresh blockers.
```

## Authentication

Most Fabric operations require Azure authentication. Start with:

```bash
az login
az account get-access-token --resource https://api.fabric.microsoft.com
```

SQL, Spark, Power BI, and KQL workflows may require workload-specific endpoints or token audiences. The installed skills provide the detailed commands and API patterns for each workload.

## MCP servers

Skills provide guidance and patterns. MCP servers provide live tool access to data sources and APIs. Some bundles include MCP configuration where supported, and you can register additional Fabric MCP servers if your environment provides them.

See [MCP setup](mcp-setup/README.md) and the [MCP servers guide](docs/mcp-servers-guide.md).

## Other AI coding tools

GitHub Copilot CLI plugin installation is the recommended path. This repository also includes root-level configuration files for compatible AI coding tools — [CLAUDE.md](CLAUDE.md) for Claude Code, [.cursorrules](.cursorrules) for Cursor, [.windsurfrules](.windsurfrules) for Windsurf, and [AGENTS.md](AGENTS.md) for Codex / Jules / OpenCode. They are picked up automatically when the repo is cloned.

## Issues and security

Report product issues in the [GitHub issue tracker](https://github.com/microsoft/skills-for-fabric/issues).

For security vulnerabilities, do not open a public issue. See [SECURITY.md](SECURITY.md) for the private reporting path.

## License

This project is licensed under the [MIT License](LICENSE).
