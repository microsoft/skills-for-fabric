# Comparative Benchmark - Part 2

Continuation of `comparative-benchmark.md`. Open this file directly from the skill reference index.

## Contents

- [Variance Encoding Standards](#variance-encoding-standards)
- [Color & Typography](#color--typography)
- [Interaction Design (Moderate)](#interaction-design-moderate)
- [PBI Formatting Reference](#pbi-formatting-reference)
- [Decision Checklist](#decision-checklist)

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
