# Phase 5 — SSIS expressions & T-SQL → Fabric

Two different expression worlds:
1. **SSIS expression language** (precedence constraints, variables, derived columns)
   → **Fabric pipeline expression language** (`@…` functions).
2. **T-SQL inside Execute SQL Tasks** → **Fabric Warehouse T-SQL** (some rewrites).

## SSIS expression → pipeline expression

| SSIS | Fabric pipeline expression |
|---|---|
| `@[User::COUNT] > 0` | `@greater(activity('CHECK FOR INCR RECORDS').output.firstRow.count, 0)` |
| `@[User::COUNT] == 0` | `@equals(activity('...').output.firstRow.count, 0)` |
| `@[User::FILE_NAME]` | `@pipeline().parameters.FILE_NAME` or `@pipeline().libraryVariables.FILE_NAME` |
| `GETDATE()` (derived col) | `@pipeline().TriggerTime` / `@utcnow()` |
| `@[System::StartTime]` | `@pipeline().TriggerTime` |
| `RIGHT(@x, LEN(@x)-FINDSTRING(...))` (filename parse) | `@last(split(pipeline().parameters.x, '/'))` |
| `REPLACE(a,b,c)` | `@replace(a,b,c)` |
| `SUBSTRING(s,i,n)` | `@substring(s,i,n)` |
| string concat `+` | `@concat(a,b)` |

## T-SQL rewrites for Fabric Warehouse

Fabric Warehouse is T-SQL but not 100% SQL Server. Common fixes:

| SSIS / SQL Server | Fabric Warehouse |
|---|---|
| 3-part / 4-part names `LHHDWEDL..EDL_NS_GL` | schema names `edl.EDL_NS_GL` (collapse DBs → schemas) |
| Linked server `OPENQUERY(NETSUITEDB,'…')` | **not supported** — move extract to a Copy activity from a NetSuite connection |
| `ISNUMERIC(x)` | `TRY_CAST(x AS DECIMAL(19,2)) IS NOT NULL` (more reliable) |
| `GETDATE()` | `GETDATE()` works; `SYSDATETIME()` also ok |
| `SELECT … INTO #temp` | supported; or use a permanent staging table |
| `MERGE` | supported in Fabric Warehouse (use for upserts) |
| Identity / `IDENTITY()` | supported; verify reseed behavior |
| `DELETE A FROM A JOIN B …` | supported (T-SQL delete-with-join) |
| Cross-database joins | only within the **same Warehouse** (use schemas) |

## FT_NS_GL specifics

- `CASE WHEN ISNUMERIC(A.AMOUNT)=1 THEN CAST(CAST(A.amount AS FLOAT) AS DECIMAL(19,2))*-1 ELSE NULL END`
  → `CASE WHEN TRY_CAST(A.AMOUNT AS FLOAT) IS NOT NULL THEN CAST(TRY_CAST(A.AMOUNT AS FLOAT) AS DECIMAL(19,2))*-1 ELSE NULL END`
- `lhhdwedl..EDL_NS_GL` → `edl.EDL_NS_GL`; `lhhdwdat..FT_NS_GL` → `dat.FT_NS_GL`;
  `lhhdwstage..STG_NS_GL` → `stg.STG_NS_GL`.
- The EDL "delete + insert + soft-delete" block can stay as three statements in one
  Script activity, or be rewritten as a single `MERGE`.
- The watermark reads/writes against `dat.ETL_CONTROL_TABLE` stay as plain T-SQL.
