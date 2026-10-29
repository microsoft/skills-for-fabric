<!-- TOPIC REFERENCE for onelake-catalog-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Manage Tags

> Part of the `onelake-catalog-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md.

Tenant tags are a **health/estate** control — they classify items and workspaces for inventory and discovery. Tag *definitions* are admin-only: tenant tags here, and domain tags (scoped to one domain) by a Fabric or domain admin. A domain tag can't reuse a tenant tag's name, but the same name can exist in different domains. *Applying* a tag isn't an admin write — see [Apply tags](#apply-tags).

---

## Create tags (Fabric admin, `Tenant.ReadWrite.All`)

```bash
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/tags/bulkCreateTags" \
  --body '{"createTagsRequest":[{"displayName":"PII"},{"displayName":"Finance-Critical"}]}'
```

## Update / delete a tag

```bash
az rest --method patch --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/tags/{tagId}" \
  --body '{"displayName":"PII-Restricted"}'

az rest --method delete --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/tags/{tagId}"
```

> ⚠️ **Deleting a tag removes it from every item where it was applied.** There is no "detach only" operation — confirm with the user and report how many items currently carry the tag before deleting.

## Apply tags

> **Applying** or removing a tag is not an admin write, and it has two routes:
> - **On an item** — `curate` mode (needs workspace Contributor or higher); it resolves applicable tags and gets the owner's approval.
> - **On a workspace** — dataowner-remediate.md § Apply or Remove Workspace Tags (needs workspace Admin; preview).
>
> Tag *definition* create/update/delete (above) stays tenant-admin-only.
