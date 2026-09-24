# Design Brief Contract

The `Design Brief:` YAML block is the authoritative handoff from
the `design` mode to the `authoring` mode. It specifies **what** to
build: page intent, design identity, semantic bindings, and a mechanical
`layout_contract` that authoring can translate into pixel geometry. Authoring
computes **how**: exact coordinates, PBIR JSON, theme registration, validation,
Desktop reloads, and screenshots.

In the planner workflow, embed this YAML block inside `_brief/report-spec.md`
under a "Canonical design contract" section. The surrounding Markdown is for
user approval and context; the embedded YAML is authoritative for
implementation.

## Contents

- [Required marker](#required-marker)
- [Why the structure](#why-the-structure)
- [Minimal-brief escape hatch](#minimal-brief-escape-hatch)
- [Full template](#full-template)
- Page layout contract (continued in `design-brief-part-02.md`)
- Common region patterns (continued in `design-brief-part-02.md`)
- Validation checklist (continued in `design-brief-part-02.md`)

## Required marker

Every non-trivial design brief produced by this skill must include:

```yaml
generated_by: powerbi-report-cli
contract_version: 1
```

The marker is not decorative. Planner and authoring use it to distinguish a
design-owned contract from a planner draft or prose-only wireframe.

## Why the structure

- **`design_identity`** captures the Step 1 tone + signature, plus brownfield
  current-state for the redesign delta. Every later decision should visibly
  serve the identity.
- **`tone` and `signature` are open vocabulary.** Catalog entries are defaults
  and calibration examples, not required enums. If a custom identity fits
  better, author it and make the downstream choices explicit enough for
  the `authoring` mode to implement.
- **`color_map`** assigns one palette color per measure. Cards use it as accent;
  line charts as `defaultColor`; bar charts as gradient max. Treat it as an
  implementation contract: `measure_match` means exact color reuse for the same
  measure across cards, lines, bars, maps, tables, and every page.
- **`color_strategy`** per visual: `measure_match`, `gradient`, `unique`,
  `semantic`, or `none`.
- The **layout contract** (`pages[].layout_contract`) is the authoritative
  geometry handoff. Optional wireframe prose may explain the design, but
  authoring should derive coordinates from `canvas`, `grid.regions`, and
  `placements`.
- **Theme base** should normally be `references/design/assets/base.json` adapted to the tone. If a
  custom theme is used instead, preserve the base theme's critical per-type
  safeguards: textbox zero padding/background/border, card zero padding/card
  spacing, table grow-to-fit styling, hidden visual headers, and chart defaults.
- Slicer type follows grain and intent: Year/Period dropdown or tile for
  executive annual/quarterly filters; full-date `between` only when arbitrary
  date-range exploration matters and the field renders as Date/DateTime.
- Callouts and context tiles need `insight_basis` / `callout_value_basis`; do
  not allocate a callout to a duplicate absolute measure.
- One analytical question per visual. If a visual answers two questions, split
  it.

## Minimal-brief escape hatch

For trivial single-visual asks ("change this card's font size", "add a slicer
for region"), a 3-line brief is enough:

```yaml
Design Brief:
  mode: brownfield
  design_identity: { tone: unchanged, signature: unchanged }
  change: "Increase Revenue card value font from 28pt to 36pt to read as the page hero"
```

The full template below is for non-trivial work: a new page, a redesign, or any
change involving more than one visual.

## Full template

For each page, include a `layout_contract` with named regions and placements.
Greenfield reports default to FHD (`1920 x 1080`) unless the user asks for a
different size; brownfield reports preserve the existing canvas unless resize is
approved. The contract must reserve a title/header band, place slicers in either
a right-aligned top filter region or a justified filter rail, include a
`space_audit`, and prevent visual overlap.

```yaml
Design Brief:
  generated_by: powerbi-report-cli
  contract_version: 1
  mode: greenfield  # greenfield | brownfield
  design_identity:
    tone: <catalog tone, remixed tone, or custom phrase with palette/type/density implications>
    signature: <gallery signature, remixed signature, or custom recurring visual move>
    # Brownfield only:
    # current_tone: <existing report's tone, or "indistinct" if none>
    # current_signature: <existing report's defining element, or "none">
  archetype: <primary archetype for the report>
  navigation_model: <page_navigator | buttons | bookmark_navigator | none>
  # Primary report-wide navigation model. Pick ONE and keep it consistent across pages.
  # See references/design/interactivity.md § Navigation Model Decision. Use buttons for actions a
  # navigator can't do (Back, Drillthrough, Apply/Clear slicers, Web URL, Q&A).
  color_map:
    - measure: Sales[Revenue]
      color: "#0072B2"
      tint: "#DEEFFF"
    - measure: Sales[Orders]
      color: "#D55E00"
      tint: "#FFE8D5"
  pages:
    - name: <descriptive insight title>
      role: <landing | detail | drillthrough | tooltip>
      archetype: <Executive | Analytical | Operational | Narrative | Comparative>
      layout_variant: <A | B | C>
      variant_rationale: <one sentence: which data signal drove this pick>
      navigation:   # nav elements/actions placed on THIS page; omit or [] if none
        - element: <page_navigator | button | bookmark_navigator>
          action: <PageNavigation | Back | Bookmark | Drillthrough | ApplyAllSlicers | ClearAllSlicers | WebUrl | Qna>
          target: <page name | bookmark name | url>   # omit for Back / Apply/Clear slicers
          label: <destination-scented label, e.g. "Regional Breakdown">
      page_background: "#F3F2F1"
      layout_summary: <short prose explanation; not authoritative for geometry>
      layout_contract:
        canvas:
          width: 1920
          height: 1080
          margin: 32
          gutter: 24
          snap: 8
        grid:
          columns: 12
          rows: 12
          regions:
            header:  [1,  1,  9,  2]
            filters: [9,  1, 13,  2]
            kpis:    [1,  2, 13,  4]
            hero:    [1,  4,  6,  9]
            trend:   [6,  4, 13,  9]
            detail:  [1,  9, 13, 13]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "Revenue Fell 8% YoY in EMEA"
            purpose: "State the page insight before any chart."
          - id: year_slicer
            region: filters
            kind: slicer
            field_bindings: Date[CalendarYear]
            slicer_type: dropdown
            slot: 1
            of: 2
          - id: region_slicer
            region: filters
            kind: slicer
            field_bindings: Region[Name]
            slicer_type: dropdown
            slot: 2
            of: 2
          - id: revenue_card
            region: kpis
            kind: cardVisual
            purpose: "What is total revenue?"
            field_bindings: Sales[Revenue]
            color_strategy: measure_match
            slot: 1
            of: 4
          - id: top_products
            region: hero
            kind: barChart
            purpose: "Which products drive the most revenue?"
            field_bindings: { Category: Product[Name], Y: Sales[Revenue] }
            sort_policy: value_desc
            color_strategy: gradient
          - id: revenue_trend
            region: trend
            kind: lineChart
            purpose: "How is revenue trending over time?"
            field_bindings: { Category: Date[Quarter], Y: Sales[Revenue] }
            color_strategy: measure_match
          - id: order_detail
            region: detail
            kind: tableEx
            purpose: "Which orders/products need follow-up?"
            field_bindings: [Date[FullDate], Product[Name], Sales[Revenue], Sales[Margin]]
        space_audit:
          content_cell_count: 132
          placed_cell_count: 132
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region:
            name: detail
            pct_of_content: 36
          balance_rationale: "KPI strip, two analysis panels, and detail table all earn visible space; no unused footer or dead band."
  interaction_pattern:
    drill_targets: <list of drillthrough destination pages>
    cross_filter_rules: <Filter | Highlight | None per source-target pair>
  accessibility:
    alt_text_strategy: <headline+trend | chart+structure | comparison framing>
    contrast_notes: <any WCAG concerns specific to this design>
  theme:
    base: <references/design/assets/base.json adapted | existing theme preserved | default Power BI theme>
    user_overrides: <what NOT to change if user has existing theme/brand>
```
