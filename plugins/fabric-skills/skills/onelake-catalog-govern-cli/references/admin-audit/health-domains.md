# Domain Health — Assignment, Ownership and Metadata


## Contents

- [List All Domains](#list-all-domains)
- [List Workspaces in a Domain](#list-workspaces-in-a-domain)
- [Find Domain-Workspace Assignment Gaps](#find-domain-workspace-assignment-gaps)
- [Domain-Health Reporting Template (mandatory for evaluative questions)](#domain-health-reporting-template-mandatory-for-evaluative-questions)
- [Find Ownerless Domains and Over-Broad Contributor Scope](#find-ownerless-domains-and-over-broad-contributor-scope)
- [Check Domain Metadata Completeness](#check-domain-metadata-completeness)

> **Read this when:** Auditing domains: what exists, which workspaces belong, which are missing, who owns them, and whether their metadata is complete.

 Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

## List All Domains

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" \
  --resource "https://api.fabric.microsoft.com"
```

Returns `id`, `displayName`, `description`, and optional `parentDomainId` for sub-domains.

---

## List Workspaces in a Domain

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/${DOMAIN_ID}/workspaces" \
  --resource "https://api.fabric.microsoft.com"
```

Use this per-domain, authoritative view when listing domain members and confirming whether a domain is empty.

---

## Find Domain-Workspace Assignment Gaps

Two gap types, both matter:

**1. Unassigned workspaces** — active workspaces with no `domainId`:
```bash
jq '[.[] | select(.state == "Active" and (.domainId == null or .domainId == ""))]' /tmp/all_workspaces.json
```

**2. Empty domains** — domains with zero workspaces assigned. For each domain from List All Domains, call List Workspaces in a Domain and flag any returning an empty `value` array.

Report: total active workspace count, unassigned count + percentage, and the named list of empty domains.

### Why each gap matters

| Finding | Why it matters |
|---|---|
| **Unassigned workspaces** | These workspaces sit outside the domain governance model, so ownership, policy delegation, and domain-level organization are incomplete. This is a governance-coverage gap, not an access-control gap. |
| **Empty domains** | Empty domains are usually either pre-staged governance containers or abandoned structure. If they are abandoned, they add catalog clutter, confuse admins about the intended operating model, and waste remediation effort if enriched instead of retired. |

### Suggesting a remediation method

When proposing a fix, name the **method**, not just the outcome — the three bulk options move different sets of workspaces. Group the unassigned list to see which fits:

- Clusters by `capacityId` → suggest **assign by capacity** (`assignWorkspacesByCapacities`).
- Clusters by a common workspace admin or team → suggest **assign by workspace admin** (`assignWorkspacesByPrincipals`).
- No clean cluster → suggest an explicit **by-ID** list, which is also the safest.

Two caveats to state alongside any suggestion:

1. Reassignment of *already-assigned* workspaces happens **only if** the tenant setting *"Allow tenant and domain admins to override workspace assignments (preview)"* is enabled — otherwise those workspaces are silently skipped.
2. All three methods are **point-in-time**. They do not assign workspaces created later; only a **default domain** (portal-only) does that.

Execution lives in `admin-remediate` mode.

---

## Domain-Health Reporting Template (mandatory for evaluative questions)

For **evaluative** prompts such as "review domains health", do **not** stop at counts. Report each applicable finding as:

**finding -> evidence -> why it matters -> recommended action -> priority -> effort**

At minimum, cover these domain-health checks individually:

| Finding type | Must report | Why it matters guidance | Recommended action guidance |
|---|---|---|---|
| **Assignment gap** | Unassigned workspaces | Governance coverage is incomplete; these workspaces are outside the intended domain structure | Recommend one named bulk-assignment method or an explicit by-ID list |
| **Cleanup candidate** | Empty / unused domains | May be abandoned governance scaffolding; creates clutter and false operating complexity | Tell the user to decide **keep vs. delete** before adding labels/descriptions or assigning owners |
| **Ownership risk** | Ownerless domains | Nobody is accountable for curation or controlled membership | Assign domain Admins, preferably a group |
| **Membership-control risk** | `EntireTenant` contributor scope | Any user can place workspaces into the domain, so membership is uncontrolled | Narrow contributor scope before mass assignment |
| **Protection gap** | Missing default sensitivity label | New or touched-unlabeled items miss a domain-level labeling baseline | Set `defaultLabelId` before bulk cleanup of unlabeled content |
| **Metadata / discoverability gap** | Missing descriptions | Domain purpose is unclear to admins and consumers | Add concise descriptions after deciding the domain is worth keeping |
| **Clean / pass finding** | Healthy description coverage or other zero-gap result | Confirms no remediation is needed in that area and prevents the reader from assuming it was skipped | Say explicitly that no action is needed |

For **empty / unused domains**, always include a recommendation path:

1. **Keep** if the domain is intentionally pre-created for near-term onboarding.
2. **Delete** if it is stale, abandoned, or test-only.
3. **Review before delete** if the domain has subdomains or known operational use.

For **clean findings**, explicitly say so. Example: **"0/10 domains missing descriptions — no description remediation is needed."**

---

## Find Ownerless Domains and Over-Broad Contributor Scope

A domain with **no assigned Admin** is an ownerless domain — nobody is accountable for its curation, and nobody can manage it except tenant admins. This is the real, API-backed form of what users often call a missing "steward". Treat it as a **pillar-1 health gap** alongside empty domains and unassigned workspaces.

```powershell
$t = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv
$h = @{ Authorization = "Bearer $t" }
function Get-AllPages([string]$Uri, [string]$Collection) {
  $results = @()
  do {
    $page = Invoke-RestMethod -Uri $Uri -Headers $h
    $results += @($page.$Collection)
    $Uri = $page.continuationUri
  } while ($Uri)
  $results
}

$domains = Get-AllPages "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" "domains"

$report = foreach ($d in $domains) {
  $ra = Get-AllPages "https://api.fabric.microsoft.com/v1/admin/domains/$($d.id)/roleAssignments" "value"
  $ws = Get-AllPages "https://api.fabric.microsoft.com/v1/admin/domains/$($d.id)/workspaces" "value"
  [pscustomobject]@{
    Domain       = $d.displayName
    IsSubdomain  = [bool]$d.parentDomainId
    AdminCount   = ($ra | Where-Object role -eq 'Admin').Count
    OpenToTenant = [bool](($ra | Where-Object role -eq 'Contributor').principal.type -contains 'EntireTenant')
    Workspaces   = $ws.Count
  }
}
$report | Sort-Object Workspaces -Descending | Format-Table -AutoSize
```

`roleAssignments` returns `role` (`Admin` | `Contributor`) and `principal` with a `type` of `User`, `Group`, `ServicePrincipal`, `ServicePrincipalProfile`, or `EntireTenant`.

### Gaps to report

| Gap | Test | Why it matters |
|---|---|---|
| **Ownerless domain** | `AdminCount == 0` | No accountable owner; only tenant admins can manage it. Rank by workspace count — an ownerless domain holding 129 workspaces is far worse than an empty one. |
| **Open contributor scope** | A `Contributor` principal of type `EntireTenant` | *Any* user in the tenant can assign workspaces into this domain, so its membership is uncontrolled. |
| **Ownerless AND populated** | `AdminCount == 0` and `Workspaces > 0` | The highest-priority combination — governed content with nobody governing it. |
| **Single-user ownership** | Exactly one `Admin` of type `User` | Key-person risk; prefer a security **Group**. |
| **Subdomain listed as ownerless** | `IsSubdomain == true` | ⚠️ **Expected, not a finding.** Subdomains have no admins of their own and inherit the parent's — check the parent instead. |

> **Report ownership gaps next to assignment gaps.** "897 workspaces unassigned" and "the 2 domains that hold all 139 assigned workspaces have no owner" are the same story: the domain structure exists but nobody drives it.

---

## Check Domain Metadata Completeness

Beyond ownership, a domain's own metadata is a health signal. The documented `Domain` object has exactly five fields — `id`, `displayName`, `description`, `parentDomainId`, `defaultLabelId` — and **null fields are omitted from responses**, so absence *is* the finding.

```powershell
$t = az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv
$h = @{ Authorization = "Bearer $t" }
$domains = (Invoke-RestMethod -Headers $h `
  -Uri "https://api.fabric.microsoft.com/v1/admin/domains?preview=false").domains

$domains | ForEach-Object {
  [pscustomobject]@{
    Domain        = $_.displayName
    HasDescription= [bool]$_.description
    HasDefaultLabel = [bool]$_.defaultLabelId   # absent => no default sensitivity label
    IsSubdomain   = [bool]$_.parentDomainId
  }
} | Format-Table -AutoSize
```

| Gap | Test | Pillar |
|---|---|---|
| Domain has no description | `description` absent | Health / discoverability |
| Domain has no default sensitivity label | `defaultLabelId` absent | **Protect** — the highest-leverage labeling fix; see the remediate skill. Note it only labels *new* and *touched-unlabeled* items, so pair it with bulk relabeling for the backlog. |

When reporting these:

- **Missing descriptions** — explain that domain purpose is harder to understand and govern consistently when the domain is unlabeled in human terms.
- **Description coverage is complete** — state that this is a **clean finding** and that no remediation is needed.
- **Missing default sensitivity labels** — explain that new items and touched unlabeled items will not inherit a baseline label, which allows the unlabeled backlog to keep growing.

> ⚠️ **Domain image (branding) cannot be audited.** Fabric domains support an image that themes the OneLake catalog when the domain is selected, and domain admins can set it — but **no branding, image, icon, colour, or theme field is exposed on any domain API** (verified against both the documented `Domain` schema and live responses). If the user asks whether domains have images set, say plainly that it is **portal-only** and point them to the Admin portal → Domains → domain settings. Do **not** report "all domains have branding" or treat its absence as verified — you cannot see it either way.

> ⚠️ **Default domain configuration cannot be audited either.** A domain can be designated the *default* for named users/groups, which auto-assigns their new and unassigned workspaces **and implicitly makes them domain contributors**. No API reads or writes this list. Two consequences you must respect when reporting:
> - When a workspace's domain membership looks unexplained, offer a default domain as the **likely** cause and point to the portal. Never assert that no default domain is configured.
> - Because default domains grant contributor rights implicitly, `roleAssignments` output is a **lower bound** on who can act on a domain — say so when reporting ownership.

---
