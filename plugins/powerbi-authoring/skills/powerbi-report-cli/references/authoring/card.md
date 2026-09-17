# Card Visual Authoring Guide

Cards (`cardVisual`) display one or more headline metrics. `card` and `multiRowCard`
(both legacy) are deprecated — always use `cardVisual`.

- [Single-Value Template](#single-value-template)
- [Multi-Value Template](#multi-value-template)
- [Key Formatting Rules](#key-formatting-rules)
- [Multi-Value Formatting](#multi-value-formatting)
- [When to Consolidate vs. Keep Separate](#when-to-consolidate-vs-keep-separate)
- [Theme Approach](#theme-approach)
- [Discovering Properties](#discovering-properties)
- [References](#references)

---

## Single-Value Template

> ⚠️ **Role name is `Data`, not `Fields`.** The only valid `queryState` key for
> `cardVisual` is `"Data"`. Using `"Fields"` (the legacy `card` role name) causes
> the visual to render empty — PBI Desktop cannot resolve the binding. The
> validator catches this as `Unknown role "Fields"` and `Required role "Data" missing`.

The `Data` role accepts one or more measures. For a single headline KPI:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 24, "y": 56, "z": 1000, "height": 80, "width": 296, "tabOrder": 1000 },
  "visual": {
    "visualType": "cardVisual",
    "query": {
      "queryState": {
        "Data": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Measure>" } },
            "queryRef": "<Table>.<Measure>",
            "nativeQueryRef": "<Measure>"
          }]
        }
      }
    }
  }
}
```

---

## Multi-Value Template

> **Default for multiple related KPIs:** When the user asks for 2–5 related
> KPIs on the same row (e.g. "Sales, Profit, Units, Gross Margin"), create
> **one** multi-value `cardVisual` with all measures as projections in `Data`.
> Do **not** create separate single-value cards unless the user explicitly needs
> per-card styling differences (see [When to Consolidate vs. Keep Separate](#when-to-consolidate-vs-keep-separate)).

Add multiple projections to the `Data` role. PBI renders them as a horizontal
row of callouts inside one visual. Use this instead of placing multiple
single-value cards side by side when they share the same container styling.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 24, "y": 56, "z": 1000, "height": 120, "width": 900, "tabOrder": 1000 },
  "visual": {
    "visualType": "cardVisual",
    "query": {
      "queryState": {
        "Data": {
          "projections": [
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Measure1>" } },
              "queryRef": "<Table>.<Measure1>",
              "nativeQueryRef": "<Measure1>"
            },
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Measure2>" } },
              "queryRef": "<Table>.<Measure2>",
              "nativeQueryRef": "<Measure2>"
            },
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "<Table>" } }, "Property": "<Measure3>" } },
              "queryRef": "<Table>.<Measure3>",
              "nativeQueryRef": "<Measure3>"
            }
          ]
        }
      }
    }
  }
}
```

> **Sizing tip:** Multi-value cards need more width. Allow ~250–300 px per
> callout. For 3 measures a width of 900 px works well. Height of 100–120 px
> accommodates value + label without clipping.

---

## Key Formatting Rules

### Instance selectors required

Most `cardVisual` formatting objects require `selector: { "id": "default" }`.
Without it, properties silently fail to apply.

Objects that need the `id` selector: `value`, `label`, `accentBar`, `outline`,
`padding`, `spacing`, `divider`, `fillCustom`, `shadowCustom`, `glowCustom`,
`image`, `layout`, `referenceLabelTitle`, `referenceLabelValue`,
`referenceLabelDetail`.

Objects that do **NOT** need a selector: `cardCalloutArea`, `referenceLabel`,
`referenceLabelLayout`.

### Remove the internal border

The `outline` object controls the internal rectangular border inside the card.
To remove it (recommended):

```json
"outline": [{
  "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } },
  "selector": { "id": "default" }
}]
```

> ⚠️ This does **NOT** cascade from theme `visualStyles` — must be set
> per-visual. The outer container border (VCO `border`) is separate and
> does cascade from theme.

### Override the category label text

By default the card shows the raw measure name from the model. Override
with `label.text`:

```json
"label": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "text": { "expr": { "Literal": { "Value": "'Total Revenue'" } } }
  },
  "selector": { "id": "default" }
}]
```

### Font sizing and clipping — MANDATORY pre-check

> **BLOCKING REQUIREMENT.** Before creating or resizing any cardVisual, compute
> `required_height` and `required_width` using the formulas below. If either
> exceeds the card's dimensions, adjust or reduce font sizes.

#### Step 1: Resolve effective values from cascade

Before computing, inspect these sources in priority order (first match wins):

1. **Visual file** (`visual.json` → `objects` and `visualContainerObjects`)
2. **Custom theme** → `visualStyles.cardVisual.*` (type-specific)
3. **Custom theme** → `visualStyles.*.*` (global wildcard)
4. **Custom theme** → `textClasses.callout.fontSize` (for value default)
5. **Base theme** → `visualStyles.cardVisual.*` (content padding, spacing)

Check the **base theme** (`StaticResources/SharedResources/BaseThemes/*.json`)
for the content area default properties:
- `visualStyles.cardVisual.*.padding.paddingUniform` → content inner padding
- `visualStyles.cardVisual.*.layout.paddingUniform` → content outer padding
- `visualStyles.cardVisual.*.spacing.verticalSpacing` → gap between value and label

These follow the same cascade as other properties (visual `objects` →
custom theme `cardVisual.*` → custom theme `*.*` → base theme).

Check the **custom theme** JSON for:
- `textClasses.callout.fontSize` → this is the default `value_fontSize`
- `visualStyles.*.*.padding.top/bottom` → VCO padding override
- `visualStyles.*.*.border.show` + `.width` → border contribution
- `visualStyles.cardVisual.*.spacing.verticalSpacing` → verticalSpacing override

Check the **visual** JSON for any per-card overrides on:
- `objects.value.fontSize`, `objects.label.fontSize`
- `visualContainerObjects.padding.top/bottom`
- `visualContainerObjects.border.show/width`
- `visualContainerObjects.title.show/fontSize`
- `visualContainerObjects.spacing.spaceBelowTitleArea`

Only after resolving all effective values, proceed to Step 2.

#### Step 2: Card visual anatomy (top to bottom)

```
┌──────────────────────────────────────────────────────────┐
│ VCO border (top)                                         │ border_width
├──────────────────────────────────────────────────────────┤
│ VCO padding (top)                                        │ padding_top
├──────────────────────────────────────────────────────────┤
│ Title text (if shown)                                    │ render(title_fontSize)
│ Space below title                                        │ spaceBelowTitleArea
├──────────────────────────────────────────────────────────┤
│ Content padding (top)                                    │ content_padding_top
│ Value text: "283K"                                       │ render(value_fontSize)
│ verticalSpacing                                          │ spacing.verticalSpacing
│ Label text: "Sum of Profit"                              │ render(label_fontSize)
│ Content padding (bottom)                                 │ content_padding_bottom
├──────────────────────────────────────────────────────────┤
│ VCO padding (bottom)                                     │ padding_bottom
├──────────────────────────────────────────────────────────┤
│ VCO border (bottom)                                      │ border_width
└──────────────────────────────────────────────────────────┘
```

Key facts:
- **Label ALWAYS renders** even with `label.show=false`. Allocate for ≥12pt.
- **Content padding** comes from two objects, each with uniform/individual modes:
  - `objects.padding`: if `paddingIndividual=true` use per-side values, else `paddingUniform`
  - `objects.layout`: if `paddingIndividual=true` use `topOuterMargin`/`bottomOuterMargin`, else `paddingUniform`
- **VCO padding** (`visualContainerObjects.padding`): `top`/`bottom`/`left`/`right`
- **verticalSpacing**: from `objects.spacing` or `visualContainerObjects.spacing`
- **calloutSize** (`objects.layout.calloutSize`): percentage that may scale the
  content area. Runtime default is unverified.

#### Step 3: Compute height

```
render(fs) = ceil(fs × 1.5)

# Resolve content padding from cascade:
# - padding object: paddingUniform (or paddingTop/paddingBottom if paddingIndividual=true)
# - layout object: paddingUniform (or topOuterMargin/bottomOuterMargin if paddingIndividual=true)
content_padding_top    = padding_obj_top + layout_obj_top
content_padding_bottom = padding_obj_bottom + layout_obj_bottom

required_height = border_width × 2
                + padding_top + padding_bottom
                + (render(title_fontSize) + spaceBelowTitleArea) × title_visible
                + content_padding_top + content_padding_bottom
                + render(value_fontSize)
                + verticalSpacing
                + render(effective_label_fontSize)
                + accentBar_width × accentBar_top_or_bottom

effective_label_fontSize = max(explicit_label_fontSize, 12)

Constraint: required_height ≤ position.height
```

#### Step 4: Width considerations

Width overflow shows ellipsis ("...") rather than clipping — less severe than
height clipping. Properties that consume horizontal space:

- VCO padding left/right (`visualContainerObjects.padding`)
- Content padding left/right (from `objects.padding` and `objects.layout`, same uniform/individual logic as vertical)
- Border width (left + right)
- Accent bar width (if positioned left or right)

If values are truncated with ellipsis, increase `position.width` or reduce
`value_fontSize`.

Use **5 chars** when display format is unknown. Width overflow shows ellipsis.

#### Default values (cascade resolution)

Priority: visual `objects` → custom theme `cardVisual.*` → custom theme `*.*` → base theme.

| Variable | Source | Notes |
|----------|--------|-------|
| `value_fontSize` | `textClasses.callout.fontSize` | Override via `objects.value.fontSize` (id selector) |
| `label_fontSize` | `textClasses.label.fontSize` | Override via `objects.label.fontSize` (id selector) |
| `padding_top/bottom/left/right` | `visualContainerObjects.padding` | VCO padding around the whole visual |
| `padding` object | `objects.padding` (id selector) | `paddingUniform` or individual `paddingTop/Bottom/Left/Right` |
| `layout` object | `objects.layout` (id selector) | `paddingUniform` or individual `topOuterMargin/bottomOuterMargin/leftOuterMargin/rightOuterMargin` |
| `verticalSpacing` | `objects.spacing` (id selector) | Gap between value and label |
| `spaceBelowTitleArea` | `visualContainerObjects.spacing` | Gap below title area |
| `calloutSize` | `objects.layout.calloutSize` | Percentage; runtime default unverified |
| `title_fontSize` | `visualContainerObjects.title` | Title font size when title is shown |
| `border_width` | `visualContainerObjects.border` | Only contributes when `border.show=true` |
| `accentBar_width` | `objects.accentBar` (id selector) | Only contributes when `accentBar.show=true` |

> Always read the report's base theme file
> (`StaticResources/SharedResources/BaseThemes/*.json`) for authoritative
> default values. Do not assume hardcoded constants.

#### Worked examples

These examples assume base theme values: `padding.paddingUniform=12`,
`layout.paddingUniform=12`, `verticalSpacing=2`, VCO padding top/bottom=8.
Always verify these values from the actual base theme file.

**Example 1 — theme callout=36, card h=100 w=180 (FAILS):**
```
content_padding = (12+12) × 2 = 48
required_height = 0 + 8+8 + 0 + 48 + ceil(36×1.5) + 2 + ceil(12×1.5) + 0
               = 16 + 48 + 54 + 2 + 18 = 138
→ 138 > 100 → CLIPS!

Fix: set value.fontSize=20 → 16+48+30+2+18 = 114, use h=120
```

**Example 2 — with title and accent bar:**
```
title_area = render(title_fontSize) + spaceBelowTitleArea
required_height = border + VCO_padding + title_area + content_padding
               + render(value) + verticalSpacing + render(label) + accentBar
```

**Example 3 — custom VCO padding=4, border=2:**
```
required_height = 2×2 + 4+4 + 0 + 48 + ceil(32×1.5) + 2 + ceil(14×1.5) + 0
               = 4 + 8 + 48 + 48 + 2 + 21 = 131
→ use h ≥ 131
```

#### Quick-reference safe dimensions

Example assuming `padding.paddingUniform=12`, `layout.paddingUniform=12`,
VCO padding=8, `verticalSpacing=2`, label=12pt, no title, no border:

| value.fontSize | Min height |
|----------------|------------|
| 20 | 114 |
| 24 | 120 |
| 28 | 126 |
| 32 | 132 |
| 36 | 138 |
| 40 | 144 |
| 45 | 152 |

With title: add `render(title_fontSize) + spaceBelowTitleArea` to height.
With custom VCO padding=4: subtract **8px** from height.

### Accent bar

Adds a colored edge bar. Match color to the card's accent from the palette:

```json
"accentBar": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "position": { "expr": { "Literal": { "Value": "'Left'" } } },
    "width": { "expr": { "Literal": { "Value": "4D" } } },
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0072B2'" } } } } }
  },
  "selector": { "id": "default" }
}]
```

> **Tip:** When using an accent bar, set VCO `padding` to all zeros so the
> bar spans the full card height. Set `layout` outer margins to all zeros
> so the accent bar is flush against the card border. Set `padding`
> `topMargin: 0L`, `bottomMargin: 0L` (content sits tight against top),
> `leftMargin: 12L` (breathing room from the bar), `rightMargin: 8L`.

---

## Multi-Value Formatting

These formatting objects only take effect when the card has **2 or more**
measures in the `Data` role. On single-value cards they validate but have
no visible effect.

### cardCalloutArea

Controls per-callout tile styling — padding, corner radius, background fill.
Does **not** need an `id` selector.

```json
"cardCalloutArea": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "paddingUniform": { "expr": { "Literal": { "Value": "8L" } } },
    "rectangleRoundedCurve": { "expr": { "Literal": { "Value": "6L" } } },
    "backgroundFillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#F5F5F5'" } } } } },
    "backgroundTransparency": { "expr": { "Literal": { "Value": "0D" } } }
  }
}]
```

### layout (gridlines between callouts)

Draws vertical separator lines between each callout tile. Use the `layout`
object — `cardVisual` does have a `grid` object that validates, but it does
**not** render the inter-callout separators in PBI Desktop. The working path
is `layout` with `style: "Table"` plus `customizeLines: true`, which unlocks
the `gridline*` properties below.

```json
"layout": [{
  "properties": {
    "style": { "expr": { "Literal": { "Value": "'Table'" } } },
    "customizeLines": { "expr": { "Literal": { "Value": "true" } } },
    "gridlineWidth": { "expr": { "Literal": { "Value": "1D" } } },
    "gridlineColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E0E0E0'" } } } } },
    "gridlineTransparency": { "expr": { "Literal": { "Value": "0D" } } },
    "gridlineStyle": { "expr": { "Literal": { "Value": "'solid'" } } }
  },
  "selector": { "id": "default" }
}]
```

### divider

Horizontal divider line between value and label within each callout. Property
names are prefixed with `divider*` (the unprefixed `width/color/style/...`
belong to the visual-container `divider` object, not `cardVisual`'s own).

```json
"divider": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "dividerWidth": { "expr": { "Literal": { "Value": "1D" } } },
    "dividerColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E0E0E0'" } } } } },
    "dividerTransparency": { "expr": { "Literal": { "Value": "0D" } } },
    "dividerLineStyle": { "expr": { "Literal": { "Value": "'solid'" } } },
    "dividerIgnorePadding": { "expr": { "Literal": { "Value": "true" } } }
  },
  "selector": { "id": "default" }
}]
```

> **Note:** `value` and `label` formatting (font, size, color, alignment)
> applies uniformly to all callouts — you cannot style individual callouts
> differently within the same multi-value card.

---

## When to Consolidate vs. Keep Separate

**Default: always use one multi-value `cardVisual`** for multiple KPIs. Put all
measures as projections in the `Data` role — this is exactly what `cardVisual`
is designed for. Do **not** create separate single-value cards per metric unless
the user explicitly needs per-card styling differences (see below).

**Only keep separate single-value cards** when the user specifically requires:
- Per-card accent bar colors (each card gets its own accent color)
- Different background colors or conditional formatting per metric
- Different font sizes per metric (e.g., one hero card larger than the rest)
- Individual card click/drill-through behavior

---

## Theme Approach

These `cardVisual` defaults can be applied report-wide via theme
`visualStyles` (plain JSON, not PBIR `expr` wrappers):

```json
"cardVisual": {
  "*": {
    "value": [{ "bold": true, "$id": "default" }],
    "label": [{ "show": true, "$id": "default" }],
    "cardCalloutArea": [{ "paddingUniform": 0 }],
    "border": [{ "show": true, "color": { "solid": { "color": "#E8E8E8" } }, "radius": 8 }],
    "title": [{ "show": false }],
    "spacing": [{ "verticalSpacing": -6 }],
    "padding": [{ "top": 0, "bottom": 0, "left": 0, "right": 0 }]
  }
}
```

> ⚠️ `outline`, `accentBar`, `layout`, visual-level `padding` (with `leftMargin` etc.),
> `value.fontColor`, and `label.text` do **NOT** cascade from theme — they
> must be set per-visual.
>
> **VCO mixing caveat**: If you set ANY VCO property per-visual (background,
> border, visualHeader), also set `padding` per-visual in the same
> `visualContainerObjects` block. Otherwise PBI may reset padding to its
> default (~5px) instead of inheriting from the theme.

**Layout outer margins** — To eliminate the gap between the card border and
content (so the accent bar sits flush), set `layout` with `id: "default"`:

```json
"layout": [{
  "properties": {
    "topOuterMargin": { "expr": { "Literal": { "Value": "0L" } } },
    "bottomOuterMargin": { "expr": { "Literal": { "Value": "0L" } } },
    "leftOuterMargin": { "expr": { "Literal": { "Value": "0L" } } },
    "rightOuterMargin": { "expr": { "Literal": { "Value": "0L" } } },
    "paddingUniform": { "expr": { "Literal": { "Value": "0L" } } }
  },
  "selector": { "id": "default" }
}]
```

---

## Discovering Properties

```bash
# List all formatting objects for cardVisual
powerbi-report-author formatting list-objects cardVisual

# Inspect a specific object
powerbi-report-author formatting describe-object cardVisual value
powerbi-report-author formatting describe-object cardVisual accentBar
powerbi-report-author formatting describe-object cardVisual outline
powerbi-report-author formatting describe-object cardVisual referenceLabel

# Search across all objects for a property
powerbi-report-author formatting search cardVisual "padding|margin"
```

---

## References

- [formatting.md § Selectors](formatting.md#selectors-targeting-specific-data) — id selector pattern
- [theming.md § Visual Styles](theming.md#6-visual-styles-visualstyles) — theme defaults

