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
- [Page layout contract](#page-layout-contract)
- [Common region patterns](#common-region-patterns)
- [Validation checklist](#validation-checklist)

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
    base: <assets/base.json adapted | existing theme preserved | default Power BI theme>
    user_overrides: <what NOT to change if user has existing theme/brand>
```

## Page layout contract

Each `pages[]` entry must include a `layout_contract`. Freeform wireframes or
Markdown descriptions may appear as explanation, but they are not authoritative
for geometry.

### Canvas

| Field | Type | Description |
|-------|------|-------------|
| `width` | int | Canvas width in pixels. Greenfield reports default to `1920` (FHD) unless the user asks for another size. |
| `height` | int | Canvas height in pixels. Greenfield reports default to `1080` (FHD) unless the user asks for another size. |
| `margin` | int | Page edge margin in pixels; usually `32` on FHD (`24` on 1280 x 720 brownfield pages). |
| `gutter` | int | Minimum pixels between sibling visuals; usually `24` on FHD (`16` on 1280 x 720 brownfield pages). |
| `snap` | int | Coordinate snap grid; use `8`. |

For brownfield work, preserve the existing canvas size unless the user approved
a resize. Tooltip pages may use a smaller canvas such as `320 x 240`, but still
require the same region and placement checks.

### Grid regions

Regions are named rectangular areas on a 12-column x 12-row grid. Coordinates
use `[col_start, row_start, col_end, row_end]`, 1-indexed and end-exclusive. For
example, `[1, 1, 13, 13]` covers the full grid.

Rules:

- Region names must describe page semantics: `header`, `filters`, `kpis`,
  `hero`, `detail`, `slicer_rail`; never `r1` or `box2`.
- Regions must not overlap unless the overlap is intentional and non-data
  bearing, such as a background shape behind a group.
- Every placement must reference a defined region.
- Every coordinate must stay within `[1, 1, columns + 1, rows + 1]`.
- The authoring step converts regions to pixels and snaps all resulting `x`,
  `y`, `width`, and `height` values to the `snap` grid.

### Space allocation and balance

The grid must account for the whole page, not just avoid overlaps. Empty
regions and oversized heroes are common failure modes: they make reports look
unfinished and leave important visuals too small to read.

Required rules:

- Every region in `grid.regions` must either have at least one placement or be
  deliberately named as non-data-bearing structure (`spacer_*`, `bg_*`,
  `divider_*`) and referenced by a non-data placement. Do not define empty
  `footer`, `callout`, `detail`, or `legend` regions as placeholders.
- Include `space_audit` under every non-trivial page's `layout_contract`. The
  audit forces the design step to count occupied space before handoff.
- Compute empty space against **content cells**: all grid cells minus reserved
  header/slicer band cells and minus justified filter-rail cells. For
  analytical, operational, and comparative pages, `empty_cell_pct` should be
  `<= 15`. For executive and narrative pages, `<= 20` is acceptable. Higher
  values require an explicit narrative/brand rationale.
- No contiguous empty band may be taller than one grid row unless it is a named
  spacer/divider region with a placement and rationale. Prefer pixel gutters for
  section breaks instead of reserving whole empty grid rows.
- For pages with 4+ data visuals, no single **non-hero** data region should
  exceed 45% of content cells. A dominant hero region may exceed this only when
  the selected archetype variant explicitly calls for one and
  `balance_rationale` says why the supporting visuals remain readable.
- For pages with 2-3 data visuals, balanced halves/thirds are usually better
  than one region swallowing the page. A single region over 55% of content cells
  needs hero rationale tied to the page question.
- A bare single-value `cardVisual` must not be the page's largest or dominant
  hero region. Cards encode one number; oversized cards create low information
  density and starve richer visuals. Use cards in KPI strips, compact status
  tiles, or side callouts. A card-like hero is acceptable only as a **composite
  KPI treatment** with explicit context (delta/reference label, sparkline,
  threshold band, annotation, or paired explanatory chart) and a
  `balance_rationale` explaining why the tradeoff is worth it.
- A side callout, context tile, smart narrative, or card-like annotation must
  add information not already carried by the neighboring chart/table. It needs a
  derived insight basis such as variance %, delta, rank shift,
  gap-to-benchmark, threshold exception, or dynamic narrative text. If the only
  available value is the same absolute measure plotted next to it, remove the
  callout or repurpose the region for richer evidence. Use Smart Narrative
  (`aiNarratives`) only when the callout must be a filter-responsive
  natural-language summary and the `authoring` mode has verified the
  formatting/query mechanics for the target report version; otherwise prefer a
  textbox bound to an explicit narrative measure or a compact KPI/context tile.
- Supporting chart regions are a floor of 3 columns x 3 rows; use 4+ columns or
  4+ rows for charts with dense labels, legends, or small multiples. Tables
  should receive at least 4 grid rows unless they are a compact top-N spotlight.
  KPI/card strips should be 2 grid rows on standard report pages so cards can
  show value plus context.

`space_audit` shape:

```yaml
space_audit:
  content_cell_count: <grid cells after excluding reserved header/slicer/rail>
  placed_cell_count: <cells covered by regions with placements>
  empty_cell_pct: <0-100>
  unplaced_regions: []
  largest_region:
    name: <region name>
    pct_of_content: <0-100>
  balance_rationale: <why region sizes match the page's analytical priorities>
```

### Space allocation counterexamples

Counter-example to fix before handoff:

```yaml
regions:
  header: [1, 1, 9, 2]
  filters: [9, 1, 13, 2]
  kpis: [1, 2, 13, 4]
  trend: [1, 4, 7, 9]
  ranking: [7, 4, 13, 9]
  footer: [1, 11, 13, 13]   # no placement references this region
```

Rows 9-11 are a dead band and `footer` is unplaced. Fix by expanding
`trend`/`ranking` to row 10 and moving a real detail table, source note, or
navigation/footer placement into the remaining row; otherwise remove the footer
region and let the occupied regions fill the content area.

Counter-example to fix before handoff:

```yaml
regions:
  header: [1, 1, 13, 2]
  hero:   [1, 2, 13, 8]   # largest region
  detail: [1, 8, 13, 13]
placements:
  - id: total_revenue
    region: hero
    kind: cardVisual       # one measure, no delta/sparkline/threshold context
    field_bindings: Sales[Revenue]
space_audit:
  largest_region: { name: hero, pct_of_content: 50 }
  balance_rationale: "Revenue is important."
```

The card wastes half the content area to show one number. Fix by moving
`total_revenue` into a 2-row KPI strip or side callout and assigning the hero
region to the explanatory trend, ranked driver chart, variance chart, map,
decomposition visual, or detail table that proves the headline. If the page
truly needs a KPI hero, make it a composite KPI treatment and say so in
`balance_rationale`.

### Header and slicer band

Every standard report page must reserve a title/header band before content
regions begin.

Required rules:

- Include exactly one placement with `id: page_title`, `kind: textbox`, and
  non-empty `text`.
- The page title must be a descriptive insight title, not a generic label such
  as "Overview" or "Dashboard".
- For 1-3 slicers, place slicers inline in a right-aligned `filters` region that
  shares the reserved header band with the title. The title remains the left
  anchor.
- For more slicers, or for archetype variants that intentionally expose a larger
  filter set, use a side `slicer_rail`/`rail` region and start content to the
  right of that rail.
- No chart, card, table, map, or data visual may start under a slicer region.
  Raising z-order is not a fix for overlap.

### Placements

Each placement assigns one authorable object to one region.

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable unique identifier for the object. |
| `region` | yes | Region name from `layout_contract.grid.regions`. |
| `kind` | yes | PBIR visual type or object kind (`textbox`, `slicer`, `cardVisual`, `barChart`, `lineChart`, `tableEx`, `azureMap`, `aiNarratives`, etc.). |
| `text` | for textbox titles | Required for `page_title`; recommended for annotations. |
| `slot` / `of` | when sharing | 1-indexed subdivision within a shared region. |
| `purpose` | data visuals | One analytical question the visual answers. |
| `field_bindings` | data visuals and slicers | `Table[Column]`, `Table[Measure]`, or role map. |
| `slicer_type` | slicers | `between`, `dropdown`, `list`, or another authorable slicer style. |
| `sort_policy` | bar/column/table visuals | `value_desc`, `value_asc`, `category_asc`, `natural_order`, or `none`. |
| `color_strategy` | color-bearing visuals | `measure_match`, `gradient`, `unique`, `semantic`, or `none`. |
| `insight_basis` | callouts, annotations, Smart Narrative, KPI context | The derived comparison, threshold, rank, anomaly, or dynamic text that makes the element worth its space. |
| `comparison_basis` | comparative visuals and callouts | Baseline being compared: prior period, plan, target, peer median, selected entity, etc. |
| `callout_value_basis` | side callouts / context tiles | Specific evidence that prevents a callout from duplicating an adjacent chart's absolute measure. |

When multiple visuals share a region, `slot` and `of` divide the region along
its longer axis. A placement with no `slot` fills its region.

### Date slicer example variants

Executive and annual-grain pages should usually use a compact Year dropdown or
tile slicer:

```yaml
- id: year_slicer
  region: filters
  kind: slicer
  field_bindings: Date[CalendarYear]
  slicer_type: dropdown
```

Use a full-date `between` slicer only when the page needs day/month range
exploration and the bound field is a renderable Date/DateTime column:

```yaml
- id: date_range_slicer
  region: filters
  kind: slicer
  field_bindings: Date[FullDate]
  slicer_type: between
  insight_basis: "Users compare arbitrary date ranges, not just years."
```

## Common region patterns

### Executive Summary with inline slicers

```yaml
regions:
  header:  [1,  1,  9,  2]
  filters: [9,  1, 13,  2]
  kpis:    [1,  2, 13,  4]
  trend:   [1,  4,  7,  9]
  hero:    [7,  4, 13,  9]
  detail:  [1,  9, 13, 13]
space_audit:
  content_cell_count: 132
  placed_cell_count: 132
  empty_cell_pct: 0
  unplaced_regions: []
  largest_region: { name: detail, pct_of_content: 36 }
  balance_rationale: "KPI strip, two balanced analysis panels, and detail row fill the content area without an unused footer."
```

### Analytical Canvas with filter rail

```yaml
regions:
  header: [1,  1, 13,  2]
  rail:   [1,  2,  3, 13]
  hero:   [3,  2, 13,  7]
  charts: [3,  7, 13, 10]
  detail: [3, 10, 13, 13]
```

### Operational Monitor

```yaml
regions:
  header: [1,  1, 13,  2]
  kpis:   [1,  2, 13,  4]
  tl:     [1,  4,  7,  8]
  tr:     [7,  4, 13,  8]
  bl:     [1,  8,  7, 13]
  br:     [7,  8, 13, 13]
```

## Validation checklist

Before handoff, fix any failure:

- [ ] `generated_by: powerbi-report-cli` and `contract_version` are present.
- [ ] Every non-trivial page has `layout_contract.canvas`,
      `layout_contract.grid.regions`, and `layout_contract.placements`.
- [ ] Every page has a `page_title` placement with non-empty title text.
- [ ] Every placement references a defined region.
- [ ] Regions do not overlap unintentionally.
- [ ] Every non-spacer region has at least one placement.
- [ ] Slicers are in `filters`, `rail`, or `slicer_rail` regions, never in the
      top-left title anchor.
- [ ] Data visuals do not start under header-band slicer regions.
- [ ] `space_audit` is present and reports no unplaced regions.
- [ ] `empty_cell_pct` is within budget (`<= 15` for analytical/operational/
      comparative, `<= 20` for executive/narrative unless justified).
- [ ] Largest-region balance is justified: no non-hero data region starves
      supporting visuals; dominant heroes cite the archetype variant and keep
      supporting charts/tables readable.
- [ ] A bare single-value `cardVisual` is not the largest/dominant region. If a
      card-like KPI hero is used, it is composite and the rationale names its
      context elements.
- [ ] Every side callout, context tile, Smart Narrative, or card-like annotation has
      `insight_basis` or `callout_value_basis` tied to derived insight; no
      callout duplicates the same absolute measure plotted in an adjacent
      visual.
- [ ] Date slicer type matches data grain and audience: executive/annual pages
      use Year dropdown/tile by default; full-date `between` is reserved for
      renderable Date/DateTime fields where arbitrary date-range exploration is
      part of the page question.
- [ ] Every chart/map/table placement has `purpose` and `field_bindings`.
- [ ] Bar/column placements specify `sort_policy`.
- [ ] Every color-bearing measure visual has a `color_strategy` that can be
      resolved against `color_map`.
