# Microsoft Fabric Skills

> **Preview branch:** this is not a release. Use [PREVIEW.md](PREVIEW.md) to test
> Azure CLI authentication with the separate preview marketplace.

Microsoft Fabric Skills are reusable AI assistant instructions for working with Microsoft Fabric. They help GitHub Copilot CLI and compatible AI coding tools understand Fabric workloads, APIs, query patterns, and operational best practices.

## Install with GitHub Copilot CLI

Add the public marketplace:

```bash
/plugin marketplace add microsoft/skills-for-fabric
```

Install the main Fabric bundle. Power BI report authoring is packaged separately:

```bash
/plugin install fabric-skills@fabric-collection
```

Or install the Power BI authoring bundle:

```bash
# Power BI authoring: semantic models, Power BI report skills, and PBIP workflows
/plugin install powerbi-authoring@fabric-collection
```

Copilot CLI installs plugins as complete bundles. To limit installed skills, choose a focused bundle instead of filtering the full bundle.

> The persona bundles `fabric-authoring`, `fabric-consumption` and `fabric-operations` are retired. Every skill they carried ships in `fabric-skills`. The three ids still resolve as deprecated aliases of `fabric-skills`, so an existing install keeps working through `/plugin update`; new installs should use `fabric-skills`.

### Update installed plugins

Update one installed bundle:

```bash
/plugin update fabric-skills@fabric-collection
```

Replace `fabric-skills` with the focused bundle name to update that bundle. From a terminal, update every installed plugin with:

```bash
copilot plugin update --all
```

### Automatic update checking

Updates are handled by the agent host, not by a skill in this repository.

**GitHub Copilot CLI** -- opt in once by adding `autoUpdate` to the
`fabric-collection` entry in your own user settings
(`~/.copilot/settings.json`, or `%USERPROFILE%\.copilot\settings.json` on
Windows):

```json
{
  "extraKnownMarketplaces": {
    "fabric-collection": {
      "source": { "source": "github", "repo": "microsoft/skills-for-fabric" },
      "autoUpdate": true
    }
  }
}
```

Copilot CLI then refreshes the bundle at the start of every session in a trusted
working directory. This opt-in is honored only from your personal user settings
-- a repository or managed (MDM) setting cannot enable or redirect auto-update
for a marketplace. Auto-update is also skipped by default in CI. See the
[Copilot CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference).

**Claude Code** -- `fabric-collection` is a third-party marketplace, so enable
auto-update once: run `/plugin`, open **Marketplaces**, select
`fabric-collection`, and choose **Enable auto-update**. Administrators can
instead set `"autoUpdate": true` on its `extraKnownMarketplaces` entry in
managed settings.

**Cursor, Windsurf, and other hosts** -- re-run the host's plugin or marketplace
update command, or `git pull` a manual clone.

Every release bumps the `version` field in each plugin manifest, which lets
Copilot CLI and Claude Code detect a new release after auto-update is enabled.

## What is included

| Bundle | Use it for |
|--------|------------|
| `fabric-skills` | Complete Microsoft Fabric skill bundle, including authoring, consumption, operations, migration, and end-to-end architecture skills. |
| `powerbi-authoring` | Authoring Power BI semantic models, reports, and PBIP workflows, including Power BI report planning, design, authoring, and management. |

The full bundle includes skills for SQL data warehouse, Spark and Lakehouse, Power BI semantic models, Eventhouse and KQL, Eventstreams, Dataflows Gen2, catalog search, migration scenarios, and medallion architecture workflows.

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

## Authentication

Most Fabric operations require Azure authentication. Start with:

```bash
az login
az account get-access-token --resource https://api.fabric.microsoft.com
```

SQL, Spark, Power BI, and KQL workflows may require workload-specific endpoints or token audiences. The installed skills provide the detailed commands and API patterns for each workload.

## MCP servers

Skills provide guidance and patterns. MCP servers provide live tool access to data sources and APIs. Some bundles include MCP configuration where supported, and you can register additional Fabric MCP servers if your environment provides them.

See [MCP setup](mcp-setup/README.md).

Local Claude Code's bundled remote MCPs reuse an existing Azure CLI sign-in.
The setup guide covers Codex configuration and older registrations that override the plugin.

## Other AI coding tools

GitHub Copilot CLI plugin installation is the recommended path. This repository also includes root-level configuration files for compatible AI coding tools — [CLAUDE.md](CLAUDE.md) for Claude Code, [.cursorrules](.cursorrules) for Cursor, [.windsurfrules](.windsurfrules) for Windsurf, and [AGENTS.md](AGENTS.md) for Codex / Jules / OpenCode. They are picked up automatically when the repo is cloned.

Gemini CLI also auto-discovers [GEMINI.md](GEMINI.md) when the repo is cloned.

## Issues and security

Report product issues in the [GitHub issue tracker](https://github.com/microsoft/skills-for-fabric/issues).

For security vulnerabilities, do not open a public issue. See [SECURITY.md](SECURITY.md) for the private reporting path.

## License

This project is licensed under the [MIT License](LICENSE).
