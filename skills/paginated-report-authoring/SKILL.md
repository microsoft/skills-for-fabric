---
name: paginatedreport-authoring-cli
description: >
  Create and publish Fabric Paginated Reports (.rdl) bound to a Power BI semantic model
  via CLI, using DAX datasets, report parameters, and the Power BI Imports API.
  Use when the user wants to:
    1. Create a paginated report over an existing semantic model
    2. Generate an RDL definition (tablix, KPIs, grouping, parameters) programmatically
    3. Bind a paginated report to a semantic model with the correct connection string
    4. Publish/upload an .rdl into a Fabric workspace and verify it renders
    5. Parameterize a paginated report (date ranges, multi-select filters) from live DAX queries
    6. Troubleshoot InvalidDefinitionFormat / blank-report / import failures
  Triggers: "create paginated report", "rdl report", "paginated report over semantic model",
  "publish rdl", "upload rdl to fabric", "paginated report parameters", "paginated report dax",
  "report builder rdl", "InvalidDefinitionFormat"
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering.
> 2. To find the semantic model details (**name AND GUID**) from workspace ID: list all `semanticModels` in that workspace and filter. The **GUID is required** for the RDL connection string.
> 3. **Prefer the Power BI Imports API** (multipart raw `.rdl` upload) to create the report. The Fabric `POST /paginatedReports` definition API is strict and frequently returns `InvalidDefinitionFormat` for hand-authored RDLs.

# paginatedreport-authoring-cli — Paginated Report Authoring over a Semantic Model via CLI

Create RDL paginated reports **programmatically** and publish them to a Fabric workspace. This skill
covers the full loop: discover the model, generate a schema-valid RDL bound to that model, and publish
via the reliable Power BI Imports API.

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — workspace/model ID resolution *(present when this skill lives in the skills-for-fabric repo)* |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401 |
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro) | Import/definition polling |
| RDL Structure (order & namespaces) | [references/rdl-structure.md](references/rdl-structure.md) | **Read first** — validator is strict about element order |
| Data Source — Semantic Model Connection | [references/datasource-connection.md](references/datasource-connection.md) | `PBIDATASET` + `sobe_wowvirtualserver-<GUID>` |
| Datasets & DAX | [references/datasets-dax.md](references/datasets-dax.md) | `EVALUATE`, `SELECTCOLUMNS`, `<DataField>` bracketing |
| Parameters & Filters | [references/parameters-filters.md](references/parameters-filters.md) | Multi-select from live queries; RDL vs DAX filtering |
| Layout — KPIs, Tablix, Grouping | [references/layout.md](references/layout.md) | Grouped tablix, subtotals, page setup |
| Publishing | [references/publishing.md](references/publishing.md) | **Imports API (reliable)** + Fabric definition API |
| Troubleshooting | [references/troubleshooting.md](references/troubleshooting.md) | Symptom → cause → fix |
| Script Templates | [references/script-templates.md](references/script-templates.md) | RDL generator + publish scripts |
| Tool Stack | [SKILL.md § Tool Stack](#tool-stack) | |
| Prerequisites & Discovery | [SKILL.md § Prerequisites & Discovery](#prerequisites--discovery) | |
| Authoring Scope | [SKILL.md § Authoring Scope](#authoring-scope) | |
| Must / Prefer / Avoid | [SKILL.md § Must / Prefer / Avoid](#must--prefer--avoid) | |
| Agentic Workflows | [SKILL.md § Agentic Workflows](#agentic-workflows) | End-to-end sequence |
| Examples | [SKILL.md § Examples](#examples) | |
| Agent Integration Notes | [SKILL.md § Agent Integration Notes](#agent-integration-notes) | |

---

## Tool Stack

| Tool | Purpose | Install |
|---|---|---|
| **az cli** | Token acquisition + Fabric control-plane discovery (workspaces, semantic models) | `winget install Microsoft.AzureCLI` |
| **python** | Generate the RDL XML and validate well-formedness before upload | `winget install Python.Python.3` |
| **PowerShell 7+** | Multipart upload to the Power BI Imports API via `System.Net.Http.HttpClient` | built-in / `winget install Microsoft.PowerShell` |
| **jq** | JSON filtering of discovery responses | `winget install jqlang.jq` |

---

## Prerequisites & Discovery

Before authoring, gather three things:

1. **Workspace ID** (from name).
2. **Semantic model name AND GUID** — the GUID goes into the RDL connection string.
3. **Model schema** — tables, columns (with data types), measures, relationships, and sample
   dimension values for parameter dropdowns.

```bash
# Resolve the semantic model GUID in a workspace
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/semanticModels" \
  --resource "https://api.fabric.microsoft.com" \
  | jq '.value[] | {name: .displayName, id: .id}'
```

> **Data-type gotcha:** only true **Date** columns range-filter cleanly. Columns stored as **Text**
> (common for close/birth/policy dates) must be converted with `DATEVALUE`/`CDATE` in DAX before use
> in a date filter. See [references/datasets-dax.md](references/datasets-dax.md).

---

## Authoring Scope

| Deliverable | Detail |
|---|---|
| RDL data source | `PBIDATASET` connection to a semantic model — see [datasource-connection.md](references/datasource-connection.md) |
| Value datasets | One `EVALUATE VALUES(...)` query per parameter dropdown |
| Detail dataset | One row per record via `SELECTCOLUMNS` + `RELATED()` across the star schema |
| Report parameters | Date From/To (scalar) + multi-select dimension filters |
| KPI band | Report-aggregate textboxes that honor the parameter filters |
| Detail tablix | Grouped table with per-group subtotals + grand total |
| Page header/footer | Title, parameter echo, execution time, page numbers |

---

## Must / Prefer / Avoid

**MUST DO**
- Resolve the semantic model **GUID** and put it in the connection string.
- Keep RDL element order + `df` namespace exactly as in [rdl-structure.md](references/rdl-structure.md).
- Bracket / table-qualify every `<DataField>` to match DAX output.
- Parse the RDL locally for well-formedness before upload.
- Ensure `datasetDisplayName` ends in `.rdl` and the file name matches the display name.

**PREFER**
- The **Power BI Imports API** over the Fabric definition API.
- **`SELECTCOLUMNS` + `RELATED()`** for detail grain; **RDL-layer filters** over DAX filters.
- Populating parameter lists from live `VALUES()` queries.

**AVOID**
- Unescaped `&`/`<`/`>` in expressions (breaks well-formedness).
- The simplified `powerbi://.../myorg` connection string.
- Assuming text-typed date columns will range-filter.
- `nameConflict=Overwrite` on first publish (returns 404).

---

## Agentic Workflows

**End-to-end sequence**
1. **Discover** — resolve workspace ID + semantic model name/GUID; inventory schema (types, measures, relationships, sample values).
2. **Design** — choose parameters, KPIs, detail columns, grouping.
3. **Generate** — build the RDL with the generator ([script-templates.md](references/script-templates.md)); validate well-formedness locally.
4. **Publish** — upload via the Imports API ([publishing.md](references/publishing.md)); poll to `Succeeded`.
5. **Verify** — open the returned `webUrl`; confirm data renders and parameters filter correctly.
6. **Iterate** — adjust columns/measures/layout; re-publish with `nameConflict=Overwrite`.

---

## Examples

**"Create a paginated report `page_test` over `autoclaims_sm`."**
1. Resolve `autoclaims_sm` GUID in the target workspace.
2. Build datasets: `ClaimDetails` (detail grain via `SELECTCOLUMNS`+`RELATED`), plus `StatusValues`,
   `TypeValues`, `StateValues` for parameter dropdowns.
3. Parameters: `DateFrom`/`DateTo` (scalar), `ClaimStatus`/`ClaimType`/`State` (multi-select).
4. KPI band (Total Amount, Count, Open Rate, Avg Amount) + detail tablix grouped by Claim Type with
   subtotals and a grand total.
5. Generate + validate the RDL; publish via Imports API (`datasetDisplayName=page_test.rdl`,
   `nameConflict=Abort`); open the `webUrl`.

---

## Agent Integration Notes

- This skill **produces and publishes an artifact** (an `.rdl` + a workspace item). Persist the
  generator script and the `.rdl` so re-publishes are reproducible.
- Report the created report **id** and **webUrl** back to the user; do not echo tokens.
- When the Fabric definition API fails with `InvalidDefinitionFormat`, **fall back to the Imports
  API** rather than retrying the same payload (`isRetriable: false`).
- Pair with `semantic-model-consumption` (schema discovery) and `powerbi-report-management`
  (post-publish governance/permissions) where available.

> **Note on COMMON links:** The three `../../common/COMMON-*.md` rows above resolve only when this
> skill folder lives inside the `microsoft/skills-for-fabric` repo. As a standalone folder, rely on
> the `references/` files, which are fully self-contained.
