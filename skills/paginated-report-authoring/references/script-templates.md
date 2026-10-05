# Script Templates

Two reusable scripts, both in [`../scripts/`](../scripts/):

- `gen_rdl.py` — generates a schema-valid RDL 2016 bound to a semantic model.
- `publish.ps1` — publishes the `.rdl` via the Power BI Imports API and polls to completion.

## RDL generator (`gen_rdl.py`)

Key patterns that make the generator reliable:

**1. Central XML escaping + local validation.** Escape once in the textbox helper; parse before upload.

```python
import base64, xml.dom.minidom as minidom

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

# ... build `rdl` string ...
minidom.parseString(rdl)                    # raises on malformed XML -> fail fast
open("page_test.rdl", "w", encoding="utf-8").write(rdl)
```

**2. Data-driven columns.** Define the detail grid as a list of tuples so the field list, header row,
detail row, and column widths all stay in sync:

```python
# (Header label, detail expression, width_in, align, format, is_number)
COLUMNS = [
    ("Claim ID",   "=Fields!ClaimID.Value",     1.0, "Left",  None,     False),
    ("Date",       "=Fields!ClaimDate.Value",   1.0, "Left",  "d",      False),
    ("Status",     "=Fields!ClaimStatus.Value", 1.0, "Left",  None,     False),
    ("Amount",     "=Fields!ClaimAmount.Value", 1.1, "Right", "'$'#,0", True),
]
```

Generate `<Field>`s (with bracketed `<DataField>`), the header `TablixRow`, the detail `TablixRow`,
and the `<TablixColumns>` all from `COLUMNS`.

**3. Reusable textbox helper.** One helper produces every cell (see the full script) so styling,
padding, borders and formatting are consistent.

Run it:

```powershell
python .\scripts\gen_rdl.py       # -> page_test.rdl (validated)
```

## Publisher (`publish.ps1`)

Parameterized wrapper around the Imports API (full listing in `../scripts/publish.ps1`):

```powershell
param(
  [string]$RdlPath      = ".\page_test.rdl",
  [string]$WorkspaceId  = "<workspace-guid>",
  [string]$DisplayName  = "page_test",
  [string]$NameConflict = "Abort"     # Abort=create new, Overwrite=replace existing
)
$token = az account get-access-token --resource 'https://analysis.windows.net/powerbi/api' `
         --query accessToken -o tsv
$base  = "https://api.powerbi.com/v1.0/myorg/groups/$WorkspaceId"

Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue
$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Authorization =
  [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
$form  = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $RdlPath))
$form.Add([System.Net.Http.ByteArrayContent]::new($bytes), 'file', "$DisplayName.rdl")

$url  = "$base/imports?datasetDisplayName=$DisplayName.rdl&nameConflict=$NameConflict"
$resp = $client.PostAsync($url, $form).Result
$importId = ($resp.Content.ReadAsStringAsync().Result | ConvertFrom-Json).id

for ($i = 0; $i -lt 40; $i++) {
  $st = Invoke-RestMethod -Uri "$base/imports/$importId" `
        -Headers @{ Authorization = "Bearer $token" }
  if ($st.importState -eq 'Succeeded') { $st.reports; break }
  if ($st.importState -eq 'Failed')    { $st.error | ConvertTo-Json -Depth 8; break }
  Start-Sleep 3
}
```

Run it:

```powershell
.\scripts\publish.ps1 -WorkspaceId "<guid>" -RdlPath .\page_test.rdl
```

## End-to-end

```powershell
python .\scripts\gen_rdl.py
.\scripts\publish.ps1 -WorkspaceId "<workspace-guid>"
# open the returned webUrl, run the report, verify data + parameters
```
