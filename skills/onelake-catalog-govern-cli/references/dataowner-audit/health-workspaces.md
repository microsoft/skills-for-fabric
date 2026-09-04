<!-- MODE REFERENCE for onelake-catalog-govern-cli (mode: dataowner-audit). Loaded on demand by the dataowner-audit reference. -->

# Workspace Health (Data Owner scope) — My Workspaces: Empty and Inactive


## Contents

- [The two questions this mode answers](#the-two-questions-this-mode-answers)
- [List My Workspaces (the scope for everything below)](#list-my-workspaces-the-scope-for-everything-below)
- [Find Empty Workspaces (zero items) — within my scope](#find-empty-workspaces-zero-items-within-my-scope)
- [Find Inactive Workspaces (no job run in the last 28 days) — within my scope](#find-inactive-workspaces-no-job-run-in-the-last-28-days-within-my-scope)
- [What This Mode Cannot Do (say so — don't substitute a weaker answer)](#what-this-mode-cannot-do-say-so-dont-substitute-a-weaker-answer)
- [Gotchas — Workspace Health (Data Owner)](#gotchas-workspace-health-data-owner)

> **Read this when:** A **non-admin** data owner wants to check the health of the workspaces **they administer** — how many are empty, and how many have gone quiet — **without** tenant admin rights.

Part of the `onelake-catalog-govern-cli` skill (dataowner-audit mode). Return to dataowner-audit.md for the mode's scope limits, auth and the rest of the workflow. For the **tenant-wide** version of these checks — every workspace, audit-log-grade activity, bulk role scans, and **orphaned / single-admin (bus-factor) analysis** — see the admin counterpart admin-audit/health-workspaces.md; it needs a Fabric tenant admin role.

---

> ### ⚠️ Scope — the workspaces you administer, not the tenant
> For a data-owner (non-admin) identity the **default scope is the workspaces where the caller holds the Admin role** — the ones they are accountable for and can actually act on — **not** the whole tenant, and not every workspace they can merely open. Enumerate them with the **Core** control-plane API:
>
> ```
> GET /v1/workspaces?roles=Admin
> ```
>
> Widen to `roles=Admin,Member,Contributor` only when the user explicitly asks about workspaces they merely participate in — and say which cut you used.
>
> This is the **opposite default** from `admin-audit` mode. Do **not** reach for `/v1/admin/*` here — those endpoints need a Fabric tenant admin role and return `403` to a data owner. The Core list returns only what the caller can see, which is typically a subset of the tenant.
>
> **Be transparent that this is a personal, self-scoped view.** Lead the answer with the scope, e.g. *"Across the N workspaces you administer…"* — never present a data-owner count as a tenant total. If the user wants the tenant picture ("how many workspaces exist?", "which domains are empty?"), tell them plainly it requires **tenant admin rights + `admin-audit` mode**; the Core API cannot answer it.

---

> **Reporting template.** Report each finding as **finding → evidence → why it matters → recommended action → priority → effort**, and state clean/pass results explicitly ("checked, no gap"). Always name the scope the numbers cover ("of the N workspaces you administer") **and the activity window you used**. Canonical definition: the shared Deliverable Contract.

## The two questions this mode answers

| Finding | Means | Source | Cost |
|---|---|---|---|
| **Empty** | Contains zero items | `GET /v1/workspaces/{id}/items` | 1 call per workspace |
| **Inactive (28 days)** | No **job run** in the window — a much narrower signal than the admin one | `GET /v1/workspaces/{id}/items/{itemId}/jobs/instances` | 1 call per **item** |

They are two different findings with two different blind spots. Report them as separate lines and **never merge them into a single "unused" number**.

## List My Workspaces (the scope for everything below)

Scope to the workspaces you administer. Paginate with `continuationToken` (a query parameter — Core-style, **not** the admin `continuationUri`):

```bash
url="https://api.fabric.microsoft.com/v1/workspaces?roles=Admin"
all_ws="[]"
while [ -n "$url" ] && [ "$url" != "null" ]; do
  resp=$(az rest --method GET --url "$url" --resource "https://api.fabric.microsoft.com")
  all_ws=$(jq -s '.[0] + .[1].value' <(echo "$all_ws") <(echo "$resp"))
  token=$(echo "$resp" | jq -r '.continuationToken // empty')
  if [ -n "$token" ]; then
    url="https://api.fabric.microsoft.com/v1/workspaces?roles=Admin&continuationToken=${token}"
  else
    url=""
  fi
done
echo "$all_ws" > /tmp/my_workspaces.json
```

`roles=Admin` is the default because you cannot remediate anything you are not the Admin of. The Core Workspace object exposes `displayName` (not `name` — that's the Admin object), so filter/report on `displayName`.

## Find Empty Workspaces (zero items) — within my scope

You **can** do this without admin rights: for each workspace you administer, list its items via the Core API and flag the ones with none. *Live-verified:* `GET /v1/workspaces/{id}/items` succeeds for a workspace the caller has a role on.

```bash
for id in $(jq -r '.[].id' /tmp/my_workspaces.json); do
  n=$(az rest --method GET \
        --url "https://api.fabric.microsoft.com/v1/workspaces/${id}/items" \
        --resource "https://api.fabric.microsoft.com" \
        --query "length(value)" --output tsv 2>/dev/null)
  echo "${id}	${n:-ERR}"
done | awk -F'\t' '$2==0 {print $1}'
```

> **Empty is an inventory fact, not a usage verdict.** A workspace with zero items may be brand-new, or actively churned — items created and deleted between scans. Report emptiness plainly and **do not** recommend deletion from an item count alone. The activity check below narrows the picture a little, but it only sees job runs, so it cannot prove disuse either.

## Find Inactive Workspaces (no job run in the last 28 days) — within my scope

You **can** measure activity without admin rights — but only one kind of it. `GET /v1/workspaces/{id}/items/{itemId}/jobs/instances` is a **Core** endpoint available to a workspace member, returning each run with `startTimeUtc`, `endTimeUtc`, `status` and `failureReason`. A workspace counts as inactive when **no item in it has a job run newer than the cutoff**.

```powershell
$token = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv
$headers = @{ Authorization = "Bearer $token" }
$cutoff = (Get-Date).ToUniversalTime().AddDays(-28)

function Get-AllValues([string]$Uri) {
  $values = @()
  $baseUri = $Uri
  $separator = if ($baseUri.Contains('?')) { '&' } else { '?' }
  do {
    $page = Invoke-RestMethod -Uri $Uri -Headers $headers
    $values += @($page.value)
    $continuationToken = [string]$page.continuationToken
    $Uri = if ([string]::IsNullOrWhiteSpace($continuationToken)) {
      $null
    } else {
      "${baseUri}${separator}continuationToken=$([uri]::EscapeDataString($continuationToken))"
    }
  } while ($null -ne $Uri)
  $values
}

$workspaces = Get-Content /tmp/my_workspaces.json | ConvertFrom-Json
$workspaceLastJob = foreach ($workspace in $workspaces) {
  $items = @(Get-AllValues "https://api.fabric.microsoft.com/v1/workspaces/$($workspace.id)/items")
  $unassessableItems = 0
  $latest = foreach ($item in $items) {
    try {
      $jobs = @(Get-AllValues "https://api.fabric.microsoft.com/v1/workspaces/$($workspace.id)/items/$($item.id)/jobs/instances")
      if ($jobs.Count -eq 0) {
        $unassessableItems++
        continue
      }
      $jobs | ForEach-Object { [datetime]$_.startTimeUtc }
    } catch {
      $unassessableItems++
      continue
    }
  }
  [pscustomobject]@{
    WorkspaceId       = $workspace.id
    ItemCount         = $items.Count
    UnassessableItems = $unassessableItems
    LastJobUtc        = @($latest | Sort-Object -Descending)[0]
  }
}

# Inactive candidates have items, at least one assessable item, and no recent run.
$workspaceLastJob | Where-Object {
  $_.ItemCount -gt 0 -and
  $_.UnassessableItems -lt $_.ItemCount -and
  (-not $_.LastJobUtc -or $_.LastJobUtc -lt $cutoff)
}

# Report these separately as unassessed, never inactive.
$workspaceLastJob | Where-Object {
  $_.ItemCount -gt 0 -and $_.UnassessableItems -eq $_.ItemCount
}
```

Both the item list and every job-instance list are paginated. Exhaust every
`continuationToken` before calculating the newest run; otherwise a later page can
contain the evidence that a workspace is active.

> ### ⚠️ Say what "inactive" actually measured — this signal is far narrower than the admin one
> `jobs/instances` records **job runs**: notebook runs, pipeline runs, dataflow refreshes, and scheduled or on-demand semantic model refreshes. It does **not** record:
>
> - report and dashboard **views**
> - SQL analytics endpoint / Warehouse **queries**
> - Lakehouse browsing and direct **OneLake reads and writes**
> - item **edits** made in the portal
>
> A workspace of Power BI reports opened by 500 people every morning has **zero job runs**, and this check will call it inactive. The admin-only Activity Events API sees all of the above; this one does not.
>
> **Never report the number without the definition.** Say *"N of the M workspaces you administer had no job run in the last 28 days"* — not *"N workspaces are unused"*. If the user needs a real usage verdict, say plainly that it requires tenant admin rights and `admin-audit` mode.

> ### The 28-day window is a choice — print it
> 28 days matches the retention ceiling of the admin Activity Events API (live-verified there: `-27` days succeeded, `-28` was rejected), so a data-owner answer stays comparable to the admin one and never implies more history than the tenant can confirm. Job history is not bound by that same limit, so a longer look-back may return data — but if you use one, **state the window**, and never quietly shorten it because the scan was slow.

**Two failure modes to handle rather than hide:**

| What you'll hit | Why | What to do |
|---|---|---|
| Empty `value` list, or a non-`200`, on `jobs/instances` | Not every item type has a job concept — reports, dashboards, unscheduled semantic models, lakehouses with no scheduled work | Treat **both** as *no signal*, not as *inactive*. Say how many workspaces rested entirely on unassessable items |
| An **empty** workspace comes back inactive | Zero items means zero job history, so it is trivially inactive — and the fact adds nothing | **Exclude empty workspaces from the inactive count.** Otherwise one workspace is reported twice as two different problems |

**Cost:** one call per item plus one per workspace. Fine for tens of workspaces, slow for hundreds — if you cap or sample, say so instead of presenting a partial scan as a complete one.

### Reporting the two together

- **Empty** — an inventory fact. Give the count and the names.
- **Has items + no job run in 28 days** — a *candidate for review*, nothing more.
- **Empty + no domain assigned** — the strongest cleanup candidate a data owner can identify alone (see Find My Unassigned Workspaces).

Deletion is never an automatic recommendation, and in this mode you cannot see the usage evidence that would justify one. Surface candidates for a human decision.

## What This Mode Cannot Do (say so — don't substitute a weaker answer)

| Question | Why it's out of reach without admin | Where it lives |
|---|---|---|
| "How many workspaces are in the tenant?" | Core `/v1/workspaces` is user-scoped; you see only a subset. | `admin-audit` — `GET /v1/admin/workspaces?type=Workspace&state=Active` |
| "Which workspaces are unused in the **audit-log** sense — views, queries, edits?" | The Activity Events API (`/v1.0/myorg/admin/activityevents`) is a **Power BI admin** endpoint — `403` for a data owner. All you can measure here is **job runs**. | `admin-audit/health-workspaces.md` |
| "Which of my workspaces are **orphaned** / single-admin (bus factor)?" | **Out of scope for this mode by design — not a permission wall.** Bus factor is a portfolio question about the whole estate; a self-scoped answer covers only your corner while reading as though it covered more. Route it to an admin, who can see the full distribution and the escalation paths. | `admin-audit/health-workspaces.md` |
| "Which domains are empty?" | No Core API lists a domain's workspaces. | `admin-audit/health-domains.md` |

## Gotchas — Workspace Health (Data Owner)

| Symptom | Cause / verified reality | Fix |
|---|---|---|
| Count looks smaller than the portal / than a colleague's | Core `/v1/workspaces` is **user-scoped**, and `roles=Admin` narrows it further to the ones you administer. | Expected. State the scope and the `roles` cut; for the tenant total, use `admin-audit` mode. |
| Answer doesn't say whose workspaces it covers | Scope left implicit; a reader may assume tenant-wide. | Lead with "of the N workspaces you administer". |
| Reported "N workspaces are unused" | The Core signal is **job runs only** — blind to report views, SQL queries, OneLake reads and portal edits. | Report it as "no job run in the last 28 days" and name the window. |
| An empty workspace also shows up in the inactive list | Zero items means zero job history — trivially inactive, and meaningless. | Exclude empty workspaces from the inactive count; report the two findings separately. |
| `jobs/instances` returns nothing for an item | That item type has no job concept (reports, dashboards, unscheduled models). | *No signal*, not *inactive*. State how much of the workspace was unassessable. |
| Activity scan runs for a very long time | One call per **item**, not per workspace. | Cap or sample if you must — and say the scan was partial rather than presenting it as complete. |
| Asked about orphaned / single-admin workspaces | Bus factor is an **admin** portfolio question; this mode deliberately doesn't answer it. | Say so and route to `admin-audit` — don't produce a self-scoped answer that looks tenant-wide. |
| `403` on any `/v1/admin/*` call | You lack the tenant admin role. | Don't retry or work around it; switch to `admin-audit` mode only if the identity actually has admin rights. |
| Pagination stops early | Used admin-style `continuationUri` instead of the Core `continuationToken` **query parameter**. | Core APIs page via `?continuationToken=...`. |
| Recommending deletion because a workspace has 0 items | **Empty ≠ unused**, and the job-run signal can't prove disuse either. | Report emptiness as inventory only; leave deletion to a human decision. |
