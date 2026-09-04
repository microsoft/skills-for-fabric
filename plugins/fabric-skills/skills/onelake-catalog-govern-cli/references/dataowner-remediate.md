<!-- MODE REFERENCE for onelake-catalog-govern-cli (mode: dataowner-remediate). Loaded on demand by the dispatcher SKILL.md. -->

# OneLake Catalog Govern — Data Owner / Operational Admin Remediate (Core-API write) mode


## Contents

- [Prerequisite Knowledge](#prerequisite-knowledge)
- [Permission model — read before any write](#permission-model-read-before-any-write)
- [Must/Prefer/Avoid](#mustpreferavoid)
- [Assign / Unassign One Workspace to a Domain (Core API, no tenant admin)](#assign-unassign-one-workspace-to-a-domain-core-api-no-tenant-admin)
- [Apply Tags to Items and Workspaces (workspace role)](#apply-tags-to-items-and-workspaces-workspace-role)
- [Fix Curation Gaps (Descriptions) (item Write, workspace Contributor)](#fix-curation-gaps-descriptions-item-write-workspace-contributor)
- [Trigger a Semantic Model Refresh (Power BI API, workspace member)](#trigger-a-semantic-model-refresh-power-bi-api-workspace-member)
- [Reassign Item Ownership (Item Identity, Preview) (item Write; assigns to caller)](#reassign-item-ownership-item-identity-preview-item-write-assigns-to-caller)
- [Assign a Workspace to a Capacity (workspace and capacity roles)](#assign-a-workspace-to-a-capacity-workspace-and-capacity-roles)
- [What a data owner still CANNOT do](#what-a-data-owner-still-cannot-do)

The **non-admin write path**. These are the governance fixes a **data owner who is also a
domain / workspace / capacity admin** can make **without a Fabric tenant admin role**, using the
**Core** and **Power BI** REST APIs (not `/v1/admin/*`). This is the 4th cell of the Govern grid:
`{data-owner tier} × {remediate}`.

For the tenant-wide, admin-API write path (create/delete domains, bulk domain assignment,
domain role assignment, bulk labeling, certification enablement), use the
**admin-remediate** mode instead: admin-remediate.md.
To find what needs fixing first, use an audit mode: dataowner-audit.md
(own workspaces) or admin-audit.md (tenant-wide).

## Prerequisite Knowledge

- `govern-roles.md` — **read first**: what a data owner / domain contributor / workspace admin can and cannot do
- `catalog-concepts.md` — entity model; which concepts are API-backed
- Repository `common/COMMON-CORE.md` — Fabric REST API patterns, auth
- Repository `common/COMMON-CLI.md` — CLI implementation (`az rest`, auth recipes)

## Permission model — read before any write

Every operation here is scoped by a **workspace or domain role the caller already holds**, not by
tenant admin. A `403` means the caller lacks the specific role on the specific object — it is a real
RBAC boundary, not a bug. Always name **which** of the required roles is missing rather than
reporting a generic "permission denied".

## Must/Prefer/Avoid

### MUST DO

- **Confirm the caller holds BOTH required roles** before an `assignToDomain` — domain contributor (or domain Admin) **and** workspace Admin. Holding one is the common failure; say which is missing.
- **Show current state before overwriting it** — a workspace already in a domain is being *reassigned*; name the domain it is leaving. A description or tag change should show before/after.
- **Use only Core reads for a single-workspace assignment preflight** — resolve the workspace with `GET /v1/workspaces`, read its current `domainId` with `GET /v1/workspaces/{id}`, and resolve the target with `GET /v1/domains`. Do not switch to `/v1/admin/*` or the admin bulk-assignment procedure.
- **Get user approval for proposed descriptions** — a confidently wrong description is worse than a missing one.
- **Report tag deletion blast radius** — applying is safe; if the user asks to *remove* a tag from items, say how many items carry it. (Deleting the tag *definition* is admin-only — that's admin-remediate tags.md § Manage Tags.)

### PREFER

- **Fix the cause, not the symptom** — a repeatedly stale model needs its schedule or data source fixed, not a manual refresh each time.
- **The least-privileged endpoint** — these calls need workspace/domain roles, not tenant admin; don't send the user to get admin rights for an item-level fix.

### AVOID

- Do NOT report `assignToDomain` success from anything other than the synchronous `200` — and do NOT write LRO polling for it (it is **not** async, unlike the admin bulk methods).
- Do NOT attempt to set item identity **for a third party** — the API assigns to the **caller** only.
- Do NOT create/update/delete tenant tag *definitions* here — that needs tenant admin; route to admin-remediate.

---

## Assign / Unassign One Workspace to a Domain (Core API, no tenant admin)

The fix for a data owner who can *see* their workspace is unassigned (from
dataowner-audit.md) but has no tenant-admin rights. This is the **Core API**
path for a single workspace.

Before proposing the write, **execute** this read-only Core preflight. Do not
stop after printing example commands: inspect the live workspace and target
domain unless the user explicitly asked for a plan only.

```bash
# Resolve the caller-visible workspace, then read its current domain assignment.
az rest --method GET --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces?roles=Admin"
az rest --method GET --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS"

# Resolve the target domain by displayName and paginate continuationToken.
az rest --method GET --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/domains"
```

If any read fails, report the corresponding state as unknown and stop the
preflight. A failed lookup never proves that a workspace or domain is absent.

```bash
# Assign — live-verified: returns 200 SYNCHRONOUSLY (not 202/async like the admin bulk methods)
az rest --method POST --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS/assignToDomain" \
  --headers "Content-Type=application/json" \
  --body "{\"domainId\": \"$DOMAIN_ID\"}"

# Reverse — live-verified: 200, no request body
az rest --method POST --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS/unassignFromDomain"
```

> ### ⚠️ Two permissions are required, on two different objects
> Per [Learn](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/assign-to-domain), the caller must have **contributor permissions on the domain (or be a domain Admin)** *and* **the workspace Admin role**. Holding only one is the common failure:
>
> | Error code | Missing |
> |---|---|
> | `InsufficientPermissionsToDomain` | Rights on the **domain** |
> | `InsufficientWorkspaceRole` | **Workspace Admin** on the workspace |
>
> So this is not a general "non-admin can self-serve" escape hatch — it works only for someone who already sits on **both** sides of the assignment. If a data owner lacks domain contributor rights, they still need an admin. Say which of the two is missing rather than reporting a generic permission error.

| Point | Detail |
|---|---|
| Scope | `Workspace.ReadWrite.All`. Users, service principals **and** managed identities are supported |
| Sync vs async | **Synchronous 200** — unlike the admin `assignWorkspaces*` bulk methods, which return `202` + `Location`. Do not write LRO polling for this call |
| Unassign | Use `unassignFromDomain`. Passing `{"domainId": null}` to `assignToDomain` is **rejected with 400** (`InvalidParameter`) — live-verified |
| Scale | One workspace per call. For many workspaces **with tenant admin**, prefer the bulk methods in admin-remediate domain-assign-workspaces.md § Choosing a bulk-assignment method |
| Overrides | Moving an already-assigned workspace here is a **reassignment**; confirm the current `domainId` first and tell the user which domain it is leaving |

---

## Apply Tags to Items and Workspaces (workspace role)

Applying an existing tenant tag needs only workspace rights. **Creating, renaming or deleting the
tag definition is tenant-admin-only** — see admin-remediate tags.md § Manage Tags.

```bash
# To an item — needs workspace Contributor or higher
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}/applyTags" \
  --body '{"tags":["<tagId>"]}'

# To a workspace (PREVIEW) — needs workspace Admin
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/applyTags" \
  --body '{"tags":["<tagId>"]}'
```

| Constraint | Value |
|---|---|
| Tags per item / per workspace | 10 |
| Rate limit | 25 req/min (apply) |
| Service principal | Supported |

---

## Fix Curation Gaps (Descriptions) (item Write, workspace Contributor)

Remediates pillar-3 "low description coverage" findings. Needs read+write on the item — **not** tenant admin.

```bash
az rest --method patch --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}" \
  --body '{"description":"Curated monthly sales fact table, refreshed nightly from ERP."}'
```

- Body accepts `description` and optionally `displayName`.
- **Description max 256 characters** — truncate proposed text before sending.
- Item-type-specific variants exist (`/reports/{id}`, `/semanticModels/{id}`) and behave the same.
- **Never auto-generate descriptions silently.** Propose text per item and get the user's approval.

---

## Trigger a Semantic Model Refresh (Power BI API, workspace member)

Remediates pillar-3 staleness findings. **Power BI API only — there is no Fabric-native REST refresh endpoint.**

```bash
az rest --method post --resource https://analysis.windows.net/powerbi/api \
  --url "https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes" \
  --body '{"notifyOption":"NoNotification"}'
```

- Requires `Dataset.ReadWrite.All`.
- **Shared capacity: max 8 refreshes per day**, and only `notifyOption` is accepted — enhanced refresh (partitions, tables, retries, timeout) is Premium/Fabric-capacity only.
- Prioritize **certified-but-stale** items first — see `govern-pillars.md` § Reporting Conventions.
- A manual refresh treats the symptom; if a model is repeatedly stale, fix the schedule or the failing data source instead.

---

## Reassign Item Ownership (Item Identity, Preview) (item Write; assigns to caller)

Fabric items historically depended on the **creator** for connection access, so they broke when that
person left. **Item identity** replaces that with an explicitly assigned `defaultIdentity`.
([Learn](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/associate-item-identity))

> ### ⚠️ This assigns the identity to the **caller** — you cannot set it to a third party
> The documented body is `{"assignmentType": "Caller"}`. You are not transferring ownership *to someone*; you are claiming it *yourself*. It requires **Write permission on the item and all child items**. This is why it lives in the data-owner cell, not the admin cell — a tenant admin generally **cannot** run this on someone else's item; the incoming owner or workspace admin runs it themselves.

```bash
# Run AS the identity that should own the item (user, SPN or managed identity)
az rest --method POST --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS/items/$ITEM/identities/default/assign?beta=true" \
  --headers "Content-Type=application/json" \
  --body '{"assignmentType": "Caller"}'
```

Returns **202 Accepted** with a `Location` header — a long-running operation. Poll it; do not assume success.

| Point | Detail |
|---|---|
| Scope | Sets the identity on the item **and all child items** in one call |
| Failure mode | If a **child** assignment fails the operation **stops** — check `errorInfo`; partial application is possible |
| Supported types | Live-verified: Lakehouse, DataPipeline, Eventstream, Homeone, CopyJob, UserDataFunction. **Learn lists only Lakehouse + Eventstream** — probe, don't hard-code |
| Coverage | **588 of 14,941 items (3.9%)** in a verified tenant — this fixes a small slice |
| Preview | `?beta=true` is mandatory. Behaviour may change |
| Known issue | The type-qualified form (`/lakehouses/{id}/identities/...`) **errors** — always use the generic `/items/{id}/` path |

**Verify afterwards** with `GET /v1/workspaces/$WS/items/$ITEM?include=defaultIdentity` — the field is omitted unless you ask for it.

---

## Assign a Workspace to a Capacity (workspace and capacity roles)

This Core API operation does not require the Fabric tenant-admin role. The caller
must be a workspace **Admin** and a capacity **Contributor** or **Admin**, with
`Workspace.ReadWrite.All` and `Capacity.ReadWrite.All`.

```bash
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/assignToCapacity" \
  --body '{"capacityId":"<capacityId>"}'
```

- The call returns **`202 Accepted`**. Poll workspace state until `capacityId`
  reaches the target; never report success from the initial response.
- Fabric items can target Fabric, Fabric Trial, or Power BI Premium capacities.
- Non-Power BI Fabric items cannot move across regions. Compare source and target
  regions before requesting confirmation.

---

## What a data owner still CANNOT do

Route these to a tenant admin (admin-remediate) or the portal:

| Request | Why not here |
|---|---|
| Create / rename / delete a **domain** or subdomain | Admin API (`/v1/admin/domains`) — see admin-remediate.md |
| Create / delete a **tenant tag definition** | Admin API (`Tenant.ReadWrite.All`) — see admin-remediate tags.md § Manage Tags |
| Assign domain admins / contributors | Admin API — see admin-remediate domain-roles.md § Assign Domain Admins and Contributors |
| **Bulk** assign workspaces by admin or capacity | Admin API — see admin-remediate domain-assign-workspaces.md § Choosing a bulk-assignment method |
| Bulk sensitivity labels / domain default label / enable certification | Admin/Power BI admin surface — see admin-remediate.md |
| Set endorsement (Promoted / Certified) badge | **No public REST API** — portal only (item **Settings → Endorsement**). ⚠️ For **Certified**, first confirm certification is **enabled** in tenant settings *and* that you are in the designated certifier group — otherwise the Certified option won't even appear. Enablement is admin-only: see admin-remediate/trust-curate.md. |
