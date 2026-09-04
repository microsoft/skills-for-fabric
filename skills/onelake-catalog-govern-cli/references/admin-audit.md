<!-- MODE REFERENCE for onelake-catalog-govern-cli (mode: admin-audit). Loaded on demand by the dispatcher SKILL.md. -->

# OneLake Catalog Govern — Admin Audit (read-only) CLI Skill


## Contents

- [Prerequisites — Admin Access Required](#prerequisites-admin-access-required)
- [Prerequisite Knowledge](#prerequisite-knowledge)
- [Reference Files (load on demand)](#reference-files-load-on-demand)
- [Must/Prefer/Avoid](#mustpreferavoid)
- [Gotchas and Troubleshooting](#gotchas-and-troubleshooting)

Read-only assessment of Fabric tenant governance posture across the three OneLake catalog Govern pillars — **data estate health**, **protect/comply**, and **trust/curate** — using the Fabric Admin REST API.

**An audit is not a data dump.** For evaluative questions, every finding must carry *why it matters*, a *recommended action*, and a *priority* — see the Deliverable Contract. For plain lookups, answer directly; see Which steps apply.

> **Routing already happened.** The dispatcher SKILL.md is the single source of truth for the 2×2 mode grid, routing rules, and the permission-tier / known-gap notes. This is the **admin-audit** mode reference — reached when a Fabric **tenant admin** wants a read-only audit.

> **CRITICAL NOTES**
> 1. **Default scope is tenant-wide, not personal.** Every audit in this mode covers the whole tenant — use the Admin APIs (`/v1/admin/*`), not the user-scoped Core control-plane APIs, and state the scope in your answer.
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. These are **Admin APIs**, not the standard `/v1/workspaces` control-plane APIs — they require the caller to hold a **Fabric/Power BI admin role** on the tenant. A `403` here means insufficient admin rights, not a token/audience bug.
> 4. "Domain" in this skill means a Fabric **governance domain** (grouping of workspaces for policy/ownership). This is unrelated to **Fabric IQ** ontologies/knowledge graphs (`skills/fabriciq`), which share the word "domain" only informally — do not conflate the two.
> 5. **"Data product" and "steward" are not Fabric entities** — there is no such item type, API, or role. Translate them to real entities (endorsed/certified items; Domain admin / Domain contributor / item owner) rather than inventing API calls. See `catalog-concepts.md`. **But "who stewards this domain?" is still answerable** — read the domain's `Admin` role assignment, and treat a missing one as a real gap (Find Ownerless Domains).
> 6. **Admin governance insights lag by up to 24 hours** (Admin Monitoring Storage refreshes daily). Never present tenant-wide governance numbers as real-time.
> 7. **Two different APIs, two different token audiences.** Fabric Admin APIs (`https://api.fabric.microsoft.com`) provide the all-Fabric item inventory, including descriptions and tags. Sensitivity labels and endorsement require the Power BI **scanner** API (`https://analysis.windows.net/powerbi/api`) and cover only scanner-supported artifact types.

## Prerequisites — Admin Access Required

> ⚠️ **Fabric/Power BI tenant admin role is mandatory.** Every endpoint in this skill lives under `/v1/admin/*`. Regular workspace members/contributors — even with full access to their own workspaces — cannot call these APIs. Before running anything in this skill, confirm with the user (or verify via `az account show` + a test call) that the signed-in identity holds a tenant admin role. If a call returns `403`, stop and tell the user they need admin rights granted — do not attempt workarounds or alternate endpoints to bypass this.
>
> **Not a tenant admin?** Use `dataowner-audit` mode instead — it checks domain assignment for the caller's own workspaces via the Core (non-admin) API. Note it has a real scope limit: it cannot detect empty domains or provide tenant-wide domain-assignment analysis, since no Core API lists all workspaces in a domain.

## Prerequisite Knowledge

- `govern-pillars.md` — **read first**: the three pillars (health / protect / trust), what "good" looks like, common gaps, and reporting conventions
- `govern-roles.md` — who can do what; Fabric admin vs. data owner insight scope and refresh lag
- `catalog-concepts.md` — entity model; which concepts are API-backed vs. conceptual ("data product", "steward")
- Repository `common/COMMON-CORE.md` — Fabric REST API patterns, auth, pagination, capacity management
- Repository `common/COMMON-CLI.md` — CLI implementation (`az rest`, pagination pattern, quick reference); see § Authentication Recipes for `az login` flows and token acquisition

## Reference Files (load on demand)

This file holds what **every** audit needs: the scope gate, blind spots, the posture workflow, the deliverable contract and cross-cutting gotchas. **Detailed procedures and their procedure-specific gotchas live in `references/` — read the one matching the question, not all of them.**

| File | Read it when the question is about |
|---|---|
| `admin-audit/health-domains.md` | Domains: what exists, assignment **gaps**, ownerless domains, metadata completeness. Includes worked end-to-end examples |
| `admin-audit/health-workspaces.md` | Workspaces: unused/empty vs. inactive, admin bus-factor and `>= N` admin policy. ⚠️ Zero-admin workspaces **do not occur** — report **single-admin (89% verified)** |
| `admin-audit/health-capacity.md` | Capacities: state, ownership, domain alignment. ⚠️ **No utilization/overload API exists** |
| `admin-audit/item-inventory.md` | **How to get items at all** — Admin API vs. scanner API, and which returns what. **Shared by all three pillars — read before the two below** |
| `admin-audit/health-item.md` | Item ownership, **item identity (`defaultIdentity`)**, departed owners, staleness, **data freshness (refresh state)** |
| `admin-audit/protect-labels-dlp.md` | Pillar 2 — sensitivity label coverage, DLP |
| `admin-audit/trust-curation.md` | Pillar 3 — endorsement, description and **tag** coverage (freshness is audited under Health — see `admin-audit/health-item.md`) |

Shared repository-wide API background lives in `common/`; this skill's pillar map,
role model, entity model, and verified field coverage live directly in this
skill's `references/` directory.

> Regardless of which reference you load, the Scope Gate below applies to **all** of them. Only 47% of a verified tenant was governable — scope first, or every statistic is wrong.

---

## Must/Prefer/Avoid

### MUST DO

- **Authenticate with an admin-scoped identity** — see COMMON-CORE.md § Authentication & Token Acquisition. Admin APIs require the signed-in user/SPN to hold a Fabric/Power BI admin role.
- **Apply the Scope Gate** — `?type=Workspace&state=Active`, built once and reused for every pillar, with exclusions stated. This is the single most important correctness step in the skill.
- **Paginate fully** via `continuationUri` before drawing conclusions — partial results understate gaps.
- **Deliver findings, not measurements — when the question is evaluative.** Every finding then carries *why it matters*, a *recommended action*, and a *priority*; a count without interpretation is not an audit. For a plain retrieval question, answer it plainly instead. See Which steps apply and the Deliverable Contract.
- **For domain-health reviews, report each finding type explicitly** — assignment gaps, empty domains, ownership risks, contributor-scope risks, default-label gaps, description coverage, and clean/pass findings. Do not mention one only in recommendations if it was observed in evidence.
- **Report both raw counts and percentages** — "897 of 1,037 active workspaces (86.5%) unassigned" is more actionable than either alone.
- **Structure findings by pillar** (health / protect / trust) — matching the OneLake catalog Govern tab. See `govern-pillars.md` § Reporting Conventions.
- **State the freshness caveat** whenever findings derive from admin monitoring data — up to 24 hours stale.
- **Bucket unresolvable references instead of dropping them** — workspaces whose `capacityId` is not in the capacity list (36% verified), and items whose `workspaceId` matches no workspace. A silently smaller denominator is the most common cause of a wrong governance percentage.
- **Resolve identities before making ownership claims** — `creatorPrincipal.type` is always `"User"`, even for service principals. Use Graph `getByIds` with **no** `types` filter, or state that ownership was not assessed.

### PREFER

- **Sample, don't dump** — show 10-15 example names inline; offer a full CSV export only if asked.
- **Named list of empty domains** over just a count — the user wants to know *which*.
- **Ownership gaps reported alongside assignment gaps** — "which domains have no owner" is as actionable as "which workspaces have no domain", and users often ask for it using the word "steward".
- **Surface cross-pillar combinations first** — a *certified but stale* item, or a *broadly shared but unlabeled* item, is higher-priority than either signal alone.
- **Calibrate against tenant intent before ranking.** Test/dev tenants (heavy `Deleted` counts, dated or `E2E_`/`test`-prefixed workspace names) make coverage gaps expected rather than alarming. Ask rather than presenting a headline percentage as a KPI.
- **Rank abandonment findings by combination, not any single signal** — empty + inactive + unassigned is a real candidate; empty alone is not, and 11 verified empty workspaces had same-day activity.
- **One scanner call for both users and Power BI governance metadata** — `getInfo?getArtifactUsers=True` returns workspace roles, labels, and endorsement in the same scan. Scanning twice wastes the 100-workspace budget.

### AVOID

- Do NOT deliver a bare inventory **in answer to an evaluative question**. Counts, tables and percentages with no interpretation, recommended action or priority are the most common failure mode of this skill.
- Do NOT wrap a plain retrieval answer in audit ceremony either. "List all domains" wants the list, not a priority-ranked remediation plan — see Which steps apply.
- Do NOT rank remediation by the size of the number. **The largest gap is frequently the lowest-priority action** — see Step 4.
- Do NOT confuse this with `skills/fabriciq` or `skills/semantic-model-consumption` — those query **data inside** Power BI semantic models/reports, not tenant governance metadata.
- Do NOT confuse Fabric **admin "Domains"** with **Fabric IQ (preview)** ontologies — different products, overlapping terminology only.
- Do NOT treat a `403` as a code bug — it means the identity lacks admin rights on the tenant.
- Do NOT invent APIs for "data products" or "stewards" — they don't exist; translate them to real entities first.
- Do NOT present domain membership as an access/security control — it does not affect item visibility or permissions. Findings about it are catalog-integrity findings, not data-leakage findings.
- Do NOT claim a capacity is **overloaded, throttled, or near its CU limit** — no API exposes utilization (verified 404 on all four candidates). Point to the Fabric Capacity Metrics app.
- Do NOT report that an item's **owner left the organisation** from a failed identity lookup — verified 11 false positives vs. 0 genuine orphans.
- Do NOT treat **zero-admin workspaces** as a routine check — verified 0 of 1,063. Report **single-admin** instead, or the check silently signals a clean bill of health.
- Do NOT treat an item's `lastUpdatedDate` as a usage signal — it records modification, so a heavily-read, never-edited certified dataset looks abandoned.

---

## Gotchas and Troubleshooting

Cross-cutting issues. **Procedure-specific gotchas live with their procedure** — see the Gotchas section at the end of health-workspaces.md, health-capacity.md, health-item.md and item-inventory.md.

| Symptom | Cause | Fix |
|---|---|---|
| `403 Forbidden` on any `/admin/*` call | Signed-in identity lacks Fabric/Power BI admin role | Have a tenant admin grant the role; this is not a token audience issue |
| `401/403` on `api.powerbi.com` scanner calls while Fabric admin calls work | Wrong token audience — the scanner API needs `https://analysis.windows.net/powerbi/api` | Acquire a second token for that resource; the Fabric token will not work |
| `domainId` missing from workspace objects | The workspace has no domain assigned (expected null, not an error) | Treat as a gap finding, not a bug |
| Any count, percentage or gap list looks roughly 2× too high | Deleted, personal or admin-monitoring workspaces in the denominator; or items in deleted workspaces | Apply the Scope Gate. A verified tenant was only 47% governable |
| View A / View B counts differ by a small number, and the extra workspaces are all `Deleted` | Deleted workspaces retain `domainId`; domain-side lists exclude them | Filter to `state == "Active"` before grouping — see Deleted Workspaces |
| Domain shows workspaces via tenant-wide filter but 0 via `/admin/domains/{id}/workspaces` | All its workspaces are deleted, or a stale `domainId` / caching lag | If all deleted, the domain is genuinely **empty** — report it as such. Otherwise re-run after a few minutes and treat any residual discrepancy as a platform data issue, not an audit finding |
| Pagination stops early | `continuationUri` not followed to completion | Loop until the field is absent/null — see repository `common/COMMON-CLI.md` § Pagination Pattern |
| `RequestBlocked` / "blocked by the upstream service until `<time>`" | Admin API throttling; the message carries a retry-after timestamp | Wait it out and **cache the inventory** — do not re-fetch it per check |
| Governance numbers don't match what the user sees right now | Admin insights derive from Admin Monitoring Storage, refreshed once per day | State the up-to-24h lag; a data owner's *My items* view refreshes on open and will legitimately differ |
| Govern-tab figures exclude items you expect | Subitems (tables), third-party workload items and guest/cross-tenant content are out of scope; Govern tab is unavailable with Private Link | See `govern-pillars.md` § Known Limitations |
| Tempted to edit the autogenerated governance report or semantic model | It is admin-managed and read-only by design | Never modify it; build a separate report from the API data instead |
| User asks about "data products" or "stewards" | Not Fabric entities — no item type, API, or role exists | Translate to endorsed/certified items and Domain admin / Domain contributor / item owner; see `catalog-concepts.md` |
| Confusing this skill with Fabric IQ ontology docs | "Domain" terminology overlap | Unrelated features; use `skills/fabriciq` for ontology/knowledge-graph work |
| Zero certified items reported | Certification may never have been enabled in tenant settings | Check enablement (and whether it was delegated to domain admins) before reporting a curation failure |
| The report is a wall of numbers with no recommendation | Steps 4 and 5 skipped | Findings without *why it matters*, an action and a priority are not an audit — see the Deliverable Contract |
