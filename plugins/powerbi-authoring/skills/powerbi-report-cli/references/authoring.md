<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `authoring` mode. -->

# powerbi-report-cli authoring mode -- Power BI Report Authoring (PBIR/PBIP)

This skill enables reading, editing, and creation of Power BI report
definition files in the **PBIR (Power BI Report)** format used by **PBIP
(Power BI Project)** files.

## Must/Prefer/Avoid

### MUST

- Use this skill only for concrete PBIR/PBIP report-file mechanics such as pages, visuals, filters, slicers, navigation, bookmarks, themes, formatting, validation, Desktop reloads, and screenshots.
- Validate PBIR with `powerbi-report-author validate` after each logical batch.
- Use `powerbi-desktop` reload/screenshot workflows for rendered-output changes.
- Use CLI capability lookup before writing visual roles, formatting objects, enum values, selectors, or expression encodings.

### PREFER

- Start from an approved `Design Brief:` or `_brief/report-spec.md` for greenfield report builds.
- Route visual-design uncertainty to the `design` mode before writing files.
- For semantic model metadata or model-side changes, use a semantic-model authoring skill, Power BI Modeling MCP, or local TMDL files when available.

### AVOID

- Do not guess PBIR JSON from memory when CLI metadata or reference files are available.
- Do not use only this skill for open-ended design, report planning, or Fabric report item CRUD; pair it with the `design` mode, the `planning` mode, or the `management` mode.

## Quick Start Workflow

0. **Plan/design routing** → for greenfield builds, read the `planning` mode
   first; for theming, visual style, layout, redesigns, or critiques, read
   the `design` mode. Return here for PBIR mechanics. Before authoring,
   use the `Design Brief:` yaml block from `_brief/report-spec.md` (or an
   approved inline `Design Brief:` block in the conversation) as implementation
   context.
1. **Set up/update CLIs** → before first use, confirm `powerbi-report-author`
   and the global `powerbi-desktop` command are available; see
   [CLI Setup](#cli-setup).
2. **Understand the model** → use the Semantic Model MCP Server/skill if available,
   or read TMDL files directly for table/column/measure names
3. **Desktop context** → for live Desktop status, opening PBIP/PBIX files,
   reloads, screenshots, or visual verification, use the
   `powerbi-desktop` CLI from `@microsoft/powerbi-desktop-bridge-cli`; see
   [Edit → Validate → Reload → Screenshot Loop](#edit--validate--reload--screenshot-loop).
4. **Route by intent** → use [Topic Files and Examples](#topic-files-and-examples) to pick the relevant
    guide.
5. **Use CLI metadata** → use [Authoring Metadata & Validation CLI](#authoring-metadata--validation-cli)
   for exact visual roles, formatting objects, property names, enum values, and
   selector requirements; do not infer these from memory.
6. **Check common pitfalls** → read [Anti-Patterns and Pitfalls](#anti-patterns-and-pitfalls)
   before editing or validating when the change touches visuals, bindings,
   filters, formatting, layout, or Desktop rendering.
7. **Validate** → run `powerbi-report-author validate <path-to-.Report-dir>`
   after every logical batch of PBIR changes; see [Validation](#validation).
8. **Verify rendering** → for any rendered-output change, use `powerbi-desktop`
     reload + screenshots; see [Edit → Validate → Reload → Screenshot Loop](#edit--validate--reload--screenshot-loop)
     and [Screenshot Review](#screenshot-review). Do not proceed until both
     validation and visual review pass. For dashboard/report builds, page
     scaffolding is not completion — each requested page needs data-bound visuals.
9. **Report back** → give the user a concise summary of what was done and any
      issues encountered (major and minor).

## Topic Files and Examples

Use the user's intent to choose the relevant topic file(s) before editing:

| File | When to read |
|------|-------------|
| [`authoring-workflows.md`](authoring/authoring-workflows.md) | Adding/modifying pages, visuals, drillthrough, interactions — includes complete JSON examples |
| [`powerbi-desktop.md`](authoring/powerbi-desktop.md) | Live Desktop verification — `powerbi-desktop` commands, PID selection, reload, screenshots, errors, troubleshooting |
| [`screenshot-review.md`](authoring/screenshot-review.md) | Screenshot review checklist and rendered-output troubleshooting after Desktop screenshot capture |
| [`formatting-overview.md`](authoring/formatting-overview.md) | **Read first for appearance changes** — cascade model, encoding rules, selectors, routing to other formatting files |
| [`formatting.md`](authoring/formatting.md) | Editing `visual.json` appearance — selectors, VCOs, encoding mechanics, background-image routing, cascade |
| [`color-strategy.md`](authoring/color-strategy.md) | Chart data point colors — theme `dataColors` vs `dataPoint.defaultColor` vs `dataPoint.fill` with selectors, cross-visual measure-color consistency |
| [`conditional-formatting.md`](authoring/conditional-formatting.md) | Data-driven formatting — color gradients (FillRule), rules-based, icon sets, data bars, web URL, field value |
| [`page-formatting.md`](authoring/page-formatting.md) | Editing `page.json` appearance — canvas background, wallpaper, page background images |
| [`filter-pane.md`](authoring/filter-pane.md) | Filter pane (`outspacePane`) and filter card (`filterCard`) chrome — Applied/Available state styling, pane width, search/checkbox colors |
| [`theming.md`](authoring/theming.md) | Creating or editing `theme.json` — dataColors, textClasses, visualStyles, style presets, ThemeDataColor reference |
| [`re-theming.md`](authoring/re-theming.md) | **Switching themes on a report with existing visuals** — re-theming workflow (color mapping + bulk sweep), dark mode checklist, dark↔light polarity changes. Pair with `theming.md` when changing colors on a report with per-visual overrides. |
| [`expressions.md`](authoring/expressions.md) | Building field references (Column, Measure, Aggregation, Hierarchy) and sort definitions |
| [`filters.md`](authoring/filters.md) | Adding/modifying filters — includes complete JSON examples |
| [`slicers.md`](authoring/slicers.md) | **Read first** when adding/modifying slicers or slicer selections — agent workflow, JSON templates, selection config |
| [`cartesian.md`](authoring/cartesian.md) | Adding bar, column, line charts — families, roles, query patterns (multi-measure, drill hierarchy, date hierarchy), formatting |
| [`map.md`](authoring/map.md) | Adding map visuals — template, roles, geocoding workflow, handling render failures |
| [`card.md`](authoring/card.md) | Adding or formatting KPI/card visuals — `cardVisual`, id selectors, callout/value sizing, accent bars |
| [`table.md`](authoring/table.md) | Adding or formatting tables/matrices — `tableEx`, `pivotTable`, grow-to-fit columns, row banding |
| [`image.md`](authoring/image.md) | Adding image visuals — local resources, URLs, data-bound images, ImageUrl validation/refusal workflow; also plot area background images for chart visuals |
| [`shape.md`](authoring/shape.md) | Adding shape visuals — containers, dividers, backgrounds, reference-image matching |
| [`textbox.md`](authoring/textbox.md) | Adding static or dynamic textbox visuals — paragraphs, text runs, and bound value expressions |
| [`version-control.md`](authoring/version-control.md) | Git branching, committing, reverting — read when the task involves version control or safe rollback planning |

### Greenfield / Design Handoff

> This skill owns PBIR file mechanics once the work is concrete: page/visual
> JSON, bindings, filters, slicers, themes, formatting, navigation, bookmarks,
> validation, Desktop reloads, and screenshots.
>
> Use the `planning` mode before authoring for new report/dashboard
> requests, requirements gathering, dependency checks, approval, or end-to-end
> build sequencing. Use the `design` mode for open-ended visual design,
> redesign/restyle, brand/theme direction, chart selection, or layout critique.
> Return here once there is an approved spec/design brief or a concrete PBIR
> edit to implement — see Quick Start step 0 for how to consume the brief.

### Large Build Execution

For full report/PBIP builds, do **not** delegate complete PBIP generation to a
subagent — the owning agent must keep the design brief, model inventory,
cross-page consistency, validation loop, and Desktop verification coordinated.

When context or repetition is the constraint, prefer a deterministic Node.js
generator that reads the approved design brief and writes PBIR JSON. If
delegation is still useful, split it by page or visual family and give each
subagent the relevant brief excerpt, exact fields/measures, and layout/visual
contract; have it return scoped PBIR JSON or a patch for the owning agent to
integrate and validate.

## CLI Setup

**Prerequisite: Node.js 20 or later.** Check with `node --version`. If missing
or older, install from [nodejs.org](https://nodejs.org/) or via your package
manager — Windows: `winget install OpenJS.NodeJS.LTS`; macOS: `brew install node`;
Linux: distro package or [nodesource](https://github.com/nodesource/distributions).

Before using the CLIs in a session, ensure the latest global versions are
installed:

```bash
npm install -g @microsoft/powerbi-report-authoring-cli@latest @microsoft/powerbi-desktop-bridge-cli@latest
```

Confirm both are on `PATH`:

```bash
powerbi-report-author --version
powerbi-desktop --version
```

## PBIR File Layout

A PBIP project on disk looks like this:

```text
<Report>.pbip                              # Project manifest
├── <Report>.Report/
│   ├── .platform                          # Fabric metadata (type, logicalId)
│   ├── definition.pbir                    # Report → SemanticModel binding
│   ├── definition/
│   │   ├── version.json                   # Format version (e.g. "2.0.0")
│   │   ├── report.json                    # Report-level: themes, settings, resources
│   │   └── pages/
│   │       ├── pages.json                 # Page order + active page name
│   │       └── <pageId>/
│   │           ├── page.json              # Page: displayName, size, type, filters
│   │           └── visuals/
│   │               └── <visualId>/
│   │                   └── visual.json    # Visual: type, position, query, formatting
│   ├── CustomVisuals/                     # Third-party .pbiviz packages
│   └── StaticResources/
│       ├── SharedResources/BaseThemes/    # Built-in base themes
│       └── RegisteredResources/           # User images, custom theme JSON
└── <Report>.SemanticModel/                # OUT OF SCOPE
```

### Key Files

| File | Purpose | Agent rule |
|------|---------|------------|
| `.platform` | Fabric/PBIP report item metadata | Keep it with the `.Report` folder |
| `definition.pbir` | Report → semantic model binding via `byPath` or `byConnection` | Preserve schema/version unless intentionally migrating |
| `version.json` | PBIR format metadata | Preserve the full scaffolded file, including `$schema` |
| `report.json` | Report-level settings, themes, resources | Edit through references and validate after changes |
| `pages.json` | Page order and active page | Add every new page to `pageOrder`; preserve `activePageName` |
| `page.json` | Page metadata, size, filters | Preserve dimensions unless resizing is approved |
| `visual.json` | Visual type, position, query, formatting | Validate roles and formatting with CLI metadata |
| `localSettings.json` | User-local settings | Do not commit or rely on it |

Schema URLs use the prefix `developer.microsoft.com/json-schemas/fabric/item/report/definition/`.
The suffixes are versioned PBIR contracts that Power BI Desktop bumps with most
releases (e.g. `visualContainer/2.9.0`, `page/2.1.0`, `report/3.3.0` at the
time of writing — newer values may appear in any user's PBIP). When editing,
**always preserve the existing `$schema` value**; when adding a new file, copy
the `$schema` URL from an existing file of the same type in the same report.
Do not invent or bump versions on your own. Validate with `powerbi-report-author validate`.

---

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
| `validate <path>` | Full validation of a `.pbip` or `.Report` directory: JSON Schema, structure, IDs, formatting properties, enum values, nesting, layout bounds, theme | **After every batch of changes** |
| `preview-* <path> [--with-derived]` | Report inventory: `preview-visuals`, `preview-pages`, `preview-filters`, `preview-themes` | Auditing existing report content |
| `--help` / `<command> --help` | Command syntax and available options | Before using an unfamiliar command or flag |

More commands: [`powerbi-report-author-cli.md`](authoring/powerbi-report-author-cli.md).

### Validation result handling

Run `powerbi-report-author validate <path-to-.Report-dir>` after every logical
batch of PBIR edits.

- `failed` / non-zero exit: fix every error before Desktop reload. Desktop may
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

## Edit → Validate → Reload → Screenshot Loop

For rendered-output changes, follow this loop. Do not report completion until
validation, reload, and screenshot review are clean.

```text
┌──────────────────────────────────────────────────────────┐
│  1. Edit PBIR files                                      │
│  2. Validate           → errors? fix and go to 1         │
│  3. Desktop status     → choose the correct bridge PID   │
│  4. Desktop reload     → error? fix PBIR and go to 1     │
│  5. Screenshot/review  → issues? fix and go to 1         │
│  6. Clean              → report completion               │
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- **Step 2** — `powerbi-report-author validate <path-to-.Report-dir>`. Pass the
  report definition directory (e.g., `Sales.Report`), not the `.pbip` file or
  project root. Fix all errors before reload — invalid PBIR errors will surface
  in Desktop.
- **Steps 3–5** — use `powerbi-desktop` CLI: `status` to choose the PID, then
  `reload --pid <pid>` for PBIP/PBIR current files and screenshots from the
  same PID. Then perform the screenshot review below.
  After `status`, if the selected instance has `hasUnsavedChanges: true`, do
  not reload yet; ask the user to save or discard their Desktop UI changes,
  rerun `status`, and continue only once it is false.
  `reload` covers report/PBIR changes only. For semantic-model/TMDL changes,
  use a semantic-model skill or Modeling MCP and reopen the PBIP if changes are
  not reflected.
    **Exception:** Theme JSON files are cache-keyed by name — Desktop may not
  pick up edits on reload. Either rename the theme file with a random suffix
  (and update `report.json`), or close and reopen Desktop.

**Desktop CLI commands:**

| Command | Purpose | When to use |
|---|---|---|
| `open "<path.pbip>"` | Launch Power BI Desktop for a PBIP/PBIX | Starting Desktop or opening the target report |
| `status` | List Desktop Bridge instances, current files, report dirs, and bridge state | Before reload/screenshot; choose the correct PID |
| `reload --pid <pid>` | Reload the selected Desktop instance's current PBIP report files | After validated PBIR edits in an open PBIP |
| `screenshot <page-id> --pid <pid> --output <file>` | Capture one page by PBIR page ID | Isolated page changes |
| `screenshot-all --pid <pid> --output-dir <dir>` | Capture every report page | Theme, navigation, page-order, or report-wide changes |

Use `powerbi-desktop screenshot <page-id> --pid <pid>` when only one PBIR
page needs review. `reload` is supported only for PBIP-backed reports. No `powerbi-desktop` command accepts `--report`; use `status`
to select the Desktop instance by PID because the same PBIP can be open in more
than one process. Screenshots default to scale `2`. Run reload and screenshot
operations serially per PID — never in parallel against the same PID, even as a
workaround for a slow or retryable error. Read `references/authoring/powerbi-desktop.md` for the
complete command reference and troubleshooting workflow.

**Common Desktop CLI outcomes:**

| Output/error | Meaning | Action |
|--------------|---------|--------|
| `"status": "not_connected"` | No Desktop Bridge discoverable | Run `powerbi-desktop open "<path.pbip>"` or ask the user to start Desktop. If still unreachable, ask them to enable the Desktop preview feature — see [docs](https://aka.ms/Report_Authoring_skill_LearnDocs) |
| `AMBIGUOUS_DESKTOP_INSTANCE` | More than one Desktop Bridge instance is available | Run `powerbi-desktop status`, choose the intended PID, retry with `--pid` |
| `METHOD_NOT_AVAILABLE` | Desktop build lacks a required production bridge method | Tell the user Desktop is stale/unsupported — see [docs](https://aka.ms/Report_Authoring_skill_LearnDocs) |
| `HostNotReady` / retryable bridge error | Desktop is up but the report host isn't ready (often briefly after a reload) | CLI auto-retries; rerun once if it surfaces. Do not add custom sleeps — rely on the CLI's retry path. |
| `Timeout` (bridge error) | A reload or screenshot exceeded the CLI's retry budget | Confirm `status` shows `bridgeStatus: "connected"`, then rerun once. If `Timeout` persists, raise the budget (e.g., `reload --pid <pid> --wait-seconds 120`). If `bridgeStatus: "error"` or `status` hangs, ask the user whether a Desktop modal dialog is blocking input. |
| `Cancelled` during screenshot/reload | A reload/screenshot was cancelled — usually a concurrent reload/screenshot on the same PID. Distinct from `Timeout` (operation ran too long). | Run reload and screenshot serially per PID. Wait for `connected` via `status`, retry one at a time. |
| `ReportDefinitionValidationFailed` | Desktop rejected the PBIR definition | Fix PBIR, run `powerbi-report-author validate <path>`, then reload again |
| `REPORT_DIR_REQUIRED` | Selected PID has no PBIP/PBIR current file; reload/screenshot-all need PBIP/PBIR state | Select the correct PID from `status` or open the target PBIP |

### Screenshot Review

After taking screenshots, perform an independent rendered-output review before reporting completion. Read [`screenshot-review.md`](authoring/screenshot-review.md), check layout, data rendering, formatting/theme, slicers, and common screenshot failure modes, then fix PBIR and repeat the loop until clean.

---

## Validation

Run `powerbi-report-author validate <path>` after every logical batch of PBIR
changes. Prefer the `.Report` directory; the CLI also accepts a `.pbip` file or
a project root containing a single `.Report` directory. Errors block Desktop
reload — fix them first. Review warnings and fix unless there's a clear reason
not to.

The validator is an offline preflight covering PBIR structure, JSON/schema
validity, cross-file references, IDs/names, visual types, role bindings,
filters, formatting objects/properties/enums/selectors, visualContainerObjects,
theme registration, layout bounds, and selected Desktop/rendering failure
patterns. It does not replace Desktop reload and screenshot review.

---

## Anti-Patterns and Pitfalls

| Pitfall | Consequence | Fix |
|---------|-------------|-----|
| Using `"Entity"` inside filter `Where` conditions | Filter silently fails | Use `"Source"` with the alias from `From` |
| Omitting `nativeQueryRef` | Visual calculations may break | Always include `nativeQueryRef` |
| Reusing visual/filter names | Unpredictable behavior | Generate unique IDs |
| Setting `visualType` to invalid string | Visual renders as error box | Run `powerbi-report-author catalog describe <type>` or `powerbi-report-author catalog list` |
| Wrong role name for visual type | Field is ignored; visual blank | Match role names from `powerbi-report-author catalog describe <type>` |
| Mixing `Column` and `Measure` types | Query fails; visual error | Columns use `Column`, measures use `Measure` |
| Forgetting to add page to `pages.json` | Page invisible | Add to `pageOrder` array |
| Booleans without correct format | Wrong type | `"true"` / `"false"` (no suffix, unquoted in Value) |
| Numbers without type suffix | Type mismatch | `D` for decimals, `L` for integers |
| Editing `$schema` version | PBI Desktop may reject | Preserve existing version |
| Stringified JSON in `paragraphs` | Textbox shows nothing | `paragraphs` is a native JSON array |
| Using textbox as a thin line/divider | Renders ~24px tall regardless of `height` | Use a `shape` visual (rectangle) instead — shapes respect small dimensions |
| `visualContainerObjects` as sibling of `visual` | Schema validation error in PBI Desktop | Must be **inside** `visual` object, as sibling of `objects` |
| Using `tableEx` with dimension columns and measures all in `Values` | Headers render but no data rows even when DAX confirms data exists | Use `pivotTable`; put dimensions in `Rows` and measures in `Values` |
| Using PowerShell `ConvertTo-Json` to edit visual JSON | Property reordering, nesting depth truncation (`-Depth` default is 2) | Use Node.js for JSON manipulation, or always pass `-Depth 20` and verify structure |
| Using regex or string replacement to modify JSON files | Corrupts nesting structure — properties end up inside sibling values, braces misalign | Read file → `JSON.parse` → modify object → `JSON.stringify` → write back. Or use the `edit` tool with exact old/new string matching |
| `dataPoint.fill` without a selector on single-series charts | Bars/columns invisible despite data in tooltips | Use `dataPoint.defaultColor` for a base color without a selector; `fill` requires a `metadata` selector |
| Using `dataPoint.defaultColor` on multi-series charts | All series/categories get the same color — no visual differentiation | Use theme `dataColors` for consistent palette across visuals, or `dataPoint.fill` with `metadata` selectors for per-series overrides — see [color-strategy.md § Color Strategy Quick Reference](authoring/color-strategy.md#color-strategy-quick-reference) |
| Clustered bar/column chart colors collapse into one legend color | The visual has a Series role but all bars and legend markers share the same hue | Use per-series `dataPoint.fill` selectors or a theme `dataColors` palette; do not use `defaultColor` on clustered charts |
| Relying on theme `dataColors` alone for cross-visual measure consistency | Same measure gets different colors on different visuals (index-based assignment varies with projection order) | Maintain a measure→color mapping and apply explicit `dataPoint.fill`/`defaultColor` per visual — see [color-strategy.md § Cross-Visual Measure-Color Consistency](authoring/color-strategy.md#pattern-cross-visual-measure-color-consistency) |
| Using `ThemeDataColor` for explicit per-measure `dataPoint.fill` with metadata selectors | Colors silently resolve to white or black instead of expected palette color | Use `Literal` hex values for explicit color assignments with metadata selectors — `ThemeDataColor` is unreliable in this context |
| Choosing bar/series colors without checking background contrast | Bars or lines invisible against page/card background (e.g., white bars on white canvas) | Always pick saturated, mid-to-dark hues that contrast with the page and VCO background colors |
| `show` property on page-level `background` | Schema error — page `background` only supports `color`, `image`, `transparency` | Only VCO `background` (on visuals) has `show`; page background is always visible |
| Copying property names from doc examples without verifying | Warnings or silent failures — property names vary by visual type | Always run `powerbi-report-author formatting describe-object <type> <object>` for exact property names |
| Guessing which object a property belongs to | Wasted calls checking wrong objects one by one | Run `powerbi-report-author formatting search <type> <regex>` to grep across all objects at once |
| Formatting property has no effect (no error) | Setting `show: false` on cardVisual outline without an id selector — validates but renders unchanged | Check `powerbi-report-author formatting describe-object <type> <object>` for `_selectorHint`; use the dual-entry pattern (static + id selector entries) |
| Using `cardCalloutArea` on a single-value card | Properties validate but have no visible effect — `cardCalloutArea` only renders on multi-value cards (2+ measures in Data) | Use `outline`/`accentBar`/`fillCustom` with `{ id: "default" }` selector for single-value cards. For multi-value cards, `cardCalloutArea` controls per-callout tile styling — see [card.md § Multi-Value Formatting](authoring/card.md#multi-value-formatting) |
| Using `"Fields"` as the `queryState` role for `cardVisual` | Cards render empty — PBI Desktop cannot resolve the binding. Validator reports `Unknown role "Fields"` and `Required role "Data" missing` | `cardVisual`'s only data role is `"Data"`. `"Fields"` is the legacy `card` visual's role name — never carry it over. Always verify role names with `powerbi-report-author catalog describe cardVisual` — see [card.md § Single-Value Template](authoring/card.md#single-value-template) |
| Creating separate single-value `cardVisual` instances for multiple related KPIs | Wastes canvas space and misuses the visual type — `cardVisual` natively supports multiple projections in one tile | Default to one multi-value `cardVisual` with all measures as `Data` projections when ≥2 related KPIs are requested. Only use separate cards when per-card styling differences are required — see [card.md § When to Consolidate vs. Keep Separate](authoring/card.md#when-to-consolidate-vs-keep-separate) |
| Adding multiple fields to button slicer Values or Label roles | Slicer breaks or shows unexpected results — each role accepts only 1 field | Put one field in Values, one in Label; additional fields go to Tooltips |
| Looking at `filterConfig` on other visuals to understand slicer selections | Slicer selections live **only** inside the slicer's own `visual.json` via `expansionStates` + `objects.general.filter`. Always read `references/authoring/slicers.md` first when modifying slicers |
| Creating an image visual without prompting for the source type | Wrong visual structure — URL vs local file vs data field each have different schemas and expression types | Always ask the user for the image source (local file / URL / data field) before creating the visual — see [image.md § Source Types Overview](authoring/image.md#source-types-overview) |
| Creating a data-bound image visual with a field that lacks `dataCategory: ImageUrl` | Visual renders blank or error | **Warn the user first** — the visual will render blank without `dataCategory: ImageUrl`. Present alternatives (other ImageUrl fields, local file, URL) and confirm before creating — see [image.md § Select from data](authoring/image.md#3-select-from-data) |
| Placing background image on page canvas instead of visual plot area | User asks for "background image" alongside a visual (e.g., "column chart with background image") but image is placed on `page.json → objects.background` instead of `visual.objects.plotArea` | When a background image is requested in the context of a specific visual, default to `plotArea.image`. Only use page-level `background.image` when the user explicitly says "page background" / "canvas background" or no visual context exists — see [image.md § Plot Area Background Image](authoring/image.md#plot-area-background-image-plotareaimage) |
| Creating a `multiRowCard` visual | Legacy multi-row card — deprecated; `powerbi-report-author validate` warns with `PBIR_VISUAL_TYPE_DEPRECATED`. Often triggered by user phrases like "multi-card", "cards for each metric", or "card per measure" | Always use `cardVisual`. For multiple KPIs, use a single multi-value `cardVisual` with all measures as projections in the `Data` role — see [card.md](authoring/card.md#multi-value-template) |
| Using `map` or `filledMap` instead of `azureMap` for map visuals | Legacy Bing Maps visuals — deprecated and must not be created; `powerbi-report-author validate` warns with `PBIR_VISUAL_TYPE_DEPRECATED` | Always use `azureMap` — see [map.md](authoring/map.md). If the map fails to render or geocode, debug the fields, try alternative geographic columns/coordinates, or ask the user — do **not** silently substitute a non-map visual without consulting the user first |
| Creating `tableEx`/`pivotTable` without `columnAdjustment: growToFit` | Columns shrink-wrap to content, leaving unused whitespace | Always set `columnHeaders.columnAdjustment` to `growToFit` and `autoSizeColumnWidth` to `true` — see [table.md](authoring/table.md#default-rule--grow-to-fit) |
| Custom table/matrix row colors with no effect (white background) | Default style preset overrides `objects`-level `backColorPrimary`/`backColorSecondary` | Set `stylePreset` VCO to `'None'` on every `tableEx`/`pivotTable` with custom colors — see [table.md § Style Presets](authoring/table.md#style-presets-for-tables) |
| Table cells white despite dark VCO background | `visualContainerObjects.background` only controls outer container — table cells paint on top | Set dark colors in `objects.values.backColorPrimary/Secondary` and `objects.columnHeaders.backColor`, not in VCO — see [re-theming.md § Dark Mode Checklist](authoring/re-theming.md#dark-mode-authoring-checklist) |
| Dark theme applied but cards/tables/slicers still white | Dark mode triggers every formatting trap simultaneously | Follow the full [re-theming.md § Dark Mode Authoring Checklist](authoring/re-theming.md#dark-mode-authoring-checklist) — covers stylePreset, fillCustom+id selector, objects vs VCO, and contrast audit |
| Theme JSON changes do not appear after Desktop reload | Desktop caches theme files by file name | Rename the theme JSON with a small random suffix, update the theme registration in `report.json`, then reload; otherwise close and reopen Desktop |
| Placing `sortDefinition` inside `visual` or at root of `visual.json` | Schema validation error; sort silently ignored — chart falls back to alphabetical | `sortDefinition` is a property of **`query`** — use `visual.query.sortDefinition`. Supported since `visualConfiguration/2.2.0` |
| Container shape fill doesn't match reference | Text invisible or wrong background color | Match the fill color and transparency to the reference image. If the page background already provides the color, skip the shape entirely. If the shape must be invisible, verify text color still contrasts with the page canvas — see [shape.md § Container Shapes](authoring/shape.md#container-shapes) |
| Shape text invisible after re-theme | Shape `text` object has no explicit `fontColor` — text inherits theme foreground, but when `fill` is a light color (e.g., white pill/button) on a light page canvas, inherited dark foreground may not render or the fill blends with canvas making text vanish | Always set explicit `fontColor` on shape `text` objects (in the `{ selector: { id: "default" } }` entry). During re-theming, audit all shapes with `text.show: true` — bulk hex-replacement misses shapes that need a *new* `fontColor` property added |
| Enabling `logAxisScale` on data with zero or negative values | PBI Desktop silently falls back to linear scale with a warning — log of zero/negative is undefined | **Warn the user before applying.** Use `ask_user` to present alternatives (filter negatives, switch measure, use `labelDisplayUnits`). Apply `logAxisScale: true` only after the user resolves negative values or confirms all bound values are positive — see [cartesian.md § Log Scale](authoring/cartesian.md#log-scale-logaxisscale) |
| Changing theme without sweeping inline overrides | Old colors remain on shapes, page backgrounds, nav buttons, textboxes — theme-only change has no effect on hardcoded `Literal` hex values at Priority 2 in the cascade | When the report has per-visual color overrides, follow [re-theming.md § Re-theming Workflow](authoring/re-theming.md#re-theming-an-existing-report) Steps 0–3: build a color mapping, update theme JSON, then bulk-sweep `definition/` files for old hex values before reload |
| Changing only `dataColors` in theme without sweeping | Shapes, accent bars, nav button borders retain old accent colors — they use hardcoded Literal hex from the old `dataColors` array, not `ThemeDataColor` references | Sweep ALL old `dataColors[N]` hex values across `definition/` files. Even same-polarity "just change the accent/data colors" requests need the full sweep — shapes and nav elements commonly hardcode `dataColors[0]` as accent fills/outlines. |

## Official Documentation

For Microsoft Learn setup guidance, support constraints, and feature
availability, use [Power BI report authoring docs](https://aka.ms/Report_Authoring_skill_LearnDocs).
