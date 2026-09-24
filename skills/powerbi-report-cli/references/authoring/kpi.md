# KPI Visual

> **Schema version:** Use `2.10.0` for new visuals; preserve existing version when editing.

## Roles

| Role | Required | Kind | Max |
|------|----------|------|-----|
| `Indicator` | ✓ | Measure or Aggregation | 1 |
| `TrendLine` | — | Column (date/numeric) | 1 |
| `Goal` | — | Measure or Aggregation | 2 |

Formatting objects: `general`, `goals`, `indicator`, `lastDate`, `status`, `trendline`

## Why KPI Goes Blank

The KPI visual fails silently (no error, blank render) in several common situations:

- **`Indicator` bound to a column**: `Indicator` requires `kind: Measure` or `kind: Aggregation` — a raw column expression is rejected with `PBIR_ROLE_KIND_MISMATCH`. Use a DAX measure or wrap the column in an aggregation.
- **`Indicator` returns `BLANK` at the latest trend point**: If the date table extends into the future, the most recent row is blank. Fix: `CALCULATE([Metric], LASTNONBLANK('Date'[Date], [Metric]))` or `COALESCE([Metric], 0)`.
- **`TrendLine` bound to a text or category column**: `TrendLine` must be a date, datetime, or monotonically increasing numeric column — text fields produce a blank sparkline.
- **`Goal` granularity does not align with `Indicator`**: If the Goal measure evaluates at a coarser grain than the Indicator time axis, the target renders blank or zero. Fix: `CALCULATE([Annual Target], ALL('Date'[Month]))`.
- **`Goal` bound to a raw numeric column**: `Goal` accepts only `Measure` or `Aggregation` expressions — a raw column expression is rejected with `PBIR_ROLE_KIND_MISMATCH`.

## Complete Example

Minimal query skeleton with all three roles (empty `objects` / `visualContainerObjects` — add formatting entries from the list above as needed):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "c3d4e5f6a7b8c9d0e1f2",
  "position": { "x": 20, "y": 20, "z": 1000, "height": 200, "width": 320, "tabOrder": 1000 },
  "visual": {
    "visualType": "kpi",
    "query": {
      "queryState": {
        "Indicator": {
          "projections": [{
            /* Aggregation/Measure Expression */
          }]
        },
        "TrendLine": {
          "projections": [{
            /* date/numeric Column Expression */
          }]
        },
        "Goal": {
          "projections": [{
            /* Measure or Aggregation Expression */
          }]
        }
      }
    },
    "objects": {},
    "visualContainerObjects": {}
  }
}
```
