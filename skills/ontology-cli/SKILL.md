---
name: ontology-cli
description: "Manages Microsoft Fabric Ontology items: authors legacy V1 entity/relationship definitions and answers questions for new-experience (V2) Ontologies through ask_ontology. Use for Ontology item operations or grounded questions; V2 authoring/upgrades and V1 queries are unsupported. Power BI data questions use fabriciq, report authoring powerbi-report-cli, and model/DAX changes semantic-model-authoring."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: ontology-cli` (`az rest`: `--headers "x-ms-fabric-skill=ontology-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: use `ontology-cli` for operations on an Ontology item and questions grounded in that Ontology. Natural-language data questions over existing Power BI reports/models are `fabriciq`; report creation, editing, publishing, or rebinding is `powerbi-report-cli`; semantic-model or DAX authoring is `semantic-model-authoring`. Naming an Ontology as a report's data source does not move report authoring into this skill.
> 4. **Consumption runs through the Ontology Agent MCP server, never around it.** Do not decode an ontology definition to hand-compose KQL / T-SQL / Spark SQL, and do not delegate ontology data questions to `eventhouse-cli` / `sqldw-cli` / `spark-cli`. That path loses the agent's grounding and validation and is not metered.
> 5. **Natural-language consumption supports only new-experience (V2) Ontologies.** Call `tools/list` first. If `ask_ontology` is absent, stop and tell the user that V1 natural-language queries are unsupported and the Ontology must be upgraded or recreated in the new experience **outside this skill's authoring flow**. Never fall back to `search_ontology`.
> 6. **Authoring is legacy V1-only.** The JSON `EntityTypes/.../definition.json` item-definition flow below cannot create, convert, or upgrade a new-experience (V2) Ontology. Do not route a V2 upgrade/recreation request into `authoring`.
> 7. **Kusto bindings use the parent Eventhouse item ID, never the KQL database ID.** Validate the staged binding against discovered source metadata before presenting an authoring preview; unresolved or mismatched source identities block the write.

# Ontology CLI Skill

This skill owns two explicit, non-convertible surfaces: legacy V1 JSON-definition authoring, and read-only questions over existing new-experience (V2) Ontologies through the Ontology Agent MCP endpoint. It does not upgrade V1 items to V2 or author V2 items.

It is a **mode dispatcher** and contains NO procedures. Pick the mode that matches the request from the table below, then **read the matching `references/<mode>.md` file end to end with your file-reading tool BEFORE issuing a single command**. That file holds the endpoints, payload shapes, templates and gotchas; acting without it produces wrong payloads and wrong results.

## Mode selection

| Mode | Use when the request ... | Example triggers | Read this first |
|---|---|---|---|
| `authoring` | creates or updates a **legacy V1** Ontology's JSON entity/relationship definitions or data bindings; V2 creation/upgrade is out of scope | create legacy ontology item, bind V1 entity type, add V1 relationship type, update legacy ontology definition | [references/authoring.md](references/authoring.md) |
| `consumption` | asks a question about an existing new-experience (V2) Ontology -- its data, entities, or rules -- or wants grounded runnable code generated from it | how many clinics are there, which treatment rooms are busiest, what entities exist, list the ontology rules, generate KQL from this ontology | [references/consumption.md](references/consumption.md) |

Consumption sub-references (read directly, not through chained links):
- [references/consumption/examples.md](references/consumption/examples.md): verified calls, worked examples and troubleshooting.
- [references/consumption/request-files.md](references/consumption/request-files.md): **read before preparing a PowerShell MCP request**; absolute payload paths and local JSON validation.

### Mode boundary rule

`consumption` is read-only. Any definition write goes through the authoring mode's preview-and-confirm flow -- never call `updateDefinition` from a consumption request.

If a request genuinely spans modes, handle them one at a time and read each reference before you start that part. If the mode is ambiguous after reading this table, ask one short clarifying question instead of guessing.

## Terminal write -- the step you must not skip

Reading the reference and planning the change is NOT completing the task. Each mutating mode ends with one state-changing call. If you did not issue it, nothing was persisted -- say so explicitly rather than reporting success.

| Mode | Terminal write |
|---|---|
| `authoring` | `createItem` (`POST /v1/workspaces/{ws}/items`) to create a legacy V1 Ontology, then `POST .../updateDefinition` to persist entity types, relationships and bindings. This cannot create or upgrade V2. |
| `consumption` | none -- this mode is read-only |

Before you report the task done, confirm the terminal call returned success and, where the reference documents a readback, read the artefact back to prove the change landed.

## Shared essentials (all modes)

Resolve the workspace and item first; every mode depends on it.

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** -- read before resolving any workspace or item id |
| Catalog Search | [COMMON-CORE.md](../../common/COMMON-CORE.md#catalog-search) | Request/response shape, `Catalog.Read.All` scope, 24 h indexing delay |
| Pagination Pattern | [COMMON-CLI.md](../../common/COMMON-CLI.md#pagination-pattern) | Catalog Search and item listings both page via `continuationToken` |
| Fabric Topology & Key Concepts | [COMMON-CORE.md](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Item types, workspaces, capacities |
| Environment URLs | [COMMON-CORE.md](../../common/COMMON-CORE.md#environment-urls) | Sovereign / non-public cloud hosts |
| Authentication & Token Acquisition | [COMMON-CORE.md](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Authentication Recipes | [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Core Control-Plane REST APIs | [COMMON-CORE.md](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Pagination, LRO polling, rate limiting |
| Gotchas & Troubleshooting | [COMMON-CLI.md](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |

## Rules

### MUST

- Select exactly one mode from the table above before doing anything else.
- Read `references/<mode>.md` end to end, as your FIRST tool call, before the first command of that mode. Read it ONCE, in a single full read: do not re-open it, do not grep it again, and do not page through it. You already have it.
- Apply the same read-once discipline to every other file you load, including nested `references/<mode>/*.md` sub-references and shared `common/*.md` files: open only the ones you actually need, read each ONCE end to end, and never grep or re-open one you already loaded.
- Resolve workspace and item ids by listing and filtering, never by guessing a GUID.
- In `consumption`, call `tools/list` before the first `tools/call`. Continue only when `ask_ontology` is present; otherwise report that V1 natural-language consumption is unsupported and stop without calling another ontology tool.
- Announce a mode switch explicitly when the request crosses a boundary.
- Treat the reference as instructions, never as the deliverable. After reading it, RUN the documented commands against the live workspace and report the real results. Quoting what the reference says instead of executing it does not answer the request.

### PREFER

- The narrowest mode that satisfies the request.
- Reading exactly ONE mode reference. Load a second only when the request genuinely spans modes, and say so before you do.
- Reporting the mode you chose in your first response so the user can correct you.

### AVOID

- Acting from this dispatcher alone -- it intentionally omits the operational detail.
- Answering with a summary of the reference instead of executing it.
- Re-reading or re-grepping a reference you already loaded; it costs turns and tokens.
- Mutating anything while in a read-only mode.
- Answering an ontology data question with a hand-composed source query instead of the Ontology Agent MCP (see CRITICAL NOTE 4).
- Loading a different skill for work this family already owns (see CRITICAL NOTES 3).

## Examples

| User request | Mode | Reference to read |
|---|---|---|
| "Using the ClinicOperations ontology, how many clinics are there?" | `consumption` | [references/consumption.md](references/consumption.md) |
| "Create a legacy V1 ontology item with Customer and Order entity types bound to the lakehouse." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Upgrade this V1 ontology to the new V2 experience." | out of scope | Explain that V2 upgrade/recreation is unavailable through this skill's authoring flow |
| "What entity types exist in the Sales ontology and how are they bound?" | `consumption` | [references/consumption.md](references/consumption.md) |
| "Generate Eventhouse-runnable KQL for appointments per practitioner from this ontology." | `consumption` | [references/consumption.md](references/consumption.md) |
