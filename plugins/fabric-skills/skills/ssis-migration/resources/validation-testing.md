# Phase 7 — Validation & testing

Prove parity between the SSIS run and the Fabric run before cutover.

## Checklist

- [ ] **Schema parity** — target tables (`edl/stg/dat` schemas) match the on-prem
      DDL: column names, datatypes, precision (`DECIMAL(18,2)` vs `(19,2)`), nullability.
- [ ] **Row counts** — for each layer (TEMP, EDL, STG, FT) compare SSIS vs Fabric for
      the same input window.
- [ ] **Watermark logic** — `ETL_CONTROL_TABLE` advances to the same `MAX(CREATED_DT/
      MODIFIED_DT)` and `STATUS='COMPLETED'`.
- [ ] **Measure totals** — `SUM(AMOUNT)`, `SUM(AMOUNT_DEBIT)`, `SUM(AMOUNT_CREDIT)`
      match (watch the `* -1` sign flip in the EDL step).
- [ ] **Key resolution** — surrogate keys (`NS_COA_KEY`, `NS_OPERATING_ENTITY_KEY`,
      `NS_DEPARTMENT_KEY`) and the `-1` / `'NA'` defaults behave identically.
- [ ] **Idempotency** — run the pipeline twice; the second run inserts 0 new fact rows
      (delete-then-insert anti-join).
- [ ] **Incremental branch** — verify the `IfCondition` (`count > 0`) takes the right
      path for both changed and no-change inputs.
- [ ] **Failure handling** — a failed Script activity stops downstream (dependsOn
      `Succeeded`), matching SSIS precedence.

## Reconciliation queries

```sql
-- counts per layer
SELECT 'EDL' lvl, COUNT(*) c FROM edl.EDL_NS_GL
UNION ALL SELECT 'STG', COUNT(*) FROM stg.STG_NS_GL
UNION ALL SELECT 'FT',  COUNT(*) FROM dat.FT_NS_GL;

-- measure parity (run on both systems, compare)
SELECT COUNT(*) rows, SUM(AMOUNT) amt, SUM(AMOUNT_DEBIT) dr, SUM(AMOUNT_CREDIT) cr
FROM dat.FT_NS_GL;

-- watermark
SELECT TABLE_NAME, EDL_created_dt, EDL_modified_dt, STATUS
FROM dat.ETL_CONTROL_TABLE WHERE TABLE_NAME = 'FT_NS_GL';
```

## Parallel-run window

Run SSIS and Fabric **side by side** against the same source for one full cycle
(2–4 weeks for daily loads) and reconcile each run before decommissioning SSIS.
