# `powerbi-report-author` CLI Reference

## Contents

- [Command catalog](#command-catalog)
- [Rendering preview vs PBIR inspection commands](#rendering-preview-vs-pbir-inspection-commands)
- [Validation result handling](#validation-result-handling)
- [Preview result handling](#preview-result-handling)
  - [Screenshot options](#screenshot-options)


Use this file when the root command table is not enough. The CLI is the source
of truth for visual roles, formatting objects, property names, enum values,
selectors, expression/value encodings, and PBIR validation.

## Command catalog

| Command | Purpose | When to use |
|---|---|---|
| `--help` / `<command> --help` | Show syntax and available flags | Before using an unfamiliar non-preview command or before the preview host/operation is selected; never before an explicit Desktop operation |
| `catalog list` | List all built-in visual types and deprecated entries | Choosing a visual type |
| `catalog describe <type>` | Roles, formatting keys, cardinality | Before creating/editing a visual |
| `formatting list-objects <type>` | Valid `objects.*` keys + VCO keys; flags objects needing id selectors | Before applying formatting |
| `formatting describe-object <type> <object>` | Property names, types, enum values, descriptions; `_selectorHint` when id selector required | Finding exact property names and allowed values |
| `formatting describe-property <type> <object> <prop>` | Focused single-property lookup | When you already know the object and want one property |
| `formatting search <type> <regex>` | Regex search across formatting objects + VCOs | When you do not know which object a property belongs to |
| `formatting list-vcos` | Enumerate shared visualContainerObjects | Auditing chrome/container formatting surface |
| `formatting effective-properties <type>` | Flattened visual objects + shared VCOs | One-shot snapshot of every formatting surface for a visual |
| `expr encode --kind <t> <v> [percent]` | Generate correct PBIR value encoding | Writing formatting values |
| `expr decode '<json>'` | Decode a PBIR expression to plain value | Inspecting existing formatted values |
| `theme encode --kind <t> <v>` | Generate the plain-JSON value used inside a theme file | Editing theme JSON |
| `theme shade-color <hex> <percent>` | Apply ThemeDataColor shadeColor adjustment | Previewing tinted/shaded theme colors |
| `text measure "<label>" [--font <name>] [--size <pt>] [--px] [--bold] [--italic] [--weight <kw>] [--icon] [--hpad <px>] [--margin <frac>] [--font-file <path>]` | Measure a label's rendered width from the installed font's real advance widths (falls back to a labeled per-character approximation when the font is not installed) and recommend a button width | Sizing text-bearing visuals (buttons) so labels don't clip — instead of a flat character-count estimate |
| `scaffold <output-dir> --name <ReportName> [--model-path ../<Model>.SemanticModel] [--page-name <name>] [--offline] [--force]` | Create a minimal, valid PBIP shell; fetches latest `$schema` versions live from the public `microsoft/json-schemas` mirror (falls back to pinned, or `--offline` to force pinned), then self-validates offline | Creating a brand-new (greenfield) report |
| `pack <folder> [--mode update\|create] [--display-name <name>] [--description <text>] [--raw]` | Serialize a PBIR report (a `.pbip`, a `.Report` directory, or a directory containing `definition/`) into a Fabric report-definition payload; default output is a `{data:...}` envelope and `--raw` emits the raw body for pipe UX; PBIR-oriented: pack collects only qualifying PBIR parts and performs no format check, so a legacy `.Report` that still has `definition.pbir` packs a partial payload instead of failing, and callers must confirm a modern `definition/` layout before packing | Pack serializes qualifying PBIR parts from a .Report folder into a Fabric report-definition payload for pipe or file-based transport |
| `unpack <folder> [--input <file>] [--force]` | Reconstruct a PBIR `.Report` folder from a Fabric `getDefinition` response read from stdin or `--input`; no-clobber is the default, and `--force` stages then swaps overwrites; PBIR-only, rejecting PBIR-Legacy with `UNPACK_FORMAT_UNSUPPORTED` | Unpack reconstructs a PBIR .Report folder from a Fabric getDefinition response read from stdin or --input |
| `validate <path>` | Full validation of a `.pbip` or `.Report` directory | After every batch of PBIR edits |
| `preview --list-hosts` | List available rendering hosts and their capabilities | When preview availability or capability support is unknown |
| `preview <folder> --host service --group <id> --dataset <id> --status` | Inspect service preview status without taking a screenshot | Before service open/reload and when the user explicitly requests status |
| `preview <folder> --host service --group <id> --dataset <id> --screenshot "<validation-screenshot-dir>\<name>.png" [--page <id>] [--scale <1-3>] [--headless]` | Capture the default or selected service page into the workflow-owned validation directory | After validation and reload for rendered-output changes |
| `preview <folder> --host service --group <id> --dataset <id> --screenshot "<validation-screenshot-dir>" --all-pages [--scale <1-3>] [--headless]` | Capture all service pages into the workflow-owned validation directory | For full-report rendered validation |
| `preview <folder> --host desktop` | Open/attach the Desktop instance resolved from the report folder; no lifecycle flag | Requires the owning `.pbip` |
| `preview <folder> --host desktop --status` | Inspect the Desktop instance resolved from the report folder; reports `details.hasUnsavedChanges` | When Desktop instance state is unclear, and as the preflight before any `--reload`, `--reload-with-model`, or bare `preview` |
| `preview <folder> --host desktop --reload` | Reload the latest PBIR layout into Desktop | After editing the report definition |
| `preview <folder> --host desktop --reload-with-model` | Load the latest PBIR layout and on-disk semantic-model definition into Desktop; does not process the live model | After validating a local TMDL change; then follow Semantic-model reload workflow (see `preview-part-04.md`, section `semantic-model-reload-workflow`) |
| `preview <folder> --host desktop --screenshot "<validation-screenshot-dir>\<name>.png" [--page <id>] [--scale <1-3>]` | Capture one Desktop page into the workflow-owned validation directory | After the latest layout is loaded |
| `preview-visuals <path> [--with-derived]` | Enumerate every visual with stable summary fields + path to JSON | Auditing visuals across a report |
| `preview-pages <path> [--with-derived]` | Page metadata summary | Quick page overview |
| `preview-filters <path>` | Enumerate report/page/visual filters | Filter audit |
| `preview-themes <path> [--with-derived]` | Registered custom theme summary | Theme audit |
| `doctor` | Environment self-check | First-run setup or troubleshooting |

## Rendering preview vs PBIR inspection commands

`preview` is the **rendering** command. Both hosts support preview, `--status`,
`--reload`, and screenshot capture; the service host additionally supports
`--close`. Compatible Desktop hosts also support `--reload-with-model`; the
service host reports `modelDefinitionReload: false`. Desktop screenshot uses
`--screenshot <path>` with
optional `--page`, `--all-pages`, and `--scale`.
Desktop screenshot is a warm capture and does not reload PBIR. Service uses the
same `--screenshot <path>` flag and supports default-page, `--page`,
`--all-pages`, and `--scale` capture.

Despite their shared prefix, `preview-visuals`, `preview-pages`,
`preview-filters`, and `preview-themes` are read-only PBIR metadata inspection
commands. They enumerate report definitions on disk; they do not contact
Desktop or service and do not produce report screenshots.

When the user has selected a host and requested attach/open, reload, or
screenshot, run only the matching host-specific command. Do not precede it with
`--help`, `--list-hosts`, validation, or another lifecycle operation. The one
call that precedes open/attach or reload is selected-host `--status`; never run
it before a screenshot. If status reports
`details.hasUnsavedChanges: true`, do not run open/reload automatically.
Structured `HOST_UNAVAILABLE` additionally permits open/attach, but not reload.
Interpret a host that does not currently expose unsaved state according to its
availability response. Otherwise report the safety-gate failure and stop
without asking whether automatic open/reload should proceed anyway. See
preview.md (see `preview.md`). After the operation runs, a failure without an
explicit machine-readable
`correction` object is terminal: make no further tool calls. Error text, hints,
usage output, unknown-option responses, and suggestions to run help are not
structured corrections. When that object is present, change only its named
value and preserve the operation, host, folder, screenshot destination, and all
other arguments. This terminal rule overrides all discovery, status, and
troubleshooting guidance.

Every Desktop command explicitly contains `--host desktop`. The public command
resolves the Desktop instance from `<folder>` and does not accept `--pid`. Desktop
screenshot contains `--screenshot "<path>"`; the output path is the value of
`--screenshot`.

For a screenshot request, every executed command must retain the selected
host's exact screenshot syntax and destination. Patch an allowed retry from the
original command; do not execute attach, reload, status, close, help, or
discovery instead.

The requested host and operation are immutable, including during a corrected
retry. Never switch Desktop to service or substitute another lifecycle
operation. Preserve the host-specific screenshot destination, supported
modifiers, service bindings, and headless mode exactly.

Attach/open/connect/show maps to the plain Desktop command. Do not append
`--reload`. Use `--reload` only for an explicit report reload or refresh
request. Use `--reload-with-model` only when local TMDL changed and both the
report and semantic-model definitions must be loaded.

```bash
powerbi-report-author preview --list-hosts
```

Desktop direct operations:

```bash
powerbi-report-author preview "<folder>" --host desktop
powerbi-report-author preview "<folder>" --host desktop --status
powerbi-report-author preview "<folder>" --host desktop --reload
powerbi-report-author preview "<folder>" --host desktop --reload-with-model
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>\page.png"
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>\page.png" --page "<page-id>"
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>" --all-pages
```

Service operations:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --reload
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --screenshot "<validation-screenshot-dir>\page.png"
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --screenshot "<validation-screenshot-dir>\page.png" --page "<page-id>" --scale 2
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --screenshot "<validation-screenshot-dir>" --all-pages --scale 2
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --close
```

Service preview renders the local edited PBIR layout against the live service
data of a published semantic model identified by `--dataset`, in the workspace
identified by `--group`; it does not publish or persist local report edits and
does not require a report ID. Never infer either tenant-scoped ID. If
`REPORT_NOT_PUBLISHED` indicates that the semantic model is unavailable,
resolve or publish that prerequisite
through its owning report-management workflow only when explicitly authorized;
never publish local report WIP as a preview side effect. Service screenshot
supports default-page, selected-page, all-pages, and scale capture. Desktop
availability and capabilities depend on the installed CLI, bridge, Desktop
build, and matching live instance. A plain Desktop preview is the open/attach
operation, but the skill issues it only after the strict status preflight passes
with boolean `false`; it never closes Desktop. A separately requested reload
updates report layout only. `--reload-with-model` updates report layout and
requests that Desktop also reload the on-disk semantic-model definition. It
does not refresh model data or prove freshness. After it succeeds, follow
Semantic-model reload workflow (see `preview-part-04.md`, section
`semantic-model-reload-workflow`): `Calculate` for metadata and
calculated-object changes, targeted `Full` for changed/new imported columns and
import partitions, or the storage-mode-specific semantic-model workflow for
non-Import models. Use the structured preview response as the source of truth
and do not bypass the preview command with a direct host command. Always pass
`--host` rather than relying on the command default. Keep `--headless`
consistent between opening and screenshot
capture or reload so the CLI preserves the service instance mode. For a
screenshot on either host, the requested command itself is the first and only
command unless its result supplies a structured correction. Open/attach and either reload form first run the selected-host `--status`
preflight. If the selected host
reports unsaved state, proceed only when `details.hasUnsavedChanges` is boolean
`false`; structured `HOST_UNAVAILABLE` also permits open/attach, but not either
reload form.
A corrected retry must keep every non-corrected argument unchanged.
For mandatory authoring validation, resolve every screenshot destination
through the external workflow-owned lifecycle in preview.md (see `preview.md`). Use
one `<validation-screenshot-dir>` per report and never use a
current-directory-relative or PBIP-local path.
See preview.md (see `preview.md`) for host and argument selection.

## Validation result handling

Run `powerbi-report-author validate <path-to-.Report-dir>` after every logical
batch of PBIR edits.

- Fix every error before rendered preview.
- Review warnings before proceeding. Unknown visual types or theme visual keys
  usually mean a typo unless the report intentionally uses a custom `.pbiviz`.
- Diagnostics include file paths and JSON paths. Use them to jump directly to
  the broken node.
- For large diagnostics, use `--pretty` for readable output or `--out <file>` to
  write the full result to a file.

## Preview result handling

### Screenshot options

`--screenshot <path>` is the capture operation and carries its destination as
the flag's value. `--page`, `--all-pages`, and `--scale` are **gated on it**,
not siblings of it. There is no `preview screenshot …` subcommand; every capture
is a `preview` invocation carrying `--screenshot`.

```text
--screenshot <path>                 the capture operation; <path> is its destination
├── <file>.png                      destination for a default-page or --page capture
├── <directory>                     destination for an --all-pages capture
├── (page selection)                OPTIONAL — at most one of the two
│   ├── --page <id>                 one page, by page ID or display name
│   └── --all-pages                 every page, one PNG each, into the directory
└── --scale <1-3>                   OPTIONAL — both hosts; host default 2
```

Omitting page selection captures the default page. Violations come back as
structured errors, not free text: a screenshot-only option without
`--screenshot`, an empty `--screenshot ""` destination, and `--page` combined
with `--all-pages` each return `INVALID_OPTION` with a `correction` object
naming the offending parameter; a `--scale` outside 1-3 returns
`PARAMETER_FORMAT_INVALID`. `--screenshot` with no value at all is a parser
error, `INVALID_USAGE`, and carries no correction — so it is terminal.

Service preview also requires `--group <workspaceId>` and `--dataset <datasetId>`
and a signed-in Azure CLI. If either ID is missing, ask for it immediately
without searching project files, running `--list-hosts`, or invoking preview.
Service and Desktop both support `--page`, `--all-pages`, and `--scale`.
`powerbi-report-author preview` is the intended interface for every Desktop
operation, including reading
Desktop's unsaved-changes flag, which `--status` reports at
`details.hasUnsavedChanges`. It takes no `--pid` and does not need one: it
resolves the instance from the report folder you pass, so several Desktop
windows holding *different* reports are matched correctly on their own. The one
shape it cannot resolve is two or more windows holding the *same* report folder.
There it refuses to guess and fails `HOST_UNAVAILABLE` ("Several Power BI
Desktop instances have this report open."), carrying the candidate pids in
`details.candidatePids` — so not even that case needs the bridge to identify
the windows. Resolving it is the user's call: show them the candidates and ask
them to close the others so exactly one window holds the report. Never close or
kill one yourself. No preview or bridge command closes the user's Desktop, and a
window you discard may hold unsaved work. Return to `preview` for the operation
itself once exactly one window remains.

The direct bridge fallback is isolated in
`powerbi-report-author-cli-part-02.md`. Do not open it for normal Desktop
operations or after a terminal preview failure.
