# Cartesian Visuals (Bar, Column, Line)

> Examples use illustrative `<table>.<measure>` identifiers — substitute your own.

<!-- TOC -->
- [Visual Type Families](#visual-type-families)
  - [Column/Bar Family](#columnbar-family)
  - [Line Family](#line-family)
- [Roles & Cardinality](#roles--cardinality)
- [Query Patterns](#query-patterns)
  - [Y Binding — Measure vs Aggregation](#y-binding--measure-vs-aggregation)
  - [Multiple Y Measures](#multiple-y-measures)
  - [Category Drill Hierarchy](#category-drill-hierarchy)
  - [Date Hierarchy Binding](#date-hierarchy-binding)
  - [Sort Definition](#sort-definition)
- [Formatting Patterns](#formatting-patterns)
  - [Per-Series Metadata Selector Pattern](#per-series-metadata-selector-pattern)
  - [dataPoint — Color Assignment](#datapoint--color-assignment)
  - [labels — Data Labels](#labels--data-labels)
  - [legend](#legend)
  - [categoryAxis / valueAxis](#categoryaxis--valueaxis)
    - [Invert Axis (`invertAxis`)](#invert-axis-invertaxis)
    - [Log Scale (`logAxisScale`)](#log-scale-logaxisscale)
  - [layout — Gap & Series Order](#layout--gap--series-order)
  - [ribbonBands — Stacked Charts](#ribbonbands--stacked-charts)
  - [totals — Stacked Charts](#totals--stacked-charts)
  - [zoom — Slider Controls](#zoom--slider-controls)
  - [lineStyles — Line Specific](#linestyles--line-specific)
  - [markers — Marker Styling](#markers--marker-styling)
  - [seriesLabels — End-of-Line Labels](#serieslabels--end-of-line-labels)
  - [y2Axis — Secondary Axis](#y2axis--secondary-axis)
  - [smallMultiplesLayout — Rows Role](#smallmultipleslayout--rows-role)
- [Minimal Examples](#minimal-examples)
  - [Bar Chart (Minimal)](#bar-chart-minimal)
  - [Clustered Bar Chart (with Per-Series Color)](#clustered-bar-chart-with-per-series-color)
- [Complete Examples](#complete-examples)
  - [Clustered Bar Chart with Per-Measure Colors](#clustered-bar-chart-with-per-measure-colors)
  - [Stacked Column Chart with Ribbons and Totals](#stacked-column-chart-with-ribbons-and-totals)
  - [Line Chart with Y2 Secondary Axis and Per-Series Styling](#line-chart-with-y2-secondary-axis-and-per-series-styling)
<!-- /TOC -->

Use these visual types for axis-based charts that plot data against category
and value axes. All share the `Category` + `Y` role pattern but differ in
orientation, stacking, and line/marker support.

> **Schema version rule:** Copy the `$schema` URL from an existing `visual.json` in the same report.
> If no reference exists, fall back to `https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json`.
> When editing existing visuals, **preserve the existing schema version** —
> do not upgrade unless the task explicitly requires it.

## Visual Type Families

### Column/Bar Family

| PBIR `visualType` | Orientation | Stacking |
|---|---|---|
| `columnChart` | Vertical | Stacked |
| `barChart` | Horizontal | Stacked |
| `clusteredColumnChart` | Vertical | Clustered (side-by-side) |
| `clusteredBarChart` | Horizontal | Clustered (side-by-side) |

### Line Family

| PBIR `visualType` | Fill |
|---|---|
| `lineChart` | Line only |

## Roles & Cardinality

Run `powerbi-report-author catalog describe <type>` to discover the exact
roles, display names, kind (Grouping/Measure), and cardinality for each visual
type:

```bash
powerbi-report-author catalog describe barChart
powerbi-report-author catalog describe lineChart
```

Example output for `catalog describe lineChart`:

```json
{
  "requiredRoles": ["Category", "Y"],
  "optionalRoles": ["Series", "Y2", "Rows", "Tooltips"],
  "maxPerRole": { "Series": 1 },
  "roles": {
    "Category":  { "displayName": "Axis",             "kind": "Grouping" },
    "Series":    { "displayName": "Legend",            "kind": "Grouping" },
    "Y":         { "displayName": "Values",            "kind": "Measure"  },
    "Y2":        { "displayName": "Secondary values",  "kind": "Measure"  },
    "Rows":      { "displayName": "Small multiples",   "kind": "Grouping" },
    "Tooltips":  { "displayName": "Tooltips",          "kind": "Measure"  }
  },
  "formattingObjects": [
    "categoryAxis", "dataPoint", "labels", "legend", "lineStyles",
    "markers", "plotArea", "seriesLabels", "smallMultiplesLayout",
    "valueAxis", "y2Axis", "zoom", ...
  ]
}
```

**Key differences:** Line charts have `Y2` (secondary axis) but no
`Gradient`. Column/bar charts have `Gradient` but no `Y2`.

## Query Patterns

### Y Binding — Measure vs Aggregation

The `Y` role accepts both expression types:

- **`Measure`** — for authored semantic-model measures (DAX). Use when the
  field is a measure defined in TMDL:
  ```json
  "field": {
    "Measure": {
      "Expression": { "SourceRef": { "Entity": "<Table>" } },
      "Property": "<MeasureName>"
    }
  }
  ```
  `queryRef`: `"<Table>.<Measure>"`, `nativeQueryRef`: `"<Measure>"`

- **`Aggregation`** — for raw columns with an aggregation function. Use when
  aggregating a column directly (Sum, Avg, Count, etc.):
  ```json
  "field": {
    "Aggregation": {
      "Expression": {
        "Column": {
          "Expression": { "SourceRef": { "Entity": "<Table>" } },
          "Property": "<Column>"
        }
      },
      "Function": 0
    }
  }
  ```
  `queryRef`: `"Sum(<Table>.<Column>)"`, `nativeQueryRef`: `"Sum of <Column>"`

  Aggregation Function values: `0`=Sum, `1`=Avg, `2`=Count, `3`=Min, `4`=Max,
  `5`=CountNonNull, `6`=Median, `7`=StandardDeviation, `8`=Variance

> **⚠️ nativeQueryRef format:** Aggregation projections require
> `"Sum of <Column>"` (not just `"<Column>"`). Using the raw column name
> causes blank visuals with no error. See `references/authoring/expressions.md` for details.

### Multiple Y Measures

There are two ways to get multiple series (lines/bars) in a chart:

1. **Series role** — put a grouping column (e.g., `Sub-Category`) in the
   `Series` role. Power BI splits one measure into multiple series based on
   the column's distinct data values. Each unique value becomes a separate
   line/bar color, and the legend should mirror that series identity.
2. **Multiple Y projections** — add multiple measures (e.g., Sales, Profit)
   to the `Y` role. Each measure becomes its own series. No `Series` role
   needed.

> **Clustered bar/column rule:** if you want distinct colors for each bar
> group, use per-series `dataPoint.fill` selectors or let the theme `dataColors`
> palette assign series colors. Do **not** use `defaultColor` on clustered
> charts — it forces every bar and legend entry to the same color.

To use approach 2, add multiple projections to `Y`:

```json
"Y": {
  "projections": [
    {
      "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Revenue" } }, "Function": 0 } },
      "queryRef": "Sum(Sales.Revenue)",
      "nativeQueryRef": "Sum of Revenue"
    },
    {
      "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Cost" } }, "Function": 0 } },
      "queryRef": "Sum(Sales.Cost)",
      "nativeQueryRef": "Sum of Cost"
    }
  ]
}
```

### Category Drill Hierarchy

When multiple fields are added to the `Category` role (e.g., Year → Quarter →
Month), they form a **drill hierarchy**. The chart initially shows only the
top level. Users can then drill down through the levels interactively.

The `active` property controls which levels are **currently visible** when
the report loads — it saves the drill state:

- **Top level only** (default): set `active: true` on the first projection only
- **Drilled down to a level**: set `active: true` on all levels up to and
  including the visible level

```json
"Category": {
  "projections": [
    {
      "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Product" } }, "Property": "Category" } },
      "queryRef": "Product.Category",
      "nativeQueryRef": "Category",
      "active": true
    },
    {
      "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Product" } }, "Property": "SubCategory" } },
      "queryRef": "Product.SubCategory",
      "nativeQueryRef": "SubCategory",
      "active": true
    }
  ]
}
```

In this example both levels have `active: true`, so the chart loads showing
data drilled down to SubCategory.

> **Cartesian charts only.** The `active` property is specific to drill
> hierarchies on cartesian Category projections. Do **not** set `active` on
> tableEx or pivotTable projections — it triggers drill behavior and causes
> columns to disappear (see SKILL.md anti-patterns).

### Date Hierarchy Binding

When a date column has a `variation` in the semantic model (auto date
hierarchy), the Category binding uses `PropertyVariationSource` → `Hierarchy`
→ `HierarchyLevel` nesting. Each level is a separate projection:

```json
"Category": {
  "projections": [
    {
      "field": {
        "HierarchyLevel": {
          "Expression": {
            "Hierarchy": {
              "Expression": {
                "PropertyVariationSource": {
                  "Expression": { "SourceRef": { "Entity": "<Table>" } },
                  "Name": "Variation",
                  "Property": "<DateColumn>"
                }
              },
              "Hierarchy": "Date Hierarchy"
            }
          },
          "Level": "Year"
        }
      },
      "queryRef": "<Table>.<DateColumn>.Variation.Date Hierarchy.Year",
      "nativeQueryRef": "<DateColumn> Year",
      "active": true
    },
    {
      "field": {
        "HierarchyLevel": {
          "Expression": {
            "Hierarchy": {
              "Expression": {
                "PropertyVariationSource": {
                  "Expression": { "SourceRef": { "Entity": "<Table>" } },
                  "Name": "Variation",
                  "Property": "<DateColumn>"
                }
              },
              "Hierarchy": "Date Hierarchy"
            }
          },
          "Level": "Quarter"
        }
      },
      "queryRef": "<Table>.<DateColumn>.Variation.Date Hierarchy.Quarter",
      "nativeQueryRef": "<DateColumn> Quarter",
      "active": false
    }
  ]
}
```

Standard date hierarchy levels: `Year`, `Quarter`, `Month`, `Day`.
Set `active: true` on the starting drill level, `false` on deeper levels.

### Sort Definition

Add `sortDefinition` at the `query` level (sibling of `queryState`) to set
the default sort order:

```json
"query": {
  "queryState": { /* ... */ },
  "sortDefinition": {
    "sort": [
      {
        "field": {
          "Aggregation": {
            "Expression": {
              "Column": {
                "Expression": { "SourceRef": { "Entity": "<Table>" } },
                "Property": "<Column>"
              }
            },
            "Function": 0
          }
        },
        "direction": "Descending"
      }
    ],
    "isDefaultSort": true
  }
}
```

Direction values: `"Ascending"` or `"Descending"`.

## Formatting Patterns

Discover formatting objects and properties with the CLI:

```bash
powerbi-report-author formatting list-objects <visualType>
powerbi-report-author formatting describe-object <visualType> <object>
powerbi-report-author formatting search <visualType> <regex>
```

> **Property names vary by visual type.** Always run
> `powerbi-report-author formatting describe-object <type> <object>` to confirm
> exact names.

### Per-Series Metadata Selector Pattern

When a chart has multiple Y measures, use metadata selectors to target
formatting to a specific measure. The selector `metadata` value **must match**
the projection's `queryRef` (not `nativeQueryRef`):

```json
"dataPoint": [
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 9, "Percent": -0.25 } } } } },
      "fillTransparency": { "expr": { "Literal": { "Value": "18D" } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Profit)"
    }
  }
]
```

This pattern applies to `dataPoint`, `labels`, `lineStyles`, and
`ribbonBands`. Each section below notes when metadata selectors are needed.

> **⚠️ Pitfall:** The selector `metadata` value must match the `queryRef` string
> (e.g., `"Sum(OrderBreakdown.Profit)"`), not the `nativeQueryRef`
> (e.g., `"Sum of Profit"`).

### dataPoint — Color Assignment

> **⚠️ Multi-visual pages:** When a page has multiple charts sharing the same
> measures, define a **measure→color mapping before creating any visuals** and
> apply it consistently to every chart. Without this, the same measure gets
> different colors on different visuals. See
> [color-strategy.md § Cross-Visual Measure-Color Consistency](color-strategy.md#pattern-cross-visual-measure-color-consistency)
> for the full pattern.

Use metadata selectors to set per-measure colors. **Always use `Literal` hex
values** (not `ThemeDataColor`) for explicit color assignments — `ThemeDataColor`
with metadata selectors can silently resolve to wrong colors (white, black).
Run `powerbi-report-author formatting describe-object <type> dataPoint` for
exact property names per visual type.

> **⚠️ Background contrast:** Always choose bar/line/point colors that contrast
> with the page and VCO background. If the canvas or card background is white,
> avoid light or desaturated colors. Pick saturated, mid-to-dark hues.

```json
"dataPoint": [
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#2E86AB'" } } } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Sales)"
    }
  },
  {
    "properties": {
      "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E6553A'" } } } } }
    },
    "selector": {
      "metadata": "Sum(OrderBreakdown.Profit)"
    }
  }
]
```

> **Note:** Property names differ between visual types (e.g., `fillTransparency`
> on bar/column vs `transparency` on lineChart). Always verify with
> `powerbi-report-author formatting describe-object <type> dataPoint`.

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

### y2Axis — Secondary Axis

When the `Y2` role is populated (lineChart only), format the secondary axis.
Example:

```json
"y2Axis": [{
  "properties": {
    "secLabelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } },
    "secTitleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
    "secLogAxisScale": { "expr": { "Literal": { "Value": "false" } } }
  }
}]
```

> **Note:** All `y2Axis` properties are prefixed with `sec`. Run
> `powerbi-report-author formatting describe-object lineChart y2Axis` for the
> full list.

### smallMultiplesLayout — Rows Role

When the `Rows` role is populated, the chart splits into a grid of small
multiples:

```json
"smallMultiplesLayout": [{
  "properties": {
    "rowCount": { "expr": { "Literal": { "Value": "9L" } } },
    "columnCount": { "expr": { "Literal": { "Value": "4L" } } },
    "gridPadding": { "expr": { "Literal": { "Value": "2D" } } },
    "gridLineWidth": { "expr": { "Literal": { "Value": "2D" } } },
    "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0.4 } } } } }
  }
}]
```

Run `powerbi-report-author formatting describe-object <type> smallMultiplesLayout`
for all available properties.

For VCO formatting (title, border, background, etc.), see
[formatting.md](formatting.md).

## Minimal Examples

### Bar Chart (Minimal)

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "a1b2c3d4e5f6a7b8c9d0",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 300, "width": 500, "tabOrder": 1000 },
  "visual": {
    "visualType": "barChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "product" } }, "Property": "ProductName" } },
            "queryRef": "product.ProductName",
            "nativeQueryRef": "ProductName",
            "active": true
          }]
        },
        "Y": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "metrics" } }, "Property": "Sales" } },
            "queryRef": "metrics.Sales",
            "nativeQueryRef": "Sales"
          }]
        }
      }
    }
  }
}
```

### Clustered Bar Chart (with Per-Series Color)

Shows both `objects` (chart formatting) and `visualContainerObjects` (container formatting).

**⚠️ `visualContainerObjects` goes INSIDE `visual`, as a sibling of `objects` — NOT as a top-level sibling of `visual`.**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "e1f2a3b4c5d6e7f8a9b0",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 400, "width": 600, "tabOrder": 1000 },
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "product" } }, "Property": "Category" } },
            "queryRef": "product.Category",
            "nativeQueryRef": "Category",
            "active": true
          }]
        },
        "Y": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "metrics" } }, "Property": "Revenue" } },
            "queryRef": "metrics.Revenue",
            "nativeQueryRef": "Revenue"
          }]
        }
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "fontSize": { "expr": { "Literal": { "Value": "11D" } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'dotted'" } } }
        }
      }],
      "dataPoint": [{
        "properties": {
          "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 0, "Percent": 0 } } } } }
        }
      }],
      "labels": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "fontSize": { "expr": { "Literal": { "Value": "9D" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
        }
      }]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "text": { "expr": { "Literal": { "Value": "'Revenue by Category'" } } },
          "fontSize": { "expr": { "Literal": { "Value": "14D" } } },
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
        }
      }],
      "background": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "transparency": { "expr": { "Literal": { "Value": "0D" } } }
        }
      }],
      "border": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E0E0E0'" } } } } },
          "radius": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }],
      "dropShadow": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "preset": { "expr": { "Literal": { "Value": "'BottomRight'" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#000000'" } } } } },
          "transparency": { "expr": { "Literal": { "Value": "80D" } } },
          "position": { "expr": { "Literal": { "Value": "'Outer'" } } }
        }
      }],
      "visualHeader": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "false" } } }
        }
      }],
      "padding": [{
        "properties": {
          "top": { "expr": { "Literal": { "Value": "5D" } } },
          "bottom": { "expr": { "Literal": { "Value": "5D" } } },
          "left": { "expr": { "Literal": { "Value": "5D" } } },
          "right": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }]
    }
  }
}
```

## Complete Examples

### Clustered Bar Chart with Per-Measure Colors

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 0, "height": 700, "width": 1000, "tabOrder": 0 },
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Category" } },
            "queryRef": "OrderBreakdown.Category",
            "nativeQueryRef": "Category",
            "active": true
          }]
        },
        "Y": {
          "projections": [
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Profit)",
              "nativeQueryRef": "Sum of Profit"
            },
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Sales" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Sales)",
              "nativeQueryRef": "Sum of Sales"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [{
          "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
          "direction": "Descending"
        }],
        "isDefaultSort": true
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "fontFamily": { "expr": { "Literal": { "Value": "'Georgia'" } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
          "titleText": { "expr": { "Literal": { "Value": "'Category'" } } },
          "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0 } } } } },
          "innerPadding": { "expr": { "Literal": { "Value": "26L" } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "start": { "expr": { "Literal": { "Value": "0D" } } },
          "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
          "labelPrecision": { "expr": { "Literal": { "Value": "2L" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
          "gridlineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
          "gridlineThickness": { "expr": { "Literal": { "Value": "4D" } } }
        }
      }],
      "legend": [{
        "properties": {
          "position": { "expr": { "Literal": { "Value": "'TopCenter'" } } },
          "titleText": { "expr": { "Literal": { "Value": "'Sales for Categories'" } } }
        }
      }],
      "zoom": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "showLabels": { "expr": { "Literal": { "Value": "true" } } },
          "showOnValueAxis": { "expr": { "Literal": { "Value": "true" } } }
        }
      }],
      "dataPoint": [{
        "properties": {
          "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 9, "Percent": -0.25 } } } } },
          "fillTransparency": { "expr": { "Literal": { "Value": "18D" } } },
          "borderShow": { "expr": { "Literal": { "Value": "true" } } },
          "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
          "borderSize": { "expr": { "Literal": { "Value": "7D" } } }
        },
        "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
      }],
      "layout": [{
        "properties": {
          "seriesOrderSorted": { "expr": { "Literal": { "Value": "true" } } },
          "clusteredGapSize": { "expr": { "Literal": { "Value": "16D" } } }
        }
      }],
      "labels": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "labelPosition": { "expr": { "Literal": { "Value": "'InsideCenter'" } } },
            "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
            "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
            "labelContentLayout": { "expr": { "Literal": { "Value": "'MultiLine'" } } }
          }
        }
      ]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "text": { "expr": { "Literal": { "Value": "'Profit and Sum of Sales by Category'" } } },
          "fontColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": -0.25 } } } } },
          "background": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.6 } } } } },
          "alignment": { "expr": { "Literal": { "Value": "'center'" } } }
        }
      }],
      "border": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": 0.4 } } } } },
          "width": { "expr": { "Literal": { "Value": "3D" } } },
          "radius": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```

### Stacked Column Chart with Ribbons and Totals

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "972da330c2a28c851c90",
  "position": {
    "x": 198.91,
    "y": 51.22,
    "z": 0,
    "height": 668.20,
    "width": 1006.46,
    "tabOrder": 0
  },
  "visual": {
    "visualType": "columnChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Category" } },
              "queryRef": "OrderBreakdown.Category",
              "nativeQueryRef": "Category",
              "active": true
            }
          ]
        },
        "Y": {
          "projections": [
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Discount" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Discount)",
              "nativeQueryRef": "Sum of Discount"
            },
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Product Name" } }, "Function": 5 } },
              "queryRef": "CountNonNull(OrderBreakdown.Product Name)",
              "nativeQueryRef": "Product Name"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [
          {
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Discount" } }, "Function": 0 } },
            "direction": "Descending"
          }
        ],
        "isDefaultSort": true
      }
    },
    "objects": {
      "categoryAxis": [
        {
          "properties": {
            "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
            "maxMarginFactor": { "expr": { "Literal": { "Value": "29L" } } },
            "fontSize": { "expr": { "Literal": { "Value": "11D" } } },
            "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": -0.25 } } } } },
            "concatenateLabels": { "expr": { "Literal": { "Value": "false" } } },
            "titleBold": { "expr": { "Literal": { "Value": "true" } } },
            "titleUnderline": { "expr": { "Literal": { "Value": "true" } } },
            "preferredCategoryWidth": { "expr": { "Literal": { "Value": "35D" } } }
          }
        }
      ],
      "valueAxis": [
        {
          "properties": {
            "start": { "expr": { "Literal": { "Value": "0D" } } },
            "invertAxis": { "expr": { "Literal": { "Value": "true" } } },
            "end": { "expr": { "Literal": { "Value": "10000D" } } },
            "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
            "labelPrecision": { "expr": { "Literal": { "Value": "1L" } } },
            "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.4 } } } } },
            "gridlineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0.4 } } } } },
            "gridlineStyle": { "expr": { "Literal": { "Value": "'solid'" } } },
            "gridlineThickness": { "expr": { "Literal": { "Value": "2D" } } }
          }
        }
      ],
      "legend": [
        {
          "properties": {
            "position": { "expr": { "Literal": { "Value": "'TopCenter'" } } },
            "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
            "showTitle": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ],
      "dataPoint": [
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "0D" } } }
          }
        },
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": 0.2 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "3D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Discount)" }
        },
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": -0.25 } } } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": -0.5 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "5D" } } }
          },
          "selector": { "metadata": "CountNonNull(OrderBreakdown.Product Name)" }
        }
      ],
      "ribbonBands": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } }
          }
        },
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "35D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Discount)" }
        },
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "44D" } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.5 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "2D" } } },
            "borderTransparency": { "expr": { "Literal": { "Value": "59D" } } }
          },
          "selector": { "metadata": "CountNonNull(OrderBreakdown.Product Name)" }
        }
      ],
      "labels": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "labelOrientation": { "expr": { "Literal": { "Value": "1D" } } },
            "labelOverflow": { "expr": { "Literal": { "Value": "false" } } },
            "optimizeLabelDisplay": { "expr": { "Literal": { "Value": "true" } } },
            "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
            "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
            "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0.6 } } } } },
            "horizontalAlignment": { "expr": { "Literal": { "Value": "'center'" } } }
          }
        }
      ],
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
      ],
      "zoom": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "showLabels": { "expr": { "Literal": { "Value": "false" } } }
          }
        }
      ]
    }
  }
}
```

### Line Chart with Y2 Secondary Axis and Per-Series Styling

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 705, "y": 0, "z": 1, "height": 591, "width": 575, "tabOrder": 1 },
  "visual": {
    "visualType": "lineChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Year"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Year",
              "nativeQueryRef": "Ship Date Year",
              "active": true
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Quarter"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Quarter",
              "nativeQueryRef": "Ship Date Quarter",
              "active": false
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Month"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Month",
              "nativeQueryRef": "Ship Date Month",
              "active": false
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Day"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Day",
              "nativeQueryRef": "Ship Date Day",
              "active": false
            }
          ]
        },
        "Y": {
          "projections": [{
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
            "queryRef": "Sum(OrderBreakdown.Profit)",
            "nativeQueryRef": "Sum of Profit"
          }]
        },
        "Y2": {
          "projections": [{
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Quantity" } }, "Function": 0 } },
            "queryRef": "Sum(OrderBreakdown.Quantity)",
            "nativeQueryRef": "Sum of Quantity"
          }]
        }
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "axisType": { "expr": { "Literal": { "Value": "'Categorical'" } } },
          "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "logAxisScale": { "expr": { "Literal": { "Value": "true" } } },
          "invertAxis": { "expr": { "Literal": { "Value": "true" } } },
          "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'custom'" } } },
          "gridlineDashArray": { "expr": { "Literal": { "Value": "'5 5 0 10 20'" } } },
          "gridlineThickness": { "expr": { "Literal": { "Value": "2D" } } }
        }
      }],
      "y2Axis": [{
        "properties": {
          "secLabelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } },
          "secTitleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } }
        }
      }],
      "lineStyles": [
        {
          "properties": {
            "strokeWidth": { "expr": { "Literal": { "Value": "5D" } } },
            "lineChartType": { "expr": { "Literal": { "Value": "'step'" } } },
            "interpolationStep": { "expr": { "Literal": { "Value": "'after'" } } },
            "showMarker": { "expr": { "Literal": { "Value": "true" } } },
            "markerShape": { "expr": { "Literal": { "Value": "'diamond'" } } },
            "markerSize": { "expr": { "Literal": { "Value": "9D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
        },
        {
          "properties": {
            "lineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
            "strokeWidth": { "expr": { "Literal": { "Value": "4D" } } },
            "lineChartType": { "expr": { "Literal": { "Value": "'smooth'" } } },
            "interpolationSmooth": { "expr": { "Literal": { "Value": "'cardinal'" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Quantity)" }
        },
        {
          "properties": {
            "areaShow": { "expr": { "Literal": { "Value": "true" } } },
            "showMarker": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ],
      "dataPoint": [
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
            "transparency": { "expr": { "Literal": { "Value": "76D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
        },
        {
          "properties": {
            "transparency": { "expr": { "Literal": { "Value": "59D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Quantity)" }
        }
      ],
      "legend": [{
        "properties": {
          "legendMarkerRendering": { "expr": { "Literal": { "Value": "'lineAndMarker'" } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": -0.25 } } } } },
          "titleText": { "expr": { "Literal": { "Value": "'Line Chart'" } } }
        }
      }],
      "zoom": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "showOnValueSecAxis": { "expr": { "Literal": { "Value": "true" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```
