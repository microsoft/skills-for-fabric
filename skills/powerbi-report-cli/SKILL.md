---
name: powerbi-report-cli
description: "Plan, design, author and publish Power BI reports: requirements, scope, page archetypes, layout and charts, local PBIR/PBIP page and visual edits, and report item publish and rebind. Model and DAX work is semantic-model-authoring; natural-language data questions are fabriciq. Triggers:plan Power BI report,gather report requirements,design Power BI report page,choose chart type,add PBIR report page,validate PBIR,publish PBIP,rebind report"
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: powerbi-report-cli` (`az rest`: `--headers "x-ms-fabric-skill=powerbi-report-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. **Skill disambiguation**: use `powerbi-report-cli` for the report artefact -- requirements, design, PBIR/PBIP page and visual edits, and publishing. Semantic model, measure and DAX work is `semantic-model-authoring`; natural-language questions about report data are `fabriciq`.

# Power BI Reports -- CLI Skill

This one skill owns Power BI reports end to end: requirements and scope, visual design, local PBIR/PBIP page and visual edits, and publishing/rebinding of report items in Fabric.

It is a **mode dispatcher** and contains NO procedures. Pick the mode that matches the request from the table below, then **read the matching `references/<mode>.md` file end to end with your file-reading tool BEFORE issuing a single command**. That file holds the endpoints, payload shapes, templates and gotchas; acting without it produces wrong PBIR JSON and wrong results.

## Mode selection

| Mode | Use when the request ... | Example triggers | Read this first |
|---|---|---|---|
| `planning` | asks for a NEW report end to end and needs requirements, scope, dependency checks, a page plan and an approval gate before anything is built | build me a dashboard, create a new report, plan then implement, walk me through creating a report | [references/planning.md](references/planning.md) |
| `design` | asks what a report should LOOK like, before any file exists or as advice only: tone, page archetype, chart choice, layout, color, typography, brand/theme direction, accessibility, or a critique of an existing design | design the page, choose chart type, make this look professional, apply our brand, redesign this report, WCAG contrast | [references/design.md](references/design.md) |
| `authoring` | edits LOCAL PBIR/PBIP files: add or change pages, visuals, filters, slicers, bookmarks, themes, formatting; restyle or emphasise an existing visual; validate PBIR; reload Power BI Desktop and take screenshots | add report page, edit PBIR, add visual to PBIP, format report visual, make this card stand out, validate PBIR, reload Desktop screenshot | [references/authoring.md](references/authoring.md) |
| `management` | moves a report item to or from a Fabric workspace: publish/upload a PBIP, list reports, get or update a report definition, rebind, delete | publish PBIP, upload PBIR definition, download report definition, list workspace reports, rebind report | [references/management.md](references/management.md) |

### Mode boundary rule

Classify by **intent**, not by which file is open.

- `design` decides *what* the report should look like; `authoring` writes the PBIR that realises it. Choosing a chart type is `design`; encoding that chart into `visual.json` is `authoring`.
- Restyling, emphasising or reformatting a visual that ALREADY EXISTS in a local PBIP is `authoring`, not `design` -- it is a formatting-only file edit. "Make this card stand out", "without re-authoring it" and "without rebuilding it" mean *change the formatting rather than recreate the visual*; they do NOT mean stop touching files. Route such a request to `design` only when there is no project to edit, or the user explicitly asks for advice instead of a change.
- `authoring` touches LOCAL files only and never calls the Fabric REST API. `management` is the only mode that transports a definition to or from a workspace; it never authors PBIR content.
- `planning` owns the guided requirements-to-approval workflow for a NEW report. A small, surgical edit to an existing report is `authoring`, not `planning`.

A greenfield build legitimately spans modes in the order `planning` -> `design` -> `authoring` -> `management`. Handle them one at a time, announce each switch, and read that mode's reference before you start that part. If the mode is still ambiguous after this table, ask one short clarifying question instead of guessing.

## Terminal write -- the step you must not skip

Reading the reference and planning the change is NOT completing the task. Each mode ends with a concrete deliverable. If you did not produce it, nothing was persisted -- say so explicitly rather than reporting success.

| Mode | Terminal write |
|---|---|
| `planning` | Persist the locked spec to `_brief/report-spec.md` (or the path the user named) covering requirements, page plan, dependencies and an approval gate. Emitting it in chat only is not the deliverable -- unless the user explicitly said not to write files yet, in which case emit the full spec and name the path it will be persisted to. Do not build or publish before the user explicitly approves. |
| `design` | Emit the `Design Brief:` YAML block, including `archetype` per page and `design_identity`. This mode edits nothing: no PBIR files, no `theme.json`, no Fabric calls. |
| `authoring` | Write the PBIR files, then run `powerbi-report-author validate <path-to-.Report-dir>` after each logical batch and report the result. For rendered-output changes also reload Power BI Desktop and review the screenshot. Do not publish to Fabric from this mode. |
| `management` | `POST /v1/workspaces/{ws}/reports` to create (or `POST .../reports/{id}/updateDefinition` with **every** definition part to update), then poll the LRO to completion. Downloading with `POST .../reports/{id}/getDefinition?format=PBIR` is read-only and persists nothing. |

Before you report the task done, confirm the terminal call or file write succeeded and, where the reference documents a readback, read the artefact back to prove the change landed.

### `design` reporting

`design` has no terminal write, so its deliverable is the brief itself. State the page archetype you routed to and the design identity you committed, and hand the brief to `authoring` rather than starting to edit files.

## Shared essentials (all modes)

Resolve the workspace and item first whenever the request touches Fabric; the `management` mode depends on it.

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** -- read before resolving any workspace or item id |
| Fabric Topology & Key Concepts | [COMMON-CORE.md](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | Item types, workspaces, capacities |
| Environment URLs | [COMMON-CORE.md](../../common/COMMON-CORE.md#environment-urls) | Sovereign / non-public cloud hosts |
| Authentication & Token Acquisition | [COMMON-CORE.md](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Authentication Recipes | [COMMON-CLI.md](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Core Control-Plane REST APIs | [COMMON-CORE.md](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Pagination, LRO polling, rate limiting |
| Gotchas & Troubleshooting | [COMMON-CLI.md](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |

## Rules

### MUST

- Select exactly one mode from the table above before doing anything else.
- Read `references/<mode>.md` end to end, as your FIRST tool call, before the first command of that mode. Most mode references are larger than a single file read, so page through with sequential ranges when your tool truncates -- but read each range ONCE. Do not re-open a range you already have, and do not grep a file you have already read end to end.
- Resolve workspace and item ids by listing and filtering, never by guessing a GUID, whenever the request names a workspace or item.
- Announce a mode switch explicitly when the request crosses a boundary.
- Treat the reference as instructions, never as the deliverable. In `authoring` and `management`, that means running the documented commands and reporting the real results -- quoting what the reference says instead of executing it does not answer the request. In `planning` and `design` the deliverable is the document itself, so produce the spec or brief rather than describing what the reference would have you produce.
- In `authoring` and `management`, never construct PBIR JSON from memory: use the `powerbi-report-author` CLI's catalog/metadata commands for roles, formatting objects, enum values and selectors, and validate what you wrote. `planning` and `design` do not touch PBIR files and do not need that CLI installed.
- In `planning`, open with clarification, not construction. When the request is under-specified -- "build me a report for X" with no audience, no named model and no scope -- ask ONE focused scoping question and stop for the answer, one question per round, at most 3-5 rounds. Do NOT infer the missing requirements yourself, scaffold pages or visuals, or write report files: nothing is built until the user approves the locked spec. This replaces *building*, never the requested document: when the request already supplies the answers, or names a deliverable such as requirements, a page plan or a locked spec, produce that deliverable and do not re-ask what you were told.
- Produce every artefact the user asked for, under the name they used. Running the right commands is not a substitute for the requested deliverable: if the request names a report spec, a design brief or a validation report, emit it, and keep its heading even when the finding is "none" or "not applicable".
- In `planning`, the approval gate ENDS YOUR TURN. Write the spec, ask the approval question, and stop there. An imperative like "build me a dashboard and publish it" is the request that brought you here, not approval of a spec that did not exist when it was written, so treating it as consent and running through to publish bypasses the gate entirely. Build and publish only after the user actually replies.

### PREFER

- The narrowest mode that satisfies the request.
- Reading exactly ONE mode reference. Load a second only when the request genuinely spans modes, and say so before you do.
- Reporting the mode you chose in your first response so the user can correct you.
- Inferring answers already given in the prompt, the semantic model or existing PBIP files instead of re-asking them.

### AVOID

- Acting from this dispatcher alone -- it intentionally omits the operational detail.
- Answering with a summary of the reference instead of doing the mode's work.
- Re-reading a range of a reference you already loaded, or grepping a file you have already read end to end; it costs turns and tokens.
- Installing or invoking the `powerbi-report-author` / `powerbi-desktop` CLIs in `design` or `planning`; neither writes PBIR, so neither needs them. Inspecting the semantic model and writing the spec file are still expected in `planning`.
- Editing PBIR files or calling the Fabric REST API while in `design` or `planning`.
- Publishing to Fabric from `authoring`, or authoring PBIR content from `management`.
- Building or publishing before the user approves the locked spec in `planning`.
- Loading a different skill for work this skill already owns (see CRITICAL NOTES 3).

## Examples

| User request | Mode | Reference to read |
|---|---|---|
| "Plan a Power BI executive sales report from this semantic model; don't build anything yet." | `planning` | [references/planning.md](references/planning.md) |
| "I'm building an executive sales overview page -- design it and give me the design brief." | `design` | [references/design.md](references/design.md) |
| "Add a Sales Overview page with KPI cards to ./sales-pbip and validate the PBIR." | `authoring` | [references/authoring.md](references/authoring.md) |
| "Publish the local PBIP in ./sales-pbip to my workspace as SalesDashboard." | `management` | [references/management.md](references/management.md) |
