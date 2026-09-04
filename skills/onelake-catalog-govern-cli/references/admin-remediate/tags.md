<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Manage Tags

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md.

Tenant tags are a **health/estate** control — they classify items and workspaces for inventory and discovery. Tag *definitions* are tenant-scoped and admin-only; *applying* a tag needs only workspace rights.

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

> **Applying** a tag needs only workspace roles — it is the **data-owner write path**. See dataowner-remediate.md § Apply Tags to Items and Workspaces. Tag *definition* create/update/delete (above) stays tenant-admin-only.
