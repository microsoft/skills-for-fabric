# Conditional Formatting Patterns - Part 3

## Contents

  - [Buttons and shapes](#buttons-and-shapes)
- [Selector summary by visual type](#selector-summary-by-visual-type)
- [Driving field vs. target field](#driving-field-vs-target-field)
- [Aggregation: columns vs. measures](#aggregation-columns-vs-measures)
- [Color value results (hex)](#color-value-results-hex)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

### Buttons and shapes

Buttons (`actionButton`) and shapes (`shape`) accept data-driven **color** on
every color property, plus a data-driven **text label**; buttons additionally
accept a data-driven **Web URL action target**.

- **Field value** (a measure returning a color/label string) →
  Type 6: Field-Driven Color
- **Rules** (`Conditional.Cases[]`) →
  Type 2: Rules-Based Formatting
- **Gradient** (`FillRule` / `linearGradient2|3`; a stop's `color` takes a
  `Literal` directly, never wrapped in `expr`) →
  Type 1: Color Gradient (FillRule)
- **Dual-entry + state selectors** → see *Selector requirements* below

> **The bound measure must exist in the model and return a value valid for the
> target property** — a text color (e.g. `"#107C10"`) for color properties, a
> caption string for the text label, or a URL string for the Web URL target.
> If the referenced field is missing or in an error state, Power BI Desktop
> errors the visual (grey "See details" ⊗ overlay) and shows a warning icon in
> the visual header. Treat this as a **missing/invalid field** state, **not** an
> unsupported binding. Bind an existing measure that returns the correct type for
> the target property (a color string, caption, or URL). Do not swap to another
> field unless it already exists and returns a valid value. If no suitable
> measure exists, or a measure returns the wrong type, delegate the model-side
> change to the `semantic-model-authoring` skill / Power BI Modeling MCP (out of
> scope for this skill), or ask the user to add or fix the measure.

**What can be data-driven**

| Property | Object.property | Button | Shape | Field value | Rules | Gradient |
|---|---|:--:|:--:|:--:|:--:|:--:|
| Fill color | `fill.fillColor` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Outline/border color | `outline.lineColor` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Text/font color | `text.fontColor` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Text label (string) | `text.text` | ✅ | ✅ | ✅ | — | — |
| Icon color | `icon.lineColor` | ✅ | — | ✅ | ✅ | ✅ |
| Shadow color | `shadow.color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Glow color | `glow.color` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Web URL action target** | `visualLink.webUrl` | ✅ | ✅ | ✅ | — | — |

Field value, rules, and gradient apply uniformly to **every** color property.
The text label and the Web URL action target take **field value only**.
**Shape CF is geometry-independent** — every property/method above works the same
on any `tileShape` (rectangle, oval, hexagon, triangle, …).

**Selector requirements (buttons and shapes).** Both visuals use *typed
`id`-selectors*, not `metadata`/`dataViewWildcard` selectors:

- **The binding must live in an `id`-selected entry.** The measure binding
  (color, label, …) must sit in an entry carrying
  `"selector": { "id": "<state>" }`. Putting the binding in a no-selector entry
  (or omitting the `id`) **silently fails to render**.
- **Buttons — separate `show` entry.** Author each object as **two entries**: a
  bare entry (no selector) that sets `show`, plus the state-`id` entry that holds
  the binding.
- **Shapes — object-specific Show placement.** Put data-bound values in an
  `{ "id": "default" }` entry. For `fill` and `outline`, keep `show` in that
  selected entry. For `text`, `shadow`, and `glow`, put `show` in a selectorless
  entry and the bound/style properties in the selected entry; Desktop ignores
  `text.show` when it is stored only in the selected entry.
- **State selectors (buttons).** The `id` may be `default`, `hover`, `selected`,
  or `disabled`. Bind each state's entry independently.
- **Shapes are single-state:** author with `{ "id": "default" }` only; they have
  no hover/selected/disabled.

| State `id` | Button | Shape |
|---|:--:|:--:|
| `default` | ✅ | ✅ |
| `hover` | ✅ | — |
| `selected` | ✅ | — |
| `disabled` | ✅ | — |

**Text label.** `text.text` accepts a measure that returns the caption string
(e.g. `Btn Label = "Rev YoY: " & FORMAT([Revenue YoY %], "0.0%")`). Only **field
value** drives the label; rules and gradients drive **colors**, not the string.

**Cannot be authored (button/shape CF limits)**

- **On `shadow`/`glow`, only `color` is data-driven.** The color binds (see
  matrix), but the numeric params (`shadowBlur`, `shadowDistance`, `angle`, glow
  blur) are static `Literal`s and cannot be bound to a measure.
- **For icons, only `icon.lineColor` is data-driven.** The glyph
  (`icon.shapeType`), size, and placement are static — you cannot bind the icon
  shape to a measure. **Shapes have no `icon` object at all.**
- **Buttons and shapes support data-driven Web URLs.** Both use the selectorless
  `visualLink` VCO contract. Shapes still lack button state variants such as
  hover, selected, and disabled.
- **The label string cannot use rules or gradients** — only a field-value
  measure returns text. Likewise the Web URL target is field-value only (a URL
  string), not rules/gradients.
- **`disabled` renders when a button's action is unavailable.** Some triggers: a
  `Drillthrough` button with no data point selected, or a `DataFunction` button
  whose item reference or a required parameter binding is invalid.

**Field-value example — formatting.** Bind a color property to a color measure.

*Button* — two entries: `show` in Entry 1, the binding in the `default` state
entry:

```json
"fill": [
  { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
  { "properties": { "fillColor": { "solid": { "color": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Btn Color" } } } } } }, "selector": { "id": "default" } }
]
```

*Shape* — keep the Show toggle selectorless and the binding in the
`{ "id": "default" }` entry:

```json
"fill": [
  { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
  { "properties": { "fillColor": { "solid": { "color": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Btn Color" } } } } } }, "selector": { "id": "default" } }
]
```

The same binding works on `outline.lineColor`, `text.fontColor`, `icon.lineColor`
(buttons), `shadow.color`, and `glow.color`. `Btn Color` must return a valid text
color, e.g. `Btn Color = IF([Revenue YoY %] >= 0, "#107C10", "#D13438")`. Bind a
**column** the same way but wrapped in `Aggregation` (see
Type 6). For **rules** and **gradients**, use the
same color slot with the `Conditional`/`FillRule` expressions from
Type 2 and
Type 1 — add one rule-bound entry per state to
react to hover/selected; for shapes, use the `default` entry only. If the bound
measure is missing or returns a non-color value, Power BI errors the visual and
shows a field-error indicator — restore/repair the measure to fix it.

**Field-value example — action (Web URL).** On buttons and shapes, the Web URL action
*target* is data-driven: set `visualLink.type` to `'WebUrl'` and bind `webUrl` to
a measure that returns a URL string. `visualLink` lives under
`visualContainerObjects` (not `objects`) and takes **no `id` selector**:

```json
"visualLink": [
  { "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "type": { "expr": { "Literal": { "Value": "'WebUrl'" } } },
      "webUrl": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Btn URL" } } }
  } }
]
```

The same selectorless contract is used by `actionButton` and `shape`. The bound
measure must return a URL string and should be marked
`dataCategory: WebUrl` in the model, e.g.
`Btn URL = "https://learn.microsoft.com/power-bi/create-reports/desktop-buttons"`.

## Selector summary by visual type

| Visual type | CF type | Object/property | Selector |
|-------------|---------|-----------------|----------|
| Tables/matrices | Data bars | `columnFormatting.dataBars` | `metadata` only |
| Tables/matrices | Background / font color | `values.backColor` / `values.fontColor` | `dataViewWildcard + metadata` |
| Tables/matrices | Icons | `values.icon` | `dataViewWildcard + metadata` |
| Tables/matrices | Web URL (differing field) | `values.webURL` | `dataViewWildcard + metadata` (displayed column) |
| Tables/matrices | Image alt text | `accessibility.altTextColumns` | `dataViewWildcard (matchingOption 0) + metadata` (image column) |
| Single-series chart data points | Gradient / rules / field color | Direct target from the matrix | `dataViewWildcard` with `matchingOption: 1` |
| Category-driven colors | Gradient / rules / field color | Direct target from the matrix | Role wildcard for the category role, for example `{ "data": [{ "roles": ["Category"] }] }` |
| Single-series line markers by category | Gradient / rules / field color | `dataPoint.fill` | `{ "data": [{ "roles": ["Category"] }] }`; omit `lineStyles.markerColor` |
| Dynamic legend series | Gradient / rules / field color | Usually `dataPoint.fill` | `{ "data": [{ "roles": ["Series"] }], "hierarchyMatching": 1 }` |
| Chart data labels | Gradient / rules / field color | `labels.color` | `dataViewWildcard` with `matchingOption: 1`; preserve a series `metadata` selector when targeting one measure |
| Card (`cardVisual`) | Callout / label font color | `value.fontColor` / `label.fontColor` | `{ "id": "default" }` |
| KPI (`kpi`) | Indicator / goal / distance / date font color | `indicator.fontColor`, `goals.*FontColor`, `lastDate.lastDateFontColor` | No selector |
| Azure Maps (`azureMap`) layer fill | Gradient / rules / field color | Icon marker: `bubbleLayer.fillColor`; 3D column / choropleth: `dataPoint.fill`; image marker: unsupported | `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }`; all-series Legend CF requires a Desktop build that exposes the all-series `fx` control. Keep static marker settings in a separate unselected `bubbleLayer` entry |
| Azure Maps (`azureMap`) marker rotation | Field value (degrees) | `bubbleLayer.markerRotation` | `{ "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }` |
| Button (`actionButton`) | Field value / rules / gradient color (fill, outline, text, icon, shadow, glow) + field-value text label + field-value Web URL action target | e.g. `fill.fillColor`, `text.text`, `visualLink.webUrl` | `{ "id": "<state>" }` per color state; `visualLink` takes no selector |
| Shape (`shape`) | Field value / rules / gradient color (fill, outline, text, shadow, glow) + field-value text label + field-value Web URL action target | e.g. `fill.fillColor`, `text.text`, `visualLink.webUrl` | `{ "id": "default" }` for formatting; selectorless `visualLink` |

> This table covers **value-driven conditional formatting**. **Static** per-series
> color (coloring a specific series a fixed hue) uses a `metadata` selector
> instead — see color-strategy.md § Per-Series Colors (see `color-strategy.md`, section `pattern-per-series-colors`).

## Driving field vs. target field

Use one flow and keep its input and output references independent:

`driver expression` → `FillRule` / `Conditional` → `target selector` → `target property`

For example, to color a **Revenue** cell by **Profit %**, put the Profit %
expression in `Input` or `Left`, identify Revenue with `selector.metadata`, and
attach the rule to `values.backColor`. Even when driver and target are the same
field, author both references. A wrong driver or selector silently drops the
formatting; use the [selector summary](#selector-summary-by-visual-type).

## Aggregation: columns vs. measures

A driving (or color-source) field must resolve to **one value per formatted
cell/point**. Choose its expression in this order:

1. If the driver already exists as a visual query selection, use `SelectRef`
   with that selection's exact `ExpressionName`.
2. Otherwise, reference a DAX measure directly with `Measure`.
3. Otherwise, wrap the raw column in `Aggregation(Column, Function)`.

| Driver kind | How to reference it | Aggregation wrapper |
|-------------|---------------------|---------------------|
| **Existing visual query selection** | `SelectRef { ExpressionName }` | Use the existing selection as authored; do not add another wrapper. |
| **Measure** (DAX) | Directly — `Measure { Expression: SourceRef, Property }` | ❌ None — a measure is already aggregated. Wrapping it in `Aggregation` is invalid. |
| **Column** | `Aggregation { Expression: { Column: {...} }, Function: N }` | ✅ Required — a raw `Column` breaks the visual. |

`Function` (`N`) uses the semantic-query `QueryAggregateFunction` enum:

| Function | Meaning | Typical CF use |
|----------|---------|----------------|
| 0 | Sum | Numeric magnitude columns feeding a gradient/rule |
| 1 | Average | Rate / ratio columns |
| 2 | Count (distinct) | Occurrence counts |
| 3 | Min | **Text / color / URL / image** source columns (field-driven) |
| 4 | Max | Text / color columns; "highest wins" |
| 5 | Count (non-null) | Non-null occurrence counts |

> Values 6–8 (Median, StandardDeviation, Variance) exist in the enum but are
> rarely appropriate as CF drivers. For a **text/color/URL** source column, use
> `Min` (3) or `Max` (4) — a text column has no numeric Sum/Average. For a
> **numeric** driving column, use `Sum` (0) or `Average` (1) to match how the
> column aggregates in the visual. There is no `First` function in this enum;
> "first/last" text behavior is expressed via `Min`/`Max`.

✅ **Correct — measure driver (no wrapper):**
```json
"Left": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Profit %" } }
```

✅ **Correct — column driver (Sum-wrapped):**
```json
"Left": {
  "Aggregation": {
    "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Discount" } },
    "Function": 0
  }
}
```

❌ **Wrong — raw column, no aggregation (breaks the visual):**
```json
"Left": { "Column": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Discount" } }
```

❌ **Wrong — aggregating a measure (a measure is already aggregated):**
```json
"Left": { "Aggregation": { "Expression": { "Measure": { "Expression": { "SourceRef": { "Entity": "Sales" } }, "Property": "Profit %" } }, "Function": 0 } }
```

This rule applies identically to gradient `Input`, rule `Left`, and
field-driven color sources.

## Color value results (hex)

Every authored color literal — gradient stops, rule `Value`, `DefaultValue`,
null-strategy `color` — and every hex a **field-driven** source returns must be
a valid hex string, single-quote-wrapped inside the `Literal` `Value`:

```json
{ "Literal": { "Value": "'#RRGGBB'" } }
```

| Form | Example | Where valid |
|------|---------|-------------|
| `#RRGGBB` (6-digit) | `"'#118DFF'"` | ✅ Everywhere — gradient stops, rules, field values. **Preferred.** |
| `#RGB` (3-digit shorthand) | `"'#09F'"` | ✅ Parsed (expands to `#0099FF`), incl. gradient stops. |
| `#RRGGBBAA` (8-digit + alpha) | `"'#118DFF80'"` | ⚠️ **Not** accepted in **gradient stops** (the client color parser reads only `#RGB`/`#RRGGBB`, so an 8-digit stop breaks interpolation — `validate` flags it as `PBIR_FILLRULE_STOP_COLOR_INVALID`). May render for **solid** rule/field-value colors via the DAX color path — verify in Desktop and prefer controlling opacity with the property's transparency setting. |

Rules:
- Always include the leading `#` **and** the single-quote wrapper inside the
  double quotes: `"'#RRGGBB'"`.
- Hex digits are case-insensitive.
- For **field-driven** color (Type 6), the source column/measure must itself
  return one of the accepted forms.

❌ **Invalid hex results** (render black / default / drop the format):
- `"'118DFF'"` — missing `#`.
- `"'#12'"`, `"'#1234'"`, `"'#12345'"`, `"'#1234567'"` — wrong length.
- `"'#GGGGGG'"` / `"'#xxxxxx'"` — non-hex characters.
- `"118DFF"` — missing the single-quote wrapper.
