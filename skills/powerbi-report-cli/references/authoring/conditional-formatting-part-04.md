# Conditional Formatting Patterns - Part 4

## Contents

- [Type 1: Color Gradient (FillRule)](#type-1-color-gradient-fillrule)
  - [Choose gradient colors by measure meaning](#choose-gradient-colors-by-measure-meaning)
  - [SelectRef Expression](#selectref-expression)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

## Type 1: Color Gradient (FillRule)

Applies data-driven color gradients. Uses `linearGradient2` (2-stop) or `linearGradient3` (3-stop).

> ⚠️ **Do not omit `mid` from `linearGradient3`.** A `linearGradient3` rule must
> include all three stops: `min`, `mid`, and `max`. If you only need two stops,
> use `linearGradient2`; deleting `mid` from `linearGradient3` can cause Desktop
> render errors or a blank table/matrix body.

### Choose gradient colors by measure meaning

Do **not** default to red/white/green for every numeric measure. Pick the color
scale based on what the measure means:

| Measure meaning | Use | Example measures | Color pattern |
|-----------------|-----|------------------|---------------|
| **Magnitude**: "how much?", "more vs less" | Single-hue `linearGradient2` | Sales, Revenue, Units, Gross Margin %, Count, COGS | Light tint of one theme `dataColors[N]` → base/saturated theme color |
| **Sentiment / variance**: "good vs bad?", negative vs positive, performance vs target | Divergent `linearGradient3` | Profit variance, MoM %, YoY %, vs target, budget variance | Bad color → neutral midpoint → good color |

**Rule of thumb:** if the measure can be read as "low to high", use a
light-to-dark gradient of one color. If the measure can be read as "bad to good"
with a meaningful neutral point (usually zero or target), use a divergent
red/neutral/green gradient.

Examples:
- `Sales`, `Units`, `Gross Margin %` as absolute magnitude: use
  `#DEEFFF` → `#118DFF` (or another light-to-dark pair derived from one theme
  `dataColors` entry).
- `Units MoM %`, `Profit variance`, `Actual vs Target %`: use divergent colors
  only when negative values are bad and positive values are good.

> ⚠️ **Do not use sentiment colors for pure magnitude.** Red/green implies
> judgment. A low Sales value is not automatically "bad" unless the user asked
> for performance/target/variance semantics.

**Supported chart targets** include:

- `dataPoint.fill` for bar/column, ribbon, combo-column, scatter, pie/donut,
  treemap, funnel, and map families.
- `dataPoint.fill` for full line/area series color.
- `dataPoint.fill` for per-category markers on a single-series non-combo line
  or area chart; omit `lineStyles.markerColor`.
- `lineStyles.strokeColor` for segments within one non-combo line/area series.
- `labels.color` for supported chart data labels.

The outer property changes, but the nested
`solid.color.expr.FillRule` expression remains the same. Use the capability
matrix above instead of copying `dataPoint.fill` to every chart.

**For tables/matrices**: add an entry to the `values` object array (NOT `columnFormatting`).
The entry must use:
- A `selector` with `data: [{ dataViewWildcard: { matchingOption: 1 } }]` and
  `metadata` pointing to the measure's queryRef.
- A `FillRule` whose `Input` follows the
  driver-expression decision path. Use
  `SelectRef` when the driver is an existing visual query selection; otherwise
  use `Measure` or `Aggregation(Column, Function)` as appropriate.

### SelectRef Expression

`SelectRef` references an existing selection in the visual query by its
expression name:

```json
{
  "SelectRef": {
    "ExpressionName": "metrics.NetIncome"
  }
}
```

The referenced query selection must exist and return a value compatible with
the target formatting property. Do not invent an `ExpressionName`; when no
matching selection exists, use `Measure` or `Aggregation(Column, Function)`
according to the decision path above.

> ⚠️ **Do NOT use `columnFormatting`** for conditional formatting on tables/matrices,
> except data bars (Type 4). `columnFormatting` is for static styling (alignment,
> display units, etc.). PBI Desktop writes other conditional formatting via "cell
> elements" to the `values` array, not `columnFormatting`. A gradient FillRule placed
> under `columnFormatting` is flagged by `validate` as
> `PBIR_CF_GRADIENT_IN_COLUMN_FORMATTING` (error).

> 🔴 **The outer color uses `expr`; each gradient-stop color does not.**
>
> ```text
> Correct:   outer color → expr → FillRule → stop color → Literal
> Incorrect: outer color → expr → FillRule → stop color → expr → Literal
> ```
>
> A double-wrapped stop can break query rebuilding across the whole report and
> crash Desktop's FillRule visitor. `powerbi-report-author validate` reports it
> as `PBIR_FILLRULE_STOP_DOUBLE_WRAP`; still verify gradients after a Desktop
> reload.

> ℹ️ `FillRule` gradients also work on **`fontColor`** (not just `backColor`) —
> use the identical structure under `values[].properties.fontColor.solid.color.expr.FillRule`.

**Pivot table / matrix magnitude gradient example** (placed as entry in `values` array inside `objects`):

```json
{
  "properties": {
    "backColor": {
      "solid": {
        "color": {
          "expr": {
            "FillRule": {
              "Input": {
                "SelectRef": { "ExpressionName": "metrics.NetIncome" }
              },
              "FillRule": {
                "linearGradient2": {
                  "min": {
                    "color": { "Literal": { "Value": "'#DEEFFF'" } }
                  },
                  "max": {
                    "color": { "Literal": { "Value": "'#118DFF'" } }
                  },
                  "nullColoringStrategy": {
                    "strategy": { "Literal": { "Value": "'noColor'" } }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "metrics.NetIncome"
  }
}
```

The `metadata` and `ExpressionName` values must match the measure's `queryRef`
from the visual's `queryState`.

**Pivot table / matrix sentiment or variance gradient example** (placed as entry in `values` array inside `objects`):

```json
{
  "properties": {
    "backColor": {
      "solid": {
        "color": {
          "expr": {
            "FillRule": {
              "Input": {
                "SelectRef": { "ExpressionName": "metrics.NetIncome" }
              },
              "FillRule": {
                "linearGradient3": {
                  "min": {
                    "color": { "Literal": { "Value": "'#FF0000'" } },
                    "value": { "Literal": { "Value": "-5000000D" } }
                  },
                  "mid": {
                    "color": { "Literal": { "Value": "'#FFFFFF'" } },
                    "value": { "Literal": { "Value": "0D" } }
                  },
                  "max": {
                    "color": { "Literal": { "Value": "'#00FF00'" } },
                    "value": { "Literal": { "Value": "5000000D" } }
                  },
                  "nullColoringStrategy": {
                    "strategy": { "Literal": { "Value": "'asZero'" } }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "metrics.NetIncome"
  }
}
```

**Key differences between chart and table/matrix conditional formatting:**
| Aspect | Charts (`dataPoint`) | Pivot Tables (`values`) |
|--------|---------------------|------------------------|
| Object | `dataPoint` | `values` |
| Property | `fill` | `backColor` or `fontColor` |
| Input ref | `Measure` + `SourceRef` (DAX measures) or `Aggregation` (columns) | `SelectRef` + `ExpressionName` |
| Selector | Instance wildcard or category/series role wildcard; per-measure labels can also preserve `metadata` | `data: [{ dataViewWildcard }]` + `metadata` |
| `matchingOption` | `1` when a `dataViewWildcard` is used | `1` |

For value-driven conditional formatting, never attach `metadata` to
`dataPoint.fill`; it causes silent failure. `metadata` remains valid for static
per-measure `Literal` fills and for `labels.color` when targeting one measure.

**3-color sentiment / variance gradient** (linearGradient3) — use only when
negative/positive values have bad/good meaning:

```json
{
  "solid": {
    "color": {
      "expr": {
        "FillRule": {
          "Input": {
            "Measure": {
              "Expression": { "SourceRef": { "Entity": "metrics" } },
              "Property": "GrossMargin"
            }
          },
          "FillRule": {
            "linearGradient3": {
              "min": {
                "color": { "Literal": { "Value": "'#FF0000'" } },
                "value": { "Literal": { "Value": "-0.01D" } }
              },
              "mid": {
                "color": { "Literal": { "Value": "'#FFFF00'" } },
                "value": { "Literal": { "Value": "0D" } }
              },
              "max": {
                "color": { "Literal": { "Value": "'#00FF00'" } },
                "value": { "Literal": { "Value": "0.01D" } }
              },
              "nullColoringStrategy": {
                "strategy": { "Literal": { "Value": "'asZero'" } }
              }
            }
          }
        }
      }
    }
  }
}
```

**2-color gradient** (linearGradient2) — omit `mid`:

```json
{
  "fillRule": {
    "linearGradient2": {
      "min": { "color": { "Literal": { "Value": "'#DEEFFF'" } } },
      "max": { "color": { "Literal": { "Value": "'#118DFF'" } } },
      "nullColoringStrategy": {
        "strategy": { "Literal": { "Value": "'noColor'" } }
      }
    }
  }
}
```

When `value` is omitted from color stops, PBI auto-calculates from data range.

> **Optional midpoint / split scales (`linearGradient3`).** The `mid` **color**
> is required (see the warning above), but the `mid` **`value`** is optional:
> - Omit **all** three `value`s → PBI spreads `min`→`mid`→`max` evenly across the
>   data's auto min/max (a single continuous scale).
> - Set **only** `mid.value` (leave `min.value`/`max.value` auto) → PBI builds
>   **two independent scales**: `min`→`mid` for values below the midpoint and
>   `mid`→`max` for values above it. Each side is scaled separately against the
>   data's actual min/max, so an off-center midpoint (e.g. `0` for variance) is
>   honored exactly. Use this for "diverging around a fixed pivot" (variance vs
>   target, YoY around zero).
> - `linearGradient2` has **no** midpoint — for a fixed pivot you must use
>   `linearGradient3`.

> ⚠️ **Gradient stop colors must be `#RGB` or `#RRGGBB`.** The client color
> parser (`isHexString`) accepts only 3- or 6-digit hex; any other value (8-digit
> `#RRGGBBAA`, a named/theme color, or a quote-corrupted string) is dropped by
> `filterToHex`, so the stop renders incorrectly (and the Desktop CF dialog can't
> reload it). `validate` flags non-conforming stop colors as
> `PBIR_FILLRULE_STOP_COLOR_INVALID`. (A stop color that is *structurally*
> malformed — an `expr` wrapper — is a different, harder failure: see the
> report-wide `PBIR_FILLRULE_STOP_DOUBLE_WRAP` crash note above.)

> ⚠️ **FillRule color stops must use `Literal` hex values** — `ThemeDataColor`
> silently renders black inside `linearGradient2` / `linearGradient3` color stops.
> To use theme-aware colors, read `dataColors[N]` from the theme file and compute
> a lighter tint (blend 40-60% toward `#FFFFFF`) for the min stop.

**For single-series bar/column charts** — the most common use case. Apply a
value-gradient so the highest bar is darkest and lowest is lightest:

```json
"dataPoint": [{
  "properties": {
    "fill": {
      "solid": {
        "color": {
          "expr": {
            "FillRule": {
              "Input": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "<table>" } },
                  "Property": "<measure>"
                }
              },
              "FillRule": {
                "linearGradient2": {
                  "min": { "color": { "Literal": { "Value": "'#D0E8F5'" } } },
                  "max": { "color": { "Literal": { "Value": "'#56B4E9'" } } },
                  "nullColoringStrategy": {
                    "strategy": { "Literal": { "Value": "'noColor'" } }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }]
  }
}]
```

Key requirements:
- **`Input`** must reference the Y-axis measure (Measure or Aggregation field)
- **`selector`** must be `data: [{ dataViewWildcard: { matchingOption: 1 } }]` —
  without this selector, the gradient does not render
- **Min color**: light tint of the base color (blend ~50% toward white)
- **Max color**: the base color at full saturation (never darker — avoid black)
- ⚠️ **Gradient color stops use `Literal` directly (no `expr` wrapper).** See
  the 🔴 gradient-stop warning under [Type 1](#type-1-color-gradient-fillrule)
  for the full rule and the Desktop crash (`visitFillRuleStop`) it prevents.

**Null coloring strategies:**

| Strategy | Behavior |
|----------|----------|
| `"asZero"` | Treat nulls as zero — apply corresponding gradient color |
| `"noColor"` | No color (transparent/default) |
| `"specificColor"` | Use the `color` property from the strategy object |

`specificColor` **requires** a sibling `color` node; the other two strategies
must **not** carry one:

✅ **Correct — `specificColor` with its color:**
```json
"nullColoringStrategy": {
  "strategy": { "Literal": { "Value": "'specificColor'" } },
  "color": { "Literal": { "Value": "'#CCCCCC'" } }
}
```

❌ **Wrong — `specificColor` with no `color`** (nulls fall back to no color;
`validate` flags this as `PBIR_FILLRULE_NULL_STRATEGY_COLOR_MISSING`):
```json
"nullColoringStrategy": { "strategy": { "Literal": { "Value": "'specificColor'" } } }
```

❌ **Wrong — unknown strategy string** (only the three literals above are valid):
```json
"nullColoringStrategy": { "strategy": { "Literal": { "Value": "'transparent'" } } }
```

`nullColoringStrategy` is optional; omit the whole node to leave nulls
unformatted.
