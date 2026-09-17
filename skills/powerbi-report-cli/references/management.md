<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `management` mode. -->

# powerbi-report-cli management mode -- Power BI Report Items in Fabric

Manage Power BI reports in Microsoft Fabric workspaces using `az rest` against
the Fabric REST API. This skill covers the full CRUD lifecycle for report items
and their PBIR definitions.

> **Scope**: Report item CRUD and definition management only. For report layout
> authoring (pages, visuals, filters, formatting), use the `authoring` mode.

> **Boundary**: This skill transports PBIR definitions to and from Fabric. PBIR
> content authoring remains owned by the `authoring` mode.

## Companion Skills

This skill is one of three that partition the Power BI authoring surface.
Each owns a single concern; route work to the right one.

| Skill | Owns | Use for |
|---|---|---|
| `authoring` mode | Report content (PBIR JSON authoring) | Pages, visuals, filters, formatting, themes, expressions, `definition.pbir`, `version.json`, `report.json` |
| `management` mode (this mode) | Report transport to/from Fabric | List, create, get, update, delete report items; download/upload PBIR definitions |
| Semantic-model authoring skill | Semantic model authoring + deployment | Create/edit measures/tables/relationships, TMDL, deploy semantic models to Fabric |

**When publishing a local `.pbip` to Fabric**, this skill is the entry
point. If the user wants to publish the local semantic model alongside
the report, this skill delegates the model deploy to
an available semantic-model authoring skill, then resolves
the resulting `semanticModelId` and binds the report to it. See the
[Publishing a local .pbip](#publishing-a-local-pbip) workflow.

## Tool Stack

| Tool | Role | Install |
|---|---|---|
| `az` CLI | **Primary**: `az rest` for Fabric REST API calls, `az login` for auth | Pre-installed in most dev environments |
| `jq` | Parse and construct JSON payloads | Standard CLI tool — see [COMMON-CLI.md § Tool Selection Rationale](../../../common/COMMON-CLI.md#tool-selection-rationale) |
| `base64` | Encode/decode PBIR file content for definition payloads | Built-in on Linux/macOS · Windows: use PowerShell `[Convert]::ToBase64String()` / `FromBase64String()` |

> **Agent check** — verify before first operation:
>
> ```bash
> az version 2>/dev/null || echo "INSTALL: https://learn.microsoft.com/cli/azure/install-azure-cli"
> ```

## Authentication

All calls use the Fabric API audience. Using the wrong audience returns a 401.

| API | Audience (`--resource`) |
|---|---|
| Fabric Report Items API | `https://api.fabric.microsoft.com` |

For the shared authentication model, token audiences, and identity types, see
[COMMON-CORE.md § Authentication & Token Acquisition](../../../common/COMMON-CORE.md#authentication--token-acquisition).

For full authentication recipes (interactive, device-code, service principal, managed identity),
see [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes).

## Finding Workspaces and Reports

> **Shared patterns** — workspace and item resolution, pagination, and LRO polling
> are documented in the common skill library.
> Read [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)
> **before** using the CRUD operations below.

### Resolve Report ID by Name

Once you have the workspace ID (per COMMON-CLI.md), resolve the report:

```bash
REPORT_NAME="Sales Report"
REPORT_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --query "value[?displayName=='$REPORT_NAME'] | [0].id" \
  --output tsv)
```

## Examples: CRUD Operations

### List Reports

Returns all reports in a workspace.

- **Permissions**: Viewer workspace role
- **Scopes**: `Workspace.Read.All` or `Workspace.ReadWrite.All`

```bash
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --query "value[].{name:displayName, id:id, description:description}" \
  --output table
```

Supports pagination via `continuationToken` query parameter.

### Get Report (Properties)

Returns properties of a specific report (name, description, ID, workspace, sensitivity label).

- **Permissions**: Read permissions on the report
- **Scopes**: `Report.Read.All` or `Report.ReadWrite.All`

```bash
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID"
```

### Get Report Definition

Downloads the full PBIR definition. This is a **POST** (not GET) and supports LRO.

- **Permissions**: Read and write permissions on the report
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`
- **Limitation**: Blocked for reports with encrypted sensitivity labels

**Always request `format=PBIR`** — without this parameter, older reports may
return PBIR-Legacy format (a single `report.json` blob), which this skill does
not support.

```bash
RESPONSE=$(az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/getDefinition?format=PBIR" \
  --verbose 2>&1)

# If 202 Accepted, extract operation ID and poll the LRO (see Long-Running Operations section)
# If 200 OK, the response contains the definition parts
```

> **Format check**: After retrieving the definition, verify
> `definition.format == "PBIR"`. If it is `"PBIR-Legacy"`, this skill does not
> support that format.

#### Decode Definition Parts to Local Files

> **Note**: `getDefinition` often returns `202 Accepted` (LRO). Check the
> Long-Running Operations section to extract the operation ID and poll for the
> result before decoding.

```bash
# After retrieving the definition (from 200 response or LRO result):
echo "$DEFINITION_JSON" | jq -r '.definition.parts[] | "\(.path)\t\(.payload)"' | \
  while IFS=$'\t' read -r path payload; do
    mkdir -p "$(dirname "./report-definition/$path")"
    echo "$payload" | base64 -d > "./report-definition/$path"
  done
```

### Create Report (with Definition)

Creates a new report with a PBIR definition. Supports LRO.

- **Permissions**: Contributor workspace role
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

```bash
# Walk ./report-definition/ and build the parts[] array — every file under the
# directory is encoded and uploaded. Includes definition.pbir, report.json,
# version.json, pages/pages.json, every pages/<page>/page.json, and every
# pages/<page>/visuals/<visual>/visual.json.
PARTS=$(find ./report-definition -type f -not -name '.*' -not -name 'Thumbs.db' | while read -r file; do
  rel="${file#./report-definition/}"
  payload=$(base64 < "$file" | tr -d '\n')
  jq -nc --arg p "$rel" --arg b "$payload" \
    '{path:$p, payload:$b, payloadType:"InlineBase64"}'
done | jq -sc '.')

jq -n \
  --arg name "My New Report" \
  --arg desc "Created via Fabric API" \
  --argjson parts "$PARTS" \
  '{displayName:$name, description:$desc, definition:{parts:$parts}}' \
  > create-report.json

az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --headers "Content-Type=application/json" \
  --body @create-report.json \
  --verbose 2>&1
```

> **PowerShell** — use `Get-ChildItem -Recurse -File` to walk the directory and
> `[Convert]::ToBase64String([System.IO.File]::ReadAllBytes($_.FullName))` to
> encode each file (instead of `base64 | tr -d '\n'`).

> **Important**: `definition.pbir` is always required. The directory walk above
> includes every file under `./report-definition/` automatically — make sure
> your local directory mirrors the full PBIR layout (top-level files, plus all
> `pages/<page>/page.json` and `pages/<page>/visuals/<visual>/visual.json`
> files) before encoding.

### Update Report Definition

Overwrites the entire definition. This is a **POST** and supports LRO.

- **Permissions**: Read and write permissions on the report
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

```bash
# Rebuild parts[] from ./report-definition/ after edits (same walk as Create).
PARTS=$(find ./report-definition -type f -not -name '.*' -not -name 'Thumbs.db' | while read -r file; do
  rel="${file#./report-definition/}"
  payload=$(base64 < "$file" | tr -d '\n')
  jq -nc --arg p "$rel" --arg b "$payload" \
    '{path:$p, payload:$b, payloadType:"InlineBase64"}'
done | jq -sc '.')

jq -n --argjson parts "$PARTS" \
  '{definition:{parts:$parts}}' \
  > update-definition.json

az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/updateDefinition" \
  --headers "Content-Type=application/json" \
  --body @update-definition.json \
  --verbose 2>&1
```

> **Critical**: `updateDefinition` replaces the **entire** definition. Include
> ALL parts — modified and unmodified. Omitting parts deletes them.

Optional query parameter `?updateMetadata=true` updates item metadata from
`.platform` file if included.

### Update Report (Properties)

Updates display name and/or description only (not the definition).

- **Permissions**: Read and write permissions on the report
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

```bash
cat > update-report.json << 'EOF'
{
  "displayName": "Renamed Report",
  "description": "Updated description"
}
EOF

az rest --method patch \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID" \
  --headers "Content-Type=application/json" \
  --body @update-report.json
```

### Delete Report

Deletes a report. Supports soft-delete (default) and hard-delete.

- **Permissions**: Write permissions on the report
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

```bash
# Soft delete (recoverable)
az rest --method delete \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID"

# Hard delete (permanent)
az rest --method delete \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID?hardDelete=true"
```

## Long-Running Operations (LRO)

`Create Report`, `Get Report Definition`, and `Update Report Definition` may
return `202 Accepted` instead of an immediate result. Capture
`x-ms-operation-id` from the verbose output and poll until terminal state per
[COMMON-CLI.md § Long-Running Operations](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern).

The management-specific guardrails below take precedence over the generic
pattern when they conflict.

> **⚠️ Never retry a create POST after receiving 202.** A `202 Accepted`
> response means the operation was accepted and is likely being processed
> server-side. Retrying the POST risks creating duplicates.
>
> **Always write `--verbose` output to a file** to reliably capture the
> `x-ms-operation-id` header on every attempt — this is the only reliable
> way to track the operation. Regex extraction from in-memory strings is
> fragile across shells and platforms. Once captured, poll the operation
> to completion just like any other LRO call.
>
> ```powershell
> # PowerShell — reliable operation ID capture
> az rest --method post ... --verbose 2>&1 | Out-File "$env:TEMP\lro-response.txt" -Encoding utf8
> $opId = (Select-String -Path "$env:TEMP\lro-response.txt" -Pattern "x-ms-operation-id.*?'([a-f0-9-]+)'" | Select-Object -First 1).Matches.Groups[1].Value
> ```
>
> As a last resort, if the operation ID is still lost despite writing to
> a file, list reports in the workspace to locate the created report —
> but this should not be the normal path.

For more details, see [Long-Running Operations](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation).

## PBIR Definition Structure

Reports use the PBIR format — a folder of JSON files:

```text
Report/
├── definition.pbir                              # Semantic model reference (required)
├── definition/
│   ├── report.json                              # Report-level settings (required)
│   ├── version.json                             # Format version (required)
│   ├── pages/
│   │   ├── pages.json                           # Page listing (required)
│   │   ├── <pageId>/
│   │   │   ├── page.json                        # Page layout
│   │   │   ├── visuals/
│   │   │   │   ├── <visualId>/
│   │   │   │   │   ├── visual.json              # Visual config
│   │   │   │   │   ├── mobile.json              # Mobile layout (optional)
│   ├── bookmarks/                               # Bookmarks (optional)
├── StaticResources/                             # Custom themes, images (optional)
```

All parts are base64-encoded in API payloads using `"payloadType": "InlineBase64"`.

### definition.pbir — Semantic Model Reference

For Fabric API, use `byConnection` (not `byPath`):

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byConnection": {
      "connectionString": "semanticmodelid=<SemanticModelId>"
    }
  }
}
```

## Must/Prefer/Avoid

### MUST

- **ALL PBIR content MUST go through the `authoring` mode** — this is the single most important rule. Whether creating a brand-new report or modifying an existing one, every PBIR file (`definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, visuals, filters, formatting, themes, expressions) must be authored using the `authoring` mode. Follow its guidance for correct PBIR structure, schemas, and field values. Use its CLI tools for validation. Never construct any PBIR JSON from memory or guesswork — not even "simple" files like `definition.pbir` or `version.json`. This mode is strictly for API transport (download, encode, upload) — it does not author PBIR content.
- **Always pass `--resource "https://api.fabric.microsoft.com"`** to `az rest` — omitting it causes silent auth failures.
- **Always pass `?format=PBIR`** on `getDefinition` — without it, older reports return PBIR-Legacy format which is not supported by this skill.
- **Only work with PBIR format** — if a definition comes back with `"format": "PBIR-Legacy"`, stop and tell the user that PBIR-Legacy is not supported.
- **Include ALL definition parts** in `updateDefinition` — modified + unmodified. The API replaces the entire definition; omitting parts deletes them.
- **Base64-encode all part payloads** — every `payload` value must be base64-encoded.
- **Use `byConnection`** in `definition.pbir` for Fabric API — `byPath` is for local/Git scenarios only.
- **Poll LRO to completion** — `Create`, `getDefinition`, and `updateDefinition` return `202 Accepted`. Poll until terminal state.
- **Always use `--verbose` on LRO operations** — `az rest` does not expose response headers by default. Without `--verbose`, you cannot capture the `x-ms-operation-id` header needed for polling, and there is no other way to retrieve it after the fact.
- **Clean up temporary files** — delete any local temp directories and files (decoded definitions, JSON payloads) created during the workflow once the operation completes. These can be large and accumulate on the user's machine.
- **Verify semantic-model bindings after the target model is resolved** — once the report's target semantic model is known (whether by a fresh deploy through an available semantic-model authoring skill or by selecting an existing workspace model), download its TMDL and compare all PBIR bindings (`Entity`, `queryRef`, `nativeQueryRef`, filter `Source`/`Entity` references) against the model's table/column/measure names. This applies to **both** branches: even a hand-off deploy may rename or transform the model during publish, so the diff is not optional. If names differ but models are structurally equivalent (same columns/measures), remap all table-qualified bindings via the `authoring` mode. If the models are not structurally equivalent, prompt the user before attempting to re-author — explain which tables/columns/measures don't match and ask whether to proceed.
- **Local edits stay local by default** — when a user requests changes to a local `.pbip` report, apply the changes to the local files only. Do not publish to Fabric unless the user explicitly asks to publish, upload, or push the report. Even if the report was previously published to Fabric, treat subsequent edits as local-only until told otherwise. **When the user does request publishing a local `.pbip`**, follow the [Publishing a local .pbip](#publishing-a-local-pbip) workflow: (a) confirm the target workspace once up front, (b) prompt publish-the-local-model vs. connect-to-an-existing-workspace-model, (c) on the publish-model branch, check whether a semantic-model authoring skill is available in the current session and degrade gracefully if not, (d) confirm create-new vs. update-existing for the report itself.

### PREFER

- **Soft delete** over hard delete — allows recovery.
- **`az rest` with JMESPath `--query`** for filtering — built-in JSON parsing, no extra tools needed.

### AVOID

- **Hand-writing or directly constructing PBIR JSON** — whether creating new files or modifying existing ones, all PBIR content (`definition.pbir`, `report.json`, `version.json`, pages, visuals, filters, formatting, themes, expressions) must go through the `authoring` mode. Never construct any PBIR JSON from memory or guesswork — not even "simple" structural files. No exceptions.
- **PBIR-Legacy format** — do not create, read, or update PBIR-Legacy definitions. Only modern PBIR format is supported.
- **Sending only modified parts** in `updateDefinition` — the API replaces the full definition; missing parts are deleted.
- **Using `byPath`** in `definition.pbir` for API payloads — only works for local/Git scenarios.
- **Hardcoded workspace/report IDs** — resolve dynamically via the List APIs.
- **Skipping LRO polling** — definition operations may be async; always check for 202 responses.
- **Omitting `?format=PBIR`** on `getDefinition` — may return unusable PBIR-Legacy format.
- **Retrying a create POST after receiving 202** — risks creating duplicates. See the [LRO section](#long-running-operations-lro) for the correct recovery pattern.

## Agentic Workflow

### Publishing a local `.pbip`

This is the primary entry point when a user has a local `.pbip` (report
plus sibling `.SemanticModel`) on disk and asks to publish, upload, push,
or deploy the report to a Fabric workspace.

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
ID by name (per [COMMON-CLI.md](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)).
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
  - **Available** → hand off to that workflow to
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
MUST [Verify semantic-model bindings after the target model is
resolved](#must). Even on the publish-the-local-model branch, the
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
local-source publish.

**8. Decide create-new vs. update-existing for the report.** Default the
report `displayName` to the `.pbip` filename without extension (e.g.
`SalesDashboard.pbip` → `"SalesDashboard"`). Surface the default to the
user so they can override.

- List reports in the target workspace and look up the chosen
  `displayName`.
  - **Not found** → create. Follow
    [Create Report (with Definition)](#create-report-with-definition).
  - **Found** → confirm with the user: overwrite the existing report
    (`updateDefinition`), publish under a different name, or cancel.
    Follow [Update Report Definition](#update-report-definition) on
    overwrite.

**9. Encode and upload.** Run the existing transport — base64-encode all
PBIR parts (forward-slash paths!), build the `parts` payload, POST,
capture `x-ms-operation-id` (with `--verbose` written to a file), poll
the LRO to terminal success.

**10. Clean up** any temporary files created during the flow.

> **Note on report-side verification**: there is no reliable
> programmatic way to confirm a report renders correctly post-publish —
> the report lives at a Fabric Service URL and visual rendering
> requires a browser session. Surface the workspace/report URL so the
> user can verify in the browser.

### Modifying an existing report in Fabric

1. **Authenticate** → see [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes)
2. **Find workspace** → Resolve workspace ID by name
3. **List/find report** → Resolve report ID by name
4. **Download definition** → `getDefinition?format=PBIR` → poll LRO → decode parts to local files
5. **Author PBIR content** → **Use the `authoring` mode** for ALL changes. This covers every file: `definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, visuals, filters, formatting, themes, and expressions. Follow its guidance for correct structure, schemas, and field values. Use its CLI tools to validate. Never construct any PBIR JSON from memory or guesswork.
6. **Upload changes** → Re-encode all local files to base64 → `updateDefinition` with ALL parts (modified + unmodified)
7. **Clean up** → Delete all temporary local files and directories created during the workflow

### Creating a new report in Fabric

1. **Authenticate** → see [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes)
2. **Find workspace** → Resolve workspace ID by name
3. **Resolve semantic model** → Find the semantic model ID and workspace name for the `definition.pbir` connection string
4. **Verify semantic-model bindings** → Download the target semantic model definition (TMDL) and compare all PBIR `Entity`, `queryRef`, `nativeQueryRef`, and filter references against the target table/column names. If names differ but structure matches, remap all table-qualified bindings. If models are structurally different, prompt the user before proceeding — explain what doesn't match and ask whether to re-author the affected bindings
5. **Author PBIR content** → **Use the `authoring` mode** to generate the complete PBIR definition from scratch — `definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, and all visuals. Never construct any PBIR JSON from memory or guesswork.
6. **Upload** → Encode all files to base64 → `POST /reports` with `displayName` and all definition parts
7. **Clean up** → Delete temporary local files

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong or missing `--resource` audience | Always pass `--resource "https://api.fabric.microsoft.com"` |
| `403 Forbidden` | Insufficient permissions | Check workspace role (Contributor+ for write ops) |
| `404 Not Found` | Wrong workspace or report ID | Re-resolve IDs via List APIs |
| `CorruptedPayload` | Malformed base64 or invalid PBIR JSON | Re-encode files; validate JSON before encoding |
| `202` with no result | LRO not polled to completion | Implement LRO polling pattern |
| `OperationNotSupportedForItem` | Report has encrypted sensitivity label | Cannot get definition for encrypted reports |
| `ItemDisplayNameAlreadyInUse` | Duplicate name in workspace | Use a unique display name |
| `format: "PBIR-Legacy"` | Report was created before PBIR was default | PBIR-Legacy is not supported by this skill |
| Visuals empty / no data after publish | PBIR entity names don't match workspace semantic model table names (e.g., local CSV table name vs workspace table name) | Download target semantic model TMDL, compare table names, update all `Entity`, `queryRef`, `nativeQueryRef`, and filter references to match |
| `MissingDefinitionParts` on create/update even though all files are included | Definition part paths use backslashes (`definition\report.json`) — the Fabric API requires forward slashes. On Windows, `path.join()` produces backslashes by default. | Normalize all `path` values in the payload to use forward slashes before uploading (e.g., `.replace(/\\\\/g, '/')` in Node.js, or `.Replace('\\', '/')` in PowerShell). |
| Duplicate reports appear in workspace after create | Create POST was retried after a `202 Accepted` response. Each retry risks creating a new report. | Never retry a create POST after `202`. See the [LRO section](#long-running-operations-lro) for reliable operation ID capture and recovery steps. Delete any duplicates with the Delete Report API. |
| Visuals empty after publishing a local `.pbip` via the model hand-off | The semantic-model authoring skill may rename or transform tables/columns during deploy, so the freshly deployed model's TMDL no longer matches the report's PBIR bindings. | Re-run the TMDL-diff verification against the deployed model (per MUST [Verify semantic-model bindings after the target model is resolved](#must)) and remap drifted bindings via the `authoring` mode. |
| Visuals empty after publish, despite TMDL diff being clean | `definition.pbir` `byConnection` still points at a stale model ID (e.g., from `.pbi/` cache or an earlier publish), not the freshly resolved one. | Re-run step 7 of [Publishing a local .pbip](#publishing-a-local-pbip) to set `byConnection` to the actually resolved `semanticModelId`, then re-publish. |
| Semantic-model authoring skill not available when user wants to publish the local model | No semantic-model authoring skill is loaded in the current session. | Inform the user and degrade to the connect-to-existing branch — re-prompt for which workspace model to bind the report to. Do not silently fall through. |
| Model published to one workspace, report POSTed to another | Workspace was not confirmed up front, or two different workspaces were used for the model deploy and the report publish. | Enforce the single-workspace rule (step 2 of [Publishing a local .pbip](#publishing-a-local-pbip)). Recovery: either re-publish the report into the model's workspace, or move the model. |
