# Color Strategy & Patterns

How to apply color overrides on chart data points, when each pattern is safe,
and how to keep the same measure the same hue across multiple visuals.

> **Prerequisite reading:** [`formatting.md` § Selectors](formatting.md#selectors-targeting-specific-data)
> — the dual-entry pattern, metadata selectors, and selector precedence are
> assumed throughout. For palette authoring, see
> [`theming.md` § Data Colors](theming.md#1-data-colors-datacolors).

> Examples use `financials.Revenue` / `financials.Profit` etc. as concrete `queryRef` values — substitute your own `<table>.<measure>` identities.

## Contents

- [Color Strategy Quick Reference](#color-strategy-quick-reference)
- [Pattern: Per-Series Colors](#pattern-per-series-colors)
- [Pattern: Single-Series Default Color](#pattern-single-series-default-color)
- [Pattern: Cross-Visual Measure-Color Consistency](#pattern-cross-visual-measure-color-consistency)
- [Pattern: Different Formatting for Totals vs Data](#pattern-different-formatting-for-totals-vs-data)

## Color Strategy Quick Reference

When the user asks to change chart/bar/series colors, choose the right approach
based on **scope** and **series count**:

| User intent | Approach | Where to edit |
|-------------|----------|---------------|
| **Change the color palette across all visuals** | Update the theme's `dataColors` palette | `theme.json` — see [theming.md § Data Colors](theming.md#1-data-colors-datacolors) |
| **Same measure = same color across all visuals** | Maintain a measure→color mapping; apply explicit `dataPoint.fill`/`defaultColor` per visual | `visual.json → visual.objects.dataPoint` per visual — see [Cross-Visual Measure-Color Consistency](#pattern-cross-visual-measure-color-consistency) below |
| **Change color for a single-series chart** (one measure, no Series role) | `dataPoint.defaultColor` | `visual.json → visual.objects.dataPoint` |
| **Override specific series colors** on one visual | `dataPoint.fill` with `metadata` selectors per series | `visual.json → visual.objects.dataPoint` |
| **Change all colors AND keep series differentiation** | Update theme `dataColors` — do **NOT** use `defaultColor` | `theme.json` |

> **⚠️ Critical:** `defaultColor` applies a **single uniform color** to every
> bar/column/point in the visual — all series and categories become the same
> color, destroying differentiation. **Never use `defaultColor` on charts with
> a Series role or multiple Y measures.**
>
> For clustered bar/column/combo charts, each legend entry should map to its
> own `dataPoint.fill` selector. If all bars and the legend collapse to one
> color, you likely used `defaultColor` or missed a per-series selector.
>
> **⚠️ Palette vs identity:** Theme `dataColors` sets the **palette** but
> assigns colors by **index position** within each visual's projection order,
> not by measure identity. If Visual A binds `[MeasureA, MeasureB]` and
> Visual B binds `[MeasureB, MeasureA]`, `MeasureA` gets `dataColors[0]` in A
> but `dataColors[1]` in B — different colors for the same measure. For
> identity-level consistency, use explicit per-measure color overrides.

## Pattern: Per-Series Colors

```json
"dataPoint": [
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 0, "Percent": 0 } } } } }
    }
  },
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FF6B35'" } } } } }
    },
    "selector": { "metadata": "financials.Revenue" }
  },
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00A878'" } } } } }
    },
    "selector": { "metadata": "financials.Profit" }
  }
]
```

> **Compatibility:** Per-series `dataPoint.fill` with `metadata` selectors
> works on cartesian charts (bar, column, line, area, combo). For non-cartesian
> visuals (pie, donut, scatter, treemap, funnel), `metadata` selectors are
> silently ignored — use `scopeId` selectors instead to color individual data
> points by category value. Use `powerbi-report-author formatting list-objects
> <type>` to confirm `dataPoint` is listed before adding color overrides.

## Pattern: Single-Series Default Color

When a chart has only one measure in the Y axis **and no Series role** (e.g.,
Revenue by Month with a single color), use `defaultColor` instead of `fill`
with a metadata selector. This overrides the theme's auto-assigned color for
all data points in the series:

```json
"dataPoint": [
  {
    "properties": {
      "defaultColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FF6B35'" } } } } }
    }
  }
]
```

For multi-series charts (multiple measures in Y, or a Series grouping role),
use per-measure `fill` with `metadata` selectors as shown in the Per-Series
Colors pattern above, or update the theme `dataColors` palette for consistent
cross-visual coloring.

> Use `powerbi-report-author formatting describe-object <visualType> dataPoint`
> to confirm `defaultColor` is available for a given visual type.

> **⚠️ `fill` vs `defaultColor` trap:** `dataPoint.fill` without a selector
> causes bars/columns to be invisible (data is there — tooltips work — but
> nothing renders). For single-series charts, always use `defaultColor`.
> Only use `fill` with a `metadata` selector for per-series coloring.

## Pattern: Cross-Visual Measure-Color Consistency

When a report has multiple visuals that share the same measures, **always
assign consistent colors so the same measure gets the same hue everywhere.**
Theme `dataColors` alone cannot guarantee this because it assigns colors by
index position (see [Color Strategy Quick Reference](#color-strategy-quick-reference)
above).

**Rule:** Before creating visuals, define a **measure→color mapping** keyed by
`queryRef` (the metadata identity used in selectors), and apply it to every
visual that references those measures.

**Step 1 — Define the mapping** (plan this before writing visual JSON).

For each measure that appears across multiple visuals, assign one color.
**Key by `queryRef` / metadata identity** (e.g. `financials.Revenue`), not by
display name — `queryRef` is what `metadata` selectors match on.

**Example mapping** (substitute your own measures):

| Measure (`queryRef`) | Color | Notes |
|----------------------|-------|-------|
| `financials.Revenue` | `#118DFF` | Theme `dataColors[0]` |
| `financials.Profit` | `#E66C37` | Theme `dataColors[2]` |
| `financials.Cost` | `#D64554` | Theme `dataColors[7]` |

**Step 2 — Apply to multi-measure charts** using `dataPoint.fill` with
`metadata` selectors. **Always use `Literal` hex values** — `ThemeDataColor`
with metadata selectors can silently resolve to wrong colors (white, black):

> **⚠️ Background contrast:** Ensure chosen colors are saturated and contrast
> with the page/VCO background. On white backgrounds, avoid light or
> desaturated hues — pick mid-to-dark saturated colors.

```json
"dataPoint": [
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } }
    },
    "selector": { "metadata": "financials.Revenue" }
  },
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E66C37'" } } } } }
    },
    "selector": { "metadata": "financials.Profit" }
  }
]
```

**Step 3 — Apply to single-measure charts** using `dataPoint.defaultColor`:

```json
"dataPoint": [
  {
    "properties": {
      "defaultColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } }
    }
  }
]
```

> **Non-cartesian charts (pie, donut, scatter, treemap, funnel):**
> `dataPoint.fill` with `metadata` selectors is silently ignored on these
> visual types — they fall back to theme colors. Use `scopeId` selectors
> (per-category value) instead to color individual slices, bubbles, or segments.

## Pattern: Different Formatting for Totals vs Data

```json
"labels": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } }
    }
  },
  {
    "properties": {
      "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
    },
    "selector": { "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }
  },
  {
    "properties": {
      "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#000000'" } } } } },
      "bold": { "expr": { "Literal": { "Value": "true" } } }
    },
    "selector": { "data": [{ "dataViewWildcard": { "matchingOption": 2 } }] }
  }
]
```
