param(
  [string]$RdlPath = "C:\Users\amolmanocha\.copilot\session-state\845b2459-6f84-4bc6-a922-e3ca57eaa24a\files\page_test.rdl",
  [string]$WorkspaceId = "9e818cab-e3c8-481c-bf38-1793992f9777",
  [string]$DisplayName = "page_test",
  [string]$NameConflict = "Abort"
)
$ErrorActionPreference = 'Stop'

$token = az account get-access-token --resource 'https://analysis.windows.net/powerbi/api' --query accessToken -o tsv
if (-not $token) { Write-Error 'no PBI token'; exit 1 }

$base = "https://api.powerbi.com/v1.0/myorg/groups/$WorkspaceId"
$auth = @{ Authorization = "Bearer $token" }

try { Add-Type -AssemblyName System.Net.Http -ErrorAction Stop } catch { }
$client = [System.Net.Http.HttpClient]::new()
$client.DefaultRequestHeaders.Authorization =
  [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)
$form = [System.Net.Http.MultipartFormDataContent]::new()
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $RdlPath))
$form.Add([System.Net.Http.ByteArrayContent]::new($bytes), 'file', 'page_test.rdl')
$dn = "$DisplayName.rdl"
$url = "$base/imports?datasetDisplayName=$([uri]::EscapeDataString($dn))&nameConflict=$NameConflict"
$resp = $client.PostAsync($url, $form).Result
$respBody = $resp.Content.ReadAsStringAsync().Result
if (-not $resp.IsSuccessStatusCode) {
  Write-Host "IMPORT_POST_HTTP $([int]$resp.StatusCode)"
  Write-Host $respBody
  exit 1
}
$importId = ($respBody | ConvertFrom-Json).id
Write-Host "Import id: $importId"

for ($i = 0; $i -lt 40; $i++) {
  $st = Invoke-RestMethod -Uri "$base/imports/$importId" -Headers $auth
  Write-Host "  importState: $($st.importState)"
  if ($st.importState -eq 'Succeeded') {
    $st.reports | ForEach-Object { Write-Host "REPORT name=$($_.name) id=$($_.id) webUrl=$($_.webUrl)" }
    exit 0
  }
  if ($st.importState -eq 'Failed') { Write-Host "IMPORT_FAILED:"; Write-Host ($st.error | ConvertTo-Json -Depth 8); exit 1 }
  Start-Sleep -Seconds 3
}
Write-Host 'timeout'; exit 1
