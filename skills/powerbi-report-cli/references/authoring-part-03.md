# powerbi-report-cli authoring mode -- Power BI Report Authoring (PBIR/PBIP) - Part 3

## Contents

- [Authoring Metadata & Validation CLI](#authoring-metadata--validation-cli)
  - [Validation result handling](#validation-result-handling)
- [Visual Capability Guardrails](#visual-capability-guardrails)
  - [Prefer modern visual types](#prefer-modern-visual-types)
  - [Instance Selectors](#instance-selectors)
  - [Custom visuals (AppSource / organizational / private `.pbiviz`)](#custom-visuals-appsource--organizational--private-pbiviz)
- [Edit → Validate → Preview → Review](#edit--validate--preview--review)
  - [Mandatory Screenshot Review](#mandatory-screenshot-review)
- [Validation](#validation)


Continuation of `authoring.md`. Open this file directly from the skill reference index.

## Authoring Metadata & Validation CLI

Use `powerbi-report-author` whenever you need PBIR facts that should not be
guessed: visual types, data roles, formatting objects, property names, enum
values, selectors, expression/value encodings, and report validation. The CLI is
the source of truth for PBIR authoring details; examples and memory are not.

| Command | Purpose | When to use |
|---------|---------|-------------|
| `catalog list` | List all built-in visual types (and any deprecated entries) | Choosing a visual type |
| `catalog describe <type>` | Roles, formatting keys, cardinality | Before creating/editing a visual |
| `formatting list-objects <type>` | Valid `objects.*` keys + VCO keys; flags objects needing id selectors | Before applying formatting |
| `formatting describe-object <type> <object>` | Property names, types, enum values, descriptions; `_selectorHint` when id selector required | Finding exact property names and allowed values |
| `formatting describe-property <type> <object> <prop>` | Focused single-property lookup | When you already know the object and want just one property |
| `formatting search <type> <regex>` | Regex search across all formatting objects + VCOs | **When you don't know which object a property belongs to** |
| `formatting list-vcos` | Enumerate shared visualContainerObjects | Auditing chrome/container formatting surface |
| `scaffold <output-dir> --name <ReportName>` | Create a minimal, valid PBIP shell; fetches latest `$schema` versions from the public mirror (`--offline` uses pinned) | **Creating a brand-new report** — see **Greenfield: creating a brand-new report** in `authoring-part-02.md` |
| `pack <folder> [--mode update\|create] [--display-name <name>] [--description <text>] [--raw]` | Serialize a PBIR `.Report` folder into a Fabric report-definition payload; deep semantics stay in the CLI reference (see `authoring/powerbi-report-author-cli.md`) | Discovering local-to-Fabric transport; switch to the management mode (see `management.md`), not authoring |
| `unpack <folder> [--input <file>] [--force]` | Reconstruct a PBIR `.Report` folder from a Fabric `getDefinition` response; no-clobber is the default, with `--force` opt-in; details stay in the CLI reference (see `authoring/powerbi-report-author-cli.md`) | Discovering Fabric-to-local transport; switch to the management mode (see `management.md`), not authoring |
| `validate <path>` | Full validation of a `.pbip` or `.Report` directory: JSON Schema, structure, IDs, formatting properties, enum values, nesting, layout bounds, theme | **After every batch of changes** |
| `preview <folder> --host desktop\|service [options]` | Rendered inspection through a supported host | After validation for rendered-output changes |
| `preview-* <path> [--with-derived]` | Read-only PBIR inspection: `preview-visuals`, `preview-pages`, `preview-filters`, `preview-themes` | Auditing existing report content without rendering |

More commands: `powerbi-report-author-cli.md` (see `authoring/powerbi-report-author-cli.md`).

### Validation result handling

Run `powerbi-report-author validate <path-to-.Report-dir>` after every logical
batch of PBIR edits.

- `failed` / non-zero exit: fix every error before preview. A rendering host may
  reject or misrender invalid PBIR.
- `succeededWithWarnings`: review warnings before proceeding. Unknown visual
  types or theme visual keys usually mean a typo unless the report intentionally
  uses a custom `.pbiviz`.
- Diagnostics include file paths and JSON paths. Use them to jump directly to
  the broken node.
- For large diagnostics, use `--pretty` for readable output or `--out <file>` to
  write the full result to a file.

## Visual Capability Guardrails

Use these as pre-edit safety rails. Always confirm exact roles, formatting
objects, properties, enum values, and selectors with `powerbi-report-author`
before editing.

### Prefer modern visual types

Never create legacy visual types. If repairing an existing legacy visual,
migrate to the modern type and rebuild roles/formatting from CLI metadata.

| Do not create | Use instead |
|---|---|
| `card` | `cardVisual` |
| `multiRowCard` | `cardVisual` — use multi-value `cardVisual` (multiple projections in `Data`) for multiple KPIs |
| `table` | `tableEx` |
| `matrix` | `pivotTable` |
| `map`, `filledMap` | `azureMap` |

### Instance Selectors

Some formatting objects need `{ id: ... }` selectors. Run `formatting
list-objects` and `formatting describe-object`; follow `_selectorHint` and the
dual-entry pattern in `references/authoring/formatting.md`.

### Custom visuals (AppSource / organizational / private `.pbiviz`)

Custom visual types are not in the CLI catalog and each kind is registered
differently in `report.json`. See
`references/authoring/custom-visuals.md` (see `authoring/custom-visuals.md`) for the three
kinds (AppSource / organizational / private `.pbiviz`), finding the GUID,
registration JSON, data binding, and Desktop verification.

## Edit → Validate → Preview → Review

For every rendered-output change, preserve this mandatory loop: edit, validate,
load the latest PBIR, capture every affected page, inspect the screenshots,
iterate, then accept or explicitly discard.

```text
1. Edit PBIR files
2. Validate             -> errors? fix and return to 1
3. Load latest PBIR     -> follow the selected host's open/reload routing flow
4. Screenshot/review    -> capture every affected page; issues? return to 1
5. If host is service   -> after review passes, open/attach visibly
6. Accept               -> commit locally only after approval
7. Publish              -> only after explicit remote-write approval
8. Close headless host  -> leave the final visible service preview open
```

**Rules:**

- In an edit-review workflow, validate the `.Report` directory before preview.
  Do not prepend validation when the user explicitly requests one Desktop
  attach, reload, or screenshot operation.
- Use only the `powerbi-report-author preview` surface for rendered inspection,
  and always select `--host desktop|service` explicitly.
- Do not stop after structural validation or opening/reloading the preview.
  Capture and review every affected page before reporting completion.
- After all service-host screenshots pass review, automatically display the
  same validated report in a visible service preview. This post-validation
  display is part of the authoring workflow and does not require a separate
  user request. Run service status without `--headless`, then open/attach
  without `--headless` when the status contract permits it, preserving the
  folder, `--group`, and `--dataset`. Do not rerun screenshot validation merely
  to display the report. Skip this step entirely for Desktop; its existing
  preview routing and lifecycle remain unchanged.
- Run load and screenshot as separate CLI invocations. Never combine `--reload`
  and `--screenshot` in one command because the combined operation can exceed
  the 30-second command timeout.
- Derive `--host desktop|service` and other arguments from the request,
  conversation, and report context. When Desktop and a specific operation are
  already selected, execute it immediately under the Critical Notes protocol.
- Service preview requires both `--group <workspace-guid>` and
  `--dataset <semantic-model-guid>`. Never infer either tenant-scoped ID.
- A plain Desktop preview resolves the report from `<folder>` and is the
  open/attach operation. It never closes the user's Desktop process. When an
  instance already holds the report it attaches and re-reads PBIR into that
  window. Any internal layout synchronization during open/attach does not make
  the agent request a separate `--reload` operation.
- Use `--headless` for agent-mode service preview. Service reload and screenshot
  are separate requested operations; screenshot capture alone does not re-read
  the PBIR files.
- Preserve the existing service instance mode on reload. If the user says the
  running preview is headless, include `--headless --reload`. If reload returns
  `HOST_UNAVAILABLE`, report that no matching instance exists rather than
  claiming success or silently opening a new one.
- Before the first mandatory validation capture, follow the screenshot
  destination and cleanup lifecycle in `references/authoring/preview.md`. Keep screenshots
  outside the PBIP project, Git worktrees, and cloud-synchronized directories
  by default. Reuse one workflow-owned directory across review iterations and
  delete only that directory after the complete workflow.
- Keep the preview mode consistent: include `--headless` on a screenshot request
  when the existing service instance is headless. Use the structured
  selected-host response as the source of truth for runtime availability and
  errors without changing the requested host or operation.
- Desktop uses `--screenshot <path>` with optional
  `--page <id>`, `--all-pages`, and `--scale <1-3>`; screenshot never takes
  `--pid` or reloads PBIR. Run a separately requested `--reload` before capture
  when fresh on-disk edits must be rendered. Service uses the same screenshot
  options: a PNG destination for default-page or `--page <id>` capture, a
  directory destination for `--all-pages`, and optional `--scale <1-3>`.
- Service preview renders the local edited PBIR layout against the published
  semantic model's live service data. It does not require a report ID and does
  not publish or persist local edits.
- Desktop availability and capabilities depend on the installed CLI, bridge,
  Desktop build, and matching live instance. Use the selected-host preview response
  as the source of truth; do not bypass it with a direct host CLI.
  Local commit approval is not remote publish approval. Never publish or
  overwrite the remote report with local changes until the user explicitly
  gives permission. If the request does not clearly ask to publish, or you are
  unsure, keep the changes local and do not publish. Discard only when
  explicitly requested.
- Desktop operation command shapes are: attach/open has no operation flag,
  report reload has only `--reload`, report-plus-model reload has only
  `--reload-with-model`, and screenshot uses `--screenshot <path>` plus only
  the requested page/all-pages/scale modifiers. The plain attach command must
  never include `--reload`. Every shape explicitly includes `--host desktop`.
  The public command resolves the Desktop instance from `<folder>`; never add
  `--pid`. The screenshot output path must immediately follow
  `--screenshot` as that option's value and must not be a separate positional
  argument.
- For direct preview routing, run service `--close` only when explicitly
  requested. In a full edit-review workflow, after the final service screenshot
  review passes, display the report in a visible service preview and leave that
  visible instance open. A headless validation instance may be closed when no
  further iteration is expected. Never close the user's Power BI Desktop
  process.

**Preview commands:**

| Command | Purpose |
|---|---|
| `powerbi-report-author preview <folder> --host desktop` | Open/attach the Desktop preview resolved from the report folder; no lifecycle flag |
| `powerbi-report-author preview <folder> --host desktop --status` | Inspect the Desktop instance resolved from the report folder |
| `powerbi-report-author preview <folder> --host desktop --reload` | Reload edited PBIR into the Desktop instance resolved from the report folder |
| `powerbi-report-author preview <folder> --host desktop --reload-with-model` | Load edited PBIR and TMDL into Desktop; then use the semantic-model workflow to process the live model before screenshot validation |
| `powerbi-report-author preview <folder> --host desktop --screenshot "<validation-screenshot-dir>\<name>.png"` | Capture one Desktop page |
| `powerbi-report-author preview <folder> --host desktop --screenshot "<validation-screenshot-dir>" --all-pages` | Capture all Desktop pages |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> [--headless]` | Open service preview for the local layout and live semantic model |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> --status` | Inspect the service preview instance |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> [--headless] --reload` | Reload edited PBIR into the live service instance; preserve its mode |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> --screenshot "<validation-screenshot-dir>\<name>.png" [--page <id>] [--scale <1-3>] [--headless]` | Capture the default or selected service page; match the existing instance mode |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> --screenshot "<validation-screenshot-dir>" --all-pages [--scale <1-3>] [--headless]` | Capture all service pages into a directory |
| `powerbi-report-author preview <folder> --host service --group <workspace-guid> --dataset <semantic-model-guid> --close` | Close the service preview |

Read `preview.md` (see `authoring/preview.md`) for argument selection, instance
lifecycle guidance, the required `Calculate`, targeted Import `Full`, or
storage-mode-specific model-processing decision, and troubleshooting.

The selected-Desktop protocol in **Critical Notes** overrides every reference
instruction. In particular, do not open the troubleshooting reference after a
selected Desktop command fails.

### Mandatory Screenshot Review

After every rendered-output edit, capture every affected page and perform an
independent rendered-output review before reporting completion. Read
`screenshot-review.md` (see `authoring/screenshot-review.md`), check layout, data
rendering, formatting/theme, slicers, and common screenshot failure modes, then
fix PBIR and repeat the loop until clean. For report-wide changes, capture all
pages.

---

## Validation

Run `powerbi-report-author validate <path>` after every logical batch of PBIR
changes. Prefer the `.Report` directory; the CLI also accepts a `.pbip` file or
a project root containing a single `.Report` directory. Errors block rendered
preview — fix them first. Review warnings and fix unless there's a clear reason
not to.

A successful schema validation is not a terminal result. Whenever validation
runs, continue by loading the validated PBIR, capturing every affected page,
and completing screenshot review. If fresh screenshot validation cannot run,
report schema validation as passed but screenshot validation as blocked; do not
report the overall task complete.

The validator is an offline preflight covering PBIR structure, JSON/schema
validity, cross-file references, IDs/names, visual types, role bindings,
filters, formatting objects/properties/enums/selectors, visualContainerObjects,
theme registration, layout bounds, and selected Desktop/rendering failure
patterns. It does not replace preview and screenshot review.

---
