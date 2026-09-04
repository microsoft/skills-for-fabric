# Changelog

User-facing changes for the public Microsoft Fabric Skills release.

## [0.3.15] - 2026-09-04


### Added
- **`skills/sqldw-cli`** -- added a read-only Capacity Metrics workflow that discovers the installed metrics model, adapts to timestamped or fixed-window schema variants, identifies costly Warehouse and Lakehouse SQL endpoint items, and analyzes every Query Insights request overlapping the Capacity Metrics spike range. Results keep fixed-window capacity health separate from broader item history, disclose timeframe and 30-day Query Insights limits, and treat SQL statement candidates as best-effort correlation because Capacity Metrics Operation Id and Query Insights `distributed_statement_id` are different identifiers.
- **`onelake-catalog-govern-cli`** -- audits and safely remediates Microsoft Fabric OneLake catalog governance across domains, workspaces, capacities, protection, and curation, with separate permission-aware modes for tenant admins and data owners.

### Changed
- **`skills/sqldw-cli`** -- expanded composite diagnostics for failed and canceled requests, SQL pool pressure, resource concentration, Lakehouse table health, performance regressions, optimization targets, and user/application activity. Custom SQL pool guidance now uses recurring historical contention and stable application classifiers rather than converting Capacity Metrics CU seconds or Query Insights CPU milliseconds into pool percentages.
- **`skills/sqldw-cli`** -- made operations follow-ups user-facing: results now turn evidence into concrete actions on the investigated workload, SQL item, capacity, or correlation report, while retaining timezone, retention, lag, and confidence caveats as limitations rather than skill-development suggestions.

### Fixed
- **`skills/sqldw-cli`** -- corrected pressure intervals to use the complete pool-state event stream and exact pool matching, included canceled requests in non-success analysis, limited Lakehouse health checks to Lakehouse SQL analytics endpoints, and stopped recommending result-set caching while the feature is unavailable.
- **`skills/sqldw-cli`** -- retained command-less and legitimate Query Insights-referencing requests in historical custom-pool profiles, excluding only agent-labeled diagnostics, and widened duration and CPU aggregation to `bigint`.
- **`semantic-model-authoring`** -- preserves existing Prep data for AI configuration during unrelated semantic model edits and uses the Power BI modeling MCP for read-only metadata discovery when available.
- `synapse-migration` now handles Dedicated SQL Pool DACPAC and zipped SQL-project schema and code migrations more reliably, validates generated Spark SQL, safely resumes interrupted operations, and isolates concurrent migrations across multiple datamarts.

## [0.3.14] - 2026-08-26


### Added
- **`databricks-migration`** -- added a guided four-phase workflow for inventorying, preparing, migrating, validating, and cutting over Databricks workloads to Fabric.
- **`databricks-migration`** -- added post-migration checks for environments, schemas, row counts, notebook and job execution, output comparison, and validation reporting.
- **`databricks-migration`** -- added troubleshooting guidance for common migration issues involving DLT, namespaces, widgets, Photon, DBFS, streaming, init scripts, and Git integration.

### Changed
- **Skill descriptions rewritten so the assistant picks the right one more often.** Every skill now states plainly what it owns, what it can do, when to choose it, and which neighbouring skill owns the work next door. Previously several skills described their area only in general terms, so a request that sat between two of them could reach the wrong skill -- or none at all, with the assistant answering from general knowledge instead. Requests that name a specific Fabric item or operation now land on the skill that owns it.

- **The full skill catalog fits comfortably within what the assistant reads at startup.** Only each skill's name and description are loaded up front, and that space is limited. The catalog previously ran close enough to the limit that adding skills risked pushing later ones past it -- and a skill past the limit is known only by its name, so the assistant can no longer tell what it does and chooses between skills on the name alone. The descriptions are now about 40% shorter with no loss of routing accuracy, leaving room for the catalog to grow.
- **`databricks-migration`** -- expanded migration planning with Blocker, Warning, and Info severity levels, accurate Scala and SparkR compatibility guidance, schema-enabled Lakehouse mapping, and structured failure reporting.
- **`semantic-model-authoring`** -- enable the `fabric-skills` bundle to use the hosted Power BI modeling service for semantic model authoring, while the `powerbi-authoring` bundle continues to support the local modeling server.

### Fixed
- **Seven skills regained the exact words people type.** The description rewrite favoured readable prose and, in doing so, dropped the literal tokens a request actually matches on: `MLV` and `OOM` (`spark-cli`), `count rows` and `SELECT` (`sqldw-cli`), `dacpac` and `sys.tables` (`sqldb-cli`), `executeQuery` and `saveAsNativeArtifact` (`dataflows-cli`), `libraryVariables` and `notebookutils` (`variable-library-cli`), and the `Gen1`/`Gen2` "not supported" caveat (`search-consumption-cli`). `git-integration-operations-cli` also lost its exclusions, so a question about `fabric-cicd` or branch switching could be captured by a skill that cannot help -- worse than a miss, because the answer sounds confident. Prose reads better to a reviewer; literals are what match a user's words. All seven are back, every description still inside the 450-character cap, for 361 characters against roughly 3,850 of bundle headroom.

- **`variable-library-cli`'s description was not a grammatical sentence.** "…and valueSets overrides, which consumers can reference a variable and with what syntax across pipelines…" -- a malformed clause in the one field the router reads. Rewritten, and `libraryVariables` and `notebookutils variableLibrary` restored with it.

- **`activator-cli`, `sqldw-cli` and `variable-library-cli`** -- these skills pointed you at skills that no longer exist. Their guidance still referred to `eventstream-authoring-cli`, `eventhouse-consumption-cli`, `spark-authoring-cli` and the separate `sqldb-authoring-cli` / `sqldb-consumption-cli` / `sqldb-operations-cli` skills, all of which were merged into single per-item skills in earlier releases. Handing work to a name that is not installed left the request stranded. They now name the current skills: `eventstream-cli`, `eventhouse-cli`, `spark-cli` and `sqldb-cli`.

- **`sqldb-cli`** -- "run a query against my Fabric SQL database" reached the Warehouse skill instead. `sqldb-cli` presented itself as a design-and-troubleshoot skill and never claimed plain querying, so the Warehouse skill won on the word "query". It now leads with querying a SQL database item, so the request reaches the right engine.

- **Git integration, deployment pipelines, Spark, Variable Library and Fabric IQ** -- several common requests reached the wrong skill or none at all: disconnecting a workspace from Git, asking which permissions or roles a deployment-pipeline stage needs, creating a materialized lake view, asking what a Variable Library value resolves to for a given release, and querying Fabric IQ directly. Each of these now names the case explicitly, so the request reaches the skill that handles it.
- **`databricks-migration`** -- corrected Databricks inventory commands, schema-enabled Lakehouse creation, Maven and JAR library handling, Environment definition paths, notebook export, Spark Job Definition deployment, job execution URLs, Spark version validation, and cancelled-versus-timed-out run handling.

## [0.3.13] - 2026-08-20


### Added
- **`skills/git-integration-operations-cli`** -- guidance for avoiding formatting-only diffs on Git sync. Fabric re-serializes item source (`notebook-content.py`, `pipeline-content.json`, `.platform`) to its canonical form (LF, no trailing final newline) on export, so an editor or AI agent that adds a trailing newline or CRLF causes every sync to report a spurious uncommitted change. Adds a troubleshooting-table row plus a "Avoiding formatting-only diffs" reference section with `.editorconfig` / `.gitattributes` snippets to pin the synced repo, and links the separate per-cell notebook newline rule in `spark-authoring-cli`.
- **`synapse-migration`** -- add a source-driven workflow for migrating Synapse Dedicated SQL Pool schema and executable code artifacts to Fabric Lakehouse, including discovery, gap assessment, T-SQL to readable Spark SQL `%%sql` notebook conversion, deployment, and validation. Stored-procedure notebooks reject PySpark/DataFrame conversions and source-only placeholders. Source table-row migration remains explicitly out of scope.
- **`synapse-migration`** -- make the gap report feature-wise and risk-driven, with support level, likelihood, impact, risk rationale, target pattern, and explicit `1:0`/`1:1`/`1:N`/`N:1`/`N:M`/`Deferred` cardinality. Target artifacts are generated only from approved designs; one source object is no longer assumed to equal one Lakehouse artifact.
- **`synapse-migration`** -- assess discovered procedure volume against projected Fabric workspace item usage, then require the user to provide and approve a `1:1`, `N:1`, or `N:N` notebook mapping, target names, and workspace placement before conversion begins.

### Fixed
- **`activator-cli`** -- creating an Activator item no longer fails with `HTTP 400 DisplayName field is required`. The authoring reference documented the create endpoint without a request body, and every rule, binding, data source and action argument in an Activator definition legitimately uses a `name` key, so `name` was easily carried over to the item itself by mistake. The Item CRUD section now includes a complete create request showing `displayName`, a callout explaining that `displayName` identifies the item while `name` belongs only inside the definition entities, and a matching entry in the AVOID list.
- **`activator-cli`** -- the authoring reference now shows the `fabricItemAction-v1` request payload inline at the assembly step that builds it, with the target carried in `payload.fabricItem` (`itemId`, `workspaceId`, `itemType`) and the supported `itemType` / `jobType` pairs listed, plus an AVOID entry for the invalid `targetItem` shape. The key was previously documented only in the delegated per-target reference, so a rule authored several steps after that file was read could invoke an item action that `updateDefinition` accepts but that never resolves its target.
- **`activator-cli`** -- the create request example now sends `--headers "Content-Type=application/json"` and carries a PowerShell variant that writes the body to `$env:TEMP` and passes it with `--body "@<file>"`. The section previously showed only a bash example with inline single-quoted JSON, so a PowerShell run failed twice before recovering -- once with `UnsupportedMediaType` for the missing content type, then with `InvalidInput` / `Unexpected character encountered while parsing value` when the shell mangled the inline JSON. The prose caveat pointing at the AVOID entry was not enough on its own, since the worked example is what gets copied.
- **`activator-cli`** -- the attribute assembly step now states that each attribute entity covers one source field and needs a unique name, that the identity field is already covered by its `IdentityPartAttribute`, and that cloning an attribute requires updating the `EventFieldSelector` `fieldName` as well as the payload `name`. Two matching AVOID entries were added. A cloned attribute that still selects the original field is accepted by `updateDefinition` and silently reads the wrong column.
- **`synapse-migration`** -- publish generated stored-procedure notebooks with externally overridable parameters, bounded status polling, clear failure reporting, persisted-definition readback, Lakehouse-binding checks, collision-safe idempotency, per-object approval states, and artifact-level validation.
- **`synapse-migration`** -- preserve stored-procedure input behavior by keeping supported inputs externally overridable, retaining exact source defaults only as `%%configure` fallbacks, blocking invented defaults, and rejecting generated SQL that replaces parameters with hardcoded literals or constant preview views.
- **`synapse-migration`** -- preserve each `1:1` stored-procedure `sourceName` as the generated notebook filename and Fabric display name, while retaining complete per-procedure traceability for approved decomposed or shared notebooks.
- **`synapse-migration`** -- make large stored-procedure migrations fully traceable and reproducible while preserving audit and logging behavior, retrying only failed conversion work, and validating complete source coverage before deployment.

## [0.3.12] - 2026-08-13

### Added
- **`skills/variable-library-cli`** -- new Microsoft Fabric skill for Variable Library definitions, value sets, active value set item state, and VL-side consumer wiring via CLI. Covers authoring, consumption and operations as modes of one skill.
- **Event Schema Set authoring** -- create, rename, override the definition of, and delete an Event Schema Set, alongside the existing read-only inspection.

### Changed
- **`skills/sqldw-cli`** -- `sqldw-authoring-cli`, `sqldw-consumption-cli`, and `sqldw-operations-cli` are now authoring, consumption, and operations modes of one skill. Existing capabilities and prompts remain supported; the MCP `fabric-sqlendpoint-execute_query` path remains primary, with the same Legacy CLI Fallback available when needed.
- **`skills/eventschemaset-cli`** -- unified Event Schema Set authoring (create, rename, override definition, delete) and read-only consumption (list, inspect, decode) behind one mode-dispatching skill, via the Fabric Items REST API (`az rest` + `jq` + base64 definitions). Handles `202 Accepted` long-running operations and the Preview delegated-identity constraints, and is available in the `fabric-authoring`, `fabric-consumption`, and `fabric-skills` plugin bundles.
- **`README.md` and `public/README.md`** -- the update-checking section is now a host-by-host table (Copilot CLI / Claude Code / Cursor, Windsurf and others) documenting how to turn on automatic updates, with the recommended `extraKnownMarketplaces` + `autoUpdate` snippet for Copilot CLI and a note that each release bumps the plugin `version` field.
- **`compatibility/CLAUDE.md`** -- the session-start update-check directive is replaced with Claude Code's one-time third-party marketplace auto-update opt-in, plus the on-demand `claude plugin update <plugin>@fabric-collection` command and a fallback for loose (non-plugin) copies.
- **Installation** -- the shipped bundles are now `fabric-skills` (every Fabric skill) and `powerbi-authoring` (Power BI report and semantic-model skills plus the `powerbi-modeling-mcp` server). The three retired ids remain resolvable as deprecated marketplace aliases of `fabric-skills`, so an already-installed user keeps working through `/plugin update`; the alias delivers the full union bundle rather than the former persona subset. New installs should use `fabric-skills`.

### Removed
- **`skills/sqldw-authoring-cli`**, **`skills/sqldw-consumption-cli`**, **`skills/sqldw-operations-cli`** -- superseded by the `sqldw-cli` item skill. Install `sqldw-cli` instead; it covers all three surfaces.
- **`skills/eventschemaset-consumption-cli`** -- replaced by `skills/eventschemaset-cli`.
- **BREAKING -- the `check-updates` skill has been removed outright** (no deprecation stub). It is gone from all five plugin bundles (`fabric-skills`, `fabric-authoring`, `fabric-consumption`, `fabric-operations`, `powerbi-authoring`), so `/fabric-skills:check-updates` and the other `<bundle>:check-updates` invocations no longer resolve. The skill did not update anything on its own initiative: it resolved the install context, compared versions, and surfaced the host's own native update command, executing it only on an unambiguous request. Both major hosts support native auto-update once configured -- GitHub Copilot CLI supports `"autoUpdate": true` on an `extraKnownMarketplaces` entry in personal user settings, while Claude Code provides a one-time **Enable auto-update** marketplace action or a managed-settings `"autoUpdate": true` option -- which makes the skill redundant at the cost of a mandatory blockquote on every skill load. On-demand updates remain available via `/plugin update` and `copilot plugin update --all`.
- **The mandatory once-per-session "Update Check" blockquote** has been stripped from every `SKILL.md` (30 skills) and is no longer a structural requirement. This reclaims the context budget the notice consumed on every skill load, and removes the extra with-skill token overhead that previously skewed skill-ROI comparisons.
- **`fabric-authoring`, `fabric-consumption`, `fabric-operations` plugin bundles** -- retired. Each was a strict subset of `fabric-skills` in skills, agents, and MCP servers, so every skill they carried still ships in `fabric-skills`. The persona split stopped describing a real boundary once skills merged to one skill per Fabric item: `sqldw-cli`, `sqldb-cli`, and `spark-cli` each carry authoring, consumption, and operations modes, so each appeared in all three bundles and installing `fabric-operations` shipped the full Spark authoring guidance.

### Fixed
- **`skills/spark-consumption-cli`** -- corrected simple Lakehouse SQL endpoint routing guidance to use the MCP `fabric-sqlendpoint-execute_query` path instead of the stale `sqlcmd` client name.

## [0.3.11] - 2026-08-06


### Added
- **`skills/git-integration-operations-cli`** -- new Microsoft Fabric skill for driving the Git integration lifecycle of a workspace via CLI: connect/disconnect against Azure DevOps and GitHub, initialize the connection, commit workspace items to Git, update (pull) a workspace from Git, check sync status, and resolve conflicts.
- **`skills/deployment-pipelines-authoring-cli`** -- new authoring skill for Microsoft Fabric
  deployment pipelines (ALM / CI-CD). Guides the Fabric core REST API surface
  (`/v1/deploymentPipelines`) to create pipelines and stages, assign/unassign workspaces to stages,
  and deploy stage content across dev/test/prod as a long-running operation (all items or selective
  item deploys). Covers per-operation **delegated scopes** (`Pipeline.Read.All` / `Pipeline.ReadWrite.All`
  / `Workspace.ReadWrite.All`, and `Pipeline.Deploy` for deploy), required **permissions** (pipeline Admin
  + workspace roles), **item pairing / autobinding** repair (unassign->reassign with a deployment-rule-loss
  warning), and a maintainable **supported item types** reference reconciled from the official Microsoft
  Fabric documentation.
- **`skills/deployment-pipelines-authoring-cli/references/scripts/diff_item_definitions.py`** -- a local,
  stdlib-only tool that compares two stages' `getDefinition` payloads and emits **only** the differences.
  It decodes each base64 part, **normalizes** the fields Fabric auto-rebinds on deploy (pipeline
  `notebookId`/`workspaceId`, report->model id, Direct Lake server/db, connections) to avoid false-positive
  "changed" items, matches parts by path, and produces a structural JSON diff for JSON parts and a unified
  diff for text parts (TMDL/`.py`/`.pq`). Exit code mirrors POSIX `diff` (`0`=identical, `1`=changed,
  `2`=error) so it doubles as the change detector for selective deploys; includes a built-in `--selftest`.
  This lets the *Deploy only changed items* workflow forward **only the emitted diff** (a few lines) to the
  model instead of two full definitions (>100 KB).
- **Change-detection & deploy guidance** -- the skill documents that `List stage items` returns item
  identity + pairing (`itemId`, `itemDisplayName`, `itemType`, `sourceItemId`, `targetItemId`,
  `lastDeploymentTime`) with no change status, and that `lastDeploymentTime` is the last *deployment* time
  (not the last edit), so change detection must diff `getDefinition` payloads per stage; notes the
  `getDefinition` contract differs by type (Notebook/SemanticModel/Report are LRO, DataPipeline is
  synchronous; Warehouse has no definition API); and captures deploy operational caveats -- one operation
  per pipeline at a time (`WorkspaceMigrationOperationInProgress` HTTP 400), first-deploy warm-up
  (`Alm_InvalidRequest_WorkloadUnavailable`, ~60-120 s), the `x-ms-operation-id` response-header location,
  the 300-item-per-deploy cap, the write-only deploy `note`, and that deploys copy definitions, not data.
- **`skills/fabriciq-ontology-cli`** -- unified Fabric IQ Ontology skill with explicit authoring and consumption modes.
- **`skills/eventstream-cli`** -- one Eventstream skill with authoring and consumption modes for topology creation, lifecycle changes, inspection, health, retention, throughput and Custom Endpoint connection metadata.
- **`skills/activator-cli`** -- one Activator / Reflex skill with authoring and consumption modes covering item and rule creation, sources, conditions and actions, plus read-only listing, inspection and `ReflexEntities.json` decoding.
- Added `sqldb-cli`, a three-mode dispatcher for Fabric SQL database authoring, consumption, and OLTP performance diagnostics.

### Changed
- **`skills/mlv-operations-cli`** -- documents the Fabric MLV job-type mismatch where history/status can show `MaterializedLakeViews`, but on-demand refresh must use the lakehouse-scoped `refreshMaterializedLakeViews/instances` endpoint. The skill now also absorbs the 2026-07-01 public API additions for MLV execution definitions and selected-lineage refresh via `executionData.mlvExecutionDefinitionId`, and directs interactive recurring refresh to Lakehouse schedules instead of notebook or pipeline orchestration.
- **Skill naming convention** -- skills are now named `{item}-cli`, one per Fabric item or capability, and cover authoring, consumption and operations as internal **modes**, selected by a dispatcher in `SKILL.md` with per-mode detail under `references/{mode}.md`. New `-authoring-` / `-consumption-` / `-operations-` skills are no longer created; add the capability as a mode of the item skill instead. Existing skills keep their names until their item migrates.
- **`skills/dataflows-cli`** -- `dataflows-authoring-cli`, `dataflows-consumption-cli` and `dataflows-save-as-authoring-cli` are now the authoring, consumption and upgrade modes of a single `dataflows-cli` skill. Behaviour is unchanged; the guidance moved into `references/{mode}.md` and the dispatcher carries a terminal-write table so each mode's state-changing call stays in the always-loaded body.
- **`skills/eventhouse-cli`** -- unified Eventhouse authoring and read-only KQL consumption behind one mode-dispatching skill.

### Removed
- **`skills/dataflows-authoring-cli`**, **`skills/dataflows-consumption-cli`**, **`skills/dataflows-save-as-authoring-cli`** -- superseded by the `dataflows-cli` item skill. Install `dataflows-cli` instead; it covers all three surfaces.
- **`skills/fabriciq-ontology-authoring-cli`** and **`skills/fabriciq-ontology-consumption-cli`** -- folded into `fabriciq-ontology-cli` without changing their operational guidance.
- **`skills/eventstream-authoring-cli`** and **`skills/eventstream-consumption-cli`** -- replaced by the matching modes in `skills/eventstream-cli`.
- **`skills/eventhouse-authoring-cli`** and **`skills/eventhouse-consumption-cli`** -- replaced by `skills/eventhouse-cli`.
- **`skills/activator-authoring-cli`** and **`skills/activator-consumption-cli`** -- replaced by the matching modes in `skills/activator-cli`.
- Removed the superseded `sqldb-authoring-cli`, `sqldb-consumption-cli`, and `sqldb-operations-cli` top-level skills.

### Fixed
- **`.mcp.json`, `plugins/fabric-skills`, `plugins/fabric-consumption`** -- explicitly allow-list every FabricIQ MCP tool via `"tools": ["*"]`, so hosts that gate MCP tools on an explicit allow-list expose the full FabricIQ tool set (artifact discovery, schema inspection, value search, query execution) to the agent.
- **`eventstream-cli` lifecycle control** -- documented bodyless pause requests, the required resume `startType` body, and the correct source/destination pause and resume endpoint order.
- **`plugins/*`** -- fix Claude Cowork "Marketplace sync failed" by materializing a `.claude-plugin/plugin.json` in each plugin bundle. The plugin trees only carried the Copilot manifest at `.github/plugin/plugin.json`, so Claude/Cowork strict-mode discovery could not find the plugin manifest it expects. The Claude manifest is generated from the same per-plugin source manifest (no drift) and shipped to the public repo during sync.
- **`.claude-plugin/marketplace.json`, `plugins/*/.claude-plugin/plugin.json`** -- fix `/plugin install <bundle>@fabric-collection` failing in Claude Code with `This plugin uses a source type your Claude Code version does not support`. Claude Code parses each `mcpServers` entry against a closed stdio/sse/http/ws schema that treats `tools` as reserved, so the per-server allow-list added for Copilot CLI made every bundle carrying MCP servers unparseable; the misleading "source type" wording pointed nowhere near the real field. Both Claude-facing manifests are now generated through `claude_safe_mcp_servers()`, which drops only that key, and the build fails non-zero if any Claude-facing manifest carries it. Copilot CLI keeps its allow-list unchanged. Resolves microsoft/skills-for-fabric#69.

## [0.3.10] - 2026-07-30

### Added
- **`skills/e2e-fabric-cost-estimation`** -- new skill for estimating Microsoft Fabric workload costs before migration. Covers CU capacity sizing, billing-mode strategy (Reserved vs. PAYG vs. Autoscale Billing for Spark), storage/network pricing, SKU right-sizing, and multi-cloud source cost equivalence (Databricks/Synapse/HDInsight and other platforms). The skill instructs the agent to fetch prices live where public APIs exist (Azure Retail Prices API, AWS Price List, GCP Cloud Billing Catalog) and from official pricing pages or the customer's billing/usage data where they don't (Databricks, Snowflake, Teradata), rather than hardcoding them, and to surface the source and date with every quoted figure.

- **`skills/eventschemaset-consumption-cli`** -- new read-only skill to list, inspect, and describe Microsoft Fabric Event Schema Sets via the Fabric Items REST API (`az rest` + `jq`): enumerate Event Schema Sets in a workspace, read item properties (OneLake root path, sensitivity label, tags), and retrieve then base64-decode the item definition to summarize its `eventTypes` and `schemas`.
- **`activator-authoring-cli` and `activator-consumption-cli`** -- create and inspect alerts backed by Power BI reports and semantic models, including validated metric queries, personalized filters, and explicit handling of the current public readback limitation.

### Changed
- **`skills/sqldw-consumption-cli`, `skills/sqldw-authoring-cli`, `skills/sqldw-operations-cli`** -- the
  primary T-SQL execution path is now the native `fabric-sqlendpoint-execute_query` MCP tool instead of
  shelling out to `sqlcmd`. SKILL.md and `references/` updated to call
  `execute_query(workspaceId, itemId, query)` (GUID-based identity, single-batch, no `GO`), document the
  MCP limits (10,000-row cap, 300s timeout, 20 req/min), and keep `sqlcmd` only as a documented legacy
  fallback. The Fabric SQL Endpoint MCP server (`fabric-sqlendpoint`) ships headerless in the
  consumption/authoring/operations plugins and authenticates lazily via Copilot's native session.
- **`skills/semantic-model-authoring`** -- Added a metadata-discovery capability using DAX `INFO` functions (new `references/metadata-discovery.md` + `Discover Semantic Model Metadata` workflow). 

### Removed
- **`skills/semantic-model-consumption`** -- Removed. Its capabilities are now split between two skills: semantic-model metadata discovery (DAX `INFO` functions) moved into `semantic-model-authoring`, and natural-language data queries are handled by `fabriciq`.

### Fixed
- **`skills/sqldw-operations-cli/references/query-reference.md`** -- clarified that the MCP tool does not
  support sqlcmd-style external parameter substitution (in-batch `DECLARE` T-SQL variables are fine), and
  changed the `DATEADD(..., -N, ...)` parameter-table defaults to positive `N` so substitution no longer
  produces a double-negative.
- **`skills/sqldw-consumption-cli/references/discovery-queries.md`** -- removed leftover `sqlcmd` artifacts
  (`$SQLCMD -Q ... -W`); query blocks now show plain T-SQL (the `query` parameter value) in `sql`-tagged fences.
- **SQL DW `SKILL.md` connection snippets** -- the workspace-discovery step now captures the result into
  `WS_ID` before reusing it, so the copy/paste flow works end-to-end. Bare code fences are language-tagged,
  and a note clarifies that the concrete MCP tool name may be prefixed.
- **`skills/sqldw-consumption-cli/references/script-templates.md`** -- export template lists explicit
  columns (no `SELECT *`) with a stable `ORDER BY` key.
- **`skills/sqldw-authoring-cli/references/authoring-cli-quickref.md`** -- upsert example wrapped in
  `TRY/CATCH` with `ROLLBACK` + `THROW` for safe transaction handling.
- **`skills/sqldw-authoring-cli/references/authoring-script-templates.md`** -- added a placeholders note for
  the illustrative storage URLs, dates, and `LABEL` values.
- **SQL DW `SKILL.md` + quickref `itemId` guidance** -- clarified that for a Lakehouse the `itemId` must be
  the SQL analytics endpoint id (`properties.sqlEndpointProperties.id`), not the lakehouse item id.
- **`hdinsight-migration`** - corrected HDFS guidance and improved routing for Oozie action migration requests.
- **`sqldb-operations-cli`** -- avoid installing SQL client tooling during diagnostics by using an available PowerShell SqlClient provider when an installed `sqlcmd` client cannot authenticate, or reporting that no compatible preinstalled TDS client is available.

## [0.3.9] - 2026-07-23

### Added
- **`skills/azmon-mirroredcatalogs-operations-cli`** -- onboards Azure Monitor / Application Insights / Log Analytics observability data into Microsoft Fabric as a Mirrored Catalog item and turns that telemetry into business-impact insights by correlating observability signals with business data, ending in ready-to-paste Operations Agent instructions.

### Changed
- **`skills/semantic-model-authoring`** -- removed instructions that referenced the upcoming Copilot file format.
- **`databricks-migration`** -- expanded Databricks-to-Fabric guidance for `dbutils` replacements, notebook parameters, environments, Lakehouse table references, MLflow, and workload mappings.

### Fixed
- **`skills/activator-authoring-cli`** -- treat schema-only, zero-row, non-emitting, or stale signal sources as missing source data so the skill stops and asks for source details instead of force-fitting a rule onto an unrelated existing item.
- **`skills/activator-consumption-cli`** -- route read-only "show me all Activators" prompts to consumption guidance instead of the authoring skill.
- **`check-updates`** -- detects marketplace plugins, direct plugins, positively identified Git clones, and loose skills copied or materialized from a file or URL; isolates the seven-day cache by installed entry or clone root; provides host-appropriate Copilot, Claude, Cursor, or safe no-command update guidance; and offers an explicit, confirmation-gated migration from official loose copies to a complete current plugin bundle.
- **`databricks-migration`** -- corrected mount and notebook parameter guidance, and now requires inventory and constraint clarification before recommending a workspace-wide Fabric topology.

## [0.3.8] - 2026-07-16

### Added
- **Public issue routing** -- the public repository now provides dedicated bug and feature issue forms with a required owner-area selector and automatic `area:<slug>` labeling.

### Changed
- **Installation and update guidance** -- the public README now clarifies the scope of the main and focused plugin bundles and documents both per-bundle updates and `copilot plugin update --all`.
- **Skill routing boundaries** -- improved selection across catalog search, Dataflows Gen1 save-as, Spark authoring/consumption/operations, Warehouse SQL, MLV operations, and end-to-end medallion prompts. Ad hoc Livy session execution now routes to `spark-consumption-cli`.
- **`eventstream-authoring-cli`** -- user-defined topology node names now require alphanumeric PascalCase; the platform-generated `DefaultStream` naming exception is documented.

### Fixed
- **`dataflows-authoring-cli`** -- connector capability answers now use the tenant's live `supportedConnectionTypes` endpoint, and completion summaries identify the actual definition persist endpoint used.
- **`dataflows-save-as-authoring-cli`** -- readiness output now consistently uses the canonical `Save-As Readiness Snapshot` heading.

## [0.3.7] - 2026-07-09

### Added
- **`skills/sqldb-authoring-cli/SKILL.md`, `skills/sqldb-consumption-cli/SKILL.md`, `skills/sqldb-operations-cli/SKILL.md`** -- new SQL Database in Fabric skills (authoring, read-only consumption, and performance/diagnostics).

### Changed
- **`skills/powerbi-report-authoring`**, **`skills/powerbi-report-design`**, **`skills/powerbi-report-management`**, **`skills/powerbi-report-planning`** -- refreshed guidance (no routing or version changes): `cardVisual` vs. legacy `multiRowCard` anti-patterns and multi-value card guidance, `catalog describe` role-name verification (`Data` vs. legacy `Fields`), CLI `@latest` install/update guidance, PBIR `.platform`/`version.json`/`pages.json` scaffolding clarifications, conditional-formatting data-bars and single-hue gradient guidance, `fontColor` vs. `fontColorPrimary` handling, Desktop unsaved-changes pre-reload check, slicer tooltip `visualTooltip.show` requirement, and cartesian/non-cartesian per-series color guidance.
- **`skills/dataflows-authoring-cli`** -- treats a terminal, non-retriable Dataflow Gen2 refresh outcome as a stop condition instead of a debugging loop: a refresh/LRO job reaching terminal `Failed`/`Cancelled`, a backend error with `isRetriable: false`, or a workspace-wide `UnknownException` now surfaces the raw `failureReason` and ends. Refresh-failure isolation is bounded to a single `executeQuery` attempt. The refresh-poll examples (bash + PowerShell) poll a bounded loop over the known terminal set (`Completed`/`Failed`/`Cancelled`/`Deduped`), treat `Deduped` as concurrency (another refresh already running) rather than a failure, and surface `.failureReason` on `Failed`/`Cancelled`.

### Fixed
- **`skills/powerbi-report-authoring`** -- schema-version guidance no longer points at the unpublished `visualContainer/2.10.0` schema (which returns 404 on live `$schema` validation); it now copies `$schema` from an existing `visual.json` and otherwise falls back to the published `2.9.0`. Fixes microsoft/skills-for-fabric#55.
- **`skills/powerbi-report-authoring`** -- map fallback guidance uses the valid `clusteredBarChart` visual type (was the invalid `barChartClustered`) and no longer mislabels `shapeMap` as a legacy visual (only `map`/`filledMap` are legacy Bing Maps visuals; verified via `powerbi-report-author validate`).
- **`skills/powerbi-report-design`** -- accessibility target-size criterion corrected from WCAG 2.5.5 (Target Size Enhanced, AAA, ≥44px) to 2.5.8 (Target Size Minimum, AA, ≥24px), and contrast-ratio examples corrected. Fixes microsoft/skills-for-fabric#43.
- **`skills/powerbi-report-authoring`** -- `version.json` scaffolding guidance now stresses preserving the full scaffolded file including `$schema`, avoiding the local-validate-passes-but-Fabric-`updateDefinition`-rejects mismatch. Relates to microsoft/skills-for-fabric#35.
- **`skills/activator-authoring-cli`** -- when a requested alert or rule targets a signal that no discoverable source in the workspace exposes, the skill now stops and asks which source and fields provide it instead of creating a Reflex or modifying an unrelated existing item to force-fit the request.

## [0.3.6] - 2026-07-02

### Added
- **`skills/dataflows-authoring-cli`** -- preview-and-confirm step in the dataflow creation flow: the agent previews each entity via `executeQuery` and renders ASCII line/bar charts (`references/charts/line_chart.py`, `references/charts/bar_chart.py`) so the user can validate output before the first refresh.

### Changed
- **Eventstream skills enhanced** (`eventstream-authoring-cli`, `eventstream-consumption-cli`; both shipped in v0.3.5) -- SKILL.md, core-reference, and API-endpoint refinements detailed below.
- **`eventstream-consumption-cli` — Custom Endpoint connection string retrieval recipe.** New "Get Custom Endpoint Connection String" section with full `az rest` CLI recipes (bash + PowerShell) showing the 2-step Topology API workflow: get topology → get source connection. Includes security guidance, multi-source disambiguation, Kafka producer config table, and MUST DO rule.
- **`EVENTSTREAM-AUTHORING-CORE.md` — Eventhouse ingestion modes guidance.** Added ProcessedIngestion as recommended API-automatable path with full example, DirectIngestion warning documenting the known UI-only data connection limitation, cross-skill collaboration pattern table, and CDC bracket-escaping fix.
- **Corrected Eventstream Definition API endpoints** -- All SKILL.md code blocks updated from unsupported `GET .../definition` / `PUT .../definition` to the official `POST .../getDefinition` / `POST .../updateDefinition` per Microsoft Learn docs.
- **`skills/search-consumption-cli`** -- reworked the skill description and triggers to lead with catalog-search framing ("search for an item", "search the catalog", "catalog search") and dropped discovery-verb-only triggers that did not reliably route to it. The skill now activates for cross-tenant "search the catalog for an item" requests, which is its actual purpose (the Fabric Catalog Search API). Reconciled the troubleshooting note on indexing lag (variable, not yet near-real-time; not a fixed ~24h).

### Fixed
- **`skills/dataflows-consumption-cli`** -- chart reference examples are now runnable as-written: bar-chart example passes the required `--labels`, `jq group_by` is preceded by `sort_by`, and the bar/pie renderers cast labels to `str` to avoid `TypeError` on numeric JSON categories.

## [0.3.5] - 2026-06-25

### Added
- **New skills `fabriciq-ontology-authoring-cli` and `fabriciq-ontology-consumption-cli`** — Fabric IQ Ontology (preview) support from the CLI. `fabriciq-ontology-authoring-cli` creates and evolves Ontology items (entity types, properties incl. timeseries, relationship types, and bindings to OneLake lakehouse or Eventhouse / KQL tables) via the Fabric item-definition REST API with a mandatory Preview & Confirm gate before any LRO write. `fabriciq-ontology-consumption-cli` reads Ontology items to produce agent grounding context and routes ontology-backed data queries by binding type to the matching per-datasource consumption skill (`eventhouse-consumption-cli`, `spark-consumption-cli`, `sqldw-consumption-cli`). Adds per-skill `references/` (including a shared ontology schema reference bundled into each skill).
- **New skill: `mlv-operations-cli`** -- Manage Materialized Lake View (MLV) refresh schedules and job execution via Fabric REST APIs. Provides scheduling and monitoring operations (9 endpoints):
  - **Schedule Management**: Create/list/update/delete refresh schedules (Cron, Daily, Weekly, Monthly)
  - **Job Execution**: Trigger on-demand refreshes, monitor job status/history, cancel running jobs
  - **UX Patterns**: Human-in-the-loop confirmations, step-by-step planning, iterative error handling
  - **Gap Documentation**: Transparently documents MLV discovery limitations — user must provide lakehouse ID and table names manually
- **Cross-skill integration** -- Routing from spark-authoring-cli, spark-operations-cli, FabricDataEngineer agent delegation
- **Competitive advantage** -- Fabric is first platform to offer conversational MLV scheduling (Databricks Lakeflow has no equivalent)

## [0.3.4] - 2026-06-18

### Added
- **Materialized Lake View (MLV) resources for `spark-authoring-cli`** -- two new resource documents:
  - `resources/materialized-lake-view-patterns.md` -- MLV design guidance, layering patterns, when to use MLVs vs. plain Delta tables, and the SQL-vs-PySpark authoring tradeoff (PySpark MLVs are lineage-schedule-refresh only and don't support on-demand notebook refresh).
  - `resources/mlv-incremental-refresh-patterns.md` -- refresh-readiness review workflow, IR-friendly syntax guide, full-refresh blocker catalog, and safe non-breaking rewrites.
- **MLV triggers + routing in `spark-authoring-cli/SKILL.md`** -- discovery phrases (`materialized lake view`, `MLV`, `CREATE MATERIALIZED LAKE VIEW`, `MLV incremental refresh`, `review MLV for incremental refresh`, `MLV refresh policy`, `schedule MLV refresh`), resource table entries, Rule 4 MLV routing, and a quick-start SQL example.
- **Cross-link from `e2e-medallion-architecture` PREFER section** -- points Silver/Gold layer authoring at the new MLV resources.
- **M language semantics reference for `dataflows-authoring-cli`** — new `references/m-language.md` covering language-side pitfalls confirmed live against a Fabric Dataflow Gen2 via `executeQuery`: `try` success vs failure record shapes (`[HasError, Value]` vs `[HasError, Error[Reason, Message, Detail]]`), `try ... otherwise` short-circuit semantics, per-cell error wrapping in `Table.TransformColumnTypes` and `Table.TransformColumns` (errors stored at the cell level — Arrow renders them as `null` but reads raise), `each` scoping divergence between row contexts (`Table.SelectRows`: `_` is a row record) and sub-table contexts (`Table.Group`: `_` is the sub-table — use `_[Col]` for the column-as-list), optional field access (`r[key]?`, `Record.FieldOrDefault`), quoted-identifier escaping (`#"..."`), error-record construction, and sandbox-disabled symbols. SKILL.md References table updated.
- **Source connector patterns for `dataflows-authoring-cli`** — new `references/connectors.md` covering the M-side source connector surface: live-verified function inventory (`Lakehouse.Contents`, `Sql.Database`, `Fabric.Warehouse`, `OData.Feed`, `Web.Contents`, `PowerPlatform.Dataflows`, `Snowflake.Databases`, `AzureStorage.DataLake`, `Excel.Workbook`, `Variable.Value`, `Html.Table`, `Csv.Document`, `Json.Document`, `Lines.FromBinary`), verified Lakehouse deep navigation (`workspaceId` → `lakehouseId` → flat-table `Name` index), `PowerPlatform.Dataflows` workspace/dataflow navigation (`{[Id="Workspaces"]}[Data]` → `workspaceId` → `dataflowName`), runtime-disabled functions (`Web.Page`, `Web.BrowserContents`), credentialed-connector argument shapes, the in-band `{"Error":"..."}` decoding contract for `executeQuery` Arrow responses, and the `[AllowCombine = true]` multi-source section attribute. Every behaviour claim was reproduced live via `executeQuery`.
- **Gemini CLI compatibility** -- new `compatibility/GEMINI.md` (a thin `@./AGENTS.md` import) is flattened to the public repo root by the release flow, so cloning the public repo enables Gemini CLI automatically.

### Changed
- **Compatibility files** (`compatibility/CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.windsurfrules`) -- added pointers to the new MLV resources so cross-tool consumers route to the same guidance.
- **`skills/dataflows-authoring-cli/SKILL.md`** — added a requirement to name the definition parts (`mashup.pq`, `queryMetadata.json`, `.platform`) in the written summary so they survive transcript truncation; condensed the connector-types note to keep the YAML description within the 1023-char limit.

### Fixed
- **Cross-tool config files** -- removed dead "see DEVELOPMENT-GUIDE.md at repository root" references (the file never existed) from `AGENTS.md`, `.cursorrules`, and `.windsurfrules`. `AGENTS.md` and `.windsurfrules` now inline the `az login` token steps the link was meant to provide, matching `CLAUDE.md`.

## [0.3.3] - 2026-06-07

### Added

- **`powerbi-report-planning`** — guided requirements-to-implementation workflow for new Power BI reports and dashboards built from semantic models, datasets, or PBIP projects. Use to plan then implement a report end-to-end: define audience, scope, page plan, design direction, dependencies, and delivery target, then produce a locked report spec with explicit approval before any PBIR authoring begins. For direct authoring without the planning gate, invoke `powerbi-report-authoring` directly.
- **`powerbi-report-design`** — visual design guidance for Power BI reports before any PBIR files are written. Use to choose tone, signature, page archetypes, chart types, layout, color, typography, theme direction, and accessibility approach; to redesign/restyle an existing report or apply a brand; or to critique chart and layout choices. Produces a design contract that downstream authoring consumes. Ships with 19 references covering accessibility, anti-patterns, page archetypes (analytical canvas, comparative benchmark, executive summary, narrative story, operational monitor), brownfield migration, chart selection, design brief, interactivity, pre-flight checklist, signatures, tone catalog, typography, and a visual cookbook.
- **`powerbi-report-authoring`** — create and modify Power BI report files in PBIR/PBIP format using the `powerbi-report-author` and `powerbi-desktop` CLIs. Implements an approved report spec or design brief; adds or edits pages, visuals, filters, slicers, bookmarks, themes, and formatting; validates PBIR and verifies rendering in Power BI Desktop. Ships with 23 references covering authoring, cartesian charts, color strategy, conditional formatting, expressions, filter pane, filters, formatting (overview + details), image, page formatting, Power BI Desktop, the `powerbi-report-author` CLI, re-theming, screenshot review, shape, slicers, table, textbox, theming, and version control. For open-ended visual design choices, invoke `powerbi-report-design` first.
- **`powerbi-report-management`** — manage Power BI report workspace items in Microsoft Fabric via `az rest` CLI against the Fabric REST API. Create reports from PBIR definitions, get or download report definitions, update report definitions or properties, list workspace reports, and delete reports. For report layout authoring (pages, visuals, filters, formatting), use `powerbi-report-authoring` instead.
- **`powerbi-authoring` plugin bundle expanded** — the dedicated `powerbi-authoring` plugin now ships the four new `powerbi-report-*` skills alongside `semantic-model-authoring` and `check-updates`, with the `powerbi-modeling-mcp` server pre-configured. Reinstall via `/plugin install powerbi-authoring@fabric-collection` to pick up the new report skills.

### Changed

- **`semantic-model-authoring` DAX performance references refined** — added Microsoft Learn further-reading links for DAX engine tracing, horizontal fusion, and Direct Lake query performance in `dax-perf-decision-guide.md` and `dax-perf-patterns.md`; renamed scenario-specific DAX examples to use generic names; rewrote DAX examples to be self-contained so they're easier to read on their own.

## [0.3.2] - 2026-06-03

### Added

- **`semantic-model-authoring`** — develop and manage Power BI semantic models across Power BI Desktop, PBIP projects, and the Fabric Service. Covers creating models (Import, DirectQuery, Direct Lake), editing measures/tables/columns/relationships, deploying to Fabric workspaces, refreshing, configuring data sources and permissions, and DAX performance optimization. Ships with 11 reference guides (connection binding, DAX guidelines, DAX performance decision guide, DAX performance patterns, Direct Lake guidelines, modeling guidelines, naming conventions, PBIP, semantic-model AI readiness, semantic-model REST API, TMDL guidelines). **Replaces `powerbi-authoring-cli`.**
- **`semantic-model-consumption`** — execute raw DAX queries and inspect metadata of Microsoft Fabric Power BI semantic models via the MCP server `ExecuteQuery` tool. Use when you already know the DAX (EVALUATE statements) or need to inspect tables, columns, measures, relationships, and hierarchies via INFO functions. **Replaces `powerbi-consumption-cli`.**
- **`fabriciq`** — answer business questions by querying Power BI reports and dashboards through the FabricIQ MCP endpoint. Orchestrates artifact discovery, schema inspection, entity-value resolution, DAX generation, and query execution; returns plain-language answers. Use for natural-language questions about Power BI report/dashboard content (use `semantic-model-consumption` for raw DAX).
- **`FabricIQ` agent** — answers questions about Power BI artifacts (reports and semantic models) by discovering artifacts, inspecting metadata and schemas, resolving entity values, generating DAX, and executing queries against the Fabric MCP endpoint. Delegates to `fabriciq`.
- **Dedicated `powerbi-authoring` plugin bundle** — ships `semantic-model-authoring` and `check-updates` with the `powerbi-modeling-mcp` server (`@microsoft/powerbi-modeling-mcp`) pre-configured for fine-grained semantic-model modeling operations. Install via `/plugin install powerbi-authoring@fabric-collection`.
- **`dataflows-authoring-cli` reference docs (3 new)** — `output-destinations.md` (Lakehouse/Warehouse/SQL DB output destination patterns including staging behavior, schema mapping, and refresh semantics), `connection-management.md` (creating, binding, and rotating connection IDs for Dataflows Gen2), and `mashup-preview.md` (inspecting and validating Power Query M before publishing).
- **`spark-operations-cli` automated diagnostic workflow** — new `references/automated-diagnostic-workflow.md` for end-to-end Spark/Livy diagnostics: job triage → executor/driver log mining → Spark Advisor findings → mitigation recommendations.
- **`synapse-migration` deep resources (12 new)** — capacity sizing, connector refactoring, external Hive Metastore migration, feature parity matrix, lake database migration, library compatibility, migration gotchas, migration orchestrator, migration report, security and governance, Spark item migration, Spark pool migration, and validation/testing.
- **`EVENTHOUSE-CONSUMPTION-CORE` common reference** — shared Eventhouse/KQL consumption patterns surfaced via the `fabric-authoring` plugin bundle.

### Changed

- **`powerbi-authoring-cli` renamed to `semantic-model-authoring`** — aligns the skill name with the underlying Microsoft Fabric / Power BI artifact (a *semantic model*) rather than the surface tool. Same coverage of model authoring plus an expanded reference library. Re-invoke as `semantic-model-authoring` going forward.
- **`powerbi-consumption-cli` renamed to `semantic-model-consumption`** — same rationale; same DAX query / metadata surface. Re-invoke as `semantic-model-consumption` going forward.

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
| Consumption | `semantic-model-consumption`, `fabriciq`, `sqldw-consumption-cli`, `spark-consumption-cli`, `eventhouse-consumption-cli`, `eventstream-consumption-cli`, `dataflows-consumption-cli`, `search-consumption-cli` |
| Operations | `sqldw-operations-cli` |
| Migration and end-to-end | `databricks-migration`, `synapse-migration`, `hdinsight-migration`, `e2e-medallion-architecture` |
| Utility | `check-updates` |

## Earlier releases

Earlier releases introduced the initial Fabric Skills marketplace, update checking, SQL data warehouse authoring and consumption skills, Spark skills, MCP setup scripts, and cross-tool configuration files.
