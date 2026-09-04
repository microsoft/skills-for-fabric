<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Domain Roles — Admins, Contributors, and the Role Model

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md. Related topics: domain-crud.md (create/update/delete), domain-assign-workspaces.md (put workspaces into a domain).

Remediates the **ownerless domain** and **over-broad contributor scope** findings from `admin-audit` mode. All calls here are **Admin APIs** (`/v1/admin/*`) requiring a **Fabric tenant administrator**.

---

## Role Model

**Who can do what is defined once, in `govern-roles.md` § Role Reference** — Fabric admin, Domain admin, Domain contributor, and the workspace roles they depend on. Read it there; it is not restated here.

Two rules from it matter so much for the operations below that they are repeated deliberately:

- **Subdomains have no admins of their own.** A subdomain's admins are always its parent domain's admins — there is no way to scope admin rights to just a subdomain.
- **Domain admins cannot delete or rename a domain**, or add/remove other domain admins. Only a Fabric admin can. If a delete call fails for a domain admin, that is the contract, not a bug.

---

## Assign Domain Admins and Contributors

This is the API-backed answer when a user asks to "assign a steward/owner" to a domain, or to narrow who may populate it.

```bash
# Inspect current ownership first — always
az rest --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments"

# Assign domain admins (note: type is PLURAL)
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments/bulkAssign" \
  --body '{"type":"Admins","principals":[{"id":"<groupObjectId>","type":"Group"}]}'

# Assign domain contributors
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments/bulkAssign" \
  --body '{"type":"Contributors","principals":[{"id":"<userObjectId>","type":"User"}]}'

# Remove a principal from a domain role
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/{domainId}/roleAssignments/bulkUnassign" \
  --body '{"type":"Contributors","principals":[{"id":"<principalId>","type":"EntireTenant"}]}'
```

- Requires **Fabric admin** (`Tenant.ReadWrite.All`); 25 req/min. Service principals and managed identities **are** supported here (unlike the labeling APIs).
- `type` must be `"Admins"` or `"Contributors"` — **plural**. `principal.type` is `User`, `Group`, `ServicePrincipal`, `ServicePrincipalProfile`, or `EntireTenant`.
- **`EntireTenant` is contributor-only.** Passing it as an Admin returns `UnsupportedPrincipalTypeForDomainAdminAssignment`.
- **Prefer a security Group over an individual User** for the Admin role — single-user ownership is key-person risk and breaks when someone leaves.
- **Do not assign admins to a subdomain** — subdomains inherit admins from the parent. Set them on the parent domain instead.
- Assigning a role a principal already holds returns `PrincipalWithDomainRoleAssignmentAlreadyExists` — not an error condition; `GET .../roleAssignments` first and skip existing principals.
- The role-assignment read is paginated. Follow every `continuationUri` before checking whether a principal already has a role.

### Narrowing an over-broad contributor scope

A new domain defaults to an **`EntireTenant`** contributor, meaning *any* user in the tenant can assign workspaces into it. To close that:

1. **First** `bulkAssign` the intended security group as `Contributors`.
2. **Then** `bulkUnassign` the `EntireTenant` principal.

Do it in that order — unassigning `EntireTenant` before granting the replacement can lock out the people currently doing the work.

### Confirm the write — do not trust the response

`bulkAssign` returns an empty success body. Re-read and fully paginate `GET /v1/admin/domains/{id}/roleAssignments`, then confirm the `Admin` / `Contributor` delta before reporting success.

> **Default domains grant contributor rights implicitly.** A domain designated the *default* for named users/groups makes them domain contributors, and no API reads that list. So `roleAssignments` output is a **lower bound** on who can act — say so when reporting ownership.
