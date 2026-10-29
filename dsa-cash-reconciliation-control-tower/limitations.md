# Limitations and production hardening

This is a controlled prototype, not a certified financial system or a
replacement for Finance's approved close controls.

- Headers and worksheet layouts have been profiled from the local August
  workbooks, but the proposed mappings are unapproved. Signed amount
  conventions, status meanings, and period/date semantics still require
  source-owner and Finance confirmation. The production YAML remains an
  explicit placeholder and must be completed and independently approved.
- The sample uses synthetic data only. There are no real account numbers,
  tenant values, processor schemas, credentials, or transaction workbooks.
- Numeric spreadsheet identifiers may already have lost leading zeros before
  ingestion; configure upstream exports to store identifiers as text. The
  metadata profiler flags numeric identifier columns but cannot recover a
  zero that was discarded before the workbook was created.
- The active September 2026 pilot profiles local synchronized `.xlsx` files by
  filename only. It does not verify reporting-period dates or reconcile
  transaction data; September labeling is a pilot workflow label, not a date
  control.
- Amount tolerance and grouping behavior require Finance validation.
  Backend/customer reference grouping may be ambiguous when references are
  reused; the exact key must be approved per real source.
- Duplicate transaction IDs are flagged, not auto-resolved. Reversal/refund/
  reject classification uses configured status text containing those terms;
  production code should map the actual status taxonomy explicitly.
- Date candidates are intentionally broad within source/date windows and are
  not prioritized by score. They are review suggestions only, never confirmed.
- SQLite is suitable for a single-user prototype only; no concurrent-writer,
  multi-user authorization, retention, backup, encryption-at-rest, or
  high-availability policy is implemented.
- Manual override approval is captured but not enforced as a two-person
  workflow. Application login, role-based access, segregation of duties,
  immutable external audit retention, and approval routing are future work.
- Microsoft Graph is optional future integration and is not used by the active
  local synchronized-folder pilot. If enabled later, delegated auth and
  Streamlit deployment need security hardening before production.
- Delta-token persistence is a foundation only; there is no scheduler, delta
  retry/expiry recovery, deletion handling, or automatic incremental
  reconciliation.
- Source row normalization handles common date and decimal forms; locale- and
  source-specific conventions need tests and approval before use.
- Excel uses ordinary workbook sheets; it is not digitally signed or
  protected from reviewer edits. The exported report should be retained under
  a Finance-approved evidence process.
- The completeness bridge proves each retained source row is categorized
  exactly once; it does not itself prove the economic validity of each match
  or equality among the four source populations.

Before production use, complete threat modeling and security review, validate
all source mapping and control assumptions with Finance, add deployment
authentication/authorization and audit controls, establish protected storage
and retention, and run parallel reconciliation against the existing approved
process.
