# Textbox Visual Authoring Guide

Use `textbox` for visible static page titles, headers, annotations, and dynamic
text values. Textboxes require a **native `paragraphs` array** directly under
`objects.general[].properties.paragraphs`; do not wrap it as
`{ "paragraphs": [...] }` and do not stringify the JSON. The wrapped object form
can validate but render invisible text in Desktop.

> Examples use illustrative `<table>.<measure>` identifiers — substitute your own.

## Static textbox title

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 60, "width": 520, "tabOrder": 0 },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [
        {
          "properties": {
            "paragraphs": [
              {
                "textRuns": [
                  {
                    "value": "Sales Overview",
                    "textStyle": {
                      "fontFamily": "Segoe UI Semibold",
                      "fontSize": "24px",
                      "color": "#FFFFFF"
                    }
                  }
                ],
                "horizontalTextAlignment": "left"
              }
            ]
          }
        }
      ]
    },
    "visualContainerObjects": {
      "background": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "border": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "padding": [{
        "properties": {
          "top": { "expr": { "Literal": { "Value": "0D" } } },
          "bottom": { "expr": { "Literal": { "Value": "0D" } } },
          "left": { "expr": { "Literal": { "Value": "0D" } } },
          "right": { "expr": { "Literal": { "Value": "0D" } } }
        }
      }]
    }
  }
}
```

## Dynamic textbox value

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 0, "height": 50, "width": 300, "tabOrder": 0 },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [{
        "properties": {
          "paragraphs": [
            {
              "textRuns": [
                {
                  "value": {
                    "propertyIdentifier": {
                      "objectName": "values",
                      "propertyName": "expr"
                    },
                    "selector": {
                      "id": "Value 3"
                    }
                  },
                  "textStyle": {
                    "fontFamily": "Arial Black",
                    "fontSize": "20pt",
                    "fontWeight": "bold",
                    "color": "#118DFF"
                  }
                }
              ],
              "horizontalTextAlignment": "left",
              "listType": "bullet",
              "indent": 1
            }
          ]
        }
      }],
      "values": [{
        "properties": {
          "expr": {
            "expr": {
              "Min": {
                "Expression": {
                  "Column": {
                    "Expression": {
                      "Subquery": {
                        "Query": {
                          "Version": 2,
                          "From": [
                            {
                              /* Entity Source Expression */
                            }
                          ],
                          "Select": [
                            {
                              "Aggregation": {
                                /* Aggregation Expression */
                              },
                              "Name": "Sum(Sales.SalesTax)"
                            }
                          ],
                          "Where": [
                            {
                              "Condition": {
                                /* Not/Comparison Expressions */
                              }
                            }
                          ]
                        }
                      }
                    },
                    "Property": "Sum(Sales.SalesTax)"
                  }
                },
                "IncludeAllTypes": 1
              },
              "Annotations": {
                "NaturalLanguage": {
                  "version": 1,
                  "kind": "NaturalLanguage",
                  "annotation": {
                    "name": "Value 3",
                    "utterance": "Sum SalesTax (column 20)"
                  }
                }
              }
            }
          }
        },
        "selector": {
          "id": "Value 3"
        }
      }]
    }
  }
}
```

## Rules

- `paragraphs` is a **native JSON array** directly under the `paragraphs`
  property — NOT a stringified JSON literal and NOT an object wrapper
  containing another `paragraphs` key. The wrapped form can validate but
  render invisible text in Desktop.
- Each paragraph has `textRuns` plus optional `horizontalTextAlignment`,
  `listType`, and `indent`.
- Font sizes can use CSS units such as `"24px"` for static title text, or `pt`
  units such as `"40pt"` / `"12pt"`. Preserve existing units when editing.
- For static text, `textRuns[].value` is a plain string.
- For dynamic values, `textRuns[].value` is an object and the matching
  `values` expression is required.
