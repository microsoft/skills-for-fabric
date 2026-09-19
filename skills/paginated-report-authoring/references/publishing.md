# Publishing

Two ways to get an `.rdl` into a Fabric workspace. **Prefer the Power BI Imports API** — it is the
proven path, actually validates and renders the RDL, and returns descriptive errors.

## Option A — Power BI Imports API (recommended)

Multipart upload of the **raw `.rdl`**. Token audience: `https://analysis.windows.net/powerbi/api`.

```powershell
$WorkspaceId = "<workspace-guid>"
$RdlPath     = ".\page_test.rdl"
$token = az account get-access-token --resource 'https://analysis.windows.net/powerbi/api' --query accessToken -o tsv
$base  = "https://api.powerbi.com/v1.0/myorg/groups/$WorkspaceId"

Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue
$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Authorization =
  [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
$form  = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $RdlPath))
$form.Add([System.Net.Http.ByteArrayContent]::new($bytes), 'file', 'page_test.rdl')

# datasetDisplayName MUST end in .rdl. nameConflict: Abort = create new; Overwrite = replace existing.
$url  = "$base/imports?datasetDisplayName=page_test.rdl&nameConflict=Abort"
$resp = $client.PostAsync($url, $form).Result
$importId = ($resp.Content.ReadAsStringAsync().Result | ConvertFrom-Json).id

do {
  Start-Sleep 3
  $st = Invoke-RestMethod -Uri "$base/imports/$importId" -Headers @{ Authorization = "Bearer $token" }
  $st.importState
} while ($st.importState -notin 'Succeeded','Failed')
$st.reports   # -> name / id / webUrl
```

**Gotchas**
- `datasetDisplayName` **must end with `.rdl`**.
- `nameConflict` is asymmetric: **`Abort` creates a new** report; **`Overwrite` requires it to
  already exist** (first-time `Overwrite` → 404). Auto-detect by listing `$base/reports` and matching
  `reportType -eq 'PaginatedReport'`.
- Workspace must be on **Premium / Embedded / Fabric capacity** to render.
- A `Failed` import returns a descriptive `error` object — read it.

## Option B — Fabric definition API (strict)

Documented, but frequently returns `400 InvalidDefinitionFormat` for hand-authored RDLs. Token
audience: `https://api.fabric.microsoft.com`.

```
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/paginatedReports
{
  "displayName": "page_test",
  "description": "…",
  "definition": {
    "format": "PaginatedReportDefinition",
    "parts": [
      { "path": "page_test.rdl", "payload": "<base64 RDL>", "payloadType": "InlineBase64" }
    ]
  }
}
```

- The RDL part **path must equal `<displayName>.rdl`**.
- Supports LRO: `201` = created immediately; `202` = poll `Location` / `x-ms-operation-id` until
  Succeeded/Failed.
- `az rest` cannot auto-derive the audience for Fabric URLs — mint the token explicitly with
  `az account get-access-token --resource https://api.fabric.microsoft.com` and call with
  `Invoke-WebRequest` / `Invoke-RestMethod`.
- Use this only when exporting an RDL straight from Power BI Report Builder, or once the API accepts
  your generated RDL. Otherwise use Option A.

## Verify

Open the returned `webUrl` (e.g. `https://<tenant>.powerbi.com/groups/<ws>/rdlreports/<id>`), run the
report, and confirm data renders and parameters filter correctly.
