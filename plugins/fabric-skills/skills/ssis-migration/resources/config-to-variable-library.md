# Phase 2 — .dtsConfig / variables → Variable Library

SSIS externalizes config in `.dtsConfig` (package configurations), project
`.params`, and package `DTS:Variables`. Fabric uses a **Variable Library** item
(`variables.json` + `settings.json` + per-env `valueSets/*.json`) — see
`common/ITEM-DEFINITIONS-CORE.md` for the exact part format.

## What goes where

| SSIS | Fabric |
|---|---|
| `.dtsConfig` connection strings | Fabric **Connections** (Phase 1), not the Variable Library |
| `.dtsConfig` / `.params` scalar settings (paths, source names, flags) | **Variable Library** variables |
| Package `User::` variables that are static | Variable Library variables |
| Package variables that are `EvaluateAsExpression=True` | **pipeline expressions** (don't store; compute — see expression-mapping) |
| Per-environment values (dev/test/prod) | Variable Library **value sets** |

## Variable type mapping

| SSIS `DataType` | Variable Library `type` |
|---|---|
| 8 (String) | `String` |
| 3 (Int32) / 6 (Int64) | `Integer` |
| 11 (Boolean) | `Boolean` |
| 5 (Double) | `Number` |
| 7 (DateTime) | `DateTime` |
| (item ref to a Fabric item) | `ItemReference` |

## FT_NS_GL variables

Most FT_NS_GL `User::` variables are **legacy file-handling** for disabled tasks —
drop them. Keep only what the active pipeline needs.

| SSIS variable | Action |
|---|---|
| `COUNT`, `INSERT_ROW_COUNT`, `UPDATE_ROW_COUNT` | drop — use `@activity().output` / Lookup |
| `FILE_NAME`, `FILE_PATH`, `RENAME_FILE_NAME`, `ARCHIVE_FILE_PATH`, `FILE_NAME_FIELD` | drop — file tasks are disabled |
| `COMPANY_NAME`, `PAY_SOURCE`, `PR_SOURCE`, `QB_SOURCE` (='NETSUITE'), `PROJECT_NAME` | keep as Variable Library `String` if still referenced |

Resulting `variables.json` (only if any are still needed):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/variableLibrary/definition/variables/1.0.0/schema.json",
  "variables": [
    {"name": "src_system", "type": "String", "value": "NETSUITE"},
    {"name": "table_name", "type": "String", "value": "FT_NS_GL"}
  ]
}
```

Reference in the pipeline via `@pipeline().libraryVariables.table_name` and bind the
`libraryVariables` block as shown in ITEM-DEFINITIONS-CORE.
