# powerbi-report-cli authoring mode -- Power BI Report Authoring (PBIR/PBIP) - Part 2

## Contents

- [Topic Files and Examples](#topic-files-and-examples)
  - [Greenfield / Design Handoff](#greenfield--design-handoff)
  - [Large Build Execution](#large-build-execution)
- [CLI Setup](#cli-setup)
- [PBIR File Layout](#pbir-file-layout)
  - [Key Files](#key-files)
  - [Greenfield: creating a brand-new report](#greenfield-creating-a-brand-new-report)


Continuation of `authoring.md`. Open this file directly from the skill reference index.

## Topic Files and Examples

Use the user's intent to choose the relevant topic file(s) before editing:

| File | When to read |
|------|-------------|
| `authoring-workflows.md` (see `authoring/authoring-workflows.md`) | Adding/modifying pages, visuals, drillthrough, interactions — includes complete JSON examples |
| `model-binding.md` (see `authoring/model-binding.md`) | Creating/repointing/repairing `definition.pbir` — `byPath` vs live-Desktop `byConnection` vs API `byConnection`, full connection-string fields, Desktop connection-error fixes |
| `preview.md` (see `authoring/preview.md`) | Desktop/service preview — selected-host routing, argument derivation, status, screenshots, lifecycle, errors, and troubleshooting |
| `screenshot-review.md` (see `authoring/screenshot-review.md`) | Screenshot review checklist and rendered-output troubleshooting after preview capture |
| `formatting-overview.md` (see `authoring/formatting-overview.md`) | **Read first for appearance changes** — cascade model, encoding rules, selectors, routing to other formatting files |
| `formatting.md` (see `authoring/formatting.md`) | Editing `visual.json` appearance — selectors, VCOs, encoding mechanics, background-image routing, cascade |
| `color-strategy.md` (see `authoring/color-strategy.md`) | Chart data point colors — theme `dataColors` vs `dataPoint.defaultColor` vs `dataPoint.fill` with selectors, cross-visual measure-color consistency |
| `conditional-formatting.md` (see `authoring/conditional-formatting.md`) | Data-driven formatting — field-value result contracts and support guardrails, color gradients (FillRule), rules, icon sets, data bars, web URLs, field-driven colors, images, and totals/subtotal targeting |
| `page-formatting.md` (see `authoring/page-formatting.md`) | Editing `page.json` appearance — canvas background, wallpaper, page background images |
| `filter-pane.md` (see `authoring/filter-pane.md`) | Filter pane (`outspacePane`) and filter card (`filterCard`) chrome — Applied/Available state styling, pane width, search/checkbox colors |
| `theming.md` (see `authoring/theming.md`) | Creating or editing `theme.json` — dataColors, textClasses, visualStyles, style presets, ThemeDataColor reference |
| `re-theming.md` (see `authoring/re-theming.md`) | **Switching themes on a report with existing visuals** — re-theming workflow (color mapping + bulk sweep), dark mode checklist, dark↔light polarity changes. Pair with `theming.md` when changing colors on a report with per-visual overrides. |
| `expressions.md` (see `authoring/expressions.md`) | Building field references (Column, Measure, Aggregation, Hierarchy), visual calculations, and sort definitions |
| `filters.md` (see `authoring/filters.md`) | Adding/modifying filters — includes complete JSON examples |
| `slicers.md` (see `authoring/slicers.md`) | **Read first** when adding/modifying slicers or slicer selections — agent workflow, JSON templates, selection config |
| `field-parameters.md` (see `authoring/field-parameters.md`) | Slicer-driven "metric selector" / "dynamic view" / "view by" visuals — recognizing/using a field parameter, target-visual projection encoding |
| `bookmark.md` (see `authoring/bookmark.md`) | Creating and editing report bookmarks — metadata/index files, saved page/visual/filter state, visibility toggles, groups, button actions, validation, and Desktop verification |
| `cartesian.md` (see `authoring/cartesian.md`) | Adding bar, column, line, and scatter/bubble charts — families, roles, query patterns (multi-measure, drill hierarchy, date hierarchy, scatter grouping), formatting |
| `map.md` (see `authoring/map.md`) | Adding map visuals — template, roles, geocoding workflow, handling render failures |
| `card.md` (see `authoring/card.md`) | Adding or formatting KPI/card visuals — `cardVisual`, id selectors, callout/value sizing, accent bars |
| `kpi.md` (see `authoring/kpi.md`) | Adding `kpi` visuals (Indicator + Trend axis + Target) — valid field combos, blank-visual root causes and fixes, query templates |
| `button.md` (see `authoring/button.md`) | Adding or formatting button visuals — `actionButton`, actions (Back, PageNavigation, WebUrl, Bookmark, Q&A), state selectors, dual-entry pattern |
| `table.md` (see `authoring/table.md`) | Adding or formatting tables/matrices — `tableEx`, `pivotTable`, grow-to-fit columns, row banding |
| `image.md` (see `authoring/image.md`) | Adding image visuals — local resources, URLs, data-bound images, ImageUrl validation/refusal workflow; also plot area background images for chart visuals |
| `shape.md` (see `authoring/shape.md`) | Adding shape visuals — containers, dividers, backgrounds, reference-image matching |
| `textbox.md` (see `authoring/textbox.md`) | Adding static or dynamic textbox visuals — paragraphs, text runs, and bound value expressions |
| `version-control.md` (see `authoring/version-control.md`) | Git branching, committing, reverting — read when the task involves version control or safe rollback planning |
| `custom-visuals.md` (see `authoring/custom-visuals.md`) | Adding AppSource, organizational, or private `.pbiviz` custom visuals — GUID discovery, `report.json` registration (`publicCustomVisuals` / `OrganizationalStoreCustomVisual` `_OrgStore` package / `resourcePackages`), `CustomVisuals/` layout, data binding, freemium licensing |

### Greenfield / Design Handoff

> This skill owns PBIR file mechanics once the work is concrete: page/visual
> JSON, bindings, filters, slicers, themes, formatting, navigation, bookmarks,
> validation, previews, and screenshots.
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
cross-page consistency, validation loop, and preview verification coordinated.

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

Before using the CLI in a session, ensure the latest published version is installed:

```bash
npm install -g @microsoft/powerbi-report-authoring-cli@latest
```

> **Public install channel:** use `@latest` for user environments. Exact
> prerelease versions pinned by repository evaluation workflows are test-only
> dependencies and must not be copied into user installation guidance.

Confirm it is on `PATH`:

```bash
powerbi-report-author --version
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
│   ├── CustomVisuals/                     # Private .pbiviz packages (also need a report.json resourcePackages entry — see references/authoring/custom-visuals.md)
│   └── StaticResources/
│       ├── SharedResources/BaseThemes/    # Built-in base themes
│       └── RegisteredResources/           # User images, custom theme JSON
└── <Report>.SemanticModel/                # OUT OF SCOPE
```

### Key Files

| File | Purpose | Agent rule |
|------|---------|------------|
| `.platform` | Fabric/PBIP report item metadata | Keep it with the `.Report` folder |
| `definition.pbir` | Report → semantic model binding via `byPath` or `byConnection` | Preserve schema/version unless intentionally migrating; when creating/repointing/repairing the binding, see `model-binding.md` (see `authoring/model-binding.md`) |
| `version.json` | PBIR format metadata | Preserve the full scaffolded file, including `$schema` |
| `report.json` | Report-level settings, themes, resources | Edit through references and validate after changes |
| `pages.json` | Page order and active page | Add every new page to `pageOrder`; preserve `activePageName` |
| `page.json` | Page metadata, size, filters | Preserve dimensions unless resizing is approved |
| `visual.json` | Visual type, position, query, formatting | Validate roles and formatting with CLI metadata |
| `localSettings.json` | User-local settings | Do not commit or rely on it |

Schema URLs live under `developer.microsoft.com/json-schemas/fabric/…`, but
**different PBIR files use different schema families** — the `item/report/definition/`
prefix only applies to the files inside the `definition/` folder, not to the
`.pbip` or `definition.pbir`:

| File | Schema family (URL after `…/fabric/`) | Example (versions at time of writing) |
|------|----------------------------------------|----------------------------------------|
| `<Report>.pbip` | `pbip/pbipProperties` | `pbip/pbipProperties/1.0.0/schema.json` |
| `definition.pbir` | `item/report/definitionProperties` | `item/report/definitionProperties/2.0.0/schema.json` |
| `version.json` | `item/report/definition/versionMetadata` | `…/definition/versionMetadata/1.0.0/schema.json` |
| `pages.json` | `item/report/definition/pagesMetadata` | `…/definition/pagesMetadata/1.1.0/schema.json` |
| `page.json` | `item/report/definition/page` | `…/definition/page/2.1.0/schema.json` |
| `report.json` | `item/report/definition/report` | `…/definition/report/3.3.0/schema.json` |
| `visual.json` | `item/report/definition/visualContainer` | `…/definition/visualContainer/2.9.0/schema.json` |

The suffixes are versioned PBIR contracts that Power BI Desktop bumps with most
releases (e.g. `visualContainer/2.9.0`, `page/2.1.0`, `report/3.3.0` at the
time of writing — newer values may appear in any user's PBIP). When editing,
**always preserve the existing `$schema` value**; when adding a new file, copy
the `$schema` URL from an existing file of the same type in the same report.
Do not bump versions on your own. Validate with `powerbi-report-author validate`.

### Greenfield: creating a brand-new report

For a **brand-new report there is no existing file to copy a `$schema` from**, so
do **not** hand-author the project-shell files
(`.pbip`, `.platform`, `definition.pbir`, `version.json`, `report.json`,
`pages.json`, first `page.json`) from memory. The two failure modes that causes
— both from guessing a `$schema` — are:

| Desktop error | Cause |
|---------------|-------|
| `UnrecognizedSchemaVersion` | Wrong **family/path** — e.g. a `.pbip` whose `$schema` points at an `item/report/…` URL instead of `pbip/pbipProperties` |
| *"This version of Power BI does not support the version you have provided in `<file>`"* | Correct family, but a **version number** the installed build does not recognize (usually guessed too new) |

**Primary path — scaffold the project with the CLI (no Desktop required):**

```bash
powerbi-report-author scaffold <output-dir> --name <ReportName> \
  [--model-path ../<Model>.SemanticModel] [--page-name "Page 1"] [--force] [--offline]
```

This writes a complete, valid PBIP shell — `.pbip`, `.platform`,
`definition.pbir`, `version.json`, `report.json` (with a real Desktop base
theme), `pages.json`, and one empty `page.json` — then self-validates the result
offline. Use it for **every** new report, then author pages/visuals into it with
the normal edit -> validate -> preview -> review loop.

- **`--model-path`** — relative path (from the `.Report` dir) to a co-located
  semantic model, e.g. `../Sales.SemanticModel`. Omit it to get a placeholder
  binding (`../<ReportName>.SemanticModel`); the CLI flags it as a placeholder
  and the binding must be repointed (see `model-binding.md` (see `authoring/model-binding.md`))
  before the report opens in Desktop.
- **Schema versions** — by default the CLI fetches the latest published
  `$schema` version per family from the public `microsoft/json-schemas` mirror
  at scaffold time (the response `schema.source` is `github`). If any family
  can't be fetched (offline, rate-limited), it falls back per-family to the
  versions pinned in the CLI (`schema.source` becomes `pinned`/`mixed`,
  `schema.fallbacks` lists what fell back). Pass **`--offline`** to skip the
  network entirely and use the pinned versions. The pinned versions are
  older-but-valid; Desktop and the Fabric service accept them and silently
  upgrade on first save/publish.
- If a scaffolded file triggers *"does not support the version you have provided
  in `<file>`"* on an **older** Desktop build (the live-fetched version is newer
  than that build supports), re-scaffold with **`--offline`** — that uses the
  older-but-valid versions pinned in the CLI, which Desktop accepts and upgrades
  in place.

---
