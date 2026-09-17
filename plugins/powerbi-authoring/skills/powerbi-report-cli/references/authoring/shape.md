# Shape Visual

<!-- TOC -->
- [Basic Example (Rectangle Divider)](#basic-example-rectangle-divider)
- [Container Shapes](#container-shapes)
- [Available Shapes and Formatting](#available-shapes-and-formatting)
- [Shape Text Caveat](#shape-text-caveat)
- [Complete Example (Arrow with All Formatting)](#complete-example-arrow-with-all-formatting)
<!-- /TOC -->

Use `shape` for decorative, non-data elements such as dividers, accent lines,
or colored bars. Shapes respect small dimensions accurately — unlike textbox
visuals, which enforce a minimum rendered height of approximately 24px.

## Basic Example (Rectangle Divider)

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 0, "y": 50, "z": 10001, "height": 4, "width": 1280, "tabOrder": 1 },
  "visual": {
    "visualType": "shape",
    "objects": {
      "shape": [{ "properties": { "tileShape": { "expr": { "Literal": { "Value": "'rectangle'" } } } } }],
      "fill": [{
        "properties": {
          "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#118DFF'" } } } } },
          "transparency": { "expr": { "Literal": { "Value": "0D" } } }
        },
        "selector": { "id": "default" }
      }],
      "outline": [{
        "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } },
        "selector": { "id": "default" }
      }]
    },
    "visualContainerObjects": {
      "background": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "border": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "padding": [{ "properties": {
        "top": { "expr": { "Literal": { "Value": "0D" } } },
        "bottom": { "expr": { "Literal": { "Value": "0D" } } },
        "left": { "expr": { "Literal": { "Value": "0D" } } },
        "right": { "expr": { "Literal": { "Value": "0D" } } }
      } }]
    }
  }
}
```

> **Tip:** Set padding to 0 and hide background/border to ensure the shape
> fills its position exactly — important for thin divider lines.

## Container Shapes

When using a shape as a **layout container** (e.g., a navigation bar, header
strip, or grouping rectangle behind other visuals), choose the fill color and
transparency to **match the reference image** while ensuring text/visuals
layered on top remain readable:

1. **If the reference shows a visible colored container** (e.g., a dark header
   bar, a blue accent strip), set `fillColor` to the reference color and
   `transparency` to `0D` (or whatever matches the reference opacity). Use
   `z: 0` for the container shape and higher `z` for content on top.
2. **If the container is invisible** (same color as page background, or purely
   for grouping), either omit the shape entirely or set `transparency` to
   `100D`.
3. **If the page background already provides the desired color**, the container
   shape is unnecessary — skip it to avoid layering issues.

> **⚠️ Always set explicit `fontColor` on shape text:** When a shape has
> `text.show: true`, always include an explicit `fontColor` in the
> `{ selector: { id: "default" } }` text entry. Without it, the text color
> inherits from the theme's foreground — which may not contrast with the
> shape's `fill` color after a theme switch (e.g., a white pill button on a
> light canvas becomes invisible). This is the most commonly missed property
> during re-theming because bulk hex-replacement only updates existing colors,
> not missing ones.

```json
// Visible container (e.g., dark header bar on a black page)
"fill": [{
  "properties": {
    "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1E1E1E'" } } } } },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } }
  },
  "selector": { "id": "default" }
}]
```

> **⚠️ Text contrast pitfall:** Setting `transparency` to `100D` makes the
> shape invisible. If text or visuals layered on top use a color that matches
> the **page canvas background** (not the shape), that content becomes
> unreadable. Example: white canvas + blue container shape + white text →
> making the shape 100% transparent turns the text invisible (white on white).
> Always verify that text color contrasts with whatever is visible behind it
> after transparency is applied.
>
> **⚠️ Don't add unnecessary shapes:** When recreating a UI layout from a
> reference image, check whether the page background already provides the
> needed color. If the reference shows a black page with content directly on
> it, set the page `background.color` and place visuals directly — do not
> add a redundant container shape that could block content or cause layering
> issues.

## Available Shapes and Formatting

Discover shape types (`tileShape` enum) and shape-specific geometry parameters:

```bash
powerbi-report-author formatting list-objects shape
powerbi-report-author formatting describe-object shape <object>
```

Shape objects that require `id` selectors need only the **single entry with the
`id` selector** — the static (no-selector) entry is redundant but harmless.
The CLI annotates these with `(selector: default)` in
`powerbi-report-author formatting list-objects` output and `_selectorHint` in
`powerbi-report-author formatting describe-object` output.

### Rotation

The `rotation` object is the **only** shape formatting object that does **not**
require a selector. It supports three independent angles:

```json
"rotation": [{
  "properties": {
    "shapeAngle": { "expr": { "Literal": { "Value": "78L" } } },
    "angle": { "expr": { "Literal": { "Value": "136D" } } },
    "textAngle": { "expr": { "Literal": { "Value": "92L" } } }
  }
}]
```

- `shapeAngle` (integer L) — rotates the shape geometry
- `angle` (numeric D) — rotates the entire visual container
- `textAngle` (integer L) — rotates the text label independently

> **⚠️ Textbox minimum height:** Do not use textbox visuals as thin decorative
> lines. PBI Desktop enforces a minimum rendered height (~24px) regardless of
> the `height` value in `position`. Use a shape visual instead.

## Shape Text Caveat

Shape `text` properties can validate successfully but still fail to render
reliably in Desktop for prominent page-level titles or headers. For visible page
titles, use a `textbox` visual with the native `paragraphs` array structure from
`textbox.md`; use a separate `shape` behind it only when you need a title
panel, accent bar, or background container.

Reserve shape text for simple labels only after screenshot verification confirms
that the text is visible. When shape text is used, always set an explicit
`fontColor` and verify contrast against the rendered fill/background.

## Complete Example (Arrow with All Formatting)

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 100, "y": 290, "z": 1, "height": 300, "width": 280, "tabOrder": 1 },
  "visual": {
    "visualType": "shape",
    "objects": {
      "shape": [{
        "properties": {
          "tileShape": { "expr": { "Literal": { "Value": "'arrow'" } } },
          "roundEdge": { "expr": { "Literal": { "Value": "6L" } } },
          "arrowheadSize": { "expr": { "Literal": { "Value": "51L" } } },
          "arrowStemWidth": { "expr": { "Literal": { "Value": "13L" } } }
        }
      }],
      "rotation": [{
        "properties": {
          "shapeAngle": { "expr": { "Literal": { "Value": "78L" } } },
          "angle": { "expr": { "Literal": { "Value": "136D" } } },
          "textAngle": { "expr": { "Literal": { "Value": "92L" } } }
        }
      }],
      "fill": [{
        "properties": {
          "fillColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": 0.2 } } } } },
          "transparency": { "expr": { "Literal": { "Value": "22D" } } }
        },
        "selector": { "id": "default" }
      }],
      "outline": [{
        "properties": {
          "lineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0 } } } } },
          "weight": { "expr": { "Literal": { "Value": "4D" } } },
          "transparency": { "expr": { "Literal": { "Value": "22D" } } }
        },
        "selector": { "id": "default" }
      }],
      "text": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } }
          }
        },
        {
          "properties": {
            "text": { "expr": { "Literal": { "Value": "'Arrow Shape Visual'" } } },
            "fontFamily": { "expr": { "Literal": { "Value": "'Georgia'" } } },
            "fontSize": { "expr": { "Literal": { "Value": "8D" } } },
            "bold": { "expr": { "Literal": { "Value": "true" } } },
            "fontColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": 0.2 } } } } },
            "horizontalAlignment": { "expr": { "Literal": { "Value": "'right'" } } },
            "verticalAlignment": { "expr": { "Literal": { "Value": "'middle'" } } },
            "topMargin": { "expr": { "Literal": { "Value": "9L" } } },
            "leftMargin": { "expr": { "Literal": { "Value": "6L" } } },
            "rightMargin": { "expr": { "Literal": { "Value": "5L" } } },
            "bottomMargin": { "expr": { "Literal": { "Value": "4L" } } }
          },
          "selector": { "id": "default" }
        }
      ],
      "shadow": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        {
          "properties": {
            "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0 } } } } },
            "transparency": { "expr": { "Literal": { "Value": "18D" } } },
            "shadowBlur": { "expr": { "Literal": { "Value": "55D" } } },
            "shadowPositionPreset": { "expr": { "Literal": { "Value": "'topRight'" } } }
          },
          "selector": { "id": "default" }
        }
      ],
      "glow": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        {
          "properties": {
            "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": 0.6 } } } } },
            "transparency": { "expr": { "Literal": { "Value": "20D" } } }
          },
          "selector": { "id": "default" }
        }
      ]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "text": { "expr": { "Literal": { "Value": "'Arrow Visual'" } } },
          "heading": { "expr": { "Literal": { "Value": "'Heading3'" } } },
          "italic": { "expr": { "Literal": { "Value": "true" } } },
          "fontColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
          "background": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0.6 } } } } },
          "alignment": { "expr": { "Literal": { "Value": "'center'" } } }
        }
      }],
      "subTitle": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "text": { "expr": { "Literal": { "Value": "'Arrow Visual'" } } },
          "alignment": { "expr": { "Literal": { "Value": "'center'" } } }
        }
      }],
      "divider": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": -0.5 } } } } },
          "style": { "expr": { "Literal": { "Value": "'dashed'" } } },
          "width": { "expr": { "Literal": { "Value": "2D" } } }
        }
      }],
      "spacing": [{
        "properties": {
          "customizeSpacing": { "expr": { "Literal": { "Value": "false" } } },
          "verticalSpacing": { "expr": { "Literal": { "Value": "2D" } } }
        }
      }],
      "padding": [{
        "properties": {
          "top": { "expr": { "Literal": { "Value": "5D" } } },
          "left": { "expr": { "Literal": { "Value": "6D" } } },
          "right": { "expr": { "Literal": { "Value": "6D" } } },
          "bottom": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }],
      "lockAspect": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } }
        }
      }],
      "visualLink": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "tooltip": { "expr": { "Literal": { "Value": "'Arrow Visual Type'" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```
