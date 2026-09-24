---
name: powerbi-report-cli
description: "Plan, design, author, preview, publish, and manage Power BI reports across requirements, page design, local PBIR/PBIP edits, validation, screenshots, Fabric upload/download, and rebinding. Use for report lifecycle work; use semantic-model-authoring for model or DAX changes and fabriciq for data questions. Triggers: plan Power BI report, design report page, edit PBIR, preview PBIP, publish report, rebind report"
metadata:
  version: 1.0.4
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: powerbi-report-cli` (`az rest`: `--headers "x-ms-fabric-skill=powerbi-report-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find workspace details, including its ID, from a workspace name: list
>    all workspaces, then use JMESPath filtering.
> 2. To find item details, including its ID, from a workspace ID, item type,
>    and item name: list all items of that type in that workspace, then use
>    JMESPath filtering.
> 3. Use `powerbi-report-cli` for the report artifact: requirements, design,
>    PBIR/PBIP page and visual edits, preview, and publishing. Semantic model,
>    measure, and DAX work belongs to a semantic-model skill. Natural-language
>    questions about report data belong to `fabriciq`.

# Power BI Reports - CLI Skill

This skill owns the Power BI report lifecycle end to end: requirements and
scope, visual design, local PBIR/PBIP authoring and preview, and report-item
transport to and from Microsoft Fabric.

It is a **mode dispatcher** and intentionally contains no detailed procedures.
Select the mode that matches the request, then read the matching mode reference
end to end before acting. The mode file holds the required workflow, commands,
payloads, templates, and failure rules.

## Mode Selection

| Mode | Use when the request... | Existing route examples | Read first |
|---|---|---|---|
| `planning` | creates a new report/dashboard and needs requirements, model/dependency inspection, scope, a page plan, and approval before implementation | create a report, build a dashboard, create from a semantic model, plan then implement, walk me through creating a report | [references/planning.md](references/planning.md), then [references/planning-part-02.md](references/planning-part-02.md) |
| `design` | decides what a report should look like: tone, signature, page archetype, chart type, layout, color, typography, theme direction, accessibility, brand application, redesign, or critique | design a Power BI report, make the dashboard professional, choose a chart, apply a brand, redesign the report, create a design brief | [references/design.md](references/design.md) |
| `authoring` | reads or edits local PBIR/PBIP files, validates them, previews the report, or captures screenshots | edit PBIR, create/add a report page or visual, format a visual, add filters/slicers/bookmarks/themes, validate PBIR, preview/reload/screenshot in Desktop or service | [references/authoring.md](references/authoring.md) |
| `management` | moves a report definition to or from Fabric or manages the workspace report item | publish/upload/download PBIR or PBIP, list reports, get/update/delete a report, rebind a report | [references/management.md](references/management.md) |

## Mode Boundary Rules

- Classify by **intent**, not by which file or tool is already open.
- `design` decides what the report should look like; `authoring` writes the
  PBIR that realizes it. Choosing a chart type is `design`; encoding it into
  `visual.json` is `authoring`.
- Restyling or reformatting an existing local report is `authoring`, even when
  the request uses design language. Use `design` when the user wants advice or
  a design contract rather than a file change.
- `authoring` changes local files and performs preview/validation. It does not
  publish to Fabric.
- `management` transports definitions and manages Fabric report items. It does
  not invent or directly author PBIR content.
- `planning` owns the guided requirements-to-approval flow for a new report. A
  focused edit to an existing report goes directly to `authoring`.

A greenfield request can span modes in this order:

```text
planning -> design -> authoring -> management
```

Handle one mode at a time. Announce each switch and read the new mode reference
before starting that part. The `planning` approval gate is a turn boundary:
never build or publish until the user explicitly approves the locked spec in a
later reply.

## Required Deliverable by Mode

| Mode | Completion requirement |
|---|---|
| `planning` | Persist `_brief/report-spec.md` or the user-named equivalent, ask for explicit approval, and stop before implementation. |
| `design` | Produce the complete `Design Brief:` contract, including `design_identity` and a page archetype/layout contract for every page. Do not edit PBIR or call Fabric APIs. |
| `authoring` | Persist the requested PBIR/PBIP changes, validate each logical batch, then complete the selected preview and screenshot-review workflow required by the authoring reference. Do not publish. |
| `management` | Complete the requested Fabric report operation, including LRO polling and documented readback verification. |

## Rules

### MUST

- Select the narrowest mode that fully covers the current request.
- Read `references/<mode>.md` end to end before the first command or file edit
  in that mode.
- In `planning` mode, also read `references/planning-part-02.md` before
  producing `_brief/report-spec.md`; it contains the required canonical design
  contract and approval checks.
- Preserve every argument and safety boundary documented by the selected mode.
- Announce and perform an explicit mode switch when the request crosses a
  boundary.
- Use the `powerbi-report-author` CLI metadata and validation surfaces instead
  of guessing PBIR schemas, roles, formatting properties, selectors, or enum
  values.
- Keep local edits local unless the user explicitly requests publishing.
- Resolve Fabric workspace and item IDs by listing and filtering rather than
  guessing identifiers.
- Produce the artifact the user requested; reading or summarizing a reference
  is not task completion.

### PREFER

- Infer facts already present in the prompt, semantic model, existing PBIP, or
  prior approved spec instead of asking again.
- Load only the selected mode and its directly relevant topic references.
- Preserve the user's existing project structure, schemas, host, operation,
  binding, and delivery target unless the selected mode explicitly requires a
  change.

### AVOID

- Acting from this dispatcher without reading the selected mode reference.
- Loading a retired sibling skill name; planning, design, authoring, and
  management are modes of this skill.
- Editing PBIR or calling Fabric APIs in `planning` or `design`.
- Publishing from `authoring`, or authoring PBIR content from `management`.
- Bypassing the planning approval gate because the original request also asked
  to build or publish.

<!-- BEGIN GENERATED REFERENCE INDEX -->
## Complete Reference Index

Open every relevant reference directly from this index. Files named `part-XX` continue the named topic.

### Authoring

- [`authoring/authoring-workflows`](references/authoring/authoring-workflows.md)
- [`authoring/bookmark`](references/authoring/bookmark.md)
- [`authoring/button-part-02`](references/authoring/button-part-02.md)
- [`authoring/button-part-03`](references/authoring/button-part-03.md)
- [`authoring/button`](references/authoring/button.md)
- [`authoring/card-part-02`](references/authoring/card-part-02.md)
- [`authoring/card-part-03`](references/authoring/card-part-03.md)
- [`authoring/card`](references/authoring/card.md)
- [`authoring/cartesian-part-02`](references/authoring/cartesian-part-02.md)
- [`authoring/cartesian-part-03`](references/authoring/cartesian-part-03.md)
- [`authoring/cartesian-part-04`](references/authoring/cartesian-part-04.md)
- [`authoring/cartesian`](references/authoring/cartesian.md)
- [`authoring/color-strategy`](references/authoring/color-strategy.md)
- [`authoring/conditional-formatting-part-02`](references/authoring/conditional-formatting-part-02.md)
- [`authoring/conditional-formatting-part-03`](references/authoring/conditional-formatting-part-03.md)
- [`authoring/conditional-formatting-part-04`](references/authoring/conditional-formatting-part-04.md)
- [`authoring/conditional-formatting-part-05`](references/authoring/conditional-formatting-part-05.md)
- [`authoring/conditional-formatting-part-06`](references/authoring/conditional-formatting-part-06.md)
- [`authoring/conditional-formatting-part-07`](references/authoring/conditional-formatting-part-07.md)
- [`authoring/conditional-formatting`](references/authoring/conditional-formatting.md)
- [`authoring/custom-visuals`](references/authoring/custom-visuals.md)
- [`authoring/expressions`](references/authoring/expressions.md)
- [`authoring/field-parameters`](references/authoring/field-parameters.md)
- [`authoring/filter-pane`](references/authoring/filter-pane.md)
- [`authoring/filters`](references/authoring/filters.md)
- [`authoring/formatting-overview`](references/authoring/formatting-overview.md)
- [`authoring/formatting-part-02`](references/authoring/formatting-part-02.md)
- [`authoring/formatting`](references/authoring/formatting.md)
- [`authoring/image`](references/authoring/image.md)
- [`authoring/kpi`](references/authoring/kpi.md)
- [`authoring/map`](references/authoring/map.md)
- [`authoring/model-binding`](references/authoring/model-binding.md)
- [`authoring/page-formatting`](references/authoring/page-formatting.md)
- [`authoring/powerbi-desktop`](references/authoring/powerbi-desktop.md)
- [`authoring/powerbi-report-author-cli-part-02`](references/authoring/powerbi-report-author-cli-part-02.md)
- [`authoring/powerbi-report-author-cli`](references/authoring/powerbi-report-author-cli.md)
- [`authoring/preview-part-02`](references/authoring/preview-part-02.md)
- [`authoring/preview-part-03`](references/authoring/preview-part-03.md)
- [`authoring/preview-part-04`](references/authoring/preview-part-04.md)
- [`authoring/preview`](references/authoring/preview.md)
- [`authoring/re-theming-part-02`](references/authoring/re-theming-part-02.md)
- [`authoring/re-theming-part-03`](references/authoring/re-theming-part-03.md)
- [`authoring/re-theming`](references/authoring/re-theming.md)
- [`authoring/screenshot-review`](references/authoring/screenshot-review.md)
- [`authoring/shape`](references/authoring/shape.md)
- [`authoring/slicers-part-02`](references/authoring/slicers-part-02.md)
- [`authoring/slicers`](references/authoring/slicers.md)
- [`authoring/table`](references/authoring/table.md)
- [`authoring/textbox`](references/authoring/textbox.md)
- [`authoring/theming-part-02`](references/authoring/theming-part-02.md)
- [`authoring/theming`](references/authoring/theming.md)
- [`authoring/version-control`](references/authoring/version-control.md)

### Design

- [`design/accessibility`](references/design/accessibility.md)
- [`design/anti-patterns`](references/design/anti-patterns.md)
- [`design/archetype-composition`](references/design/archetype-composition.md)
- [`design/archetypes/analytical-canvas`](references/design/archetypes/analytical-canvas.md)
- [`design/archetypes/comparative-benchmark-part-02`](references/design/archetypes/comparative-benchmark-part-02.md)
- [`design/archetypes/comparative-benchmark`](references/design/archetypes/comparative-benchmark.md)
- [`design/archetypes/executive-summary`](references/design/archetypes/executive-summary.md)
- [`design/archetypes/narrative-story`](references/design/archetypes/narrative-story.md)
- [`design/archetypes/operational-monitor`](references/design/archetypes/operational-monitor.md)
- [`design/brownfield`](references/design/brownfield.md)
- [`design/chart-selection`](references/design/chart-selection.md)
- [`design/color`](references/design/color.md)
- [`design/design-brief-part-02`](references/design/design-brief-part-02.md)
- [`design/design-brief`](references/design/design-brief.md)
- [`design/interactivity`](references/design/interactivity.md)
- [`design/layout`](references/design/layout.md)
- [`design/pre-flight-checklist`](references/design/pre-flight-checklist.md)
- [`design/signatures`](references/design/signatures.md)
- [`design/tone-catalog`](references/design/tone-catalog.md)
- [`design/typography`](references/design/typography.md)
- [`design/visual-cookbook-part-02`](references/design/visual-cookbook-part-02.md)
- [`design/visual-cookbook`](references/design/visual-cookbook.md)

### Mode Guides

- [`authoring-part-02`](references/authoring-part-02.md)
- [`authoring-part-03`](references/authoring-part-03.md)
- [`authoring-part-04`](references/authoring-part-04.md)
- [`authoring`](references/authoring.md)
- [`design`](references/design.md)
- [`management-part-02`](references/management-part-02.md)
- [`management-part-03`](references/management-part-03.md)
- [`management-part-04`](references/management-part-04.md)
- [`management`](references/management.md)
- [`planning-part-02`](references/planning-part-02.md)
- [`planning`](references/planning.md)

<!-- END GENERATED REFERENCE INDEX -->

## Examples

| User request | Mode |
|---|---|
| "Create a new executive report from this semantic model." | `planning` |
| "Design an operational page and choose the right charts." | `design` |
| "Add a KPI page to this PBIP, validate it, and take screenshots." | `authoring` |
| "Publish this local PBIP to my Fabric workspace and rebind it." | `management` |

## Route Compatibility

The merged skill preserves the four previous route surfaces. Treat the
following phrases as explicit aliases for the corresponding mode:

| Mode | Preserved route phrases |
|---|---|
| `planning` | create a report; build a report; create a dashboard; create a new report from scratch; create a report from a semantic model or dataset link; build a report for this model; make me a dashboard; plan then implement; walk me through creating a report |
| `design` | design Power BI report; make dashboard look professional; choose chart type; apply brand to report; redesign report; create design brief; Power BI report design archetype |
| `authoring` | edit PBIR; create Power BI report page; add visual to PBIP; format report visual; validate Power BI report; preview Power BI report; Power BI Desktop preview status; preview report in service; preview report in browser; screenshot report page; screenshot all report pages; list preview hosts; implement dashboard in PBIP; add dashboard visuals to report; implement an approved PBIP report spec; edit PBIR pages/visuals; edit a Power BI report |
| `management` | upload PBIR report definition; upload Power BI report; download PBIR definition; publish PBIR definition; publish Power BI report to Fabric; manage Power BI reports; list workspace reports |
