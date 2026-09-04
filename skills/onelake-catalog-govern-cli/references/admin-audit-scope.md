# Admin Audit Scope and Blind Spots

Apply this leaf reference before computing any tenant-wide governance statistic.

## Scope Gate — Apply Before Any Statistic

Two server-side filters on `/v1/admin/workspaces`, both verified, both mandatory:

```
?type=Workspace&state=Active
```

Build this governable-workspace ID set **once**, reuse it for every pillar, and state what it excluded. In a verified tenant only **1,062 of 2,242 workspaces (47%) were governable** — an unfiltered audit overstates the estate by more than 2×, making every percentage roughly half its true value.

| Type | Active | Deleted |
|---|---|---|
| `Workspace` | **1,062** ← the only governable set | 1,133 |
| `Personal` (My workspace) | 38 | 3 |
| `AdminWorkspace` (Monitoring) | 1 | 5 |

Why each filter is load-bearing:

- **`state=Active`** — a deleted workspace cannot be assigned, relabeled, endorsed or refreshed. Any finding against one is unactionable and erodes trust in the whole report.
- **`type=Workspace`** — **verified: only `Workspace`-type ever carries a `domainId`** (all 141 domain-assigned workspaces in the test tenant were this type). `Personal` and `AdminWorkspace` are *structurally incapable* of domain assignment, so including them manufactures permanently-unfixable gaps. Telling an admin "39 workspaces are unassigned" when those are My-workspaces produces a remediation task that fails every time it is attempted.

> **Report the exclusion, don't just apply it:** *"1,062 governable workspaces (excluded: 1,141 deleted, 38 personal, 1 admin-monitoring)"* — so an admin reconciling against a raw API call doesn't think you lost data.

### List All Tenant Workspaces (Paginated)

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/admin/workspaces?type=Workspace&state=Active" \
  --resource "https://api.fabric.microsoft.com"
```

Each item includes `id`, `name`, `state`, `capacityId`, and `domainId` (absent/null when unassigned). Follow `continuationUri` until absent — see repository `common/COMMON-CLI.md` § Pagination Pattern. Partial results understate gaps.

```bash
# Generic paginated fetcher (bash) — note type + state filters
url="https://api.fabric.microsoft.com/v1/admin/workspaces?type=Workspace&state=Active"
all_workspaces="[]"
while [ -n "$url" ] && [ "$url" != "null" ]; do
  resp=$(az rest --method GET --url "$url" --resource "https://api.fabric.microsoft.com")
  all_workspaces=$(jq -s '.[0] + .[1].workspaces' <(echo "$all_workspaces") <(echo "$resp"))
  url=$(echo "$resp" | jq -r '.continuationUri // empty')
done
echo "$all_workspaces" > /tmp/all_workspaces.json
```

Prefer the server-side filter over client-side `select(.state == "Active")`: it halves the payload and pages fetched, and removes any chance of a later step forgetting it. Keep a client-side check as a belt-and-braces assertion when you did not control the fetch.

### Deleted Workspaces (Exclude Them Everywhere)

Deleted workspaces are the subtlest trap in this skill, because the two directions disagree — **verified live**:

| Direction | Behaviour |
|---|---|
| `GET /v1/admin/workspaces` (no filter) | A `Deleted` workspace **still carries its `domainId`** |
| `GET /v1/admin/domains/{id}/workspaces` | The same workspace is **absent** — domain-side lists are already Active-only |

**Rule: filter to `state == "Active"` *before* grouping by `domainId`, on both sides of any comparison.** Otherwise:

- **False cross-view differences.** In the verified tenant, 141 workspaces carried a `domainId` while domain endpoints listed 140 — a difference of exactly one deleted workspace. Reported naively, that is a fabricated data-integrity finding.
- **Inflated domain sizes**, and **fake "populated" domains** — a domain whose only workspaces are deleted is genuinely **empty**, a real finding you would then miss.

⚠️ The same trap applies to **items**: `/v1/admin/items` and the scanner API report items in deleted workspaces as `state: Active`. Filtering on the item's own state does **not** remove them — join `item.workspaceId` against the governable set. See Items in Deleted Workspaces.

---

## Known Blind Spots (state these when reporting)

Portal-only governance surfaces that no API in this skill can see. Reporting a clean bill of health without naming these is misleading.

| Surface | Why it matters | What to say |
|---|---|---|
| **Domain image / branding** | Recognisability in the catalog domain selector | Portal-only; not auditable either way |
| **Default domain configuration** | Silently auto-assigns workspaces and grants implicit contributor rights | Portal-only; likely explanation for unexpected assignments; makes role reads a **lower bound** |
| **DLP policies, violations, last-evaluation time** | Half of the Protect pillar | Direct the user to Govern tab → Protect, secure & comply |
| **Endorsement badge writes** | Cannot remediate trust findings programmatically | Read is possible via the scanner API; setting a badge is portal-only |
| **Tenant-setting delegation state per domain** | Determines which domains self-govern | Not on the `Domain` object, but **is** readable via `GET /v1/admin/domains/delegatedTenantSettingOverrides` (empty `value[]` when nothing is delegated) |
| **Capacity utilization / CU / throttling / overload** | The whole "is this capacity healthy?" question | **No REST API — verified 404 on every candidate.** Only the Fabric Capacity Metrics app has it. Never infer it from workspace or item counts |
| **Capacities not returned by the admin list** | Workspaces reference them, but they cannot be resolved | **383 of 1,065 workspaces (36%)** pointed at capacities absent from both endpoints; direct fetch returned **401**. Report an explicit "capacity not resolvable" bucket |

---
