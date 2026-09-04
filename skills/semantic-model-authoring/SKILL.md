---
name: semantic-model-authoring
description: "Manages Power BI semantic models, including tables, columns, measures, relationships, DAX authoring and tuning, Performance Analyzer diagnostics, Import, DirectQuery and Direct Lake designs, sources, connections, permissions, refresh, and deployment. Load this skill before acting on a semantic model or analyzing a Power BI Performance Analyzer JSON export, unless it is part of publishing a PBIP project, which powerbi-report-management owns. For natural-language data questions use fabriciq; for visuals use powerbi-report-authoring."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: semantic-model-authoring` (`az rest`: `--headers "x-ms-fabric-skill=semantic-model-authoring"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. Always consider the [Tool selection priority](#tool-selection-priority) when choosing which tool to use for each operation. Do not default to TMDL edits or `az rest` if MCP is available and connected to the target model.

# Power BI Semantic Model Authoring — CLI Skill

## Workflow Selector

Use this decision tree to route to the correct workflow based on user intent:

| User wants to...                                                                | Workflow                                                                             |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Create a semantic model from scratch                                            | [Create new semantic model](#workflow-create-new-semantic-model)                     |
| Inspect or discover model metadata (tables, columns, measures, relationships)   | [Discover Semantic Model Metadata](#workflow-discover-semantic-model-metadata)      |
| Add/edit semantic model objects (e.g. measures, tables, columns, relationships) | [Modify an Existing Model](#workflow-modify-an-existing-model)                       |
| Write or refactor DAX code                                                      | [Modify an Existing Model](#workflow-modify-an-existing-model)                       |
| Improve DAX query or measure performance                                        | [Optimize DAX Performance](#workflow-optimize-dax-performance)                       |
| Analyze a Power BI Performance Analyzer JSON export                             | [Analyze Performance Analyzer JSON](#workflow-analyze-performance-analyzer-json)     |
| Analyze semantic model against best practices                                   | [Analyze Best Practices](#workflow-analyze-best-practices)                           |
| Prepare a semantic model for AI consumption (Copilot / Data Agents)             | [Semantic Model AI Readiness](#workflow-semantic-model-ai-readiness)                 |
| Deploy a model to a Fabric workspace                                            | [Deploy to Fabric](#workflow-deploy-to-fabric)                                       |
| Refresh a semantic model                                                        | [Refresh Semantic Model](#workflow-refresh-semantic-model)                           |
| Configure data sources, parameters, or permissions                              | [Manage Semantic Model in Fabric](#workflow-manage-semantic-model-in-fabric)         |
| Bind a semantic model to a Fabric connection (or unbind)                        | [Bind Semantic Model to a Connection](#workflow-bind-semantic-model-to-a-connection) |
| Export / Get semantic model definition as PBIP                                  | [Export to PBIP](#workflow-export-to-pbip)           |

## Table of Contents

Load these references on demand when a workflow step requires them. Do not load all at once.

| Topic                            | Reference                                                                          | When to load                                                                                |
| -------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Modeling Best Practices          | [modeling-guidelines.md](./references/modeling-guidelines.md)                      | Before creating or editing any model                                                        |
| Naming Conventions               | [naming-conventions.md](./references/naming-conventions.md)                        | When naming or renaming tables, columns, measures                                           |
| Direct Lake Modeling             | [direct-lake-guidelines.md](./references/direct-lake-guidelines.md)                | When model connects to OneLake                                                              |
| TMDL Editing                     | [tmdl-guidelines.md](./references/tmdl-guidelines.md)                              | Before generating or editing any TMDL file                                                  |
| PBIP Projects                    | [pbip.md](./references/pbip.md)                                                    | When working with PBIP folders                                                              |
| DAX Language                     | [dax-guidelines.md](./references/dax-guidelines.md)                                | When writing or reviewing any DAX code                                                      |
| Metadata Discovery (DAX INFO functions) | [metadata-discovery.md](./references/metadata-discovery.md)                 | When discovering model metadata via DAX INFO functions (see [Workflow: Discover Semantic Model Metadata](#workflow-discover-semantic-model-metadata)) |
| DAX Performance Decision Guide   | [dax-perf-decision-guide.md](./references/dax-perf-decision-guide.md)              | Start here when optimizing DAX                                                             |
| DAX Performance Pattern Catalog  | [dax-perf-patterns.md](./references/dax-perf-patterns.md)                          | Load on demand after the decision guide identifies candidate patterns                       |
| Performance Analyzer JSON        | [performance-analyzer-guidelines.md](./references/performance-analyzer-guidelines.md) | When working with a Performance Analyzer JSON file                                          |
| Semantic Model AI Readiness                | [semantic-model-ai-readiness.md](./references/semantic-model-ai-readiness.md)                          | When preparing a model for Copilot or Data Agents                                           |
| Semantic Model REST API          | [semantic-model-rest-api.md](./references/semantic-model-rest-api.md)              | When using `az rest` for TMDL CRUD, refresh, parameters, permissions, or property retrieval |
| Connection Binding               | [connection-binding.md](./references/connection-binding.md)                        | When binding/unbinding a semantic model to a Fabric data connection (gateway, cloud, VNet, automatic, none) |
| Finding Workspaces/Items         | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | When resolving workspace/item IDs                                                           |
| Fabric Control-Plane API         | [COMMON-CLI.md](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest)   | When using `az rest` patterns, LRO, pagination                                              |
| Authentication                   | [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes)                 | When authenticating with `az login`                                                         |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Definition Envelope              | [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md#semanticmodel)    | When building TMDL definition payloads                                                      |
| Examples                         | [Examples](#examples)                                                              | Reference end-to-end walkthroughs. |

---

## Tool Selection Priority

Priority order (highest first):

1. **Tier 1 — `powerbi-modeling-mcp` MCP is registered** -> Use MCP for authoring (new or edit) operations against the model from any source: Power BI Desktop, Fabric workspace, or local PBIP folder. MCP is the most reliable and full-featured way to edit semantic models, with immediate effect on the live model and no risk of TMDL desync.

   **Important:** In case of dynamic search tools is available (e.g. `tool_search_tool_regex`) search for an available MCP server matching the pattern `powerbi-modeling-mcp`.

   **This includes BOTH writes AND reads/inspection.**
   - To inspect or verify changes -> use the corresponding MCP operations (List / Get).
   - **Anti-pattern:** opening, `view`-ing, `glob`-ing or otherwise reading TMDL files (`*.tmdl`) while MCP is connected. The MCP-loaded model is the source of truth - the on-disk TMDL is stale. The only exceptions is when the user explicitly asks to work with the TMDL files.

2. **Tier 2 — MCP not registered + PBIP folder or Fabric workspace** -> Edit TMDL files directly. Load [tmdl-guidelines.md](./references/tmdl-guidelines.md) and [pbip.md](./references/pbip.md). When the source is a Fabric workspace, use `az rest` to round-trip the TMDL (load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md)): `getDefinition` -> edit TMDL locally -> `updateDefinition`.

**Fallback — none of the above available (e.g., Power BI Desktop with no PBIP and no MCP)** -> STOP. The agent cannot author the model in this configuration. Instruct the user to either (a) install and register the `powerbi-modeling-mcp` MCP server, or (b) save the PBIX as a PBIP project, then restart the workflow.

> **All workflows below are tool-agnostic.** Workflow steps describe the *intent* (connect, create, edit, save, deploy, refresh). The tool used to perform each step is determined here. Always select the highest-priority tool available for the current environment; do not mix tools when a higher-priority option works. Some workflows OVERRIDE this default priority, always check the workflow's own tool-selection rules before defaulting to Tier 1.

### Connecting to a Semantic Model

A semantic model can live in three locations. Resolve the connection per [Tool Selection Priority](#tool-selection-priority):

- **Power BI Desktop**: Locate the running Power BI Desktop instance and connect to its local model.
- **Fabric workspace**: First, find the workspace and semantic model using the [Finding Workspaces and Items](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) pattern: list workspaces to resolve the workspace ID by name, then list items of type `SemanticModel` in that workspace to resolve the model ID by name. Then connect to the model (live) or export its TMDL definition for local editing.
- **PBIP project**: Connect to the `[Name].SemanticModel/definition` folder. Load [pbip.md](./references/pbip.md) to understand the PBIP folder structure - only load the `[Name].SemanticModel/definition` folder that includes the TMDL code.

### Saving Changes to a Semantic Model

How changes are persisted depends on where the model lives and which tool tier (per [Tool Selection Priority](#tool-selection-priority)) is in use:

**Live connection (Tier 1 - MCP against Desktop or Fabric workspace):**

- Changes are applied immediately as each operation executes against the live model. No explicit save step is needed.
- **PBIP project (live via MCP)**: Serialize the model back to the `[Name].SemanticModel/definition` folder at the end of the session. If the PBIP folder does not exist yet, follow [Export to PBIP](#workflow-export-to-pbip) to create the full structure first.

**Local TMDL editing (Tier 2 - direct file edits or `az rest` round-trip):**

- **PBIP project**: Changes are already written to the TMDL files during editing. No additional save step is needed.
- **Fabric workspace**: Changes were made to local TMDL files exported from the service. Re-deploy the model (load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md) for the `updateDefinition` flow) to push changes back to the workspace.

---

## Workflow: Create new Semantic Model

**When this applies:** User asks to create a new semantic model from scratch.

Steps:

1. **Gather requirements** - interview the user until both reach a shared understanding of: purpose of the model, data source connection details and schemas, and key business entities/facts. **If data source information is not available, STOP and use `ask_user`. Do not guess or fabricate.**
2. **Determine storage mode** - data source is Fabric OneLake -> **Direct Lake**; otherwise default to **Import**. Only use **DirectQuery** when the user explicitly asks for it.
3. **Design star schema** - identify fact and dimension tables and relationship keys.
   - If fact table includes date field(s), create a separate date dimension table and link it to the fact with a relationship. If not explicitly requested, use PowerQuery/M partition instead of DAX calculated table.
4. **Load applicable guidelines** - **MANDATORY: load [modeling-guidelines.md](./references/modeling-guidelines.md) before building any object** (including the Tier 1 MCP path below); also load [direct-lake-guidelines.md](./references/direct-lake-guidelines.md) if Direct Lake. Don't build from memory.
5. **Build** - follow [Tool Selection Priority](#tool-selection-priority): **prefer the modeling MCP to build the whole model when one is available; otherwise use the TMDL code-edit path.** Create an empty database (compatibility level 1702+), then for each table follow the execution order from [Modify an Existing Model](#workflow-modify-an-existing-model) (partitions -> columns -> relationships -> measures). Storage-mode specifics:
   - **Import / DirectQuery** - create M parameters for the data source (`Server`, `Database`, ...) and reference them in partition M code; ensure proper `dataType` and `sourceColumn` mapping on columns.
   - **Direct Lake** - create a shared named expression for the Direct Lake connection using the `AzureStorage.DataLake` connector; use `EntityPartitionSource` with `directLake` mode mapped to the lakehouse table columns.

   > **Build the whole model in one pass, then deploy once.** Add every table, column, relationship and measure before deploying - don't deploy a partial model and edit-redeploy. On the MCP path, keep the model in the session end to end.
6. **Deploy or save** - Fabric workspace available -> [Deploy to Fabric](#workflow-deploy-to-fabric); otherwise -> [Export to PBIP](#workflow-export-to-pbip). See [Saving Changes to a Semantic Model](#saving-changes-to-a-semantic-model). Deploy through the same path you built with.
7. **Validate** - run [Validation Checklist](#validation-checklist).

---

## Workflow: Discover Semantic Model Metadata

**When this applies:** User asks to inspect, list, or discover the model's structure - tables, columns, measures, relationships, hierarchies, partitions, roles, or storage internals. Also used internally by other workflows ([Modify](#workflow-modify-an-existing-model), [Analyze Best Practices](#workflow-analyze-best-practices), [AI Readiness](#workflow-semantic-model-ai-readiness)) to inventory the model before editing.

> **Scope:** This workflow covers **metadata** discovery only. To answer natural-language/data questions against the model, use the `FabricIQ` skill instead.

Pick a discovery method (highest priority first):

1. **`powerbi-modeling-mcp` TOM inspection (List / Get)** - the default when `powerbi-modeling-mcp` is registered and connected to the target model **with Write access**. It returns the structured object model directly and stays in sync with pending edits, so it is preferred while authoring.

2. **DAX `INFO` functions** - query the model's `INFO.VIEW.*` / `INFO.*` metadata rowsets. **MANDATORY: before writing or running ANY `INFO`-function DAX, you MUST load [metadata-discovery.md](./references/metadata-discovery.md) first**. Do NOT compose `INFO` queries from memory; load the reference and use its patterns. **Prioritize this method when any of the following is true:**
   - **You lack Write permission** on the model. `powerbi-modeling-mcp` operations require Write access; with Read or Build access, use `INFO` functions.
   - **`powerbi-modeling-mcp` is not registered or not available** in the current environment.
 
   Execute the `INFO`-function DAX through one of these tools (highest priority first):
   - **FabricIQ `ExecuteQuery`** - requires only **Read** permission on the model. Load the `FabricIQ` skill for artifact discovery (`DiscoverArtifacts`) and execution mechanics.
   - **`powerbi-modeling-mcp` `dax_query_operations`** - requires **Write** permission. Use this when the modeling MCP is already connected with Write access.

> **Do NOT use FabricIQ `GetSemanticModelSchema` for authoring metadata discovery** - it is a data-consumption tool that can return stale metadata and miss recent edits. Even when FabricIQ is available, always use the `INFO` functions (via `ExecuteQuery`); they query the live model.

Start narrow: run the scope-estimation and `INFO.VIEW.*` queries first, then project/filter to only the objects relevant to the task (see [metadata-discovery.md](./references/metadata-discovery.md)).

---

## Workflow: Modify an Existing Model

**When this applies:** User asks to add/edit/remove measures, tables, columns, relationships, write DAX code, refactor with UDFs, or edit TMDL directly.

Steps:

1. **Connect & discover** - per [Connecting to a Semantic Model](#connecting-to-a-semantic-model) and [Discover Semantic Model Metadata](#workflow-discover-semantic-model-metadata). List tables, relationships, existing measures, and identify storage mode (it dictates which guidelines apply).
2. **Load applicable guidelines** - [modeling-guidelines.md](./references/modeling-guidelines.md) always; [direct-lake-guidelines.md](./references/direct-lake-guidelines.md) if Direct Lake; [tmdl-guidelines.md](./references/tmdl-guidelines.md) when editing TMDL directly; [dax-guidelines.md](./references/dax-guidelines.md) for any DAX changes (includes UDF refactoring).
3. **Plan changes** - identify exactly what to add, modify, or remove. Check for naming conflicts and duplicates.
4. **Execute** in correct order:
   - **Adding tables** - partitions -> columns -> relationships -> measures.
   - **Adding relationships** - ensure key columns exist on both sides with matching data types;
   - **Adding measures** - verify referenced columns/tables exist;
5. **Save & validate** - per [Saving Changes to a Semantic Model](#saving-changes-to-a-semantic-model) and [Validation Checklist](#validation-checklist).

---

## Workflow: Optimize DAX Performance

**When this applies:** User asks to improve DAX query performance, diagnose slow measures, or optimize calculations.

> **Hard requirement:** Requires a trace-capable client (MCP preferred))

Load [dax-perf-decision-guide.md](./references/dax-perf-decision-guide.md) first and follow the framework defined there. Load [dax-perf-patterns.md](./references/dax-perf-patterns.md) only when applying candidate optimization patterns. The framework includes:

1. Tier model for categorizing optimization effort
2. Trace diagnostics to identify bottlenecks
3. Pattern catalog with candidate optimization techniques to test and validate

---

## Workflow: Analyze Performance Analyzer JSON

**When this applies:** User asks to inspect a Power BI Performance Analyzer JSON export, diagnose slow report visuals, rank visual timings, or review captured DAX or DirectQuery evidence.

Load [performance-analyzer-guidelines.md](./references/performance-analyzer-guidelines.md) before starting and follow its analysis workflow, reporting contract, and validation checklist.

Steps:

1. **Validate the capture** - resolve the local `.json` file, parse it with a structured JSON parser, identify the export schema, and stop with a specific error when the file is malformed or unsupported.
2. **Normalize the evidence** - extract visual identity, page grouping, timing categories, DAX text, and DirectQuery text without double counting repeated events.
3. **Calculate and rank** - calculate the canonical metrics from the reference and rank visuals by actionable duration. Keep `Other` visible as synchronization or queueing evidence, but exclude it from actionable ranking.
4. **Diagnose** - assess DAX, DirectQuery, rendering, parameter evaluation, page density, legacy Card usage, capture quality, and relative outliers using only evidence supported by the export.
5. **Report** - create the complete HTML, Markdown, JSON, and CSV package under `./powerbi_performance_report`, relative to the execution working directory. Do not modify the source report or semantic model.
6. **Validate and hand off** - run the reference validation checklist. When DAX materially contributes and trace-capable model access is available, continue with [Optimize DAX Performance](#workflow-optimize-dax-performance). Route broader modeling concerns to [Analyze Best Practices](#workflow-analyze-best-practices), and treat DirectQuery source recommendations as investigation steps until source-side evidence validates them.

---

## Workflow: Analyze Best Practices

**When this applies:** User asks to review, audit, or analyze a semantic model against best practices.

Steps:

1. **Connect & inventory** - per [Connecting to a Semantic Model](#connecting-to-a-semantic-model) and [Discover Semantic Model Metadata](#workflow-discover-semantic-model-metadata). Capture all tables, columns, relationships, measures, and storage mode.
2. **Load applicable guidelines** - [modeling-guidelines.md](./references/modeling-guidelines.md) always; [direct-lake-guidelines.md](./references/direct-lake-guidelines.md) if Direct Lake; [naming-conventions.md](./references/naming-conventions.md) when assessing naming; [dax-guidelines.md](./references/dax-guidelines.md) when assessing DAX.
3. **Evaluate** - compare the model against the loaded guidelines (star schema, naming, relationship cardinality and cross-filter, explicit measures with `formatString`, column data types and `sourceColumn`, hidden FK columns, calculated-column-vs-measure choices, Direct Lake constraints, etc.).
4. **Present findings** grouped by severity (critical, recommended, optional). For each item state the rule violated and the proposed fix. Wait for user approval.
5. **Apply approved fixes** via [Modify an Existing Model](#workflow-modify-an-existing-model).
6. **Save & validate** - per [Saving Changes to a Semantic Model](#saving-changes-to-a-semantic-model) and [Validation Checklist](#validation-checklist).

---

## Workflow: Semantic Model AI Readiness

**When this applies:** User asks to make a semantic model ready for Microsoft Fabric Copilot, a Power BI Data Agent, or any conversational BI experience. Triggers include "Copilot readiness", "AI readiness", "Prep for AI", "prepare model for Copilot".

Load [semantic-model-ai-readiness.md](./references/semantic-model-ai-readiness.md) before starting.

Steps:

1. **Confirm scope & gather context** - via `ask_user`, confirm consumption mode (reports only / conversational BI / both) and model stability per the *When to Apply* section. Collect business context (process, key metrics, common natural-language questions, vocabulary). Do not invent.
2. **Connect & inventory** - per [Connecting to a Semantic Model](#connecting-to-a-semantic-model). Capture model contents and the source location (PBIP / Fabric workspace / Desktop-only).
3. **Evaluate & route** - walk the [Readiness Checklist](./references/semantic-model-ai-readiness.md#readiness-checklist) in order; for each gap, classify the fix per [Editing Capability](./references/semantic-model-ai-readiness.md#editing-capability) (agent-editable TOM metadata vs AI-specific artifacts the user configures in the Power BI "Prep data for AI" UI).
4. **Present findings** grouped by severity, each tagged with routing (agent-applicable vs user-action-required). Wait for approval.
5. **Apply approved changes** - apply TOM metadata fixes via [Modify an Existing Model](#workflow-modify-an-existing-model); for AI instructions, AI Data Schema, and Verified Answers, instruct the user to configure them in the Power BI "Prep data for AI" UI and, only if the user agrees, offer suggestions per the readiness reference; Desktop-only PBIX -> instruct user.
6. **Save, validate, recommend live testing** - per [Saving Changes to a Semantic Model](#saving-changes-to-a-semantic-model) and [Validation Checklist](#validation-checklist); advise the user to test representative natural-language prompts in Copilot or the Data Agent and iterate.

---

## Workflow: Export to PBIP

**When this applies:** User asks to export or save a semantic model to a PBIP project folder, or there is no Fabric workspace available to deploy to (e.g., after building a model in-memory).

> **Key fact:** Exporting a model only produces the TMDL definition files. It does NOT create the surrounding PBIP folder structure (Report folder, `definition.pbism`, `definition.pbir`, `.pbip` entry point). The agent must scaffold these before exporting, otherwise the result cannot be opened in Power BI Desktop.

Load [pbip.md](./references/pbip.md) before starting and follow the PBIP folder structure defined there.

Steps:

1. **Determine target** - via `ask_user`, get the target folder path and the semantic model name. If only a folder is provided, use the model's database name as the semantic model folder name.
2. **Scaffold the PBIP structure** - per [pbip.md](./references/pbip.md), ensure `<Name>.SemanticModel/` (with `definition/` and `definition.pbism`), `<Name>.Report/` (with `definition/` and `definition.pbir` using a `byPath` reference), and `<Name>.pbip` exist. Create any missing piece.
3. **Export TMDL** into `<Name>.SemanticModel/definition/`, per [Tool Selection Priority](#tool-selection-priority):
   - **Tier 1 (MCP)** - use the MCP export/save operation against the live model.
   - **Tier 2 (Fabric workspace, no MCP)** - call `getDefinition` (load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md)) and write the returned parts.
   - **Local TMDL files already on disk** - copy or move them into the `definition/` folder.
4. **Validate** - confirm the `definition/` folder contains at minimum `model.tmdl` and table `.tmdl` files; confirm `definition.pbism`, `<Name>.Report/definition.pbir` (with correct `byPath` to `../<Name>.SemanticModel`), and `<Name>.pbip` exist and reference each other correctly.

---

## Workflow: Deploy to Fabric

**When this applies:** User asks to deploy or publish a semantic model to a Fabric workspace.

> **Hard rule — this workflow OVERRIDES the default [Tool Selection Priority](#tool-selection-priority).** Do not default to MCP just because it is available. The deployment path is determined by the **source of the model**, not by which tools are connected. If the source is PBIP/TMDL files on disk, you **MUST** use the Fabric REST API even when an MCP session is active.

Decision tree (pick exactly one — top-down, first match wins):

1. **Are there PBIP / TMDL files on disk that need to be deployed?**
   -> **YES — use Fabric REST API.** Call `az rest` with `createItemWithDefinition` (new model) or `updateDefinition` (existing model). Load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md).
   - Rationale: deploying TMDL files directly via the Fabric API is more reliable, faster, and avoids unnecessarily loading the model into MCP only to push it back out.
   - **Do NOT** open the PBIP in MCP first and then deploy via MCP. That is an explicit anti-pattern for this workflow.
2. **Is the model already loaded in a live MCP session** (e.g., just built in-memory, or currently being edited via MCP) **with no PBIP/TMDL files involved?**
   -> Use MCP tool to deploy with the target workspace and semantic model name.
3. **Is the model live in Power BI Desktop with no PBIP saved?**
   -> Use MCP Deploy if MCP is connected to Desktop. If MCP is not available, instruct the user to save as PBIP first, then restart this workflow at step 1.

Verify deployment succeeded by listing workspace items of type `SemanticModel`.

> **Deploy exactly once; the deploy is NOT idempotent.** A retried deploy creates a *second* model with the same name, after which the deploy fails with `There are multiple datasets named '<name>'`. If you hit that error, do NOT retry blindly: list the workspace's semantic models, **delete every duplicate with that name**, then deploy once from the clean state. If deploying a model that may already exist, delete the existing same-named model(s) *before* the single deploy.

---

## Workflow: Refresh Semantic Model

**When this applies:** User asks to refresh data in a semantic model.

Refresh is only possible when working against a live model in Desktop or Fabric Service. If working with local TMDL files, deploy the model first.

Trigger a refresh per [Tool Selection Priority](#tool-selection-priority):

- **Power BI Desktop**: Tier 1 (MCP) only — use the MCP Refresh operation.
- **Fabric Service**: Tier 1 (MCP Refresh operation) or fallback to the Power BI Enhanced Refresh API (load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md)).

If the refresh fails with a credential error, **stop immediately** and instruct the user to configure the data source connections manually in Power BI Service. Do not attempt to retry or work around credential errors programmatically.

---

## Workflow: Manage Semantic Model in Fabric

**When this applies:** User asks to configure data sources, update parameters, or manage permissions for a semantic model in Fabric Service.

> **Hard rule — this workflow OVERRIDES the default [Tool Selection Priority](#tool-selection-priority).** Do not default to MCP (Tier 1) prefer using `az rest` and REST APIs.

### Data Sources & Parameters

Get/update data sources and parameters via Power BI REST API. Load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md#4-data-sources--parameters-power-bi-datasets-api).

### Permissions

List/grant/update dataset user permissions via Power BI REST API. Load [semantic-model-rest-api.md](./references/semantic-model-rest-api.md#5-permissions-power-bi-datasets-api).

### Connection Binding

Load [connection-binding.md](./references/connection-binding.md) and follow it. The reference covers prerequisites, the `bindConnection` endpoint, the discover -> match -> bind -> validate steps, all `connectivityType` values, the unbind pattern, and troubleshooting.

Key rules (full details in the reference):

- Use the Fabric **Bind Semantic Model Connection** REST API (supersedes the legacy Power BI `BindToGateway`).
- **One bind request per data source reference** - the API does not support bulk binding.
- Discover the model's data source references via `List Item Connections`, then match `connectionDetails` against `List Connections` to find the target `id`. Create a connection first if no match exists.
- Validate by re-listing item connections and triggering a refresh.

---

## Validation Checklist

Run after any model creation or modification:

**Always (works with PBIP, Desktop, and Fabric Service):**

1. **Check the PBIP structure** - if the model is sourced from a PBIP folder, ensure the folder structure and files are correct (see [pbip.md](./references/pbip.md)).
2. **Verify against modeling guidelines** - re-check every change against [modeling-guidelines.md](./references/modeling-guidelines.md) (and [direct-lake-guidelines.md](./references/direct-lake-guidelines.md) for Direct Lake models).

**Only when connected to an Analysis Services database (Power BI Desktop or Fabric Service):**

3. **Test new measures** - for each new measure, run a simple DAX query to validate it returns expected results (e.g., `EVALUATE { [Measure Name] }`). Skip this step when working with local TMDL/PBIP files only.
4. **Test table refresh** - when new tables were created, trigger a refresh to verify that partitions, data source expressions, and column mappings are correct. A failed refresh typically indicates mismatched `sourceColumn` names, invalid M expressions, or incorrect Direct Lake entity references. Skip this step when working with local TMDL/PBIP files only.

If any check fails, fix the issue and re-run validation.

---

## Must/Prefer/Avoid

### MUST

- **Understand the data source schema before starting** - analyze source tables, columns, and data types before designing or modifying the model.
- **Follow modeling guidelines** - load [modeling-guidelines.md](./references/modeling-guidelines.md) before creating or editing any model; apply star schema design, naming conventions, and column/measure rules
- **Follow [Tool Selection Priority](#tool-selection-priority)** - always pick the highest-priority tool tier available for the current environment; do not mix tiers when a higher-priority option works

### PREFER

- **Star schema over snowflake or flat tables** - denormalized dimensions with single-column relationship keys
- **Consistency with existing model patterns** - when editing an existing model, match its naming conventions and structure rather than imposing new ones
- **TMDL format over TMSL** - text-based, diff-friendly, preferred for Fabric
- **Validate after changes** - use [Workflow: Discover Semantic Model Metadata](#workflow-discover-semantic-model-metadata) to confirm objects landed.

### AVOID

- **Hardcoded workspace/item IDs** - resolve dynamically via API
- **Reading TMDL files when MCP is connected** - `view`/`glob` on `*.tmdl` while a Tier 1 MCP session is live is an anti-pattern (see [Tool Selection Priority](#tool-selection-priority)).
- **Hand-authoring TMDL files when MCP is registered** - using `create`/`edit`/file-write tools to scaffold `model.tmdl`, `database.tmdl`, `relationships.tmdl`, or `tables/*.tmdl` is a Tier 1 anti-pattern, including for brand-new models. Build and export via MCP tools.

### DENY

- **Manage RLS/OLS role membership** - do not propose REST calls, `az rest` URLs, MCP operations, or TMDL changes to add/remove users or groups from a security role. Refuse the request as out-of-scope here and redirect the user to the Power BI portal.

---

## Examples

> **Scope note** — examples use `az rest` for discovery to resolve ID's and discover Fabric metadata (see [COMMON-CLI.md § Finding Workspaces and Items](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)). Authoring of the semantic model definition is routed through [Tool Selection Priority](#tool-selection-priority): Tier 1 MCP `powerbi-modeling-mcp` when available, Tier 2 TMDL editing via `getDefinition` / `updateDefinition` otherwise.

### Example 1: Modify an Existing Semantic Model

**Prompt**: "Create base measures for all aggregable columns in the semantic model **Sales** in workspace **Marketing**."

**Agent response** - follows [Workflow: Modify an Existing Model](#workflow-modify-an-existing-model).

1. **Discover IDs** via `az rest`.
2. **Connect to the model** per [Connecting to a Semantic Model](#connecting-to-a-semantic-model) and [Tool Selection Priority](#tool-selection-priority). With `powerbi-modeling-mcp` registered, connect MCP directly to the Fabric workspace model (Tier 1). Otherwise fall back to Tier 2 (`getDefinition` -> edit TMDL locally).
3. **Inspect & plan** - list tables and columns via the active tool tier; identify aggregable columns (numeric, not foreign keys, not hidden surrogate IDs) and decide on `SUM` / `AVERAGE` / `MIN` / `MAX` per column following [modeling-guidelines.md](./references/modeling-guidelines.md) and [naming-conventions.md](./references/naming-conventions.md). Load [dax-guidelines.md](./references/dax-guidelines.md) before writing DAX.
4. **Add measures** per [Workflow: Modify an Existing Model](#workflow-modify-an-existing-model).
   - **Tier 1 (MCP)**: call tool create for each new measure with `expression`, `formatString`, and target table. Do not hand-author TMDL.
   - **Tier 2 (no MCP)**: edit the table's `.tmdl` file directly and round-trip via `updateDefinition` REST API.
5. **Save & validate** per [Saving Changes to a Semantic Model](#saving-changes-to-a-semantic-model).

---

### Example 2: Create a New Semantic Model from a Fabric Lakehouse

**Prompt**: "Create a new Power BI semantic model in workspace **Marketing**, using the **SalesLakehouse** in the same workspace as the data source."

**Agent response** - follows [Workflow: Create new Semantic Model](#workflow-create-new-semantic-model).

1. **Discover workspace + lakehouse IDs** via `az rest`.
2. **Discover lakehouse schema** - list tables and columns via the Lakehouse OneLake APIs or the SQL Endpoint of the lakehouse. Capture table names, column names, and data types - these drive semantic model table, column definitions and partition metadata.
3. **Select tool tier** per [Tool Selection Priority](#tool-selection-priority): prefer Tier 1 (`powerbi-modeling-mcp`) for the full build. Tier 2 (PBIP/TMDL scaffolding then deploy) only if MCP is not registered.
4. **Build the model** following [Workflow: Create new Semantic Model](#workflow-create-new-semantic-model) - data source is OneLake so the storage mode is **Direct Lake** (load [direct-lake-guidelines.md](./references/direct-lake-guidelines.md) and [modeling-guidelines.md](./references/modeling-guidelines.md)). Design a star schema from the lakehouse tables, then:
   - Create the empty database.
   - Create one shared named expression for the lakehouse connection.
   - For each table: add `EntityPartitionSource` (mode `directLake`) -> columns mapped to lakehouse columns -> relationships -> measures.
5. **Deploy** per [Workflow: Deploy to Fabric](#workflow-deploy-to-fabric):
6. **Validate** per the [Validation Checklist](#validation-checklist) - confirm the model appears in the workspace and trigger an initial refresh to verify Direct Lake column mappings resolve.

---

### Example 3: Bind a Semantic Model to a Fabric Connection

**Prompt**: "Bind semantic model **Sales** in workspace **Marketing** to the **sql-prod** connection."

**Agent response** - follows [Workflow: Manage Semantic Model in Fabric § Connection Binding](#connection-binding). **No MCP** - this workflow overrides [Tool Selection Priority](#tool-selection-priority) and is REST-only.

1. **Discover workspace + model IDs** via `az rest`.
2. **Discover the target connection** in Fabric by matching the server name:

   ```bash
   SERVER="sql-prod"
   CONN_ID=$(az rest --method get --resource "https://api.fabric.microsoft.com" \
     --url "https://api.fabric.microsoft.com/v1/connections" \
     --query "value[?connectionDetails.path | contains(@, '$SERVER')] | [0].id" -o tsv)
   ```

   If no connection matches, **stop** and instruct the user to create one first per [connection-binding.md](./references/connection-binding.md).
3. **Execute the bind** per [Workflow: Manage Semantic Model in Fabric § Connection Binding](#connection-binding) - load [connection-binding.md](./references/connection-binding.md) and follow the discover -> match -> bind -> validate flow:
   - List the model's data source references (`List Item Connections`).
   - For each reference whose `connectionDetails` matches `$CONN_ID`, call the Fabric `bindConnection` endpoint **one request per data source reference** (no bulk binding).
4. **Validate** - re-list item connections to confirm the binding, prompt the user to trigger a refresh per [Workflow: Refresh Semantic Model](#workflow-refresh-semantic-model). Credential errors -> stop and direct the user to the Service portal (per TROUBLESHOOTING).

---

## TROUBLESHOOTING

| Symptom                              | Fix                                                                                                                   |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| MCP connection failure               | Fall back to TMDL editing (see Tool Selection Priority). Inform the user about the fallback.                          |
| TMDL validation errors               | Read error details, fix syntax, re-validate. Load [tmdl-guidelines.md](./references/tmdl-guidelines.md).              |
| `403 Forbidden` / `identity None`    | User needs Contributor+ role - stop immediately. Do not retry.                                                        |
| `401 Unauthorized`                   | Correct the `--resource` audience once (see [semantic-model-rest-api.md](./references/semantic-model-rest-api.md)). If it persists after the audience is right, it is missing permissions - stop and tell the user. Do not retry-loop. |
| `202 Accepted` but no result         | Poll LRO to completion.                                                                                               |
| Parts missing after updateDefinition | Must include ALL parts - modified + unmodified.                                                                       |
| Refresh credential error             | Direct user to configure in Service portal. Do not retry.                                                             |
| DAX errors in measures               | Check column/table name references (case-sensitive). Verify referenced objects exist.                                 |
| Deployment failure                   | Check workspace permissions, model compatibility level, and Direct Lake expression source references.                 |
| Missing data source                  | Verify M parameters or named expressions are correctly defined.                                                       |
