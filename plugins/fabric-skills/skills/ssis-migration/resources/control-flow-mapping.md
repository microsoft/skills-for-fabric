# Phase 3 — Control Flow → Pipeline activities

Map each Control Flow task to a Fabric pipeline activity, and each precedence
constraint to `dependsOn` (and `IfCondition` when the constraint has an expression).

## Task mapping

| SSIS task (`ExecutableType`) | Fabric activity | typeProperties / notes |
|---|---|---|
| `Microsoft.ExecuteSQLTask` | **Script** (or `SqlServerStoredProcedure`) | `scriptType: NonQuery` for DML/DDL, `Query` to return a value |
| `Microsoft.ExecuteSQLTask` returning a single value (e.g. `@COUNT`) | **Lookup** | output → `@activity('x').output.firstRow.<col>` |
| `Microsoft.Pipeline` (Data Flow Task) | **Copy** / **Notebook** / **Dataflow Gen2** | see data-flow-mapping |
| Sequence Container | (no item) — group via `dependsOn` ordering or nested `ExecutePipeline` | |
| `Microsoft.ForEachLoop` | **ForEach** | move inner tasks into `activities` |
| `Microsoft.ForLoop` | **Until** | |
| `Microsoft.FileSystemTask` | **Notebook** (`notebookutils.fs`) or `Copy` | park if pure local-FS |
| `Microsoft.ExecuteProcess` | **Notebook** / `WebActivity` | park if it calls a local .exe |
| `Microsoft.ExecutePackageTask` | **InvokePipeline** | point at the migrated child pipeline |
| Send Mail Task | `WebActivity` / Office365 Outlook | |
| Script Task (`Microsoft.ScriptTask`) | **Notebook** | **manual refactor — flag** |

## Precedence constraints → dependsOn

Each `DTS:PrecedenceConstraint` has `From`, `To`, optional `Expression`, `EvalOp`.

| SSIS constraint | Fabric |
|---|---|
| Success (default) | `dependsOn: [{activity, dependencyConditions:["Succeeded"]}]` |
| Failure | `["Failed"]` |
| Completion | `["Completed"]` |
| Expression + Constraint (`EvalOp=1`, e.g. `@[User::COUNT]>0`) | wrap the downstream branch in an **IfCondition** whose `expression` is the converted SSIS expression (see expression-mapping) |
| `LogicalAnd=False` (OR) | model with multiple `dependsOn` or restructure |

## FT_NS_GL control flow (active path)

```
TRUNC TEMP_EDL_NS_GL  (Script, NonQuery)
   └─Succeeded→ Copy: NetSuite → edl.TEMP_EDL_NS_GL
        └─Succeeded→ Script: EDL_NS_GL upsert
            └─Succeeded→ Lookup: CHECK FOR INCR RECORDS  →  count
                └─ IfCondition  @greater(activity('CHECK FOR INCR RECORDS').output.firstRow.count, 0)
                     ├─ TRUE  → Script: TRUNC stg.STG_NS_GL
                     │           └→ Script: STG_NS_GL load
                     │                └→ Script: DELETE dat.FT_NS_GL
                     │                     └→ Script: FT_NS_GL insert
                     │                          └→ Script: UPDATE STATUS
                     └─ FALSE → (no-op; original FST_RENAME_FILE is disabled)
```

Resulting `pipeline-content.json` skeleton:

```json
{
  "properties": {
    "activities": [
      {"name": "Trunc Temp", "type": "Script", "dependsOn": [],
       "typeProperties": {"scripts": [{"type": "NonQuery", "text": "TRUNCATE TABLE edl.TEMP_EDL_NS_GL"}]}},
      {"name": "Copy NetSuite to Temp", "type": "Copy",
       "dependsOn": [{"activity": "Trunc Temp", "dependencyConditions": ["Succeeded"]}],
       "typeProperties": {"source": {"type": "..."}, "sink": {"type": "DataWarehouseSink"}}},
      {"name": "EDL Upsert", "type": "Script",
       "dependsOn": [{"activity": "Copy NetSuite to Temp", "dependencyConditions": ["Succeeded"]}],
       "typeProperties": {"scripts": [{"type": "NonQuery", "text": "<EDL merge T-SQL>"}]}},
      {"name": "CHECK FOR INCR RECORDS", "type": "Lookup",
       "dependsOn": [{"activity": "EDL Upsert", "dependencyConditions": ["Succeeded"]}],
       "typeProperties": {"source": {"type": "DataWarehouseSource",
         "sqlReaderQuery": "SELECT COUNT(*) AS count FROM edl.EDL_NS_GL WHERE ..."}}},
      {"name": "If Incremental", "type": "IfCondition",
       "dependsOn": [{"activity": "CHECK FOR INCR RECORDS", "dependencyConditions": ["Succeeded"]}],
       "typeProperties": {
         "expression": {"type": "Expression",
           "value": "@greater(activity('CHECK FOR INCR RECORDS').output.firstRow.count, 0)"},
         "ifTrueActivities": [ /* Trunc Stg → Stg load → Delete Ft → Ft insert → Update Status */ ]
       }}
    ]
  }
}
```

Hand the assembled JSON to Phase 6 (delegate deploy to the authoring skill /
ITEM-DEFINITIONS-CORE: base64 `pipeline-content.json` → POST `/items`).
