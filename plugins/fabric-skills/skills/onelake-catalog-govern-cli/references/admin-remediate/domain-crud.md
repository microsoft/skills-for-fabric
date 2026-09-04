<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Domain CRUD — Create, Update, Delete


## Contents

- [Creating Domains and Subdomains](#creating-domains-and-subdomains)
- [Updating a Domain](#updating-a-domain)
- [Deleting a Domain — The Portal-vs-API Safety Gap](#deleting-a-domain-the-portal-vs-api-safety-gap)

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md for the Must/Prefer/Avoid rules, the irreversible-write gates, and the load-on-demand table. Related topics: domain-assign-workspaces.md (put workspaces into a domain), domain-roles.md (owners & contributor scope, and the role model).

All calls here are **Admin APIs** (`/v1/admin/*`) and require a **Fabric tenant administrator**; a Domain admin gets `403`.

---

## Creating Domains and Subdomains

> ⚠️ **MUST prompt for the governance elements at creation time — do not create a bare domain.** Every element below is something `admin-audit` mode flags as a gap the moment the domain exists. Creating a domain without them just manufactures the exact findings (ownerless domain, open contributor scope, missing default label, missing description) that a later audit will report and that a later remediation pass will have to fix one-by-one. Capturing them **up front, in one interaction, is the cheapest point to close them** — a subdomain created now with no owner is an audit finding an hour later.
>
> **Before calling the create API, walk the user through these four elements. The user MAY explicitly skip any of them — record the skip and surface it in the result so it is a conscious choice, not a silent omission.** Never invent values (never fabricate an owner principal, a label, or a description) — collect them, or mark them skipped.
>
> | # | Element | What to ask | If provided | If skipped (state this in the result) |
> |---|---|---|---|---|
> | 1 | **Admin owner** | "Who should own this domain? A security **group** is strongly preferred over an individual (single-user ownership is key-person risk)." Resolve the group/UPN to an Entra object ID. | After create, assign via domain-roles.md § Assign Domain Admins and Contributors (`bulkAssign`, `type:"Admins"`). **Do not** set an admin on a **subdomain** — it inherits the parent's admins; ask about the parent instead. | Domain is **ownerless** — only tenant admins can manage it. Flag it as a pillar-1 gap to fix next. |
> | 2 | **Description** | "What is this domain for?" **Offer suggested text** the user can accept, edit, or reject — e.g. `"<DisplayName> data products and reports, governed by <owner team>."` Keep ≤ 256 chars. | Pass in the `description` field of the create body (below). | Domain purpose is opaque to admins and consumers — discoverability gap. |
> | 3 | **Default sensitivity label** | "Set a default sensitivity label so new and touched-unlabeled items inherit a baseline?" | After create, set `defaultLabelId` via domain-default-label.md. Note it only labels **new** and **touched-unlabeled** items — pair with bulk relabeling for any backlog. | No labeling baseline — the unlabeled backlog keeps growing. **Protect**-pillar gap. |
> | 4 | **Contributor scope** | "Who may assign workspaces into this domain?" A new domain defaults to **`EntireTenant`** contributor scope, meaning *any* user in the tenant can populate it. Recommend narrowing to a named group. | Assign the intended group as `Contributors`, **then** `bulkUnassign` the `EntireTenant` principal (in that order, so you don't lock out current workers) — see domain-roles.md. | Membership is **uncontrolled** — any tenant user can assign workspaces in. Membership-control risk. |
>
> Only `displayName` (and `parentDomainId` for a subdomain) are strictly required by the API; the four elements above are required by **this skill's workflow**, each with an explicit opt-out.

```bash
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"displayName": "Finance", "description": "Finance data and reports", "parentDomainId": null}'
```

- `displayName` max 40 characters, `description` max 256 characters.
- Omit `parentDomainId` for a top-level domain; set it to create a subdomain.
- **`preview=false` is mandatory** as a query parameter — this API was promoted from preview but still requires the flag.
- Errors: `EntityNotFound` (bad `parentDomainId`), `EntityConflict` (display name already exists **tenant-wide**), `InvalidInput`.
- `description` and `defaultLabelId` can be set in this create call *or* patched afterwards; **admin owner and contributor scope are always separate calls** (`roleAssignments/bulkAssign`), so a create is not "done" until those follow-ups run or are explicitly skipped.

### After creating — confirm the governance posture

Close the loop so the user sees exactly what was set vs. skipped. Read the new domain back and report a one-line posture summary, e.g.:

> Created **Trial** (`2c45…`). Owner: **Testuser1** ✓ · Description: ✓ · Default label: **skipped** · Contributor scope: still **EntireTenant** (skipped). Two elements were skipped — say the word and I'll close them.

This mirrors the `admin-audit` domain-health checks, so a domain created through this skill starts in a state the audit would pass — or with the gaps named out loud.

### Example — create a subdomain under Finance

```bash
# 1. Find the Finance domain's ID
az rest --method GET --url "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" \
  --resource "https://api.fabric.microsoft.com" | jq -r '.domains[] | select(.displayName=="Finance") | .id'

# 2. Create the subdomain
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"displayName": "Finance-EMEA", "parentDomainId": "<finance-domain-id>"}'
```

---

## Updating a Domain

```bash
az rest --method PATCH \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/${DOMAIN_ID}?preview=false" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{"displayName": "Finance (EMEA)", "description": "Updated description"}'
```

- `preview=false` is a **mandatory** query parameter on Update as well as Create.
- `UpdateDomainRequest` accepts only `displayName`, `description`, `defaultLabelId` — no branding/image or default-domain fields exist (see the dispatcher's What Has No Write API).
- Subdomains currently only support general settings (name/description) in the portal — they don't have their own admins, images, or delegated settings panels.

---

## Deleting a Domain — The Portal-vs-API Safety Gap

> ⚠️ **This is the most important rule in this file. Read it before writing any delete logic.**

**What the Admin Portal UI does** (observed behavior, confirmed by the user of this repo who has seen it directly): when a Fabric/domain admin deletes a domain that has a **subdomain with workspaces still assigned to it**, the portal shows a confirmation dialog stating that once the domain is deleted, its (and its subdomains') associated workspaces will become **unassigned** — i.e., they lose their domain attribute rather than being deleted or auto-moved anywhere. The admin can back out and reassign those workspaces first, or proceed and accept that the workspaces become unassigned.

**What the REST API does**:

```bash
az rest --method DELETE \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/${DOMAIN_ID}" \
  --resource "https://api.fabric.microsoft.com"
```

The public API reference for `DELETE /v1/admin/domains/{domainId}` documents **no** cascade-block, no "force" parameter, and no special error code for "domain has a subdomain with assigned workspaces" — only generic `DomainNotFound`/`UnknownError`. In other words:

- **The portal's confirmation step is a UI-only safeguard.** The REST API itself provides no equivalent protection.
- Calling `DELETE` directly is expected to proceed and, presumably, leave the domain's (and any subdomain's) previously-assigned workspaces unassigned — **without warning**, since the API has no confirmation mechanism.
- This has **not been independently verified against a live tenant** by this repo's automated tests — treat the "workspaces become unassigned" outcome as the expected behavior based on documented portal UX, not as an API-guaranteed contract test result.

### MUST DO before calling Delete Domain via this skill

1. **Always check for subdomains first**: exhaust `GET /v1/admin/domains?preview=false` and filter for any domain with `parentDomainId` equal to the target domain's ID.
2. **For the target domain and every subdomain found, exhaust all pages of** `GET /v1/admin/domains/{id}/workspaces`.
3. **If any lookup fails or is denied, stop and report existence and blast radius as unknown.** A `401`, `403`, malformed response, or incomplete page never proves that the named domain, its subdomains, or its workspaces are absent.
4. **If any workspaces would be orphaned, get explicit user confirmation** before calling `DELETE` — state clearly: "Deleting domain X will leave N workspace(s) [list names] unassigned from any domain, including M workspace(s) in subdomain(s) [list subdomain names]. This cannot be undone automatically. Proceed?"
5. **Never silently delete a domain with assigned workspaces (directly or via subdomains) without this confirmation** — the API will not protect the user from data-governance loss the way the portal does.
6. If the user wants to preserve assignments, **reassign workspaces to another domain first** (via domain-assign-workspaces.md) before deleting.

### Example — safely delete a domain with a subdomain

```bash
# 1. Check for subdomains
az rest --method GET --url "https://api.fabric.microsoft.com/v1/admin/domains?preview=false" \
  --resource "https://api.fabric.microsoft.com" | jq '[.domains[] | select(.parentDomainId=="TARGET_DOMAIN_ID")]'

# 2. For target domain + each subdomain found, check assigned workspaces
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/TARGET_DOMAIN_ID/workspaces" \
  --resource "https://api.fabric.microsoft.com"

# Follow every continuationUri from both reads before deciding the blast radius.
# 3. If any workspaces exist, STOP and get explicit user confirmation before proceeding (see MUST DO above)

# 4. Only after confirmation:
az rest --method DELETE \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/TARGET_DOMAIN_ID" \
  --resource "https://api.fabric.microsoft.com"
```
