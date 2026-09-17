# Table & Matrix Visual Authoring Guide

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

## References

- [formatting.md](formatting.md) — selectors, encoding, conditional formatting, VCO cascade
- [theming.md § Visual Styles](theming.md#6-visual-styles-visualstyles) — theme-level defaults
- `powerbi-report-author formatting list-objects tableEx` — discover all formatting objects
- `powerbi-report-author formatting describe-object tableEx columnHeaders` — inspect column header properties
