# Phase 1 — Connection Managers → Fabric Connections

Fabric uses **Connections** (managed, gateway-aware, **Microsoft Entra ID** auth).
SSIS SQL/Windows auth and embedded passwords do **not** carry over.

## Mapping table

| SSIS `CreationName` | Fabric Connection | Notes |
|---|---|---|
| `OLEDB` (SQL Server) | SQL Server / Azure SQL connection | Entra ID or service principal; no `User ID=…;Password=…` |
| `OLEDB` via linked server (`OPENQUERY`) | **native connector** for the real source | **Parked** — linked servers don't exist in Fabric; see gotchas |
| `FLATFILE` | Lakehouse Files / ADLS Gen2 connection | upload/land files in OneLake |
| `EXCEL` | Dataflow Gen2 Excel connector | the Excel ACE provider is gone |
| `ODBC` | ODBC / native connector | prefer a first-class connector if one exists |
| `SMTP` | (no direct) | Office 365 Outlook via `WebActivity` / Power Automate |
| `FTP` | (no direct) | Notebook with `notebookutils` or Copy with SFTP connector |

## Procedure

1. For each non-disabled connection manager, extract the server + initial catalog
   from the `ConnectionString`. **Discard** `User ID` / `Password` / `Persist
   Security Info`.
2. Create one Fabric Connection per distinct source/target, authenticated with
   Entra ID (delegate creation to `sqldw-authoring-cli` / the Connections API).
3. Record a `connectionId` for each; the Copy/Script activities reference these.

## FT_NS_GL example

| SSIS CM | Initial Catalog | Fabric target |
|---|---|---|
| `EDW_EDL_LHHDWEDL_MSSQL` | `LHHDWEDL` | Warehouse schema `edl` (or its own Warehouse) |
| `EDW_STG_LHHDWSTAGE_MSSQL` | `LHHDWSTAGE` | Warehouse schema `stg` |
| `EDW_TGT_LHHDWDAT_MSSQL` | `LHHDWDAT` | Warehouse schema `dat` (fact + dims + control) |
| (source) `OPENQUERY(NETSUITEDB)` | NetSuite | **NetSuite connector** — parked, manual |

> Recommendation: collapse the three on-prem databases into **one Fabric
> Warehouse with three schemas** (`edl`, `stg`, `dat`). Rewrite `LHHDWEDL..TABLE`
> 3-part names to `edl.TABLE`, etc. (see expression-mapping).
