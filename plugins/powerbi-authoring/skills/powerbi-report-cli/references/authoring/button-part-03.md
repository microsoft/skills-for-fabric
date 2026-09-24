# Button Visual Authoring Guide - Part 3

## Contents

- [Hover State Example](#hover-state-example)
- [Common Patterns](#common-patterns)
  - [Back button](#back-button)
  - [Navigation bar (multiple page buttons)](#navigation-bar-multiple-page-buttons)
  - [Reset/Clear button](#resetclear-button)
  - [Drillthrough button](#drillthrough-button)
- [Anti-Patterns](#anti-patterns)


Continuation of `button.md`. Open this file directly from the skill reference index.

## Hover State Example

Button with fill color change on hover:

```json
{
  "$schema": "<copy from existing visual>",
  "name": "<20hexchars>",
  "position": { "x": 40, "y": 600, "z": 1000, "height": 48, "width": 150, "tabOrder": 1000 },
  "visual": {
    "visualType": "actionButton",
    "objects": {
      "text": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        { "properties": { "text": { "expr": { "Literal": { "Value": "'Click Me'" } } }, "fontSize": { "expr": { "Literal": { "Value": "12D" } } }, "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } }, "horizontalAlignment": { "expr": { "Literal": { "Value": "'center'" } } } }, "selector": { "id": "default" } },
        { "properties": { "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } } }, "selector": { "id": "hover" } }
      ],
      "icon": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } },
        { "properties": { "shapeType": { "expr": { "Literal": { "Value": "'rightArrow'" } } }, "placement": { "expr": { "Literal": { "Value": "'left'" } } } }, "selector": { "id": "default" } }
      ],
      "fill": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0078D4'" } } } } } }, "selector": { "id": "default" } },
        { "properties": { "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#005A9E'" } } } } } }, "selector": { "id": "hover" } }
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
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } }, "type": { "expr": { "Literal": { "Value": "'Back'" } } } } }
      ]
    },
    "drillFilterOtherVisuals": true
  },
  "howCreated": "InsertVisualButton"
}
```

---

## Common Patterns

### Back button

Every drillthrough target page must include an `actionButton` whose
`visualContainerObjects.visualLink` uses the `Back` action:

```json
"visualLink": [
  {
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "type": { "expr": { "Literal": { "Value": "'Back'" } } }
    }
  }
]
```

The action returns to the source page while preserving the expected
drillthrough navigation behavior. Validate it by navigating to the target page
from a selected source data point and activating the Back button.

### Navigation bar (multiple page buttons)

Create one `actionButton` per page, arranged horizontally. Use `PageNavigation`
action type with each button targeting a different `navigationSection` (page ID).

### Reset/Clear button

```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'ClearAllSlicers'" } } },
    "tooltip": { "expr": { "Literal": { "Value": "'Clear all slicers on this page'" } } }
  }
}]
```

### Drillthrough button

Place on a page with cross-filter context. When clicked, navigates to the
drillthrough target page passing the current filter context:

```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'Drillthrough'" } } },
    "drillthroughSection": { "expr": { "Literal": { "Value": "'<drillthrough_page_id>'" } } }
  }
}]
```

---

## Anti-Patterns

| Pitfall | Consequence | Fix |
|---------|-------------|-----|
| Putting `show` and styling in one entry with a selector | Button renders with defaults — no fill, text, or icon styling applied | Use dual-entry pattern: `show` in unselectored entry, styling in selectored entry |
| Writing `shape` as a single selector-less entry | Validates, but Desktop renders a **flat rectangle** ignoring `tileShape` | Add a second `{ "properties": { "tileShape": … }, "selector": { "id": "default" } }` entry (see Shape Options) |
| Placing shape geometry params in the `default`-selector entry | File no longer matches Power BI's serialization; values may not round-trip | Keep geometry params in the no-selector Entry 1; the `default` entry carries `tileShape` only |
| Authoring `tileShape: 'line'` | Renders as a near-invisible thin rule and **crashes the Desktop format pane** (`transformDropdowns` TypeError) when the button is selected | Never use `'line'` — it is a phantom enum value not offered in Desktop; use any other `tileShape` from the CLI |
| Custom icon via inline `data:` URI in `image.url` | May author and validate (schema checks skipped when schema unreachable) but can fail to render or destabilize Desktop | Register the raster under `StaticResources/RegisteredResources/` + `resourcePackages` and point `image.url` at that resource; prefer a built-in `shapeType` glyph |
| Using `{ "metadata": "default" }` instead of `{ "id": "default" }` | Selector not recognized — formatting silently dropped | Always use `{ "id": "<state>" }` |
| Omitting `visualLink.show: true` | Action is configured but never fires on click | Always include `show: true` in the `visualLink` properties |
| Setting `icon.show: false` in the selectored entry instead of unselectored | Icon still appears in some states | Put `icon.show` in the first unselectored entry |
| Using `shape` where button interaction states or semantics are required | Shapes support actions, including field-value Web URLs, but lack button hover/selected/disabled states and button-specific semantics | Use `actionButton` when those states or semantics matter; use the shared selectorless `visualLink` contract when a shape action is intentional |
| Binding a color property to a measure that is missing from the model or returns a non-color value | Desktop **errors the visual** (grey "See details" ⊗ overlay) with a field-error indicator | Ensure the referenced measure exists and returns a valid text color (name, `#hex`, `rgb()`, or `hsl()`) — field value itself **is** supported; see Conditional Formatting |
| Button too small, or `verticalAlignment` used to center the label | Label clips (buttons don't scroll/shrink like tables/charts); default white container box makes the fill look inset, and `text.verticalAlignment` is **ignored** by the renderer | Size `width`/`height` from the label via Button Sizing & Placement; apply the Step 3 render contract (disable `visualContainerObjects.background`+`border`, `tileShape: 'rectangleRounded'` not `pill`, icon `placement: 'left'`). Do **not** rely on `verticalAlignment` or shrink height (that clips the label) |
| Forgetting `drillFilterOtherVisuals: true` | May affect cross-filtering behavior | Include in the `visual` object |
