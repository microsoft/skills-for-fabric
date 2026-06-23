# Gotchas & parked items

Consult before and during migration. "Parked" = no clean Fabric equivalent; needs a
manual decision.

## Hard blockers

| Item | Why | What to do |
|---|---|---|
| **`ExecuteSSISPackage` activity** | Fabric has **no Azure-SSIS IR** | Keep SSIS in ADF and invoke from Fabric via `WebActivity` → ADF REST API; or fully refactor |
| **Script Task / Script Component (C#/VB)** | no .NET runtime in Fabric pipelines | Rewrite logic as a **Notebook** (PySpark) |
| **Linked server / `OPENQUERY`** | Fabric Warehouse has no linked servers | Replace with a native source **Connection** + Copy activity |
| **Cross-database joins** (`db1..t JOIN db2..t`) | Warehouse can't join across DBs | Put all schemas in **one Warehouse**; rewrite to `schema.table` |
| **SHIR-only on-prem sources** | | Use an **on-premises data gateway** connection |
| **ACE/Excel & Jet providers** | not available | Dataflow Gen2 Excel connector, or pre-convert to CSV/Parquet |
| **`xp_cmdshell` / Execute Process (.exe)** | no shell | Notebook (`notebookutils`) or external orchestration |

## The hybrid fallback (when refactor isn't worth it)

1. Migrate the `.dtsx` to **Azure Data Factory** and keep the **Azure-SSIS IR** there.
2. From the Fabric pipeline, call the ADF pipeline via **`WebActivity`** hitting the
   ADF REST API (`createRun`), then poll for completion.
3. This lets you modernize the *orchestration* in Fabric while the SSIS package keeps
   running unchanged — convert it to native later.

## Behavioral differences to validate

- **Identity/sequence** reseed behavior differs — verify surrogate keys.
- **Collation / case sensitivity** may differ from on-prem — affects `UPPER()` joins
  and `'NA'`/`-1` default matching.
- **Transactions**: SSIS `TransactionOption` and `MaxConcurrentExecutables` have no
  direct pipeline analog — Script activities are independent; design idempotency
  (the FT_NS_GL delete-then-insert pattern is already idempotent ✅).
- **Decimal precision**: SSIS `DECIMAL(18,2)` vs `DECIMAL(19,2)` casts — keep exact
  precision from the original to avoid rounding diffs.

## FT_NS_GL parked/manual items

- `OPENQUERY(NETSUITEDB, …)` — the only real blocker. Stand up a **NetSuite
  connection** (SuiteAnalytics Connect / ODBC) and move the extract SELECT into a
  Copy activity source query.
- Everything else (8 Execute SQL tasks, 1 simple data flow, 0 script tasks) is
  low-risk and maps cleanly.
