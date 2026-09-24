# Conditional Formatting Patterns - Part 7

## Contents

- [Type 6: Field-Driven Color](#type-6-field-driven-color)
  - [Contract](#contract)
  - [Aggregation Function values](#aggregation-function-values)
  - [Selector](#selector)
  - [Applies to tables and matrices](#applies-to-tables-and-matrices)
  - [Chart field-value color](#chart-field-value-color)
- [Type 7: Image Field Values](#type-7-image-field-values)
- [Totals, subtotals, and the matrix `total` slot](#totals-subtotals-and-the-matrix-total-slot)
- [Column width — not conditionally formattable](#column-width--not-conditionally-formattable)
- [Chart color inheritance](#chart-color-inheritance)
  - [Line, marker, legend, and series-label consistency](#line-marker-legend-and-series-label-consistency)
  - [Category consistency across visuals](#category-consistency-across-visuals)
  - [Line segment limitation](#line-segment-limitation)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

## Type 6: Field-Driven Color

Colors a property using hex values stored in a data column. There is no special
`fieldValue` property — this is a pattern of placing an `Aggregation` expression
(referencing a color column) inside any standard color property slot
(`backColor`, `fontColor`, `foreColor`, etc.).

### Contract

```json
{
  "properties": {
    "backColor": {
      "solid": {
        "color": {
          "expr": {
            "Aggregation": {
              "Expression": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "Colors" } },
                  "Property": "Color"
                }
              },
              "Function": 3
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "Sum(OrderBreakdown.Sales)"
  }
}
```

### Aggregation Function values

A **color source column** is wrapped in `Aggregation` with `Min` (3) or
`Max` (4) — a text/color column has no numeric Sum/Average:

| Function | Meaning |
|----------|---------|
| 3 | Min |
| 4 | Max |

See Aggregation: columns vs. measures for
the full `Function` enum and the measure-vs-column rule (a color-returning
**measure** is referenced directly, with no `Aggregation` wrapper).

### Selector

The `metadata` queryRef targets the **column being colored** (the measure or
column whose cells receive the color), not the color source column.

| `matchingOption` | Meaning |
|------------------|---------|
| 0 | All data points including totals |
| 1 | Values only (excludes totals) |

### Applies to tables and matrices

Works with `backColor` and `fontColor`. The color source column must contain
valid color strings such as `#FF6B35` — see
Color value results (hex) for the accepted forms
and the `#RRGGBBAA` caveat.

### Chart field-value color

For charts, place a color-returning `Measure` or aggregated text `Column`
expression in the supported chart color property. Choose the instance,
category-role, or series-role selector that matches what the color repeats
over; do not default every chart to one wildcard shape.

For a single-series non-combo line chart whose markers should vary by
category, use this pattern and do not also set
`lineStyles.markerColor`:

```json
"dataPoint": [
  {
    "properties": {
      "fill": {
        "solid": {
          "color": {
            "expr": {
              "Measure": {
                "Expression": {
                  "SourceRef": { "Entity": "Sales" }
                },
                "Property": "Marker Color"
              }
            }
          }
        }
      }
    },
    "selector": {
      "data": [{ "roles": ["Category"] }]
    }
  }
]
```

When only markers should vary, add a static `lineStyles.strokeColor`. When
segments and markers should match, apply the same conditional source to
`lineStyles.strokeColor` and `dataPoint.fill`.

The measure must return a supported color value: hex, CSS color name,
RGB/RGBA, HSL/HSLA, or a report-theme color name. Prefer a text-typed DAX
measure. Calculation groups or mixed return types can make the measure variant
typed and prevent field-value formatting from rendering.

For a color column, use an `Aggregation` expression with `Function: 3` (Min) or
`Function: 4` (Max), matching the table/matrix pattern. Replace
`dataPoint.fill` with another supported direct target from the chart capability
matrix as needed.

## Type 7: Image Field Values

Renders images inside table/matrix cells from a field of image URLs — the
**"Field value"** style of conditional formatting (the output is driven by the
data, like [Type 6: Field-Driven Color](#type-6-field-driven-color)). Unlike
color/icon CF, there is **no `objects` rule to author**: image rendering is
enabled by the field's **Data Category**. Any field whose Data Category is
**"Image URL"** (TMDL `dataCategory: ImageUrl`) is rendered as an `<img>` in
every data cell. Two supporting objects refine the result — `grid` (size) and
`accessibility.altTextColumns` (alt text).

> For standalone image **visuals** (an image on the canvas, not a cell) see
> image.md (see `image.md`).

**Prerequisite — the field must be Image URL data-category.** Inspect the TMDL
first:
- Field **has** `dataCategory: ImageUrl` → place it in the visual; cells render
  as images automatically.
- Field **lacks** the category → cells render the raw URL **text**. Warn the
  user; offer to use an ImageUrl field or set the category on a column/measure
  holding valid image URLs.
- URLs must be valid, publicly reachable image URLs (HTTPS preferred). Invalid
  URLs render blank / broken.

**Column vs measure placement:**
- In a **table** (`tableEx`), an ImageUrl **column** goes in `Values`. Its
  **grand-total** cell is **blank** (no image) — a column has no value at the
  total grain. The word **"Total"** appears only in the visual's **first /
  left-most (row-label) column**, not in the image column itself.
- In a **matrix** (`pivotTable`), `Values` is a **measure-only** role: a raw
  column there fails validation (`PBIR_ROLE_KIND_MISMATCH`, *"use Measure or
  Aggregation"*). To show a column's images in matrix `Values`, wrap it in an
  `Aggregation` (e.g. `Function: 3` = Min) or expose it as a measure; the raw
  column may otherwise be placed in matrix `Rows` / `Columns` (grouping roles).
- An ImageUrl **measure** is a value, not a grouping field — it must go in
  `Values` only. Placing a measure in `Rows` / `Columns` fails validation
  (`PBIR_ROLE_KIND_MISMATCH`, grouping-only role).
- **Total-cell rule:** anything that returns a URL in **every** context — a
  **measure**, or an **Aggregation-wrapped column** in matrix `Values` — renders
  the **image** in its total cell. A plain **column** (table `Values`, or matrix
  `Rows` / `Columns`) renders **no image** at the total: its own total cell is
  **blank**, and the word **"Total"** shows only in the visual's first / row-label
  column, because a column has no value at the total grain.

**Image size — `grid.imageHeight` / `grid.imageWidth`** (shared by all image
columns in the visual):

```json
"grid": [{
  "properties": {
    "imageHeight": { "expr": { "Literal": { "Value": "75D" } } },
    "imageWidth": { "expr": { "Literal": { "Value": "120D" } } }
  }
}]
```

| Property | Default | Notes |
|----------|---------|-------|
| `imageHeight` | `75` | Height in px for image cells |
| `imageWidth` | *(auto)* | Width in px; omit to preserve the source aspect ratio. `imageHeight` is always honored. |

**Alt text — `accessibility.altTextColumns`.** Bind a text field or measure per
image column (same field-value shape as [Type 6: Field-Driven Color](#type-6-field-driven-color)),
`metadata` = the **image field's** projection queryRef, `matchingOption: 0`
(InstancesAndTotals). The queryRef matches how the image is projected: a plain
column → `Table.Column`; an Aggregation-wrapped column in matrix `Values` →
`Min(Table.Column)`; a measure → `Table.Measure`. Alt text works for image
fields bound to `Rows` / `Columns` / `Values`:

```json
{
  "properties": {
    "altTextColumns": {
      "expr": {
        "Aggregation": {
          "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "Products" } }, "Property": "ProductName" } },
          "Function": 3
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 0 } }],
    "metadata": "Products.ImageUrl"
  }
}
```

**Clickable images.** Pair an image column with a `webURL` rule (Type 5)
or place it in a Web URL data-category column to make the rendered image a link.
A Web URL data-category value on the same cell is not double-linked (phishing
guard).

Image diagnostics:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cells show URL text, not images | Field is not `dataCategory: ImageUrl` | Set the Image URL data category on the field in the semantic model |
| Blank / broken image | URL invalid, not public, or not a direct image link | Use absolute, publicly reachable image-file URLs (HTTPS) |
| Images too small / cropped | Default `imageHeight` (75) too small or `imageWidth` forcing distortion | Set `grid.imageHeight`; omit `imageWidth` to keep aspect ratio |
| Screen reader reads the URL | No alt text bound | Add `accessibility.altTextColumns` for the image column |
| "Total" appears instead of an image | Grand-total row of an image **column** | Expected; use an image measure if the total should show an image |

## Totals, subtotals, and the matrix `total` slot

The `data` selector's `dataViewWildcard.matchingOption` controls **which cells**
a value rule (`backColor`, `fontColor`, `icon`, `webURL`) targets:

| `matchingOption` | Name | Targets |
|------------------|------|---------|
| `1` | InstancesOnly | Data cells only (**default** for `tableEx` / `pivotTable`; excludes totals) |
| `0` | InstancesAndTotals | Data cells **and** total / subtotal cells |
| `2` | TotalsOnly | Total / subtotal cells only |

- Use `matchingOption: 1` (the default) for ordinary cell formatting; use `0` or
  `2` to extend or restrict a rule to totals — honored only on the `tableEx` /
  `pivotTable` visuals.
- A value rule with `matchingOption: 1` does **not** color totals; add a second
  rule (or switch to `0`) if totals must match.
- On a **matrix**, the `total` object's `fontColor` is itself a CF slot (behaves
  like `values.fontColor`). Static total colors use `rowTotal` / `columnTotal`
  (and `subTotals`) — see table.md § Table/Matrix Formatting Regions (see `table.md`, section `tablematrix-formatting-regions`).

## Column width — not conditionally formattable

**Power BI has no conditional/measure-driven column width.** Width is a static
layout value, not a CF target — there is no **fx** ("Format by field value" /
rules / gradient) entry for width on `tableEx` or `pivotTable`, and it does not
belong with the seven CF types above. `powerbi-report-author validate` rejects a
data-bound expression placed in `columnWidth.value`.

For the supported **static** per-column width shape and alternatives, see
table.md § Column width (static) (see `table.md`, section `column-width-static`). To convey
magnitude inside a fixed-width column, use a data bar.

## Chart color inheritance

Do not duplicate a conditional expression when the visual can inherit the
conditionally formatted series color.

### Line, marker, legend, and series-label consistency

For line/area charts:

- `dataPoint.fill` is the direct full-series line-color target.
- With a Category-role selector on a single-series non-combo chart,
  `dataPoint.fill` is also the per-category marker-color target. It supports
  gradients, rules, and field-value colors. Set
  `lineStyles.strokeColor` independently when the line must remain static.
- `lineStyles.strokeColor` is the per-category line-segment target for a
  single non-combo line series.
- `lineStyles.markerColor` supports static marker styling. Omit it when using
  per-category marker colors through `dataPoint.fill`.
- If markers should follow one conditionally formatted full-series line color,
  omit separate marker formatting and use the visual's match/inherit behavior.
- `legend.matchLineColor: true` makes the legend symbol follow the line rather
  than the marker.
- `seriesLabels.seriesMatchColor: true` makes end-of-line series labels follow
  the series color.
- `lineStyles.areaMatchStrokeColor: true` makes shaded area follow the
  conditionally formatted line.

**Avoid:**

- Do not place per-category marker conditional formatting in
  `lineStyles.markerColor`; use Category-scoped `dataPoint.fill`.
- Do not set `lineStyles.markerColor` alongside Category-scoped
  `dataPoint.fill`, because the explicit marker color overrides the
  per-category colors.
- Do not use `dataViewWildcard` for per-category markers; use
  `{ "data": [{ "roles": ["Category"] }] }`.
- Do not apply the per-category marker pattern to combo charts, multiple Y
  measures, or charts with a categorical legend.

```json
"legend": [
  {
    "properties": {
      "matchLineColor": {
        "expr": { "Literal": { "Value": "true" } }
      }
    }
  }
],
"seriesLabels": [
  {
    "properties": {
      "seriesMatchColor": {
        "expr": { "Literal": { "Value": "true" } }
      }
    }
  }
],
"lineStyles": [
  {
    "properties": {
      "areaMatchStrokeColor": {
        "expr": { "Literal": { "Value": "true" } }
      }
    }
  }
]
```

The legend's `labelColor` property controls legend **text**, not category
identity. Do not apply a second conditional rule to `legend.labelColor` to
synchronize categories.

### Category consistency across visuals

To keep the same category color across bar/column, line, pie/donut, and
treemap visuals:

1. Create one text measure or column that returns a color for the current
   category.
2. Apply that same field-value expression to each visual's direct color target.
3. Keep the category/legend field consistent across visuals.
4. Let each visual's legend symbol inherit the resulting data or series color.

This is data-driven category consistency. Static per-measure colors use
`metadata` selectors instead; see
color-strategy.md (see `color-strategy.md`, section `pattern-cross-visual-measure-color-consistency`).

### Line segment limitation

Conditional line-segment coloring applies to a single line series and uses a
category-role selector:

```json
"selector": {
  "data": [{ "roles": ["Category"] }]
}
```

Adding a categorical legend creates multiple line series and disables segment
formatting. With multiple series, author full-series color on `dataPoint.fill`
with the series-role selector:

```json
"selector": {
  "data": [{ "roles": ["Series"] }],
  "hierarchyMatching": 1
}
```
