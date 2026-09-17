# Conditional Formatting Patterns

Read this when applying data-driven visual formatting in PBIR. Conditional
formatting is supported on chart `dataPoint` properties (charts) and on table /
matrix `values` cells, but **not** on container objects like axes, legends, or
visual containers.

Related references:
- [`formatting.md`](formatting.md) — value encoding, selectors, VCOs.
- [`formatting-overview.md`](formatting-overview.md) — cascade and encoding.
- [`table.md`](table.md) — table/matrix authoring and style presets.

> Examples use illustrative `<table>.<measure>` identifiers — substitute your own.

## Contents

- [Selector summary by visual type](#selector-summary-by-visual-type)
- [Type 1: Color Gradient (FillRule)](#type-1-color-gradient-fillrule)
- [Type 2: Rules-Based Formatting](#type-2-rules-based-formatting)
- [Type 3: Icon Sets](#type-3-icon-sets)
- [Type 4: Data Bars](#type-4-data-bars)
- [Type 5: Web URL](#type-5-web-url)
- [Type 6: Field-Driven Color](#type-6-field-driven-color)

## Selector summary by visual type

| Visual type | CF type | Object/property | Selector |
|-------------|---------|-----------------|----------|
| Tables/matrices | Data bars | `columnFormatting.dataBars` | `metadata` only |
| Tables/matrices | Background / font color | `values.backColor` / `values.fontColor` | `dataViewWildcard + metadata` |
| Tables/matrices | Icons | `values.icon` | `dataViewWildcard + metadata` |
| Charts | Gradient / rules / field color | `dataPoint.fill` | No selector, or `dataViewWildcard` only (do NOT include `metadata`) |

> This table covers **value-driven conditional formatting**. **Static** per-series
> color (coloring a specific series a fixed hue) uses a `metadata` selector
> instead — see [color-strategy.md § Per-Series Colors](color-strategy.md#pattern-per-series-colors).

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

**Supported on** `dataPoint.fill` (or `dataPoint.fillRule`) for: barChart,
clusteredBarChart, clusteredColumnChart, columnChart, funnel,
hundredPercentStackedBarChart, hundredPercentStackedColumnChart, ribbonChart,
lineStackedColumnComboChart, lineClusteredColumnComboChart, map, filledMap,
shapeMap, treemap, scatterChart, heatMap.

**For tables/matrices**: add an entry to the `values` object array (NOT `columnFormatting`).
The entry must use:
- A `selector` with `data: [{ dataViewWildcard: { matchingOption: 1 } }]` and
  `metadata` pointing to the measure's queryRef.
- A `FillRule` with `Input` using `SelectRef` / `ExpressionName` (referencing
  the measure's queryRef) instead of a direct `Measure` / `SourceRef`.

> ⚠️ **Do NOT use `columnFormatting`** for conditional formatting on tables/matrices,
> except data bars (Type 4). `columnFormatting` is for static styling (alignment,
> display units, etc.). PBI Desktop writes other conditional formatting via "cell
> elements" to the `values` array, not `columnFormatting`.

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
| Selector | `dataViewWildcard` only (do NOT include `metadata`) | `data: [{ dataViewWildcard }]` + `metadata` |
| `matchingOption` | `0` | `1` |

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
    "data": [{ "dataViewWildcard": { "matchingOption": 0 } }]
  }
}]
```

Key requirements:
- **`Input`** must reference the Y-axis measure (Measure or Aggregation field)
- **`selector`** must be `data: [{ dataViewWildcard: { matchingOption: 0 } }]` —
  without this selector, the gradient does not render
- **Min color**: light tint of the base color (blend ~50% toward white)
- **Max color**: the base color at full saturation (never darker — avoid black)
- ⚠️ **Gradient color stops use `Literal` directly** — do NOT add an `expr`
  wrapper inside the gradient `min.color` / `max.color`. Write
  `{ "Literal": { "Value": "'#hex'" } }` not
  `{ "expr": { "Literal": { "Value": "'#hex'" } } }`.
  The `expr` wrapper exists on the outer `fill.solid.color.expr.FillRule` but
  NOT inside the gradient stops. Adding `expr` inside stops causes a
  Desktop crash (`Cannot read properties of undefined (reading 'accept')`
  in `visitFillRuleStop`).

**Null coloring strategies:**

| Strategy | Behavior |
|----------|----------|
| `"asZero"` | Treat nulls as zero — apply corresponding gradient color |
| `"noColor"` | No color (transparent/default) |
| `"specificColor"` | Use the `color` property from the strategy object |

## Type 2: Rules-Based Formatting

Applies colors based on value conditions using `Conditional.Cases[]` inside a
color property. The structure is the same for charts (`dataPoint.fill`) and
tables/matrices (`values.backColor` or `values.fontColor`).

> ⚠️ There is no `backColorRule` or `fontColorRule` property — these do not
> exist. Rules are expressed as `Conditional.Cases[]` inside the standard color
> property path (`backColor.solid.color.expr.Conditional`).

**Table/matrix example** (entry in `values` array):

```json
{
  "properties": {
    "backColor": {
      "solid": {
        "color": {
          "expr": {
            "Conditional": {
              "Cases": [
                {
                  "Condition": {
                    "Comparison": {
                      "ComparisonKind": 2,
                      "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Right": { "Literal": { "Value": "500D" } }
                    }
                  },
                  "Value": { "Literal": { "Value": "'#1AAB40'" } }
                },
                {
                  "Condition": {
                    "Comparison": {
                      "ComparisonKind": 3,
                      "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Right": { "Literal": { "Value": "0D" } }
                    }
                  },
                  "Value": { "Literal": { "Value": "'#D64554'" } }
                }
              ],
              "DefaultValue": { "Literal": { "Value": "'#FFFFFF'" } }
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "Sum(Sales.TotalProfit)"
  }
}
```

**Chart example** (entry in `dataPoint` array — no selector needed):

```json
{
  "properties": {
    "fill": {
      "solid": {
        "color": {
          "expr": {
            "Conditional": {
              "Cases": [
                {
                  "Condition": {
                    "Comparison": {
                      "ComparisonKind": 2,
                      "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Right": { "Literal": { "Value": "500D" } }
                    }
                  },
                  "Value": { "Literal": { "Value": "'#1AAB40'" } }
                }
              ],
              "DefaultValue": { "Literal": { "Value": "'#118DFF'" } }
            }
          }
        }
      }
    }
  }
}
```

**Key rules:**

- All keys are **PascalCase**: `Conditional`, `Cases`, `Condition`, `Comparison`,
  `ComparisonKind`, `Value`, `DefaultValue`.
- The operator is **`Comparison`** (not `Compare`).
- `Left` must be a self-aggregating expression: use `Measure` (already aggregated)
  or wrap a `Column` in `Aggregation { Expression: Column, Function: N }`.
  A raw `Column` in `Left` breaks the visual.
- `DefaultValue` provides the fallback color when no case matches.
- For "is not equal" conditions, use `Not { Expression: { Comparison: { ComparisonKind: 0, ... } } }`
  — there is no NotEqual ComparisonKind.

**Selector requirements (critical — wrong selector silently drops all formatting):**

| Visual type | Required selector | Notes |
|-------------|-------------------|-------|
| Tables/matrices | `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }], "metadata": "<queryRef>" }` | Both `data` AND `metadata` required — either alone fails |
| Charts | No selector, or `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }` | Do NOT include `metadata` — it causes silent failure |

**ComparisonKind values:**

| Value | Operator | Meaning |
|-------|----------|---------|
| 0 | `==` | Equal |
| 1 | `>` | Greater Than |
| 2 | `>=` | Greater Than or Equal |
| 3 | `<` | Less Than |
| 4 | `<=` | Less Than or Equal |

## Type 3: Icon Sets

Adds icons alongside values in tables/matrices based on thresholds. Uses the
`icon` property in a `values` array entry with `Conditional.Cases[]`.

> ⚠️ There is no `iconRule` or `iconDefinition` property — these do not exist
> and are silently discarded. Icons use the same `Conditional.Cases[]` pattern
> as rules-based formatting, with icon name literals as `Value`.

**Table/matrix example** (entry in `values` array):

```json
{
  "properties": {
    "icon": {
      "kind": "Icon",
      "layout": {
        "expr": { "Literal": { "Value": "'Before'" } }
      },
      "verticalAlignment": {
        "expr": { "Literal": { "Value": "'Middle'" } }
      },
      "value": {
        "expr": {
          "Conditional": {
            "Cases": [
              {
                "Condition": {
                  "Comparison": {
                    "ComparisonKind": 2,
                    "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                    "Right": { "Literal": { "Value": "1000D" } }
                  }
                },
                "Value": { "Literal": { "Value": "'CircleHigh'" } }
              },
              {
                "Condition": {
                  "Comparison": {
                    "ComparisonKind": 3,
                    "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                    "Right": { "Literal": { "Value": "500D" } }
                  }
                },
                "Value": { "Literal": { "Value": "'CircleLow'" } }
              }
            ],
            "DefaultValue": { "Literal": { "Value": "'CircleMedium'" } }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "Sum(Sales.TotalProfit)"
  }
}
```

**Icon property structure:**

| Property | Required | Type | Values |
|----------|----------|------|--------|
| `kind` | ✅ | string | `"Icon"` (always) |
| `value` | ✅ | expr Conditional | `Conditional.Cases[]` with icon name literals |
| `layout` | optional | expr literal | `"Before"` (default), `"After"`, `"IconOnly"` (hide value) |
| `verticalAlignment` | optional | expr literal | `"Top"`, `"Middle"` (default), `"Bottom"` |

**Icon name catalog** (use as `Value: { Literal: { Value: "'<name>'" } }`):

| Family | Icons (high → low / full → empty) |
|--------|-----------------------------------|
| Circles (3-state) | `CircleHigh` · `CircleMedium` · `CircleLow` |
| Circles (4-state) | `CircleHigh` · `CircleMedium` · `4CircleMedium2` · `4CircleLow` |
| Circle fill | `CircleFilled` · `Circle75` · `CircleHalf` · `Circle25` · `CircleEmpty` |
| Circle pattern | `CircleGreenPatternFill` · `CircleYellowPatternFill` · `CircleRedPatternFill` · `CircleBlackFill` · `CircleGrayPatternFill` · `CirclePurplePatternFill` |
| Circle pattern (black bg) | `CircleGreenBlackBackgroundPatternFill` · `CircleYellowBlackBackgroundPatternFill` · `CircleRedBlackBackgroundPatternFill` |
| Circle pattern (outline) | `CircleGreenBlackOutlinePatternFill` · `CircleYellowBlackOutlinePatternFill` · `CircleRedBlackOutlinePatternFill` |
| Signs | `SignMedium` · `SignLow` |
| Symbols (✓/!/✗) | `SymbolHigh` · `SymbolMedium` · `SymbolLow` |
| Circled symbols | `CircleSymbolHigh` · `CircleSymbolMedium` · `CircleSymbolLow` |
| Triangles | `TriangleHigh` · `TriangleMedium` · `TriangleLow` |
| Colored arrows | `ColoredArrowUp` · `ColoredArrowUpRight` · `ColoredArrowRight` · `ColoredArrowDownRight` · `ColoredArrowDown` |
| Colored arrows (alt) | `ColoredArrowUpRed` · `ColoredArrowDownGreen` |
| Grey arrows | `GreyArrowUp` · `GreyArrowUpRight` · `GreyArrowRight` · `GreyArrowDownRight` · `GreyArrowDown` |
| Traffic lights | `TrafficHigh` · `TrafficMedium` · `TrafficLow` · `TrafficBlackRimmed` |
| Traffic lights (light) | `TrafficHighLight` · `TrafficMediumLight` · `TrafficLowLight` · `TrafficBlackRimmedLight` |
| Flags | `FlagHigh` · `FlagMedium` · `FlagLow` · `FlagBlack` |
| Flag pattern | `FlagGreenPatternFill` · `FlagYellowPatternFill` · `FlagRedPatternFill` |
| Stars | `StarHigh` · `StarMedium` · `StarLow` |
| Stars (light) | `StarHighLight` · `StarMediumLight` |
| Signal bars | `SignalBarFull` · `SignalBarMedium2` · `SignalBarMedium` · `SignalBarLow` · `SignalBarEmpty` |
| Signal bars (colored) | `SignalBarFullColored` · `SignalBarMedium2Colored` · `SignalBarMediumColored` · `SignalBarLowColored` |
| Quadrants | `QuadrantFull` · `Quadrant75` · `Quadrant50` · `Quadrant25` · `QuadrantEmpty` |
| Quadrants (colored) | `QuadrantFullColored` · `Quadrant75Colored` · `Quadrant50Colored` · `Quadrant25Colored` |

> ⚠️ Invalid icon names cause a Desktop crash ("Unable to find resource").
> Only use names from the catalog above.

**Selector:** Same as rules-based — tables/matrices require both `data` and
`metadata`; the `metadata` must reference the measure's queryRef.

## Type 4: Data Bars

In-cell bar visualization for tables/matrices. Applied per-column via metadata selector.

**Placed as an entry in the `columnFormatting` array (NOT `values`), with a
metadata-only selector:**

> ⚠️ **Do not use `dataViewWildcard` for data bars.** Unlike `values.backColor`,
> `values.fontColor`, and `values.icon`, data bars are column-level formatting.
> They render with `{ "selector": { "metadata": "<queryRef>" } }`; adding
> `data: [{ "dataViewWildcard": ... }]` causes the bars to disappear.

```json
{
  "properties": {
    "dataBars": {
      "positiveColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } },
      "negativeColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#D64554'" } } } } },
      "axisColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#999999'" } } } } },
      "reverseDirection": { "expr": { "Literal": { "Value": "false" } } },
      "hideText": { "expr": { "Literal": { "Value": "false" } } }
    }
  },
  "selector": { "metadata": "Sales.Revenue" }
}
```

Properties: `positiveColor`, `negativeColor`, `axisColor` (fills), `reverseDirection` (bool),
`hideText` (bool), `minValue`/`maxValue` (optional numeric scale bounds).

## Type 5: Web URL

Turns text into clickable hyperlinks using a URL field:

```json
{
  "properties": {
    "webUrl": {
      "expr": {
        "Column": {
          "Expression": { "SourceRef": { "Entity": "Companies" } },
          "Property": "WebsiteUrl"
        }
      }
    }
  }
}
```

Supported in tables and matrices.

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

| Function | Meaning |
|----------|---------|
| 3 | Min |
| 4 | Max |

### Selector

The `metadata` queryRef targets the **column being colored** (the measure or
column whose cells receive the color), not the color source column.

| `matchingOption` | Meaning |
|------------------|---------|
| 0 | All data points including totals |
| 1 | Values only (excludes totals) |

### Applies to

Works with `backColor` and `fontColor`. The color source column must contain
valid hex strings (e.g., `#FF6B35`).
