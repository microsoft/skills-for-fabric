# User guide

## Start and run

1. Install dependencies and start Streamlit (`streamlit run app.py`); see the
   [README](README.md).
2. Set the desired reporting period. The run retains rows without a parseable
   date as data-quality exceptions; valid dates outside the period are logged
   and excluded.
3. Choose **Run synthetic demonstration** to validate the end-to-end flow
   without real financial data, or choose **List and ingest SharePoint files**
   after the mappings, environment values, and site grant are approved.
4. Review the status banner. `Critical` means row/dollar completeness did not
   reconcile and the run is not complete.
5. Review exceptions, inspect lineage, record any controlled override, and
   download the Excel report.

## Pages

- **Executive Summary:** row-level status counts for current filters, candidate
  count, run status and per-source controls.
- **Exception Queue:** filtered non-fully-matched ledger rows and a separate
  date-only candidate table. Candidates never become confirmed matches.
- **Transaction Lineage:** select a reconciliation group and review SnapPay,
  BluePay, BMO, and JDE source rows, keys, component amounts, dates, filenames,
  worksheets, source rows, and raw values. A missing source appears as no row.
  The override form captures prior/revised status, reason, preparer, optional
  approver, and supporting reference.
- **Control Totals:** per-source input and disposition counts/dollars plus the
  row and dollar completeness bridge.
- **Reconciliation Run History:** prior run IDs, periods, created times, and
  complete/critical run status.
- **Configuration Validation:** checks required source mappings and flags
  example placeholders before production data runs.

The sidebar filters records by source/processor, payment type, algorithmic
match status, exception type, transaction date range, batch, transaction ID,
backend ID, and source filename. Selecting a reconciliation run scopes the
review to that reporting-period run.

## Excel report

The export always contains these 15 sheets, in order:

1. Executive Summary
2. Control Totals
3. Reconciliation Ledger
4. Exception Queue
5. Timing Differences
6. Rejects Reversals Refunds
7. Missing from Bank
8. Missing from GL
9. Amount Mismatches
10. Duplicate IDs
11. Manual Overrides
12. Source File Inventory
13. Data Quality Issues
14. Run Log
15. Data Dictionary

Summary rows are calculated from the exported source/ledger detail, and
control totals include per-source row/dollar differences. Candidate-only rows
appear in the Exception Queue and Run Log, not as confirmed ledger matches.
The report retains Critical status and bridge issues rather than labelling a
failed run complete. Generated files are under ignored `output/`.

## Manual overrides

Use overrides only with evidence. The original algorithm status is immutable;
the current reviewed status is derived from the latest override displayed
separately. The required prior status must equal the algorithm's result. No
override edits source rows, raw values, or the original matching evidence.
Approver and supporting reference are optional in this prototype but should
be required by the organization's approved review policy.
