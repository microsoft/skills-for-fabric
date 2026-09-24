# Button Visual Authoring Guide

## Contents

- [CLI Discovery](#cli-discovery)
- [Template](#template)
- [Button Sizing & Placement (Required)](#button-sizing--placement-required)
  - [Step 0: Gather inputs](#step-0-gather-inputs)
  - [Step 1: Compute width (prevents horizontal truncation)](#step-1-compute-width-prevents-horizontal-truncation)
  - [Step 2: Set height (fixed range — do NOT derive by shrinking)](#step-2-set-height-fixed-range--do-not-derive-by-shrinking)
  - [Step 3: Apply the fixed render contract (REQUIRED for consistent appearance)](#step-3-apply-the-fixed-render-contract-required-for-consistent-appearance)
  - [Step 4: Verify (self-check before finalizing)](#step-4-verify-self-check-before-finalizing)
  - [Step 5: Render-verify and fix clipped labels (required for non-rectangular shapes)](#step-5-render-verify-and-fix-clipped-labels-required-for-non-rectangular-shapes)
  - [Worked example](#worked-example)
  - [Placement](#placement)


Buttons (`actionButton`) are interactive visuals that trigger navigation or
actions when clicked. They have **no data roles** — all configuration is
formatting (appearance) and a `visualLink` VCO (action).

Related visual types:
- `pageNavigator` — auto-generated page tabs (no manual button creation needed)
- `bookmarkNavigator` — auto-generated bookmark tabs

**Contents:**

- [CLI Discovery](#cli-discovery)
- [Template](#template)
- [Button Sizing & Placement (Required)](#button-sizing--placement-required)
- Action Types (continued in `button-part-02.md`)
- Formatting Objects (continued in `button-part-02.md`)
- Dual-Entry Pattern (Required) (continued in `button-part-02.md`)
- State Selectors (continued in `button-part-02.md`)
- Shape Options (continued in `button-part-02.md`)
- Icon Options (continued in `button-part-02.md`)
- Hover State Example (continued in `button-part-03.md`)
- Common Patterns (continued in `button-part-03.md`)
- Anti-Patterns (continued in `button-part-03.md`)

---

## CLI Discovery

Before authoring, use CLI commands to confirm capabilities:

```bash
# Confirm visual type and roles (actionButton has no data roles)
powerbi-report-author catalog describe actionButton

# List all formatting objects and which need selectors
powerbi-report-author formatting list-objects actionButton

# Drill into any object from that list for exact properties, types, and enum values
powerbi-report-author formatting describe-object actionButton <object>

# Discover the enum values for a specific property
powerbi-report-author formatting describe-property actionButton <object> <property>

# Find the action configuration (visualLink VCO)
powerbi-report-author formatting search actionButton "action|link|type"
```

> **Always use CLI metadata** for exact property names, types, and enum values —
> it is the source of truth as the schema evolves.

---

## Template

```json
{
  "$schema": "<copy from existing visual in same report>",
  "name": "<20hexchars>",
  "position": { "x": 40, "y": 600, "z": 1000, "height": 44, "width": 150, "tabOrder": 1000 },
  "visual": {
    "visualType": "actionButton",
    "objects": {
      "text": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        { "properties": { "text": { "expr": { "Literal": { "Value": "'Button Label'" } } }, "fontSize": { "expr": { "Literal": { "Value": "11D" } } }, "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } }, "horizontalAlignment": { "expr": { "Literal": { "Value": "'center'" } } } }, "selector": { "id": "default" } }
      ],
      "icon": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } },
        { "properties": { "shapeType": { "expr": { "Literal": { "Value": "'rightArrow'" } } }, "placement": { "expr": { "Literal": { "Value": "'left'" } } } }, "selector": { "id": "default" } }
      ],
      "fill": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0078D4'" } } } } } }, "selector": { "id": "default" } }
      ],
      "outline": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }
      ],
      "shape": [
        { "properties": { "tileShape": { "expr": { "Literal": { "Value": "'rectangleRounded'" } } }, "roundEdge": { "expr": { "Literal": { "Value": "8L" } } } } },
        { "properties": { "tileShape": { "expr": { "Literal": { "Value": "'rectangleRounded'" } } } }, "selector": { "id": "default" } }
      ]
    },
    "visualContainerObjects": {
      "background": [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ],
      "border":     [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ],
      "visualLink": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "type": { "expr": { "Literal": { "Value": "'<ActionType>'" } } }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  },
  "howCreated": "InsertVisualButton"
}
```

---

## Button Sizing & Placement (Required)

A button's label is a **single line of text drawn once** at a fixed anchor inside the
`position` box. Unlike a table or matrix (which paginates / scrolls when short on space) or a
chart (which rescales), a button does **not** scroll, shrink-to-fit, or wrap — if the box is
smaller than the text, the glyphs are simply **clipped** ("Income Statement" → "Income…").
So compute the width from the label, set a height in the safe range, and apply the **fixed
render contract** below. Run the Step 4 self-check before moving on — do not eyeball dimensions.

### Step 0: Gather inputs

- `label` — the exact button text (use the **longest** label if sizing a row of buttons; all
  buttons in a row share one width and height).
- `fontSizePt` — the text font size in points (default **12**; use 11 for dense nav rows).
- `free_zone` — the horizontal span available on the page for the button(s), from the page
  layout (e.g. header-right band, or the gap left of a slicer cluster). Read sibling visual
  positions from the page's `visuals/*/visual.json`.

### Step 1: Compute width (prevents horizontal truncation)

Run `text measure` with the exact label, font, size, and weight of the button, and use
`recommendedButtonWidthPx` from the output for `position.width`:

```bash
powerbi-report-author text measure "Balance Sheet & Liquidity" --font "Segoe UI" --size 11 --bold
# → recommendedButtonWidthPx = position.width
```

The command measures the label against the real installed-font metrics and returns a width that
already includes horizontal padding, an optional icon allowance (pass `--icon`), and a safety
margin, rounded up to a 10px grid. For a **row** of buttons,
measure the **longest** label and give every button that width. Confirm tight rows with the
Step 4 render check.

### Step 2: Set height (fixed range — do NOT derive by shrinking)

```
position.height = clamp(fontSizePt × 4, 40, 56)   # 11pt → 44; 12pt → 48
```

The renderer reserves internal vertical padding, so a height below ~36px clips the label
regardless of font size. Height does **not** center the text (see render contract) — never
shrink height to "tighten" spacing.

> ⚠️ **Non-rectangular shapes: how to handle the label.** The Step 1 width and Step 2
> height target a **rectangular** text area (`rectangle` / `rectangleRounded` / `pill`
> fill edge-to-edge). Shapes that inset the content region — arrows and chevrons,
> `parallelogram`/`trapezoid` slants, `hexagon`/`octagon`/`pentagon`/triangles,
> `heart`, `oval`, `speechbubbleRectangle` — and any button using `shape.shapeAngle`
> (shape rotated, label stays horizontal) put horizontal text over a region that is
> **not an axis-aligned rectangle**. The label then overruns the colored fill and spills
> onto the page canvas — where it looks clipped, and if the label color does not contrast
> with the canvas behind it, it vanishes entirely (label and canvas colors are arbitrary;
> the failure is the overrun, not any specific color). **No formula can predict the inset —
> the shape geometry varies.** Handle it with these levers, in order:
> 1. **Prefer the rectangle family for any button that must carry a real text label.**
>    `rectangle`/`rectangleRounded`/`pill` are the only shapes where the sizing formula is
>    reliable. Reserve arrows, triangles, `heart`, etc. for **icon-only or very short**
>    labels (they are decorative/directional).
> 2. **Seat the text in the shape's thick region with `text.horizontalAlignment`** instead
>    of centering it into a narrow/empty part: e.g. `'left'` for a right-pointing arrow or a
>    right-triangle whose mass is on the left; align away from an arrowhead or a slanted
>    edge. This alone rescues many shapes.
> 3. **Shorten the label** (or drop to icon-only) so it fits the narrow band.
> 4. **Render-verify and adjust** (Step 5). Adding width/height *may* help but is **not
>    reliable** on its own — enlarging grows the shape and the empty margins together, so a
>    centered label can still miss the colored area. The Desktop render is the only
>    authoritative test.

### Step 3: Apply the fixed render contract (REQUIRED for consistent appearance)

These are not stylistic choices — omitting any of them produces the "white box / text sits
low / inset fill" defects. Every button must set all four (the [Template](#template) already
encodes them):

| # | Setting | Why |
|---|---------|-----|
| 1 | `visualContainerObjects.background.show = false` | Removes the default white container box that makes the fill look inset |
| 2 | `visualContainerObjects.border.show = false` | Removes the faint container outline |
| 3 | `shape.tileShape = 'rectangleRounded'` (+ `roundEdge`), **not** `'pill'` | `pill` renders the fill inset inside the container; `rectangleRounded` fills edge-to-edge |
| 4 | `icon.placement = 'left'` (or `'right'`) even when `icon.show = false` | The default top icon slot reserves vertical space that pushes the label down |

> ⚠️ `text.verticalAlignment` is **ignored** by the `actionButton` renderer — `'top'`,
> `'middle'`, `'center'`, and `'bottom'` all render identically. The label is drawn at a
> fixed, roughly centered position with a slight downward
> bias that **cannot** be adjusted through formatting. Do not add `verticalAlignment` as a
> "fix" and do not shrink the height to compensate (that clips the label). If pixel-perfect
> vertical centering is truly required, the only workaround is a rectangle `shape` visual for
> the styled label with a transparent `actionButton` overlaid for the click target — heavier,
> use only when the small default bias is unacceptable.

### Step 4: Verify (self-check before finalizing)

```
Constraint A (fit):        position.width ≥ recommendedButtonWidthPx  # label not truncated
Constraint B (height):     40 ≤ position.height ≤ 56
Constraint C (no overlap): sum(button widths + gaps) ≤ free_zone width
Constraint D (uniform):    all buttons in one row share width & height
Constraint E (contract):   Step 3 items 1–4 all present
Constraint F (shape fit):  non-rectangular tileShape → label fully visible in the Desktop render (formula alone is insufficient; see Step 2 note)
```

If any constraint fails, adjust and re-check. Width overflow of the *free zone* (Constraint C)
means the labels are too long for one row — reduce `fontSizePt`, wrap to a second row, or free
up contended space (e.g. move slicers), **never** shrink the button below `recommendedButtonWidthPx`.

### Step 5: Render-verify and fix clipped labels (required for non-rectangular shapes)

The formula and self-check cannot guarantee a non-rectangular label fits — the render is the
authoritative test. After authoring, run the preview verification loop
(preview.md (see `preview.md`)) and **inspect the screenshot of each button**:

1. `powerbi-report-author validate "<folder>"` →
   `powerbi-report-author preview "<folder>" --host desktop --status` (the
   unsaved-changes preflight required before every reload) →
   `powerbi-report-author preview "<folder>" --host desktop --reload` →
   `powerbi-report-author preview "<folder>" --host desktop --screenshot "<file>" --page <pageId>`.
2. Scan every button in the image for a **clipped or truncated label** (glyphs cut at an
   edge, an ellipsis, or text overrunning the shape's narrow region — common on triangles,
   `heart`, `arrow`/chevron tips, `parallelogram`/`trapezoid` slants).
3. For each clipped button, apply **one** fix and reload. Which fix works depends on *why*
   it clips:
   - **Rectangular shape, label just too long** — this is *horizontal* truncation, so
     increase `position.width` (re-run `text measure` for the value) **or shorten the label**
     to fit the available width. Height does not affect horizontal fit — keep it within the
     Step 2 `40–56` range; do not bump it to "make room". Reliable.
   - **Non-rectangular shape** (triangles, `heart`, `arrow`/chevron tips,
     `parallelogram`/`trapezoid` slants) — the label overruns the shape's narrow colored
     region and spills onto the page canvas, looking clipped (and invisible if it does not
     contrast with the canvas). **Enlarging the
     container is not a reliable fix** (it grows the shape but the axis-aligned label still
     may not land inside the colored area). Prefer a **shorter label**; only then adjust
     size. This case can only be settled by the render, not the formula.
4. Repeat 1–3 until **no** button shows a clipped label. Do not stop at "validates" — a
   button can validate and still clip.

> **Rotation — three different failure modes, not one.** The `rotation` object behaves
> differently per property; do not treat them the same:
> - **`angle`** rotates the **whole visual (shape + label together)**. The shape stays
>   rectangular relative to its own frame, so the sizing formula still holds and the label
>   still fits — the only problem is the *tilted rectangle's bounding box* overflowing the
>   `position` rectangle, so Power BI clips the corners. Fix: add `position.width`/`height`
>   padding for the rotated bounding box. **Reliable.**
> - **`shapeAngle`** rotates **only the shape; the label stays horizontal**. Horizontal text
>   now sits over a tilted rectangle and spills past the colored area — this **breaks the
>   rectangular formula the same way a non-rectangular shape does**, and enlarging is **not**
>   a reliable fix. Shorten the label and render-verify.
> - **`textAngle`** rotates **only the label**; the shape stays rectangular. The diagonal
>   text box just needs extra `position.height` (and a little width). Render-verify.

### Worked example

Row of 3 nav buttons, longest label `"Balance Sheet & Liquidity"` at 11pt bold, in an 888px
header-right band:

```
powerbi-report-author text measure "Balance Sheet & Liquidity" --font "Segoe UI" --size 11 --bold
  → textWidthPx = 177.07,  recommendedButtonWidthPx = 220

position.width  = 220                                  # longest label → every button in the row
position.height = clamp(11 × 4, 40, 56) = 44
Constraint C:   3 × 220 + 2 × 16 gaps = 692 ≤ 888      ✓
```

### Placement

Keep the **whole** button inside the canvas, like any other visual:

- `x ≥ margin`, `y ≥ margin`, `x + width ≤ canvasWidth − margin`, `y + height ≤ canvasHeight − margin`
  (margin ≈ 16–32px). Do not append a button below all other content where `y + height` can
  spill past the page edge — place it inside its reserved band (e.g. the bottom of a filter rail).
- Leave ≥ 8px gaps between adjacent buttons so grids don't crowd or overlap.

Validated defaults: `height 44, fontSize 11, center` + a `text measure`-derived width + the
Step 3 render contract — no clipping, no white box.

---
