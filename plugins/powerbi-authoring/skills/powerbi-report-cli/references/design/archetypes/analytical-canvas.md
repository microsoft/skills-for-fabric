# Analytical Canvas

> **Archetype**: Analytical Canvas
> **Theme**: for generated reports, preserve `references/design/assets/base.json` safeguards while adapting `dataColors` to domain; for brownfield, preserve the existing theme unless a theme swap is requested
> **Canvas**: greenfield default FHD 1920 x 1080; preserve existing size for brownfield unless resize is approved · F-pattern
> **Success metric**: Questions answered per session

---

## Job To Be Done

| Dimension | Value |
|-----------|-------|
| Primary user | Analyst, data scientist, business partner |
| Session trigger | Live question: "Why did EMEA revenue dip in Q3?" |
| Workflow | Form hypothesis → slice by dimension → drill outlier → pivot measure → bookmark finding |
| Success metric | Questions answered per session; reproducibility of each cut |
| Failure signal | Analyst exports to Excel to "really look at it" |
| Design implication | Density is a feature; 10–12 visuals acceptable; interactivity is primary |

---

## Core Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Shneiderman mantra** | Overview → zoom → filter → details-on-demand |
| 2 | **Linked views** | One selection cross-filters all visuals |
| 3 | **Density is a feature** | 10–12 visuals OK; small type OK; information over white-space |
| 4 | **Expose the dimensions** | Field parameters, visible slicer rail, measure picker |
| 5 | **Cleveland-McGill** | Position and length over hue and area encodings |
| 6 | **Show current filter state** | Breadcrumb or filter summary always visible |
| 7 | **Every cut reproducible** | Bookmarks, personalized visuals, shareable URLs |

---

## Layout Variants

Pick ONE variant based on the data shape from Step 0. Do NOT mix. Default to **A** only when signals genuinely tie — record the data signal that drove your pick in `variant_rationale`.

| Signal (from semantic model + brief) | Variant |
|---|---|
| 4+ slicers needed (filter rail justified at ≥50% column fill) | **A. Filter-Rail** |
| 1–3 slicers — small filter set, content needs full width | **B. Inline-Slicers** |
| Comparing many entities along similar axes (regions, products, segments) — small-multiples is the analytical tool | **C. Small-Multiples-Grid** |

---

### Variant A — Filter-Rail (default for dense exploration)

The canonical F-pattern: vertical filter rail on the left, hero analysis on the right, supporting visuals below, detail matrix at the bottom.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE                    filter breadcrumb / pills │  h=56
├────────────┬─────────────────────────────────────────────┤
│            │                                             │
│  FILTER    │  HERO VISUAL                                │
│  RAIL      │  (scatter / trend / decomp tree)            │  h=320
│  200-240px │                                             │
│  4-6       │                                             │
│  slicers   │                                             │
│            │                                             │
├────────────┼─────────────────────┬───────────────────────┤
│            │  SUPPORTING 1       │  SUPPORTING 2         │  h=200
│  (cont'd)  │  (small multiples)  │  (stacked / grouped)  │
├────────────┴─────────────────────┴───────────────────────┤
│  DETAIL MATRIX — sortable, drill-down, expandable        │  h=240
├──────────────────────────────────────────────────────────┤
│  footer                                                  │  h=24
└──────────────────────────────────────────────────────────┘
```

| Zone | Size | Content |
|------|------|---------|
| Title bar | h=56 | Page title + active filter breadcrumb |
| Filter rail | 200–240 px wide, left | 4–6 slicers, reset button |
| Hero visual | Remaining width × 320 px | Primary analysis chart |
| Supporting visuals | 2-up, h=200 | Small multiples + grouped/stacked bar |
| Detail matrix | Full width, h=240 | Sortable, drill-down, expandable rows |
| Footer | h=24 | Source, timestamp |

> Rail is justified only when slicers fill ≥50% of the rail height. With three 56px dropdowns + 8px gaps = 184px in a ~660px column = 28% fill — that's the threshold to switch to **B**.

---

### Variant B — Inline-Slicers (1–3 slicers, content gets full width)

No vertical rail. Slicers go inline with the title row. The freed left column becomes content space — usually a wider hero or a third supporting visual.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE              [Slicer 1] [Slicer 2] [Slicer 3]│  h=56
├──────────────────────────────────────────────────────────┤
│                                                          │
│  HERO VISUAL — full width                                │  h=320
│  (scatter / trend / decomp / hero comparison)            │
│                                                          │
├──────────────────┬───────────────────┬───────────────────┤
│  SUPPORTING 1    │  SUPPORTING 2     │  SUPPORTING 3     │  h=200
│  (line)          │  (clustered bar)  │  (small mult.)    │
├──────────────────┴───────────────────┴───────────────────┤
│  DETAIL MATRIX — full width                              │  h=240
├──────────────────────────────────────────────────────────┤
│  footer                                                  │  h=24
└──────────────────────────────────────────────────────────┘
```

| Zone | Size | Content |
|------|------|---------|
| Title bar | h=56 | Title (left ~700px) + 1–3 slicers (right) |
| Hero visual | Full 1232px × 320 px | Primary analysis chart, gets ~250px more width than A |
| Supporting visuals | 3-up, h=200 | One extra panel vs. A — use it for a third comparison angle |
| Detail matrix | Full width, h=240 | Sortable, drill-down, expandable rows |
| Footer | h=24 | Source, timestamp |

> Slicer widths: 160px (or 120px for short labels like "Year"), h=56, 16px gaps. The title block fills the remaining width on the left.

---

### Variant C — Small-Multiples-Grid

When the analytical question IS comparison across many entities (regions, products, channels), the small-multiples grid becomes the page — not a supporting visual. No single hero.

```text
┌──────────────────────────────────────────────────────────┐
│  PAGE TITLE              [Metric ▼] [Period ▼] [Sort ▼]  │  h=56
├──────────────────────────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ Ent1 │ │ Ent2 │ │ Ent3 │ │ Ent4 │ │ Ent5 │ │ Ent6 │ │  h=200
│  │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ Ent7 │ │ Ent8 │ │ Ent9 │ │Ent10 │ │Ent11 │ │Ent12 │ │  h=200
│  │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │ ~∿~  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
├──────────────────────────────────────────────────────────┤
│  RANKED COMPARISON — sortable bar across all entities    │  h=200
├──────────────────────────────────────────────────────────┤
│  footer                                                  │  h=24
└──────────────────────────────────────────────────────────┘
```

| Zone | Size | Content |
|------|------|---------|
| Title bar | h=56 | Title + 2–3 field-parameter dropdowns (metric / period / sort) |
| Trellis grid | 2 rows × h=200 | 6–12 small panels, **shared Y axis mandatory** |
| Ranked comparison | Full width, h=200 | One bar/dot chart that ranks all entities by current metric |
| Footer | h=24 | Source, timestamp |

> Every panel uses the **same Y-axis range** — independent axes silently distort the comparison. Use field parameters in the title row so the analyst can swap measure or sort order without breaking the trellis.

---

## Chart Selection

### Use

| Visual type | Role | Notes |
|-------------|------|-------|
| Slicer rail | Dimension filtering | 3–6 visible; dropdown for high cardinality |
| `scatterChart` | Relationship / outlier detection | Enable `playAxis` for time animation |
| `smallMultiplesChart` | Trend by dimension | Shared Y axis mandatory |
| `decompositionTreeVisual` | AI-assisted root-cause drill | Automatic split by best attribute |
| `pivotTable` / `matrix` | Detail on demand | Drill-up / drill-down; stepped layout |
| `filledMap` | Geographic dimension | Choropleth for regional analysis |
| Field parameters | Measure / dimension swap | Let analyst choose what to plot |

### Do NOT Use

| Visual type | Reason |
|-------------|--------|
| KPI cards (dominating) | This is analysis, not status monitoring |
| `gauge` | Low density; not analytical |
| `donutChart` | Poor angle encoding; use bar instead |
| 3D visuals | Distortion; no analytical value |
| Infographic icons | Decoration; wastes analysis space |

---

## Filter Rail Design

| Property | Spec | Rationale |
|----------|------|-----------|
| Count | 3–6 visible slicers | Beyond 6, use filter pane or hierarchy |
| Position | Left-anchored, 200–240 px wide | F-pattern: eye scans left rail first |
| State visibility | Each slicer shows current selection | Analyst always knows active filters |
| Reset button | `actionButton` → clear all slicers | One-click return to base state |
| Sync groups | Pin filters across pages | `syncGroup` for consistent context |
| Search | Enable on cardinality > 20 | Dropdown search for long lists |

### Control Selection Table

| Dimension type | Slicer control | Example |
|----------------|---------------|---------|
| Low cardinality (< 8) | Button / tile list | Region, Segment |
| Medium cardinality (8–50) | Dropdown with search | Product category |
| High cardinality (> 50) | Dropdown + search, single-select | Customer name |
| Hierarchy | Tree / hierarchy slicer | Geo → Country → City |
| Date | Relative date / between | Last N months, custom range |

---

## Color & Typography

### Palette Strategy

| Encoding | Palette type | Notes |
|----------|-------------|-------|
| Categorical (identity) | 8–12 distinct hues | Regions, products, segments |
| Sequential (magnitude) | Single-hue gradient | Revenue, count, intensity |
| Diverging (deviation) | Two-hue with neutral midpoint | Variance from target |

### Focus + Context

| State | Treatment |
|-------|-----------|
| Selected / highlighted | Full accent color, 100 % opacity |
| Context / unselected | Grey `#BDBDBD`, 30 % opacity |
| Cross-filtered out | Grey `#E0E0E0`, 20 % opacity |

### Typography

| Element | Size | Weight |
|---------|------|--------|
| Page title | 14 pt | SemiBold |
| Visual title | 11 pt | SemiBold |
| Body / labels | 10 pt | Regular |
| Axis labels (floor) | 9 pt | Regular |
| Tooltip text | 10 pt | Regular |

> WCAG AA: Ensure 4.5:1 contrast even at 9 pt. Test grey-on-white carefully.

---

## Interaction Design

This is the richest-interaction archetype. All patterns below are expected.

| Pattern | PBI mechanism | Purpose |
|---------|--------------|---------|
| Cross-filter + highlight | Default visual interactions | Linked views across all charts |
| Drill-down / drill-up | Matrix hierarchy, chart drill | Navigate aggregation levels |
| Field parameters | Swap measure or dimension | Analyst controls what is plotted |
| Personalized visuals | `personalizeVisuals: true` | End-user customizes without edit mode |
| Bookmarks | Named cuts, shareable | Reproduce and share specific findings |
| Page tooltips | Rich detail on hover | 320 × 240 tooltip pages |
| Edit interactions | Customize cross-filter behavior | Remove noisy cross-filter links |
| Sync slicers | `syncGroup` across pages | Consistent filter context across pages |

### Interaction Precedence

| Priority | When conflicts arise… |
|----------|-----------------------|
| 1 | Cross-filter is the default; opt out selectively |
| 2 | Drill-down on hierarchical visuals takes priority over cross-filter |
| 3 | Field parameters apply to the host visual only |
| 4 | Bookmarks capture slicer state + visual state together |

---

> Anti-patterns: see references/design/anti-patterns.md

---

## PBI Formatting Reference

### Slicers

| Property path | Value | Purpose |
|---------------|-------|---------|
| `slicer > slicerMode` | `Dropdown` / `List` / `Between` | Match to dimension type |
| `slicer > search` | `true` (cardinality > 20) | Filterable list |
| `syncGroup` | Named group ID | Cross-page filter sync |

### Analytical Visuals

| Visual | Key properties | Purpose |
|--------|---------------|---------|
| `decompositionTreeVisual` | AI splits, bars | Root-cause analysis |
| `pivotTable` / `matrix` | `subtotals`, `steppedLayout`, drill | Detail on demand |
| `scatterChart` | `playAxis`, `size` role, `legend` | Relationship + outlier + time |
| `smallMultiplesChart` | Shared `valueAxis.start` / `end` | Controlled comparison by dimension |

### Page-Level Settings

| Property path | Value | Purpose |
|---------------|-------|---------|
| `personalizeVisuals` | `true` | Enable end-user customization |
| Field parameters | Measure / dimension swap | Dynamic analysis |
| `editInteractions` | Per-visual configuration | Tune cross-filter behavior |
| Bookmarks | Named, with slicer + visual state | Reproducible cuts |
| Page tooltip canvas | 320 × 240 | Rich hover detail |

---

## Decision Checklist

| # | Check | Pass? |
|---|-------|-------|
| 1 | Filter rail shows 3–6 slicers with visible state | ☐ |
| 2 | Reset button clears all slicers | ☐ |
| 3 | Active filters shown in breadcrumb / pills | ☐ |
| 4 | Hero visual supports drill-down or field parameter swap | ☐ |
| 5 | Small multiples share Y axis | ☐ |
| 6 | Cross-filter behavior tuned (edit interactions) | ☐ |
| 7 | Bookmarks capture reproducible findings | ☐ |
| 8 | Page fits the approved canvas without scrolling | ☐ |
| 9 | ≤ 12 visuals on page | ☐ |
| 10 | Personalized visuals enabled | ☐ |
