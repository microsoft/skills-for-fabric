# Comparative / Benchmark Dashboard

> **Archetype**: Comparative / Benchmark
> **Theme**: for generated reports, preserve `references/design/assets/base.json` safeguards while adapting `dataColors` to domain; for brownfield, preserve the existing theme unless a theme swap is requested
> **Canvas**: greenfield default FHD 1920 x 1080; preserve existing size for brownfield unless resize is approved
> **Core question**: "Relative to what?"

---

## Job To Be Done

| Dimension | Value |
|-----------|-------|
| Primary user | FP&A analyst, regional manager, product owner |
| Core question | "Relative to what?" — rank, pair, or benchmark 2+ entities |
| Typical queries | "Which region overperforms plan?" "Did Product B close the gap to A YoY?" |
| Success metric | Differences immediately visible — deltas, %, rank shifts, gap-to-benchmark |
| Failure signal | Viewer does arithmetic in their head |
| Design implication | Pre-compute every comparison; show absolute AND relative variance |

---

## Core Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Shared scales** across every small multiple | Independent Y axes silently lie |
| 2 | **Diverging palette centered at zero** | Variance direction is instantly visible |
| 3 | **Consistent ordering** | Sort by recent value or variance desc — NEVER alphabetical (unless lookup) |
| 4 | **Absolute AND relative variance** | Show both when scales differ; Δ and Δ% side by side |
| 5 | **Align pairs, don't stack** | Clustered bars / dumbbells, NOT stacked bars |
| 6 | **Every comparison has a baseline — draw it** | Reference line, constant line, or dedicated series |
| 7 | **IBCS where audience is trained** | Adopt wholesale in finance; cherry-pick notation elsewhere |

---

## IBCS Primer

| Concept | Description |
|---------|-------------|
| **SUCCESS** | Say, Unify, Condense, Check, Express, Simplify, Structure |
| **Visual vocabulary** | Filled = Actual (AC), Outlined = Prior Year (PY) / Budget (BU), Hatched = Forecast (FC) |
| **Variance columns** | Δ absolute + Δ% side by side |
| **Category axis** | Left-aligned text |
| **Time axis** | Always horizontal |

### When to Use IBCS

| Context | Recommendation |
|---------|---------------|
| Finance / controlling audience trained in IBCS | Adopt full visual vocabulary |
| Mixed audience | Cherry-pick: variance columns + Δ/Δ% notation |
| Consumer-facing / marketing | Skip IBCS; use standard charting |

> **Caution**: IBCS is a coherent system — partial adoption can confuse viewers who expect the full vocabulary.

---

## Layout Variants

Pick ONE variant based on the comparison shape from Step 0. Do NOT mix. Default to **A** only when signals genuinely tie — record the signal that drove your pick in `variant_rationale`.

| Signal (from semantic model + brief) | Variant |
|---|---|
| 4–6 entities to compare across one metric over time (AC vs PY trend per entity) | **A. Side-by-Side** |
| 2–4 paired comparisons (AC vs Plan, this-year vs last-year) — pair-wise framing | **B. Stacked-Pairs** |
| Ranking many entities (8+) on a single metric — rank shift / position is the point | **C. Slope-Graph-First** |

---

### Variant A — Side-by-Side (default, small multiples + headline)

Headline variance chart on the left, optional big-idea callout on the right,
small-multiples trellis below. Use the callout only when it adds derived
comparison insight (variance %, delta, gap-to-benchmark, rank shift, exception
threshold, or generated explanatory text). If the only available value is the
same absolute measure already plotted in the headline chart, skip the callout
and expand the variance chart, add a compact detail table, or use the space for
filter/context notes.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE + comparison dimension + period              │  h=56
├──────────────────────────────┬───────────────────────────┤
│                              │                           │
│  HEADLINE VARIANCE           │  OPTIONAL CALLOUT         │
│  (tornado / ranked Δ bar)    │  "EMEA is 12% below plan" │  h=200
│  sorted by abs(Δ) desc       │                           │
│                              │                           │
├──────────────────────────────┴───────────────────────────┤
│  SMALL MULTIPLES (4–6 panels, shared Y axis)             │
│  ┌─Ent A─┐ ┌─Ent B─┐ ┌─Ent C─┐ ┌─Ent D─┐ ┌─Ent E─┐    │  h=260
│  │ AC|PY │ │ AC|PY │ │ AC|PY │ │ AC|PY │ │ AC|PY │    │
│  │ Δ%:+4%│ │ Δ%-12%│ │ Δ%:+1%│ │ Δ%:-3%│ │ Δ%:+8%│    │
│  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘    │
├──────────────────────────────────────────────────────────┤
│  methodology · outlier notes · refresh · source          │  h=40
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title | 56 px | Page title + comparison dimension + period selector |
| Headline variance | 200 px | Ranked Δ bar or tornado + optional big-idea callout with derived insight |
| Small multiples | 260 px | 4–6 panels, shared Y, AC \| PY per panel, Δ% annotation |
| Footer | 40 px | Methodology, outlier notes, refresh timestamp |

---

### Variant B — Stacked-Pairs

One paired comparison per row. Each row pairs an entity (or measure) with its baseline. Use when the comparison is fundamentally pair-wise and the entities aren't peers of each other.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE + period + scenario [AC ▼] [vs PY ▼]         │  h=56
├──────────────────────────────────────────┬───────────────┤
│  PAIR 1 — Revenue: AC vs Plan            │ Δ: +$4.2M     │  h=140
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ AC          │ Δ%: +6%       │
│  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ Plan          │ ↑ favorable    │
├──────────────────────────────────────────┼───────────────┤
│  PAIR 2 — Margin %: AC vs Plan           │ Δ: -1.4 pp    │  h=140
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ AC               │ Δ%: -7%       │
│  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ Plan            │ ↓ unfavorable  │
├──────────────────────────────────────────┼───────────────┤
│  PAIR 3 — Orders: AC vs PY               │ Δ: +1,240     │  h=140
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ AC                │ Δ%: +9%       │
│  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ PY                   │ ↑ favorable    │
├──────────────────────────────────────────┴───────────────┤
│  PAIR 4 — (similar)                                       │  h=140
├──────────────────────────────────────────────────────────┤
│  methodology · outlier notes · refresh · source          │  h=40
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title | 56 px | Title + period + scenario toggle (AC / PY / BU / FC) |
| Pair row 1–N | 140 px each | Bar pair (left ~960px) + variance summary block (right ~272px) |
| Footer | 40 px | Methodology, outlier notes, refresh timestamp |

> Each row is a complete comparison with its own variance summary — Δ absolute, Δ%, and a directional arrow. **Maximum 4 pair rows** per page; beyond that, split into multiple pages or switch to A.

---

## Callout Evidence Rule

Callouts are conditional. A callout placement must name its
`callout_value_basis` in the design brief:

| Acceptable basis | Example |
|---|---|
| Absolute + relative variance | `Sales vs Plan: -$1.2M (-8.4%)` |
| Rank shift | `Region moved from #5 to #2 YoY` |
| Gap-to-benchmark | `Margin trails peer median by 3.1 pp` |
| Threshold exception | `3 segments below SLA target` |
| Dynamic narrative measure | `Top driver text` measure generated from model logic |

Implementation may be a textbox, compact KPI/context tile, or Smart Narrative
(`aiNarratives`). Choose Smart Narrative only when the summary needs to respond
dynamically to filters and the `authoring` mode verifies the formatting/query
mechanics for the target report version.

Do **not** create a callout whose only value is the same absolute measure used
by the adjacent bar/line/table. A plain `Total Sales` card next to a `Total
Sales by Region` chart is redundant; the chart already carries that measure.

---

### Variant C — Slope-Graph-First

A slope graph (or dot plot) ranking many entities dominates the page. Position on the shared scale IS the point — readers see who moved up/down at a glance. Supporting bar chart shows current absolute values.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE + comparison dimension + period              │  h=56
├──────────────────────────────────────────────────────────┤
│                                                          │
│  SLOPE GRAPH — entity rank/position, period A → period B │
│                                                          │
│  Ent01 ●─────────────────────────────● Ent01             │  h=420
│  Ent02 ●╲           ╱──────────────● Ent03               │
│  Ent03 ●─╲─────────╱──────────────●  Ent02              │
│  Ent04 ●──╲───────╱────────────────● Ent04               │
│  Ent05 ●───╲─────╱─────────────────● Ent06               │
│  Ent06 ●────╲───╱──────────────────● Ent05               │
│  ...                                                     │
│        period A                          period B        │
├──────────────────────────────────────────────────────────┤
│  SUPPORTING — current-period ranked bar, all entities    │  h=200
│  Ent01 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                            │
│  Ent03 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                                │
│  Ent02 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                                 │
├──────────────────────────────────────────────────────────┤
│  methodology · refresh · source                          │  h=40
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title | 56 px | Title + comparison dimension + period selector |
| Slope graph | 420 px | All entities, position = metric value at start/end period; crossing lines show rank shifts |
| Supporting bar | 200 px | Same entities ranked by current-period absolute value |
| Footer | 40 px | Methodology, refresh, source |

> PBI has no native slope graph — simulate with a `lineChart` (categorical X axis: period A, period B). Highlight gainers and losers in two distinct colors; everything else grey. Use the supporting bar to give absolute scale that the slope graph hides.

---

## Chart Selection

### Use

| Visual type | Role | Best for |
|-------------|------|----------|
| Paired / clustered bar | AC vs PY side by side | Direct entity comparison |
| Dumbbell plot (simulated) | Gap = variance | Before / after or actual vs target |
| Variance column | Standalone Δ bars diverging at zero | Deviation magnitude + direction |
| Small multiples trellis | Shared Y, one panel per entity | Time trend across entities |
| Ranked horizontal bar | Sorted by metric desc | Performance ranking |
| Tornado / butterfly | Back-to-back bars | Two-entity head-to-head |
| `waterfallChart` | Additive contribution | Bridge from budget to actual |
| Dot plot / barbell | Position on shared scale | Multiple entities on one axis |

### Do NOT Use

| Visual type | Reason |
|-------------|--------|
| Stacked bar | Obscures per-segment comparison; inner segments lack common baseline |
| `pieChart` / `donutChart` | Cannot show variance or deviation |
| `gauge` | Single-entity; no comparison affordance |
| Radar / spider | Distorts magnitude via area encoding |

---

## Variance Encoding Standards

| Rule | Detail |
|------|--------|
| **Anchor at zero** | NEVER truncate the variance axis; zero must be visible |
| **Show Δ and Δ% together** | Absolute variance for scale; relative for context |
| **Prefix consistently** | Use Δ for absolute, Δ% for relative — everywhere |
| **Annotate outliers** | Callout box on any Δ > 2σ or any business-meaningful threshold |
| **NEVER dual-axis Δ + Δ%** | Two variance axes mislead; use side-by-side columns instead |
| **Sign convention** | Positive = favorable (green); negative = unfavorable (red). State explicitly. |

---

## Color & Typography

### Diverging Palette

| Position | Color | Hex | Usage |
|----------|-------|-----|-------|
| Positive extreme | Blue | `#2166AC` | Strong overperformance |
| Positive moderate | Light blue | `#67A9CF` | Moderate overperformance |
| Neutral / zero | Grey | `#F7F7F7` | At target |
| Negative moderate | Light red | `#EF8A62` | Moderate underperformance |
| Negative extreme | Red | `#B2182B` | Strong underperformance |

> **Alternative**: Brown-Blue-Green (BrBG) for color-blind safety.

### IBCS Purist Palette

| Element | Color |
|---------|-------|
| Actual (AC) | Black, filled |
| Prior Year (PY) / Budget (BU) | Black, outlined |
| Forecast (FC) | Black, hatched |
| Negative variance | Red, filled |
| Everything else | Grey |

### Typography

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Page title | 16 pt | SemiBold | Includes comparison framing |
| Visual title | 11 pt | SemiBold | — |
| Data labels / Δ values | 10 pt | Regular | Tabular / lining numerals MANDATORY |
| Axis labels | 9–10 pt | Regular | Humanist sans for readability |
| Methodology footnote | 8–9 pt | Light | Bottom of page |

> **Tabular numerals**: All variance values MUST use tabular (monospaced) figures so columns align visually.

---

## Interaction Design (Moderate)

| Pattern | PBI mechanism | Purpose |
|---------|--------------|---------|
| Period slicer | Synced slicer: YTD, QTD, MTD | Time frame selection |
| Scenario slicer | AC / PY / BU / FC toggle | Switch comparison baseline |
| Sort toggle | Field parameter or bookmark set | Alpha / ranked-actual / ranked-Δ |
| Drill-through on panel | `actionButton` from small multiple | Deep dive on one entity |
| Bookmark sets | Top-10 / Bottom-10 / Full view | Quick variance focus |
| Rich tooltips | AC / PY / Δabs / Δ% / rank change | Full context on hover |

### Sort Toggle Implementation

| Method | Mechanism | Trade-off |
|--------|-----------|-----------|
| Field parameter | Swap sort column dynamically | Requires field parameter setup |
| Bookmark set | Pre-configured sort states | Simpler but static |
| Slicer + SWITCH measure | Slicer drives sort logic | Most flexible, most complex |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## PBI Formatting Reference

### Comparison Charts

| Visual | Key properties | Purpose |
|--------|---------------|---------|
| `clusteredBarChart` / `clusteredColumnChart` | Two series: AC + PY | Side-by-side comparison |
| `smallMultiplesChart` | `valueAxis.start` / `end` (shared) | Controlled trellis |
| `lineAndClusteredColumnChart` | Combo: bars + line | Absolute (bars) + trend (line) |
| `waterfallChart` | `increase` / `decrease` / `total` colors | Additive bridge |
| `ribbonChart` | Rank-change encoding | Period-over-period rank shift |
| `scatterChart` | X = metric A, Y = metric B, quadrants | Performance matrix |

### Variance Formatting

| Property path | Value | Purpose |
|---------------|-------|---------|
| `referenceLine` / `constantLine` | Zero, target, benchmark | Draw comparison baseline |
| CF `fillRule` | Diverging at zero | Color bars by deviation direction |
| CF `dataBar` | In matrix cells | Inline magnitude encoding |
| CF cell background | Diverging palette | Heat-map in tabular layout |

### Navigation & State

| Property path | Value | Purpose |
|---------------|-------|---------|
| `actionButton` | `Drillthrough` action | Navigate from panel to detail |
| Field parameter | Sort-by swap | Dynamic sort toggle |
| `sortBy` + `sortDirection` | Column + Desc | Ranked ordering |
| Theme `dataColors` | Paired: AC color + PY color | Consistent series identity |
| Theme `sentimentColors` | Diverging: positive + negative | Variance encoding |

### Known Gaps

| Need | Status | Workaround |
|------|--------|------------|
| Native dumbbell chart | Not available | Simulate with `barChart` + error bars or dot plot |
| Native tornado chart | Not available | Simulate with back-to-back bars or use AppSource |
| IBCS hatching | Not native | Use pattern fills via theme or custom visual |

---

## Decision Checklist

| # | Check | Pass? |
|---|-------|-------|
| 1 | Every small multiple shares the same Y axis | ☐ |
| 2 | Variance axis includes zero (not truncated) | ☐ |
| 3 | Both Δ and Δ% shown where scales differ | ☐ |
| 4 | Sort order is by variance or value, not alphabetical | ☐ |
| 5 | Diverging palette centered at zero | ☐ |
| 6 | Baseline drawn (reference line / constant line) | ☐ |
| 7 | AC and PY visually distinct (fill vs outline or separate bars) | ☐ |
| 8 | Tabular numerals used for all variance values | ☐ |
| 9 | Outliers annotated with callouts | ☐ |
| 10 | Viewer never does arithmetic — all comparisons pre-computed | ☐ |
