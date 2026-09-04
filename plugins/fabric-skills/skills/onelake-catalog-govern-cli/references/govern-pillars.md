# The Three OneLake Catalog Governance Pillars


## Contents

- [Pillar Map](#pillar-map)
- [Pillar 1 — Manage Your Data Estate (Health)](#pillar-1-manage-your-data-estate-health)
- [Pillar 2 — Protect, Secure & Comply (Protect)](#pillar-2-protect-secure-comply-protect)
- [Pillar 3 — Discover, Trust & Reuse (Trust / Curate)](#pillar-3-discover-trust-reuse-trust-curate)

What a Fabric admin or data owner is actually worried about, organized by the three pillars the OneLake catalog **Govern** tab uses. Each pillar section states **what "good" looks like**, **what the common gaps are**, and **how to assess it programmatically**.

Primary source: [Govern your Fabric data with the OneLake catalog](https://learn.microsoft.com/en-us/fabric/governance/onelake-catalog-govern).

---

## Pillar Map

Microsoft's Govern tab "View more" report organizes insights into three tabs. These map onto the informal admin vocabulary of **health / protect / trust**:

| Official pillar name | Informal name | Core question |
|---|---|---|
| **Manage your data estate** | Health | *Do I know what I have, and is it organized, resourced, and current?* |
| **Protect, secure & comply** | Protect | *Is sensitive data labeled, and are policies being enforced and not violated?* |
| **Discover, trust, and reuse** | Trust / Curate | *Can people find data, and can they trust it's described, endorsed, and tagged?* |

Use these three buckets when reporting a governance assessment — it matches what the user sees in the product UI.

> **One deliberate divergence from the product tabs.** The Govern tab shows **data freshness** under *Discover, trust & reuse*, but this skill audits freshness under **Health** — "is this item actively refreshing?" is a data-estate/currency question. Tags are **split**: tag *hygiene* (sprawl, duplication) is a Health concern, while tag *coverage for discovery* is a Trust concern. Everything else follows the product's three tabs.

---

## Pillar 1 — Manage Your Data Estate (Health)

**Contains** (per the Govern tab): inventory overview, capacities & domains information, and feature usage across the tenant.

### What "good" looks like
- Every active workspace is assigned to a domain (or deliberately exempted).
- No empty domains left over from abandoned governance initiatives.
- Domains reflect current org structure; subdomains used for genuine subdivision, not clutter.
- Workspaces sit on **active, non-suspended** capacities, and capacity assignment aligns with the owning domain. (Whether a capacity is *overloaded* is **not knowable via API** — see below.)
- Every workspace has more than one admin, and at least one **human** admin.
- Capacities have named admins and are not left empty or mid-deletion.
- Tags applied consistently, not ad-hoc/duplicated.
- Data items refresh on schedule; few stale or failed refreshes.
- No large population of orphaned or abandoned items/workspaces.

### Common gaps to look for
| Gap | How to detect |
|---|---|
| Workspaces with no domain | Active workspaces where `domainId` is absent/null |
| Empty domains | Domains returning zero workspaces from `/v1/admin/domains/{id}/workspaces` |
| Domain/capacity misalignment | Workspace `capacityId` not among the capacities associated with its domain |
| Deleted-state clutter | Deleted, personal and admin-monitoring workspaces inflating inventory counts; items in deleted workspaces still reported `Active` |
| Tag sprawl | Near-duplicate tag `displayName`s across workspaces |
| **Empty workspaces** | Active workspaces with zero items in `/v1/admin/items`. ⚠️ **Empty ≠ unused** — verify against activity events before treating as abandoned |
| **Inactive workspaces** | No events in `/v1.0/myorg/admin/activityevents`. One day per call, **~28-day retention**; a short window mislabels most of a tenant |
| **Single-admin workspaces** | Exactly one `Admin` role holder — the dominant ownership risk. ⚠️ Zero-admin workspaces **do not occur** |
| **No human admin** | All admins are service principals or groups; the true analogue of "ownerless" |
| **Suspended / deleting capacity holding workspaces** | `state != 'Active'` on `/v1.0/myorg/admin/capacities` with workspaces assigned — content is inaccessible now |
| **Ownerless or single-admin capacity** | Empty or one-element `admins[]` |
| **Unresolvable capacity** | Workspace `capacityId` absent from the capacity list — bucket explicitly, never drop |
| **Stale items** | `lastUpdatedDate` older than an agreed threshold. Records **modification, not use** |
| **Stale / failing refreshes** | Semantic model whose latest refresh `status != "Completed"` or whose `endTime` is past the expected cadence (Power BI refresh history API). ⚠️ `lastUpdatedDate` does **not** capture this — freshness is audited under Health in this skill, not Trust |
| **Items with an unresolvable creator** | `creatorPrincipal` that Microsoft Graph cannot resolve. ⚠️ See the creator-type warning below before calling anyone "departed" |

### Key APIs
- `GET /v1/admin/workspaces?type=Workspace&state=Active` — returns `id`, `name`, `state`, `capacityId`, `domainId`, `tags` (**verified**). `state=Active` is a **server-side filter** and should be the default.
- `GET /v1/admin/domains`, `GET /v1/admin/domains/{id}/workspaces` (**verified** — domain-side lists are already Active-only)
- `GET /v1.0/myorg/admin/capacities` — Power BI admin API; returns capacity state and administrators
- `GET /v1/admin/items` — tenant-wide item inventory
- `GET /v1.0/myorg/admin/capacities/refreshables?$expand=capacity,group` — refresh ownership (`configuredBy`) and last-refresh status; or the per-model Power BI refresh history API (`/datasets/{id}/refreshes`) for freshness. The scanner API does **not** return refresh state

> **Always scope to `type=Workspace&state=Active` before computing health percentages.** Both filters are server-side and verified. In a test tenant only **1,062 of 2,242 workspaces (47%)** were governable — unfiltered percentages were roughly 2× wrong.
>
> Verified traps:
> - **Only `Workspace`-type workspaces can carry a `domainId`.** `Personal` (My workspace) and `AdminWorkspace` (admin monitoring) are structurally incapable of domain assignment, so counting them produces permanently unfixable "unassigned" gaps.
> - **Deleted workspaces retain `domainId`**, but domain-side endpoints omit them. Grouping an unfiltered list by `domainId` inflates domain sizes and manufactures false View A / View B differences.
> - **Items in deleted workspaces are still returned as `state: Active` by `/v1/admin/items`** — 461 of 14,912 in the verified tenant. Filtering items by their *own* state does **not** exclude them. You must join `item.workspaceId` against the governable-workspace list.
> - **Personal-workspace items are a Protect exception.** Exclude them from domain and endorsement metrics, but report their label coverage separately — they hold real data and dropping them hides exposure.

---

## Pillar 2 — Protect, Secure & Comply (Protect)

**Contains** (per the Govern tab): sensitivity label coverage and data loss prevention (DLP) policies activated and scanned across workspaces. This absorbs insights previously found in the Microsoft Purview Hub.

### What the product surfaces
- **Sensitivity labels selector** — most frequently used labels and the **percentage of unlabeled items**. Drillable by item type and by user to find labeling gaps and policy misalignment. Label distribution can be analyzed by domain or workspace.
- **DLP selector** — which workspaces/data items were evaluated by DLP policies, used to **identify policy violations** and act (apply a more restrictive label, remove sensitive information). Breaks down scanned items by type/location and shows **last evaluation time**, so you can judge scan freshness and trigger a new scan.

### What "good" looks like
- Low percentage of unlabeled items, especially among data-bearing items.
- Sensitivity label coverage is consistent *within* a domain (a domain-level default sensitivity label can be delegated — see below).
- DLP policies actually evaluated recently (recent "last evaluation time"), not stale.
- Zero or actively-triaged policy violations.

### Common gaps to look for
| Gap | Why it matters |
|---|---|
| High % unlabeled items | Sensitive data unprotected and invisible to DLP enforcement |
| Labeling uneven by user | Indicates a team/individual not following policy — drill by user |
| Stale DLP last-evaluation time | Violations may exist but be undetected; trigger a rescan |
| Open policy violations | Direct compliance exposure — remediate via more restrictive label or data removal |
| Domain default sensitivity label unset | Missed opportunity for automatic baseline protection |

### Delegated protection settings
Certain tenant-level settings can be **delegated to the domain level**, letting each business unit set its own rules:
- **Domain-level default sensitivity label** — the only delegated domain setting that is **fully API-backed**: read as `defaultLabelId` on the `Domain` object, write via `PATCH /v1/admin/domains/{id}?preview=false`. Applied when a **new** item is created and saved, or when an **existing unlabeled** item is updated and saved. It **never** retroactively labels dormant items, and never overrides a *manually* applied label. Requires the tenant setting *"Domain admins can set default sensitivity labels for their domains (preview)"*. Not supported with deployment pipelines or Git integration.
- **Certification settings** — see Pillar 3.

> **Reading `defaultLabelId` is a real gap check.** Null fields are omitted from API responses, so a domain with no `defaultLabelId` key has no default label configured — a concrete, checkable Protect-pillar finding.

> **Explain the consequence, not just the absence.** A missing domain default label means newly created items and existing unlabeled items that get edited will not inherit a baseline label, so the unlabeled backlog keeps regrowing even after one-time cleanup.

> **Access vs. protection**: domain assignment does **not** control who can see or access an item. Never present domain membership as a protection control — access is workspace roles + item permissions + OneLake security roles.

---

## Pillar 3 — Discover, Trust & Reuse (Trust / Curate)

**Contains** (per the Govern tab): data **freshness**, item **curation state** (description and endorsement coverage), and a content **sharing** view. ⚠️ **In this skill, freshness is audited under Pillar 1 Health** (see the divergence note in the Pillar Map). This pillar therefore covers **description, endorsement and tag coverage** plus sharing; freshness intersects it only as a cross-pillar combination (certified-but-stale).

### What "good" looks like
- High description coverage — items are self-explanatory to consumers.
- Meaningful endorsement coverage, with certification actually governed (not everything auto-certified).
- Content is tagged for classification-based discovery, not just findable by exact name.
- Sharing patterns are intentional, not accidental broad sharing.

### Endorsement model (the core "trust" signal)
Three badges, with **different authority requirements**:

| Badge | Meaning | Who can apply |
|---|---|---|
| **Promoted** | Creators consider it ready for sharing/reuse | **Any user with write permissions** on the item |
| **Certified** | An organization-authorized reviewer confirms it meets quality standards and is authoritative | **Only users specified by a Fabric admin** (any user may *request* it) |
| **Master data** | The authoritative single source of truth for core organizational data (e.g., product codes, customer lists) | **Only users specified by a Fabric admin**; applies only to **data-bearing items** (lakehouses, semantic models) |

Notes:
- All Fabric/Power BI items **except Power BI dashboards** can be promoted or certified.
- **Certification and master data must be enabled by a Fabric admin** before they can be used at all.
- **Certification enablement can be delegated to domain admins**, enabling a different reviewer set per domain — a good pattern for federated governance.

### Common gaps to look for
| Gap | Why it matters |
|---|---|
| Low description coverage | Consumers can't evaluate fitness for use; drives duplicate datasets |
| Low tag coverage | Content is hard to discover by classification; consumers fall back to name search or recreate datasets |
| Zero certified items | Either governance isn't enabled, or no reviewers are designated |
| Everything "Promoted", nothing "Certified" | Self-service endorsement without authoritative review — trust signal is diluted |
| Certified/endorsed item that is **stale** (cross-pillar Health×Trust) | Worst case: an authoritative item serving stale data. Freshness is detected under Health — prioritize the *intersection* with the endorsed set |
| Broad sharing of unendorsed, unlabeled items | Combines a trust gap with a protection gap |

> **Cross-pillar priority rule**: an item that is **endorsed AND stale** (freshness is a Health signal — see Pillar 1), or **broadly shared AND unlabeled**, is a higher-priority finding than either signal alone. Surface these combinations first.

---
