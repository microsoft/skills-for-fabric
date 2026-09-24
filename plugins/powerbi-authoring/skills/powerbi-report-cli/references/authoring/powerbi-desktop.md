# Power BI Desktop Preview Routing

## Contents

- [Canonical entry point](#canonical-entry-point)
- [Desktop operations](#desktop-operations)
- [Model-aware reload](#model-aware-reload)
- [Failures and diagnostics](#failures-and-diagnostics)

## Canonical entry point

Always route Desktop inspection through `powerbi-report-author preview`. Do not
invoke or describe the underlying `powerbi-desktop` bridge CLI directly, do not
select a Desktop PID, and do not translate a failed preview operation into a
direct bridge command.

Read `preview.md` for host selection, operation routing, safety gates, and
argument construction. Read `preview-part-02.md` for exact commands, lifecycle,
status handling, and errors. Read `preview-part-03.md` for screenshot artifact
handling.

## Desktop operations

Use the report folder or owning `.pbip` as `<folder>`:

| Intent | Canonical command |
|---|---|
| Status | `powerbi-report-author preview "<folder>" --host desktop --status` |
| Open or attach | `powerbi-report-author preview "<folder>" --host desktop` |
| Reload PBIR | `powerbi-report-author preview "<folder>" --host desktop --reload` |
| Reload PBIR and model files | `powerbi-report-author preview "<folder>" --host desktop --reload-with-model` |
| Capture one page | `powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>\page.png" --page "<page-id>"` |
| Capture all pages | `powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>" --all-pages` |

Open/attach, `--reload`, and `--reload-with-model` must pass the unsaved-changes
status preflight in `preview-part-02.md`. Screenshots are warm captures and must
not be preceded by an implicit status or reload operation.

## Model-aware reload

When TMDL or other semantic-model files changed, do not use plain `--reload`.
Follow Semantic-model reload workflow (see `preview-part-04.md`, section
`semantic-model-reload-workflow`). That workflow separates file loading from
model processing, requires the appropriate Calculate or targeted Full refresh,
verifies expected values with DAX, and then captures every affected report page.

## Failures and diagnostics

Treat the structured result from `powerbi-report-author preview` as the source
of truth. Follow the terminal and correction rules in `preview.md`; do not run
the direct bridge CLI, switch hosts, add PID selection, or replace the requested
operation with another lifecycle operation.
