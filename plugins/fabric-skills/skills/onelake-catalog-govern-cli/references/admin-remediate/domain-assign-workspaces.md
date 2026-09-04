<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Assign Workspaces to a Domain


## Contents

- [The three assignment methods](#the-three-assignment-methods)
- [Choosing a bulk-assignment method](#choosing-a-bulk-assignment-method)
- [Example — assign a batch of workspaces, checking for overrides first](#example-assign-a-batch-of-workspaces-checking-for-overrides-first)
- [Non-admin alternative (single workspace, no tenant admin)](#non-admin-alternative-single-workspace-no-tenant-admin)

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md. Related topics: domain-crud.md (create/update/delete the domain), domain-roles.md (who may assign into it).

Remediates the **unassigned-workspaces** and **empty-domain** findings from `admin-audit` mode. All calls here are **Admin APIs** (`/v1/admin/*`) requiring a **Fabric tenant administrator**.

---

## The three assignment methods

**All three portal methods have a REST equivalent.** Picking the wrong one changes *which* workspaces move, so match the API to the user's stated intent.

| Portal option | Endpoint (`POST /v1/admin/domains/{domainId}/…`) | Body key | Selects |
|---|---|---|---|
| By workspace name | `assignWorkspaces` | `workspacesIds` | The exact workspace IDs you pass |
| By workspace admin | `assignWorkspacesByPrincipals` | `principals` | Workspaces where a named principal holds the **Admin** workspace role |
| By capacity | `assignWorkspacesByCapacities` | `capacitiesIds` | All workspaces residing on the named capacities |

Unassign: `unassignWorkspaces` (`workspacesIds`) or `unassignAllWorkspaces`.

📖 **Request/response schemas, principal types, scopes and identity support: [Domains API reference](https://learn.microsoft.com/rest/api/fabric/admin/domains).** Read it rather than relying on this file for payload shape — these are stable, fully documented, and may gain fields.

```bash
# Shape is identical for all three; only the body key changes.
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/${DOMAIN_ID}/assignWorkspaces" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"workspacesIds": ["<id1>", "<id2>"]}'
```

---

## Choosing a bulk-assignment method

Route on the user's stated intent:

| User says | Use | Endpoint |
|---|---|---|
| "these specific workspaces" / a named list | **By workspace ID** | `assignWorkspaces` |
| "everything owned by the Finance team / this group" | **By workspace admin** | `assignWorkspacesByPrincipals` |
| "everything on the Finance capacity" | **By capacity** | `assignWorkspacesByCapacities` |

**Prefer by-ID whenever the targets can be enumerated** — it is the only method whose blast radius is knowable before the call; the other two are evaluated server-side against criteria you cannot fully inspect. Before either bulk method, dry-run the predicted targets and show them to the user:

```bash
# Predicted targets for a by-capacity assignment
jq -r --arg cap "CAPACITY_ID" \
  '[.workspaces[] | select(.capacityId==$cap)] | "\(length) workspaces:", (.[].name)' /tmp/active_ws.json
```

> ⚠️ **`assignWorkspacesByCapacities` / `assignWorkspacesByPrincipals` move *every* matching workspace — including ones already assigned to another domain.** When the override tenant setting is **enabled**, that silently *reassigns* those workspaces out of their current domain. If the user's intent is "assign the **unassigned** ones," enumerate the unassigned IDs on that capacity/principal and use **by-ID** instead, so you never disturb existing members.

### What the reference documentation will not tell you

> ⚠️ **Override is conditional, not guaranteed.** Preexisting assignments are overridden **only if** the tenant setting *"Allow tenant and domain admins to override workspace assignments (preview)"* is enabled. If it is off, already-assigned workspaces are **silently skipped while the operation still reports success**. Never quote an intended count as an achieved one — **re-read the domain's workspace list afterwards and report the actual delta.**

> ⚠️ **All three are point-in-time, not standing rules.** They affect **existing** workspaces only. A workspace created later by a named principal, or later moved onto a named capacity, is **not** assigned. If the intent is "keep this domain populated going forward", these are the wrong tool — that is a **default domain** (portal-only, no API; see the audit skill's Known Blind Spots). Say so rather than implying the problem is permanently solved.

- **Both bulk methods exclude personal workspaces**, consistent with the verified finding that only `Workspace`-type workspaces can hold a `domainId`.
- **By-ID is synchronous** — `assignWorkspaces` returns `200 OK`; verify the resulting membership but do not poll for a nonexistent operation.
- **Principal- and capacity-based methods are asynchronous** — `assignWorkspacesByPrincipals` and `assignWorkspacesByCapacities` return `202 Accepted` + `Location`. Poll to a terminal state and do **not** report success on the 202.
- **Rate limit: 10 requests/minute per principal** — batch accordingly.

---

## Example — assign a batch of workspaces, checking for overrides first

> ⚠️ **Never assign a deleted, personal or admin-monitoring workspace.** `/v1/admin/workspaces` returns all of them by default — only 47% of a verified tenant was governable. **Only `Workspace`-type workspaces can hold a `domainId`** (verified); `assignWorkspaces` on a `Personal` or `AdminWorkspace` ID is not a valid operation. Fetch with `type=Workspace&state=Active` and drop any ID not present before calling `assignWorkspaces`.

```bash
# Active-only snapshot, reused for every check below
az rest --method GET --url "https://api.fabric.microsoft.com/v1/admin/workspaces?type=Workspace&state=Active" \
  --resource "https://api.fabric.microsoft.com" > /tmp/active_ws.json

for id in ws-id-1 ws-id-2; do
  row=$(jq -r --arg id "$id" '.workspaces[] | select(.id==$id)' /tmp/active_ws.json)
  if [ -z "$row" ]; then
    echo "SKIP: workspace $id is not an active workspace (deleted or not found)"
    continue
  fi
  current=$(echo "$row" | jq -r '.domainId // empty')
  if [ -n "$current" ]; then
    echo "WARNING: workspace $id already assigned to domain $current — will be overridden ONLY if the override tenant setting is enabled"
  fi
done

az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/TARGET_DOMAIN_ID/assignWorkspaces" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"workspacesIds": ["ws-id-1", "ws-id-2"]}'

# Verify the delta — do not trust the response alone
az rest --method GET --url "https://api.fabric.microsoft.com/v1/admin/domains/TARGET_DOMAIN_ID/workspaces" \
  --resource "https://api.fabric.microsoft.com" | jq -r '.value[].id'
```

---

## Non-admin alternative (single workspace, no tenant admin)

A domain contributor who is also a workspace Admin can self-assign **one** workspace via the Core API (`POST /v1/workspaces/{workspaceId}/assignToDomain`) without tenant-admin rights — **both** permissions are required. That path lives in the data-owner cell: dataowner-remediate.md § Assign / Unassign One Workspace to a Domain. As a tenant admin with **many** workspaces to move, prefer the bulk methods above.
