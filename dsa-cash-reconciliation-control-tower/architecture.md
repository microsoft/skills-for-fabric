# Architecture

## Components and trust boundaries

1. **SharePoint landing zone:** the pilot uses the locally synchronized
   SharePoint folder supplied through `LOCAL_SHAREPOINT_ROOT` or the UI root
   path. It never writes to source files. Microsoft Graph remains an optional
   future connector, not the active pilot mode.
2. **Source profiler:** recursively selects only the five September pilot
   filename prefixes and `.xlsx` files for the September 2026 pilot. It detects headers within the first
   50 rows, records every worksheet structure and data-row count, compares
   SnapPay daily-file layouts, and reports identifier storage metadata. It
   does not extract or persist transaction content.
3. **Mapping validation:** confidence-rated header proposals are editable,
   visibly unapproved drafts kept separately from the active mapping. A
   reviewer may independently assign adapters, select exact observed headers
   and worksheets, and explicitly approve mappings; none of these steps occurs
   automatically. `RC BLUEPAY GENERAL` stays unassigned until its source and
   ledger semantics are confirmed. Approval metadata is saved only in ignored
   local `data/`.
4. **Source adapters:** one configured adapter per source reads CSV, XLSX, or
   XLSM; selects configured worksheet names; maps configured source headers to
   the canonical fields; and preserves raw row values and workbook/sheet/row
   lineage. Missing required headers are fatal configuration errors. Blank
   required values and malformed values are row-level quality exceptions.
5. **Matching and controls:** pure Python logic applies ordered exact-key
   matches. It does not use fuzzy matching or machine learning. Timing
   candidates are kept out of confirmed matches.
6. **Persistence:** `ReconciliationRepository` is the storage boundary.
   `SQLiteRepository` stores runs, canonical source rows, algorithmic ledger
   rows, file hashes, state/delta URLs, and separate manual override audit
   events.
7. **Review/reporting:** Streamlit provides the source-profile and mapping
   validation pilot pages. The reconciliation dashboard and report APIs remain
   in the package but are not exposed by this pilot UI. Excel export is
   generated from the same persisted run detail and has the fixed set of 15
   sheets in [user_guide.md](user_guide.md).

```text
Local synchronized SharePoint folder (read-only)
       │ filename rules, September 2026 pilot group
       ▼
Workbook profiler ── sheet/header/row inventory ── Configuration Validation
                                                         │
                                          explicit human mapping approval
                                                         │
                                  Reconciliation intentionally not enabled
```

## Canonical row

Each input row carries source, normalized transaction ID, account/payment
type, batch, backend/customer reference, signed Decimal amount, transaction
and settlement dates, status, file hash, workbook, worksheet, source row,
original `raw_values`, quality issues, and an internal source record ID.
Normalization does not modify source files. Identifier values are strings;
the adapter does not infer omitted leading zeros from numeric spreadsheet cells.

## Matching sequence

1. SnapPay ↔ BluePay exact transaction ID; compare signed amounts using the
   configured tolerance. Duplicate IDs or poor-quality rows are not confirmed.
2. BluePay ↔ BMO exact backend ID, otherwise exact customer reference; compare
   grouped totals for one-to-one or many-to-one settlements.
3. SnapPay (preferred to avoid double counting) or BluePay ↔ JD Edwards by
   exact batch number and grouped totals.
4. Date-window candidates are emitted separately for human review and never
   join components. A date by itself never creates a confirmed match.
5. Every connected group receives one algorithmic disposition, propagated to
   its source rows with rule, fields, variance, component amounts, dates, and
   full source-row lineage.

The exact algorithm and disposition priorities are described in
[control_framework.md](control_framework.md). An exception is never hidden
because another source row joined its group.

## Repository interface and transactions

Matching depends on source/ledger models and the repository protocol, not
SQLite SQL. Replacing the prototype store requires implementing the repository
contract for run writes/reads, file-hash checks, and overrides. SQLite creates
the parent directory and enables foreign keys; each run write, row inserts,
and inventory updates execute in a transaction. Manual overrides are inserted
in their own audit table, never applied to the immutable `algorithm_status`.

## Delta-token extension

`GraphSharePointClient.read_delta()` follows Graph `@odata.nextLink` pages and
persists the final `@odata.deltaLink` in repository state. The current prototype
does not schedule polling or automatically reconcile delta removals. The drive
delta endpoint can enumerate the drive hierarchy; consumers must constrain
changes to the configured root/source-folder paths before treating them as
eligible financial inputs. See the Graph [driveItem delta API](https://learn.microsoft.com/graph/api/driveitem-delta?view=graph-rest-1.0).
