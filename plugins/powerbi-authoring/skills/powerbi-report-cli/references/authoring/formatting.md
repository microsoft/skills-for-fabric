# Formatting Patterns

> **Read first:** [`formatting-overview.md`](formatting-overview.md) — cascade
> model and encoding rules. Related: [`authoring-workflows.md`](authoring-workflows.md) for full
> visual JSON examples, [`theming.md`](theming.md) for theme.json, and
> [`conditional-formatting.md`](conditional-formatting.md) for data-driven
> formatting.

> **⚠️ The CLI is the source of truth for property names and enum values.**
> Patterns here show structure, but property names vary between visual types.
> Confirm before applying formatting:
>
> | Use case | Command |
> |---|---|
> | Inspect properties + enums of one object | `powerbi-report-author formatting describe-object <type> <object>` |
> | Look up one property | `powerbi-report-author formatting describe-property <type> <object> <property>` |
> | Search by name across all objects of a visual | `powerbi-report-author formatting search <type> <regex>` |
> | Flattened (object, property) list across `objects` + VCOs | `powerbi-report-author formatting effective-properties <type>` |

> Examples use illustrative `<table>.<measure>` identifiers — substitute your own.

## Contents

- [Formatting JSON Structure](#formatting-json-structure)
- [Literal Values](#literal-values)
- [Solid Color Fill](#solid-color-fill)
- [Theme Data Color Reference](#theme-data-color-reference)
- [Selectors](#selectors-targeting-specific-data)
- [Visual Container Objects (VCO)](#visual-container-objects-vco)
- [Color Strategy & Patterns](#color-strategy--patterns) → [`color-strategy.md`](color-strategy.md)
- [Conditional Formatting](#conditional-formatting) → [`conditional-formatting.md`](conditional-formatting.md)
- [Shape Visual Formatting](#shape-visual-formatting) → [`shape.md`](shape.md)
- [Line & Marker Formatting](#line--marker-formatting-linestyles--markers) → [`cartesian.md`](cartesian.md)
- [Row Banding (Table & Matrix)](#row-banding-table--matrix) → [`table.md`](table.md)
- [Page-Level Formatting](#page-level-formatting-pagejson-objects) → [`page-formatting.md`](page-formatting.md)
- [Background Images — Routing](#background-images--routing) → [`image.md`](image.md), [`page-formatting.md`](page-formatting.md)
- [References](#references)

## Formatting JSON Structure

All formatting properties in `visual.json` live inside the `objects` or
`visualContainerObjects` keys within the `visual` object. Every object is an
**array of property sets** — even when there is only one entry.

```text
visual.json
└── visual
    ├── objects              ← chart-specific formatting
    │   └── <objectName>     ← array of { properties, selector? }
    │       └── [{ "properties": { "prop1": <expr>, ... }, "selector": ... }]
    └── visualContainerObjects  ← container formatting (title, background, …)
        └── <objectName>
            └── [{ "properties": { "prop1": <expr>, ... } }]
```

**Rules:**
1. Each object name (e.g. `dataPoint`, `categoryAxis`, `title`) holds an
   **array** — `[{ "properties": { ... } }]`, not a bare properties object.
2. Each array entry is `{ "properties": { <propertyName>: <value-expression> } }`.
3. An optional `"selector"` may appear alongside `"properties"` — see the
   [Selectors](#selectors-targeting-specific-data) section below for which
   objects require or accept selectors and what shape to use.
4. `objects` contains chart-specific formatting (axes, data colors, legend, labels).
5. `visualContainerObjects` contains container formatting (title, background,
   border, shadow). See the VCO section below.
6. Discover valid object and property names with the CLI:
   `powerbi-report-author formatting list-objects <visualType>`
   `powerbi-report-author formatting describe-object <visualType> <objectName>`

## Literal Values

Most formatting properties use a `Literal` expression wrapper:
```json
{
  "expr": {
    "Literal": { "Value": "<typedValue>" }
  }
}
```

**Value type suffixes:**
| Suffix | Type | Example |
|--------|------|---------|
| `D` | Double/decimal | `"11D"`, `"0.8D"`, `"80D"` |
| `L` | Long/integer | `"1L"`, `"1000000L"` |
| (none) | Boolean | `"true"`, `"false"` |
| `'...'` | String (single-quoted) | `"'Left'"`, `"'Center'"`, `"'Top'"` |
| `'#...'` | Color hex (single-quoted) | `"'#118DFF'"`, `"'#f6c7b9'"` |

## Solid Color Fill
```json
{
  "solid": {
    "color": {
      "expr": {
        "Literal": { "Value": "'#118DFF'" }
      }
    }
  }
}
```

> **Color name → hex mapping:** When a user specifies a color by name (e.g.
> "green", "red", "blue") without an explicit hex code, use the **standard
> CSS/HTML named-color hex value**. Common mappings:
>
> | Name | Hex | | Name | Hex |
> |------|-----|-|------|-----|
> | red | `#FF0000` | | green | `#008000` |
> | blue | `#0000FF` | | yellow | `#FFFF00` |
> | orange | `#FFA500` | | purple | `#800080` |
> | black | `#000000` | | white | `#FFFFFF` |
> | gray / grey | `#808080` | | lime | `#00FF00` |
>
> Note: CSS "green" is `#008000`, **not** `#00FF00` (which is "lime").

## Theme Data Color Reference
References a color from the active theme palette:
```json
{
  "solid": {
    "color": {
      "expr": {
        "ThemeDataColor": {
          "ColorId": 4,
          "Percent": 0.6
        }
      }
    }
  }
}
```
- `ColorId`: 0-based index into the theme's `dataColors` array.
- `Percent`: Lightness adjustment. 0 = base, positive = lighter, negative = darker.

## Selectors (Targeting Specific Data)

Selectors control which data a formatting entry applies to. Each object array
entry can have an optional `selector` that targets specific data points.

### Selector Types and Precedence

Resolution order (highest to lowest priority):

| Priority | Type | Syntax | Use Case |
|----------|------|--------|----------|
| 1 | **data** (scope identity) | `"data": [{"scopeId": {Comparison...}}]` | Color a specific category value (charts only) |
| 2 | **data** (wildcard) | `"data": [{"dataViewWildcard": {"matchingOption": N}}]` | All instances, totals, or both |
| 3 | **metadata** | `"metadata": "Table.Field"` | Target a specific measure/column |
| 4 | **id** | `"id": "default"` | User-defined instance (cards, filter cards) |
| 5 | **none** (static) | *(no selector)* | Base/fallback for objects that use selectors; the only mode for visual-wide objects (axes, legend, VCOs) |

Within each priority row, **first match in array order wins**.

### No Selector (Static / Base)

```json
{ "properties": { "show": true } }
```

Base formatting for all data points. Any other selector overrides this.

### Metadata Selector

```json
{
  "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FF0000'" } } } } } },
  "selector": { "metadata": "financials.Revenue" }
}
```

Targets a specific field by its queryName (`Table.Field` or `Sum(Table.Field)`).
Common for per-series colors in `dataPoint.fill`.

### DataViewWildcard Selector

```json
{
  "properties": { "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333'" } } } } } },
  "selector": {
    "data": [{ "dataViewWildcard": { "matchingOption": 1 } }]
  }
}
```

**`matchingOption` values:**

| Value | Constant | Meaning |
|-------|----------|---------|
| `0` | InstancesAndTotals | Both data rows and subtotal/total rows |
| `1` | InstancesOnly | Regular data instances only (not subtotals) |
| `2` | TotalsOnly | Only subtotal and grand total rows |

**`highlightMatching`** (optional, on the selector itself):

| Value | Meaning |
|-------|---------|
| `0` | ValuesOnly — apply to non-highlighted only (default) |
| `1` | ValuesAndHighlight — apply to both |
| `2` | HighlightsOrValues — highlighted if exists, else non-highlighted |

### Scope Identity Selector

Targets a specific data point value (e.g., "Electronics" in Category).
Works on chart visuals only (bar, column, pie, donut, line, area, scatter,
treemap, funnel).

```json
{
  "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E66C37'" } } } } } },
  "selector": {
    "data": [{
      "scopeId": {
        "Comparison": {
          "ComparisonKind": 0,
          "Left": { "Column": { "Expression": { "SourceRef": { "Entity": "Product" } }, "Property": "Category" } },
          "Right": { "Literal": { "Value": "'Electronics'" } }
        }
      }
    }]
  }
}
```

> ⚠️ **Only `ComparisonKind: 0` (Equal) is honored.** Other comparison kinds
> (1–4) pass schema validation but are silently ignored at render. Values ≥ 5
> cause schema validation errors. For compound conditions, use rules-based
> `Conditional.Cases[]` (see `conditional-formatting.md` Type 2).

Highest priority among data selectors. Used for per-category color assignment.

### ID Selector (Instance Selector)

```json
{
  "properties": { "fontSize": { "expr": { "Literal": { "Value": "28D" } } } },
  "selector": { "id": "default" }
}
```

User-defined instance identifier. Several visual types require id selectors for
their formatting objects to take effect. Run
`powerbi-report-author formatting list-objects <type>` to see which objects
need selectors — they're annotated inline.

**Common id values by visual type:**

| Visual Type | ID Values | Objects Affected |
|---|---|---|
| `cardVisual` | `"default"` | outline, accentBar, fillCustom, shape, label, value, layout, spacing, padding, divider, image, shadowCustom, glowCustom, referenceLabelTitle/Value/Detail |
| `pageNavigator` / `bookmarkNavigator` / `actionButton` | `"default"`, `"hover"`, `"selected"`, `"disabled"` | fill, outline, text, icon, shadow, glow, accentBar, image, value, label, background, padding |
| `advancedSlicerVisual` | `"default"`, `"hover"`, `"press"`, `"selected"`, `"mixed"` | fill, outline, text, accentBar, background, label, padding, spacing, selectionIcon, expansionIcon |
| `pivotTable` | `"Row"`, `"Column"` | subTotals |
| `filterCard` (page-level) | `"Available"`, `"Applied"` (PascalCase required) | filterCard |

> The CLI provides this data automatically:
> `powerbi-report-author formatting describe-object <type> <object>` shows
> `_selectorHint` when an object requires id selectors.
> `powerbi-report-author formatting list-objects <type>` annotates objects that
> need selectors.

#### Dual-Entry Pattern

Objects with `id` selectors always require at least the entry with the `id` selector.
Some visual types (`actionButton`, `pageNavigator`, `bookmarkNavigator`) require
**two** array entries — one static (no selector) and one with the `id` selector.
For `cardVisual` and `shape` objects, the entry with the `id` selector alone is
sufficient (the static entry is redundant but harmless).

**Example: actionButton fill (dual entry required)**

```json
"fill": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00FF00'" } } } } },
      "transparency": { "expr": { "Literal": { "Value": "0D" } } }
    }
  },
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00FF00'" } } } } },
      "transparency": { "expr": { "Literal": { "Value": "0D" } } }
    },
    "selector": { "id": "default" }
  }
]
```

**Example: cardVisual accentBar (single entry sufficient)**

```json
"accentBar": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FF0000'" } } } } },
      "transparency": { "expr": { "Literal": { "Value": "0L" } } }
    },
    "selector": { "id": "default" }
  }
]
```

> ⚠️ **Without the `id` selector, property overrides are silently dropped.**
> The object still renders but with its default theme appearance instead of
> the JSON-specified values. No error is produced. If formatting has no effect,
> check `powerbi-report-author formatting describe-object <type> <object>` for
> a `_selectorHint` on that object.

### Which Objects Support Selectors?

| Object | Supports | Selector Types |
|--------|----------|---------------|
| `dataPoint` | ✅ | `metadata`, `data` (wildcard + scope identity) |
| `labels` | ✅ | `data`, `metadata` |
| `columnFormatting` | ✅ | `metadata` |
| `values` | ✅ | `metadata`, `data` |
| `filterCard` | ✅ | `id` (`"Applied"`, `"Available"`) |
| cardVisual objects (16) | ✅ | `id` (`"default"`) — see table above |
| navigator/button objects (12) | ✅ | `id` (4 states) — see table above |
| slicer objects | ✅ | `id` (5 states) — see table above |
| shape objects | ✅ | `id` (`"default"`) — single entry sufficient |
| `legend` | ❌ | **none** — omit `selector` |
| `categoryAxis` / `valueAxis` | ❌ | **none** — omit `selector` |
| `title`, `background`, `border` (VCO) | ❌ | **none** — omit `selector` |

**Rule**: Data-bound objects support `metadata`/`data` selectors. Tile-based
visuals (cardVisual, shape, navigators, slicers) use `id` selectors for
instance targeting. Visual-wide settings (axes, legends, VCOs) do not support
selectors.

## Visual Container Objects (VCO)

Format the visual container itself (not chart data). Located **inside `visual`**
as a sibling of `objects` — NOT as a top-level property of the visual.json root.

```text
visual.json root
├── name, position
└── visual
    ├── visualType, query
    ├── objects              ← chart-specific formatting
    └── visualContainerObjects  ← container formatting (title, background, etc.)
```

### Auto-Generated Subtitles

When you set a VCO `title` on a chart, PBI also auto-generates a
**subtitle** from the bound field names (e.g., "Sales and Profit by Date").
Set the subtitle state in the same pass as the title. If the subtitle repeats
the title or exposes raw field names, it creates visual noise. Keep or author a
subtitle when it adds context the title cannot carry cleanly (time window,
active filter, units, comparison baseline, caveat); hide it when it is
redundant.

```json
"visualContainerObjects": {
  "title": [{ "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "text": { "expr": { "Literal": { "Value": "'Revenue by Region'" } } }
  }}],
  "subTitle": [{ "properties": {
    "show": { "expr": { "Literal": { "Value": "false" } } }
  }}]
}
```

> ⚠️ If you see duplicate titles in screenshots (your custom title + an
> auto-generated field-name subtitle below it), set `subTitle.show` to false or
> replace it with a hand-authored contextual subtitle.

### Page Objects vs Visual Container Objects

Page objects (`page.json → objects`) and VCOs (`visual.json → visualContainerObjects`)
share some names but have **different valid properties**:

| Object | Page (`page.json`) | VCO (`visual.json`) |
|--------|--------------------|---------------------|
| `background` | `color`, `image`, `transparency` — **NO `show`** | `show`, `color`, `transparency` |
| `outspace` | `color`, `image`, `transparency` | *(not a VCO)* |
| `outspacePane` | 12 filter pane properties | *(not a VCO)* |
| `filterCard` | 8 properties per Applied/Available state | *(not a VCO)* |
| `title` | *(not a page object)* | `show`, `text`, `fontColor`, `fontSize`, etc. |
| `border` | *(not a page object)* | `show`, `color`, `radius`, `width` |

Do not mix page and VCO property lists — use `powerbi-report-author validate`
to catch mismatches (`PBIR_FORMATTING_OBJECT_UNKNOWN`,
`PBIR_FORMATTING_PROP_UNKNOWN`).

### VCO Property Reference

There are **15 VCO keys**, shared across all visual types:
title, subTitle, divider, spacing, background, padding, lockAspect, general,
border, dropShadow, visualLink, visualTooltip, stylePreset, visualHeader,
visualHeaderTooltip.

Discover them with `powerbi-report-author formatting list-vcos`. For property
details, see the CLI table in the preamble.

## Color Strategy & Patterns

For color overrides on chart data points — when to use theme `dataColors`,
`dataPoint.defaultColor`, and per-series `dataPoint.fill` with `metadata`
selectors, plus the cross-visual measure-color consistency pattern — see
[`color-strategy.md`](color-strategy.md).

## Conditional Formatting

For data-driven formatting (FillRule color gradients, rules-based formatting,
icon sets, data bars, web URLs, field values) — including the `expr` wrapper
rule inside FillRule color stops and the `dataViewWildcard` selector pattern
for table/matrix conditional formatting — see
[`conditional-formatting.md`](conditional-formatting.md).

## Shape Visual Formatting

For shape-object discovery, available shapes, and formatting, see
[`shape.md` § Available Shapes and Formatting](shape.md#available-shapes-and-formatting).

## Line & Marker Formatting (lineStyles / markers)

For line stroke properties (width, style, dash cap, line join, interpolation),
marker properties (shape, size, border, rotation), and the per-series metadata
selector pattern for line/area/scatter charts, see
[`cartesian.md` § lineStyles](cartesian.md#linestyles--line-specific) and
[`cartesian.md` § markers](cartesian.md#markers--marker-styling).

## Row Banding (Table & Matrix)

For row banding (`backColorPrimary` / `backColorSecondary`), the full
table/matrix region map (`values`, `columnHeaders`, `rowHeaders`, `total`,
`subTotals`), the **critical style preset rule** (`stylePreset` must be set to
`'None'` for custom row colors to render), and the `backColor` vs
`backColorPrimary` distinction, see
[`table.md` § Row Banding](table.md#row-banding-table--matrix).

## Page-Level Formatting (`page.json` objects)

For canvas background, wallpaper (`outspace`), and page-level background
images, see [`page-formatting.md`](page-formatting.md). For filter pane
(`outspacePane`) and filter card states (Applied / Available), see
[`filter-pane.md`](filter-pane.md).

## Background Images — Routing

When the user requests a "background image," route based on the target:

| User says | Target | Reference |
|-----------|--------|-----------|
| "background image" while creating/modifying a chart visual | `visual.objects.plotArea.image` | [`image.md` § Plot Area Background Image](image.md#plot-area-background-image-plotareaimage) |
| "page background image" / "canvas background" | `page.json → objects.background.image` | [`page-formatting.md` § Background Images](page-formatting.md#background-images) |
| "background image" with no visual context | Ask the user to clarify — page canvas or visual plot area | — |

**⚠️ Both visual plot areas and page backgrounds use the nested `image.image` structure** (`image.image.name`, `image.image.url`, `image.image.scaling`). A flat `image.name/url/scaling` will silently fail to render.

For the `image` object on image visuals themselves (border, background,
corner-radius routing between `objects.image` and VCOs), see
[`image.md` § Image Formatting](image.md#image-formatting-objectsimage).

## References

- [`formatting-overview.md`](formatting-overview.md) — cascade resolution order (visual → VCO → page → custom theme → base theme → defaults), encoding rules, and the Theme JSON vs PBIR encoding comparison table.
- [`theming.md`](theming.md) — `theme.json` authoring: dataColors, textClasses, visualStyles, dark-mode checklist.
- [`conditional-formatting.md`](conditional-formatting.md) — gradients, rules, field values, and the six conditional formatting types.
- [`table.md`](table.md), [`shape.md`](shape.md), [`cartesian.md`](cartesian.md), [`image.md`](image.md), [`card.md`](card.md) — visual-type-specific formatting details.

