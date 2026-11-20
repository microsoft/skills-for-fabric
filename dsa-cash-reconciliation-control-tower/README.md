# DSA Cash Reconciliation Control Tower

A Python prototype for controlled cash-reconciliation workflow development.
The September 2026 pilot currently exposes only local source profiling and
mapping validation; it does not run reconciliation or ingest transaction
rows. The reconciliation engine remains covered by synthetic tests, but is
deliberately not exposed in the pilot UI.

> **Configuration required:** `config/column_mappings.yaml` intentionally
> contains clearly marked header and worksheet placeholders. Replace them with
> approved source specifications before processing non-synthetic data. No
> tenant, site, drive, URL, account, or credential values are fabricated.

## September 2026 local-file pilot

The default and only active pilot intake mode is **Local Synced SharePoint
Folder**. Set `LOCAL_SHAREPOINT_ROOT` in `.env` or paste the synchronized
SharePoint path in the app sidebar. The app profiles matching workbooks
recursively, reads workbook metadata/headers in read-only mode, and offers a
downloadable Excel source-profile report. It does not edit, rename, move, or
save over source files.

Profile filename groups are `SnapPay AR Transaction*.xlsx`, `BMO
BLUEPAY*.xlsx`, `BLUEPAY Fiserv Bankcard*.xlsx`, `RC BLUEPAY
GENERAL*.xlsx`, and `G.L. 1.1070*.xlsx`. Filename-based adapter assignments
are suggestions that the reviewer may change. No production column mappings
are inferred from those names.

Use **Configuration Validation** to select worksheet names and map canonical
required/optional fields to headers observed in the scanned workbooks. The
page also shows confidence-rated proposals with their rationale and allows
editing and saving them as a separate, unapproved draft under ignored `data/`.
Drafts never change the active mapping. Mapping approval is an explicit
reviewer action; it is never automatic. Reconciliation is disabled in this
pilot UI. `RC BLUEPAY GENERAL` remains unassigned pending confirmation of its
provenance and amount/ledger rules, and is profiled separately from `G.L.
1.1070`. **Microsoft Graph** remains an optional future connector; the pilot
does not request Graph authentication or download files.

## Quick start

From this directory, install the prototype and test dependencies:

```powershell
python -m pip install -e ".[test]"
```

Copy `.env.example` to `.env` if it does not exist. Leave
`LOCAL_SHAREPOINT_ROOT=` blank if you prefer to enter the path in the app.
Otherwise set it to the local synchronized SharePoint folder. Graph credentials
are not required for this pilot.

Launch the dashboard from this project directory:

```powershell
streamlit run app.py
```

Select **Local Synced SharePoint Folder**, enter the local root, and choose
**Profile September 2026 source files**. Review all worksheet/header structures,
header-row placement, SnapPay daily-file consistency, and identifier-storage
risks. In **Configuration Validation**, review and optionally save the
proposed mappings as an unapproved draft. The app does not reconcile.

Run automated tests using synthetic workbooks created under pytest temporary
directories:

```powershell
pytest
```

## Runtime setup

The app uses the locally synchronized SharePoint folder and does not request
Graph authentication. Microsoft Graph is an optional future connector; see
[sharepoint_setup.md](sharepoint_setup.md) for its administrator-supplied
configuration. Never commit source files, extracted data, databases, reports,
or credentials.

The app saves explicit, reviewer-approved pilot mappings under ignored local
`data/approved_column_mappings.yaml`; it does not modify the tracked template.
The synthetic mappings in `config/synthetic_column_mappings.yaml` are for
tests only and are not a representation of real processor formats.

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
