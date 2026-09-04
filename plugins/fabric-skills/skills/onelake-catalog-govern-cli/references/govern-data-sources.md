# Governance Data Sources and Reporting

Use this leaf reference to select the correct API surface, state product blind spots, and format findings.

## Programmatic Data Sources (verified)

The Fabric Admin API and the Power BI Admin *scanner* API cover different pillars. Choosing the wrong one is the most common mistake.

| Need | Endpoint | Verified response fields |
|---|---|---|
| Domain inventory | `GET /v1/admin/domains?preview=false` | `id`, `displayName`, `description`, `parentDomainId`, `defaultLabelId` — null fields are **omitted** |
| Workspace inventory (health) | `GET /v1/admin/workspaces?type=Workspace` | `id`, `name`, `state`, `capacityId`, `domainId` (absent when unassigned), `tags[]` |
| Workspaces in a domain | `GET /v1/admin/domains/{id}/workspaces` | `id`, `displayName` |
| Item inventory (health and all-Fabric curation) | `GET /v1/admin/items` | `id`, `type`, `name`, `description`, `tags[]`, `state`, `lastUpdatedDate`, `creatorPrincipal`, `workspaceId`, `capacityId`, `childItems` |
| Item **effective owner** (preview) | `GET /v1/admin/items?include=defaultIdentity` — also on `/v1/admin/workspaces/{ws}/items/{id}` and core `/v1/workspaces/{ws}/items` | `defaultIdentity` `{id, displayName, type, userDetails.userPrincipalName \| servicePrincipalDetails.aadAppId}`. **Omitted unless `include` is passed.** Live-verified **588 of 14,941 items (3.9%)** — Lakehouse, DataPipeline, Eventstream, Homeone, CopyJob, UserDataFunction. Unlike `creatorPrincipal.type`, **its `type` is accurate** |
| **Workspace roles / admins** | Power BI scanner — `POST /v1.0/myorg/admin/workspaces/getInfo?getArtifactUsers=True` | `users[]` with `groupUserAccessRight`, `principalType`, `graphId`, `emailAddress`. **100 workspaces per scan** — prefer over per-workspace calls |
| Workspace roles (single workspace) | `GET /v1/admin/workspaces/{id}/users` | `principal{id,displayName,type}`, `workspaceAccessDetails.workspaceRole`. Use only for drill-down — one call per workspace |
| **Capacity inventory + ownership** | `GET /v1.0/myorg/admin/capacities` (Power BI audience) | `id`, `displayName`, `sku`, `state`, `region`, `admins[]`, `users[]`. **`GET /v1/admin/capacities` does not exist (404)** |
| Capacity inventory (core, subset) | `GET /v1/capacities` | `id`, `displayName`, `sku`, `state`, `region` — **no `admins`**, and a strict subset of the admin list |
| **Workspace/item activity** | `GET /v1.0/myorg/admin/activityevents` | `WorkspaceId`, `Operation`, `UserId`, `CreationTime`. **One day per call; ~28-day retention; multi-day ranges are rejected** |
| Refresh ownership + last refresh | `GET /v1.0/myorg/admin/capacities/refreshables?$expand=capacity,group` | `configuredBy`, `refreshSchedule`, `capacity`, last-refresh status |
| **Resolving creators/admins to real identities** | Microsoft Graph `POST /v1.0/directoryObjects/getByIds` | Call with **no `types` filter**, then classify by `@odata.type`. Requires `Directory.Read.All` |
| Sensitivity labels and endorsement (Power BI artifact types only) | Power BI **scanner API** — `POST /v1.0/myorg/admin/workspaces/getInfo` | `sensitivityLabel.labelId`, `endorsementDetails`; state the scanned type denominator and mark unsupported Fabric-native types unassessed |
| Item **discovery** by name (not governance) | `POST /v1/catalog/search` | `id`, `type`, `displayName`, `description`, `catalogEntryType`, `hierarchy.workspace` |

> ⚠️ **`creatorPrincipal.type` is always `"User"`** — verified across 14,772 items, of which 131 were created by service principals. It cannot distinguish a person from automation. Resolve against Graph before making any ownership claim, and **never** report "the owner left the organisation" from a failed lookup alone.

> ⚠️ **No API exposes capacity utilization, CU consumption, throttling or overload.** Verified 404 on `/utilization`, `/throttling`, `/metrics` and `/usage` across both audiences. That data exists only in the Fabric Capacity Metrics app. State this rather than substituting a proxy — refresh failures in particular are usually data-source errors, not capacity pressure.

> ⚠️ **The capacity list is incomplete.** In a verified tenant, 36% of active workspaces referenced a `capacityId` absent from both capacity endpoints (direct fetch returned `401`, not `404`). Always report an explicit *"capacity not resolvable"* bucket instead of dropping those workspaces.

> ⚠️ **Catalog Search is not a governance data source.** It returns no sensitivity label, endorsement, `domainId`, or refresh state; it is **caller-scoped** (under-reports for tenant-wide audits) and its index lags up to 24 hours. Use it only to resolve a user-mentioned name into IDs. The one exception is **non-admin** description-coverage checks, where it is the only option — see `skills/onelake-catalog-govern-cli`.

> ⚠️ **`GET /v1/admin/items` does NOT return sensitivity labels or endorsement.** It does return descriptions and tags for all-Fabric curation coverage, plus `defaultIdentity` when explicitly requested. Use the Power BI scanner for label and endorsement metrics, and state its narrower artifact-type denominator.

### Scanner API essentials
- **Different token audience**: `https://analysis.windows.net/powerbi/api` (not `https://api.fabric.microsoft.com`).
- **Asynchronous, three-call flow**:
  1. `GET /v1.0/myorg/admin/workspaces/modified` → workspace IDs (optionally `?modifiedSince=`)
  2. `POST /v1.0/myorg/admin/workspaces/getInfo` with body `{ "workspaces": [ids] }` → returns a scan `id`
  3. Poll `GET /v1.0/myorg/admin/workspaces/scanStatus/{id}` until `Succeeded`, then `GET /v1.0/myorg/admin/workspaces/scanResult/{id}`
- **Batch limit**: 100 workspaces per `getInfo` call — chunk the ID list.
- **Optional detail flags** on `getInfo`: `lineage`, `datasourceDetails`, `getArtifactUsers`, `datasetSchema`, `datasetExpressions`. Each increases payload size and scan time — request only what the analysis needs.
- **Sparse fields**: `sensitivityLabel` returns only a `labelId` (a GUID) — resolve friendly names via Microsoft Purview, not this API. `endorsementDetails` is **absent entirely on unendorsed items** — treat "field missing" as "not endorsed", not as an error.
- **Refresh state is not in the scanner output** — use the Power BI refresh history APIs per semantic model for pillar-3 freshness analysis.

---

## Known Limitations of Govern-Tab-Derived Insight

These apply when reasoning about, or reproducing, the Govern tab's numbers:

- **Subitems (e.g., tables) are not supported** and never appear in insights.
- **No cross-tenant or guest-user support.**
- **Not available when Private Link is activated.**
- **Admin insights refresh once per day** — up to a 24-hour gap between reality and reported state. Data-owner insights refresh on tab open.
- **Third-party workload items are excluded** from the charts.
- The admin semantic model is **read-only** and **cannot be used with Fabric data agents**.
- **Never modify the autogenerated Govern report or its semantic model** — doing so breaks the Govern tab. To customize, copy the report or build a new one on the autogenerated semantic model.

---

## Reporting Conventions

When delivering a governance assessment, structure findings by pillar and always include:
1. **Denominator hygiene** — state totals and exclude `Deleted` workspaces; give percentages, not just counts.
2. **Named examples** — 10–15 sample item/workspace names, not an exhaustive dump; offer an export.
3. **Cross-pillar combinations first** — e.g., certified-but-stale, shared-but-unlabeled.
4. **Freshness caveat** — if the data derives from admin monitoring storage, note it may be up to a day old.
5. **Scope exclusions** — state what was excluded and why ("1,062 governable workspaces; excluded 1,141 deleted, 38 personal, 1 admin-monitoring"), so an admin reconciling against a raw API call doesn't think data is missing.
