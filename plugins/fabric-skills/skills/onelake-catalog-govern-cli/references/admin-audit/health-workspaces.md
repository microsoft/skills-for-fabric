# Workspace Health — Unused Workspaces and Admin Gaps


## Contents

- [Find Unused Workspaces (Empty vs. Inactive)](#find-unused-workspaces-empty-vs-inactive)
- [Find Workspace Admin Gaps (Bus Factor and Policy Thresholds)](#find-workspace-admin-gaps-bus-factor-and-policy-thresholds)
- [Gotchas — Workspace Health](#gotchas-workspace-health)

> **Read this when:** Deciding whether a workspace is genuinely abandoned, and whether it has enough admins to survive one person leaving.

 Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

> ### ⚠️ Scope — tenant-wide, via the Admin API
> Enumerate the estate with `GET /v1/admin/workspaces?type=Workspace&state=Active` and filter by `name` (the Admin object uses `name`, not `displayName`). **Do NOT** use the user-scoped Core `GET /v1/workspaces` for inventory — it returns only workspaces the caller has a role on and under-reports the tenant even for an admin. State the scope in your answer; if the Admin API returns `403` and you fall back to Core, label the result as user-scoped, not tenant-wide.

---

 > **Reporting template.** Don't stop at counts — report each applicable finding as **finding → evidence → why it matters → recommended action → priority → effort**, and state clean/pass results explicitly ("checked, no gap"). Priority tracks **blast radius × compounding signals**; effort must say whether a tenant admin can fix it or must **escalate**. Canonical definition: the shared Deliverable Contract.
## Find Unused Workspaces (Empty vs. Inactive)

"Unused" is **two different findings with two different costs**. Never conflate them, and never report one as the other.

| Finding | Means | Source | Cost |
|---|---|---|---|
| **Empty** | Contains zero items | `/v1/admin/items`, already fetched | Free |
| **Inactive** | Nobody has *done* anything in it | Activity Events API | Expensive — one call per day over the retention window |

### Empty workspaces (zero items) — cheap, always do this

Reuse the item inventory you already fetched. Group items by `workspaceId`, then find active workspaces with no entry:

```bash
jq -r --slurpfile ws /tmp/active_workspaces.json '
  [.[] | .workspaceId] | unique as $withItems
  | $ws[0] | map(select(.id as $i | ($withItems | index($i)) | not))
  | map({id, name, capacityId, domainId}) | .[]' /tmp/all_items.json
```

> **Empty-but-assigned matters most.** A domain containing empty workspaces reports healthy assignment coverage while delivering nothing discoverable. Always report *empty-but-assigned* separately — it is the case where the health metric and reality diverge.

### ⚠️ Empty does not mean unused

An empty workspace can still be actively worked in — items created and deleted, shortcuts rewritten, queries run — and show zero items at the moment you sample it. Recommending deletion on an item count of zero can destroy a workspace in active use.

State the item count as what it is — **an inventory fact, not a usage verdict**.

### Prove item coverage before calling a workspace empty

"Empty" is a claim about the *whole* Fabric estate of a workspace, so it is only as trustworthy as the inventory behind it. An emptiness verdict from a partial inventory is worse than no verdict — it invites deletion.

- **Use an all-Fabric item inventory, and page it fully.** `GET /v1/admin/items` returns a server-provided `continuationUri`; follow it until it is empty. A truncated first page makes populated workspaces look empty. When drilling into a specific candidate, scope with `GET /v1/admin/items?workspaceId={id}` — but page every response to exhaustion before trusting a zero count.
- **Never infer emptiness from Power BI-only results.** The Power BI scanner (`getInfo`) and the Power BI-audience APIs enumerate *Power BI* artifacts, not the full Fabric item set (lakehouses, notebooks, data pipelines, KQL databases, eventstreams, …). A workspace can return zero Power BI artifacts and still hold Fabric items. Determine emptiness only from the all-Fabric `/v1/admin/items` inventory — the same one this skill already fetches — not from a scanner result.
- **If coverage cannot be proven, report `unknown`, not `empty`.** If any page failed, an item type was excluded, or the inventory was Power BI-scoped, you have not proven zero items. Report the workspace as **coverage unknown** and state what was missing — do not fold it into the empty count.

> ### ⚠️ `empty` and `unknown` are different verdicts
> `empty` = a fully-paged, all-Fabric inventory returned zero items. `unknown` = coverage could not be proven. Only `empty` (plus inactive + unassigned) is ever a deletion candidate. An `unknown` workspace reported as `empty` is exactly how a live workspace gets deleted.

### Inactive workspaces (no activity) — expensive, and easy to get wrong

`GET /v1.0/myorg/admin/activityevents` (Power BI audience) returns `WorkspaceId`, `Operation`, `UserId`, `CreationTime`.

```powershell
$d = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd')
$u = "https://api.powerbi.com/v1.0/myorg/admin/activityevents?startDateTime='${d}T00:00:00'&endDateTime='${d}T23:59:59'"
$r = Invoke-RestMethod -Uri $u -Headers @{Authorization="Bearer $pbiToken"}
$ev = @($r.activityEventEntities)
while ($r.continuationUri) { $r = Invoke-RestMethod -Uri $r.continuationUri -Headers @{Authorization="Bearer $pbiToken"}; $ev += @($r.activityEventEntities) }
```

API constraints — all four change how you must scope the question:

1. **One day per call.** A multi-day range is **rejected**, not truncated. A 28-day look-back is 28 paginated calls.
2. **Retention is ~28 days.** `-27` days succeeded; `-28` and beyond were rejected. You **cannot** answer "unused for 90 days" with this API. Say so rather than substituting a shorter window silently.
3. **Volume is large.** A single day can return hundreds of thousands of events. Budget for pagination, not a single request.
4. **Absence of events is not proof of disuse.** The window is short and only covers audited operations.

> ### ⚠️ Never call a workspace inactive from a one-day sample
> Most workspaces show no activity on any given day — that does not make them unused. A one-day window mislabels the majority of the tenant as unused, confidently and wrongly.
>
> Use the **full available window** (~28 days) or report no inactivity finding at all. If the cost is not acceptable, report the empty-workspace count and state explicitly that inactivity was **not assessed**.

### Reporting

Report empty and inactive as separate lines, then intersect them:

- **Empty + inactive + unassigned** — the only combination that is a genuine deletion candidate.
- **Empty + recent activity** — a *new or transient* workspace. Not a finding.
- **Has items + inactive** — possible abandonment, but check freshness (see Data freshness (refresh state)) before saying so; a certified, never-changing reference dataset is *supposed* to look inactive.

Deletion is never an automatic recommendation. Surface candidates for a human decision.

> ### ⚠️ Check dependencies before proposing removal — and never unassign silently
> A workspace empty of items can still be a dependency of something else: assigned to a **deployment pipeline** stage, targeted by shortcuts, or bound to a capacity or domain. Treat those assignments as **separate findings**, report them alongside the deletion candidate, and **never unassign or delete a pipeline assignment (or any dependency) without explicit confirmation**. Emptiness is a fact about item count; it says nothing about what points *at* the workspace.

---
## Find Workspace Admin Gaps (Bus Factor and Policy Thresholds)

Domain ownership (above) and **workspace** ownership are different checks against different endpoints. A tenant can have perfectly owned domains and still have thousands of single-admin workspaces.

### Getting workspace roles

Two paths — the choice matters at tenant scale:

| Path | Endpoint | Returns | Cost |
|---|---|---|---|
| Per-workspace | `GET /v1/admin/workspaces/{id}/users` | `principal{id,displayName,type}`, `workspaceAccessDetails.workspaceRole` | **One call per workspace** — do not do this tenant-wide |
| **Bulk (preferred)** | `POST /v1.0/myorg/admin/workspaces/getInfo?getArtifactUsers=True` | `users[]` with `groupUserAccessRight`, `principalType`, `graphId`, `emailAddress` | **~1 scan per 100 workspaces** |

Use the per-workspace call only to drill into a specific finding. The bulk path uses the same async 3-call scan flow as Labels, descriptions, and endorsement, so fetch users and curation metadata in the **same** scan rather than scanning twice.

Role values differ between the two APIs — `workspaceRole` (`Admin`/`Member`/`Contributor`/`Viewer`) vs. `groupUserAccessRight` (same values). Normalise before comparing.

### ⚠️ "Workspace with no admin" is the wrong thing to look for

**Fabric will not leave a workspace adminless**, so a zero-admin check reliably returns nothing and creates false confidence that ownership was assessed.

The real finding is not *absent* ownership, it is **concentrated** ownership — in most tenants a large share of workspaces have a single admin, leaving them one departure away from being orphaned. Lead with that.

### Gaps to report

Report each with **priority** (blast radius × compounding signals) and **effort** (can a tenant admin fix it, or must it be escalated?). Workspace-role gaps are **not admin-fixable at scale** — see the warning below.

| Gap | Test | Why it matters | Priority | Effort |
|---|---|---|---|---|
| **Single admin (bus factor)** | `Admin` count `== 1` | The dominant real-world risk — typically the largest ownership gap in a tenant. | **High** — one departure from an orphaned workspace | **Escalate — not admin-fixable.** No admin-scoped write for workspace roles; each needs a workspace admin to act, or a portal takeover |
| **No *human* admin** | Zero admins of `principalType == 'User'` | The true analogue of "ownerless": administered only by a service principal or group — invisible to a plain admin count, which reports it as owned. | **High** — no accountable person at all | **Escalate** — same constraint; add a human admin via a workspace admin/portal |
| **Policy threshold violation** | `Admin` count `< N` (tenant policy, e.g. `N = 2`) | Configurable. Always print the threshold you applied. | **Medium–High** (depends on `N`) | **Escalate at scale** — one ask per workspace admin |
| **Zero admins** | `Admin` count `== 0` | Does not normally occur. If it ever does, treat as a **critical anomaly**, not a routine gap. | **Critical if ever seen** | Investigate as an anomaly — not a routine remediation |

**Clean/pass:** if the tenant's admin distribution meets the policy threshold, say so explicitly — e.g. "all workspaces have ≥ 2 admins — no bus-factor remediation needed."

> ### ⚠️ This finding cannot be remediated at scale — say so when you report it
> There is **no admin-scoped write** for workspace roles. `POST /v1/admin/workspaces/{id}/roleAssignments` returns **404** (the admin route is read-only), and the core write route returns **403** to a tenant admin because it requires the **workspace Admin** role.
>
> So a tenant admin can *find* single-admin workspaces and fix **none** of them directly. Remediation means asking each workspace admin to act, or taking over workspaces in the portal — an auditable permission change, not a silent cleanup. Report the finding with that constraint attached, or you hand someone a long list with no viable action.

### ⚠️ Group admins break naive counting — state this caveat

A security group counts as **one** principal but may contain many people.

- A workspace with one group admin containing 10 people is **not** a bus-factor risk, but a principal count reports it as `1`.
- The reverse also holds: a group with one member reports as `1` and *is* a risk.

The admin APIs return the group principal, **not its membership** — resolving it requires Microsoft Graph, which is outside this skill. Therefore:

> When any admin is a `Group`, report the workspace as **"1 admin (group — membership not resolved)"** rather than asserting a bus-factor risk. Give the count *and* its uncertainty. Reporting single-admin workspaces without noting that some are group-backed overstates the finding.

Count `ServicePrincipal` / `App` admins separately too: they satisfy a `>= 2` policy numerically while adding **no** human accountability. A policy check that counts SPNs toward the threshold can be passed by automation alone.

---

## Gotchas — Workspace Health

| Symptom | Cause | Fix |
|---|---|---|
| Workspace list is far shorter than the portal / undercounts the tenant | Used the **user-scoped** Core `GET /v1/workspaces` — returns only workspaces the admin has a role on. | Use `GET /v1/admin/workspaces?type=Workspace&state=Active`; only fall back to Core on a `403`, and label that result as user-scoped. |
| Answer doesn't say whether it's tenant-wide or "my" workspaces | Scope was left implicit; an admin expects tenant scope by default. | State endpoint + scope up front (tenant-wide, Admin API). |
| Recommending deletion because a workspace has 0 items | **Empty is not unused** — an empty workspace can have activity the same day. | Check activity before ever suggesting deletion. |
| "Unused workspace" report based on 1 day of activity events | Most workspaces show no activity on any single day — a 1-day window mislabels the majority of the tenant. | Use the full ~28-day window, or report no inactivity finding. |
| `activityevents` returns an error for a multi-day range | **One day per call, by design.** Multi-day ranges are rejected, not truncated. | Loop day by day. |
| "Unused for the last 90 days" cannot be answered | Retention is **~28 days** (`-27` OK, `-28` rejected). | Say the window is unavailable rather than silently answering for a shorter period. |
| Zero-admin workspace check returns nothing | **Expected.** Fabric does not leave workspaces adminless. | Report **single-admin** and **no-human-admin** instead. |
| Admin count of 1 reported as bus-factor risk | A **Group** admin may contain many people; membership is not resolvable from these APIs. | Check `principalType` first; report "1 admin (group — membership not resolved)". |
| Workspace passes a `>= 2` admin policy but has no human owner | Service principals count numerically toward the threshold. | Count human admins separately. |
| Calling `/v1/admin/workspaces/{id}/users` for every workspace | One call per workspace — does not scale tenant-wide. | Use the scanner API (`getInfo?getArtifactUsers=True`) — 100 workspaces per scan — and combine it with the curation-metadata scan. |
| Emptiness verdict came from the Power BI scanner / `getInfo` scan | Those enumerate **Power BI artifacts only** — Fabric items (lakehouses, notebooks, pipelines, KQL DBs, …) are invisible to them, so populated workspaces look empty. | Determine emptiness only from a fully-paged all-Fabric `/v1/admin/items` inventory. |
| Populated workspace reported as empty | The `/v1/admin/items` response was **not paged to exhaustion** — a truncated first page drops items. | Follow each response's `continuationUri` to the end before trusting a zero count; otherwise report **coverage unknown**, not empty. |
| Empty workspace deleted despite being in use elsewhere | It was assigned to a **deployment pipeline** stage or another dependency; item count says nothing about what references it. | Report dependencies as separate findings; never unassign/delete without explicit confirmation. |
