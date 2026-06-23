---
name: ssis-migration
description: >
  Migrate SQL Server Integration Services (SSIS) packages (.dtsx) and project
  configs (.dtsConfig / .params) to Microsoft Fabric Data Factory pipelines,
  Dataflows Gen2, Notebooks, and Warehouse T-SQL. Use when the user has an SSIS
  package or .dtsx file, mentions SSIS / Integration Services, or asks to
  convert, modernize, or migrate SSIS ETL to Microsoft Fabric.
license: MIT
---

# SSIS → Microsoft Fabric Migration

SSIS has **no Azure-SSIS IR in Fabric** and `ExecuteSSISPackage` has **no Fabric
equivalent**. This skill therefore performs a **re-architecture** (not a
lift-and-shift): it parses the `.dtsx` XML, classifies every task, and emits
Fabric-native item definitions.

This skill is the SSIS-specific **parser + mapper + orchestrator**. It does NOT
re-implement item creation — it **delegates** the actual build to existing skills:

- `sqldw-authoring-cli`     → Warehouse, T-SQL DDL, stored procedures
- `dataflows-authoring-cli` → Dataflow Gen2 (Power Query `mashup.pq`)
- `spark-authoring-cli`     → Notebooks for transforms / former Script Tasks
- `common/ITEM-DEFINITIONS-CORE.md` → the `format` + `parts` + base64 → POST `/items` mechanism

## Prerequisites

1. Azure auth: `az login` then a token for `https://api.fabric.microsoft.com`
   (`az account get-access-token --resource https://api.fabric.microsoft.com`).
2. A target Fabric **workspace id** and a **Warehouse** (or Lakehouse) created
   via `sqldw-authoring-cli`.
3. The `.dtsx` file(s) and any `.dtsConfig` / project `.params` available locally.

## Workflow

Run the phases in order. Each phase has a dedicated resource file — load it only
when you reach that phase (progressive disclosure).

| Phase | Action | Resource |
|---|---|---|
| 0 | **Assess** — parse `.dtsx`, inventory tasks/connections/variables, score complexity, flag blockers | `resources/ssis-assessment.md` |
| 1 | **Connections** — map Connection Managers → Fabric Connections (Entra ID) | `resources/connection-manager-mapping.md` |
| 2 | **Config & variables** — `.dtsConfig` + package variables → Variable Library | `resources/config-to-variable-library.md` |
| 3 | **Control flow** — tasks + precedence constraints → pipeline `activities[]` | `resources/control-flow-mapping.md` |
| 4 | **Data flows** — Data Flow Task components → Copy / Dataflow Gen2 / Notebook | `resources/data-flow-mapping.md` |
| 5 | **Expressions** — SSIS expression language → pipeline expressions / T-SQL | `resources/expression-mapping.md` |
| 6 | **Build & deploy** — assemble `pipeline-content.json`, encode, POST via the authoring skills | (delegates; see ITEM-DEFINITIONS-CORE) |
| 7 | **Validate** — row counts, watermarks, schema parity | `resources/validation-testing.md` |
| 8 | **Report** — summary of migrated / parked items | `resources/migration-report.md` |

## Decision rules

- **Execute SQL Task** → `Script` activity (or stored proc) on the Warehouse. T-SQL
  is largely compatible; rewrite `ISNUMERIC`, linked-server, and `..` 3-part names.
- **Data Flow Task**: if it is source→light-map→sink, use a **Copy activity**. If it
  has Lookups/Merge/Conditional Split/SCD, use a **Notebook** (Spark) or **Dataflow
  Gen2**, or fold the logic into Warehouse T-SQL.
- **Script Task (C#/VB)** → **Notebook** (manual refactor — flag in report).
- **Linked server `OPENQUERY(...)`** → native source **Connection** (parked: needs a
  real connector; flag in report).
- **Precedence constraint with expression** → `Lookup` activity → `IfCondition`.
- **File System / Execute Process tasks** → Notebook (`notebookutils`/`mssparkutils`)
  or `WebActivity`; park if no equivalent.

## Gotchas

Always consult `resources/gotchas.md` for parked items (SSIS IR, Script Tasks,
linked servers, SHIR) and the hybrid fallback (keep SSIS in ADF, invoke from Fabric
via `WebActivity` → ADF REST API).

## Worked example

`resources/ssis-assessment.md` and `resources/data-flow-mapping.md` use a real
package, **FT_NS_GL** (NetSuite GL incremental load: NetSuite `OPENQUERY` →
`TEMP_EDL_NS_GL` → `EDL_NS_GL` → `STG_NS_GL` → `FT_NS_GL`), as the end-to-end example.
