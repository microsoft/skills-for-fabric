# Conditional Formatting Patterns - Part 6

## Contents

- [Type 3: Icon Sets](#type-3-icon-sets)
  - [Icon name catalog](#icon-name-catalog)
- [Type 4: Data Bars](#type-4-data-bars)
- [Type 5: Web URL](#type-5-web-url)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

## Type 3: Icon Sets

Adds icons alongside values in tables/matrices based on thresholds. Uses the
`icon` property in a `values` array entry with `Conditional.Cases[]`.

> ⚠️ There is no `iconRule` or `iconDefinition` property — these do not exist
> and are silently discarded. Icons use the same `Conditional.Cases[]` pattern
> as rules-based formatting, with icon-name literals as `Value`.

> ℹ️ Icon rule thresholds support the same **Number vs Percent** kinds as
> Type 2 — a percent-of-range
> icon boundary uses the identical `RangePercent` `Right` encoding. Percentile
> is likewise unsupported.

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
              },
              {
                "Condition": {
                  "Comparison": {
                    "ComparisonKind": 2,
                    "Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "TotalProfit" } },
                    "Right": { "Literal": { "Value": "500D" } }
                  }
                },
                "Value": { "Literal": { "Value": "'CircleMedium'" } }
              }
            ]
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

> The three ordered cases cover every band (`>= 1000` `CircleHigh`, `< 500`
> `CircleLow`, `>= 500` `CircleMedium`) — no `DefaultValue`. To leave a band
> unformatted, omit its case (no icon renders for those values).

**Icon property structure:**

| Property | Required | Type | Values |
|----------|----------|------|--------|
| `kind` | ✅ | string | `"Icon"` (always) |
| `value` | ✅ | expr Conditional | `Conditional.Cases[]` with icon name literals |
| `layout` | optional | expr literal | `"Before"` (default), `"After"`, `"IconOnly"` (hide value) |
| `verticalAlignment` | optional | expr literal | `"Top"`, `"Middle"` (default), `"Bottom"` |

### Icon name catalog

Use these names as `Value: { Literal: { Value: "'<name>'" } }`:

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
`hideText` (bool), `minValue`/`maxValue` (optional numeric scale bounds),
`totalMatchingOption` (optional totals enum). Every property is an `Expr` node —
use the `{ "expr": { "Literal": { "Value": "…" } } }` shape (the fills use the
`solid.color.expr` shape shown above).

**Optional `minValue` / `maxValue` — fixed axis scale.** By default a data bar
auto-scales (longest bar = the column's largest value). Set both to pin the axis
to fixed bounds so bar lengths stay comparable across refreshes/visuals. Numeric
literals use the `D` suffix:

```json
"dataBars": {
  "minValue": { "expr": { "Literal": { "Value": "0D" } } },
  "maxValue": { "expr": { "Literal": { "Value": "1000D" } } },
  "positiveColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } },
  "negativeColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#D64554'" } } } } },
  "axisColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#999999'" } } } } },
  "reverseDirection": { "expr": { "Literal": { "Value": "false" } } },
  "hideText": { "expr": { "Literal": { "Value": "false" } } }
}
```

Omit `minValue`/`maxValue` (as in the first example) for auto-scaling. If you set
one, set both.

> **`hideText: true` = the dialog's "Show bar only" toggle.** With `hideText: false`
> (default) each cell shows the number *and* the bar; with `hideText: true` the
> numeric text is hidden and **only the bar** is drawn. Do not stack `hideText: true`
> on the same column as a `fontColor` rule/gradient — the hidden text makes the font
> color impossible to see.

> ⚠️ **Data bars are numeric-only.** They render only on columns whose value is
> a number (`shouldApplyDataBars` requires a numeric cell). A data-bar rule on a
> text/date column is silently ignored — no error.

> **Data-bar totals matching is separate.** Data bars carry their own
> `totalMatchingOption`, independent of the `values`-rule `matchingOption`. It is
> an `Expr`-wrapped integer literal (`L` suffix) using the same
> `DataViewWildcardMatchingOption` enum as `dataViewWildcard.matchingOption`:
> `0` = instances **and** totals, `1` = instances only (**default** when omitted),
> `2` = totals only. By default bars render on data cells only; add
> `"totalMatchingOption": { "expr": { "Literal": { "Value": "0L" } } }` inside
> `dataBars` to also draw bars on total/subtotal rows (or `"2L"` to draw bars on
> the total rows only). Unlike the `backColor`/`fontColor`/`icon` selectors,
> the data-bar selector stays `metadata`-only — the totals behavior is controlled
> by this property, not by a `dataViewWildcard` selector.

## Type 5: Web URL

Turns table/matrix cell values into clickable hyperlinks. Two distinct
mechanisms exist: Web URL data-category fields work on `tableEx` and
`pivotTable`, while `values.webURL` conditional formatting is a `pivotTable`
route. Pick the mechanism that matches the data and target visual.

**1. Data-category Web URL (data-category driven — no rule to author).** If the displayed
field's **Data Category is "Web URL"** (TMDL `dataCategory: WebUrl`), each value
renders as a link automatically. **By default the cell prints the raw URL text as a
clickable hyperlink** (e.g. `https://bing.com/search?q=...`). Optionally **collapse
that URL text into a compact 🔗 glyph** by enabling the `urlIcon` boolean — valid on
`values`, `columnHeaders`, and `rowHeaders`. The glyph is **not** the default: with
`urlIcon` off you see the full URL string; only with `urlIcon: true` do you see the
glyph instead.

```json
"values": [{ "properties": { "urlIcon": { "expr": { "Literal": { "Value": "true" } } } } }]
```

When a field is already a Web URL data-category column, **do not** also add a
`webURL` rule to it — the displayed value wins and the rule is ignored (a
phishing-prevention guard).

> **Data-category links include the total cell.** A Web URL data-category column
> renders its **grand-total / subtotal** cell as a link too (e.g. a "Total" row
> showing the base URL as a hyperlink). This is inherent to the field's data
> category and is **not** governed by any `matchingOption` — that selector only
> controls the `webURL` conditional-formatting rule below, not data-category
> auto-linking. To stop a total from linking, change the field/measure, not a CF
> setting.

**2. `webURL` conditional formatting (matrix only; URL field differs from the
displayed field).** Use on `pivotTable` when the **displayed** column is ordinary
text/number (a company name, a measure) but the link target lives in a
**separate URL field**. The current `tableEx` formatting contract does not
expose `values.webURL`; use a displayed Web URL data-category field or a matrix
when a separate URL driver is required.

> ⚠️ **The property key is `webURL` (capital `URL`), on the `values` object.** A
> lowercase `webUrl` key is silently ignored.

Requirements:
- Object / property: `values.webURL`.
- Selector: `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }], "metadata": "<displayed column queryRef>" }` — both `data` (InstancesOnly = `1`) and `metadata` (the **displayed** column, not the URL source) are required.
- Value: the URL-driving field expression. A **measure** is referenced directly; a **column** is wrapped in `Aggregation` (`Function: 3` = Min), the same field-value shape as Type 6: Field-Driven Color.
- Not allowed on a displayed column that is itself a Web URL data-category column.
- **Not applied to sparkline columns** — a `webURL` rule on a sparkline column is skipped.
- **Totals:** the `matchingOption: 1` above targets data cells only. To make total/subtotal cells clickable too, use `matchingOption: 0` (or `2` for totals only) — see Totals, subtotals, and the matrix `total` slot. (Note: a **data-category** Web URL column links its total cell automatically, regardless of `matchingOption` — that is the field's data category, not this rule.)

Measure-driven URL:

```json
{
  "properties": {
    "webURL": {
      "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Companies" } }, "Property": "WebsiteUrl" } }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "Companies.CompanyName"
  }
}
```

Column-driven URL — wrap in `Aggregation` with `Function: 3` (Min):

```json
{
  "properties": {
    "webURL": {
      "expr": {
        "Aggregation": {
          "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "Companies" } }, "Property": "WebsiteUrl" } },
          "Function": 3
        }
      }
    }
  },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }],
    "metadata": "Companies.CompanyName"
  }
}
```

Web URL diagnostics:

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cell shows plain text, no link | `metadata` omitted, or points at the URL source instead of the displayed column | Set `metadata` to the **displayed** column's queryRef and include the `dataViewWildcard` `data` entry |
| Rule silently dropped | Lowercase `webUrl` key, or `data`/`metadata` half-specified | Use `webURL`; supply both selector parts |
| No link even though field has URLs | Displayed column is itself a Web URL data-category column | Remove the rule; the data-category auto-link already applies |
| Link points to the visible value, not the URL field | Column source not wrapped in `Aggregation` | Wrap column exprs in `Aggregation` (`Function: 3`); reference measures directly |
| Non-URL / malformed values render without links | Runtime URL validation rejects them | Ensure the source field yields absolute `http(s)` URLs |
