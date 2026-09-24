# Slicer Authoring Guide - Part 2

## Contents

  - [Calendar Date Picker Templates](#calendar-date-picker-templates)
  - [Date Between Slicer Template](#date-between-slicer-template)
- [Add/Modify a Slicer](#addmodify-a-slicer)
  - [Slicer types](#slicer-types)
  - [Setting slicer selections](#setting-slicer-selections)
- [Slicer Sync Groups](#slicer-sync-groups)
- [Theme Approach](#theme-approach)
- [Discovering Properties](#discovering-properties)


Continuation of `slicers.md`. Open this file directly from the skill reference index.

### Calendar Date Picker Templates

Bind exactly one renderable Date/DateTime column to `Values`.

Use `RelativeDatePicker` for the calendar-style Date Picker. It supports two
selection methods:

- **Manual** — select an explicit start and end date on the calendar. Author
  either an unselected state or a fixed preselected range.
- **Relative** — select a rolling range such as Last 30 Days or Last 13 Years.

Keep `data.mode` set to `RelativeDatePicker` for both methods. The stored
properties and filter expression determine the active selection method and
value.
Do not substitute `Between` or `Relative`; those values author different
compact slicer styles without the two-tab Date Picker UI.

#### Resolve the date field and preselection

Delegate semantic-model discovery to the semantic-model authoring skill or
available modeling MCP server. Ask it to return a renderable Date/DateTime
column and the exact table/column identity needed by the report query. For a
fixed Manual preselection, also request the live minimum and maximum nonblank
dates; for a Relative preselection, provide the requested business period so
the model workflow can confirm that it intersects available data.

Use the verified field identity and date values returned by that capability in
the report templates below; semantic-model inspection and DAX-query procedures
remain owned by the semantic-model capability. If no model capability is
available, author the unselected Manual state or ask the user to provide the
date field and intended range.

Start from the base slicer template and set:

```json
"data": [{
  "properties": {
    "mode": { "expr": { "Literal": { "Value": "'RelativeDatePicker'" } } }
  }
}]
```

#### Manual

Omit `general.filter`, `data.startDate`, and `data.endDate` to author Manual
with no preselection.

To author Manual with a fixed inclusive range, add matching `startDate` and
`endDate` literals to the `data` entry and add a matching
`general.filter`. Encode the exclusive filter upper bound as the day after
`endDate`:

```json
"data": [{
  "properties": {
    "mode": { "expr": { "Literal": { "Value": "'RelativeDatePicker'" } } },
    "startDate": { "expr": { "Literal": { "Value": "datetime'2014-01-01T00:00:00'" } } },
    "endDate": { "expr": { "Literal": { "Value": "datetime'2014-06-30T00:00:00'" } } }
  }
}],
"general": [{
  "properties": {
    "filter": {
      "filter": {
        "Version": 2,
        "From": [{ "Name": "d", "Entity": "<table>", "Type": 0 }],
        "Where": [{
          "Condition": {
            "And": {
              "Left": {
                "Comparison": {
                  "ComparisonKind": 2,
                  "Left": {
                    "Column": {
                      "Expression": { "SourceRef": { "Source": "d" } },
                      "Property": "<date_column>"
                    }
                  },
                  "Right": { "Literal": { "Value": "datetime'2014-01-01T00:00:00'" } }
                }
              },
              "Right": {
                "Comparison": {
                  "ComparisonKind": 3,
                  "Left": {
                    "Column": {
                      "Expression": { "SourceRef": { "Source": "d" } },
                      "Property": "<date_column>"
                    }
                  },
                  "Right": { "Literal": { "Value": "datetime'2014-07-01T00:00:00'" } }
                }
              }
            }
          }
        }]
      }
    }
  }
}]
```

#### Relative

To author Relative with a preselection, keep `mode: 'RelativeDatePicker'`, add
the relative controls to `data`, add
`dateRange.includeToday`, and add a matching relative `general.filter`. Keep
`relativeDuration` and the negative `DateAdd` amount synchronized. Set that
negative `DateAdd.TimeUnit` to the selected period, but keep both enclosing
`DateSpan.TimeUnit` values at `0`:

```json
"data": [{
  "properties": {
    "mode": { "expr": { "Literal": { "Value": "'RelativeDatePicker'" } } },
    "relativeRange": { "expr": { "Literal": { "Value": "'Last'" } } },
    "relativePeriod": { "expr": { "Literal": { "Value": "'Days'" } } },
    "relativeDuration": { "expr": { "Literal": { "Value": "30D" } } }
  }
}],
"dateRange": [{
  "properties": {
    "includeToday": { "expr": { "Literal": { "Value": "true" } } }
  }
}],
"general": [{
  "properties": {
    "filter": {
      "filter": {
        "Version": 2,
        "From": [{ "Name": "d", "Entity": "<table>", "Type": 0 }],
        "Where": [{
          "Condition": {
            "Between": {
              "Expression": {
                "Column": {
                  "Expression": { "SourceRef": { "Source": "d" } },
                  "Property": "<date_column>"
                }
              },
              "LowerBound": {
                "DateSpan": {
                  "Expression": {
                    "DateAdd": {
                      "Expression": {
                        "DateAdd": {
                          "Expression": { "Now": {} },
                          "Amount": 1,
                          "TimeUnit": 0
                        }
                      },
                      "Amount": -30,
                      "TimeUnit": 0
                    }
                  },
                  "TimeUnit": 0
                }
              },
              "UpperBound": {
                "DateSpan": {
                  "Expression": { "Now": {} },
                  "TimeUnit": 0
                }
              }
            }
          }
        }]
      }
    }
  }
}]
```

For the negative `DateAdd`, use `TimeUnit` `0` for days, `1` for weeks, `2`
for months, and `3` for years. Set `relativePeriod` to the matching `Days`,
`Weeks`, `Months`, or `Years` value. Do not apply that period unit to
`DateSpan.TimeUnit`; Desktop stores both `DateSpan` wrappers with value `0`.
Use the relative-filter expression variants in
filters.md § Relative Date/Time filter (see `filters.md`, section `relative-datetime-filter`)
for other periods and directions.

Size `RelativeDatePicker` at `w >= 280, h >= 240`.

---

### Date Between Slicer Template

Use the `slicer` visual in `Between` mode only when
users need arbitrary date-range exploration and the bound field is a renderable
Date/DateTime column. For executive dashboards or annual/quarterly grain,
prefer a compact Year/Period dropdown or tile.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<unique-id>",
  "position": { "x": 1040, "y": 8, "z": 1000, "height": 104, "width": 216, "tabOrder": 1000 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "<table>" } }, "Property": "<date_column>" } },
            "queryRef": "<table>.<date_column>",
            "nativeQueryRef": "<date_column>"
          }]
        }
      }
    },
    "objects": {
      "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Between'" } } } } }],
      "header": [{ "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "text": { "expr": { "Literal": { "Value": "'Date Range'" } } }
      }}]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": {
        "top":    { "expr": { "Literal": { "Value": "8D" } } },
        "bottom": { "expr": { "Literal": { "Value": "8D" } } },
        "left":   { "expr": { "Literal": { "Value": "8D" } } },
        "right":  { "expr": { "Literal": { "Value": "8D" } } }
      }}]
    }
  }
}
```

**Sizing**:
- Compact: **`w=216, h = 84 + top + bottom`** — dates stack vertically.
  With theme default `8/8` padding, snap `100` up to the 8px grid and use
  **`h=104`**.
- Wider layouts may render dates side-by-side. Do not assume a fixed threshold;
  validate the target Desktop build by screenshot and use
  **`h = 60 + top + bottom`** only after both inputs visibly share one row.

Fill and light variants are the same as the dropdown slicer (see above).

---

## Add/Modify a Slicer

### Slicer types

| Type | `visualType` | Query roles | `data.mode` | Notes |
|------|-------------|-------------|-------------|-------|
| **Dropdown** | `slicer` | `Values` only (Column/Hierarchy) | `'Dropdown'` | Any cardinality, compact; default for executive Year/Period filters |
| **Date Picker** | `slicer` | `Values` only (Date/DateTime column) | `'RelativeDatePicker'` | Calendar-style picker; supports Manual and Relative selection |
| **Compact date range** | `slicer` | `Values` only (Date/DateTime column) | `'Between'` | Side-by-side or stacked date bounds without the calendar picker |
| **Single** | `slicer` | `Values` only (Column) | `'Single'` | Single-select |
| **Before** | `slicer` | `Values` only (Date/Numeric) | `'Before'` | Upper bound only (≤) |
| **After** | `slicer` | `Values` only (Date/Numeric) | `'After'` | Lower bound only (≥) |
| **Relative date control** | `slicer` | `Values` only (Date column) | `'Relative'` | Compact "Last N days/months/years" control; use `RelativeDatePicker` when the calendar-style picker is required |
| **Relative time** | `slicer` | `Values` only (DateTime column) | `'RelativeTime'` | "Last N minutes/hours" — uses `data.relativeTimePeriod` instead of `relativePeriod` |
| **Scrollable list** | `listSlicer` | `Values` (Column/Hierarchy), `Tooltips` (Measure/Aggregation) | — | Default for list-style slicers. `data.mode` not available. |
| **Button/tile** | `advancedSlicerVisual` | `Values` (1 Column only), `Label` (1 Measure, optional), `Tooltips` (Aggregations) | — | ≤10 values, tile layout. `data.mode` not available. |

**Temporal decision matrix:**

| Signal | Use |
|---|---|
| Executive page, annual grain, ≤10 years | Year dropdown or year tile |
| Discrete period comparison (e.g., 2020 vs 2023) | Year/month dropdown with multi-select |
| Month/quarter reporting with 12-36 periods | Period dropdown or relative date |
| Calendar-based day/month range exploration on Date/DateTime field | `RelativeDatePicker` |
| Compact lower/upper date bounds | `Between` |
| Integer/text date key or date picker does not render | Year/Period dropdown |

**Constraints:**
- `data.mode` is only available on the classic `slicer` visual — not on
  `listSlicer` or `advancedSlicerVisual`.
- `advancedSlicerVisual` allows only **one field** in `Values`.
- Hierarchy slicers: only `slicer` (mode: Basic/Dropdown) and `listSlicer`
  support hierarchies. Add `expansionStates` for expanded nodes (see
  expressions.md).
- A full-date column does not automatically require a Date Picker. Use a
  Year/Period dropdown or tile for annual/quarterly executive pages,
  `RelativeDatePicker` for calendar-based exploration, and `Between` for compact
  lower/upper bounds.

### Setting slicer selections

The `general.filter` property in `objects` controls which values are
selected. This is only needed when pre-selecting specific values — omit
it entirely for the default "All" state.

```json
"general": [{
  "properties": {
    "orientation": { "expr": { "Literal": { "Value": "0D" } } },
    "filter": {
      "filter": {
        "Version": 2,
        "From": [
          { "Name": "d", "Entity": "dim_company", "Type": 0 }
        ],
        "Where": [{
          "Condition": { /* filter expression — see expressions.md */ },
          "Annotations": {
            "filterExpressionMetadata": {
              "expressions": [{ /* Column Expression for the filtered field */ }],
              "decomposedIdentities": {
                "values": [[
                  { "0": [{ "Literal": { "Value": "'A. Datum'" } }] },
                  { "1": [{ "Literal": { "Value": "'N'" } }] },
                  { "2": [{ "Literal": { "Value": "5L" } }] },
                  { "3": [{ "Literal": { "Value": "'A. Datum'" } }] }
                ]],
                "columns": [{ "value": { /* Column Expression — grouping key */ } }]
              },
              "valueMap": [{ "0": "A. Datum", "1": "N", "2": "5", "3": "A. Datum" }]
            }
          }
        }]
      }
    }
  }
}]
```

- `decomposedIdentities.values` — the actual selected values as literals
- `decomposedIdentities.columns` — the grouping key columns
- `valueMap` — maps indices in `decomposedIdentities` to queryRef values
- `expansionStates` — only needed for hierarchy slicers when nodes are expanded;
  `identityKeys` defined on the first level only, `identityValues` inside
  `root.children[]` only when a specific node has been toggled open
- **Literal format**: strings use single quotes inside double quotes
  (`"Value": "'A. Datum'"`); numbers use type suffixes (`"Value": "5L"`).

---

## Slicer Sync Groups

Slicers can be synced across pages so that changing a selection on one page
applies to all other pages with slicers in the same sync group. Add `syncGroup`
inside the `visual` object (sibling of `visualType`, `query`, `objects`):

```json
{
  "visual": {
    "visualType": "slicer",
    "syncGroup": {
      "groupName": "DateSync",
      "fieldChanges": true,
      "filterChanges": true
    },
    "query": { /* ... */ },
    "objects": { /* ... */ }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `groupName` | string | Unique name for the sync group. Slicers with the same `groupName` across pages are synced. |
| `fieldChanges` | boolean | When `true`, field/projection changes propagate to all group members. |
| `filterChanges` | boolean | When `true`, filter/selection changes propagate to all group members. |

**Rules:**
- All slicers in the same sync group must have the same `visualType` and bound column.
  Slicers of the same type that produce the same filter expressions can be in the
  same group — e.g. two `slicer` visuals both bound to `Date.Date` with mode `'Between'`.
- Set the same `groupName` on each slicer you want synced (e.g. `"DateSync"`; any unique string works).
- Typically set both `fieldChanges: true` and `filterChanges: true`.

> **Note:** The published PBIR JSON schemas (`visualContainer/2.5.0–2.9.0`) do
> not list `syncGroup`. However, the internal schema (`visualConfiguration/9999.0.0`)
> does include it with full type definition. Desktop reads and writes it correctly.

---

## Theme Approach

These slicer defaults are applied report-wide via theme `visualStyles`
(plain JSON, not PBIR `expr` wrappers):

```json
"slicer": {
  "*": {
    "header": [{
      "fontFamily": "Segoe UI Semibold",
      "textSize": 10,
      "fontColor": { "solid": { "color": "#252423" } },
      "outlineStyle": 0
    }],
    "items": [{
      "fontFamily": "Segoe UI Variable, Segoe UI, sans-serif",
      "textSize": 9,
      "fontColor": { "solid": { "color": "#252423" } },
      "outlineStyle": 0,
      "padding": 2
    }]
  }
}
```

The global `*.*` wildcard also provides: border (#E8E8E8, radius=8),
hidden visual header, and VCO padding (8px). Per the
VCO override caveat, this `*.*.padding`
cascade is **dropped** the moment a slicer sets any per-visual VCO, so every
slicer template must redeclare `padding` explicitly — `8/8/8/8` to match the
theme for normal slicers, or `0/0/0/0` for the fill variant
(so the white fill reaches the container edges).

> `header.text` does **NOT** usefully cascade from theme — it would set
> the same name on every slicer. Always set per-visual.

---

## Discovering Properties

```bash
# List all formatting objects for a slicer type
powerbi-report-author formatting list-objects slicer
powerbi-report-author formatting list-objects advancedSlicerVisual
powerbi-report-author formatting list-objects listSlicer

# Inspect specific objects
powerbi-report-author formatting describe-object slicer header
powerbi-report-author formatting describe-object slicer items
powerbi-report-author formatting describe-object slicer data
powerbi-report-author formatting describe-object slicer selection

# Search across all objects
powerbi-report-author formatting search slicer "font|text|padding"
```
