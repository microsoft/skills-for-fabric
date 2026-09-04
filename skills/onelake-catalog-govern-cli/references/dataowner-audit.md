<!-- MODE REFERENCE for onelake-catalog-govern-cli (mode: dataowner-audit). Loaded on demand by the dispatcher SKILL.md. -->

> **Routing already happened.** The dispatcher SKILL.md is the single source of truth for the 2×2 mode grid, routing rules, and the permission-tier / known-gap notes. This is the **dataowner-audit** mode reference — reached when a **non-admin** checks governance for the workspaces they can access.


> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. This skill uses only the **Core** (non-admin) API — no tenant admin role needed. It only sees what the caller has access to.
> 4. **Scope limitation is real, not just a permission nuance**: there is no Core API to list all workspaces assigned to a domain (that endpoint — `/v1/admin/domains/{id}/workspaces` — only exists under `/admin`). This means empty-domain detection and tenant-wide domain-assignment analysis are **not possible** with this skill. Tell the user this upfront rather than presenting partial results as a full audit.

# OneLake Catalog Govern — Data Owner Audit (non-admin) CLI Skill


## Contents

- [Prerequisite Knowledge](#prerequisite-knowledge)
- [Table of Contents](#table-of-contents)
- [Must/Prefer/Avoid](#mustpreferavoid)
- [List My Workspaces](#list-my-workspaces)
- [List Domains I Can See](#list-domains-i-can-see)
- [Find My Unassigned Workspaces](#find-my-unassigned-workspaces)
- [Look Up a Single Workspace's Domain](#look-up-a-single-workspaces-domain)
- [Check Description Coverage for My Items](#check-description-coverage-for-my-items)
- [Examples](#examples)
- [Gotchas and Troubleshooting](#gotchas-and-troubleshooting)

Read-only checks of domain assignment scoped to the caller's own workspaces, using the Fabric **Core** REST API (no admin role required). For a full tenant-wide audit (empty domains, ownership, metadata completeness, and overall domain-assignment coverage), see the companion skill `admin-audit` mode (requires Fabric/Power BI tenant admin).

## Prerequisite Knowledge

- `govern-roles.md` — **read first**: what a "data owner" can and can't see, and how domain contributor + workspace Admin combine
- `catalog-concepts.md` — entity model; which concepts are API-backed vs. conceptual
- Repository `common/COMMON-CORE.md` — Fabric REST API patterns, auth, pagination
- Repository `common/COMMON-CLI.md` — CLI implementation (`az rest`, pagination pattern, quick reference)

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Authentication & Token Acquisition | COMMON-CORE.md § Authentication & Token Acquisition | Standard user delegated token — no admin role needed |
| Authentication Recipes | COMMON-CLI.md § Authentication Recipes | `az login` flows and token acquisition |
| Resolve Workspace Properties | COMMON-CLI.md § Finding Workspaces and Items in Fabric | Workspace name → ID resolution |
| List My Workspaces | [Data-owner audit § List My Workspaces](#list-my-workspaces) | |
| Workspace Health (empty / inactive) | `dataowner-audit/health-workspaces.md` | Empty workspaces & 28-day inactivity (**job runs only**) among the workspaces you administer. Orphaned / bus-factor analysis is **admin-only** |
| List Domains I Can See | [Data-owner audit § List Domains I Can See](#list-domains-i-can-see) | |
| Find My Unassigned Workspaces | [Data-owner audit § Find My Unassigned Workspaces](#find-my-unassigned-workspaces) | |
| Look Up a Single Workspace's Domain | [Data-owner audit § Look Up a Single Workspace's Domain](#look-up-a-single-workspaces-domain) | |
| Check Description Coverage for My Items | [Data-owner audit § Check Description Coverage for My Items](#check-description-coverage-for-my-items) | Only curation signal available without admin rights |
| Catalog Search Syntax | `skills/search-consumption-cli/SKILL.md` | Type filters, pagination, error codes |
| Examples | [Data-owner audit § Examples](#examples) | |
| Gotchas and Troubleshooting | [Data-owner audit § Gotchas and Troubleshooting](#gotchas-and-troubleshooting) | |

---

## Must/Prefer/Avoid

### MUST DO

- **Tell the user the scope limit before running anything** — this skill can only answer "which of *my* workspaces are unassigned," not "which domains are empty" or "what is the tenant-wide assignment picture." If the user actually wants a full audit, they need tenant admin rights and `admin-audit` mode.
- **Call `GET /v1/workspaces/{id}` per workspace** to reliably get `domainId` — the list endpoint (`GET /v1/workspaces`) may omit it in the summary view; confirm the field is present before relying on it.
- **Paginate `GET /v1/workspaces`** via `continuationToken` (query parameter, not `continuationUri` like the admin API — different pagination shape).

### PREFER

- **Filter by role** using `?roles=Admin,Member,Contributor` on `GET /v1/workspaces` to scope to workspaces the user actually manages, rather than every workspace they merely have Viewer access to.
- **Map domain IDs to names** via `GET /v1/domains` once, then join locally, rather than repeated lookups.

### AVOID

- Do NOT claim to detect "empty domains" or run a full tenant-wide assignment audit — the required Core endpoint doesn't exist. Redirect the user to the admin skill for that.
- Do NOT confuse this with `admin-audit` mode — that one is tenant-wide and admin-only; this one is self-scoped and role-agnostic.
- Do NOT assume `GET /v1/domains` returns only domains the caller "owns" — verify actual returned entries against what the user expects, since the delegated scope (`Domain.Read.All`) does not guarantee tenant-wide restriction is enforced identically to workspace access.

---

## List My Workspaces

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces?roles=Admin,Member,Contributor" \
  --resource "https://api.fabric.microsoft.com"
```

Returns only workspaces the caller can access. Paginate with `continuationToken`:

```bash
url="https://api.fabric.microsoft.com/v1/workspaces?roles=Admin,Member,Contributor"
all_ws="[]"
while [ -n "$url" ] && [ "$url" != "null" ]; do
  resp=$(az rest --method GET --url "$url" --resource "https://api.fabric.microsoft.com")
  all_ws=$(jq -s '.[0] + .[1].value' <(echo "$all_ws") <(echo "$resp"))
  token=$(echo "$resp" | jq -r '.continuationToken // empty')
  if [ -n "$token" ]; then
    url="https://api.fabric.microsoft.com/v1/workspaces?roles=Admin,Member,Contributor&continuationToken=${token}"
  else
    url=""
  fi
done
echo "$all_ws" > /tmp/my_workspaces.json
```

---

## List Domains I Can See

```bash
url="https://api.fabric.microsoft.com/v1/domains"
all_domains="[]"
while [ -n "$url" ]; do
  resp=$(az rest --method GET --url "$url" --resource "https://api.fabric.microsoft.com")
  all_domains=$(jq -s '.[0] + .[1].value' <(echo "$all_domains") <(echo "$resp"))
  token=$(echo "$resp" | jq -r '.continuationToken // empty')
  if [ -n "$token" ]; then
    url="https://api.fabric.microsoft.com/v1/domains?continuationToken=${token}"
  else
    url=""
  fi
done
echo "$all_domains" > /tmp/visible_domains.json
```

Returns `id`, `displayName`, `description`, `parentDomainId`. Exhaust every
`continuationToken` before resolving a domain name or ID. This list is used only
to map domain IDs to display names for reporting — it does not tell you which
workspaces are in each domain.

---

## Find My Unassigned Workspaces

`GET /v1/workspaces` may not include `domainId` in the summary view — fetch each workspace individually to confirm:

```bash
for id in $(jq -r '.[].id' /tmp/my_workspaces.json); do
  az rest --method GET \
    --url "https://api.fabric.microsoft.com/v1/workspaces/${id}" \
    --resource "https://api.fabric.microsoft.com"
done | jq -s '[.[] | {id, displayName, domainId}]' > /tmp/my_workspaces_with_domain.json

# Unassigned ones:
jq '[.[] | select(.domainId == null)]' /tmp/my_workspaces_with_domain.json
```

### Fixing what you found

This skill is read-only, but the fix is **not necessarily an admin task**. `POST /v1/workspaces/{workspaceId}/assignToDomain` is a **Core API** call that a non-tenant-admin can make — provided the caller holds **both**:

1. **Contributor permissions on the target domain** (or domain Admin), and
2. **the workspace Admin role** on the workspace being assigned.

If you hold both, you can self-serve. Procedure, error codes and the unassign call are in `onelake-catalog-govern-cli` dataowner-remediate mode § Assign / Unassign One Workspace to a Domain — it needs no tenant admin.

If you hold only the workspace role and no domain rights, you **cannot** self-serve — ask a domain admin. Report which of the two is missing rather than "permission denied".

---

## Look Up a Single Workspace's Domain

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  --query "{name:displayName, domainId:domainId}"
```

Join against List Domains I Can See locally to resolve `domainId` to a display name.

---

## Check Description Coverage for My Items

This is the **only curation signal available without admin rights**. The scanner API used by `admin-audit` mode is admin-only, but Catalog Search returns a `description` field for every item the caller can see.

```powershell
$t = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv
$h = @{ Authorization = "Bearer $t"; "Content-Type" = "application/json" }

$items = @(); $token = $null
do {
  $b = @{ search = ""; pageSize = 1000 }
  if ($token) { $b.continuationToken = $token }
  $r = Invoke-RestMethod -Method Post -Headers $h -Body ($b | ConvertTo-Json) `
       -Uri "https://api.fabric.microsoft.com/v1/catalog/search"
  $items += $r.value; $token = $r.continuationToken
} while ($token)

$missing = $items | Where-Object { -not $_.description }
"{0} of {1} items ({2:P1}) have no description" -f $missing.Count, $items.Count, ($missing.Count / $items.Count)
$missing | Select-Object displayName, type, @{n='workspace';e={$_.hierarchy.workspace.displayName}} -First 15
```

Verified response fields per item: `id`, `type`, `displayName`, `description`, `catalogEntryType`, `hierarchy.workspace`.

> ⚠️ **Scope and freshness caveats — always state these when reporting.**
> - Results cover **only items the signed-in user can access**, so this is a *personal* curation view, not a tenant number.
> - The catalog index can lag **up to 24 hours**; newly created items may be missing.
> - There is **no** sensitivity label, endorsement, or refresh-state field here. Those require admin APIs — route the user to `admin-audit` mode.
> - Dataflow Gen1/Gen2 items are not returned at all.

See `skills/search-consumption-cli/SKILL.md` for full Catalog Search syntax, type filters, and error handling.

---

## Examples

### "Which of my workspaces have no domain assigned?"
```bash
# 1. List workspaces I manage
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces?roles=Admin,Member,Contributor" \
  --resource "https://api.fabric.microsoft.com" > /tmp/my_workspaces.json

# 2. Fetch domainId per workspace (see Find My Unassigned Workspaces)
# 3. Filter to domainId == null
# 4. Report: "You have N workspaces; M have no domain assigned: <names>"
```

### "What domain is Contoso-Hub in?"
```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  --query "domainId"
# then resolve against /v1/domains list
```

---

## Gotchas and Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `domainId` missing from `GET /v1/workspaces` list response | Core list endpoint's summary view may omit it | Call `GET /v1/workspaces/{id}` per workspace instead |
| User asks "are there empty domains?" | No Core API lists a domain's workspaces | Explain this requires tenant admin; point to `admin-audit` mode |
| User asks for tenant-wide domain assignment analysis | Same as above — no domain-to-workspace inventory is available without admin | Same redirect |
| `403` on `/v1/workspaces/{id}` | Caller lacks even Viewer access to that specific workspace | Confirm the workspace ID and the caller's role; this is a normal RBAC boundary, not a bug |
| Pagination stops early | Used `continuationUri` (admin-style) instead of `continuationToken` (Core-style) query param | Core APIs use `continuationToken` as a query parameter, not a full `continuationUri` |
| Results seem to include workspaces the user barely touches | `roles` filter omitted or too broad | Use `?roles=Admin,Member,Contributor` to exclude Viewer-only workspaces if that's not the intent |
