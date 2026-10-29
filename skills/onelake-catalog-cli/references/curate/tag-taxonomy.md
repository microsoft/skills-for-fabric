# Tag Taxonomy & Resolution

Fabric item tags are defined at either **tenant** or **domain** scope and applied by referencing
existing tag **IDs**. Tenant tags are available across the tenant; domain tags are available for
new application only when the item's workspace is assigned to that domain. This skill can
*apply* existing, applicable tags; it cannot create tags.

## Model

| Concept | Detail |
|--------|--------|
| Tenant tags | Tags with `scope.type: Tenant`; available across the tenant. |
| Domain tags | Tags with `scope.type: Domain` and a `scope.domainId`; available for new application only within that domain. |
| Tag identity | Each tag has an `id` (uuid), `displayName`, and `scope`. |
| Applying | `POST .../items/{id}/applyTags` takes an array of tag **IDs**. |
| Unapplying | `POST .../items/{id}/unapplyTags` removes tag IDs from an item. |

## Resolution workflow (name → ID)

1. Read the target workspace's current domain assignment, if any.
2. List the tenant's tag definitions (both tenant- and domain-scoped) with `GET /v1/tags`,
   following `continuationUri` until it is absent. Filter only after every page is read.
3. Build the applicable set: include every tag with `scope.type: Tenant`; include a tag with
  `scope.type: Domain` only when its `scope.domainId` matches the workspace's current domain.
4. Match each suggested tag name against the applicable set's `displayName` values
  (case-insensitive, trimmed). Do not resolve by name alone: the same name can exist in
  different domains.
5. Collect the matched `id` values into the `applyTags` request array.
6. If the name exists only in another domain, report it as **not applicable to this workspace**
  and exclude it. If it does not exist at all, say the appropriate Fabric
  or domain admin would need to create it.

## Choosing candidate tags

Draw candidates from a few consistent facets (use only what the content supports):

| Facet | Examples |
|-------|----------|
| Data domain | `Sales`, `Finance`, `HR`, `Marketing` |
| Subject area | `Customer`, `Product`, `Orders`, `Inventory` |
| Lifecycle / trust | `Certified`, `Curated`, `Raw`, `Deprecated` |
| Sensitivity theme | `PII`, `Confidential` *(a tag is not a sensitivity label — see api-reference.md)* |

Prefer 2–5 high-signal tags over many low-signal ones. Reuse the applicable tenant or domain
vocabulary.

## Guardrails

- Never fabricate tag IDs. Only send IDs returned by `GET /v1/tags`.
- Never newly apply a domain tag outside its `scope.domainId`. An already-applied domain tag may
  remain after a workspace moves domains; preserve and report it unless the owner explicitly
  asks to remove it. Once removed, it cannot be reapplied outside its domain.
- A tag is a **suggestion the owner accepts or rejects** — there is no free-text editing of a
  tag (unlike description / display name). Only accepted tags go into the `applyTags` array.
- A tag named `Confidential` is **not** the same as a sensitivity label; do not imply
  protection was applied (a sensitivity label can't be set here).
- Respect the 25 requests/minute limit on `applyTags` and the maximum of 10 tags per item.
