<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `design` mode. -->

# powerbi-report-cli design mode -- Power BI Report Visual Design

This skill provides design guidance for Power BI reports. It commits a design identity (tone + signature), routes user requests to the right archetype per page, and applies cross-cutting design principles (color, typography, iconography, layout, interactivity, accessibility).

**Scope boundary** — This skill decides *what* a report should look like and *why*. It does **not** write PBIR files. After producing a design contract, hand off to the `authoring` mode for all file mechanics: page/visual creation, theme registration, expression encoding, formatting objects, and validation.

## Must/Prefer/Avoid

### MUST

- Inspect the semantic model or available fields before making design decisions.
- Produce concrete design choices: tone, signature, page archetype, chart rationale, layout direction, color, typography, and accessibility considerations.
- Hand off file mechanics to the `authoring` mode; this skill does not edit PBIR.

### PREFER

- Ask only for missing design inputs that materially affect the outcome.
- Use reference files on demand instead of loading the full design catalog.
- Emit a structured `Design Brief:` when the design will be implemented.

### AVOID

- Do not create pages, visuals, filters, themes, or PBIR files directly.
- Do not provide vague "make it modern" guidance without concrete layout/color/chart decisions.
- Do not replace the planning workflow for broad create/build requests.

## Topic Files and Examples

This root file covers the end-to-end workflow, theme, gotchas, and the design contract template. Read the topic files as needed:

| File | When to read |
|------|-------------|
| `references/design/tone-catalog.md` | Read when the prompt lacks a specific tone or needs concrete downstream palette/type choices |
| `references/design/signatures.md` | Read when selecting or refining the report's signature visual move |
| `references/design/archetype-composition.md` | Read for multi-page reports when page roles or variant rotation are unclear |
| `references/design/archetypes/<name>.md` | **Read before** laying out each page — layout template, density, chart mix |
| `references/design/chart-selection.md` | **Read before** selecting a chart type — encoding hierarchy, purpose matching |
| `references/design/visual-cookbook.md` | **Read before** configuring any visual — sort, color, labels, CF per type |
| `references/design/layout.md` | **Read before** placing visuals on canvas — 8-px grid, composition templates |
| `references/design/color.md` | Read if defining palette, color semantics, gradients, or conditional formatting |
| `references/design/typography.md` | Read if overriding font sizes, type pairings, or weight conventions |
| `references/design/assets/base.json` | **Read before** theme work for generated reports — preserve its textbox/card/table per-type safeguards when adapting a custom theme |
| `references/design/interactivity.md` | Read if adding drill-through, bookmarks, or cross-filter rules |
| `references/design/brownfield.md` | Read for redesigns, restyles, theme swaps, or brand application |
| `references/design/accessibility.md` | **Read before** finalizing any report — WCAG checklist, alt text, contrast |
| `references/design/anti-patterns.md` | **Read before** finalizing any report — common failures and how to fix them |
| `references/design/pre-flight-checklist.md` | Read for the full checklist before handoff/final audit |
| `references/design/design-brief.md` | **Read before handoff** — full `Design Brief:` template, mechanical `layout_contract` schema, page title/header band, slicer placement, non-overlap rules, and validation checklist |

## Workflow

### Step 0 — Data-First Investigation

Inspect the semantic model before making any design decision. Use the Semantic Model MCP server if available, or read `.tmdl` files directly. Sample top-N rows per table to understand distributions, cardinality, and magnitudes. Catalog tables, columns, measures, hierarchies, and relationships. Map each measure+dimension to the analytical question it answers.

### Step 1 — Design Identity

Before routing archetypes or picking charts, commit to a **tone** and **signature**. The tone captures the report's feel; the signature is the one defining visual move that recurs across pages. If the prompt lacks a specific identity, use `references/design/tone-catalog.md` and `references/design/signatures.md` to choose, remix, or author a tone/signature. Do not force-fit catalog entries; the requirement is a concrete identity that drives palette, typography, layout, and recurring visual treatment. For brownfield redesigns, read `references/design/brownfield.md` and capture both current and target tone/signature.

### Step 2 — Archetype Router

Route **per page**, not per report. Even a single broad request ("a report covering everything about our business") usually decomposes into pages with different audiences, purposes, and cadences — and therefore different archetypes. Treat each page as an independent routing decision.

| Signal | Archetype | Reference |
|--------|-----------|-----------|
| C-suite, board, GM; ≤10 s scan; "is it on track?" | **Executive Summary** | `references/design/archetypes/executive-summary.md` |
| Shift operator, NOC, wallboard; "is it broken?" | **Operational Monitor** | `references/design/archetypes/operational-monitor.md` |
| Analyst; hypothesis testing; "why did X happen?" | **Analytical Canvas** | `references/design/archetypes/analytical-canvas.md` |
| Author-driven argument; "here's what happened" | **Narrative Story** | `references/design/archetypes/narrative-story.md` |
| Ranking, benchmarking, variance; "relative to what?" | **Comparative Benchmark** | `references/design/archetypes/comparative-benchmark.md` |

When the signal is ambiguous, default to **Analytical Canvas** — it is the most flexible archetype and degrades gracefully.

**Vague prompts: ASK before routing.** A prompt is vague if audience, purpose, page count, or filtering depth is missing. When vague, **stop and offer 2–3 concrete named options** in user-facing terms (never expose archetype names). Each option references a specific archetype + variant combination tailored to what's in the semantic model from Step 0. If the user picks, proceed; if still unsure, ask one narrowing follow-up; after at most two rounds, pick the best option, document the assumption in `variant_rationale`, and proceed.

**Then pick a layout variant.** Each archetype reference file ships **2–3 layout variants** (A / B / C) with a selection table keyed on data signals. Walk the variant selection table per page using the data shape from Step 0. Do NOT default to variant A out of habit. Record the variant + the data signal that drove the pick (`layout_variant` + `variant_rationale` in the `Design Brief:` YAML).

**Treat archetype zones as advisory, not mandatory.** A variant is a layout
starting point, not a required component checklist. Every card, callout,
annotation, and context tile must earn its space by answering a distinct
analytical question. If the semantic model lacks the needed derived insight
(delta, variance %, rank shift, exception threshold, comparison baseline, or
dynamic explanatory text), drop or repurpose that zone rather than filling it
with a duplicate absolute measure.

For multi-page reports, see [`references/design/archetype-composition.md`](design/archetype-composition.md) — common compositions (Executive + Drill, Ops + Detail, Story + Evidence, Multi-domain) + cross-page variant rotation rules. Avoid mono-archetype reports; same-archetype pages must rotate variants where data signals support it.

### Step 3 — Chart Selection

Read [`references/design/chart-selection.md`](design/chart-selection.md) to match each analytical question to the right visual type. Respect the encoding hierarchy: position → length → angle → area → hue. Sample the data first — a line chart with flat lines or a bar chart with two bars indicates the wrong visual choice.

### Step 4 — Visual Configuration

Read `references/design/visual-cookbook.md` for per-visual-type rules: sort order, color strategy, label placement, axis config, and conditional formatting. These rules determine whether charts look professional or amateur. Read `references/design/layout.md` before placing visuals on the canvas.

### Step 5 — Theme

Adapt the report theme to the design identity from Step 1. For generated reports,
start from `references/design/assets/base.json` or preserve its critical per-type safeguards when
creating an adapted custom theme: `textbox` padding/background/border overrides,
`cardVisual` zero padding/card spacing, table grow-to-fit styling, hidden visual
headers, and type-specific chart defaults. Do not replace these with a blunt
wildcard `visualStyles["*"]["*"].padding` / background unless every affected
visual type is checked and overridden. If the report already has a theme,
preserve it unless the user asked for a theme swap or brand refresh. For full
mechanics of theme registration — including how to choose the `$schema`
version when adapting `references/design/assets/base.json` — use the `authoring`
mode.

### Step 6 — Canonical Design Contract

Emit a structured `Design Brief:` YAML block. This is the contract with
the `authoring` mode. Populate every field with concrete values from Steps
0-5 and include a mechanical `layout_contract` per page.

When this skill is used inside the planner workflow, embed this YAML block in
`_brief/report-spec.md` under a "Canonical design contract" section. For the
full template, field rationale, brownfield current/target fields,
minimal-brief escape hatch, page-level mechanical schema, examples, and
validation checklist, read `references/design/design-brief.md`.

The contract must have a design provenance marker (`generated_by: powerbi-report-cli`) and `contract_version`. Greenfield reports default to FHD (`1920 x 1080`) unless the user asks for another size; brownfield reports preserve the existing canvas unless resize is approved. Do not hand off a non-trivial page until its `layout_contract` has a `page_title` placement, a reserved header/slicer band or justified filter rail, a `space_audit`, and non-overlapping regions/placements.

Keep this minimal shape in mind; use `references/design/design-brief.md` for the full
template and validation rules:

```yaml
Design Brief:
  generated_by: powerbi-report-cli
  contract_version: 1
  mode: greenfield
  design_identity: { tone: <tone>, signature: <signature> }
  pages:
    - name: <descriptive insight title>
      role: <landing | detail | drillthrough | tooltip>
      archetype: <Executive | Analytical | Operational | Narrative | Comparative>
      layout_variant: <A | B | C>
      variant_rationale: <one sentence: which data signal drove this pick>
      layout_contract:
        canvas: { width: 1920, height: 1080, margin: 32, gutter: 24, snap: 8 }
        grid:
          columns: 12
          rows: 12
          regions:
            header:  [1, 1, 9, 2]
            filters: [9, 1, 13, 2]
            body:    [1, 2, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: <descriptive insight title>
          - id: <visual_or_slicer_id>
            region: <defined region>
            kind: <cardVisual | barChart | lineChart | tableEx | slicer | azureMap | ...>
            purpose: <one analytical question>
            field_bindings: <Table[Field] or role map>
        space_audit:
          content_cell_count: <cells after excluding reserved header/slicer/rail>
          placed_cell_count: <cells covered by regions with placements>
          empty_cell_pct: <0-100>
          unplaced_regions: []
          largest_region: { name: <region>, pct_of_content: <0-100> }
          balance_rationale: <why region sizes match analytical priorities>
```

**Minimal-brief escape hatch** (trivial single-visual asks): 3 lines suffice —
`mode`, `design_identity { tone, signature }` (or `unchanged` in brownfield),
and the one decision. See `references/design/design-brief.md` for examples.

### Step 7 — Review and Handoff

Before handing off, read `references/design/design-brief.md` and
`references/design/pre-flight-checklist.md`, then critically review the design
contract against both. For brownfield, also walk the brownfield-specific items
in `references/design/brownfield.md`. Fix problems before handing off.

If you can get an independent review (a separate reasoning pass or a colleague), do so — layout gaps, missing slicers, monochrome charts, raw field names, and tone-not-propagated failures are easiest to catch with fresh eyes.

Once the contract passes the checklist, hand off to the `authoring` mode for implementation.

## Gotchas

Non-obvious issues that cause reports to look broken or indistinct. Check each one.

**Tone declared but never propagated** — A brief that says `tone: editorial newsroom` but ships the same typography, palette, and gridline/border treatment as every other report. The tone has to *show up* in concrete visual choices. Walk the tone-catalog row's downstream-choices column.

**Page background** — Use an intentional page surface on every page; avoid white canvas + white visual containers, which creates flat, borderless visuals that bleed into the background. Authoring owns the exact `page.json` mechanics.

**No overlap / clipped controls** — No visual bounding boxes may overlap unless the overlap is explicitly intentional (for example, an annotation shape behind a chart). Top-bar slicers share a reserved title/slicer band: the page title remains the left anchor and slicers sit to the right. Charts/cards start below that band, not underneath it. Raising slicer z-order is not a substitute for non-overlapping layout.

**Redundant callouts** — A side callout or KPI context tile that repeats the
same absolute measure already shown in the adjacent chart is noise. Callouts
need `insight_basis` / `callout_value_basis` tied to a derived comparison,
threshold, rank, anomaly, or generated narrative; otherwise remove the callout
and give the space to a chart, table, filter context, or annotation that adds
information.

**Temporal slicer grain** — Do not reflexively choose a full-date `Between`
slicer just because a date column exists. For executive pages and annual-grain
data, use a Year dropdown/tile unless users need day/month range exploration
and the column is a renderable Date/DateTime field.

**Textbox scrollbar** — Textboxes need enough height for their font size plus any VCO/theme padding or Desktop renders a scrollbar. Height formula: `max(18, ⌈fontSize × 25/16⌉) + padding_top + padding_bottom`. If the theme uses wildcard padding, add a textbox-specific zero-padding override or increase the textbox height.

**Color-map contract** — Every measure-bound visual must follow `Design Brief.color_map`. `measure_match` means exact base color reuse across cards, lines, bars, maps, and tables; `gradient` means tint → base for that same measure. Audit the built report for mismatches before handoff.

**Monochrome bars** — Single-measure bar charts can render all bars in one color because PBI assigns palette colors by series, not by category. If category contrast matters, specify the intended per-category or gradient treatment in the brief and let authoring handle the mechanics. Do not work around this by duplicating the same field as both category and legend.

**Raw field names** — Agents consistently leave raw database names like `method_category`, `customer_id`, `Count of order_line_id`, or `date_of_enrolment` on axes, headers, and legends. Check every axis label, column header, legend entry, and card label. Set human-readable display names on every field.

**Display names for aggregations** — Use descriptive names like "Total Fights" or "Students", not "Sum of fight_key" or "Count of student_id". Set via `displayName` in the projection or via axis title override.

**Percentage formatting** — Rates stored as decimals (e.g., 0.53) should display as "53%", not "0.53". Set the number format string to `"0%"` or `"0.0%"` on the relevant visual property.
