<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# What Has No Write API — and How to Escalate

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md. **Read this before promising any remediation.**

At admin tier you can read *almost everything* and write *almost nothing* about item content. This file lists what has no admin write path, how to turn such a finding into a **named contact list**, and the one preview exception (item identity).

---

## What Has No Write API

Do **not** invent endpoints for these. If the user asks for them, say plainly that no public REST API exists and give the portal path.

| Request | Why this API matters | Status | Do this instead |
|---|---|---|---|
| Set endorsement (Promoted / Certified / Master data) on an item | Endorsement is the trust signal consumers rely on to tell an authoritative item from an ad-hoc one. Scripting it would let governance certify at scale and keep trust badges current across thousands of items, instead of clicking through each one by hand. | **No public REST API** — not on Fabric core, Fabric admin, or Power BI. `PATCH` item endpoints expose only `displayName` and `description`. | Endorse via the item's **Settings → Endorsement** page in the Fabric portal. You *can* enable certification **via the tenant-settings API** (`GET`/`POST …/tenantsettings/CertifyDatasets`, see trust-curate.md) — that half is scriptable; only applying the badge to an item is portal-only. |
| Create or modify Fabric DLP policies | DLP policies are the primary control stopping sensitive data from leaking out of the tenant. API access would let teams codify, version-control, and consistently roll out data-loss protection rather than hand-editing them in a portal where drift and gaps go unnoticed. | **No public REST API documented.** | Microsoft Purview portal → Data loss prevention. |
| Read DLP violations or last-evaluation time | Violation counts and evaluation freshness are core compliance evidence. Without them you cannot automate audit reporting, alert on new violations, or catch items whose DLP evaluation has gone stale and is silently no longer protecting anything. | **Not exposed by any API** used in this skill family. | OneLake catalog **Govern tab → View more → Protect, secure & comply** (DLP selector: evaluated items, violations, last evaluation time), or **Microsoft Purview portal → Data loss prevention → Alerts** for aggregate alerts. |
| Set the tenant-wide default sensitivity label policy | A tenant-wide default guarantees nothing ships unclassified — the baseline that makes every downstream protection (encryption, DLP, access) enforceable. Scripting it would let governance set and prove that floor across the whole tenant in one action. | Not in Fabric REST. | Microsoft Purview, or PowerShell `Set-LabelPolicy`. Domain-level defaults *are* settable — see domain-default-label.md. |
| Read **or** set a **domain image** / branding | Branding is how users recognize an authoritative domain at a glance, which drives them toward governed data and away from shadow copies. An API would let large orgs standardize domain identity consistently instead of relying on each domain admin to get it right. | **No API field exists — not readable and not writable.** The `Domain` object exposes only `id`, `displayName`, `description`, `parentDomainId`, `defaultLabelId` — verified against the schema and live responses — so there is no field to `GET` and none to `PATCH`. This is not a missing write path over a readable value (as with endorsement); the property is absent from the API surface entirely. | Admin portal → Domains → select domain → domain settings. Domain admins can set it themselves. |
| Configure a **default domain** (auto-assign users' workspaces) | Auto-assigning new workspaces to the right domain keeps the catalog organized and governed as the tenant grows, instead of accumulating unclassified workspaces. An API would let this scale and be audited — especially since the setting also grants contributor access, a permission change that ought to be tracked. | **No API exists** to read or set the user/group list. `UpdateDomainRequest` accepts only `displayName`, `description`, `defaultLabelId`; all candidate endpoints return 404. | Admin portal → Domains → domain settings. ⚠️ Note this also **implicitly grants domain contributor** to those users, so it is a permission change, not just an assignment convenience. |
| Fabric-native semantic model refresh | Fresh data is the entire purpose of a semantic model; a stale one silently serves wrong numbers to every report built on it. Admin-triggerable refresh would let governance guarantee freshness SLAs and remediate stalled models without chasing each owner. | **Not documented — no admin or public REST API.** The Power BI refresh API applies to Power BI semantic models, not Fabric-native ones. | **Escalate** — the **item owner** or a **workspace admin** must run it (portal *Refresh now*, a scheduled refresh, or a Data Factory semantic-model-refresh activity). Name them via Route a Finding to Someone Who Can Fix It. For Power BI models, the owner can use the Power BI refresh API (dataowner-remediate.md). |
| **Add or change a workspace role assignment as tenant admin** (e.g. fix a single-admin workspace) | A workspace with a single admin is a bus-factor risk — if that person leaves, the workspace becomes unmaintainable and its data ungoverned. An admin write path would let the tenant admin remediate this resilience gap directly, which is exactly the kind of finding the audit surfaces. | **No admin-scoped write route.** Live-verified: `GET /v1/admin/workspaces/{id}/roleAssignments` reads roles fine, but `POST` to it returns **404** — it is read-only. The write route `POST /v1/workspaces/{id}/roleAssignments` returned **403** to a tenant admin, because it requires the **workspace Admin** role, which tenant admin does not confer. | Ask an existing workspace admin to add the second admin, or have the tenant admin take over the workspace first via the portal. ⚠️ Taking over is a visible, auditable permission change — never do it silently to "fix" a report. |
| **Set a capacity's admins, or resolve an invisible capacity** | Capacity admins own cost and performance for everything running on that capacity; an invisible capacity is a governance blind spot with no accountable owner. An API would let governance restore visibility and assign ownership so capacity risk doesn't go unmanaged. | No governance write path here, and 36% of workspaces in a verified tenant referenced a capacity absent from both capacity endpoints (direct fetch returned `401`). | Capacity admins are managed in the **Azure portal** (Fabric capacity resource) or Power BI admin portal, not via these APIs. |
| **Reassign ownership of items whose creator has left** | An item whose creator has left is orphaned — no one is accountable for maintaining, refreshing, or securing it, yet it stays live in the catalog. Reassignable ownership keeps every item tied to an active, contactable person. | `creatorPrincipal` is **not writable** — `PATCH` item endpoints expose only `displayName` and `description`. ⚠️ **Partly superseded:** for item types supporting **item identity**, ownership *is* now reassignable — see Reassign Item Ownership below. | For unsupported types (~96% of items): take over in the portal, or recreate under an active owner. For semantic models, use *Take over* in dataset settings. |
| **Delete or edit an item as tenant admin** (e.g. clean up stale/unused items found by the audit) | Stale and unused items inflate cost, clutter the catalog, and widen the attack surface. An admin write path would let governance act on its own audit findings — the audit is only worthwhile if the admin who runs it can also clean up what it finds. | **No admin-tier write route exists at all.** Live-verified: `DELETE /v1/admin/items/{id}` and `DELETE /v1/admin/workspaces/{ws}/items/{id}` both return **404** — the routes are not real. The only delete route is the core `DELETE /v1/workspaces/{ws}/items/{id}`, which needs **workspace Contributor or above**. Against a workspace the tenant admin is not a member of, even `GET /v1/workspaces/{ws}/items` returned **401 Unauthorized**. | **You cannot do this yourself.** Route it to the workspace admins or the item creator — see Route a Finding to Someone Who Can Fix It. A tenant admin can add themselves via the portal first, but that is a visible, auditable permission change. |
| **Read one item's permission list** | Per-item access is what proves least-privilege: an item may be shared far more narrowly — or more widely — than its workspace. Without per-item ACLs you cannot verify an item isn't over-shared, which is the central question of an access audit. | `GET /v1/admin/items/{id}/users` returns **404** — live-verified against a real item ID; no per-item ACL exists at admin tier. | Fall back to **workspace**-level access: `GET /v1/admin/workspaces/{id}/users`. State plainly that you are reporting workspace access, not item access. |

---

## Route a Finding to Someone Who Can Fix It (Escalation Lists)

Several Pillar 1 findings — stale items, unused items, creator-unresolvable items, single-admin workspaces — are **found by the tenant admin but fixable only by someone else**. The audit surfaces them; the tenant admin has no write path (see the table above).

Do not end there. **A finding with no named owner is not actionable.** Convert it into a contact list.

> **The asymmetry to state out loud:** at admin tier you can read *everything* and write *almost nothing* about item content. Live-verified on a workspace the tenant admin was not a member of: `/v1/admin/workspaces/{id}/users` and `/v1/admin/items?workspaceId=` both returned **200**, while the core `/v1/workspaces/{id}/items` returned **401**. You will always be able to say **who** must act, and usually not act yourself.

### Who to contact, in priority order

| Rank | Contact | Where it comes from | Use when |
|---|---|---|---|
| 1 | **Workspace admins** | `GET /v1/admin/workspaces/{id}/users` → entries with `workspaceAccessDetails.workspaceRole == "Admin"`, each carrying `principal.userDetails.userPrincipalName` | Always. They can delete, re-permission and reassign inside the workspace. |
| 2 | **Item creator** | `creatorPrincipal.userDetails.userPrincipalName` on `GET /v1/admin/items` | Context on *why* the item exists. Not an authority — see caveats. |
| 3 | **Domain admins** | `GET /v1/admin/domains/{id}` → `adminPrincipals` | The workspace is in a domain and its admins are unresponsive or absent. |
| 4 | **Capacity admins** | `GET /v1.0/myorg/admin/capacities` → `admins` | Capacity-level findings only. |

### Building the list

```bash
# For each workspace containing findings, get its admins with contactable UPNs
curl -sS -H "Authorization: ******" \
  "https://api.fabric.microsoft.com/v1/admin/workspaces/$WS/users" \
| jq -r '.accessDetails[]
         | select(.workspaceAccessDetails.workspaceRole == "Admin")
         | [.principal.displayName, .principal.type,
            (.principal.userDetails.userPrincipalName // "no-upn")] | @tsv'
```

For more than a handful of workspaces use the scanner API instead — `POST /v1.0/myorg/admin/workspaces/getInfo?getArtifactUsers=True` returns `users[]` with `emailAddress` and `groupUserAccessRight`, **100 workspaces per call**. Live-verified.

### Caveats you must carry into the report

1. **Creator is not owner and not an authority.** They may have moved teams or left. Never write "ask the owner" — write "created by X; workspace admins are Y and Z."
2. **`creatorPrincipal.type` is always `"User"`**, including for service principals. An SPN-created item has no human to email; escalate to the workspace admins instead.
3. **Group admins are not a person.** A `principal.type` of `Group` gives you a group, not an inbox — its membership is not resolvable from these APIs. Report the group name and say membership was not expanded.
4. **Workspace access ≠ item access.** There is no per-item ACL at admin tier (404). An item may be shared more narrowly than its workspace.
5. **Deleted workspaces still return users.** Scope to `state=Active` and `type=Workspace` first, or you will email people about workspaces that no longer exist.

### Reporting shape

Group by **who must act**, not by finding type — one person should receive one list, not six:

```
Testuser1@contoso.com — workspace "Sales Analytics" (Admin)
  - 12 items not modified in 180+ days  → confirm still needed, else delete
  - 1 item whose creator no longer resolves → reassign or take over
  - Workspace has 1 admin → add a second (tenant admin cannot do this for you)
```

Then state explicitly which of these the tenant admin **could** have done and chose not to, versus which are **impossible** at admin tier. That distinction is the difference between a delegation and an excuse.

---

## Reassign Item Ownership (Item Identity, Preview)

> **This runs in the data-owner cell, not here.** Item-identity assignment requires **Write on the item and its children** and assigns to the **caller** — a tenant admin generally cannot run it on someone else's item. The full procedure is dataowner-remediate.md § Reassign Item Ownership (Item Identity, Preview). When you find orphaned ownership as an admin, hand this instruction to the workspace admin / incoming owner and pair it with the escalation list above.
