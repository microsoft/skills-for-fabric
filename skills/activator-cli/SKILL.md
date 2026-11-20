---
name: activator-cli
description: "Creates and inspects Fabric Activator (Reflex) alerts: rules, their data sources, conditions, and the Teams or email action they fire, plus decoding an existing ReflexEntities definition and reporting when rules fired (activation history). Choose it whenever someone wants to be told, or something done, when values cross a threshold. The pipeline delivering those values is eventstream-cli."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: activator-cli` (`az rest`: `--headers "x-ms-fabric-skill=activator-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: use `activator-cli` for every Fabric Activator / Reflex item — both authoring alert rules and inspecting existing alerts. The streaming topology that feeds an alert belongs to `eventstream-cli`, the KQL database behind it to `eventhouse-cli`, and Power BI report questions to `fabriciq`.

# Fabric Activator (Reflex) — CLI Skill

This one skill owns Fabric Activator / Reflex items: alert rules, their sources, their actions, and the `ReflexEntities.json` definition that holds them.

It is a **mode dispatcher** and contains NO procedures. Pick the mode that matches the request from the table below, then **read the matching `references/<mode>.md` file end to end with your file-reading tool BEFORE issuing a single command**. That file holds the endpoints, entity schemas, templates and gotchas; acting without it produces invalid `ReflexEntities.json` payloads and 400s.

The reference is needed to *act*, not to *ask*. If the request is under-specified and your next message will be a clarifying question with no Fabric call in it, ask it now and read the reference when you go on to act.

## Mode selection

| Mode | Use when the request ... | Example triggers | Read this first |
|---|---|---|---|
| `authoring` | creates, updates, configures or deletes an Activator item, rule, source or action | create an alert, create an activator, create a reflex, notify me when, let me know when, take action when, send me an email when, send a teams message when, run a pipeline when, update an alert, delete an alert | [references/authoring.md](references/authoring.md) |
| `consumption` | lists, inspects, decodes or explains existing Activators, rules, sources or actions, or reports when rules fired | show my alerts, what alerts do I have, list activators, inspect this alert, show me the rule, show me the source, get reflex definition, why does this alert fire, when did my alert fire, activation history, how often did this rule fire | [references/consumption.md](references/consumption.md); for when rules fired, [references/consumption/activation-history.md](references/consumption/activation-history.md) instead |

### Mode boundary rule

`consumption` is read-only. A request to create, update, configure or delete an Activator item, rule, source or action requires `authoring`: say so, read `references/authoring.md`, then proceed.

A pure GET / explain request stays in `consumption` — do not switch to `authoring` and do not mutate anything to answer it.

If a request genuinely spans modes, handle them one at a time and read each reference before you start that part. If the mode is ambiguous after reading this table, ask one short clarifying question instead of guessing.

## Terminal write — the step you must not skip

Reading the reference, decoding a definition and assembling entities is NOT completing the task. Authoring ends with one state-changing call. If you did not issue it, nothing was persisted — say so explicitly rather than reporting success.

| Mode | Terminal write |
|---|---|
| `authoring` | `POST /v1/workspaces/{ws}/reflexes` to create the item, `POST /v1/workspaces/{ws}/reflexes/{id}/updateDefinition` to persist rules, sources and actions, or `DELETE /v1/workspaces/{ws}/reflexes/{id}` to remove it. Building, stringifying or base64-encoding `ReflexEntities.json` is not the write. |
| `consumption` | none — this mode is read-only |

Before you report an authoring task done, confirm the terminal call returned an explicit success (HTTP `200`/`201`, or a terminal LRO success for a `202`), then read the definition back where the mode reference documents a readback. Power BI sources are the exception: public ALM export can reject an artifact that imported successfully, so an empty or unavailable readback is **not** proof the write failed — report the `updateDefinition` result and the readback limitation separately, per [references/authoring/powerbi-source.md](references/authoring/powerbi-source.md).

### Source validation gate (authoring only)

Before authoring any rule that references a signal, confirm the source is real: **resolve** it in the requested workspace only, **validate** that the requested column/field/property exists on it, and **observe** at least one representative row, event or sample carrying that signal.

Schema-only, zero-row, non-emitting or stale evidence is **missing source data**. When the source is missing, **stop and ask** which source and fields provide the signal — do not create a Reflex and do not call `updateDefinition` on an unrelated existing Activator or Eventstream to force-fit the request, and state plainly that no Activator / Reflex / Eventstream was created or updated. The only exception is an explicit instruction to author against a future / not-yet-emitting source, which you must state as an assumption.

Everything you need to run this gate is on this page. When the request already lacks the source mapping, threshold, recipients or action target, ask for them **first** — do not read `references/authoring.md`, and do not call a Fabric API, just to discover that the request is under-specified.

## Shared essentials (all modes)

Resolve the workspace and the Activator item first; every mode depends on it — list and filter by display name exactly as CRITICAL NOTES 1 and 2 describe. That recipe is self-contained and is all you need to start.

The table below is **optional background** living in the shared `common/` docs. Open a row only when you actually need that detail. If `common/` is not present in your environment, say so in one line and continue with the mode reference — **never glob, list or search the filesystem looking for it.**

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | Pagination and JMESPath filtering detail |
| Fabric Topology & Key Concepts | [COMMON-CORE.md](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Item types, workspaces, capacities |
| Authentication & Token Acquisition | [COMMON-CORE.md](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Authentication Recipes | [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Core Control-Plane REST APIs | [COMMON-CORE.md](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Pagination, LRO polling, rate limiting |
| Fabric Item Definitions | [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Base64-encoded `parts` structure |
| Gotchas & Troubleshooting | [COMMON-CLI.md](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |

Activator uses the `reflexes` collection, not the generic `items` collection: `/v1/workspaces/{workspaceId}/reflexes[/{reflexId}]`.

## Rules

### MUST

- Select exactly one mode from the table above before doing anything else.
- Read `references/<mode>.md` end to end, as your FIRST tool call, before the first command of that mode. A reply that only asks a clarifying question, and issues no Fabric call, does not need it yet.
- Pass `--resource https://api.fabric.microsoft.com` on every `az rest` call — without it the token audience is wrong and the call returns 401.
- Call `getDefinition` as a **POST** with `--body '{}'`, then Base64-decode the `ReflexEntities.json` part before inspecting it; a GET returns 405 and an omitted body can return 411.
- Poll the `Location` header when `create`, `getDefinition` or `updateDefinition` returns 202.
- Resolve workspace and Activator ids by listing and filtering, never by guessing a GUID.
- Announce a mode switch explicitly when the request crosses a boundary.
- Treat the reference as instructions, never as the deliverable. After reading it, RUN the documented commands against the live workspace and report the real results.
- In `authoring`, clear the [source validation gate](#source-validation-gate-authoring-only) before you author a rule, and build `ReflexEntities.json` with Python `json.dumps()` — PowerShell's `ConvertTo-Json` corrupts the nested JSON strings that `definition.instance` requires.

### PREFER

- The narrowest mode that satisfies the request.
- Reading exactly ONE mode reference. Load a second only when the request genuinely spans modes, and say so before you do.
- Read-modify-write over full replacement in `authoring`: get the current definition, modify the entity array, then update.
- Transition-based detectors (`NumberBecomes`, `NumberEntersOrLeavesRange`, `LogicalBecomes`) over steady-state conditions in `authoring`, unless the user explicitly asks for repeated firing while the value stays in the triggered state.
- A summary view before individual entities in `consumption`: give the high-level picture, then drill in.
- Offering an alert when earlier work in this session surfaced a timely operational signal — a spike, failure, anomaly, SLA risk or capacity constraint — rather than waiting to be asked. Ask once, and author nothing until the user agrees.

### AVOID

- Acting from this dispatcher alone — it intentionally omits the entity schemas and templates.
- Answering with a summary of the reference instead of executing it.
- Mutating anything while in the read-only `consumption` mode, including "just to check".
- Hardcoded workspace or item ids in either mode — always resolve dynamically.
- Globbing, listing or shell-searching the filesystem for the `common/` docs. They are optional background; if a link does not resolve, note it in one line and carry on.
- Building the Eventstream topology that feeds an alert here; that is `eventstream-cli`. Querying the KQL data behind an alert is `eventhouse-cli` — but an alert's own activation history stays here, via `queryActivations`.
- Loading a different skill for work this skill already owns (see CRITICAL NOTES 3).

## Examples

| User request | Mode | Reference to read |
|---|---|---|
| "Create an Activator named eval_smoke_activator in my workspace." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Notify me on Teams when the average temperature goes above 30." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Delete the alert that emails me about failed pipeline runs." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Show me all Activators in this workspace." | `consumption` | [references/consumption.md](references/consumption.md) |
| "What rule and action are behind SkillsTestActivator?" | `consumption` | [references/consumption.md](references/consumption.md) |
| "Decode this Reflex definition and explain the Power BI source." | `consumption` | [references/consumption.md](references/consumption.md) |
| "When did my 'Too hot for medicine' alert fire this week?" | `consumption` | [references/consumption/activation-history.md](references/consumption/activation-history.md) |
