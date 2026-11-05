# User guide

## Start the September 2026 source-profile pilot

1. Install dependencies and start Streamlit (`streamlit run app.py`); see the
   [README](README.md).
2. Keep **Local Synced SharePoint Folder** selected and set the root folder in
   the sidebar. The field is editable and may also be configured as
   `LOCAL_SHAREPOINT_ROOT` in `.env`.
3. Choose **Profile September 2026 source files**. This scans only filenames
   matching the five configured prefixes and `.xlsx` extension, recursively.
   It opens workbooks read-only and displays filenames, inferred type, sheet
   names, nonempty data-row counts (header row excluded), detected header row,
   exact headers, distinct worksheet structures, identifier-storage risks,
   and missing/unmapped required fields.
4. Download the source-profile report if useful. It is generated in memory
   and is not saved by the application unless you choose to download it.
5. In **Configuration Validation**, review the proposed mapping table. Its
   source type, canonical field, exact observed header, worksheet, confidence,
   and reason are shown. The header cell is editable; saving writes a separate
   `data/proposed_mapping_drafts.yaml` marked `draft_unapproved` and does not
   alter active mappings.
6. Independently review source-adapter assignment, worksheet selection, and
   exact canonical mappings. The explicit **Save and approve mappings** action
   is never triggered automatically and should only be used after Finance
   review. This saves mapping and approval metadata under ignored local
   `data/`. The pilot does not run reconciliation.

## Pages

- **Source Profile:** workbook and worksheet inventory, row counts, header
  positions, distinct worksheet structures, SnapPay daily-file consistency,
  identifier storage risks, inferred source type, missing required fields,
  and an in-memory generated workbook report.
- **Configuration Validation:** editable filename-type/adapter assignment,
  unapproved mapping proposals, worksheet selection, exact source-header
  mapping, schema validation, and explicit local approval. Approval is
  invalidated if the approved mapping file changes.

All five filename types are profiled separately. SnapPay sheet structures are
compared across daily files, including header-row placement. The `RC BLUEPAY
GENERAL` workbook is kept unassigned and treated as a separate adapter/subtype
draft until Finance confirms its provenance and amount/ledger semantics; it is
not assigned to JDE merely because it contains general-ledger-like columns.
If headers differ between worksheets, map only columns valid on every selected
worksheet or select worksheets/files with a consistent schema.

## Reconciliation safeguard

This pilot version intentionally exposes no reconciliation action. Do not
interpret a mapping approval as a reconciliation approval. A future
implementation must separately validate source-period semantics and matching
controls before reading transaction rows into a ledger.

## Manual overrides

Use overrides only with evidence. The original algorithm status is immutable;
the current reviewed status is derived from the latest override displayed
separately. The required prior status must equal the algorithm's result. No
override edits source rows, raw values, or the original matching evidence.
Approver and supporting reference are optional in this prototype but should
be required by the organization's approved review policy.
