# Conditional Formatting Patterns - Part 5

## Contents

- [Type 2: Rules-Based Formatting](#type-2-rules-based-formatting)
  - [Number vs percent thresholds (and percentile)](#number-vs-percent-thresholds-and-percentile)
  - [Rule bounds: one-sided vs two-sided ranges](#rule-bounds-one-sided-vs-two-sided-ranges)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

## Type 2: Rules-Based Formatting

Applies colors based on value conditions using `Conditional.Cases[]` inside a
color property. The structure is the same for charts (`dataPoint.fill`) and
tables/matrices (`values.backColor` or `values.fontColor`).

> ⚠️ There is no `backColorRule` or `fontColorRule` property — these do not
> exist. Rules are expressed as `Conditional.Cases[]` inside the standard color
> property path (`backColor.solid.color.expr.Conditional`).

> **`fontColor` is skipped on sparkline columns.** A `backColor`/`fontColor`
> rule works on ordinary columns; a `fontColor` rule targeting a sparkline
> column is ignored (`backColor` still applies).

> ⚠️ **Every color band that users must edit in Power BI Desktop must be an
> explicit `Cases[]` entry.** Desktop renders `DefaultValue`, but its
> conditional-formatting dialog does not expose that fallback as an editable
> rule row. Do not encode an intended low/red band only as `DefaultValue`.
> Add an explicit comparison for it (for example, `< 1000000`) and reserve
> `DefaultValue` for blanks or otherwise unmatched values. It may repeat the
> lowest-band color when that is the safest fallback.

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
                      "ComparisonKind": 2,
                      "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Right": { "Literal": { "Value": "0D" } }
                    }
                  },
                  "Value": { "Literal": { "Value": "'#FFFFFF'" } }
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
              ]
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

> The three ordered cases cover every value (`>= 500` green, `>= 0` white, `< 0`
> red) — no `DefaultValue` needed; each is an editable rule in the dialog.

**Chart example** (entry in a supported chart object array):

```json
{
  "properties": {
    "<colorProperty>": {
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
                      "Right": { "Literal": { "Value": "500D" } }
                    }
                  },
                  "Value": { "Literal": { "Value": "'#118DFF'" } }
                }
              ]
            }
          }
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }]
  }
}
```

Replace `<colorProperty>` and its containing object using the capability
matrix. For example:

| Result | Object | Replace `<colorProperty>` with |
|--------|--------|--------------------------------|
| Bar/column/slice/rectangle/bubble color | `dataPoint` | `fill` |
| Full line/area series color | `dataPoint` | `fill` |
| Single-series line/area marker color by category | `dataPoint` | `fill` |
| Single-series line segment color | `lineStyles` | `strokeColor` |
| Data-label color | `labels` | `color` |

**Key rules:**

- All keys are **PascalCase**: `Conditional`, `Cases`, `Condition`, `Comparison`,
  `ComparisonKind`, `Value`, and `DefaultValue`.
- The operator is **`Comparison`** (not `Compare`).
- `Left` must be a self-aggregating expression: use `Measure` (already
  aggregated) or wrap a `Column` in
  `Aggregation { Expression: Column, Function: N }`. A raw `Column` in `Left`
  breaks the visual. See
  Aggregation: columns vs. measures for the
  full `Function` enum and valid/invalid examples.
- `DefaultValue` provides the fallback color when no case matches.
- For "is not equal", use
  `Not { Expression: { Comparison: { ComparisonKind: 0, ... } } }`; there is no
  `NotEqual` `ComparisonKind`.

**Selector requirements (critical — wrong selector silently drops all formatting):**

| Visual type | Required selector | Notes |
|-------------|-------------------|-------|
| Tables/matrices | `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }], "metadata": "<queryRef>" }` | Both `data` AND `metadata` required — either alone fails |
| Single-series chart points | `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }` | Matches identity-bearing instances and excludes totals |
| Category-role chart rules | `{ "data": [{ "roles": ["Category"] }] }` | Replace `Category` with the visual's actual category role name |
| Dynamic legend-series rules | `{ "data": [{ "roles": ["Series"] }], "hierarchyMatching": 1 }` | `hierarchyMatching: 1` is Partial; it enables per-series evaluation |

**`ComparisonKind` values:**

| Value | Operator | Meaning |
|-------|----------|---------|
| 0 | `==` | Equal |
| 1 | `>` | Greater Than |
| 2 | `>=` | Greater Than or Equal |
| 3 | `<` | Less Than |
| 4 | `<=` | Less Than or Equal |

### Number vs percent thresholds (and percentile)

A rule threshold is the `Right` operand of each `Comparison`. In Power BI
Desktop the rules dialog exposes a per-boundary **Number / Percent** dropdown;
these are the only two threshold kinds. They encode differently:

| Threshold kind | Meaning | `Right` encoding |
|----------------|---------|------------------|
| **Number** (default) | A fixed, absolute cutoff | `Literal` — `{ "Literal": { "Value": "500D" } }` |
| **Percent** | A percent **of the based-on field's min→max range**; recomputed as the data changes | `RangePercent` (see below) |
| **Percentile** | *Not a conditional-formatting threshold kind* | — unsupported; see note |

> 📊 **Where the Percent kind is available (tables/matrices *and* charts).** The
> *Percent* (`RangePercent`) kind is offered for **any Type-2 rules visual that has
> a category grouping** — table/matrix rows, or a chart **Category/Axis**. Two
> preconditions are enforced by Desktop (`disableAutoRange = !hasGrouping || totalMatchingOption.disableAutoRange`):
> - **Grouping required.** A visual with no grouping (e.g. a single-value card)
>   offers **Number only**.
> - **Instances, not totals.** The rule must target instances — use the
>   instances-only selector `matchingOption: 1` (`InstancesOnly`). With
>   `InstancesAndTotals` (`0`, the default) or `TotalsOnly` (`2`) Desktop
>   **disables** Percent and the boundary falls back to Number.

**Number thresholds on a percentage-valued measure.** When the based-on field is
itself a percentage (e.g. `Margin %` stored as `0.25` for 25%), a Number
threshold must be the **actual decimal value**, not the display percentage:
`0.25D`, never `25D`. This matches Desktop's guidance to pick *Number* (not
*Percent*) and type decimals for percentage fields. The *Percent* kind below is
a different concept — percent of the value range, not the field's own units.

> 🟢 **Detect a percentage field before authoring a Number threshold.** Read the
> based-on field (the rule's `Left`) in the **semantic model** and inspect its
> `formatString` — the TMDL `measure`/`column` line, or the measure/column
> `formatString` in `model.bim`. Look for an **active `%` token** — a `%` that is
> **not** escaped as `\%` and **not** inside a quoted literal (`"…"`). An active
> `%` (e.g. `0.0%`, `#,0.0%;-#,0.0%`, `0.0%;-0.0%;0.0%`) means the field is stored
> as a **decimal** and Power BI multiplies by 100 for display — choose a
> **Number** `Literal` and type the decimal (`0.25D` for 25%). An **escaped or
> quoted** percent sign (`0\%`, `0"%"`) prints a literal `%` **without** ×100
> scaling, so the stored value already equals the displayed number — type it
> as-is (`25` displays `25%` → author `25D`). When unsure, read the field's
> stored values against its display: `0.0%` storing `0.25` shows `25%` (author
> `0.25`); `0\%` storing `25` shows `25%` (author `25`). If there is no active
> `%`, type the value as-is. `validate` runs structurally on the PBIR only and
> does **not** read the model, so it cannot enforce this — the agent must perform
> the check (needs a local `.pbip` semantic model or a live model via Modeling
> MCP). Do **not** use the *Percent* (`RangePercent`) kind just because the field
> is a percentage — that is a different concept (percent of the value range).

**Percent-of-range thresholds (`RangePercent`).** A *Percent* boundary is not a
static number: Desktop resolves it against the current **minimum and maximum of
the based-on field**, so the effective cutoff moves as the data range changes
(e.g. "top 25% of the range"). Encode the threshold's `Right` as a
`RangePercent` whose `Min`/`Max` are the global aggregate min/max of the
based-on field:

- `Percent` is a fraction **0–1** (Desktop shows 0–100; divide by 100 — `25` → `0.25`).
- `Min` / `Max` wrap the based-on field in `ScopedEval` →
  `Aggregation` (`Function` **3 = Min**, **4 = Max**) → `ScopedEval` with an
  `AllRolesRef` scope. The field inside `Min`/`Max` must be the **same** field
  as the rule's `Left` (the based-on field).

```json
{
  "Condition": {
    "Comparison": {
      "ComparisonKind": 2,
      "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
      "Right": {
        "RangePercent": {
          "Percent": 0.25,
          "Min": {
            "ScopedEval": {
              "Expression": {
                "Aggregation": {
                  "Expression": {
                    "ScopedEval": {
                      "Expression": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Scope": [{ "AllRolesRef": {} }]
                    }
                  },
                  "Function": 3
                }
              },
              "Scope": []
            }
          },
          "Max": {
            "ScopedEval": {
              "Expression": {
                "Aggregation": {
                  "Expression": {
                    "ScopedEval": {
                      "Expression": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                      "Scope": [{ "AllRolesRef": {} }]
                    }
                  },
                  "Function": 4
                }
              },
              "Scope": []
            }
          }
        }
      }
    }
  },
  "Value": { "Literal": { "Value": "'#1AAB40'" } }
}
```

The `Min`/`Max` shape is fixed boilerplate — only the inner based-on field and
the `Percent` value change per rule. Keep the two boundaries **within a single
rule** the same kind (both Number, or both Percent) — see
[Rule bounds: one-sided vs two-sided ranges](#rule-bounds-one-sided-vs-two-sided-ranges).

**Charts use the identical `RangePercent` encoding.** Percentage thresholds are
not table/matrix-only — place the same `Right` `RangePercent` block in the
chart's color object (e.g. `dataPoint.fill`; see the
[Type 2 chart example](#type-2-rules-based-formatting) and capability matrix for
the object/property per visual) and use a chart **instances-only** selector
`{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }` (no `metadata`).
The `Min`/`Max` inner field is still the rule's based-on `Left`, and the same
grouping/instances preconditions above apply (the chart's Category/Axis provides
the grouping).

> ⚠️ **Percentile thresholds are not supported** in conditional formatting on
> **any** visual — tables, matrices, or charts. The rules dialog offers only
> *Number* and *Percent* — there is no
> percentile threshold kind, and there is no expression that encodes one here.
> (The `Percentile { Expression, K, Exclusive }` expression is a DAX
> aggregation for **summarizing a field**, not a CF threshold.) To approximate a
> percentile cutoff, add a measure that computes the percentile (e.g.
> `PERCENTILEX.INC`) and compare the based-on field against that measure or an
> absolute Number.

> ℹ️ **Gradient (color scale) stops are not percent/percentile either.** A
> `FillRule` `min`/`mid`/`max` stop takes only **auto** (omit `value` → Desktop
> uses the data's lowest/highest) or an **absolute custom number**
> (`value` `Literal`). Do not place a `RangePercent` in a gradient stop — percent
> semantics are a *rules-only* feature. See Type 1.

### Rule bounds: one-sided vs two-sided ranges

One-sided `Cases[]` entries — a single `Comparison` like the examples above — are
**valid and render correctly**. Author them freely; do **not** pad rules with
synthetic sentinel bounds to force a closed range. Encode every color band —
including the default/"else" color — as an explicit `Cases[]` entry rather than
relying on `DefaultValue` (see
[Type 2: Rules-Based Formatting](#type-2-rules-based-formatting)).

Use a two-sided `Condition.And` band only for **interior** bands that need both a
floor and a ceiling. Keep the **outermost** bands open-ended (a single
`Comparison`) so the full data domain stays covered — do **not** add sentinel
outer bounds unless they are verified business-domain limits, since a sentinel
leaves values beyond it uncovered. Both `Comparison`s in an interior band use the
**same threshold kind** on their `Right` operands (both `Literal` Number, or both
`RangePercent`):

```json
"Cases": [
  {
    "Condition": { "Comparison": { "ComparisonKind": 2, "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } }, "Right": { "Literal": { "Value": "500D" } } } },
    "Value": { "Literal": { "Value": "'#1AAB40'" } }
  },
  {
    "Condition": {
      "And": {
        "Left":  { "Comparison": { "ComparisonKind": 2, "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } }, "Right": { "Literal": { "Value": "0D" } } } },
        "Right": { "Comparison": { "ComparisonKind": 3, "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } }, "Right": { "Literal": { "Value": "500D" } } } }
      }
    },
    "Value": { "Literal": { "Value": "'#FFFFFF'" } }
  },
  {
    "Condition": { "Comparison": { "ComparisonKind": 3, "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } }, "Right": { "Literal": { "Value": "0D" } } } },
    "Value": { "Literal": { "Value": "'#D64554'" } }
  }
]
```

**Rules:**

- `And { Left, Right }` and `Comparison { ComparisonKind, Left, Right }` are
  **PascalCase** (matches the Desktop serializer).
- Every `Comparison` in a rule must use the **same `Left`** (the based-on field),
  and both bounds of an interior `And` band must use the **same threshold kind**
  on `Right`.
- Desktop's canonical operators are lower **`>=` (2)** and upper **`<` (3)** — keep
  that ordering so contiguous `[min, max)` bands leave no gaps or overlaps.
- Cases evaluate top-down (first match wins); order them so the intended band is
  reached first.
- Keep the outermost bands open-ended so the full domain is covered; reach for an
  interior `And` band only where a color needs both a floor and a ceiling.
