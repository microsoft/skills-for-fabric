# Cartesian Visuals (Bar, Column, Line, Scatter) - Part 2

## Contents

  - [Conditional Colors](#conditional-colors)
  - [labels — Data Labels](#labels--data-labels)
  - [legend](#legend)
  - [categoryAxis / valueAxis](#categoryaxis--valueaxis)
  - [layout — Gap & Series Order](#layout--gap--series-order)
  - [ribbonBands — Stacked Charts](#ribbonbands--stacked-charts)
  - [totals — Stacked Charts](#totals--stacked-charts)
  - [zoom — Slider Controls](#zoom--slider-controls)
  - [lineStyles — Line Specific](#linestyles--line-specific)
  - [markers — Marker Styling](#markers--marker-styling)
  - [seriesLabels — End-of-Line Labels](#serieslabels--end-of-line-labels)


Continuation of `cartesian.md`. Open this file directly from the skill reference index.

### Conditional Colors

Routing sequence: start with
formatting-overview.md (see `formatting-overview.md`) for any appearance change,
use this Cartesian guide when chart family, roles, or bindings are involved,
then use conditional-formatting.md (see `conditional-formatting.md`) for the exact
target, selector, and expression. If an existing chart's bindings are
unchanged, go directly from the formatting overview to the
conditional-formatting reference.

For data-driven gradients, rules, and field-value colors, use the target matrix
and exact expression patterns in
conditional-formatting.md § Chart target capability
matrix (see `conditional-formatting.md`, section `chart-target-capability-matrix`).

Quick routing:

| Visual result | Object/property |
|---------------|-----------------|
| Bar/column or scatter color | `dataPoint.fill` |
| Full non-combo line/area series color | `dataPoint.fill` |
| Single-series non-combo marker color by category | `dataPoint.fill` |
| Single-series non-combo line segment color | `lineStyles.strokeColor` |
| Data-label color | `labels.color` |

Selector routing depends on what the rule repeats over:

- Single-series data points:
  `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }`
- Categories, line segments, or per-category line markers:
  `{ "data": [{ "roles": ["Category"] }] }`
- Dynamic legend series:
  `{ "data": [{ "roles": ["Series"] }], "hierarchyMatching": 1 }`

Role names vary by visual type. Use `catalog describe` and preserve any
Desktop-authored `metadata` selector when a rule targets one measure's labels.

For line charts, prefer inheritance over duplicate rules:

- `legend.matchLineColor: true` keeps legend symbols aligned with line color.
- `seriesLabels.seriesMatchColor: true` keeps end labels aligned with series
  color.
- `lineStyles.areaMatchStrokeColor: true` keeps shaded area aligned with line
  color.

Conditional line-segment coloring works only for a single line series and uses
`lineStyles.strokeColor` with the category-role selector. A categorical legend
creates multiple series and disables segment formatting. Full-series line
color on non-combo charts uses the historical `dataPoint.fill` path.

Combo charts still expose `dataPoint.fill` for line-series color and
`lineStyles.markerColor` for marker color, but do not use Gradient, Rules, or
Field Value conditional formatting on those targets. Use these properties only
for static combo-series styling; see the capability matrix for details.

For marker-specific requirements and anti-patterns, use
conditional-formatting.md § Line, marker, legend, and series-label
consistency (see `conditional-formatting.md`, section `line-marker-legend-and-series-label-consistency`).

Scatter `categoryLabels.color` supports one static color for all category
labels. It does not conditionally color each label to match its bubble.

### labels — Data Labels

Basic labels — enable for all series (from barChart reference visual):

```json
"labels": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } }
    }
  },
  {
    "properties": {
      "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
      "titleBold": { "expr": { "Literal": { "Value": "true" } } },
      "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
      "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 2, "Percent": 0.4 } } } } },
      "labelContentLayout": { "expr": { "Literal": { "Value": "'MultiLine'" } } },
      "horizontalAlignment": { "expr": { "Literal": { "Value": "'center'" } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Profit)"
    }
  }
]
```

The first entry (no selector) enables labels globally. The second entry uses
a metadata selector to customize labels for a specific measure — adding title,
bold, background, and multi-line layout.

**Dynamic label title/detail** — bind label content to aggregation expressions
using a `dataViewWildcard` selector (from clusteredBarChart reference visual):

```json
"labels": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "labelPosition": { "expr": { "Literal": { "Value": "'InsideCenter'" } } },
      "labelOverflow": { "expr": { "Literal": { "Value": "true" } } },
      "optimizeLabelDisplay": { "expr": { "Literal": { "Value": "true" } } },
      "labelContainerMaxWidth": { "expr": { "Literal": { "Value": "174D" } } },
      "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
      "titleContentType": { "expr": { "Literal": { "Value": "'Custom'" } } },
      "enableDetailDataLabel": { "expr": { "Literal": { "Value": "true" } } },
      "detailColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 2, "Percent": 0.6 } } } } },
      "detailTransparency": { "expr": { "Literal": { "Value": "20D" } } },
      "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
      "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 2, "Percent": 0 } } } } },
      "backgroundTransparency": { "expr": { "Literal": { "Value": "40D" } } },
      "labelContentLayout": { "expr": { "Literal": { "Value": "'MultiLine'" } } }
    }
  },
  {
    "properties": {
      "dynamicLabelTitle": {
        "expr": {
          "Aggregation": {
            "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "ListOfOrders" } }, "Property": "State" } },
            "Function": 3
          }
        }
      },
      "dynamicLabelDetail": {
        "expr": {
          "Aggregation": {
            "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "ListOfOrders" } }, "Property": "Ship Mode" } },
            "Function": 3
          }
        }
      }
    },
    "selector": {
      "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
      "highlightMatching": 1
    }
  }
]
```

The `dataViewWildcard` selector with `matchingOption: 1` applies to all data
point instances. `Function: 3` is Min aggregation. Run
`powerbi-report-author formatting describe-object <type> labels` for all
available properties.

### legend

Bar/column example (from clusteredBarChart reference visual):

```json
"legend": [{
  "properties": {
    "position": { "expr": { "Literal": { "Value": "'TopCenter'" } } },
    "titleText": { "expr": { "Literal": { "Value": "'Sales for Categories'" } } }
  }
}]
```

Line chart example with marker rendering (from lineChart reference visual):

```json
"legend": [{
  "properties": {
    "legendMarkerRendering": { "expr": { "Literal": { "Value": "'lineAndMarker'" } } },
    "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": -0.25 } } } } },
    "titleText": { "expr": { "Literal": { "Value": "'Line Chart'" } } },
    "bold": { "expr": { "Literal": { "Value": "false" } } },
    "italic": { "expr": { "Literal": { "Value": "true" } } },
    "underline": { "expr": { "Literal": { "Value": "true" } } }
  }
}]
```

Run `powerbi-report-author formatting describe-object <type> legend` for all
available properties and valid enum values.

### categoryAxis / valueAxis

categoryAxis example (from clusteredBarChart reference visual):

```json
"categoryAxis": [{
  "properties": {
    "fontFamily": { "expr": { "Literal": { "Value": "'Georgia'" } } },
    "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
    "titleText": { "expr": { "Literal": { "Value": "'Category'" } } },
    "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0 } } } } },
    "innerPadding": { "expr": { "Literal": { "Value": "26L" } } },
    "maxMarginFactor": { "expr": { "Literal": { "Value": "24L" } } }
  }
}]
```

valueAxis example (from clusteredBarChart reference visual):

```json
"valueAxis": [{
  "properties": {
    "start": { "expr": { "Literal": { "Value": "0D" } } },
    "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
    "labelPrecision": { "expr": { "Literal": { "Value": "2L" } } },
    "gridlineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
    "gridlineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
    "gridlineThickness": { "expr": { "Literal": { "Value": "4D" } } }
  }
}]
```

Run `powerbi-report-author formatting describe-object <type> categoryAxis` and
`powerbi-report-author formatting describe-object <type> valueAxis` for all
available properties and valid enum values.

#### Invert Axis (`invertAxis`)

Use `invertAxis` to reverse the order of values on an axis.

- On **categoryAxis**: reverses the category order (e.g., alphabetical Z→A
  instead of A→Z, or bottom-to-top instead of top-to-bottom on bar charts).
- On **valueAxis**: reverses the numeric direction (e.g., values grow
  right-to-left instead of left-to-right on bar charts).

> **When the user asks to "invert" a bar or column chart**, apply
> `invertAxis: true` to **both** `categoryAxis` and `valueAxis` unless they
> explicitly specify only one axis. Setting `categoryAxis` alone only reorders
> the categories; setting `valueAxis` alone only flips the value direction.
> Both together fully inverts the chart.

```json
"categoryAxis": [{
  "properties": {
    "invertAxis": { "expr": { "Literal": { "Value": "true" } } }
  }
}],
"valueAxis": [{
  "properties": {
    "invertAxis": { "expr": { "Literal": { "Value": "true" } } }
  }
}]
```

#### Log Scale (`logAxisScale`)

> **⚠️ Confirm with the user before setting `logAxisScale: true`** if any bound
> measure or column can produce zero or negative values. Logarithms of zero or
> negative numbers are mathematically undefined. PBI Desktop silently falls
> back to linear scale with a warning:
> *"The axis changed to a linear scale to accommodate both positive and negative values."*
>
> **Workflow before enabling `logAxisScale`:**
> 1. Inspect the columns/measures bound to the axis — can they produce zero or
>    negative values? (e.g., Profit, Discount, Net Change often go negative)
> 2. If negatives are possible, **warn the user before applying log scale**.
>    Explain that log scale is mathematically undefined for zero/negative values
>    and PBI will silently fall back to linear. Use the `ask_user` tool to
>    present alternatives and let the user choose:
>    - Filter out zero/negative values (visual-level or page-level filter)
>    - Switch to a different column/measure that is always positive (e.g., Sales, Quantity)
>    - Use a DAX measure with `ABS()` (requires semantic model change)
>    - Keep linear scale with `labelDisplayUnits` for readability instead
> 3. Apply `logAxisScale: true` only after the user resolves the negative values
>    via one of the alternatives above, or confirms that all values are positive.

```json
"valueAxis": [{
  "properties": {
    "logAxisScale": { "expr": { "Literal": { "Value": "true" } } }
  }
}]
```

### layout — Gap & Series Order

Clustered charts example:

```json
"layout": [{
  "properties": {
    "seriesOrderSorted": { "expr": { "Literal": { "Value": "true" } } },
    "seriesOrderReversed": { "expr": { "Literal": { "Value": "false" } } },
    "clusteredGapSize": { "expr": { "Literal": { "Value": "16D" } } }
  }
}]
```

Stacked charts (`barChart`, `columnChart`) use different properties
(e.g., `stackedGapSize` instead of `clusteredGapSize`). Run
`powerbi-report-author formatting describe-object <type> layout` to discover
available properties for each visual type.

### ribbonBands — Stacked Charts

Ribbon connectors link same-series segments across categories. Available on
`barChart` and `columnChart`.

```json
"ribbonBands": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } }
    }
  },
  {
    "properties": {
      "fillTransparency": { "expr": { "Literal": { "Value": "7D" } } },
      "borderShow": { "expr": { "Literal": { "Value": "true" } } },
      "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
      "borderSize": { "expr": { "Literal": { "Value": "4D" } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Profit)"
    }
  }
]
```

First entry: static `show` toggle. Subsequent entries: per-measure styling
via metadata selectors. Run
`powerbi-report-author formatting describe-object <type> ribbonBands` for
all available properties.

### totals — Stacked Charts

Total labels on stacked bars/columns. Available on `barChart` and
`columnChart`.

Example with background and per-instance color:

```json
"totals": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.5 } } } } },
      "backgroundTransparency": { "expr": { "Literal": { "Value": "68D" } } }
    }
  },
  {
    "properties": {
      "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } }
    },
    "selector": {
      "data": [{ "dataViewWildcard": { "matchingOption": 1 } }]
    }
  }
]
```

Run `powerbi-report-author formatting describe-object <type> totals` for all
available properties.

### zoom — Slider Controls

Example:

```json
"zoom": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "showOnValueAxis": { "expr": { "Literal": { "Value": "true" } } },
    "showLabels": { "expr": { "Literal": { "Value": "true" } } },
    "showTooltip": { "expr": { "Literal": { "Value": "true" } } }
  }
}]
```

Run `powerbi-report-author formatting describe-object <type> zoom` for all
available properties.

### lineStyles — Line Specific

For line charts. Set line width, style, interpolation, and markers. Use
metadata selectors for per-series styling. Run
`powerbi-report-author formatting describe-object lineChart lineStyles` for the
full property list and valid enum values.

**Visual types with `lineStyles`:** areaChart, lineChart, stackedAreaChart,
lineStackedColumnComboChart, lineClusteredColumnComboChart,
hundredPercentStackedAreaChart.

**Key properties:**

| Property | Type | Description |
|----------|------|-------------|
| `strokeShow` | bool | Show/hide the line |
| `strokeWidth` | numeric (D) | Line width in pixels |
| `strokeColor` | fill/color | Line color |
| `strokeTransparency` | numeric (D) | Transparency (0–100) |
| `lineStyle` | enum | `'solid'`, `'dashed'`, `'dotted'`, `'custom'` |
| `strokeDashCap` | enum | `'none'`, `'round'`, `'square'` |
| `strokeLineJoin` | enum | Line join style |
| `showMarker` | bool | Show data-point markers |
| `markerShape` | enum | `'circle'`, `'square'`, `'diamond'`, `'triangle'`, `'x'`, `'shortDash'`, `'longDash'`, `'plus'` |
| `markerSize` | numeric (D) | Marker size in pixels |
| `markerColor` | fill/color | Marker fill color |
| `lineChartType` | enum | Interpolation: `'linear'`, `'smooth'`, `'step'` |

```json
"lineStyles": [
  {
    "properties": {
      "strokeWidth": { "expr": { "Literal": { "Value": "5D" } } },
      "lineChartType": { "expr": { "Literal": { "Value": "'step'" } } },
      "interpolationStep": { "expr": { "Literal": { "Value": "'after'" } } },
      "showMarker": { "expr": { "Literal": { "Value": "true" } } },
      "markerShape": { "expr": { "Literal": { "Value": "'diamond'" } } },
      "markerSize": { "expr": { "Literal": { "Value": "9D" } } },
      "strokeLineJoin": { "expr": { "Literal": { "Value": "'bevel'" } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Profit)"
    }
  },
  {
    "properties": {
      "lineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
      "strokeWidth": { "expr": { "Literal": { "Value": "4D" } } },
      "lineChartType": { "expr": { "Literal": { "Value": "'smooth'" } } },
      "interpolationSmooth": { "expr": { "Literal": { "Value": "'cardinal'" } } },
      "strokeTransparency": { "expr": { "Literal": { "Value": "11D" } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Quantity)"
    }
  },
  {
    "properties": {
      "areaShow": { "expr": { "Literal": { "Value": "true" } } },
      "showMarker": { "expr": { "Literal": { "Value": "true" } } }
    }
  }
]
```

A static entry (no selector) sets defaults for all series. Per-series entries
with metadata selectors override specific measures.

### markers — Marker Styling

Controls marker appearance independently of `lineStyles.showMarker`. Available
on all line/area visual types **plus scatterChart**.

| Property | Type | Description |
|----------|------|-------------|
| `transparency` | numeric (D) | Marker transparency (0–100) |
| `rotation` | numeric (D) | Rotation angle |
| `borderShow` | bool | Show marker border |
| `borderWidth` | numeric (D) | Border width |
| `borderColorMatchFill` | bool | Match border to fill color |
| `borderColor` | fill/color | Marker border color |
| `borderTransparency` | numeric (D) | Border transparency |

### seriesLabels — End-of-Line Labels

Labels at the end of each line series (lineChart only). Run
`powerbi-report-author formatting describe-object lineChart seriesLabels` for
all available properties.
