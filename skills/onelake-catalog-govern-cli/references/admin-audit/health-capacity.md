# Capacity Health — State, Ownership and Domain Alignment

> **Read this when:** Auditing capacities, and the hard limits on what "capacity health" can mean without a utilization API.

Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

> **Reporting template.** Don't stop at counts — report each applicable finding as **finding → evidence → why it matters → recommended action → priority → effort**, and state clean/pass results explicitly ("checked, no gap"). Priority tracks **blast radius × compounding signals**; effort must say whether a tenant admin can fix it or must **escalate**. Canonical definition: the shared Deliverable Contract.
## Capacity Health (Listing, State and Ownership)

Capacity problems surface as governance problems: content on a suspended capacity is inaccessible regardless of how well it is labelled or assigned.

### ⚠️ There is no capacity utilization API — do not claim "overloaded"

Live-verified **404** on every candidate: `/v1/admin/capacities/{id}/utilization`, `/{id}/throttling`, `/v1/capacities/{id}/metrics`, `/v1.0/myorg/admin/capacities/{id}/metrics`, `/{id}/usage`.

**CU consumption, throttling, overload and carry-forward are not exposed by any REST API.** They live in the **Microsoft Fabric Capacity Metrics app** (a semantic model). If asked whether a capacity is overloaded:

1. Say plainly that overload **cannot be determined** through the admin APIs.
2. Direct the user to the Capacity Metrics app.
3. Offer the **proxies below** — and label them as proxies, not utilization.

Never infer overload from workspace counts, item counts, or SKU size. A 165-workspace F2 may be idle; a 1-workspace F2048 may be throttled.

### Listing capacities — two endpoints, neither complete

| Endpoint | Verified count | Returns |
|---|---|---|
| `GET /v1.0/myorg/admin/capacities` (Power BI audience) | **59** | `id, displayName, sku, state, region, admins[], users[]` |
| `GET /v1/capacities` (Fabric core) | **54** | `id, displayName, sku, state, region` — **no `admins`**, and a strict subset |

Prefer the **admin** endpoint: it is the superset and the only one returning ownership.

> ### ⚠️ 36% of workspaces referenced a capacity that neither endpoint returns
> Live-verified: **383 of 1,065** active workspaces carried a `capacityId` absent from **both** lists (union = 59, unchanged). The single largest capacity by workspace count — **165 workspaces** — was invisible, and fetching it directly returned **401**, not 404.
>
> These are real, running capacities (internal, trial, or otherwise not admin-visible). A naive join therefore **silently drops a third of the tenant**.
>
> **Always** bucket workspaces whose `capacityId` does not resolve into an explicit **"capacity not resolvable"** group and report its size. Never drop them, and never report per-capacity percentages without stating the unresolved count.

### Health checks that *are* possible

Report each with **priority** and **effort**. ⚠️ Capacity admins and scale live in the **Azure portal / Power BI admin portal**, not the Fabric governance APIs — most fixes here are *not* Fabric-API remediations.

| Check | Test | Live-verified result | Priority | Effort |
|---|---|---|---|---|
| **Suspended capacity holding content** | `state == 'Suspended'` with assigned workspaces | **1 capacity, 156 workspaces.** The highest-severity capacity finding — that content is inaccessible now. | **Critical** — active content is unreachable | Resume the capacity or reassign its workspaces (Azure portal) |
| **Capacity being deleted** | `state == 'Deleting'` | 3 capacities. Check for assigned workspaces urgently. | **High** — urgent if it holds workspaces | Reassign workspaces before deletion completes |
| **Ownerless capacity** | `admins` empty | 1 capacity. Nobody can manage scale or assignment. | **Medium** | Assign a capacity admin (Azure portal — no Fabric API) |
| **Single-admin capacity** | `admins.Count == 1` | **53 of 59 (90%)** — same bus-factor pattern as workspaces. | **Medium** — bus factor | Add a second capacity admin (Azure portal) |
| **Empty capacity** | 0 active workspaces assigned | **15 of 59.** A cost finding, not a governance failure — report it as such. | **Low** — cost, not governance | Human keep/delete decision — never auto-recommend deletion |
| **Workspace with no capacity** | `capacityId` null | 1 workspace. | **Medium** | Assign to a capacity (remediate skill) |

**Clean/pass:** state clean areas explicitly — e.g. "0 of 59 capacities suspended — no availability risk found."

```powershell
$caps = (Invoke-RestMethod -Uri "https://api.powerbi.com/v1.0/myorg/admin/capacities" -Headers $pbiHeaders).value
$caps | Group-Object state
$caps | Where-Object { -not $_.admins -or $_.admins.Count -eq 0 } | Select-Object id, displayName, sku
```

State values seen live: `Active`, `Suspended`, `Deleting`. Treat any unlisted value as unknown rather than assuming it is healthy.

### Proxies for capacity pressure — and their limits

`GET /v1.0/myorg/admin/capacities/refreshables?$expand=capacity,group` returns per-model `refreshSchedule`, `configuredBy`, `capacity`, and last-refresh status.

**Live-verified: 12 of 87 refreshables had a failed last refresh — but every failure was a *data-source* error** (missing tables, duplicate keys), not capacity throttling.

> **Refresh failure is not evidence of capacity pressure.** Inspect `serviceExceptionJson`. Only capacity-related codes are a pressure signal; data-source and model errors are unrelated. Reporting a raw failure count as a capacity finding is a fabricated correlation.

`GET /v1.0/myorg/admin/capacities/{id}/workloads` returns `maxMemoryPercentageSetByUser` — **configuration, not consumption**. A workload capped at 0% is a settings finding, never a utilization reading.

---
## Domain-Capacity Alignment

Fabric domains can be associated with specific capacities for policy enforcement. Compare each workspace's `capacityId` (from List All Tenant Workspaces) against the capacities associated with its assigned `domainId` (see repository `common/COMMON-CORE.md` § Capacity Management for listing capacities) to catch workspaces running on out-of-policy capacity for their domain.

---


## Gotchas — Capacity Health

| Symptom | Cause / verified reality | Fix |
|---|---|---|
| Reporting a capacity as "overloaded" or near its CU limit | **No API exposes utilization** — verified 404 on `/utilization`, `/throttling`, `/metrics`, `/usage`. | Say it cannot be assessed and point to the Fabric Capacity Metrics app. |
| Per-capacity percentages that don't add up to the workspace total | **383 of 1,065 workspaces (36%)** referenced a capacity absent from both capacity endpoints. | Add an explicit "capacity not resolvable" bucket rather than dropping them. |
| `GET /v1/admin/capacities` returns 404 | That route does not exist. | Use `GET /v1.0/myorg/admin/capacities` (Power BI audience) — a superset of core `/v1/capacities` and the only one returning `admins`. |
| Fetching a capacity by ID returns 401, not 404 | The capacity exists but is not admin-visible. | Treat as unresolvable, not absent. |
| Refresh failures reported as capacity pressure | Verified: all 12 failures in the test tenant were **data-source** errors. | Inspect `serviceExceptionJson` before attributing anything to capacity. |
