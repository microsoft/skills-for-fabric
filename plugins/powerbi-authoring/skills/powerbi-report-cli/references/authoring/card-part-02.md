# Card Visual Authoring Guide - Part 2

## Contents

- [Card Sizing (Required)](#card-sizing-required)
  - [Step 0: Read the canvas height](#step-0-read-the-canvas-height)
  - [Step 1: Compute dimensions](#step-1-compute-dimensions)
  - [Step 2: Resolve effective values from cascade](#step-2-resolve-effective-values-from-cascade)
  - [Step 3: Verify no clipping](#step-3-verify-no-clipping)
  - [Step 4: Width considerations](#step-4-width-considerations)
  - [Step 5: Apply in PBIR](#step-5-apply-in-pbir)
  - [Default values (cascade resolution)](#default-values-cascade-resolution)
  - [Worked examples](#worked-examples)
- [Card Sizing Anti-Patterns](#card-sizing-anti-patterns)


Continuation of `card.md`. Open this file directly from the skill reference index.

## Card Sizing (Required)

> Before creating or resizing any `cardVisual`,
> compute all sizing values using the formula below. Cards must be **compact**
> (not crowd detail visuals) AND **not clipped** (text fully visible).

### Step 0: Read the canvas height

Read from the page's `page.json` file:
```
<Report>.Report/definition/pages/<pageId>/page.json → "height"
```
Common values: 720 (standard), 1080 (Full HD), 600 (mobile).

### Step 1: Compute dimensions

Fonts scale with the canvas (readability). Height is **generated** as the content
minimum for those fonts — never hardcoded — so text never clips and there is no
empty band. The canvas budget only *caps* height so cards can't crowd out other
visuals; it is never added to the height.

```
# 1. Fonts scale with the canvas — floored and capped
value_font_size = min(28, max(12, floor(canvas_height * 0.028)))
label_font_size = min(14, max(8,  floor(value_font_size * 0.55)))

# 2. Fixed inner geometry (applied by the Step 5 recipe)
vco_padding = 8   # visualContainerObjects.padding — outer breathing room
inner_pad   = 8   # objects.padding.paddingUniform — keeps text off the accent bar / edge
spacing     = 2   # verticalSpacing between value and label

# 3. Height = content minimum for those fonts (label budgeted at >=12pt)
render(fs)         = ceil(fs * 1.5)
content_min        = 2*vco_padding + 2*inner_pad + spacing
                   + render(value_font_size) + render(max(label_font_size, 12))
target_card_height = content_min

# 4. Canvas budget cap (crowd-out guard): height must stay <=15% of canvas
canvas_cap = floor(canvas_height * 0.15)
if content_min > canvas_cap:
    reduce value_font_size (then label_font_size) toward the floors until
    content_min <= canvas_cap    # if already at the floors, the canvas is too small for cards
horizontal_padding = vco_padding
```

> **Caps 28/14pt, floors 12/8pt.** Caps prevent oversized fonts on large canvases
> (readability plateaus above them); floors keep text legible. If the fonts hit
> the floor and `content_min` still exceeds the canvas cap, the canvas is too
> small for cards.

**Quick Reference** (height is the generated content minimum):

| Canvas Height | Value Font | Label Font | Card Height |
|---------------|------------|------------|-------------|
| 400px | — | — | **Not supported** — 15% cap (60px) < 70px minimum |
| 600px | 16pt | 8pt | 76 px |
| 720px | 20pt | 11pt | 82 px |
| 1080px | 28pt (cap) | 14pt (cap) | 97 px |

> Heights use the **compact recipe** (Step 5): inner padding 8, VCO padding 8.
> Height budgets the label at >=12pt even when a smaller label font is set, so a
> shown or hidden label never clips.

**For cards with reference labels**, add ~16px to `target_card_height` to
accommodate the third text line (reference value/label pair).

### Step 2: Resolve effective values from cascade

If modifying an existing card or if a custom theme is active, resolve the
effective values before verifying. Inspect these sources in priority order
(first match wins):

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

> **These content-area defaults are a `cardVisual` runtime built-in and are
> usually absent from the theme file.** The effective defaults are
> **`padding.paddingUniform ≈ 12`** (inner callout padding) and
> **`layout.paddingUniform = 0`** — `layout` adds height only when explicitly
> set. The compact recipe (Step 5) sets `padding` to **8** (trimming the ≈12
> default just enough to keep the value and label off the accent bar and card
> edge) and leaves `layout` at 0, so budget inner padding at 8, not 12.

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

Only after resolving all effective values, proceed to Step 3.

### Step 3: Verify no clipping

Card visual anatomy (top to bottom):

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
- **Always reserve label height** — compute it as `render(max(label,12))`, so even
  a label font below 12pt still gets ≥12pt of vertical room in the card. This
  keeps a row of cards the same height; only a single, standalone value-only card
  (`label.show=false`) may drop it for a tighter fit.
- **Content padding** comes from two objects, each with uniform/individual modes:
  - `objects.padding`: if `paddingIndividual=true` use per-side values, else `paddingUniform`
  - `objects.layout`: if `paddingIndividual=true` use `topOuterMargin`/`bottomOuterMargin`, else `paddingUniform`
- **VCO padding** (`visualContainerObjects.padding`): `top`/`bottom`/`left`/`right`
- **verticalSpacing**: from `objects.spacing` or `visualContainerObjects.spacing`
- **calloutSize** (`objects.layout.calloutSize`): percentage that may scale the
  content area. Runtime default is unverified.

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

### Step 4: Width considerations

Width overflow shows ellipsis ("...") rather than clipping — less severe than
height clipping. Properties that consume horizontal space:

- VCO padding left/right (`visualContainerObjects.padding`)
- Content padding left/right (from `objects.padding` and `objects.layout`, same uniform/individual logic as vertical)
- Border width (left + right)
- Accent bar width (if positioned left or right)

If values are truncated with ellipsis, increase `position.width` or reduce
`value_font_size`.

Use **5 chars** when display format is unknown. Width overflow shows ellipsis.

### Step 5: Apply in PBIR

The recipe sets `objects.padding.paddingUniform` to **8** and
`objects.layout.paddingUniform` to **0**. This trims the built-in inner callout
padding (≈12) to keep the card compact, while leaving a small margin so the value
and label never touch the accent bar or card edge. VCO padding (below) supplies
the outer breathing room.

```json
"objects": {
  "value": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<value_font_size>D" } } } }, "selector": { "id": "default" } }],
  "label": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<label_font_size>D" } } } }, "selector": { "id": "default" } }],
  "padding": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "8D" } } } }, "selector": { "id": "default" } }],
  "layout": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "0D" } } } }, "selector": { "id": "default" } }]
},
"visualContainerObjects": {
  "padding": [{
    "properties": {
      "top": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } },
      "bottom": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } },
      "left": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } },
      "right": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } }
    },
    "selector": { "id": "default" }
  }],
  "spacing": [{
    "properties": {
      "customizeSpacing": { "expr": { "Literal": { "Value": "true" } } },
      "verticalSpacing": { "expr": { "Literal": { "Value": "2D" } } }
    },
    "selector": { "id": "default" }
  }]
}
```

### Default values (cascade resolution)

Priority: visual `objects` → custom theme `cardVisual.*` → custom theme `*.*` → base theme.

| Variable | Source | Notes |
|----------|--------|-------|
| `value_fontSize` | `textClasses.callout.fontSize` | Override via `objects.value.fontSize` (id selector) |
| `label_fontSize` | `textClasses.label.fontSize` | Override via `objects.label.fontSize` (id selector) |
| `padding_top/bottom/left/right` | `visualContainerObjects.padding` | VCO padding around the whole visual |
| `padding` object | `objects.padding` (id selector) | `paddingUniform` or individual `paddingTop/Bottom/Left/Right` |
| `layout` object | `objects.layout` (id selector) | `paddingUniform` or individual `topOuterMargin/bottomOuterMargin` |
| `verticalSpacing` | `objects.spacing` (id selector) | Gap between value and label |
| `spaceBelowTitleArea` | `visualContainerObjects.spacing` | Gap below title area |
| `calloutSize` | `objects.layout.calloutSize` | Percentage; runtime default unverified |
| `title_fontSize` | `visualContainerObjects.title` | Title font size when title is shown |
| `border_width` | `visualContainerObjects.border` | Only contributes when `border.show=true` |
| `accentBar_width` | `objects.accentBar` (id selector) | Only contributes when `accentBar.show=true` |

> Always read the report's base theme file
> (`StaticResources/SharedResources/BaseThemes/*.json`) for authoritative
> default values. Do not assume hardcoded constants.

### Worked examples

These examples use the compact recipe (Step 5): `padding.paddingUniform=8`,
`layout.paddingUniform=0`, `verticalSpacing=2`, VCO padding top/bottom=8, label
budgeted at ≥12pt. Example 1 shows what happens if you skip the recipe and leave
the ≈12 built-in inner padding (plus an added `layout`).

**Example 1 — recipe skipped: built-in padding ≈12 plus an added layout=12 (FAILS):**
```
content_padding = (12 padding + 12 layout) × 2 sides = 48
required_height = 8+8 + 48 + ceil(20×1.5) + 2 + ceil(12×1.5)
               = 16 + 48 + 30 + 2 + 18 = 114
→ 114 > 82 → CLIPS!

Fix — apply the Step 5 recipe (padding=8, layout=0):
content_padding = (8 + 0) × 2 = 16
required_height = 16 + 16 + 30 + 2 + 18 = 82   → fits an 82px card
```

**Example 2 — with title and accent bar:**
```
title_area = render(title_fontSize) + spaceBelowTitleArea
required_height = border + VCO_padding + title_area + content_padding
               + render(value) + verticalSpacing + render(label) + accentBar
```

**Example 3 — custom VCO padding=4, border=2, value=32/label=14:**
```
content_padding = (8 padding + 0 layout) × 2 = 16
required_height = 2×2 + 4+4 + 16 + ceil(32×1.5) + 2 + ceil(14×1.5)
               = 4 + 8 + 16 + 48 + 2 + 21 = 99
→ use h ≥ 100
```

#### Quick-reference safe dimensions

Compact recipe (`padding.paddingUniform=8`, `layout.paddingUniform=0`,
VCO padding=8, `verticalSpacing=2`, label=12pt, no title, no border):

| value.fontSize | Min height |
|----------------|------------|
| 20 | 82 |
| 24 | 88 |
| 28 | 94 |
| 32 | 100 |
| 36 | 106 |
| 40 | 112 |
| 45 | 120 |

With title: add `render(title_fontSize) + spaceBelowTitleArea` to height.
With custom VCO padding=4: subtract **8px** from height.

> **These are the true minimums** for the compact recipe — the smallest height
> that renders a value + label without clipping. Step 1 sets card height to this
> minimum, so cards stay compact by construction. Add `render(title_fontSize) +
> spaceBelowTitleArea` for a title, and ~16px for a reference/delta line.

---

## Card Sizing Anti-Patterns

| ❌ Anti-pattern | ✅ Do instead |
|----------------|--------------|
| Hardcoding card height (e.g. `height: 80`) | Generate it from the Step 1 formula (content minimum for the derived fonts) |
| Leaving the ≈12 built-in inner padding, or adding `layout` padding | Apply the Step 5 recipe: `objects.padding.paddingUniform=8`, `objects.layout.paddingUniform=0` |
| Growing card height to stop the label clipping | Trim inner padding to 8 instead; height then matches the content |
| Setting inner padding to 0 to save space | Keep 8 — at 0 the value/label touch the accent bar and card edge |
| Quoting numeric `position` values (`"height": "80"`) | Use raw numbers (`"height": 82`) |

---
