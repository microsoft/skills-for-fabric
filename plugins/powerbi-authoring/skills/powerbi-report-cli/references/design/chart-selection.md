# Chart Selection Decision Framework

## Core Principle

Match the chart to the **question**, not the data type.
Every visualization answers one of a small set of analytical questions:
comparison, composition, distribution, relationship, trend, ranking, deviation, flow, or status.
Identify the question first, then pick the chart that answers it most directly.

> Sources: Abela's Chart Chooser, FT Visual Vocabulary, Schwabish taxonomy.

---

## Primary Decision Matrix

| Purpose | Primary Choice | Use When | Alternative | Avoid |
|---|---|---|---|---|
| **Comparison** | Horizontal bar | ≥7 items or long labels | Clustered bar, dot plot | Pie, donut, 3D bars |
| **Composition** | 100% stacked bar, treemap | Showing parts of a whole | Waterfall (additive breakdown) | Pie with >5 slices |
| **Distribution** | Histogram, box plot | Shape of spread matters | Violin, strip/jitter plot | Single bar showing mean |
| **Relationship** | Scatter plot | Testing correlation / clusters | Bubble (encodes 3rd variable) | Dual-axis line |
| **Trend** | Line chart | Continuous time axis, ≥7 points | Column chart (≤6 periods) | Smoothed line hiding volatility |
| **Ranking** | Sorted horizontal bar | Top-N / bottom-N emphasis | Lollipop, bump chart | Unsorted bars |
| **Deviation** | Diverging bar | +/− variance from a reference | Bullet graph, waterfall | Bar with arbitrary baseline |
| **Flow** | Sankey | Redistribution across stages | Funnel (monotone shrinkage) | Sankey for tiny flows |
| **Single KPI** | Compact card + sparkline/context | Executive glance metric | Bullet graph (vs target) | Gauge or oversized bare-card hero |
| **Geospatial** | Symbol/choropleth map (`azureMap`) | Location or spatial distribution carries the message | Sorted bar when the question is pure country/region ranking | Legacy maps or bubble maps without a size legend |

---

## Secondary Selection Filters

Apply these after the primary decision to refine or override:

| Filter | Rule |
|---|---|
| **Precision vs pattern** | Need exact values → table/matrix. Need shape/trend → chart. |
| **Cardinality** | >15 categories → group/filter or small multiples. Never plot 40 bars. |
| **Part-to-whole cardinality** | ≤5 → donut, 6–15 → sorted bar, >15 → treemap |
| **Magnitude span** | >100× range → log scale or separate charts. Do not let one bar dominate. |
| **Mixed units** | Revenue ($) vs count (#) → separate visuals. Never dual-axis to merge. |
| **Audience tolerance** | Exec: cards + 1 hero chart. Analyst: scatter, box plot acceptable. |
| **Data density** | Sparse → dot plot, strip. Dense → histogram, hex-bin scatter. |
| **Comparison mode** | Absolute values → bar. Relative share → 100% stacked. Rate of change → line. |

---

## Power BI Visual Type Crosswalk

Maps each analytical purpose to native PBI visual types.

| Purpose | Native PBI Visual | Notes |
|---|---|---|
| Comparison | `barChart` (horizontal) | Set `orientation: horizontal` |
| Comparison (clustered) | `clusteredBarChart` | Limit to 2-3 series |
| Composition | `hundredPercentStackedBarChart`, `treemap` | Treemap for hierarchical |
| Distribution | `histogram` (via binning on column chart) | No native box plot — use custom visual |
| Relationship | `scatterChart` | Enable `play axis` for time animation |
| Trend | `lineChart` | Use `lineChart` not `areaChart` for precision |
| Trend (few periods) | `columnChart` | ≤6 discrete time periods only |
| Ranking | `barChart` sorted desc | Apply Top N filter or sortBy |
| Deviation | `waterfallChart`, `barChart` with reference line | Diverging bar needs conditional formatting |
| Flow | `decompositionTreeVisual` | Native Sankey limited — consider custom |
| Single KPI | `cardVisual` | Pair card with `lineChart` sparkline |
| Geospatial | `azureMap` | Prefer for location/spatial distribution; use sorted `barChart` when geography is only a ranked category |
| Table/detail | `tableEx`, `pivotTable` | Use when precision > pattern |

---

## Archetype Applicability

Which chart families suit each report archetype:

| Archetype | Preferred Charts | Acceptable | Avoid |
|---|---|---|---|
| **Executive** | Card, KPI, single hero line/bar, bullet | Waterfall, treemap | Scatter, box plot, histogram, matrix |
| **Operational** | Card + trend sparkline, table, RAG indicators | Bar, funnel | Scatter, Sankey, violin |
| **Analytical** | Scatter, histogram, box plot, small multiples, matrix | Any chart with clear purpose | Gauge, 3D, pie |
| **Narrative** | Annotated line, waterfall, before/after bar | Slope chart | Cluttered multi-series |
| **Comparative** | Small multiples, grouped bar, slope chart | Scatter (group color) | Stacked bar for comparison |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## Decision Checklist

Before committing to a visual type, verify:

1. **What question does this chart answer?** — State it as a sentence.
2. **Is the chart type the most direct encoding for that answer?** — Check the matrix above.
3. **Does the cardinality fit?** — Bars ≤15, pie ≤5, lines ≤5 series, scatter up to hundreds.
4. **Is the baseline honest?** — Bars start at 0. Lines may break axis only if clearly marked.
5. **Would a simpler chart work?** — If a card answers the question, keep it compact; do not give a bare single-value card the hero/largest region.
6. **Does the archetype allow it?** — Executive pages reject scatter plots; analytical pages reject gauges.
7. **Can the reader decode it in <5 seconds?** — If not, simplify or split.

---

## Quick-Reference: FT Visual Vocabulary Mapping

| FT Category | Recommended PBI Visuals |
|---|---|
| Deviation | Diverging bar (cond. format), waterfall |
| Correlation | Scatter, bubble |
| Ranking | Sorted bar, lollipop (custom) |
| Distribution | Histogram (binned column), strip (custom) |
| Change over time | Line, column, area (use sparingly) |
| Part-to-whole | Treemap, 100% stacked bar, donut (≤5 slices only) |
| Magnitude | Bar, paired bar, lollipop |
| Spatial | `azureMap` symbol/choropleth map; sorted bar if only ranking locations |
| Flow | Sankey (custom), funnel, decomposition tree |

---

## Cardinality Limits by Visual Type

| Visual Type | Max Categories | Max Series | Behavior When Exceeded |
|---|---|---|---|
| Horizontal bar | 15–20 | 1 (best), 2–3 clustered | Scroll or "Other" bucket beyond limit |
| Clustered bar | 10 | 2–3 | Beyond 3 series, switch to small multiples |
| Line chart | n/a (continuous axis) | 5 lines max | Beyond 5, lines become spaghetti |
| Pie / donut | 5 max | 1 | Beyond 5, slices become unreadable |
| Scatter | n/a (hundreds OK) | 3–5 color groups | Beyond 5 groups, use facets |
| Treemap | 20–30 tiles | 1–2 levels | Deep nesting becomes unreadable |
| Small multiples | 4–16 panels | 1 per panel | Beyond 16, cognitive overload |
| Table / matrix | Unlimited rows | 5–8 columns visible | Scroll for more; hide low-value columns |
| Card | 1 | 1 | One value per card by design |
| Map | 200–500 points | 1 measure | Beyond 500, aggregate to regions |

---

## Encoding Accuracy Hierarchy

Based on Cleveland & McGill's perceptual experiments, ranked from most to least accurate:

| Rank | Encoding | Accuracy | Best For |
|---|---|---|---|
| 1 | Position on common scale | ★★★★★ | Bar chart, dot plot, scatter |
| 2 | Position on non-aligned scale | ★★★★ | Small multiples (shared axis) |
| 3 | Length | ★★★★ | Bar chart (length = value) |
| 4 | Direction / slope | ★★★ | Line chart (trend direction) |
| 5 | Angle | ★★ | Pie chart — this is why pies are imprecise |
| 6 | Area | ★★ | Bubble chart, treemap |
| 7 | Volume | ★ | 3D charts — never use |
| 8 | Color saturation / hue | ★ | Heatmap (pattern, not precision) |

**Implication**: When precision matters, prefer bars and dots (position encoding).
When pattern/shape matters, heatmaps and area charts are acceptable.

---

## Series Count Decision Tree

```text
How many data series?
├── 1 series
│   ├── Single value → Card
│   ├── Over time → Line chart
│   └── Across categories → Sorted bar
├── 2–3 series
│   ├── Same unit → Clustered bar or multi-line
│   └── Different units → Separate charts (NOT dual axis)
├── 4–5 series
│   ├── Comparison focus → Small multiples
│   └── Composition focus → Stacked bar (100%)
└── 6+ series
    ├── Group into "Top 5 + Other"
    └── Or use small multiples grid
```

---

## Edge Cases & Exceptions

| Scenario | Default Rule | Exception | Condition |
|---|---|---|---|
| Bar chart baseline | Always 0 | Non-zero OK | Only for line/dot plots where relative change matters |
| Pie chart | Avoid | Acceptable | ≤5 slices, exact % labeled, composition is the question |
| Area chart | Avoid (implies volume) | Acceptable | Stacked area for composition over time, ≤3 series |
| Dual axis | Never | Acceptable with caution | Only if both series share the same unit (e.g., $ vs $) |
| 3D | Never | No exceptions | — |
| Sorted bars | Always sort by value | Alphabetical OK | When the category order is inherently meaningful (months, stages) |
| Smoothed lines | Avoid | Acceptable | Moving average overlay (labeled as such) alongside raw data |
