# Executive Summary Dashboard

> **Archetype**: Executive Summary
> **Theme**: for generated reports, preserve `references/design/assets/base.json` safeguards while adapting `dataColors` to domain; for brownfield, preserve the existing theme unless a theme swap is requested
> **Canvas**: greenfield default FHD 1920 x 1080; preserve existing size for brownfield unless resize is approved · `pageAlignment: Middle`
> **Scan-time target**: ≤ 10 seconds to comprehension

---

## Job To Be Done

| Dimension | Value |
|-----------|-------|
| Primary user | CEO, GM, VP — time-poor decision-maker |
| Session trigger | Monday-morning skim before leadership standup |
| Core question | "Is the business on or off track, and why?" |
| Success metric | State comprehension in ≤ 10 s |
| Failure signal | Viewer opens a second artifact to understand status |
| Design implication | Everything beyond headline + KPIs belongs behind drill-through |

---

## Core Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Descriptive title** — thesis sentence, not label ("Revenue is 4 % above plan" not "Executive Dashboard Q3") | Eliminates interpretation step |
| 2 | **3–6 KPI hard cap** | Miller's 7 ± 2; beyond 6, comprehension collapses |
| 3 | **Period-over-period context mandatory** | Absolute + delta + direction arrow on every KPI |
| 4 | **Sparklines over full trend charts** | Convey trajectory without consuming scan budget |
| 5 | **One hero chart proving the headline** | Anchors the "why" behind the insight |
| 6 | **3-color semantic palette** | Green / Red / Neutral + grey — nothing else |
| 7 | **Drill-through for all detail** | Keeps surface clean; depth is one click away |

---

## Layout Variants

Pick ONE variant based on the data shape from Step 0. Do NOT mix. Default to **A** only when signals genuinely tie — record the data signal that drove your pick in `variant_rationale`.

| Signal (from semantic model + brief) | Variant |
|---|---|
| 3–4 KPIs **and** ONE clear hero metric with a meaningful trend/chart | **A. Hero-Right** |
| 5–6 KPIs of comparable importance, no single hero metric | **B. KPI-Strip** |
| 1–2 KPIs **and** a strong narrative chart (waterfall, decomp, big trend) | **C. Headline-Hero** |

---

### Variant A — Hero-Right (default)

KPI cards on the left, hero chart on the right. The classic executive Z-pattern.
The hero is the explanatory chart, not a blown-up single card.

```text
┌──────────────────────────────────────────────────────────┐
│  TITLE BAR (h=48)                         [date slicer] │  ← thesis sentence
│  subtitle / as-of date (h=24)                           │
├────────┬────────┬────────┬────────┬──────────────────────┤
│ KPI 1  │ KPI 2  │ KPI 3  │ KPI 4  │   HERO CHART        │  h=160
│ +spark │ +spark │ +spark │ +spark │   (bar / line)       │
├────────┴────────┴────────┴────────┼──────────────────────┤
│  VARIANCE SNAPSHOT                │  RISK / EXCEPTION    │  h=240
│  (ranked bar, top-5 movers)       │  LIST (table, ≤8)    │
├───────────────────────────────────┴──────────────────────┤
│  source · refresh · active filters · [drill buttons]     │  h=32
└──────────────────────────────────────────────────────────┘
```

| Zone | Height | Content |
|------|--------|---------|
| Title bar | 48 px | Descriptive title + subtitle |
| KPI row + hero | 160 px | 4 cards (sparklines on) + 1 hero chart |
| Analysis row | 240 px | Variance snapshot + risk/exception list |
| Footer | 32 px | Source, refresh, filter state, drill buttons |

> KPI cards take the left ~830px (4 × 200 + gaps); hero chart takes the right ~400px. Sparklines on cards convey trajectory; the hero chart proves the headline.

---

### Variant B — KPI-Strip

Full-width KPI row across the top, dual analysis charts below. No single hero — the KPI row IS the message.

```text
┌──────────────────────────────────────────────────────────┐
│  TITLE BAR (h=48)                         [date slicer] │
├──────┬──────┬──────┬──────┬──────┬──────────────────────┤
│KPI 1 │KPI 2 │KPI 3 │KPI 4 │KPI 5 │ KPI 6 (optional)    │  h=120
│value │value │value │value │value │ value               │
│ +Δ   │ +Δ   │ +Δ   │ +Δ   │ +Δ   │ +Δ                  │
├──────┴──────┴──────┴──────┼──────┴──────────────────────┤
│  TREND — last 6 periods   │  TOP MOVERS — ranked bar    │  h=300
│  (line, multi-measure)    │  (top-5 by Δ%)              │
├───────────────────────────┴──────────────────────────────┤
│  source · refresh · filters · [drill buttons]            │  h=32
└──────────────────────────────────────────────────────────┘
```

The callout row is conditional: use it for a thesis sentence, variance summary,
exception note, or dynamic narrative that explains the hero chart. Do not fill
it with a bare card repeating a measure already visible in the hero chart or KPI
strip.

| Zone | Height | Content |
|------|--------|---------|
| Title bar | 48 px | Descriptive title + subtitle |
| KPI strip | 120 px | 5–6 cards equal-width across full canvas |
| Analysis row | 300 px | Multi-measure trend + ranked top movers |
| Footer | 32 px | Source, refresh, filter state, drill buttons |

> **Sparklines OFF** on cards in this variant — the KPI strip already conveys breadth, and inline sparklines would compete with the trend chart below. Cards lose ~24px of value-area in exchange.

---

### Variant C — Headline-Hero

One or two KPI cards stacked on the left, a single dominant narrative chart on the right. Use when the headline IS the chart (a waterfall, decomp, or big annotated trend).
The KPI cards may be larger than strip cards, but they are context panels; the
dominant hero remains the chart.

```text
┌──────────────────────────────────────────────────────────┐
│  TITLE BAR (h=48)                         [date slicer] │
├────────────┬─────────────────────────────────────────────┤
│            │                                             │
│  KPI 1     │  HERO CHART                                 │
│  (large)   │  (waterfall / decomp / annotated trend)     │  h=400
│            │                                             │
│  KPI 2     │  Annotations and reference lines            │
│  (large)   │  carry the explanation                      │
│            │                                             │
├────────────┴─────────────────────────────────────────────┤
│  CALLOUT — thesis sentence supporting the chart          │  h=80
├──────────────────────────────────────────────────────────┤
│  source · refresh · filters · [drill buttons]            │  h=32
└──────────────────────────────────────────────────────────┘
```

The callout row is conditional: use it for a thesis sentence, variance summary,
exception note, or dynamic narrative that explains the hero chart. Do not fill
it with a bare card repeating a measure already visible in the hero chart or KPI
strip.

| Zone | Height | Content |
|------|--------|---------|
| Title bar | 48 px | Descriptive title + subtitle |
| Hero block | 400 px | 1–2 large KPI cards (left ~280px) + dominant chart (right) |
| Callout | 80 px | Textbox: one-sentence interpretation of the hero chart |
| Footer | 32 px | Source, refresh, filter state, drill buttons |

> Annotations on the hero chart matter more than KPI count. Use reference lines, shaded periods, or arrow shapes to point at the moment that made the point.

---

## Chart Selection

### Use

| Visual type | Role | Sizing / Notes |
|-------------|------|----------------|
| `cardVisual` | KPI display (value + delta + label) | One per metric |
| `lineChart` (sparkline) | Inline trend on KPI cards | 120 × 48 px, all chrome off |
| `barChart` | Ranked variance (top movers) | Sort desc by absolute delta |
| `actionButton` | Drill-through navigation | One per target page |

### Do NOT Use

| Visual type | Reason |
|-------------|--------|
| `scatterChart` | Requires interpretation time > 10 s |
| `treemap` | Area encoding unreliable at small size |
| `histogram` | Statistical; wrong audience |
| `pivotTable` / `matrix` | Detail belongs behind drill-through |
| `gauge` | Consumes space, poor information density |
| `donutChart` | Part-to-whole not the question asked |

---

## Color & Typography

| Element | Spec | Token |
|---------|------|-------|
| Descriptive title | 20–24 pt SemiBold | `foreground` |
| KPI value | 28–36 pt Bold | `foreground` |
| KPI label | 10–11 pt Regular | `secondaryForeground` |
| Delta / change | 12 pt SemiBold | Semantic color (green ↑ / red ↓) |
| Body text | 11 pt Regular | `foreground` |

**Palette (3 + grey)**

| Role | Hex | Usage |
|------|-----|-------|
| Positive | `#107C10` | Delta up, on-track KPI |
| Negative | `#D13438` | Delta down, off-track KPI |
| Neutral | `#605E5C` | Flat / within-tolerance |
| Chrome / baseline | `#E1DFDD` | Grid lines, borders, backgrounds |

> **Numeral rule**: Always tabular / lining figures — proportional numerals misalign columns.

---

## Interaction Design

| Pattern | Implementation | Notes |
|---------|---------------|-------|
| Drill-through from KPI | `actionButton` with `drillthrough` action + `altText` | One button per detail page |
| Page tooltip on KPI card | Tooltip page 320 × 240, `tooltipType: ReportPage` | Shows 24 h sparkline + context |
| Period toggle | Bookmarks: vs-week / vs-plan | ONE toggle, not N slicers |
| Date filter | Single date picker, top-right | Maximum ONE slicer on page |

### Do NOT Use

| Anti-pattern | Why |
|--------------|-----|
| Slicer panels / filter pane | Configuration tax; scan-time > 10 s |
| Cross-filter webs | Unpredictable state changes on passive page |
| Multiple slicer combos | Adds cognitive load incompatible with ≤ 10 s goal |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## PBI Formatting Reference

### Card / CardVisual

| Property path | Value | Purpose |
|---------------|-------|---------|
| `calloutValue > fontSize` | `36` | KPI prominence |
| `categoryLabel > show` | `true` | Metric name below value |
| `referenceLabel > show` | `true` | Delta / period-over-period |
| `visualHeader > show` | `false` | Clean card surface |
| `border > show` | `false` | Borderless card |

### Sparkline (lineChart)

| Property path | Value | Purpose |
|---------------|-------|---------|
| `categoryAxis > show` | `false` | No X axis labels |
| `valueAxis > show` | `false` | No Y axis labels |
| `labels > show` | `false` | No data labels |
| `markers > show` | `false` | Clean line only |
| Size | 160 × 48 px | Inline with KPI card |

### Variance Bar (barChart)

| Property path | Value | Purpose |
|---------------|-------|---------|
| `fillRule` (CF) | Diverging at zero | Green positive / red negative |
| `sortByColumn` | Desc by absolute delta | Worst first |

### Page & Navigation

| Property path | Value | Purpose |
|---------------|-------|---------|
| `page > width` | `1920` for greenfield | FHD default unless user requests another size |
| `page > height` | `1080` for greenfield | 16:9 ratio |
| `pageAlignment` | `Middle` | Centered rendering |
| `actionButton > action` | `Drillthrough` | Navigate to detail |
| `actionButton > altText` | Descriptive label | Accessibility |
| Page tooltip canvas | 320 × 240 | Compact context tooltip |
| `tooltipType` | `ReportPage` | Enable custom tooltip page |

---

## Decision Checklist

Before shipping, verify every row:

| # | Check | Pass? |
|---|-------|-------|
| 1 | Title is a thesis sentence, not a label | ☐ |
| 2 | KPI count ≤ 6 | ☐ |
| 3 | Every KPI shows absolute + delta + direction | ☐ |
| 4 | One hero chart directly supports the headline | ☐ |
| 5 | Palette is exactly 3 semantic colors + grey | ☐ |
| 6 | All detail is behind drill-through | ☐ |
| 7 | Page scans in ≤ 10 s (test with a colleague) | ☐ |
| 8 | Maximum ONE slicer visible | ☐ |
| 9 | Visual headers hidden on all cards | ☐ |
| 10 | Footer shows data source + refresh timestamp | ☐ |
