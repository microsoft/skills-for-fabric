# powerbi-report-cli management mode -- Power BI Report Items in Fabric - Part 2

## Contents

- [Examples: CRUD Operations](#examples-crud-operations)
  - [List Reports](#list-reports)
  - [Get Report (Properties)](#get-report-properties)
  - [Get Report Definition](#get-report-definition)
  - [Create Report (with Definition)](#create-report-with-definition)
  - [Update Report Definition](#update-report-definition)
  - [Conceptual fallback safety requirements (not an executable workflow)](#conceptual-fallback-safety-requirements-not-an-executable-workflow)
  - [Update Report (Properties)](#update-report-properties)
  - [Delete Report](#delete-report)
- [Long-Running Operations (LRO)](#long-running-operations-lro)
- [PBIR Definition Structure](#pbir-definition-structure)
  - [definition.pbir — Semantic Model Reference](#definitionpbir--semantic-model-reference)


Continuation of `management.md`. Open this file directly from the skill reference index.

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
set -euo pipefail

# Robust file-based flow: save only the final successful PBIR body, then unpack it.
GET_DEF_URL="https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/getDefinition?format=PBIR"

az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "$GET_DEF_URL" \
  --output-file payload.json \
  --verbose 2>&1 | tee get-definition-start.log

# If the initial 202 response appears, payload.json is not the definition yet.
# Capture the operation ID from verbose headers, poll to Succeeded, then save
# the terminal successful getDefinition body to payload.json before unpacking.
OP_ID=$(grep -ioE "x-ms-operation-id[^a-f0-9-]*[a-f0-9-]+" get-definition-start.log | grep -ioE "[a-f0-9-]+$" | head -1 || true)
if [ -n "$OP_ID" ]; then
  OP_URL="https://api.fabric.microsoft.com/v1/operations/$OP_ID"
  MAX_LRO_ATTEMPTS=60
  LRO_ATTEMPT=1
  RETRY_AFTER=$(grep -ioE "Retry-After[^0-9]*[0-9]+" get-definition-start.log | grep -oE "[0-9]+$" | head -1 || true)
  SLEEP_SECONDS=5
  MAX_SLEEP_SECONDS=30
  if [ -n "$RETRY_AFTER" ]; then
    SLEEP_SECONDS="$RETRY_AFTER"
    [ "$SLEEP_SECONDS" -gt "$MAX_SLEEP_SECONDS" ] && SLEEP_SECONDS="$MAX_SLEEP_SECONDS"
  fi
  while [ "$LRO_ATTEMPT" -le "$MAX_LRO_ATTEMPTS" ]; do
    if ! STATUS=$(az rest --method get \
      --resource "https://api.fabric.microsoft.com" \
      --url "$OP_URL" \
      --query status \
      --output tsv); then
      echo "Failed to poll getDefinition LRO status for operation $OP_ID" >&2
      exit 1
    fi
    case "$STATUS" in
      Succeeded) break ;;
      Failed|Cancelled)
        az rest --method get \
          --resource "https://api.fabric.microsoft.com" \
          --url "$OP_URL"
        exit 1
        ;;
      Running|NotStarted) ;;
      "") echo "Empty getDefinition LRO status for operation $OP_ID" >&2; exit 1 ;;
      *) echo "Unexpected getDefinition LRO status: $STATUS" >&2; exit 1 ;;
    esac
    if [ "$LRO_ATTEMPT" -eq "$MAX_LRO_ATTEMPTS" ]; then
      echo "Timed out waiting for getDefinition LRO operation $OP_ID" >&2
      exit 1
    fi
    # Honor the initial Retry-After header when present; subsequent Retry-After
    # values are not reliably exposed by az rest with --query/--output tsv, so
    # use documented bounded backoff without corrupting status parsing.
    sleep "$SLEEP_SECONDS"
    if [ "$SLEEP_SECONDS" -lt "$MAX_SLEEP_SECONDS" ]; then
      SLEEP_SECONDS=$((SLEEP_SECONDS * 2))
      [ "$SLEEP_SECONDS" -gt "$MAX_SLEEP_SECONDS" ] && SLEEP_SECONDS="$MAX_SLEEP_SECONDS"
    fi
    LRO_ATTEMPT=$((LRO_ATTEMPT + 1))
  done

  az rest --method get \
    --resource "https://api.fabric.microsoft.com" \
    --url "https://api.fabric.microsoft.com/v1/operations/$OP_ID/result" \
    --output-file payload.json \
    --verbose 2>&1 | tee get-definition-result.log
fi

# Only unpack payload.json after it contains either the synchronous 200 body or
# the /operations/$OP_ID/result body from the terminal successful LRO.
```

> **Format check**: After retrieving the definition, verify
> `definition.format == "PBIR"`. If it is `"PBIR-Legacy"`, this skill does not
> support that format. `powerbi-report-author unpack` also rejects non-PBIR
> input early with `UNPACK_FORMAT_UNSUPPORTED`, so do not hand-decode a legacy
> blob.

#### Decode Definition Parts to Local Files

> **Note**: `getDefinition` often returns `202 Accepted` (LRO). Check the
> Long-Running Operations section to extract the operation ID and poll for the
> result before decoding.

Use `powerbi-report-author unpack` for the decode + path-normalization step.
The file-based form is recommended for LRO safety and for Windows shells:

```bash
powerbi-report-author unpack ./MyReport.Report --input payload.json
```

`--input payload.json` supersedes stdin. By default unpack refuses to clobber
existing files; pass `--force` only after the user confirms staged overwrite.

Default stdin form (only when the final PBIR `getDefinition` JSON is already on
stdout, such as after a completed LRO poll command):

```bash
printf '%s' "$DEFINITION_JSON" | powerbi-report-author unpack ./MyReport.Report
```

### Create Report (with Definition)

Creates a new report with a PBIR definition. Supports LRO.

- **Permissions**: Contributor workspace role
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

`pack --raw --mode create --display-name '<name>' [--description '<text>']`
emits the Fabric create request body with `displayName`, optional
`description`, and **all qualifying PBIR parts** from the `.Report` directory.

Run **Modern-PBIR preflight before pack** in `management.md` first.

Recommended file-based flow (especially on Windows/PowerShell):

```bash
set -euo pipefail

powerbi-report-author pack ./MyReport.Report --raw --mode create --display-name "My New Report" --description "Created via Fabric API" --out create-report.json

az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --headers "Content-Type=application/json" \
  --body @create-report.json \
  --verbose 2>&1 | tee create-report-start.log
```

After the POST, follow [Long-Running Operations](#long-running-operations-lro)
for `202 Accepted`: capture `x-ms-operation-id`, poll to terminal state, and
never retry the create POST after a `202`.

Direct pipe form (Bash/Zsh; PowerShell callers should prefer the file-based
form unless they first force UTF-8 console output):

```bash
set -euo pipefail

powerbi-report-author pack ./MyReport.Report --raw --mode create --display-name "My New Report" --description "Created via Fabric API" | az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" \
  --headers "Content-Type=application/json" \
  --body @- \
  --verbose 2>&1 | tee create-report-pipe-start.log
```

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
# Then, if you intentionally use the pipe form:
powerbi-report-author pack ./MyReport.Report --raw --mode create --display-name "My New Report" --description "Created via Fabric API" | az rest --method post --resource "https://api.fabric.microsoft.com" --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports" --headers "Content-Type=application/json" --body "@-" --verbose 2>&1 | Out-File ".\create-report-pipe-start.log" -Encoding utf8
```

Keep `2>&1` on the `az rest` side of the PowerShell pipe so verbose response
headers are captured without merging pack diagnostics into the request-body
stdin. Do not put `2>&1` on the `powerbi-report-author pack` side.

> **Important**: `definition.pbir` is always required. `pack` starts from the
> `.Report` boundary (or locates it from a `.pbip`) and emits the full PBIR API
> definition body. Make sure the local `.Report` directory mirrors the complete
> PBIR layout before packing.

### Update Report Definition

Overwrites the entire definition. This is a **POST** and supports LRO.

- **Permissions**: Read and write permissions on the report
- **Scopes**: `Report.ReadWrite.All` or `Item.ReadWrite.All`

`pack` defaults to update mode. Do not pass `--display-name` for
`updateDefinition`; the body contains only `definition.parts` and pack emits
**all qualifying PBIR parts** on every invocation.

> **Preflight**: run the
> **Modern-PBIR preflight before pack** in `management.md` before
> packing. A legacy `.Report` that still contains `definition.pbir` packs a
> partial payload, and replace-all `updateDefinition` then deletes the omitted
> parts.

Recommended file-based flow (especially on Windows/PowerShell):

```bash
set -euo pipefail

powerbi-report-author pack ./MyReport.Report --raw --out update-definition.json

az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/updateDefinition" \
  --headers "Content-Type=application/json" \
  --body @update-definition.json \
  --verbose 2>&1 | tee update-definition-start.log
```

After the POST, follow [Long-Running Operations](#long-running-operations-lro)
for `202 Accepted`: capture `x-ms-operation-id` and poll to terminal state.

Direct pipe form (Bash/Zsh; PowerShell callers should prefer the file-based
form unless they first force UTF-8 console output):

```bash
set -euo pipefail

powerbi-report-author pack ./MyReport.Report --raw | az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/updateDefinition" \
  --headers "Content-Type=application/json" \
  --body @- \
  --verbose 2>&1 | tee update-definition-pipe-start.log
```

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
# Then, if you intentionally use the pipe form:
powerbi-report-author pack ./MyReport.Report --raw | az rest --method post --resource "https://api.fabric.microsoft.com" --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/reports/$REPORT_ID/updateDefinition" --headers "Content-Type=application/json" --body "@-" --verbose 2>&1 | Out-File ".\update-definition-pipe-start.log" -Encoding utf8
```

Keep `2>&1` on the `az rest` side of the PowerShell pipe so verbose response
headers are captured without merging pack diagnostics into the request-body
stdin. Do not put `2>&1` on the `powerbi-report-author pack` side.

> **Critical**: `updateDefinition` replaces the **entire** definition. Include
> ALL parts — modified and unmodified. Omitting parts deletes them.

Optional query parameter `?updateMetadata=true` updates item metadata from
`.platform` file if included.

### Conceptual fallback safety requirements (not an executable workflow)

`powerbi-report-author >= 0.3.0-beta.0` remains required for all primary documented
workflows in this skill. This section is **not** permission to continue with a
non-CLI jq/base64/find/PowerShell branch when the preflight check fails. If the
CLI is missing or older than 0.3.0-beta.0, stop and instruct the user to install or
upgrade `@microsoft/powerbi-report-authoring-cli@latest` before publishing,
downloading, or updating PBIR definitions.

The safety requirements below exist only to evaluate external legacy/manual
recipes outside this skill. Any such replacement would need safety parity with
`pack`/`unpack`, including normalized non-traversing part paths, PBIR
payload-type checks, valid base64 decode/encode, the same part allowlist, and
the same file-exclusion rules before writing files or constructing
create/update request bodies. Because this skill does not provide an
executable, safety-equivalent non-CLI branch, agents must not attempt to
assemble one from these requirements.

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
COMMON-CLI.md § Long-Running Operations (see `../../../common/COMMON-CLI.md`, section `long-running-operations-lro-pattern`).

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
