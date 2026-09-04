# OneLake Catalog Product and Entity Model


## Contents

- [What the OneLake Catalog Is](#what-the-onelake-catalog-is)
- [Entity Model](#entity-model)
- [Key Relationship Semantics](#key-relationship-semantics)
- [Programmatic Entry Points](#programmatic-entry-points)

What the OneLake catalog *is*, how its entities relate, and — critically — **which concepts are API-backed Fabric entities versus organizational vocabulary**. Read this before designing any governance automation, so you don't generate calls against concepts that don't exist.

Primary sources: [OneLake catalog overview](https://learn.microsoft.com/en-us/fabric/governance/onelake-catalog-overview), [Domains](https://learn.microsoft.com/en-us/fabric/governance/domains), [Endorsement](https://learn.microsoft.com/en-us/fabric/governance/endorsement-overview).

---

## What the OneLake Catalog Is

A centralized place in Fabric to **find, explore, use, and govern** data. Accessed from the Fabric navigation pane, and embedded in **Microsoft Teams, Microsoft Excel, and Microsoft Copilot Studio**. Catalog metadata is also reachable programmatically via the [Catalog Search REST API](https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search).

### Three tabs

| Tab | Purpose | Related skill |
|---|---|---|
| **Explore** | Browse/filter items with an in-context details view; scope by domain; request access to discoverable content | `search-consumption-cli` |
| **Govern** | Governance posture insights + recommended actions, scoped to your responsibility (tenant for admins, *My items* for data owners) | `onelake-catalog-govern-cli` |
| **Secure** | Unified view of **workspace roles and OneLake security roles** across items; audit permissions, view user access, create/edit/delete security roles | — |

---

## Entity Model

The mental model people usually sketch looks like this:

```
Domain
├─ owns      Data Products
├─ has       Workspaces
├─ governed by  Policy
├─ consumed by  Teams
└─ has       Steward
```

That's a fine *conceptual* model, but only some of those edges correspond to real Fabric entities you can query. Here is the same model annotated for reality:

```
Domain  [REAL — /v1/admin/domains, has id, displayName, parentDomainId]
│
├─ has Subdomain          [REAL — a Domain with parentDomainId set]
│                          └─ NOTE: inherits parent's admins; has no admins of its own
│
├─ has Workspace          [REAL — workspace.domainId; assign/unassign APIs exist]
│   └─ contains Item      [REAL — /v1/admin/items; lakehouses, semantic models, reports, ...]
│       ├─ has Sensitivity Label   [REAL — protection metadata]
│       ├─ has Endorsement         [REAL — Promoted | Certified | Master data]
│       ├─ has Description         [REAL — curation metadata]
│       └─ has Refresh state       [REAL — freshness metadata]
│
├─ has Tag                [REAL — workspace.tags[], each with id + displayName]
│
├─ runs on Capacity       [REAL — workspace.capacityId; Power BI admin capacity inventory]
│
├─ governed by Delegated Settings   [REAL — but a narrow, specific list:
│                                    default sensitivity label + certification settings]
│
├─ has Domain admin / Domain contributor  [REAL roles]
│
├─ owns "Data Products"   [CONCEPTUAL ONLY — no such item type or API]
├─ has "Steward"          [CONCEPTUAL ONLY — no such role]
└─ consumed by "Teams"    [CONCEPTUAL — Fabric models users/security groups and
                           workspace roles, not business "teams" as an entity]
```

### The distinction matters

| Concept | Status | What to do with it |
|---|---|---|
| Domain, Subdomain | **API entity** | Query/modify directly |
| Workspace, Item, Capacity, Tag | **API entity** | Query/modify directly |
| Sensitivity label, Endorsement, Description, Refresh state | **API-visible metadata on items** | Assess for the Protect and Trust pillars |
| Delegated settings | **Real but narrow** — default sensitivity label, certification settings only | Don't assume arbitrary tenant settings are delegable |
| **Data product** | **Conceptual** | Interpret as "a set of endorsed/certified items in a domain's workspaces". Never call a "data product API" |
| **Steward** | **Conceptual** | Map to Domain admin, Domain contributor, or item owner — ask the user which they mean |
| **Team** | **Conceptual** | Map to users/security groups + workspace roles |

> **Rule for agents**: if a user asks about data products or stewards, do not correct them pedantically — translate. Say what you're mapping it to ("I'll treat 'data products' as certified items within the domain's workspaces"), then proceed with real entities.

---

## Key Relationship Semantics

### Domain ↔ Workspace
- One workspace belongs to **at most one** domain (`domainId` is singular).
- Assigning a workspace that's already in another domain **silently overrides** the prior assignment, unless the tenant setting *"Allow tenant and domain admins to override workspace assignments (preview)"* is disabled.
- **Assignment is inherited downward**: when a workspace is assigned to a domain, **all items in that workspace** receive the domain attribute in their metadata.
- **Deleting a domain does not delete workspaces** — they become unassigned.

### Domain ↔ Subdomain
- A subdomain is just a Domain with `parentDomainId` set.
- **Subdomains have no independent admins** — parent's domain admins govern them.
- Subdomains currently support **general settings only** (name/description) — no image, no separate delegated settings.

### Domain ↔ Governance scope
- Domain is **not a security boundary**. It does not affect item visibility or access.
- **All tenant users can see all domains**, regardless of their domain roles.
- Domain *is* a scope for: OneLake catalog filtering, Govern tab insight scoping, and the narrow set of delegated settings.

### Item ↔ Trust signals
- Endorsement authority is tiered: **Promoted** = any writer; **Certified** / **Master data** = only Fabric-admin-designated users, and both features must be enabled first.
- **Master data** applies only to data-bearing items (lakehouses, semantic models).
- Power BI **dashboards** cannot be promoted or certified.

---

## Programmatic Entry Points

| Need | Endpoint | Skill |
|---|---|---|
| Find items across workspaces | `POST /v1/catalog/search` | `search-consumption-cli` |
| Tenant-wide workspace/domain/capacity inventory | `GET /v1/admin/workspaces`, `/v1/admin/domains`, `GET /v1.0/myorg/admin/capacities` | `onelake-catalog-govern-cli` |
| Create/modify/delete domains, assign workspaces | `POST/PATCH/DELETE /v1/admin/domains/...` | `onelake-catalog-govern-cli` |
| A non-admin checking their own workspaces | `GET /v1/domains`, `GET /v1/workspaces/{id}` | `onelake-catalog-govern-cli` |

> **Catalog index lag**: newly created items can take **up to 24 hours** to appear in Catalog Search results. If an item is known to exist but isn't found, verify via `GET /v1/workspaces/{id}/items` instead of concluding it's missing.
