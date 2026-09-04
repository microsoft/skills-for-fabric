<!-- MODE REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand by the dispatcher SKILL.md. -->

> **Routing already happened.** The dispatcher SKILL.md is the single source of truth for the 2×2 mode grid, routing rules, and the permission-tier / known-gap notes. This is the **admin-remediate** mode reference — reached when a Fabric **tenant admin** performs tenant-wide governance writes via `/v1/admin/*`.


> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. These are **Admin APIs** (`/v1/admin/*`) — the caller must be a **Fabric tenant administrator**. A **Domain admin is NOT sufficient** and will get `403`; that is the API contract, not a bug. (Non-admin Core-API writes — applying tags, setting item descriptions, single-workspace assignment — are not here; they live in the `dataowner-remediate` mode.)
> 4. **Deleting a domain never deletes workspaces or their data.** It only removes the domain's grouping/governance attribute from the workspace — but a domain with a subdomain that has assigned workspaces has a **real, non-obvious safety gap** between the Admin Portal (which warns you) and the raw REST API (which does not). **Read admin-remediate/domain-crud.md § Deleting a Domain before calling Delete Domain.**
> 5. **Three different token audiences.** Fabric admin/core APIs use `https://api.fabric.microsoft.com`; Power BI label and refresh APIs use `https://analysis.windows.net/powerbi/api`. Using the wrong one returns `401`/`403` that looks like a permissions problem but isn't.
> 6. **Endorsement and DLP policies have NO public write API.** Never fabricate one — see `admin-remediate/no-write-api-escalation.md`.

# OneLake Catalog Govern — Admin Remediate (write) CLI Skill


## Contents

- [Prerequisite Knowledge](#prerequisite-knowledge)
- [Reference Files (load on demand)](#reference-files-load-on-demand)
- [Must/Prefer/Avoid](#mustpreferavoid)
- [Gotchas and Troubleshooting](#gotchas-and-troubleshooting)

Tenant-wide write operations for Fabric governance across all three Govern pillars: **health** (domains, subdomains, bulk domain assignment, tag definitions), **protect** (sensitivity labels, domain default labels), and **trust/curate** (certification enablement). Object-scoped workspace capacity assignment, descriptions, refresh, and item identity belong to `dataowner-remediate`.

**This dispatcher holds only what applies to *every* remediation** — the prerequisites, the Must/Prefer/Avoid rules, and the cross-cutting troubleshooting table. **Each concrete procedure and its procedure-specific gotchas live in a topic file under [admin-remediate/](admin-remediate/) — load the one that matches the task, not all of them.**

## Prerequisite Knowledge

- `govern-roles.md` — **read first**: Fabric admin vs. Domain admin vs. Domain contributor, subdomain admin inheritance, default-domain auto-assignment behavior
- `catalog-concepts.md` — entity model and relationship semantics; which concepts are API-backed
- Repository `common/COMMON-CORE.md` — Fabric REST API patterns, auth
- Repository `common/COMMON-CLI.md` — CLI implementation (`az rest`, quick reference)

## Reference Files (load on demand)

Read the one matching the request. Each carries its own worked example and procedure-specific gotchas; the cross-cutting Gotchas table below applies regardless of which you load.

| File | Read it when the task is… | Pillar / tier |
|---|---|---|
| domain-crud.md | Create / update / **delete** a domain or subdomain. **Read before any delete** — the portal-vs-API safety gap | Health |
| domain-assign-workspaces.md | Assign / unassign workspaces to a domain — **three methods**, choosing between them, override behavior, dry-run first | Health |
| domain-roles.md | Assign domain **admins / contributors** (fixes ownerless domains); the role model; narrowing over-broad scope | Health |
| tags.md | Create / update / delete **tenant tag definitions** (admin-only); applying tags is the data-owner path | Health |
| item-sensitivity-label.md | **Apply / remove item sensitivity labels** — genuinely admin-only, no SPN support, 25 req/hr | Protect |
| domain-default-label.md | Set a domain's **`defaultLabelId`** — stops the backlog regrowing; never labels dormant items | Protect |
| trust-curate.md | **Enable certification** / designate certifiers; where descriptions & refresh live (data-owner) | Trust / curate |
| `admin-remediate/no-write-api-escalation.md` | **Read before promising any remediation** — what has no write API (endorsement, DLP, item delete/ownership, workspace roles) and how to turn a finding into a **named contact list** | Cross-cutting |

> **What lives in the data-owner cell, not here:** applying tags to items/workspaces, fixing item descriptions, triggering a semantic-model refresh, assigning a single workspace to a domain, and reassigning item ownership (item identity) — all need only workspace/item rights, not tenant admin. See dataowner-remediate.md.

---

## Must/Prefer/Avoid

### MUST DO

- **Read admin-remediate/domain-crud.md before any delete operation** — the REST API has no cascade-block or force parameter for domains with subdomains/assigned workspaces; the safety check is the agent's responsibility, not the API's.
- **Before deleting any domain**: check for subdomains (`parentDomainId` match) and check assigned-workspace counts for the domain and every subdomain via `GET /v1/admin/domains/{id}/workspaces`. If any workspaces would be orphaned, get explicit user confirmation naming the affected workspaces and domains before calling `DELETE`.
- **Before bulk-assigning workspaces**, check each target workspace's current `domainId` and warn the user if it will silently override an existing assignment.
- **Use `preview=false`** on Create Domain and Update Domain calls — it's a mandatory query parameter despite the API no longer being preview-only.
- **Dry-run every bulk write.** For label changes, tag deletions, and description updates, show the user the exact affected item list and the before/after value, and get confirmation before executing.
- **Check what actually has a write API** before promising a remediation — see `admin-remediate/no-write-api-escalation.md`. Endorsement and DLP policies cannot be set via REST.
- **When a fix is outside tenant-admin reach, name who can do it.** Item deletion, item ownership and workspace role changes are not admin-writable. Never report "cannot be automated" on its own — produce the contact list, see `admin-remediate/no-write-api-escalation.md` § Route a Finding.
- **Read tenant settings before writing them** — show the current value, then the proposed value. Tenant settings have tenant-wide blast radius.

### PREFER

- **Reassign before delete** — if the user wants to remove a domain but keep its workspaces governed, assign those workspaces to another domain first, then delete.
- **Confirm subdomain admin inheritance** — since subdomains have no admins of their own, don't attempt to set subdomain-specific admins; direct the user to the parent domain's admin settings instead.
- **Domain default sensitivity label over bulk relabeling** — setting `defaultLabelId` on a domain stops the backlog regrowing; bulk `setLabels` clears the existing backlog. Do both, in that order. Note the default label **never** touches dormant unlabeled items.
- **Fix the cause, not the symptom** — a repeatedly stale model needs its schedule or data source fixed, not a manual refresh each time.
- **Batch within documented limits** — 2,000 items per label call, 100 workspaces per scan, 10 tags per item.
- **The least-privileged endpoint** — setting a description needs only workspace rights; don't require the user to obtain tenant admin for item-level fixes.

### AVOID

- Do NOT call `DELETE /v1/admin/domains/{domainId}` without first checking for subdomains and assigned workspaces — this skill's whole value is closing the gap the raw API leaves open.
- Do NOT assume assignment operations warn on override — they don't; check current assignment status yourself.
- Do NOT delete a tag without reporting how many items carry it — deletion detaches it everywhere, and there is no undo.
- Do NOT attempt sensitivity-label writes with a service principal or managed identity — **neither labeling API supports them**; the call will fail.
- Do NOT auto-generate item descriptions without user review — a confidently wrong description is worse than a missing one.
- Do NOT invent an endorsement or DLP-policy endpoint. None exists.
- Do NOT confuse this skill with the read-only `admin-audit` mode (diagnostics only, no writes) or `dataowner-audit` mode (self-service reads on the caller's own workspaces).

---

## Gotchas and Troubleshooting

Cross-cutting symptoms across every remediation. Procedure-specific gotchas live in the matching topic file.

| Symptom | Cause | Fix |
|---|---|---|
| `403 Forbidden` on any write call | Caller lacks the **Fabric tenant administrator** role — a domain or capacity admin is **not** sufficient for `/v1/admin/*` | Confirm the signed-in identity holds the Fabric admin role. A domain admin has **no** admin-API path to these writes (see the dispatcher's known-gap note). |
| `EntityConflict` on Create Domain | Display name already exists tenant-wide | Domain names must be unique across the whole tenant, not just per parent |
| `EntityNotFound` on Create Domain | Bad `parentDomainId` | Verify the parent domain ID exists via `GET /v1/admin/domains` first |
| Workspace assignment silently changed domain | Assign APIs override an existing assignment when the override tenant setting is **enabled** | Check `domainId` before assigning and warn the user; see domain-assign-workspaces.md § Choosing a bulk-assignment method |
| Deleted a domain and workspaces "disappeared" from governance view | Expected — deletion unassigns workspaces, it does not delete them or their data | Reassign the orphaned workspaces to a new/existing domain; nothing was lost except the domain attribute |
| Bulk assign returned success but some workspaces did not move | The tenant setting *"Allow tenant and domain admins to override workspace assignments (preview)"* is **disabled**, so already-assigned workspaces were silently skipped | Re-read `/v1/admin/domains/{id}/workspaces` and report the actual delta. To move them, either enable the setting or unassign from the old domain first |
| Assigned by workspace admin, but new workspaces those people create aren't in the domain | **Expected** — `assignWorkspacesByPrincipals` is point-in-time, not a standing rule | Ongoing auto-assignment requires a **default domain** (portal-only, no API) |
| Assigned by capacity, but workspaces later moved onto that capacity aren't in the domain | **Expected** — same point-in-time semantics | Re-run the bulk assignment periodically, or use a default domain |
| Personal workspaces not picked up by bulk assignment | **Expected and correct** — both bulk methods exclude *My workspaces*, which can never hold a `domainId` | Not a gap; do not report it as one |
| `202 Accepted` from a bulk assign, then reporting success immediately | Both bulk methods are long-running operations | Poll the `Location` URL to a terminal state before reporting anything |
| Unsure if a domain has subdomains before deleting | Domains list doesn't nest subdomains visually | Filter `GET /v1/admin/domains` results by `parentDomainId == <target>` |
| Tried to set a subdomain-specific admin | Subdomains inherit admins from their parent domain | Set admins on the parent domain instead — see domain-roles.md § Role Model |
| `UnsupportedPrincipalTypeForDomainAdminAssignment` | Tried to assign `EntireTenant` (or another unsupported type) as a domain **Admin** | `EntireTenant` is valid for Contributors only; use a `User` or `Group` for Admin |
| `PrincipalWithDomainRoleAssignmentAlreadyExists` | Principal already holds that role on the domain | Not an error condition — `GET .../roleAssignments` first and skip existing principals |
| Domain role assign call rejects the body | `type` must be **plural** — `"Admins"` / `"Contributors"`, not `"Admin"` | Fix the payload casing/plurality |
| Removed `EntireTenant` contributor and users lost access | Contributor scope was the only thing letting them assign workspaces | Assign the intended group **before** unassigning `EntireTenant` |
| Domain contributor still can't assign a workspace | Domain contributor is useless without **workspace Admin** on that workspace | Grant the workspace Admin role, or have a workspace admin perform the assignment |
| `401`/`403` on `api.powerbi.com` calls while Fabric calls succeed | Wrong token audience — label and refresh APIs need `https://analysis.windows.net/powerbi/api` | Acquire a second token for that resource; the Fabric token will not work |
| Label write fails under automation | **Neither `bulkSetLabels` nor `informationprotection/setLabels` supports service principals or managed identities** | Run interactively as a signed-in Fabric admin; there is no unattended path |
| Label write rejected as unknown label | The label is not in the calling admin's own Purview label policy | Use a label assigned to the caller's policy, or have Purview grant it |
| `429` / throttling on bulk labeling | Power BI variant allows only **25 requests/hour** | Batch up to 2,000 items per request and pace the calls |
| Tag deleted and it vanished from many items | Expected — deleting a tag detaches it everywhere | No undo; recreate the tag and re-apply. Always report the applied-item count before deleting |
| Item description rejected | Exceeds the **256-character** limit | Truncate before sending |
| Refresh rejected on shared capacity | Shared capacity allows **8 refreshes/day** and only `notifyOption` | Move to Fabric/Premium capacity for enhanced refresh, or wait for the quota to reset |
| User asks to certify an item via API | **No public REST API exists for setting endorsement** | Enable certification via tenant settings, then endorse in the portal — see `admin-remediate/no-write-api-escalation.md` |
| User asks to create a DLP policy | Not available in Fabric REST | Microsoft Purview portal |
| `PATCH` domain rejected | Missing the mandatory `?preview=false` query parameter | Append it — required on Create *and* Update Domain |
| Domain default label set successfully but nothing gets labeled | Tenant setting **"Domain admins can set default sensitivity labels for their domains (preview)"** is not enabled | Enable it before debugging the call |
| Domain default label set, but old unlabeled items stay unlabeled | **Expected** — the default applies only to *new* items and to *existing unlabeled* items when updated and saved. Dormant items are never touched | Use bulk `setLabels` to clear the backlog, and the default label to stop it regrowing |
| Domain default label didn't override an existing label | Manually applied labels are **never** overridden; auto/policy labels only when lower priority | Working as designed — relabel explicitly if required |
| Domain default label not applying via deployment pipelines or Git | Documented limitation — neither is supported | No workaround; label explicitly in those flows |
| `DELETE /v1/admin/items/{id}` returns 404 | **No admin-tier item write route exists.** Not a permission problem — the route is not real. | Use the core route as someone with workspace Contributor+, or hand off. Never retry with a different admin path. |
| `GET`/`DELETE` on `/v1/workspaces/{id}/items` returns **401** for a tenant admin | Tenant admin does **not** confer workspace membership. Live-verified. | Have a workspace admin act, or take over the workspace in the portal first — an auditable permission change, never silent. |
| User asks "who owns this item so I can ask them to delete it?" | Legitimate and answerable | `admin-remediate/no-write-api-escalation.md` § Route a Finding — workspace admins first, creator second. Do not present the creator as an authority. |
| Assign-identity call returns 202 and nothing seems to change | It is a **long-running operation** | Poll the `Location` header URL; inspect the per-item `assignmentStatus` array. A failed **child** halts the whole operation. |
| `.../lakehouses/{id}/identities/default/assign` errors | **Documented known issue** — the type-qualified path is broken | Use the generic `/items/{id}/identities/default/assign?beta=true` form. |
| User asks to assign an item identity to *another* person or SPN | Not supported — the body is `{"assignmentType":"Caller"}`, which claims ownership **for the caller** | The target identity must make the call itself, with Write on the item and all children. Hand them the command; do not run it as admin. |
