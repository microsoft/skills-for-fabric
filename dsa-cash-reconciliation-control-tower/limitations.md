# Limitations and production hardening

This is a controlled prototype, not a certified financial system or a
replacement for Finance's approved close controls.

- Production source headers, worksheets, signed amount conventions, statuses,
  period/date semantics, tolerance, settlement window, and SharePoint paths
  are unknown. The production YAML is an explicit placeholder and must be
  completed and independently approved.
- The sample uses synthetic data only. There are no real account numbers,
  tenant values, processor schemas, credentials, or transaction workbooks.
- Numeric spreadsheet identifiers may already have lost leading zeros before
  ingestion; configure upstream exports to store identifiers as text.
- The file-level SharePoint modified-date filter can exclude a file with
  in-period transactions if that file was last modified outside the period.
  Row transaction/posting date is the authoritative processing filter.
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
- Interactive delegated auth is designed for a local prototype. Tokens are
  ephemeral, Streamlit deployment/authentication is not hardened, and the app
  is not suitable for unattended scheduled production ingestion.
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
