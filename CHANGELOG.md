# Changelog

User-facing changes for the public Microsoft Fabric Skills release.

## Unreleased

### Fixed

- **`powerbi-consumption-cli` now explicitly documents that `ExecuteQuery.artifactId` must be the semantic model GUID, not the friendly model name.** This helps agents recover from invalid-argument failures by resolving the semantic model item before executing DAX queries.

## [0.3.1] - 2026-05-10

### Added

- **`activator-authoring-cli`** — create alerts, notifications, and automated actions on Fabric data and events via Fabric REST API and `az rest` CLI. Covers Activator/Reflex item creation, trigger configuration, action wiring (Teams messages, emails, Fabric item runs), and connections to Eventhouse, Eventstream, Real-Time Hub, and Digital Twin Builder.
- **`activator-consumption-cli`** — read-only inspection of existing Activator alerts, notifications, and automated actions via `az rest`. List alerts in a workspace, inspect alert configuration, decode `ReflexEntities.json` definitions.

### Changed

- **`spark-diagnostics-cli` renamed to `spark-operations-cli`** — aligned with the three-category naming convention (`-authoring-`, `-consumption-`, `-operations-`). Same skill, same diagnostic surface (failed Spark jobs, unhealthy Livy sessions, OOM/shuffle/skew, driver/executor logs, Spark Advisor findings) — only the name has changed. Re-invoke as `spark-operations-cli` going forward.

### Fixed

- **`/plugin update` now works again for users who installed under the legacy `skills-for-fabric@fabric-collection` id.** When the bundle was renamed in 0.3.0 (`skills-for-fabric` → `fabric-skills`), the old plugin id was dropped from `marketplace.json`, which silently broke `/plugin update skills-for-fabric@fabric-collection` for everyone still on the legacy id (`Plugin "skills-for-fabric" not found in marketplace`). The legacy id is restored as a deprecated alias of `fabric-skills@fabric-collection` — running `/plugin update` under either name now pulls the canonical `fabric-skills` payload. To migrate your installed entry to the canonical id (optional, recommended cleanup): `/plugin uninstall skills-for-fabric@fabric-collection` then `/plugin install fabric-skills@fabric-collection`.
- **`check-updates` skill works inside Copilot CLI plugin installs.** The skill assumed a `package.json` and a `.git/` directory at the install root, but the Copilot CLI plugin install layout (`~/.copilot/installed-plugins/fabric-collection/fabric-skills/`) has neither — only `.github/plugin/plugin.json`. Step 1 (read local version), Step 2 (parse repository URL), and Method A (`git fetch origin main`) now read the manifest path that matches the actual install layout. The "Update Available" banner no longer references the `install.ps1` / `install.sh` scripts that were removed from the public release in 0.3.0.

## [0.3.0] - 2026-05-06

### Added

- **Plugin bundles for focused installation**
  - `fabric-skills` - complete bundle for Fabric authoring, consumption, operations, migration, and end-to-end architecture workflows.
  - `fabric-authoring` - developer-oriented skills for REST APIs, CLI automation, notebooks, T-SQL, KQL, Eventstreams, Dataflows Gen2, semantic models, and medallion architecture.
  - `fabric-consumption` - read-only and interactive exploration skills for SQL, Spark/Lakehouse, Power BI semantic models, Eventhouse/KQL, Eventstreams, Dataflows Gen2, and catalog search.
  - `fabric-operations` - diagnostics-focused bundle for warehouse performance investigation.
- **Dataflows Gen2 skills**
  - `dataflows-authoring-cli` for creating, updating, and managing Dataflows Gen2 definitions and Power Query M mashups.
  - `dataflows-consumption-cli` for inspecting, monitoring, and exploring Dataflows Gen2 artifacts.
  - `dataflows-save-as-authoring-cli` for Dataflows Gen1 to Gen2 save-as upgrade workflows, readiness assessment, risk checks, and validation.
- **Real-Time Intelligence skills**
  - `eventhouse-consumption-cli` for read-only KQL queries and schema discovery.
  - `eventhouse-authoring-cli` for KQL table, ingestion, policy, function, and materialized-view management.
  - `eventstream-consumption-cli` for inspecting and monitoring Eventstream topologies.
  - `eventstream-authoring-cli` for creating and deploying Eventstream sources, transformations, and destinations.
- **Search and discovery**
  - `search-consumption-cli` for finding Fabric items across the OneLake catalog by name, description, workspace, and type.
- **Migration skills**
  - `databricks-migration` for Databricks to Fabric migration planning and code mapping.
  - `synapse-migration` for Azure Synapse Analytics to Fabric migration.
  - `hdinsight-migration` for Azure HDInsight to Fabric migration.
- **Power BI authoring coverage**
  - `powerbi-authoring-cli` is now included in the authoring and full bundles.

### Changed

- **Plugin installation is now bundle-scoped.** Installing `fabric-authoring`, `fabric-consumption`, or `fabric-operations` installs only the skills and resources for that bundle instead of copying the entire repository.
- **Plugin packages are self-contained.** Public plugin folders include the materialized skills, agents, common references, and MCP configuration needed for GitHub-based plugin installation.
- **MCP configuration is scoped per bundle.** `fabric-consumption` and `fabric-skills` include the Power BI query MCP server configuration; authoring and operations bundles do not include unused MCP configuration.
- **`sqldw-monitoring-cli` was renamed to `sqldw-operations-cli`.** The new name aligns with the authoring, consumption, and operations skill categories.
- **Catalog search is now part of item discovery guidance.** Skills can use the Fabric Catalog Search API alongside list-and-filter workflows.
- **Version updated to `0.3.0`.**

### Available skills in this release

| Category | Skills |
|----------|--------|
| Authoring | `sqldw-authoring-cli`, `spark-authoring-cli`, `eventhouse-authoring-cli`, `eventstream-authoring-cli`, `powerbi-authoring-cli`, `dataflows-authoring-cli`, `dataflows-save-as-authoring-cli` |
| Consumption | `powerbi-consumption-cli`, `sqldw-consumption-cli`, `spark-consumption-cli`, `eventhouse-consumption-cli`, `eventstream-consumption-cli`, `dataflows-consumption-cli`, `search-consumption-cli` |
| Operations | `sqldw-operations-cli` |
| Migration and end-to-end | `databricks-migration`, `synapse-migration`, `hdinsight-migration`, `e2e-medallion-architecture` |
| Utility | `check-updates` |

## Earlier releases

Earlier releases introduced the initial Fabric Skills marketplace, update checking, SQL data warehouse authoring and consumption skills, Spark skills, MCP setup scripts, and cross-tool configuration files.
