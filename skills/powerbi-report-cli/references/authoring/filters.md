# Filters authoring Workflows & Examples

> Referenced from SKILL.md. Read this when creating or modifying filters
> For reference of expressions, see **references/authoring/expressions.md**
>
> **For filter pane and filter card appearance** (collapse panel colors,
> fonts, Applied/Available state styling, pane width) — these are stored in
> `page.json → objects.outspacePane` / `filterCard`, separate from the
> `filterConfig` definitions covered below. See
> [`filter-pane.md`](filter-pane.md).

## Add a Filter

Filters exist at three levels: report (`report.json`), page (`page.json`),
and visual (`visual.json`). All use the same `filterConfig.filters` array.

### Filter Types
| Type | Description |
|------|-------------|
| `Categorical` | Discrete value selection (in-list) |
| `Range` | Numeric or date range |
| `Advanced` | Custom condition expressions |
| `TopN` | Top/Bottom N by measure |
| `RelativeDate` | Relative date (e.g. "Last 30 days") |
| `RelativeTime` | Relative time range |
| `Exclude` | Exclude specific data point |
| `Include` | Include specific data point |

### Categorical Filter (In-list)
```json
{
  "name": "Filter<24hexchars>",
  "field": {
    "Column": {
      "Expression": { "SourceRef": { "Entity": "<Table>" } },
      "Property": "<Column>"
    }
  },
  "type": "Categorical",
  "filter": {
    "Version": 2,
    "From": [
      { /* Entity Source Expression */ }
    ],
    "Where": [
      {
        "Condition": {
          /* In Expression */
        }
      }
    ]
  },
  "howCreated": "User" // must have
}
```
**⚠️ Critical**: Inside a `filter.Where` condition, `SourceRef` uses `"Source"` 
(the alias from `From`), NOT `"Entity"`. The `field` property at the top level
uses `"Entity"`. `powerbi-report-author validate` flags entity refs that
slip into `Where` with `PBIR_FILTER_ENTITY_IN_WHERE`. To inventory every filter
defined in a report (report / page / visual scopes), run
`powerbi-report-author preview-filters <path-to-.Report-dir>`. Each
entry returns `{ path, scope, name, type, displayName?, isHiddenInViewMode?,
isLockedInViewMode? }` only — open the file at `path` to inspect the actual
predicates (`filter.Where`), `From` sources, and `howCreated`.

### Inverted Selection (Exclude)

To exclude values (inverted selection), **two** changes are required:

1. **Filter condition** — wrap the `In` expression with `Not` in the `Where` clause:
```json
"Where": [
  {
    "Condition": {
      "Not": {
        "Expression": {
          "In": {
            "Expressions": [{ /* Column Expression */ }],
            "Values": [
              [{ "Literal": { "Value": "<excluded-value>" } }]
            ]
          }
        }
      }
    }
  }
]
```

2. **Slicer interaction state** — set `isInvertedSelectionMode` in the slicer's
   `objects.data` so Desktop knows future checkbox clicks should subtract from
   an "all selected" base state:
```json
"objects": {
  "data": [{
    "properties": {
      "isInvertedSelectionMode": {
        "expr": { "Literal": { "Value": "true" } }
      }
    }
  }]
}
```

### Exclude/Include Filter
```json
{
  "name": "Filter<24hexchars>",
  "type": "Include", // Will be "Exclude" for exclude filter
  "filter": {
    "Version": 2,
    "From": [
      {
        /* Entity Source Expression */
      }
    ],
    "Where": [
      {
        "Condition": {
          "In": {
            "Expressions": [
              {
                /* Column Expression */
              }
            ],
            "Values": [
              [
                {
                  "Literal": {
                    "Value": "<Value>"
                  }
                }
              ]
            ]
          }
        }
      }
    ]
  },
  "howCreated": "Include" // Will be "Exclude" for exclude filter
}
```

### Range Filter
```json
{
  "name": "Filter<24hexchars>",
  "field": { /* Column expression */ },
  "type": "Advanced",
  "filter": {
    "Version": 2,
    "From": [{ /* Entity Source Expression */ }],
    "Where": [{
      "Condition": {
        "Between": {
          "Expression": {
            "Column": {
              "Expression": { "SourceRef": { "Source": "<alias>" } },
              "Property": "<Column>"
            }
          },
          "LowerBound": { "Literal": { "Value": "100D" } },
          "UpperBound": { "Literal": { "Value": "500D" } }
        }
      }
    }]
  },
  "howCreated": "User" // must have
}
```

### Advanced Filter
Uses logical operators (AND/OR) and comparison operators (e.g., contains, greater than, before) to dynamically include or exclude data

```json
{
  "name": "Filter<24hexchars>",
  "field": { /* Column expression */ },
  "type": "Advanced",
  "filter": {
    "Version": 2,
    "From": [{ /* Entity Source Expression */ }],
    "Where": [{
      "Condition": {
        "And": {
            "Left": { /* Comparison/Not/Contains/StartsWith Expression */},
            "Right": {/* Comparison/Not/Contains/StartsWith Expression */}
        }
      }
    }]
  },
  "howCreated": "User" // must have
}
```
Condition can be And/Or.

### TopN Filter
```json
{
  "name": "Filter<24hexchars>",
  "field": {
    "Column": {
      "Expression": {
        "SourceRef": {
          "Entity": "<Table>"
        }
      },
      "Property": "<Column>"
    }
  },
  "type": "TopN",
  "filter": {
    "Version": 2,
    "From": [
      {
        "Name": "subquery",
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
                  "Column": {
                    /* Column Expression */
                  },
                  "Name": "field"
                }
              ],
              "OrderBy": [
                {
                  "Direction": 2,
                  "Expression": {
                    /* Aggregation Expression */
                  }
                }
              ],
              "Top": 5
            }
          }
        },
        "Type": 2
      },
      {
        "Name": "<alias>",
        "Entity": "<Table>",
        "Type": 0
      }
    ],
    "Where": [
      {
        "Condition": {
          "In": {
            "Expressions": [
              {
                /* Column Expression */
              }
            ],
            "Table": {
              "SourceRef": {
                "Source": "subquery"
              }
            }
          }
        }
      }
    ]
  },
  "howCreated": "User" // must have
}
```
**⚠️ Critical:**
- TopN filter can only be added as a **visual-level** filter — not page-level or report-level.
- It can only be applied on a normal column or measure field.
- The `OrderBy.Expression` **must use an `Aggregation` expression** (wrapping a Column
  with a function like Sum/Count), **not a `Measure` expression**. Using a Measure
  reference in the subquery's OrderBy causes a Desktop error:
  `Cannot read properties of undefined (reading 'accept')` in `SemanticQueryRewriter.rewriteOrderBy`.
- Direction value: `1` = Bottom, `2` = Top.

### Relative Date/Time filter
``` json
{
  "name": "Filter<24hexchars>",
  "field": {
    "Column": {
      "Expression": {
        "SourceRef": {
          "Entity": "<Table>"
        }
      },
      "Property": "<Column>"
    }
  },
  "type": "RelativeDate", // "RelativeTime" for relative time filter only targeting hours/minutes/seconds
  "filter": {
    "Version": 2,
    "From": [
      {
        /* Entity Source Expression */
      }
    ],
    "Where": [
      {
        "Condition": {
          "Between": {
            "Expression": {
              "Column": {
                "Expression": {
                  "SourceRef": {
                    "Source": "<alias>"
                  }
                },
                "Property": "<Column>"
              }
            },
            "LowerBound": {
              "DateSpan": {
                "Expression": {
                  "DateAdd": {
                    "Expression": {
                      "DateAdd": {
                        "Expression": {
                          "Now": {}
                        },
                        "Amount": 1,
                        "TimeUnit": 0
                      }
                    },
                    "Amount": -10,
                    "TimeUnit": 3
                  }
                },
                "TimeUnit": 0
              }
            },
            "UpperBound": {
              "DateSpan": {
                "Expression": {
                  "Now": {}
                },
                "TimeUnit": 0
              }
            }
          }
        }
      }
    ]
  },
  "howCreated": "User" // must have
}
```
TimeUnit values: `0`=Day, `1`=Week, `2`=Month, `3`=Year, `4`=Decade, `5`=Second, `6`=Minute, `7`=Hour

## References
Type value inside of the From array in the filter template: `0`=Table
