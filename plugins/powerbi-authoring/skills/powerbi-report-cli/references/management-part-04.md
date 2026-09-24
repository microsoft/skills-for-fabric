# powerbi-report-cli management mode -- Power BI Report Items in Fabric - Part 4

## Contents

- [Agentic Workflow](#agentic-workflow)
  - [Publishing a local `.pbip`](#publishing-a-local-pbip)
  - [Modifying an existing report in Fabric](#modifying-an-existing-report-in-fabric)
  - [Creating a new report in Fabric](#creating-a-new-report-in-fabric)
- [Troubleshooting](#troubleshooting)


Continuation of `management.md`. Open this file directly from the skill reference index.

## Agentic Workflow

### Publishing a local `.pbip`

This is the primary entry point when a user has a local `.pbip` (report
plus sibling `.SemanticModel`) on disk and asks to publish, upload, push,
or deploy the report to a Fabric workspace.

Do not enter this workflow merely because local authoring and screenshot review
finished successfully. Never publish or overwrite the remote report with local
changes until the user explicitly gives permission. If the user has not
explicitly requested this remote write in the current request, or you are
unsure, keep the changes local and do not publish. A request to publish does not
by itself authorize replacing an existing report; step 8 requires the user to
confirm they agree to overwrite the existing remote report.

**1. Detect that the source is a local `.pbip`.** Any of these signals:

- A `<Name>.pbip` file in or above the working directory.
- A `<Name>.Report` folder with a sibling `<Name>.SemanticModel` folder.
- The report's `definition.pbir` uses `byPath` (local/Git form) rather
  than `byConnection` (API form).
- Presence of a `.pbi/` cache folder.

If the source is *not* a local `.pbip` (e.g., the report was already
downloaded from Fabric and only the `.Report` folder is present with a
`byConnection` `definition.pbir`), use the
[Modifying an existing report in Fabric](#modifying-an-existing-report-in-fabric)
workflow instead.

**2. Confirm the target workspace once.** Resolve and store the workspace
ID by name (per COMMON-CLI.md (see `../../../common/COMMON-CLI.md`, section `finding-workspaces-and-items-in-fabric`)).
This single workspace is reused for both the model deploy (if applicable)
and the report publish — never split them.

**3. Prompt the user about the semantic model.** Ask explicitly — do not
silently choose:

> "Do you want me to publish the local semantic model to this workspace
> too, or connect this report to an existing semantic model already in
> the workspace?"

**4a. Branch: "Publish the local model".**

- Check whether a semantic-model authoring skill is
  available in the current session.
  - **Available** → hand off to that skill to
    create or update the semantic model. Pass: target workspace ID,
    the local `.SemanticModel` folder path (TMDL source), and the
    desired model display name. Wait for that skill's workflow to
    reach terminal success before proceeding.
  - **Not available** → tell the user a semantic-model authoring skill is not
    loaded in this session and that publishing the local model is not
    possible without it. Then degrade to branch 4b
    (connect-to-existing) and re-prompt for which workspace model to
    bind the report to.

**4b. Branch: "Connect to an existing model in the workspace".**

- List semantic models in the target workspace and confirm the target
  model with the user. Resolve `semanticModelId` by name.

**5. Resolve `semanticModelId`.** Regardless of branch, the report needs
a concrete model ID to bind to:

- After 4a: list semantic models in the target workspace and find the
  model just deployed by name (the model skill verifies by listing
  workspace items but does not return an ID).
- After 4b: this was already done.

**6. Verify bindings against the resolved model (universal, both
branches).** Download the model TMDL and run the bindings diff per
**Verify semantic-model bindings after the target model is resolved** in the
**MUST** section of `management-part-03.md`. Even on the
publish-the-local-model branch, the
model skill may rename tables or apply transforms during deploy, so
this diff is not optional. Remap any drift via the `authoring` mode
or, if structurally divergent, prompt the user before re-authoring.

**7. Rebind `definition.pbir` from `byPath` → `byConnection`.** Use
the `authoring` mode to set:

```json
"datasetReference": {
  "byConnection": {
    "connectionString": "semanticmodelid=<resolved-id>"
  }
}
```

The Fabric API rejects `byPath`; this swap is mandatory on every
local-source publish. This remains delegated to
the authoring mode (see `authoring.md`) and MUST execute before any
`powerbi-report-author pack` command; pack is byte-verbatim and does not repair
dataset references.

**8. Decide create-new vs. update-existing for the report.** Default the
report `displayName` to the `.pbip` filename without extension (e.g.
`SalesDashboard.pbip` → `"SalesDashboard"`). Surface the default to the
user so they can override.

- List reports in the target workspace and look up the chosen
  `displayName`.
  - **Not found** → create. Follow
    **Create Report (with Definition)** in `management-part-02.md`.
  - **Found** → confirm with the user: overwrite the existing report
    (`updateDefinition`), publish under a different name, or cancel.
    Follow **Update Report Definition** in `management-part-02.md` on
    overwrite.

**9. Pack and upload.** Pick the branch that matches the create-new versus
overwrite-existing decision from step 8. Use the create branch for a new report
and the overwrite branch for an existing one. Run the
**Modern-PBIR preflight before pack** in `management.md` first,
then run `powerbi-report-author pack` for the base64+walk transport step and use
`az rest` for the Fabric call. Pack emits all qualifying PBIR parts with
forward-slash paths; `az rest` still owns POST, `x-ms-operation-id` capture
(with `--verbose` written to a file), and LRO polling to terminal success.

- **Create branch** from step 8:

  ```bash
  set -euo pipefail

  REPORT_DISPLAY_NAME="SalesDashboard"   # Non-empty name confirmed in step 8.
  REPORT_DESCRIPTION="Published from local PBIP"   # Optional; leave unset to omit.
  PACK_CREATE_ARGS=(--raw --mode create --display-name "$REPORT_DISPLAY_NAME")
  if [ -n "${REPORT_DESCRIPTION:-}" ]; then
    PACK_CREATE_ARGS+=(--description "$REPORT_DESCRIPTION")
  fi

  powerbi-report-author pack ./MyReport.Report "${PACK_CREATE_ARGS[@]}" --out create-report.json
  az rest --method post \
    --resource "https://api.fabric.microsoft.com" \
    --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
    --headers "Content-Type=application/json" \
    --body @create-report.json \
    --verbose 2>&1 | tee publish-create-start.log
  ```

  Do not pass `--description ""`; omit the flag when no description is intended.

- **Overwrite branch** from step 8:

  ```bash
  set -euo pipefail

  powerbi-report-author pack ./MyReport.Report --raw --out update-definition.json
  az rest --method post \
    --resource "https://api.fabric.microsoft.com" \
    --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/updateDefinition" \
    --headers "Content-Type=application/json" \
    --body @update-definition.json \
    --verbose 2>&1 | tee publish-update-start.log
  ```

**10. Clean up** any temporary files created during the flow.

> **Note on report-side verification**: there is no reliable
> programmatic way to confirm a report renders correctly post-publish —
> the report lives at a Fabric Service URL and visual rendering
> requires a browser session. Surface the workspace/report URL so the
> user can verify in the browser.

### Modifying an existing report in Fabric

1. **Authenticate** → see COMMON-CLI.md § Authentication Recipes (see `../../../common/COMMON-CLI.md`, section `authentication-recipes`)
2. **Find workspace** → Resolve workspace ID by name
3. **List/find report** → Resolve report ID by name
4. **Download definition** → `getDefinition?format=PBIR` → capture/poll any LRO → save the final PBIR JSON to `payload.json`, then `powerbi-report-author unpack ./MyReport.Report --input payload.json`. Use a fresh or explicitly emptied directory for every download, including reruns. `unpack` only overwrites files present in the payload and leaves other local files untouched, so `--force` into a reused directory keeps parts that were deleted on the server and the next `pack` re-uploads them. Do not rerun with `--force` into a directory that already holds a previous download.
5. **Author PBIR content** → **Use the `authoring` mode** for ALL changes. This covers every file: `definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, visuals, filters, formatting, themes, and expressions. Follow its guidance for correct structure, schemas, and field values. Use its CLI tools to validate. Never construct any PBIR JSON from memory or guesswork.
6. **Upload changes** → run **Modern-PBIR preflight before pack** in `management.md`, then `powerbi-report-author pack ./MyReport.Report --raw --out update-definition.json` → `POST /reports/{id}/updateDefinition` with `--body @update-definition.json` → persist verbose headers to a named log, capture `x-ms-operation-id`, and poll the LRO; pack emits ALL parts (modified + unmodified)
7. **Clean up** → Delete all temporary local files and directories created during the workflow

### Creating a new report in Fabric

1. **Authenticate** → see COMMON-CLI.md § Authentication Recipes (see `../../../common/COMMON-CLI.md`, section `authentication-recipes`)
2. **Find workspace** → Resolve workspace ID by name
3. **Resolve semantic model** → Find the semantic model ID and workspace name for the `definition.pbir` connection string
4. **Verify semantic-model bindings** → Download the target semantic model definition (TMDL) and compare all PBIR `Entity`, `queryRef`, `nativeQueryRef`, and filter references against the target table/column names. If names differ but structure matches, remap all table-qualified bindings. If models are structurally different, prompt the user before proceeding — explain what doesn't match and ask whether to re-author the affected bindings
5. **Author PBIR content** → **Use the `authoring` mode** to generate the complete PBIR definition from scratch — `definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, and all visuals. Never construct any PBIR JSON from memory or guesswork.
6. **Upload** → choose a concrete non-empty display name first (for example `REPORT_DISPLAY_NAME="My New Report"`). Build create arguments with `--display-name "$REPORT_DISPLAY_NAME"` and add `--description "$REPORT_DESCRIPTION"` only when a non-empty description is intended; otherwise omit `--description`. Run **Modern-PBIR preflight before pack** in `management.md`, then `powerbi-report-author pack ./MyReport.Report --raw --mode create --display-name "$REPORT_DISPLAY_NAME" [--description "$REPORT_DESCRIPTION"] --out create-report.json` → `POST /reports` with `--body @create-report.json` → persist verbose headers to a named log, capture `x-ms-operation-id`, and poll the LRO; pack emits `displayName` and all definition parts
7. **Clean up** → Delete temporary local files

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong or missing `--resource` audience | Always pass `--resource "https://api.fabric.microsoft.com"` |
| `403 Forbidden` | Insufficient permissions | Check workspace role (Contributor+ for write ops) |
| `404 Not Found` | Wrong workspace or report ID | Re-resolve IDs via List APIs |
| `CorruptedPayload` | Malformed base64 or invalid PBIR JSON, usually from unsupported manual hand-walking | Install/upgrade `powerbi-report-author >= 0.3.0-beta.0` and use `pack`/`unpack`, which avoid manual base64 and path mistakes. Do not continue with fallback recipes from this skill. |
| `202` with no result | LRO not polled to completion | Implement LRO polling pattern |
| `OperationNotSupportedForItem` | Report has encrypted sensitivity label | Cannot get definition for encrypted reports |
| `ItemDisplayNameAlreadyInUse` | Duplicate name in workspace | Use a unique display name |
| `format: "PBIR-Legacy"` | Report was created before PBIR was default | PBIR-Legacy is not supported by this skill |
| `UNPACK_FORMAT_UNSUPPORTED` | `powerbi-report-author unpack` received PBIR-Legacy or another non-PBIR format | Re-run `getDefinition?format=PBIR`; if Fabric still returns PBIR-Legacy, stop — this skill only supports modern PBIR |
| Visuals empty / no data after publish | PBIR entity names don't match workspace semantic model table names (e.g., local CSV table name vs workspace table name) | Download target semantic model TMDL, compare table names, update all `Entity`, `queryRef`, `nativeQueryRef`, and filter references to match |
| `MissingDefinitionParts` on create/update even though all files are included | Unsupported manual hand-walking can emit backslashes in definition part paths (`definition\report.json`), but the Fabric API requires forward slashes. `powerbi-report-author pack` normalizes to forward slashes for you. | Install/upgrade `powerbi-report-author >= 0.3.0-beta.0` and use `pack`; do not continue with manual fallback path walkers. |
| Duplicate reports appear in workspace after create | Create POST was retried after a `202 Accepted` response. Each retry risks creating a new report. | Never retry a create POST after `202`. See **Long-Running Operations (LRO)** in `management-part-02.md` for reliable operation ID capture and recovery steps. Delete any duplicates with the Delete Report API. |
| Visuals empty after publishing a local `.pbip` via the model hand-off | The semantic-model authoring skill may rename or transform tables/columns during deploy, so the freshly deployed model's TMDL no longer matches the report's PBIR bindings. | Re-run the TMDL-diff verification against the deployed model (per **Verify semantic-model bindings after the target model is resolved** in the MUST section of `management-part-03.md`) and remap drifted bindings via the `authoring` mode. |
| Visuals empty after publish, despite TMDL diff being clean | `definition.pbir` `byConnection` still points at a stale model ID (e.g., from `.pbi/` cache or an earlier publish), not the freshly resolved one. | Re-run step 7 of [Publishing a local .pbip](#publishing-a-local-pbip) to set `byConnection` to the actually resolved `semanticModelId`, then re-publish. |
| Semantic-model authoring skill not available when user wants to publish the local model | No semantic-model authoring skill is loaded in the current session. | Inform the user and degrade to the connect-to-existing branch — re-prompt for which workspace model to bind the report to. Do not silently fall through. |
| Model published to one workspace, report POSTed to another | Workspace was not confirmed up front, or two different workspaces were used for the model deploy and the report publish. | Enforce the single-workspace rule (step 2 of [Publishing a local .pbip](#publishing-a-local-pbip)). Recovery: either re-publish the report into the model's workspace, or move the model. |
