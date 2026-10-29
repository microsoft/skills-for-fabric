# API Reference — OneLake Catalog Curation

All control-plane calls use `az rest --resource "https://api.fabric.microsoft.com"`.
Base URL: `https://api.fabric.microsoft.com/v1`. Auth is delegated to
`common/COMMON-CLI.md` / `common/COMMON-CORE.md` (linked from `SKILL.md`)
— never embed tokens.

## Contents

- [Update Item (description, display name)](#update-item-description-display-name)
- [List Tags (resolve names → IDs)](#list-tags-resolve-names--ids)
- [Apply Tags](#apply-tags)
- [Unapply Tags](#unapply-tags)
- [Get Item (baseline / verify)](#get-item-baseline--verify)
- [Get Item Definition (content basis)](#get-item-definition-content-basis)
- [List Items (enumerate a workspace's candidates)](#list-items-enumerate-a-workspaces-candidates)
- [Bulk apply — batching & throttling](#bulk-apply--batching--throttling)
- [Gaps (no owner-facing write API)](#gaps-no-owner-facing-write-api)

## Update Item (description, display name)

`PATCH /v1/workspaces/{workspaceId}/items/{itemId}`

- Permissions: read **and write** on the item. Scope `Item.ReadWrite.All` (or `{type}.ReadWrite.All`).
- Body accepts only `description` (**≤ 256 chars**) and `displayName`. Send only the keys you change.
- **`displayName` is not writable for every item type.** Some types (e.g. **SQLDatabase**) reject a
  name change with `400 SQLDatabaseDisplayNameCannotBeChanged` — the name is fixed at creation and
  bound to the provisioned database identity. Say the rename isn't possible for those types (see
  `metadata-suggestion-guidance.md`).
- **`PATCH` is atomic** — if any field in the body is rejected, the whole call fails and *no* field
  is written. Apply `displayName` and `description` in **separate** PATCH calls (or drop
  `displayName` and retry description-only) so an immutable/invalid name can't block the description.

```bash
cat > /tmp/update.json << 'EOF'
{ "description": "Sales warehouse holding order and revenue facts, used for company-wide revenue reporting." }
EOF
az rest --method patch \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items/$ITEM_ID" \
  --body @/tmp/update.json
```

Response is the updated `Item` (includes `description`, `displayName`, `tags`, `sensitivityLabel`).
Common errors: `ItemNotFound`, `InvalidRequest`, `429 Too Many Requests` (honor `Retry-After`).

## List Tags (resolve names → IDs)

`GET /v1/tags` — returns the tenant's tag definitions, including tenant-scoped tags and
domain-scoped tags, with `id`, `displayName`, and `scope`. A tenant scope is
`{ "type": "Tenant" }`; a domain scope is `{ "type": "Domain", "domainId": "<uuid>" }`.
Before applying, include all tenant-scoped tags but only domain-scoped tags whose `domainId`
matches the target workspace's current domain. Scope `Tag.Read.All`; limit **25 requests /
minute** per principal — read it once per run and reuse the result. The response is paginated:
follow `continuationUri` until it is absent, then filter the combined list — a tag on a later
page is not missing.

```bash
# collect every page, then filter; keep the scope: the same name can exist in several domains
URL="https://api.fabric.microsoft.com/v1/tags"; : > /tmp/tags.jsonl
while [ -n "$URL" ]; do
  PAGE=$(az rest --method get --resource "https://api.fabric.microsoft.com" --url "$URL")
  echo "$PAGE" | jq -c '.value[]' >> /tmp/tags.jsonl
  URL=$(echo "$PAGE" | jq -r '.continuationUri // empty')
done
jq -s '[.[] | select(.displayName == "Sales") | {id, scope}]' /tmp/tags.jsonl
```

Use an ID only if its scope is `Tenant`, or `Domain` with the workspace's current `domainId`.

## Apply Tags

`POST /v1/workspaces/{workspaceId}/items/{itemId}/applyTags`

- Permissions: Contributor or higher on the workspace. Scope `ItemMetadata.ReadWrite.All` or `Item.ReadWrite.All`.
- Limit: **25 requests / minute** per principal; at most **10 tags** per item.
- Body: `{ "tags": ["<tagId>", ...] }` — **tag IDs**, not names.

```bash
cat > /tmp/tags.json << 'EOF'
{ "tags": ["97dd1d38-a4c6-41ed-bc4f-1e383f8ddd0f", "41d5b790-76d9-4ebe-9f06-b34cc280a612"] }
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items/$ITEM_ID/applyTags" \
  --body @/tmp/tags.json
```

Errors: `ItemNotFound`, `EntityNotFound` (tag ID does not exist), `InvalidInputs`.

## Unapply Tags

`POST /v1/workspaces/{workspaceId}/items/{itemId}/unapplyTags` — same body shape as Apply Tags.

## Get Item (baseline / verify)

`GET /v1/workspaces/{workspaceId}/items/{itemId}` — returns `displayName`, `description`,
`tags[]` (`{id, displayName}`; the field is absent when the item has no tags), `sensitivityLabel`
(`{id}`), `type`, `workspaceId`. Use before proposing (baseline) and after applying (verify).

## Get Item Definition (content basis)

`POST /v1/workspaces/{workspaceId}/items/{itemId}/getDefinition` — returns the item's
definition envelope, used to ground description/tag suggestions. **Not supported** for
Warehouse, SQL Database, SQL analytics endpoint, ML model/experiment or Datamart (see the
[item-definition overview](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/item-definition-overview))
— don't call it for them. For lakehouse/warehouse/SQL database use
`GET /v1/workspaces/{ws}/lakehouses/{id}/tables` and SQL system catalog queries.

## List Items (enumerate a workspace's candidates)

For **workspace** curation, enumerate items in the **one named workspace** and keep those with
weak metadata (empty `description`, placeholder `displayName`, empty `tags`), excluding
Dataflows Gen2 staging artifacts.

```bash
# items in the named workspace (optionally filter by ?type=Lakehouse); follow continuationToken
az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items"
```

Filter locally for candidates, e.g. items with an empty description:

```bash
--query "value[?description==null || description==''].{id:id,name:displayName,type:type}"
```

The endpoint paginates via `continuationToken` — follow it until exhausted. **Exclude system
plumbing** — Dataflows Gen2 staging items (`StagingLakehouseForDataflows*`,
`StagingWarehouseForDataflows*`, and their SQL endpoints) are never owner-curated. Confirm the
caller has **write access** on the workspace before proposing changes; a `403` at apply is the
safety net for item-level sharing edge cases.

## Bulk apply — batching & throttling

- `applyTags` is limited to **25 requests / minute** per principal. For a batch, queue the
  per-item `applyTags` calls and throttle to stay under the limit; honor `Retry-After` on `429`.
- Apply each item independently (`PATCH` then `applyTags`); on a per-item failure, record it and
  continue the batch. Report each change as saved, skipped or not saved (with the reason).

## Gaps (no owner-facing write API)

| Capability | Why it's a gap |
|-----------|----------------|
| **Sensitivity label write** | `Update Item` body does not accept `sensitivityLabel`. Only the tenant-admin **Admin — Items Set Labels** API can set labels. Not an owner self-service action — say so. |
| **Endorsement (promote/certify) write** | No public Fabric core REST API to set endorsement today (portal UI only) — say so. |
| **SQLDatabase display-name rename** | The display name of a **SQLDatabase** item is immutable (fixed at creation, bound to the provisioned database identity). `Update Item` rejects it with `400 SQLDatabaseDisplayNameCannotBeChanged` — say it can't be renamed; curate the **description** and **tags** instead. |

`GET items/{id}` returns `displayName` and `sensitivityLabel` for display; never *write* either
label or endorsement here. It returns **no endorsement** field, so it can't show an item's current
endorsement — that comes from the admin scanner for supported Power BI items (a governance read,
see govern-data-sources.md).
