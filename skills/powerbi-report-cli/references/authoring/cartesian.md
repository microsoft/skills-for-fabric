# Cartesian Visuals (Bar, Column, Line, Scatter)

## Contents

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
- [Scatter / Bubble Charts (scatterChart)](#scatter--bubble-charts-scatterchart)
  - [One bubble per group — the single-point pitfall](#one-bubble-per-group--the-single-point-pitfall)
  - ["Remove Values to display x-and-y-axis pairs" error](#remove-values-to-display-x-and-y-axis-pairs-error)
- [Formatting Patterns](#formatting-patterns)
  - [Per-Series Metadata Selector Pattern](#per-series-metadata-selector-pattern)
  - [dataPoint — Color Assignment](#datapoint--color-assignment)


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
- [Scatter / Bubble Charts (scatterChart)](#scatter--bubble-charts-scatterchart)
  - [One bubble per group — the single-point pitfall](#one-bubble-per-group--the-single-point-pitfall)
  - ["Remove Values to display x-and-y-axis pairs" error](#remove-values-to-display-x-and-y-axis-pairs-error)
- [Formatting Patterns](#formatting-patterns)
  - [Per-Series Metadata Selector Pattern](#per-series-metadata-selector-pattern)
  - [dataPoint — Color Assignment](#datapoint--color-assignment)
  - Conditional Colors (continued in `cartesian-part-02.md`)
  - labels — Data Labels (continued in `cartesian-part-02.md`)
  - legend (continued in `cartesian-part-02.md`)
  - categoryAxis / valueAxis (continued in `cartesian-part-02.md`)
    - Invert Axis (`invertAxis`) (continued in `cartesian-part-02.md`)
    - Log Scale (`logAxisScale`) (continued in `cartesian-part-02.md`)
  - layout — Gap & Series Order (continued in `cartesian-part-02.md`)
  - ribbonBands — Stacked Charts (continued in `cartesian-part-02.md`)
  - totals — Stacked Charts (continued in `cartesian-part-02.md`)
  - zoom — Slider Controls (continued in `cartesian-part-02.md`)
  - lineStyles — Line Specific (continued in `cartesian-part-02.md`)
  - markers — Marker Styling (continued in `cartesian-part-02.md`)
  - seriesLabels — End-of-Line Labels (continued in `cartesian-part-02.md`)
  - y2Axis — Secondary Axis (continued in `cartesian-part-03.md`)
  - smallMultiplesLayout — Rows Role (continued in `cartesian-part-03.md`)
- Minimal Examples (continued in `cartesian-part-03.md`)
  - Bar Chart (Minimal) (continued in `cartesian-part-03.md`)
  - Clustered Bar Chart (with Per-Series Color) (continued in `cartesian-part-03.md`)
- Complete Examples (continued in `cartesian-part-03.md`)
  - Clustered Bar Chart with Per-Measure Colors (continued in `cartesian-part-03.md`)
  - Stacked Column Chart with Ribbons and Totals (continued in `cartesian-part-04.md`)
  - Line Chart with Y2 Secondary Axis and Per-Series Styling (continued in `cartesian-part-04.md`)
<!-- /TOC -->

Use these visual types for axis-based charts that plot data against category
and value axes. The bar/column/line family shares the `Category` + `Y` role
pattern but differs in orientation, stacking, and line/marker support.
`scatterChart` is also covered here but uses a different role model (X and Y are
both aggregates, grouping comes from `Category`/*Details*) — see
[Scatter / Bubble Charts](#scatter--bubble-charts-scatterchart).

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

## Scatter / Bubble Charts (scatterChart)

`scatterChart` differs from the bar/column/line family: **both X and Y are
`GroupingOrMeasure`** (plot an aggregate value per bubble), and grouping comes
from the **`Category`** role (labeled *Details*) — or from `Series`. Run
`powerbi-report-author catalog describe scatterChart` for the full role list;
only the non-obvious rules are covered here.

### One bubble per group — the single-point pitfall

The number of bubbles equals the number of distinct values of the **grouping
role** (`Category`, or `Series`). Without an effective grouping, X and Y are
aggregated **once over the whole table**, so the visual renders **one point**.
Two ways this happens, both looking identical on screen:

- **Mode A — no grouping.** `Category` (and `Series`) is missing or empty, so
  the query returns a single grand-total row → one real bubble. `validate` now
  emits `PBIR_SCATTER_NO_GROUPING` (warning) for this case.
- **Mode B — grouping present but the X/Y filter doesn't propagate.** `Category`
  is bound, so the query returns N rows, but the grouping table's filter never
  reaches the X/Y measure table — each group's aggregate is computed over the
  **entire** table → identical X/Y for every group → all N bubbles stack on one
  coordinate. Causes: **inactive relationship**, **wrong cross-filter
  direction**, or **no relationship path** between the grouping column's table
  and the X/Y column's table. Fix the model relationship (or point X/Y at a
  table that the grouping actually filters).

> **Not an aggregation-function problem.** `Avg` over a per-group Category does
> **not** collapse groups — it yields one value *per group*, exactly like `Max`.
> If switching Avg→Max appears to "fix" the collapse, the real change was to the
> grouping/relationship, not the function. Choose the aggregation for its
> meaning, not to work around a single point.

To tell Mode A from Mode B: click the dot — if it cross-highlights **all**
items, it is N overlapping bubbles (Mode B); the visual's data-point count also
reveals the true row count.

### "Remove Values to display x-and-y-axis pairs" error

This error fires when `X` or `Y` is bound to a **plain Column reference** (a
grouping field) while a measure role such as `Size` is present. Scatter X/Y
must each be a single aggregate per bubble — use an **`Aggregation`** (e.g.
`Function: 1` for Avg) or a **`Measure`**, never a raw `Column`. See
[Y Binding — Measure vs Aggregation](#y-binding--measure-vs-aggregation) and the
`nativeQueryRef` rule (`"Sum of <Column>"`) above; the same rules apply to X/Y.

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
> color-strategy.md § Cross-Visual Measure-Color Consistency (see `color-strategy.md`, section `pattern-cross-visual-measure-color-consistency`)
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
