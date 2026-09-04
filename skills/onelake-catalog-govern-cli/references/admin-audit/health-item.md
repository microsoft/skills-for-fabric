# Item Health — Ownership, Item Identity and Staleness


## Contents

- [Item Health (Ownership and Staleness)](#item-health-ownership-and-staleness)
- [Gotchas — Item Health](#gotchas-item-health)

> **Read this when:** Deciding who owns an item, whether it is abandoned, and whether it is still refreshing on schedule — without manufacturing false findings.

Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

> **Reporting template.** Don't stop at counts — report each applicable finding as **finding → evidence → why it matters → recommended action → priority → effort**, and state clean/pass results explicitly ("checked, no gap"). Priority tracks **blast radius × compounding signals**; effort must say whether a tenant admin can fix it or must **escalate**. Canonical definition: the shared Deliverable Contract.
## Item Health (Ownership and Staleness)

Two questions, both answerable from `/v1/admin/items` — but the ownership one has a trap that produces confident false accusations.

### Item creator — coverage and the type lie

`/v1/admin/items` returns `creatorPrincipal` with `{id, displayName, type, userDetails.userPrincipalName}`.

**Live-verified: 14,772 of 14,978 items (98.6%) carry a creator.** The **206** without one were legacy Power BI types — `Dashboard` (141), `App` (27), plus a few `Eventhouse`/`Eventstream`/`Report`. Report these as **"creator unknown"**, never as ownerless.

> ### ⚠️ `creatorPrincipal.type` is always `"User"` — even for service principals
> Live-verified: **all 14,772** items reported `type: "User"`, yet resolving the 25 distinct creators against Microsoft Graph showed **9 were service principals** (131 items).
>
> **Do not trust `creatorPrincipal.type`.** It cannot distinguish a person from automation, so it cannot answer "does this item have a human owner?" on its own.
>
> Where `defaultIdentity` exists (below), **it reports the type correctly** — use it in preference. Live-verified on 16 items: same principal `id`, `creatorPrincipal.type: "User"` but `defaultIdentity.type: "ServicePrincipal"`. That is the same principal described correctly by one field and incorrectly by the other.

### Item Identity: the Effective Owner (Preview)

Fabric is replacing the implicit "item owner is whoever created it" dependency with an **associated identity** — `defaultIdentity` — so items stop breaking when a person leaves. ([Learn](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/associate-item-identity))

**This is the ownership field. `creatorPrincipal` is history — `defaultIdentity` is authority.** Where both exist, report `defaultIdentity`.

Request it explicitly with `include=defaultIdentity`; it is **omitted by default**:

```bash
# Tenant-wide, one paginated sweep — live-verified, works on the admin route
az rest --method GET --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/admin/items?include=defaultIdentity" \
| jq -r '.itemEntities[] | select(.defaultIdentity)
         | [.type, .name, .defaultIdentity.type,
            (.defaultIdentity.userDetails.userPrincipalName
             // .defaultIdentity.servicePrincipalDetails.aadAppId)] | @tsv'
```

Both tiers support it — live-verified: `/v1/admin/items`, `/v1/admin/workspaces/{ws}/items/{id}`, and the core `/v1/workspaces/{ws}/items`.

| Identity type | Contact field |
|---|---|
| `User` | `defaultIdentity.userDetails.userPrincipalName` |
| `ServicePrincipal` | `defaultIdentity.servicePrincipalDetails.aadAppId` (no human — escalate to workspace admins) |

> ### ⚠️ Coverage is 3.9% — do not report it as an ownership gap
> Live-verified: **588 of 14,941 items** carry a `defaultIdentity`. The other 96% are **not "missing an owner"** — their item type does not support the feature yet. Reporting them as ownerless would manufacture ~14,000 false findings.
>
> Supported types observed live: **Lakehouse (382), DataPipeline (107), Eventstream (49), Homeone (24), CopyJob (15), UserDataFunction (11)**.
>
> Learn currently lists only **Lakehouse and Eventstream** — the live surface is already wider. **Detect supported types by probing** (`select(.defaultIdentity)`), never from a hard-coded list, and re-check rather than trusting either source.

Two further cautions:

- **Divergence is the signal, and it is currently zero.** In the verified tenant **0 of 588** items had a `defaultIdentity` differing from `creatorPrincipal` — nobody has reassigned yet. So today it adds no *new* ownership information in this tenant; it becomes load-bearing the moment a takeover happens. Do not conclude the field is redundant.
- It is **preview** (`?beta=true` on the write path). Tag findings accordingly.

### ⚠️ Detecting departed owners — the trap that manufactures findings

The natural check — "creator no longer resolves in Entra ⇒ they left the org" — is **wrong**, and wrong in the direction that generates false positives.

Live-verified on 25 distinct creators:

| Method | Unresolvable | Reality |
|---|---|---|
| `getByIds` with `types: ['user']` | **11 principals / ~206 items** | **9 were live service principals**, not departed people |
| `getByIds` with **no type filter** | **2 principals** | A `#EXT#` guest (`GitIntegration1`) and a system principal (`Admin Monitoring`) |

**Genuine departed-user orphans in the verified tenant: zero. The naive check reports eleven.**

Mandatory procedure:

0. **Check `defaultIdentity` first.** For the ~4% of items that have one, it answers the ownership question directly and correctly — including whether the owner is a service principal. Only fall through to creator-resolution for items without it.
1. Resolve creators with `POST https://graph.microsoft.com/v1.0/directoryObjects/getByIds` and **no `types` filter** — the filter is what causes service principals to look like deleted users.
2. Classify what came back by `@odata.type`: `#microsoft.graph.user` vs. `#microsoft.graph.servicePrincipal`.
3. Only a principal unresolvable **without** a type filter is a candidate.
4. Before reporting, exclude **guest (`#EXT#`)** and **system** principals, then check `accountEnabled` on resolved users — a disabled account is a departure the directory still returns.
5. Report survivors as **"creator no longer resolvable — verify with IAM"**, never as "employee left the organisation."

Requires Microsoft Graph (`Directory.Read.All`). If Graph is unavailable, say ownership **could not be assessed** — do not substitute the unreliable `type` field.

> **Creator is not owner.** The creator may have left while the workspace remains well-administered. Always report creator-orphaned items **alongside** the workspace's admin list (Find Workspace Admin Gaps). An item whose creator is gone but whose workspace has two active admins is **not** an ownership gap.

Semantic models expose a second, independent owner via `configuredBy` on `GET /v1.0/myorg/admin/capacities/refreshables` — useful for refresh ownership specifically.

### Stale / unused items

`lastUpdatedDate` is the only per-item time signal `/v1/admin/items` returns.

```bash
jq -r --arg cut "$(date -u -d '180 days ago' +%Y-%m-%d)" \
  '[.[] | select(.lastUpdatedDate < $cut)] | group_by(.type)
   | map({type: .[0].type, stale: length}) | .[]' /tmp/all_items.json
```

Three limits to state whenever you use it:

1. It records **modification, not use.** A certified reference dataset that is read daily and never edited looks stale. Cross-check with activity events before calling anything unused.
2. It is **not** a refresh timestamp. For semantic models use the refresh history API (see Data freshness (refresh state) below).
3. Thresholds are policy, not fact. Print the cut-off you applied and never delete on this signal alone.

### Data freshness (refresh state)

> **Freshness is a Health signal in this skill.** "Is this item actively refreshing?" is a data-estate/currency question, so it is audited here rather than under Trust. This is a **deliberate divergence from the product's Govern tab**, which lists data freshness under *Discover, trust & reuse* — see `govern-pillars.md` § Pillar 1.

`lastUpdatedDate` (above) is **modification** time, not refresh time — and the Power BI scanner API does **not** return refresh state either. For semantic models, use the Power BI refresh history API per model:

```bash
az rest --resource https://analysis.windows.net/powerbi/api \
  --url "https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes?\$top=1"
```

Flag items whose latest refresh `status != "Completed"` or whose `endTime` is older than the expected cadence. Refresh **ownership** (who configured it) comes from `configuredBy` on `GET /v1.0/myorg/admin/capacities/refreshables` — pair it with the finding so it can be routed.

> **Cross-pillar (Health × Trust).** Intersect the stale/failed-refresh set with the **endorsed** set (trust-curation.md) — a *certified but stale* item (authoritative content serving out-of-date data) is a higher-priority finding than either signal alone. Surface these first.

### Reporting

Report each finding as **finding → evidence → why it matters → recommended action → priority → effort**, and rank by **combination** — any single signal is weak. ⚠️ Almost nothing here is admin-fixable: the tenant admin can *find* these but has **no item write route** (see the warning below), so **effort is almost always "escalate"**.

- **Stale + creator unresolvable + workspace has one admin** — the strongest orphan candidate. **Priority: High.** **Effort: escalate** — name the workspace admins/creator; the admin cannot delete or reassign it directly.
- **Stale + active workspace + multiple admins** — likely a stable asset. **Not a finding** — report as clean/pass, not as a risk.
- **Creator is a service principal** — report separately. Automation-created content has no human owner *by design*; it needs a documented owner, not an orphan flag. **Priority: Low–Medium.** **Effort: escalate** — assign a documented owner.
- **Has a `defaultIdentity` pointing at a departed/disabled user** — the highest-confidence ownership finding available, and the only one with a supported API fix. **Priority: High.** **Effort: medium** — route it to someone with Write on the item, who can reassign via the assign API (see remediate skill).
- **Endorsed + stale/failed refresh** — a Promoted/Certified item whose latest refresh failed or is past its cadence. The worst case in the estate: authoritative content serving out-of-date data. **Priority: High.** **Effort: escalate** — a refresh needs workspace/dataset rights, not tenant admin; a Fabric-native model has no refresh API at all (see remediate skill).

**Clean/pass:** when a checked signal is clean (e.g. "0 items with an unresolvable creator after excluding SPNs and guests"), say so explicitly so the reader knows ownership was assessed, not skipped.

> ### ⚠️ You are finding items you cannot delete
> Live-verified: there is **no admin-tier item write route** (`DELETE /v1/admin/items/{id}` → **404**), and the core route requires **workspace Contributor or above** — a tenant admin who is not a workspace member got **401** on even `GET /v1/workspaces/{id}/items`.
>
> So never close a stale/unused item finding with "delete these." Every such finding must ship with **who can act on it**: the workspace admins (`GET /v1/admin/workspaces/{id}/users`, filter `workspaceRole == "Admin"` — includes `userPrincipalName`) and the item creator. The remediate skill has the full procedure in § Route a Finding to Someone Who Can Fix It.
>
> Note also that `GET /v1/admin/items/{id}/users` returns **404** — there is no per-item permission list at admin tier. Workspace access is the finest granularity you can report.

---

## Gotchas — Item Health

| Symptom | Cause / verified reality | Fix |
|---|---|---|
| Item creator shows `type: "User"` but is automation | **`creatorPrincipal.type` is always `User`** — 9 of 25 verified creators were service principals. | Resolve against Graph to determine the real type. |
| Items flagged as "owner left the organisation" | Almost certainly false. `getByIds` with `types:['user']` produced **11 false positives vs. 0 real orphans**. | Query **without** a type filter, then exclude SPNs, `#EXT#` guests and system principals. |
| Items with no `creatorPrincipal` at all | 206 verified, nearly all legacy `Dashboard`/`App`. | Report as **"creator unknown"**, not ownerless. |
| Reported stale/unused items as "delete these" | The tenant admin has **no item delete route** — `DELETE /v1/admin/items/{id}` is **404**, and the core route needs workspace Contributor+ (`401` for a non-member tenant admin). | Name the workspace admins and creator instead — see remediate § Route a Finding to Someone Who Can Fix It. |
| `GET /v1/admin/items/{id}/users` returns 404 | **The route does not exist** — no per-item permission list at admin tier. | Use `GET /v1/admin/workspaces/{id}/users` and state you are reporting *workspace* access, not item access. |
| `defaultIdentity` missing from every item | It is **omitted by default**. | Pass `?include=defaultIdentity`. If still absent, the item **type** does not support item identity (only ~4% do) — that is not an ownership gap. |
| Reporting ~96% of items as "no owner assigned" | You treated absent `defaultIdentity` as a finding. Live-verified only **588 of 14,941** items support it. | Report coverage only across **supported types**, detected by probing for the field. |
| `creatorPrincipal.type` and `defaultIdentity.type` disagree | **`defaultIdentity` is right.** Live-verified on 16 items: identical principal `id`, creator said `User`, identity said `ServicePrincipal`. | Always prefer `defaultIdentity.type` where present. |
