# Formatting Patterns

> **Read first:** `formatting-overview.md` (see `formatting-overview.md`) — cascade
> model and encoding rules. Related: `authoring-workflows.md` (see `authoring-workflows.md`) for full
> visual JSON examples, `theming.md` (see `theming.md`) for theme.json, and
> `conditional-formatting.md` (see `conditional-formatting.md`) for data-driven
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
- [Color Strategy & Patterns](#color-strategy--patterns) → `color-strategy.md` (see `color-strategy.md`)
- [Conditional Formatting](#conditional-formatting) → `conditional-formatting.md` (see `conditional-formatting.md`)
- Shape Visual Formatting (continued in `formatting-part-02.md`) → `shape.md` (see `shape.md`)
- Line & Marker Formatting (continued in `formatting-part-02.md`) → `cartesian.md` (see `cartesian.md`)
- Row Banding (Table & Matrix) (continued in `formatting-part-02.md`) → `table.md` (see `table.md`)
- Page-Level Formatting (continued in `formatting-part-02.md`) → `page-formatting.md` (see `page-formatting.md`)
- Background Images — Routing (continued in `formatting-part-02.md`) → `image.md` (see `image.md`), `page-formatting.md` (see `page-formatting.md`)
- References (continued in `formatting-part-02.md`)

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
      "show": { "expr": { "Literal": { "Value": "true" } } }
    }
  },
  {
    "properties": {
      "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00FF00'" } } } } },
      "transparency": { "expr": { "Literal": { "Value": "0D" } } }
    },
    "selector": { "id": "default" }
  }
]
```

> **Entry 1 (no selector):** Toggle properties (`show`) — applies to ALL states.
> **Entry 2 (with state selector):** Styling properties — applies to that state.
> Do NOT combine `show` with styling in one entry — formatting silently fails.

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

### Per-Visual Requirements

These `visualContainerObjects` properties must be set **per-visual** —
they do not cascade reliably from theme `visualStyles`:

- `border` (including `radius`) — for rounded corners
- `background` (show, color, transparency)
- `padding` — must accompany any other VCO override
- Card-specific: `accentBar`, `outline`, `layout` (require
  `selector: { id: "default" }`)

**Rule**: when setting any `visualContainerObjects` per-visual, always set
`background`, `border` (with `radius`), `padding`, and `visualHeader` together.
Partial VCO overrides cause PBI to reset omitted properties to system defaults.

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
`color-strategy.md` (see `color-strategy.md`).

## Conditional Formatting

For data-driven formatting (FillRule color gradients, rules-based formatting,
icon sets, data bars, web URLs, field values) — including the `expr` wrapper
rule inside FillRule color stops and the `dataViewWildcard` selector pattern
for table/matrix conditional formatting — see
`conditional-formatting.md` (see `conditional-formatting.md`).
