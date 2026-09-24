# Cartesian Visuals (Bar, Column, Line, Scatter) - Part 4

## Contents

  - [Stacked Column Chart with Ribbons and Totals](#stacked-column-chart-with-ribbons-and-totals)
  - [Line Chart with Y2 Secondary Axis and Per-Series Styling](#line-chart-with-y2-secondary-axis-and-per-series-styling)


Continuation of `cartesian.md`. Open this file directly from the skill reference index.

### Stacked Column Chart with Ribbons and Totals

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "972da330c2a28c851c90",
  "position": {
    "x": 198.91,
    "y": 51.22,
    "z": 0,
    "height": 668.20,
    "width": 1006.46,
    "tabOrder": 0
  },
  "visual": {
    "visualType": "columnChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Category" } },
              "queryRef": "OrderBreakdown.Category",
              "nativeQueryRef": "Category",
              "active": true
            }
          ]
        },
        "Y": {
          "projections": [
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Discount" } }, "Function": 0 } },
              "queryRef": "Sum(OrderBreakdown.Discount)",
              "nativeQueryRef": "Sum of Discount"
            },
            {
              "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Product Name" } }, "Function": 5 } },
              "queryRef": "CountNonNull(OrderBreakdown.Product Name)",
              "nativeQueryRef": "Product Name"
            }
          ]
        }
      },
      "sortDefinition": {
        "sort": [
          {
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Discount" } }, "Function": 0 } },
            "direction": "Descending"
          }
        ],
        "isDefaultSort": true
      }
    },
    "objects": {
      "categoryAxis": [
        {
          "properties": {
            "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
            "maxMarginFactor": { "expr": { "Literal": { "Value": "29L" } } },
            "fontSize": { "expr": { "Literal": { "Value": "11D" } } },
            "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": -0.25 } } } } },
            "concatenateLabels": { "expr": { "Literal": { "Value": "false" } } },
            "titleBold": { "expr": { "Literal": { "Value": "true" } } },
            "titleUnderline": { "expr": { "Literal": { "Value": "true" } } },
            "preferredCategoryWidth": { "expr": { "Literal": { "Value": "35D" } } }
          }
        }
      ],
      "valueAxis": [
        {
          "properties": {
            "start": { "expr": { "Literal": { "Value": "0D" } } },
            "invertAxis": { "expr": { "Literal": { "Value": "true" } } },
            "end": { "expr": { "Literal": { "Value": "10000D" } } },
            "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
            "labelPrecision": { "expr": { "Literal": { "Value": "1L" } } },
            "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.4 } } } } },
            "gridlineColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": 0.4 } } } } },
            "gridlineStyle": { "expr": { "Literal": { "Value": "'solid'" } } },
            "gridlineThickness": { "expr": { "Literal": { "Value": "2D" } } }
          }
        }
      ],
      "legend": [
        {
          "properties": {
            "position": { "expr": { "Literal": { "Value": "'TopCenter'" } } },
            "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
            "showTitle": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ],
      "dataPoint": [
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "0D" } } }
          }
        },
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 7, "Percent": 0.2 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "3D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Discount)" }
        },
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 8, "Percent": -0.25 } } } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": -0.5 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "5D" } } }
          },
          "selector": { "metadata": "CountNonNull(OrderBreakdown.Product Name)" }
        }
      ],
      "ribbonBands": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } }
          }
        },
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "35D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Discount)" }
        },
        {
          "properties": {
            "fillTransparency": { "expr": { "Literal": { "Value": "44D" } } },
            "borderShow": { "expr": { "Literal": { "Value": "true" } } },
            "borderColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.5 } } } } },
            "borderSize": { "expr": { "Literal": { "Value": "2D" } } },
            "borderTransparency": { "expr": { "Literal": { "Value": "59D" } } }
          },
          "selector": { "metadata": "CountNonNull(OrderBreakdown.Product Name)" }
        }
      ],
      "labels": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "labelOrientation": { "expr": { "Literal": { "Value": "1D" } } },
            "labelOverflow": { "expr": { "Literal": { "Value": "false" } } },
            "optimizeLabelDisplay": { "expr": { "Literal": { "Value": "true" } } },
            "enableTitleDataLabel": { "expr": { "Literal": { "Value": "true" } } },
            "enableBackground": { "expr": { "Literal": { "Value": "true" } } },
            "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": 0.6 } } } } },
            "horizontalAlignment": { "expr": { "Literal": { "Value": "'center'" } } }
          }
        }
      ],
      "totals": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "backgroundColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.5 } } } } },
            "backgroundTransparency": { "expr": { "Literal": { "Value": "68D" } } }
          }
        },
        {
          "properties": {
            "color": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } }
          },
          "selector": {
            "data": [{ "dataViewWildcard": { "matchingOption": 1 } }]
          }
        }
      ],
      "zoom": [
        {
          "properties": {
            "show": { "expr": { "Literal": { "Value": "true" } } },
            "showLabels": { "expr": { "Literal": { "Value": "false" } } }
          }
        }
      ]
    }
  }
}
```

### Line Chart with Y2 Secondary Axis and Per-Series Styling

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 705, "y": 0, "z": 1, "height": 591, "width": 575, "tabOrder": 1 },
  "visual": {
    "visualType": "lineChart",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Year"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Year",
              "nativeQueryRef": "Ship Date Year",
              "active": true
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Quarter"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Quarter",
              "nativeQueryRef": "Ship Date Quarter",
              "active": false
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Month"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Month",
              "nativeQueryRef": "Ship Date Month",
              "active": false
            },
            {
              "field": {
                "HierarchyLevel": {
                  "Expression": {
                    "Hierarchy": {
                      "Expression": {
                        "PropertyVariationSource": {
                          "Expression": { "SourceRef": { "Entity": "ListOfOrders" } },
                          "Name": "Variation",
                          "Property": "Ship Date"
                        }
                      },
                      "Hierarchy": "Date Hierarchy"
                    }
                  },
                  "Level": "Day"
                }
              },
              "queryRef": "ListOfOrders.Ship Date.Variation.Date Hierarchy.Day",
              "nativeQueryRef": "Ship Date Day",
              "active": false
            }
          ]
        },
        "Y": {
          "projections": [{
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Profit" } }, "Function": 0 } },
            "queryRef": "Sum(OrderBreakdown.Profit)",
            "nativeQueryRef": "Sum of Profit"
          }]
        },
        "Y2": {
          "projections": [{
            "field": { "Aggregation": { "Expression": { "Column": { "Expression": { "SourceRef": { "Entity": "OrderBreakdown" } }, "Property": "Quantity" } }, "Function": 0 } },
            "queryRef": "Sum(OrderBreakdown.Quantity)",
            "nativeQueryRef": "Sum of Quantity"
          }]
        }
      }
    },
    "objects": {
      "categoryAxis": [{
        "properties": {
          "axisType": { "expr": { "Literal": { "Value": "'Categorical'" } } },
          "titleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 4, "Percent": -0.25 } } } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } }
        }
      }],
      "valueAxis": [{
        "properties": {
          "logAxisScale": { "expr": { "Literal": { "Value": "true" } } },
          "invertAxis": { "expr": { "Literal": { "Value": "true" } } },
          "labelDisplayUnits": { "expr": { "Literal": { "Value": "1000D" } } },
          "gridlineStyle": { "expr": { "Literal": { "Value": "'custom'" } } },
          "gridlineDashArray": { "expr": { "Literal": { "Value": "'5 5 0 10 20'" } } },
          "gridlineThickness": { "expr": { "Literal": { "Value": "2D" } } }
        }
      }],
      "y2Axis": [{
        "properties": {
          "secLabelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 3, "Percent": 0.2 } } } } },
          "secTitleColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } }
        }
      }],
      "lineStyles": [
        {
          "properties": {
            "strokeWidth": { "expr": { "Literal": { "Value": "5D" } } },
            "lineChartType": { "expr": { "Literal": { "Value": "'step'" } } },
            "interpolationStep": { "expr": { "Literal": { "Value": "'after'" } } },
            "showMarker": { "expr": { "Literal": { "Value": "true" } } },
            "markerShape": { "expr": { "Literal": { "Value": "'diamond'" } } },
            "markerSize": { "expr": { "Literal": { "Value": "9D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
        },
        {
          "properties": {
            "lineStyle": { "expr": { "Literal": { "Value": "'dashed'" } } },
            "strokeWidth": { "expr": { "Literal": { "Value": "4D" } } },
            "lineChartType": { "expr": { "Literal": { "Value": "'smooth'" } } },
            "interpolationSmooth": { "expr": { "Literal": { "Value": "'cardinal'" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Quantity)" }
        },
        {
          "properties": {
            "areaShow": { "expr": { "Literal": { "Value": "true" } } },
            "showMarker": { "expr": { "Literal": { "Value": "true" } } }
          }
        }
      ],
      "dataPoint": [
        {
          "properties": {
            "fill": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 5, "Percent": 0.2 } } } } },
            "transparency": { "expr": { "Literal": { "Value": "76D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Profit)" }
        },
        {
          "properties": {
            "transparency": { "expr": { "Literal": { "Value": "59D" } } }
          },
          "selector": { "metadata": "Sum(OrderBreakdown.Quantity)" }
        }
      ],
      "legend": [{
        "properties": {
          "legendMarkerRendering": { "expr": { "Literal": { "Value": "'lineAndMarker'" } } },
          "labelColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 6, "Percent": -0.25 } } } } },
          "titleText": { "expr": { "Literal": { "Value": "'Line Chart'" } } }
        }
      }],
      "zoom": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "showOnValueSecAxis": { "expr": { "Literal": { "Value": "true" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```
