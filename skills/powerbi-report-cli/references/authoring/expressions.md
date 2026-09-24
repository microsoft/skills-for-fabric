# Expressions — Semantic Query Trees

## Contents

- [Expression Tree Templates](#expression-tree-templates)
  - [Entity Source Expression](#entity-source-expression)
  - [Column Expression](#column-expression)
  - [Measure Expression](#measure-expression)
  - [NativeVisualCalculation Expression](#nativevisualcalculation-expression)
  - [NativeMeasure Expression](#nativemeasure-expression)
  - [Hierarchy Level Expression](#hierarchy-level-expression)
  - [Aggregation Expression](#aggregation-expression)
  - [ScopedEval Expression](#scopedeval-expression)
  - [Comparison Expression](#comparison-expression)
  - [Not Expression](#not-expression)
  - [Contains/StartsWith Expression](#containsstartswith-expression)
  - [In Expression](#in-expression)
  - [Visual Query Projection](#visual-query-projection)
  - [Sort Definition](#sort-definition)
  - [Expansion state](#expansion-state)
- [Filters](#filters)


> Referenced from SKILL.md. Read this for expression tree templates used in
> visual queries (`queryState`) and sort definitions. For **filter** templates
> (Categorical, Range, etc.), see **references/authoring/filters.md § Add a Filter**.

## Expression Tree Templates

All data field references in `queryState`, `filterConfig`, and `sortDefinition`
use the Semantic Query expression tree format. These are the canonical patterns.

### Entity Source Expression
Expression references a table(entity) in the semantic model:
```json
{
  "Name": "<alias>",
  "Entity": "<Table>",
  "Type": 0
}
```

### Column Expression
Expression references a column from a table (entity) in the semantic model:
```json
{
  "Column": {
    "Expression": {
      "SourceRef": { "Entity": "<TableName>" }
    },
    "Property": "<ColumnName>"
  }
}
```

### Measure Expression
Expression references a measure defined in the semantic model:
```json
{
  "Measure": {
    "Expression": {
      "SourceRef": { "Entity": "<TableName>" }
    },
    "Property": "<MeasureName>"
  }
}
```

### NativeVisualCalculation Expression

A visual calculation is DAX embedded directly in one visual's query. It exists
only on that visual and can be customized without creating a semantic-model
measure.

Add the calculation as another projection in the same query role as its input:

```json
"Y": {
  "projections": [
    {
      "field": {
        "Measure": {
          "Expression": {
            "SourceRef": {
              "Entity": "Expenditure Statistics"
            }
          },
          "Property": "Arrivals per month"
        }
      },
      "queryRef": "Expenditure Statistics.Arrivals per month",
      "nativeQueryRef": "Arrivals per month"
    },
    {
      "field": {
        "NativeVisualCalculation": {
          "Language": "dax",
          "Expression": "MOVINGAVERAGE([Arrivals per month], 3)",
          "Name": "Moving average"
        }
      },
      "queryRef": "select",
      "nativeQueryRef": "Moving average"
    }
  ]
}
```

Power BI Desktop visual-calculation functions include:

- `RUNNINGSUM()`
- `MOVINGAVERAGE()`
- `PREVIOUS()`
- `NEXT()`
- `FIRST()`
- `LAST()`
- `RANGE()`
- `EXPAND()`
- `COLLAPSE()`

Rules:

- `Language` must be `"dax"`.
- `Expression` contains the visual-calculation DAX.
- `Name` is the calculation's display name and should match
  `nativeQueryRef`.
- The calculation can reference only columns, measures, or calculations already
  projected on the same visual.
- It cannot be reused by another visual or referenced by semantic-model
  measures.
- Relationship-dependent functions such as `RELATED`, `RELATEDTABLE`, and
  `USERELATIONSHIP` are not supported.

### NativeMeasure Expression

An inline DAX expression embedded directly in the report query. Unlike
`Measure`, it does not reference an existing semantic-model measure.

```json
{
  "NativeMeasure": {
    "Language": "dax",
    "Expression": "\"Sales for \" & SELECTEDVALUE('Date'[Year])",
    "DataType": 1,
    "ProposedName": "Dynamic Title"
  }
}
```

Rules:

- `Language` must be `"dax"`.
- `Expression` contains the DAX expression.
- `DataType` declares the expected result type.
- Use a text-returning expression for `title.text`.
- Support depends on the host/query pipeline; referencing a model `Measure` is
  generally safer.

### Hierarchy Level Expression
```json
{
  "HierarchyLevel": {
    "Expression": {
      "Hierarchy": {
        "Expression": {
          "SourceRef": { "Entity": "<TableName>" }
        },
        "Hierarchy": "<HierarchyName>"
      }
    },
    "Level": "<LevelName>"
  }
}
```

### Aggregation Expression
Wraps a column with an aggregation function:
```json
{
  "Aggregation": {
    "Expression": {
      "Column": {
        "Expression": {
          "SourceRef": { "Entity": "<TableName>" }
        },
        "Property": "<ColumnName>"
      }
    },
    "Function": 0
  }
}
```
Aggregation Function values: `0`=Sum, `1`=Avg, `2`=Count, `3`=Min, `4`=Max,
`5`=CountNonNull, `6`=Median, `7`=StdDev, `8`=Var

### ScopedEval Expression

Evaluates an expression at a specific grouping scope rather than the visual's
default scope.

```json
{
  "ScopedEval": {
    "Expression": {
      "Measure": {
        "Expression": {
          "SourceRef": {
            "Entity": "Sales"
          }
        },
        "Property": "Dynamic Title"
      }
    },
    "Scope": [
      {
        "Column": {
          "Expression": {
            "SourceRef": {
              "Entity": "Geography"
            }
          },
          "Property": "Region"
        }
      }
    ]
  }
}
```

Rules:

- `Expression` is the value being evaluated.
- `Scope` is a non-empty array of column expressions only.
- The scope columns must be available to the visual query.
- It is mainly useful for matrix/grouped data and conditional formatting.
- For an ordinary dynamic visual title, use a model `Measure`; use `ScopedEval`
  only when evaluation at a particular grouping level is required.

### Comparison Expression
Expression compares between two values
```json
{
  "Comparison": {
    "ComparisonKind": 0,
    "Left": {
      /* column/hierarchy/measure expression */
    },
    "Right": {
      "Literal": {
        "Value": "<Value>" /* "null" for blank value, "''" for empty text only value */
      }
    }
  }
}
```

ComparisonKind values: `0`=Equal, `1`=GreaterThan, `2`=GreaterThanOrEqual, `3`=LessThan, `4`=LessThanOrEqual

### Not Expression

```json
{
  "Not": {
    "Expression": {
      /* Comparison/Contains/StartsWith/In expression */
    }
  }
}
```
"Not" with "GreaterThan" equals "LessThanOrEqual"

### Contains/StartsWith Expression

```json
{
  "Contains": { /* StartsWith for StartsWith Expression */
    "Left": {
      /* column/hierarchy/measure expression */
    },
    "Right": {
      "Literal": {
        "Value": "<Value>"
      }
    }
  }
}
```
Only available for text value

### In Expression

```json
{
  "In": {
    "Expressions": [
      {
        "Column": {
          "Expression": { "SourceRef": { "Source": "<alias>" } },
          "Property": "<Column>"
        }
      }
    ],
    "Values": [
      [{ "Literal": { "Value": "'<value>'" } }],
      [{ "Literal": { "Value": "'<value2>'" } }]
    ]
  }
}
```

### Visual Query Projection
Each field well role contains an array of projections. Each projection binds a
data field to the visual:
```json
{
  "field": { /* Column/Measure/Aggregation/Hierarchy expression from above */ },
  "queryRef": "<Entity>.<Property>",
  "nativeQueryRef": "<Property>",
  "active": true
}
```
- `queryRef`: Unique per visual. Format: `Entity.Property` for simple refs.
  For aggregated columns: `CountNonNull(Entity.Property)` etc.
- `nativeQueryRef`: Usually the Property name. If duplicated across roles,
  append a number (e.g. `Sales1`).
- `active`: Only used in drill hierarchies. The currently active level is `true`.

### Sort Definition

`sortDefinition` is a property of the **`query`** object
(`visual.query.sortDefinition`). Supported in all schema versions (2.2.0+).
Use it to sort bar charts by value descending so "Top N" charts display
correctly.

```json
// Add inside: visual.query (sibling of queryState)
"sortDefinition": {
  "sort": [
    {
      "field": { /* Column or Measure expression */ },
      "direction": "Descending"
    }
  ],
  "isDefaultSort": false
}
```

- Direction values: `"Ascending"` or `"Descending"`.
- `isDefaultSort`: When `false`, Power BI treats this as user-explicit and
  won't auto-override it. When `true` or omitted, Power BI may change the
  sort to match the visual type's default.

**Known Limitations:**
- `sortDefinition` controls sort order of the **measure values**, not the
  category axis order. Text-based categories (e.g., Month Name, Quarter
  Name) always sort **alphabetically** regardless of `sortDefinition`.
  "April" comes before "January" because "A" < "J".
- To get chronological order on a time axis, use a **Date column** or
  **numeric column** (Month Number, Quarter Number) as the Category —
  never text month/quarter names.
- If the semantic model has `sortByColumn` configured on a text column
  (e.g., Month Name sorted by Month Number), PBI respects that. But
  `sortDefinition` in PBIR cannot create or override `sortByColumn` —
  it must exist in the TMDL model definition.

---

### Expansion state

Expansion state describes which nodes in a hierarchy are expanded or collapsed. It is only used when a visual has hierarchy structure (e.g., a matrix with Row or Column hierarchies, or a hierarchy slicer). If the visual has no hierarchy structure, omit `expansionStates` entirely.

- **`roles`** — which query roles contain the hierarchy (e.g., `["Rows"]` for a matrix, `["Values"]` for a slicer)
- **`levels`** — one entry per hierarchy level; `queryRefs` must match a `queryRef` in the visual's query; `identityKeys` reference the field expressions; `isCollapsed` / `isPinned` control the default UI state
- **`root.children`** — records which specific data values the user has toggled open; each child has `identityValues` (literal values identifying the node) and `isToggled: true`; nested `children` represent deeper expansions

```json
{
  "expansionStates": [ // Defines the specific data points that are expanded
    {
      "roles": [
        "Values"
      ],
      "levels": [
        {
          "queryRefs": [ // Which fields in the query does this relate to - must match a queryRef in the query above
            "Brand.BrandName"
          ],
          "isCollapsed": true,
          "identityKeys": [
            {
              /* Hierarchy level/Column/Measure/Aggregation expressions from the expression in the query above*/
            }
          ],
          "isPinned": true
        },
      ],
      "root": { // Defines the specific values that are expanded for each field in the hierarchy
        "children": [
          {
            "identityValues": [
              {
                "Literal": {
                  "Value": "'A. Datum'"
                }
              }
            ],
            "isToggled": true,
            "children": [
              {
                "identityValues": [
                  {
                    "Literal": {
                      "Value": "'N'"
                    }
                  }
                ],
                "isToggled": true
              }
            ]
          },
          {
            "identityValues": [
              {
                "Literal": {
                  "Value": "null"
                }
              }
            ],
            "isToggled": true,
            "children": [
              {
                "identityValues": [
                  {
                    "Literal": {
                      "Value": "null"
                    }
                  }
                ],
                "isToggled": true
              }
            ]
          }
        ]
      }
    }
  ]
}
```

## Filters

Filter templates (Categorical, Range, Inverted, TopN, etc.) are in
**references/authoring/filters.md § Add a Filter**. Expression trees above (Column, Measure,
Aggregation) are used inside filter `field` and `Where` conditions.
