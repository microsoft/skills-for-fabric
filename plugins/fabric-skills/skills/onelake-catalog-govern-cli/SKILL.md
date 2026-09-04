---
name: onelake-catalog-govern-cli
description: "Governs Microsoft Fabric OneLake catalog health, protection, and trust through Fabric Admin, Core, and Power BI REST APIs. Use for tenant or owner-scoped audits and guarded remediation of domains, workspace assignment, capacity, labels, tags, descriptions, refresh, and item identity. Catalog item discovery belongs to search-consumption-cli."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: onelake-catalog-govern-cli` (`az rest`: `--headers "x-ms-fabric-skill=onelake-catalog-govern-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

# OneLake Catalog Govern — CLI (mode dispatcher)

One skill for the whole OneLake Catalog **Govern** family. The governance persona detail lives in four **mode references** loaded on demand. This top-level file exists to do three things and nothing else:

1. **Pick the mode** (the table below).
2. **Surface the safety boundary and the irreversible-write gates** so they are
   never diluted inside a large reference (see [Irreversible operations](#step-2--irreversible-operations--must-do-gates-read-before-any-write)).
3. **Load exactly one mode reference** and follow it.

## Must/Prefer/Avoid

### MUST DO

- Start with the audit cell for the caller's permission tier before any remediation.
- Apply the operation-specific confirmation gate in Step 2 before every destructive, irreversible, or broad write.
- Use the exact Fabric Admin, Core, Power BI, or Graph API surface documented for the selected procedure; do not treat a `401` or `403` as permission to bypass RBAC.
- State scope, exclusions, pagination completeness, and freshness caveats with every governance statistic.

### PREFER

- Use least-privileged Core or Power BI APIs for data-owner actions instead of requiring tenant-admin rights.
- Report findings as evidence, consequence, recommended action, priority, and effort rather than returning an inventory dump.
- Sequence ownership and access-scope fixes before bulk assignment or labeling.

### AVOID

- Do not mutate a tenant from an audit mode.
- Do not invent write APIs for endorsement, DLP policy, admin item deletion, or third-party item-identity assignment.
- Do not report asynchronous `202` responses as successful completion.

## Step 1 — Pick the mode

**Two axes → a 2×2 grid.** Tier (which API surface you can reach) × action (audit vs. remediate). Each cell covers all three Govern pillars (health / protect / trust).

|  | **Audit** (read-only) | **Remediate** (write) |
|---|---|---|
| **Fabric Admin** — `/v1/admin/*`, **Fabric tenant admin only** | `admin-audit` | `admin-remediate` |
| **Data owner / Operational admin** — Core API + workspace/domain/capacity admins, no tenant admin | `dataowner-audit` | `dataowner-remediate` |

| Mode | Load this reference | Persona / permission tier | Scope | Reads | Writes |
|---|---|---|---|---|---|
| **admin-audit** | [references/admin-audit.md](references/admin-audit.md) | **Fabric tenant admin** (`/v1/admin/*`) | Whole tenant | ✅ | ❌ |
| **admin-remediate** | [references/admin-remediate.md](references/admin-remediate.md) | **Fabric tenant admin only** — every `/v1/admin/*` write requires the Fabric administrator role; **domain & capacity admins do NOT qualify** | Whole tenant | ✅ | ✅ |
| **dataowner-audit** | [references/dataowner-audit.md](references/dataowner-audit.md) | **Non-admin** workspace or domain owner (Core API only) | Workspaces the caller administers (widen to accessible on request) | ✅ | ❌ |
| **dataowner-remediate** | [references/dataowner-remediate.md](references/dataowner-remediate.md) | **Data owner who is also a domain / workspace / capacity admin** — Core & Power BI API writes, **no tenant admin** | Objects the caller has the role on | ✅ | ✅ (self-service) |

### Routing rules

- **Start with an audit mode.** Never remediate before establishing the current state. Audit → remediate within the **same tier** unless the caller's rights change.
- **Choose the tier by the API surface the caller can reach**, not by job title: a **Fabric tenant admin** who needs `/v1/admin/*` → the `admin-*` cell; a data owner acting through workspace/domain/capacity roles → the `dataowner-*` cell.
- **"Fix / assign / apply / create / delete"** → a **remediate** cell. Tenant-wide writes (create/delete domain, bulk domain assignment, domain roles, bulk labels, certification) → `admin-remediate`. Single-workspace `assignToDomain` or `assignToCapacity`, applying tags, setting descriptions, refresh, and item identity → `dataowner-remediate` (these need object-scoped roles, not tenant admin).
- The read/write split is a **safety boundary**: an audit mode must not mutate a tenant even if a prompt asks it to. If you are in an audit mode and the user asks for a write, switch to the matching remediate mode explicitly — do not improvise a write.

> **Tier = API surface, not role title.** The `admin-*` modes call `/v1/admin/*` and require the **Fabric tenant administrator** role (Fabric admin / Power Platform admin / M365 global admin) — **domain, capacity and workspace admins do NOT qualify**, even for their own domain. The `dataowner-*` modes use the Core/Power BI APIs scoped to roles the caller already holds on specific objects. A domain/WS/capacity admin who is *not* a Fabric tenant admin therefore lives entirely in the `dataowner-*` cells; they cross into `admin-*` **only if they are separately granted the Fabric tenant admin role**. Roles are **scope branches inside** a mode; only a different **API surface** justifies a separate mode.

> ⚠️ **Known Fabric gap — scoped governance has no non-admin API.** A **domain admin** or **workspace admin** who is *not* a Fabric tenant admin currently has **no API path** to their scoped governance posture: `/v1/admin/*` rejects them (it needs the tenant Fabric admin role — see the [Assign Domain Workspaces](https://learn.microsoft.com/en-us/rest/api/fabric/admin/domains/assign-domain-workspaces-by-ids#permissions) permission note), and the Core API has **no** endpoint that lists the workspaces in a domain or returns a domain's governance state. `dataowner-audit` can only report on workspaces the caller can directly access — not "my whole domain." If a domain/WS admin asks for their scoped govern details, **state this limitation up front** and do not route them into an `admin-*` mode that will 401/403.

## Step 2 — Irreversible operations — MUST-DO gates (read before any write)

> ⚠️ **Why this lives here and not only in the mode reference.** These are terminal,
> hard-to-undo acts. When such an instruction sits as one line among dozens inside a
> large reference file, it gets read but silently skipped. It is repeated here, in the
> auto-loaded dispatcher body, so the gate fires **before** the write — not after.
> Full procedures remain in the remediate mode references ([admin-remediate.md](references/admin-remediate.md), [dataowner-remediate.md](references/dataowner-remediate.md)); this is the checklist, not a substitute.

Before executing any of these in **either** remediate mode, the gate MUST pass. The **Mode** column shows which cell owns the operation:

| Irreversible / terminal act | Mode | Gate that MUST fire first |
|---|---|---|
| **Delete a domain** (`DELETE /v1/admin/domains/{id}`) | admin | Check for subdomains (`parentDomainId`) **and** assigned-workspace counts for the domain and every subdomain. If any workspaces would be orphaned, STOP and get explicit user confirmation naming the affected domains/workspaces. The REST API has **no** cascade-block — the check is yours. See [domain-crud.md § Deleting a Domain](references/admin-remediate/domain-crud.md#deleting-a-domain--the-portal-vs-api-safety-gap). |
| **Delete a tag** definition | admin | Report how many items carry it first — deletion detaches it everywhere with **no undo**. |
| **Bulk-assign workspaces to a domain** | admin | Check each target's current `domainId` and warn before **silently overriding** an existing assignment. Dry-run the target list first. |
| **Remove a principal from a domain role** | admin | Confirm it will not leave the domain **ownerless**; name the principal being removed. |
| **Bulk sensitivity-label change** | admin | Dry-run: show the exact affected item list and before/after label, get confirmation. **No service principal / managed identity** — the call will fail. |
| **Write a tenant setting** (e.g. enable certification) | admin | Read the current value and show it, then the proposed value — tenant-wide blast radius. |
| **Assign / unassign one workspace to a domain** | dataowner | A move is a **reassignment** — confirm the current `domainId` and name the domain it is leaving. Needs domain-contributor **and** workspace-Admin; say which is missing on failure. |
| **Reassign item ownership** (item identity, preview) | dataowner | Assigns to the **caller** only; needs Write on the item and its children. Confirm the intended identity. |
| **Assign a workspace to a capacity** | dataowner | Needs workspace Admin plus capacity Contributor/Admin. Async `202` — do **not** report success from the 202 alone; poll to a terminal state. |

> **Do not promise a remediation that has no write API.** Endorsement, DLP policies, and item *deletion* by a tenant admin have **no** write route. For those, produce a contact list of who *can* act — see [references/admin-remediate/no-write-api-escalation.md § Route a Finding to Someone Who Can Fix It](references/admin-remediate/no-write-api-escalation.md#route-a-finding-to-someone-who-can-fix-it-escalation-lists).

## Step 3 — Load the reference and proceed

Load only the one mode reference matching Step 1 and follow it end to end. Shared
background and every leaf procedure are indexed here so each file is one hop from
this dispatcher. References are leaves: after loading one, return to this index
when another procedure is needed.

### Shared governance references

- [Govern pillars](references/govern-pillars.md) — the three pillars, what "good" looks like, and reporting conventions
- [Governance data sources](references/govern-data-sources.md) — verified API field coverage, product blind spots, and reporting conventions
- [Governance roles](references/govern-roles.md) — permission tiers, domain/workspace roles, and insight refresh lag
- [Catalog concepts](references/catalog-concepts.md) — the entity model and API-backed versus conceptual terms
- `../../common/COMMON-CORE.md` — repository-level Fabric REST patterns, auth, and pagination
- `../../common/COMMON-CLI.md` — repository-level CLI implementation (`az rest`, pagination, auth recipes)

### Mode dispatchers

- [Admin audit](references/admin-audit.md) — tenant-wide read-only governance assessment
- [Admin audit scope](references/admin-audit-scope.md) — governable denominator, exclusions, and known blind spots
- [Admin audit assessment](references/admin-audit-assessment.md) — end-to-end evaluative workflow, prioritization, and deliverable contract
- [Admin remediate](references/admin-remediate.md) — tenant-wide guarded writes through Admin APIs
- [Data-owner audit](references/dataowner-audit.md) — caller-scoped read-only checks through Core APIs
- [Data-owner remediate](references/dataowner-remediate.md) — least-privileged writes through Core and Power BI APIs

### Admin audit procedures

- [Domain health](references/admin-audit/health-domains.md) — assignment, ownership, contributor scope, and metadata
- [Workspace health](references/admin-audit/health-workspaces.md) — empty/inactive workspaces and admin bus factor
- [Capacity health](references/admin-audit/health-capacity.md) — capacity state, ownership, and domain alignment
- [Item inventory](references/admin-audit/item-inventory.md) — Admin versus scanner inventory and field coverage
- [Item health](references/admin-audit/health-item.md) — ownership, staleness, and refresh state
- [Protect coverage](references/admin-audit/protect-labels-dlp.md) — sensitivity labels and DLP visibility
- [Trust curation](references/admin-audit/trust-curation.md) — descriptions, endorsement, and tag coverage

### Admin remediation procedures

- [Domain lifecycle](references/admin-remediate/domain-crud.md) — create, update, and safely delete domains
- [Workspace assignment](references/admin-remediate/domain-assign-workspaces.md) — choose and dry-run bulk assignment methods
- [Domain roles](references/admin-remediate/domain-roles.md) — assign admins and contributors
- [Tags](references/admin-remediate/tags.md) — manage tenant tag definitions
- [Item sensitivity labels](references/admin-remediate/item-sensitivity-label.md) — guarded bulk label changes
- [Domain default labels](references/admin-remediate/domain-default-label.md) — prevent new unlabeled backlog
- [Trust remediation](references/admin-remediate/trust-curate.md) — certification enablement and delegated actions
- [No-write escalation](references/admin-remediate/no-write-api-escalation.md) — identify missing APIs and named owners who can act

### Data-owner procedures

- [Data-owner workspace health](references/dataowner-audit/health-workspaces.md) — empty and inactive workspace checks within caller scope

## Examples

```text
Audit our tenant's OneLake catalog governance posture and prioritize the findings.
```

```text
Which workspaces I administer are not assigned to a domain?
```

```text
Show a dry run for assigning these workspaces to the Finance domain, including current assignments.
```

```text
Find unlabeled items tenant-wide and explain which remediations require a tenant admin versus a data owner.
```
