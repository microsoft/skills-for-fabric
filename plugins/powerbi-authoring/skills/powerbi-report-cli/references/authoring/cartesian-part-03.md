# Cartesian Visuals (Bar, Column, Line, Scatter) - Part 3

## Contents

  - [y2Axis — Secondary Axis](#y2axis--secondary-axis)
  - [smallMultiplesLayout — Rows Role](#smallmultipleslayout--rows-role)
- [Minimal Examples](#minimal-examples)
  - [Bar Chart (Minimal)](#bar-chart-minimal)
  - [Clustered Bar Chart (with Per-Series Color)](#clustered-bar-chart-with-per-series-color)
- [Complete Examples](#complete-examples)
  - [Clustered Bar Chart with Per-Measure Colors](#clustered-bar-chart-with-per-measure-colors)


Continuation of `cartesian.md`. Open this file directly from the skill reference index.

### y2Axis — Secondary Axis

When the `Y2` role is populated (lineChart only), format the secondary axis.
Example:

```json
"y2Axis": [{
  "properties": {
    "secLabelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } },
    "secTitleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
    "secLogAxisScale": { "expr": { "Literal": { "Value": "false" } } }
  }
}]
```

> **Note:** All `y2Axis` properties are prefixed with `sec`. Run
> `powerbi-report-author formatting describe-object lineChart y2Axis` for the
> full list.

### smallMultiplesLayout — Rows Role

When the `Rows` role is populated, the chart splits into a grid of small
multiples:

```json
"smallMultiplesLayout": [{
  "properties": {
    "rowCount": { "expr": { "Literal": { "Value": "9L" } } },
    "columnCount": { "expr": { "Literal": { "Value": "4L" } } },
    "gridPadding": { "expr": { "Literal": { "Value": "2D" } } },
    "gridLineWidth": { "expr": { "Literal": { "Value": "2D" } } },
    "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0.4 } } } } }
  }
}]
```

Run `powerbi-report-author formatting describe-object <type> smallMultiplesLayout`
for all available properties.

For VCO formatting (title, border, background, etc.), see
formatting.md (see `formatting.md`).

## Minimal Examples

### Bar Chart (Minimal)

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "a1b2c3d4e5f6a7b8c9d0",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 300, "width": 500, "tabOrder": 1000 },
  "visual": {
    "visualType": "barChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "product" } }, "Property": "ProductName" } },
            "queryRef": "product.ProductName",
            "nativeQueryRef": "ProductName",
            "active": true
          }]
        },
        "Y": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "metrics" } }, "Property": "Sales" } },
            "queryRef": "metrics.Sales",
            "nativeQueryRef": "Sales"
          }]
        }
      }
    }
  }
}
```

### Clustered Bar Chart (with Per-Series Color)

Shows both `objects` (chart formatting) and `visualContainerObjects` (container formatting).

**⚠️ `visualContainerObjects` goes INSIDE `visual`, as a sibling of `objects` — NOT as a top-level sibling of `visual`.**

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "e1f2a3b4c5d6e7f8a9b0",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 400, "width": 600, "tabOrder": 1000 },
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "product" } }, "Property": "Category" } },
            "queryRef": "product.Category",
            "nativeQueryRef": "Category",
            "active": true
          }]
        },
        "Y": {
          "projections": [{
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "metrics" } }, "Property": "Revenue" } },
            "queryRef": "metrics.Revenue",
            "nativeQueryRef": "Revenue"
          }]
        }
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "fontSize": { "expr": { "Literal": { "Value": "11D" } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'dotted'" } } }
        }
      }],
      "dataPoint": [{
        "properties": {
          "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 0, "Percent": 0 } } } } }
        }
      }],
      "labels": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "fontSize": { "expr": { "Literal": { "Value": "9D" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
        }
      }]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "text": { "expr": { "Literal": { "Value": "'Revenue by Category'" } } },
          "fontSize": { "expr": { "Literal": { "Value": "14D" } } },
          "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#333333'" } } } } }
        }
      }],
      "background": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } } },
          "transparency": { "expr": { "Literal": { "Value": "0D" } } }
        }
      }],
      "border": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#E0E0E0'" } } } } },
          "radius": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }],
      "dropShadow": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "preset": { "expr": { "Literal": { "Value": "'BottomRight'" } } },
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#000000'" } } } } },
          "transparency": { "expr": { "Literal": { "Value": "80D" } } },
          "position": { "expr": { "Literal": { "Value": "'Outer'" } } }
        }
      }],
      "visualHeader": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "false" } } }
        }
      }],
      "padding": [{
        "properties": {
          "top": { "expr": { "Literal": { "Value": "5D" } } },
          "bottom": { "expr": { "Literal": { "Value": "5D" } } },
          "left": { "expr": { "Literal": { "Value": "5D" } } },
          "right": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }]
    }
  }
}
```

## Complete Examples

### Clustered Bar Chart with Per-Measure Colors

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 0, "height": 700, "width": 1000, "tabOrder": 0 },
  "visual": {
    "visualType": "clusteredBarChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Category" } },
            "queryRef": "OrderBreakdown.Category",
            "nativeQueryRef": "Category",
            "active": true
          }]
        },
        "Y": {
          "projections": [
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Profit)",
              "nativeQueryRef": "Sum of Profit"
            },
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Sales" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Sales)",
              "nativeQueryRef": "Sum of Sales"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [{
          "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
          "direction": "Descending"
        }],
        "isDefaultSort": true
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "fontFamily": { "expr": { "Literal": { "Value": "'Georgia'" } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
          "titleText": { "expr": { "Literal": { "Value": "'Category'" } } },
          "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0 } } } } },
          "innerPadding": { "expr": { "Literal": { "Value": "26L" } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "start": { "expr": { "Literal": { "Value": "0D" } } },
          "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
          "labelPrecision": { "expr": { "Literal": { "Value": "2L" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
          "gridlineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0 } } } } },
          "gridlineThickness": { "expr": { "Literal": { "Value": "4D" } } }
        }
      }],
      "legend": [{
        "properties": {
          "position": { "expr": { "Literal": { "Value": "'TopCenter'" } } },
          "titleText": { "expr": { "Literal": { "Value": "'Sales for Categories'" } } }
        }
      }],
      "zoom": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "showLabels": { "expr": { "Literal": { "Value": "true" } } },
          "showOnValueAxis": { "expr": { "Literal": { "Value": "true" } } }
        }
      }],
      "dataPoint": [{
        "properties": {
          "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 9, "Percent": -0.25 } } } } },
          "fillTransparency": { "expr": { "Literal": { "Value": "18D" } } },
          "borderShow": { "expr": { "Literal": { "Value": "true" } } },
          "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
          "borderSize": { "expr": { "Literal": { "Value": "7D" } } }
        },
        "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
      }],
      "layout": [{
        "properties": {
          "seriesOrderSorted": { "expr": { "Literal": { "Value": "true" } } },
          "clusteredGapSize": { "expr": { "Literal": { "Value": "16D" } } }
        }
      }],
      "labels": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "labelPosition": { "expr": { "Literal": { "Value": "'InsideCenter'" } } },
            "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
            "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
            "labelContentLayout": { "expr": { "Literal": { "Value": "'MultiLine'" } } }
          }
        }
      ]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "text": { "expr": { "Literal": { "Value": "'Profit and Sum of Sales by Category'" } } },
          "fontColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": -0.25 } } } } },
          "background": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.6 } } } } },
          "alignment": { "expr": { "Literal": { "Value": "'center'" } } }
        }
      }],
      "border": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": 0.4 } } } } },
          "width": { "expr": { "Literal": { "Value": "3D" } } },
          "radius": { "expr": { "Literal": { "Value": "5D" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```
