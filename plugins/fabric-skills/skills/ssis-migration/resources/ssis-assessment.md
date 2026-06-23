# Phase 0 — SSIS Assessment

Read-only. Parse the package(s) and produce an inventory + complexity score
**before** creating anything in Fabric.

## What to parse from each `.dtsx`

The `.dtsx` is XML in the `www.microsoft.com/SqlServer/Dts` namespace.

| Element | XPath-ish location | What to extract |
|---|---|---|
| Package name | `/DTS:Executable/@DTS:ObjectName` | display name |
| Connection managers | `DTS:ConnectionManagers/DTS:ConnectionManager` | name, `CreationName` (OLEDB/FLATFILE/EXCEL), `ConnectionString` |
| Variables | `DTS:Variables/DTS:Variable` | namespace, name, datatype, value, `EvaluateAsExpression`/`Expression` |
| Tasks | `DTS:Executables/DTS:Executable` | `ExecutableType`, `ObjectName`, `Disabled` |
| Execute SQL | `…ExecuteSQLTask` → `SQLTask:SqlStatementSource` | the T-SQL, `ResultType`, result bindings |
| Data Flow | `…Pipeline` → `pipeline/components/component` | each `componentClassID` |
| Precedence | `DTS:PrecedenceConstraints/DTS:PrecedenceConstraint` | `From`, `To`, `EvalOp`, `Expression`, `LogicalAnd` |
| Configs | `DTS:Configurations/DTS:Configuration` | `.dtsConfig` path |

> Skip tasks with `DTS:Disabled="True"` — note them as "disabled (not migrated)".

## Complexity scoring (per package)

| Signal | Weight | Notes |
|---|---|---|
| Script Task / Script Component (C#/VB) | **HIGH** | manual notebook refactor — biggest overrun driver |
| Linked-server `OPENQUERY` / 4-part names | HIGH | needs native connector |
| Data Flow with Lookup / Merge Join / SCD / Conditional Split | MEDIUM | → Notebook or Dataflow Gen2 |
| Execute SQL with `..` 3-part DB refs / `ISNUMERIC` / `GETDATE` | LOW | T-SQL tweaks |
| Plain Copy-style Data Flow (source→map→sink) | LOW | → Copy activity |
| File System / Execute Process / FTP / Send Mail tasks | MEDIUM | notebook/WebActivity or park |

Classify the package **Low / Medium / High**:
- Low: only Execute SQL + simple Copy, no scripts → 12–24h
- Medium: data-flow transforms, some expressions → 24–60h
- High: Script Tasks, linked servers, many containers → 60–180h

## Output of this phase

Produce a JSON inventory like:

```json
{
  "package": "FT_NS_GL",
  "complexity": "Medium",
  "connections": [
    {"name": "EDW_EDL_LHHDWEDL_MSSQL", "type": "OLEDB", "db": "LHHDWEDL"},
    {"name": "EDW_STG_LHHDWSTAGE_MSSQL", "type": "OLEDB", "db": "LHHDWSTAGE"},
    {"name": "EDW_TGT_LHHDWDAT_MSSQL", "type": "OLEDB", "db": "LHHDWDAT"}
  ],
  "tasks": [
    {"name": "TRUNC TEMP_EDL_NS_GL", "type": "ExecuteSQL", "map": "Script", "risk": "low"},
    {"name": "TEMP_EDL_NS_GL", "type": "DataFlow", "map": "Copy", "risk": "high",
     "note": "source is OPENQUERY(NETSUITEDB) linked server — needs NetSuite connector"},
    {"name": "EDL_NS_GL", "type": "ExecuteSQL", "map": "Script", "risk": "low"},
    {"name": "CHECK FOR INCR RECORDS", "type": "ExecuteSQL", "map": "Lookup", "risk": "low"},
    {"name": "STG_NS_GL", "type": "ExecuteSQL", "map": "Script", "risk": "low"},
    {"name": "DELETE FT_NS_GL", "type": "ExecuteSQL", "map": "Script", "risk": "low"},
    {"name": "FT_NS_GL", "type": "ExecuteSQL", "map": "Script", "risk": "low"},
    {"name": "UPDATE STATUS", "type": "ExecuteSQL", "map": "Script", "risk": "low"}
  ],
  "parked": ["OPENQUERY(NETSUITEDB) linked-server extract"],
  "disabled": ["GET_SOURCE_FILE_PATH", "EXCEL TO CSV CONV", "FST_RENAME_FILE", "FST_ARCHIVE_FILE"],
  "scriptTasks": 0
}
```

`scriptTasks: 0` is the best possible signal — low migration risk.

Hand this inventory to the later phases; the `tasks[].map` field drives Phase 3/4.
