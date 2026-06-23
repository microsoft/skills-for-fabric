# Phase 4 — Data Flow Task → Copy / Dataflow Gen2 / Notebook

A Data Flow Task is a `Microsoft.Pipeline` executable containing
`pipeline/components/component`, each with a `componentClassID`. Map by component.

## Component mapping

| SSIS Data Flow component (`componentClassID`) | Fabric target |
|---|---|
| `Microsoft.OLEDBSource` | Copy **source** (or `sqlReaderQuery`) |
| `Microsoft.OLEDBDestination` | Copy **sink** (`DataWarehouseSink`) or `INSERT…SELECT` |
| `Microsoft.DerivedColumn` | Copy column mapping / SQL `SELECT` expr / Dataflow custom column |
| `Microsoft.DataConvert` | Copy type mapping / `CAST` in SQL |
| `Microsoft.Lookup` | SQL `JOIN` (Notebook or Warehouse) / Dataflow Merge |
| `Microsoft.MergeJoin` | SQL `JOIN` / Dataflow Merge queries |
| `Microsoft.ConditionalSplit` | `IfCondition` / `Filter` / SQL `WHERE` / Dataflow filter |
| `Microsoft.Aggregate` | SQL `GROUP BY` / Dataflow Group By |
| `Microsoft.SCD` (Slowly Changing Dimension) | `MERGE` T-SQL / Dataflow / Notebook |
| `Microsoft.RowCount` | pipeline variable / `@activity().output.rowsCopied` |
| Script Component | **Notebook** (manual) |

## Choosing the target shape

- **source → DataConvert/DerivedColumn → destination** (no joins) → **Copy activity**
  with column + type mappings. Cheapest.
- **joins / lookups / splits / SCD** → **Notebook (Spark)** or **Dataflow Gen2**, or
  push the whole thing into **Warehouse T-SQL** (often simplest when source already
  lands in the Warehouse).

## FT_NS_GL data flow (TEMP_EDL_NS_GL)

Components present: `OLEDBSource` (an `OPENQUERY(NETSUITEDB,…)` SELECT) →
`DataConvert` (widen text to str/1252) → `DerivedColumn` "AUDIT COLUMNS"
(`CREATED_DT/MODIFIED_DT = StartTime`, `CREATED_BY/MODIFIED_BY = 'EDL_NS_GL'`,
`SRC_SYSTEM = 'NETSUITE'`) → `OLEDBDestination` `[dbo].[TEMP_EDL_NS_GL]`.

Recommended Fabric shape: **Copy activity**.

- **Source**: NetSuite connector (parked → see gotchas). The original SELECT joins
  NetSuite `transaction ⋈ transactionLine ⋈ Entity ⋈ accountingPeriod ⋈ Account`.
  Keep that query in the Copy `query` against the NetSuite connection.
- **Sink**: `DataWarehouseSink` → `edl.TEMP_EDL_NS_GL`.
- **Audit columns**: add as additional columns in the Copy mapping
  (`@pipeline().TriggerTime` for the timestamps, literals for the rest) — no Spark needed.
- **Type conversions**: express in the Copy type mapping or simply land as the
  source types and `CAST` later in the EDL upsert Script.

> The full column lineage (NetSuite field → TEMP → EDL → STG → FT) is documented in
> the project's `FT_NS_GL_STTM.xlsx`. Reuse it as the Copy mapping spec.

Because every downstream step (EDL/STG/FT) is already T-SQL, the lowest-effort path
for FT_NS_GL is: **Copy NetSuite→TEMP, then do everything else as Script activities**
in the Warehouse. No Notebook or Dataflow Gen2 is required for this package.
