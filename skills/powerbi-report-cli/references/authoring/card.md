# Card Visual Authoring Guide

## Contents

- [Single-Value Template](#single-value-template)
- [Multi-Value Template](#multi-value-template)


Cards (`cardVisual`) display one or more headline metrics. `card` and `multiRowCard`
(both legacy) are deprecated — always use `cardVisual`.

- [Single-Value Template](#single-value-template)
- [Multi-Value Template](#multi-value-template)
- Card Sizing (Required) (continued in `card-part-02.md`)
- Key Formatting Rules (continued in `card-part-03.md`)
- Multi-Value Formatting (continued in `card-part-03.md`)
- When to Consolidate vs. Keep Separate (continued in `card-part-03.md`)
- Theme Approach (continued in `card-part-03.md`)
- Discovering Properties (continued in `card-part-03.md`)
- References (continued in `card-part-03.md`)

---

## Single-Value Template

> ⚠️ **Role name is `Data`, not `Fields`.** The only valid `queryState` key for
> `cardVisual` is `"Data"`. Using `"Fields"` (the legacy `card` role name) causes
> the visual to render empty — PBI Desktop cannot resolve the binding. The
> validator catches this as `Unknown role "Fields"` and `Required role "Data" missing`.

The `Data` role accepts one or more measures. For a single headline KPI:

> **All sizing values must be computed dynamically** from the canvas height
> using the Card Sizing Formula (continued in `card-part-02.md`). Do not hardcode
> height, padding, or font sizes — derive them from `page.json → height`.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 24, "y": 56, "z": 1000, "height": <target_card_height>, "width": 296, "tabOrder": 1000 },
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
    },
    "objects": {
      "value": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<value_font_size>D" } } } }, "selector": { "id": "default" } }],
      "label": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<label_font_size>D" } } } }, "selector": { "id": "default" } }],
      "padding": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "8D" } } } }, "selector": { "id": "default" } }],
      "layout": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "0D" } } } }, "selector": { "id": "default" } }]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": { "top": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } }, "bottom": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } }, "left": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } }, "right": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } } }, "selector": { "id": "default" } }],
      "spacing": [{ "properties": { "customizeSpacing": { "expr": { "Literal": { "Value": "true" } } }, "verticalSpacing": { "expr": { "Literal": { "Value": "2D" } } } }, "selector": { "id": "default" } }]
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
> per-card styling differences (see When to Consolidate vs. Keep Separate (continued in `card-part-03.md`)).

Add multiple projections to the `Data` role. PBI renders them as a horizontal
row of callouts inside one visual. Use this instead of placing multiple
single-value cards side by side when they share the same container styling.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 24, "y": 56, "z": 1000, "height": <target_card_height>, "width": 900, "tabOrder": 1000 },
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
    },
    "objects": {
      "value": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<value_font_size>D" } } } }, "selector": { "id": "default" } }],
      "label": [{ "properties": { "fontSize": { "expr": { "Literal": { "Value": "<label_font_size>D" } } } }, "selector": { "id": "default" } }],
      "padding": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "8D" } } } }, "selector": { "id": "default" } }],
      "layout": [{ "properties": { "paddingUniform": { "expr": { "Literal": { "Value": "0D" } } } }, "selector": { "id": "default" } }]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": { "top": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } }, "bottom": { "expr": { "Literal": { "Value": "<vertical_padding>D" } } }, "left": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } }, "right": { "expr": { "Literal": { "Value": "<horizontal_padding>D" } } } }, "selector": { "id": "default" } }],
      "spacing": [{ "properties": { "customizeSpacing": { "expr": { "Literal": { "Value": "true" } } }, "verticalSpacing": { "expr": { "Literal": { "Value": "2D" } } } }, "selector": { "id": "default" } }]
    }
  }
}
```

> **Sizing tip:** Multi-value cards need more width. Allow ~250–300 px per
> callout. For 3 measures a width of 900 px works well.

---
