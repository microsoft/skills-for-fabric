# Item Inventory — Admin API and Scanner API


## Contents

- [Item Inventory and Curation Metadata](#item-inventory-and-curation-metadata)
- [Gotchas — Item Inventory and Curation Metadata](#gotchas-item-inventory-and-curation-metadata)

> **Read this when:** Getting a reliable item list. Shared foundation for all three pillars — read before item health, label coverage or curation checks.

Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

## Item Inventory and Curation Metadata

Two different APIs are required — this is the single most important thing to get right in this skill.

### Health-only item inventory (Fabric Admin API)

```bash
az rest --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/items?type=SemanticModel"
```

Returns paginated `itemEntities[]` including `id`, `type`, `name`, `description`, `tags`,
`state`, `lastUpdatedDate`, `creatorPrincipal`, `workspaceId`, and `capacityId`.

### Why not Catalog Search?

`POST /v1/catalog/search` (see `skills/search-consumption-cli`) is a **discovery** API, not a governance source. Verified response fields are only `id`, `type`, `displayName`, `description`, `catalogEntryType`, `hierarchy.workspace` — no sensitivity label, no endorsement, no `domainId`, no refresh state. It is also **caller-scoped** (returns only items the signed-in user can see, so it under-reports for a tenant-wide audit) and its index can lag **up to 24 hours**.

Use it only to *resolve a name the user mentioned* into an item ID + workspace ID before drilling in — never as the inventory basis for a governance percentage.

> The Admin item inventory does **not** return sensitivity labels or endorsement.
> Use it for all-Fabric description and tag coverage, and use the scanner API
> below only for label and endorsement coverage across scanner-supported artifact types.

### Labels and endorsement (Power BI scanner API)

Different token audience (`https://analysis.windows.net/powerbi/api`) and an asynchronous three-call flow:

```powershell
$t = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
$h = @{ Authorization = "Bearer $t"; "Content-Type" = "application/json" }

# 1. Get workspace IDs
$ids = (Invoke-RestMethod -Uri "https://api.powerbi.com/v1.0/myorg/admin/workspaces/modified" -Headers $h).id

# 2. Scan every batch of <= 100 and aggregate successful results
$results = @()
$failedBatches = @()
for ($offset = 0; $offset -lt $ids.Count; $offset += 100) {
  $end = [Math]::Min($offset + 99, $ids.Count - 1)
  $batch = @($ids[$offset..$end])
  try {
    $body = @{ workspaces = $batch } | ConvertTo-Json
    $scan = Invoke-RestMethod -Method Post -Headers $h -Body $body `
      -Uri "https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo?lineage=false&datasourceDetails=false&getArtifactUsers=false"

    $deadline = (Get-Date).ToUniversalTime().AddMinutes(10)
    do {
      Start-Sleep -Seconds 5
      $status = Invoke-RestMethod -Headers $h `
        -Uri "https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanStatus/$($scan.id)"
      if ($status.status -eq "Failed") {
        throw "Scanner job $($scan.id) failed."
      }
      if ((Get-Date).ToUniversalTime() -ge $deadline) {
        throw "Scanner job $($scan.id) exceeded the 10-minute timeout."
      }
    } while ($status.status -ne "Succeeded")

    $results += Invoke-RestMethod -Headers $h `
      -Uri "https://api.powerbi.com/v1.0/myorg/admin/workspaces/scanResult/$($scan.id)"
  } catch {
    $failedBatches += [pscustomobject]@{ Offset = $offset; Count = $batch.Count; Error = $_.Exception.Message }
  }
}

if ($failedBatches.Count) {
  $failedBatches | Format-Table -AutoSize
  Write-Warning "Scanner coverage is incomplete; report failed batches as unassessed."
}
```

Per-item fields available in `$result.workspaces[].{datasets|reports|dashboards|...}[]`:

| Field | Notes |
|---|---|
| `sensitivityLabel.labelId` | GUID only — no friendly name. Missing ⇒ **unlabeled**. |
| `endorsementDetails` | **Absent entirely on unendorsed items** — treat missing as "not endorsed", not an error. |

Set `lineage`, `datasourceDetails`, `getArtifactUsers`, `datasetSchema`, or `datasetExpressions` to `true` only when the analysis needs them — each enlarges the payload and slows the scan.

The scanner covers Power BI artifact collections, not every Fabric-native item type.
State the scanned type denominator for label and endorsement percentages. Report
Fabric-native types absent from scanner output as **unassessed**, never as unlabeled
or unendorsed.

---

### Items in Deleted Workspaces Are Reported as Active

**Verified live and more dangerous than the workspace case**, because the obvious defence does not work.

`/v1/admin/items` returns a `state` field, but it reflects the **item's** state, not its workspace's. In the verified tenant **every one of 14,912 items returned `state: Active` — yet 461 of them (3.1%) belonged to `Deleted` workspaces.** Filtering on `item.state` removes none of them.

These ghost items silently inflate every pillar-2 and pillar-3 denominator: they appear as unlabeled, undescribed, unendorsed and stale, and no remediation can ever fix them because their workspace is gone. An agent that reports them will hand the user a worklist with unfixable rows.

**Rule: build the active-workspace ID set first, then join.**

```powershell
$t = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv
$h = @{ Authorization = "******" }

# 1. Active workspace IDs (server-side filter)
$activeWs = @{}
$u = "https://api.fabric.microsoft.com/v1/admin/workspaces?type=Workspace&state=Active"
while ($u) { $r = Invoke-RestMethod -Uri $u -Headers $h; $r.workspaces | ForEach-Object { $activeWs[$_.id] = $_.name }; $u = $r.continuationUri }

# 2. All items, then join
$items = @(); $u = "https://api.fabric.microsoft.com/v1/admin/items"
while ($u) { $r = Invoke-RestMethod -Uri $u -Headers $h; $items += $r.itemEntities; $u = $r.continuationUri }

$live  = @($items | Where-Object { $activeWs.ContainsKey($_.workspaceId) })
$ghost = @($items | Where-Object { -not $activeWs.ContainsKey($_.workspaceId) })
"Items in active workspaces: $($live.Count); excluded (deleted workspaces): $($ghost.Count)"
```

Use `$live` as the all-Fabric denominator for description, tag, and freshness
coverage. Apply the same active-workspace join to scanner output, then use only
the resulting scanner-supported artifact set as the denominator for sensitivity
label and endorsement percentages.

### Bucket items by workspace type — do not blanket-drop

Building `$activeWs` with `type=Workspace&state=Active` also silently removes items in **personal** workspaces. For domain/health questions that is correct. For **Protect** it is not: personal-workspace items hold real user data that can be labeled and leaked, and dropping them hides genuine risk.

Verified item distribution in the test tenant (14,912 items):

| Owning workspace | Items | Treatment |
|---|---|---|
| `Workspace` / Active | 14,315 | **The governed estate.** Denominator for all pillar-1/2/3 percentages. |
| `Workspace` / Deleted | 401 | Exclude — unremediable. |
| `AdminWorkspace` / Deleted | 60 | Exclude — system-owned. |
| `Personal` / Active | 129 | **Exclude from domain and endorsement metrics** (structurally impossible), but **report separately for Protect** — unlabeled personal items are a real exposure. |
| Workspace ID not in the workspace list | 7 | **Report as unknown — never silently drop.** |

> ⚠️ **Always keep an "unknown workspace" bucket.** Seven items referenced a `workspaceId` absent from the full admin workspace list. Causes are unconfirmed (timing between the two calls is the most likely). Silently discarding them means item counts won't reconcile and nobody will know why — surface the count and say it is unexplained.

```powershell
$byType = $items | Group-Object {
  if ($wsType.ContainsKey($_.workspaceId)) { $wsType[$_.workspaceId] } else { 'UNKNOWN' }
}
```
where `$wsType` maps every workspace ID to `"$($_.type)/$($_.state)"` from an **unfiltered** workspace fetch — you need the deleted and personal entries present in order to classify, and only then to exclude.

---


## Gotchas — Item Inventory and Curation Metadata

| Symptom | Cause / verified reality | Fix |
|---|---|---|
| Sensitivity label / endorsement / refresh fields missing from `/v1/admin/items` responses | **Expected** — verified that this endpoint returns only `id`, `type`, `name`, `state`, `lastUpdatedDate`, `creatorPrincipal`, `workspaceId`, `capacityId`. | Use the Power BI scanner API instead — see Item Inventory and Curation Metadata. |
| `endorsementDetails` absent on many items | The field is omitted entirely for unendorsed items. | Treat missing as "not endorsed"; do not error out. |
| `sensitivityLabel` returns only a GUID | By design — the scanner returns `labelId`, not the friendly name. | Resolve names via Microsoft Purview; report by GUID with a note if unavailable. |
| Scanner `getInfo` rejects the request | More than 100 workspace IDs in one call. | Chunk the ID list into batches of 100. |
