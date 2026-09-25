# DSA Cash Reconciliation Control Tower

A Python prototype for controlled, exception-based cash reconciliation across
SnapPay → BluePay → BMO Bank → JD Edwards GL. Source files remain immutable;
the prototype ingests approved files read-only, stores a run ledger in SQLite,
and presents review evidence in Streamlit and Excel.

> **Configuration required:** `config/column_mappings.yaml` intentionally
> contains clearly marked header and worksheet placeholders. Replace them with
> approved source specifications before processing non-synthetic data. No
> tenant, site, drive, URL, account, or credential values are fabricated.

## Quick start

From this directory, install the prototype and test dependencies:

```powershell
python -m pip install -e ".[test]"
```

Create the synthetic source files and run the end-to-end reconciliation:

```powershell
python scripts/run_synthetic.py
```

Expected result: four synthetic input files are read, an SQLite ledger is
created under ignored `data/`, and the source-to-output row and dollar bridge
is zero for all sources. The synthetic data covers clean, grouped, timing,
missing, duplicate, mismatch, reject, reversal, refund, and data-quality cases.

Launch the dashboard:

```powershell
streamlit run app.py
```

Choose **Run synthetic demonstration** to create a fresh synthetic run from
the UI. Use **Download reconciliation Excel workbook** for the 15-sheet report.
The dashboard can also list/download the approved SharePoint file types after
the environment, site-specific permission grant, and production mappings have
been configured.

Content hashes cannot be processed twice in the same run/reporting period. A
duplicate mixed with new source files aborts the entire run to prevent a
partial-population success; identical files can be reused for a different
reporting period.

Run automated tests:

```powershell
pytest
```

## Runtime setup

Copy `.env.example` to `.env` and supply values issued by your Microsoft 365
administrator. The app uses interactive delegated Microsoft Graph
authentication and the read-only `Sites.Selected` permission; the application
must also be granted read access to the specific SharePoint site. See
[sharepoint_setup.md](sharepoint_setup.md). Never put access tokens, client
secrets, financial exports, databases, or generated reports in source control.

Update the production header, worksheet, required-field, amount tolerance,
date-window, and SharePoint source-folder mappings in
`config/column_mappings.yaml`. The synthetic mappings in
`config/synthetic_column_mappings.yaml` are fixture-only and are not a
representation of real processor formats.

## Status terminology

- **Fully Matched:** exact-key matching rules linked the required processor,
  bank, and GL evidence, with grouped amounts within tolerance.
- **Candidate match:** date proximity only; stays separate and requires human
  review. It never confirms a match.
- **Timing Difference:** exact identifiers/references and amounts support the
  connection, but settlement dates differ within the configured window.
- **Manual override:** separate append-only audit event; it does not replace
  the original algorithm status or raw evidence.
- **Unresolved exception:** any remaining missing, duplicate, mismatched, or
  invalid item requiring review.

See [architecture.md](architecture.md), [control_framework.md](control_framework.md),
[user_guide.md](user_guide.md), and [limitations.md](limitations.md).
