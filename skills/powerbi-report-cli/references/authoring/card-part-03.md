# Card Visual Authoring Guide - Part 3

## Contents

- [Key Formatting Rules](#key-formatting-rules)
  - [Instance selectors required](#instance-selectors-required)
  - [Remove the internal border](#remove-the-internal-border)
  - [Override the category label text](#override-the-category-label-text)
  - [Accent bar](#accent-bar)
- [Multi-Value Formatting](#multi-value-formatting)
  - [cardCalloutArea](#cardcalloutarea)
  - [layout (gridlines between callouts)](#layout-gridlines-between-callouts)
  - [divider](#divider)
- [When to Consolidate vs. Keep Separate](#when-to-consolidate-vs-keep-separate)
- [Theme Approach](#theme-approach)
- [Discovering Properties](#discovering-properties)
- [References](#references)


Continuation of `card.md`. Open this file directly from the skill reference index.

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

- formatting.md § Selectors (see `formatting.md`, section `selectors-targeting-specific-data`) — id selector pattern
- theming.md § Visual Styles (see `theming.md`, section `6-visual-styles-visualstyles`) — theme defaults
