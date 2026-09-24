# Table & Matrix Visual Authoring Guide

## Contents

- [Default Rule — Grow to Fit](#default-rule--grow-to-fit)
- [Table (`tableEx`)](#table-tableex)
- [Matrix (`pivotTable`)](#matrix-pivottable)
- [Theme Approach](#theme-approach)
- [Row Banding (Table & Matrix)](#row-banding-table--matrix)
  - [Values Object Properties](#values-object-properties)
  - [Table/Matrix Formatting Regions](#tablematrix-formatting-regions)
  - [Style Presets for Tables](#style-presets-for-tables)
  - [`backColor` vs `backColorPrimary` — Different Purposes](#backcolor-vs-backcolorprimary--different-purposes)
  - [`fontColor` vs `fontColorPrimary` — Different Purposes (pivotTable)](#fontcolor-vs-fontcolorprimary--different-purposes-pivottable)
  - [Full Table Example with Custom Styling](#full-table-example-with-custom-styling)
- [Conditional Formatting](#conditional-formatting)
- [Column width (static)](#column-width-static)
- [References](#references)


Tables (`tableEx`) and matrices (`pivotTable`) in PBIR format.

## Default Rule — Grow to Fit

**Always** set both properties in `columnHeaders` unless the user explicitly opts out:

| Property | Value | Effect |
|----------|-------|--------|
| `autoSizeColumnWidth` | `true` | Enables automatic column sizing |
| `columnAdjustment` | `growToFit` | Columns expand to fill visual width (vs `fitToContent` which shrink-wraps) |

Both are already included in the templates below. To apply report-wide via
theme instead of per-visual, see [Theme Approach](#theme-approach).

---

## Table (`tableEx`)

Flat tabular data — columns bound to the `Values` role.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 400, "width": 700, "tabOrder": 1000 },
  "visual": {
    "visualType": "tableEx",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Column1>" } },
              "queryRef": "<Table>.<Column1>",
              "nativeQueryRef": "<Column1>"
            },
            {
              "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Column2>" } },
              "queryRef": "<Table>.<Column2>",
              "nativeQueryRef": "<Column2>"
            }
          ]
        }
      }
    },
    "objects": {
      "columnHeaders": [{
        "properties": {
          "columnAdjustment": {
            "expr": { "Literal": { "Value": "'growToFit'" } }
          },
          "autoSizeColumnWidth": {
            "expr": { "Literal": { "Value": "true" } }
          }
        }
      }]
    }
  }
}
```

---

## Matrix (`pivotTable`)

Row grouping, column grouping, and value aggregation. **When users ask for a
"matrix", use this template.**

| Role | Purpose |
|------|---------|
| `Rows` | Row grouping (hierarchy levels) |
| `Columns` | Column grouping |
| `Values` | Aggregated measures |

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 400, "width": 700, "tabOrder": 1000 },
  "visual": {
    "visualType": "pivotTable",
    "query": {
      "queryState": {
        "Rows": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<RowField>" } },
            "queryRef": "<Table>.<RowField>",
            "nativeQueryRef": "<RowField>"
          }]
        },
        "Values": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Measure>" } },
            "queryRef": "<Table>.<Measure>",
            "nativeQueryRef": "<Measure>"
          }]
        }
      }
    },
    "objects": {
      "columnHeaders": [{
        "properties": {
          "columnAdjustment": {
            "expr": { "Literal": { "Value": "'growToFit'" } }
          },
          "autoSizeColumnWidth": {
            "expr": { "Literal": { "Value": "true" } }
          }
        }
      }]
    },
    "expansionStates": [/* see expressions.md — "roles": ["Rows"]; only for hierarchy visuals */]
  }
}
```

---

## Theme Approach

To apply grow-to-fit to **every** table and matrix in the report, add to the
report theme's `visualStyles` (uses plain JSON values, not PBIR `expr` wrappers):

```json
"visualStyles": {
  "tableEx": {
    "*": {
      "columnHeaders": [{
        "autoSizeColumnWidth": true,
        "columnAdjustment": "growToFit"
      }]
    }
  },
  "pivotTable": {
    "*": {
      "columnHeaders": [{
        "autoSizeColumnWidth": true,
        "columnAdjustment": "growToFit"
      }]
    }
  }
}
```

> ⚠️ Do NOT use `"*"` as the visual type key — `columnHeaders` is specific
> to table/matrix and could cause issues on other visual types.
>
> Visual-level `objects` override theme `visualStyles`. See
> `references/authoring/formatting-overview.md` for the full cascade order.

---

## Row Banding (Table & Matrix)

Tables (`tableEx`) and matrices (`pivotTable`) use a **Primary/Secondary color
pair** model for alternating row colors.

### Values Object Properties

```json
"values": [{
  "properties": {
    "backColorPrimary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
    "backColorSecondary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#F5F5F5'" } } } } },
    "fontColorPrimary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } },
    "fontColorSecondary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
  }
}]
```

| Property | Applied To |
|----------|-----------|
| `backColorPrimary` | Odd rows (1st, 3rd, 5th…) |
| `backColorSecondary` | Even rows (2nd, 4th, 6th…) |
| `fontColorPrimary` | Text on odd rows |
| `fontColorSecondary` | Text on even rows |

When Primary ≠ Secondary → banding visible. When equal → no banding.

### Table/Matrix Formatting Regions

| Region | Object Name | Key Properties |
|--------|-------------|---------------|
| Data cells + row headers | `values` | `backColorPrimary/Secondary`, `fontColorPrimary/Secondary` |
| Column headers | `columnHeaders` | `fontColor`, `backColor`, `outline`, `outlineColor`, `autoSizeColumnWidth`, `columnAdjustment` |
| Row headers (matrix) | `rowHeaders` | `fontColor`, `backColor` |
| Total label (matrix) | inherits from `rowHeaders` | `fontColor` |
| Row totals (bottom row values) | `rowTotal` | `fontColor`, `backColor`, `applyToHeaders` (bool) |
| Column totals ("Total" column) | `columnTotal` | `fontColor`, `backColor`, `applyToHeaders` (bool) |
| Subtotals | `subTotals` | `fontColor`, `backColor` |

> ⚠️ **`pivotTable` has `rowTotal` and `columnTotal` — not just `total`.**
> The `total` object exists but its `fontColor` is a conditional formatting slot
> (like `values.fontColor`). Use `rowTotal` and `columnTotal` for static total
> colors on matrices.

Matrix has an additional `bandedRowHeaders` (bool) property to band row headers.

### Style Presets for Tables

Use the `stylePreset` VCO to apply built-in formatting bundles:

```json
"visualContainerObjects": {
  "stylePreset": [{
    "properties": {
      "name": { "expr": { "Literal": { "Value": "'AlternatingRows'" } } }
    }
  }]
}
```

**9 built-in presets**: `None`, `Minimal`, `BoldHeader`, `AlternatingRows`,
`ContrastAlternatingRows`, `FlashyRows`, `BoldHeaderFlashyRows`, `Sparse`, `Condensed`.

The new table visual (`tableEx`) also has `Default` and `AlternatingRowsNew` presets.

> ⚠️ **Critical: Style presets OVERRIDE `objects`-level formatting.** When no
> `stylePreset` VCO is set, the default preset applies automatically. The default
> preset includes white row/header backgrounds that override any `backColorPrimary`,
> `backColorSecondary`, or `columnHeaders.backColor` you set in `objects`.
>
> **You MUST set `stylePreset` to `'None'` when using custom row/header colors:**
>
> ```json
> "visualContainerObjects": {
>   "stylePreset": [{
>     "properties": {
>       "name": { "expr": { "Literal": { "Value": "'None'" } } }
>     }
>   }]
> }
> ```
>
> Without this, custom table colors silently fail — no error, no warning, just
> white backgrounds. This is the single most common dark-mode table formatting bug.

### `backColor` vs `backColorPrimary` — Different Purposes

Both appear as valid `fill` properties on `values` in the CLI, but they serve
different roles:

| Property | Purpose | Use Case |
|----------|---------|----------|
| `backColorPrimary` | **Static** odd-row background | Base row banding |
| `backColorSecondary` | **Static** even-row background | Base row banding |
| `backColor` | **Conditional formatting** slot | FillRule gradients, rules-based, field-value |

**For base row colors, always use `backColorPrimary` / `backColorSecondary`.**
`backColor` is intended for conditional formatting — it's the property PBI
Desktop writes when you enable data-driven cell coloring (gradients, rules,
field values). Use `backColorPrimary`/`Secondary` for static row backgrounds.

### `fontColor` vs `fontColorPrimary` — Different Purposes (pivotTable)

Both appear as valid `fill` properties on `values` in the CLI, but they serve
different roles:

| Property | Purpose | Use Case |
|----------|---------|----------|
| `fontColorPrimary` | **Static** odd-row text color | Base text coloring |
| `fontColorSecondary` | **Static** even-row text color | Base text coloring |
| `fontColor` | **Conditional formatting** slot | Rules-based, field-value text coloring |

**For static data cell text colors, always use `fontColorPrimary` /
`fontColorSecondary`.** Setting `values.fontColor` to a static color has NO
effect — text will inherit from the theme `foreground` instead. This is the most
common cause of invisible text on dark-themed matrices.

> ⚠️ **This inconsistency applies only to `values` and `total` on
> `pivotTable`.** On other objects (`columnHeaders`, `rowHeaders`, `rowTotal`,
> `columnTotal`, `subTotals`), `fontColor` works as a normal static color.
> `tableEx` does not expose `fontColor` on `values` at all — only
> `fontColorPrimary`/`Secondary`.

**Scope of `values.fontColorPrimary`/`Secondary`:** These properties control
text color for both data cells AND row header labels. The "Total" row label
inherits from `rowHeaders.fontColor` instead.

### Full Table Example with Custom Styling

```json
{
  "visual": {
    "visualType": "pivotTable",
    "objects": {
      "columnHeaders": [{
        "properties": {
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "backColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#2B579A'" } } } } },
          "columnAdjustment": { "expr": { "Literal": { "Value": "'growToFit'" } } },
          "autoSizeColumnWidth": { "expr": { "Literal": { "Value": "true" } } }
        }
      }],
      "rowHeaders": [{
        "properties": {
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "backColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1A1F27'" } } } } }
        }
      }],
      "values": [{
        "properties": {
          "fontColorPrimary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "fontColorSecondary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E0E0E0'" } } } } },
          "backColorPrimary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#14181E'" } } } } },
          "backColorSecondary": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1A1F27'" } } } } }
        }
      }],
      "rowTotal": [{
        "properties": {
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "backColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1B3A5C'" } } } } }
        }
      }],
      "columnTotal": [{
        "properties": {
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "backColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1B3A5C'" } } } } }
        }
      }]
    },
    "visualContainerObjects": {
      "stylePreset": [{
        "properties": {
          "name": { "expr": { "Literal": { "Value": "'None'" } } }
        }
      }]
    }
  }
}
```

> **Why `stylePreset: 'None'` is included:** without it, the default style
> preset overrides the custom `backColor` / `backColorPrimary` /
> `backColorSecondary` values above and the table renders with white
> backgrounds (no error, no warning). This applies to every `tableEx` and
> `pivotTable` with custom row, header, or total colors.

---

## Conditional Formatting

Data-driven cell formatting for tables and matrices — gradients, rule-based
colors, icon sets, data bars, web-URL links, field-driven colors, image field
values, and totals/subtotal targeting — is documented centrally in
conditional-formatting.md (see `conditional-formatting.md`). See the
Tables/matrices formatting options (see `conditional-formatting.md`, section `tablesmatrices`)
for the full menu of supported CF types, their objects, and selectors.

For **static** total/subtotal colors (not data-driven), use `rowTotal` /
`columnTotal` / `subTotals` as described in
[Table/Matrix Formatting Regions](#tablematrix-formatting-regions) above.

## Column width (static)

Column width is a **static layout value, not conditional formatting** — Power BI
has no measure-driven/conditional column width (there is no **fx** /
"Format by field value" / rules / gradient entry for width on `tableEx` or
`pivotTable`). A column has only two width states: an **authored literal** pixel
width, or the **Desktop default** (auto-fit / grow-to-fit) when no literal is
set. There is no "width scales with the data" state.

Static per-column widths live in the **`columnWidth`** object — one array entry
per column, each with a numeric `value` and a **`metadata`** selector whose
queryRef matches that column's projection. Auto-sizing must be **off** for custom
widths to take effect, which is the explicit opt-out from
[Default Rule — Grow to Fit](#default-rule--grow-to-fit) above — only do this when
the user explicitly wants fixed widths.

```json
"objects": {
  "columnHeaders": [{
    "properties": {
      "columnAdjustment": { "expr": { "Literal": { "Value": "'fixedWidth'" } } },
      "autoSizeColumnWidth": { "expr": { "Literal": { "Value": "false" } } }
    }
  }],
  "columnWidth": [
    {
      "properties": { "value": { "expr": { "Literal": { "Value": "180D" } } } },
      "selector": { "metadata": "Sum(Sales.Amount)" }
    },
    {
      "properties": { "value": { "expr": { "Literal": { "Value": "240D" } } } },
      "selector": { "metadata": "Product.Category" }
    }
  ]
}
```

- **`columnWidth.value`** — numeric, decimal-suffixed (`180D`); one entry per
  column to pin. Pinned widths only apply with auto-sizing off (this section sets
  `autoSizeColumnWidth: false` + `columnAdjustment: 'fixedWidth'`, since
  grow-to-fit otherwise recomputes every column from its content and ignores
  `columnWidth`). In that fixed mode a column with **no** `columnWidth` entry is
  **not** sized to its content — it falls back to the **default fixed width
  (90px)**. So pin every column whose width you care about; leaving one out gives
  it 90px, not an auto fit. Only a static
  `Literal` is valid — a data-bound expression
  (`Measure`/`Column`/`Aggregation`/`Conditional`/`FillRule`) is rejected by
  `powerbi-report-author validate` with
  **`PBIR_COLUMN_WIDTH_DATA_BOUND_UNSUPPORTED`**, because Desktop cannot resolve a
  pixel width from data and reverts to the default width.
- **Selector** — `{ "metadata": "<column queryRef>" }` (e.g. `Sum(Sales.Amount)`
  for a measure column, `Product.Category` for a column). `metadata`-only — **no**
  `dataViewWildcard`.
- **`autoSizeColumnWidth` must be `false`** — while `true` (the grow-to-fit
  default), Desktop recomputes widths and discards custom `columnWidth` entries.
- **`columnHeaders.columnAdjustment` must be `'fixedWidth'`** — valid values are
  `fitToContent`, `growToFit`, and `fixedWidth`; only `fixedWidth` honors
  per-column `columnWidth`. (`validate` rejects any other string, e.g. `'none'`,
  with `PBIR_FORMATTING_ENUM_INVALID`.)
- **`columnHeaders.defaultColumnWidth`** sets one fixed width for *all* columns (a
  static fallback), independent of per-column `columnWidth`.

If a user asks for widths that change with the data ("make the column wider when
the value is large"), tell them Power BI does not support conditional column
width and offer the supported alternatives: static per-column widths (above),
grow-to-fit auto-sizing, or an in-cell
data bar (see `conditional-formatting.md`, section `type-4-data-bars`) to convey magnitude inside
a fixed-width column.

**Measure-driven cell text** is not conditional formatting either: a measure that
returns text (e.g. `IF(...,"On track","At risk")`) is shown by binding it as a
normal **Values** projection — no `objects`/selector.

## References

- formatting.md (see `formatting.md`) — selectors, encoding, conditional formatting, VCO cascade
- theming.md § Visual Styles (see `theming.md`, section `6-visual-styles-visualstyles`) — theme-level defaults
- `powerbi-report-author formatting list-objects tableEx` — discover all formatting objects
- `powerbi-report-author formatting describe-object tableEx columnHeaders` — inspect column header properties
