# Governance Role Model for OneLake Catalog and Fabric


## Contents

- [The Two Governance Personas](#the-two-governance-personas)
- [Role Reference](#role-reference)
- [What Domain Assignment Does *Not* Do](#what-domain-assignment-does-not-do)
- [Default Domains (automatic assignment behavior)](#default-domains-automatic-assignment-behavior)
- [Role → Which Skill To Use](#role-which-skill-to-use)
- [Terminology Warning: "Steward" and "Data Product"](#terminology-warning-steward-and-data-product)
- [Domain Role Assignments (the API-backed answer to "who owns this domain?")](#domain-role-assignments-the-api-backed-answer-to-who-owns-this-domain)

Who is responsible for what in Fabric governance, what each role can actually *do*, and what each persona sees in the OneLake catalog's **Govern** tab. Read this before assuming a user can perform a governance action — most `403`s and "I can't see that insight" confusions trace back to this model.

Primary sources: [Domains](https://learn.microsoft.com/en-us/fabric/governance/domains), [Govern tab](https://learn.microsoft.com/en-us/fabric/governance/onelake-catalog-govern), [Workspace roles](https://learn.microsoft.com/en-us/fabric/fundamentals/roles-workspaces).

---

## The Two Governance Personas

Fabric's governance surface is built around **two personas**, and the OneLake catalog Govern tab renders differently for each:

| Persona | Scope of responsibility | Govern tab default view | Data source for insights | Refresh cadence |
|---|---|---|---|---|
| **Fabric admin** | The entire tenant — every item, workspace, capacity, and domain | **All Data in Fabric** (can switch to *My items*) | Admin Monitoring Storage (auto-created in the Admin Monitoring workspace) | **Once per day** — insights can lag reality by up to 24h |
| **Data owner** | Only the items *they own* (the *My items* filter on the Explore tab) | **My items** | The user's own OneLake catalog governance report, in *My workspace* | On every Govern tab open (plus a manual Refresh button) |

> **Critical implication for agents**: a Fabric admin asking "why doesn't my change show up?" is usually hitting the **daily refresh lag**, not a bug. A data owner has no such lag. Never tell an admin their governance data is real-time.

**A single human is often both.** A "data owner" in the business sense is frequently also a Domain admin and/or a Workspace admin. These are separate, independently-granted roles — do not infer one from another. Always establish which specific role the user holds for the specific object they're asking about.

---

## Role Reference

### Tenant-level

| Role | Grants |
|---|---|
| **Fabric admin** (or higher) | Create/edit/**delete** domains, specify domain admins and contributors, assign any workspace to any domain, see all domains in the admin portal, full tenant-wide Govern insights. Required for all `/v1/admin/*` REST APIs. |

### Domain-level

| Role | Grants | Explicitly **cannot** |
|---|---|---|
| **Domain admin** | Update domain description, define/update domain contributors, assign workspaces to the domain, set domain image, override delegated tenant settings for that domain | **Delete** the domain, **rename** it, or add/remove other domain admins |
| **Domain contributor** | Assign *the workspaces they are workspace Admin of* to the domain, or change that assignment | Access the **Domains** tab in the admin portal at all |

> **Subdomains have no admins of their own.** A subdomain's admins are always its parent domain's admins. Never attempt to grant subdomain-scoped admin rights — direct the user to the parent domain.

> **Domain contributor requires workspace Admin.** Being a domain contributor is useless on its own: the user must *also* hold the Admin role on a given workspace to assign that workspace to the domain.

### Workspace-level

Standard Fabric workspace roles — **Admin**, **Member**, **Contributor**, **Viewer**. Relevant to governance because:
- Only workspace **Admin** can assign that workspace to a domain (in combination with domain contributor rights).
- Domain assignment is done from the workspace's own settings by contributors, not from the admin portal.

---

## What Domain Assignment Does *Not* Do

> Domain assignment **does not affect item visibility, discoverability, or access permissions.** Access depends on workspace role and item permissions only.

Furthermore, **all users in a tenant can see all domains defined in the tenant**, regardless of their domain roles — e.g., a user with no relationship to "Finance" still sees "Finance" in the OneLake catalog domain filter. Do not treat domain membership as a security boundary; it is an organizational/governance grouping that drives filtering, delegated settings, and governance reporting.

---

## Default Domains (automatic assignment behavior)

A domain can be designated the **default domain** for specified users/security groups. When set:

1. Fabric scans existing workspaces. For each workspace whose **admin** is a specified user or group member:
   - If the workspace **already has a domain**, that assignment is **preserved** — the default domain does *not* override it.
   - If the workspace is **unassigned**, it is assigned to the default domain.
2. Thereafter, **new workspaces** created by those users are auto-assigned to the default domain.
3. Those users generally become **domain contributors** of the workspaces assigned this way.

> This is a common explanation for "workspaces I didn't assign are showing up in a domain" — check whether a default domain is configured before treating it as a governance anomaly.

> ⚠️ **Default domain configuration is NOT exposed by any API.** The `Domain` object contains only `id`, `displayName`, `description`, `parentDomainId`, `defaultLabelId`, and `UpdateDomainRequest` accepts only `displayName`, `description`, `defaultLabelId`. There is no endpoint to read or set the default-domain user/group list (verified against the schema and by probing; all candidate paths return 404).
>
> **Consequences for an agent:**
> - You **cannot** confirm or rule out a default domain as the cause of an unexpected assignment. Offer it as the *likely* explanation and direct the user to Admin portal → Domains → domain settings; never state that no default domain is configured.
> - Default domains **grant domain contributor implicitly**. A `roleAssignments` read may therefore *understate* who can act on a domain. Treat role-assignment output as a lower bound, not a complete picture.
> - It is an invisible, ongoing mutation: workspaces keep getting auto-assigned after the fact. An assignment audit is a point-in-time snapshot, not a stable state.

---

## Role → Which Skill To Use

| Caller's role | Use this skill |
|---|---|
| Fabric admin, wants tenant-wide read-only diagnostics | `onelake-catalog-govern-cli` |
| Fabric admin or Domain admin, wants to create/modify/delete domains or assignments | `onelake-catalog-govern-cli` |
| Data owner / workspace admin with no tenant admin rights | `onelake-catalog-govern-cli` |

---

## Terminology Warning: "Steward" and "Data Product"

Third-party blogs commonly describe Fabric governance using **"data steward"** and **"data product"** as if they were first-class Fabric entities. **They are not**, as of this writing:

- There is **no "Steward" role** in Fabric. The official roles are those listed above. "Steward" is an *organizational* concept that usually maps onto Domain admin, Domain contributor, or item owner.
- There is **no "Data Product" item type or API**. A "data product" is an *organizational* concept typically realized as a set of endorsed/certified items within a domain's workspaces.

Use these words when talking with the user about intent, but **never generate API calls or claim capabilities based on them**. See `catalog-concepts.md` for which concepts are API-backed and which are conceptual.

> **However — "who stewards this domain?" *is* an answerable, API-backed question.** Translate it to the domain's **Admin role assignment**, and treat a missing one as a genuine governance gap. Don't dismiss the question just because "steward" isn't a Fabric role.

---

## Domain Role Assignments (the API-backed answer to "who owns this domain?")

```
GET  /v1/admin/domains/{domainId}/roleAssignments
POST /v1/admin/domains/{domainId}/roleAssignments/bulkAssign
POST /v1/admin/domains/{domainId}/roleAssignments/bulkUnassign
```

- Caller must be a **Fabric administrator** (`Tenant.ReadWrite.All`); 25 req/min. Service principals and managed identities **are** supported.
- `GET` returns `value[]` of `{ role, principal }` where `role` is `Admin` or `Contributor`.
- `principal.type` is one of `User`, `Group`, `ServicePrincipal`, `ServicePrincipalProfile`, or **`EntireTenant`**.
- Write body uses `type` (`"Admins"` or `"Contributors"` — **plural**) plus a `principals[]` array.
- Error `UnsupportedPrincipalTypeForDomainAdminAssignment` means the principal type is not valid for the **Admin** role (notably, `EntireTenant` is contributor-only).

### How to read the result

| Observation | Interpretation |
|---|---|
| No `Admin` entry | **Ownerless domain.** Nobody is accountable; only tenant admins can manage it. A real governance gap. |
| `Contributor` = `EntireTenant` | Contributor scope is open to the **whole tenant** — any user can assign workspaces into this domain. Often the default; flag it, especially on populated domains. |
| Exactly one `Admin` of type `User` | Key-person risk. Prefer a security **Group** so ownership survives staff changes. |
| Subdomain with no `Admin` | **Expected, not a finding.** Subdomains have no admins of their own and inherit the parent's — evaluate the parent domain instead. |

> **Domain contributor is not enough on its own.** A domain contributor still needs **workspace Admin** on a workspace to assign it into the domain. "I'm a contributor but assignment fails" is almost always a missing workspace role, not a domain-role problem.
