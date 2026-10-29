---
name: onelake-catalog-cli
description: "Governs and curates the Microsoft Fabric OneLake catalog through Fabric Admin, Core and Power BI REST APIs. Use for tenant or data-owner governance audits and guarded remediation of domains, workspace assignment, capacity, labels, tag definitions, workspace tags, certification, refresh and item identity, and for owners curating an item's description, name, tags and table and column descriptions. Item discovery belongs to search-consumption-cli."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: onelake-catalog-cli` (`az rest`: `--headers "x-ms-fabric-skill=onelake-catalog-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace ID from its name, one call: `az rest --method get --resource "https://api.fabric.microsoft.com" --url "https://api.fabric.microsoft.com/v1/workspaces" --query "value[?displayName=='<name>'] | [0].id" -o tsv` (follow `continuationToken` only if it isn't on the first page; details in [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)).
> 2. To find an item's ID, one call: the same on `.../v1/workspaces/{ws}/items?type=<Type>` with `--query "value[?displayName=='<name>'] | [0].id"`.
> 3. **Write-gated skill** — never call a write API before its gate below has passed. For curation that means the owner reviewed **every** proposed change and explicitly confirmed — not even a "test" write to check whether a change is allowed or what is already applied.
> 4. The item list and Get Item both return an item's `tags`. **An item with no tags has no `tags` field** — that absence means untagged.

# OneLake Catalog — CLI Skill (mode dispatcher)

One skill for the OneLake catalog. **Govern** (catalog health, protection and trust: audits and
guarded remediation, by permission tier) and **curate** (an owner improving specific items'
discoverability metadata) are modes, each detailed in a reference loaded on demand. This file
picks the mode, holds every write gate, and indexes the references.

## Mode selection

| Mode | Use when | Load | Writes |
|---|---|---|---|
| **curate** | An owner wants specific items easier to find: a description, a clearer display name, tags, or table and column descriptions (items with a OneLake Tables folder) — one item, an explicit list, or one named workspace's weakly-described items | [references/curate.md](references/curate.md) | ✅ after the owner approves each suggestion |
| **dataowner-audit** | A **non-admin** workspace or domain owner wants governance posture for workspaces they administer (widen to accessible on request; Core API) | [references/dataowner-audit.md](references/dataowner-audit.md) | ❌ |
| **dataowner-remediate** | A data owner who is also a domain / workspace / capacity admin fixes a governance finding — single-workspace domain or capacity assignment, workspace tags, refresh, item identity (Core & Power BI APIs, no tenant admin), including dry runs of these | [references/dataowner-remediate.md](references/dataowner-remediate.md) | ✅ self-service |
| **admin-audit** | A **Fabric tenant admin** wants tenant-wide governance posture (`/v1/admin/*`) | [references/admin-audit.md](references/admin-audit.md); any tenant count starts from [admin-audit-scope.md](references/admin-audit-scope.md) | ❌ |
| **admin-remediate** | A **Fabric tenant admin** makes tenant-wide writes — domains, bulk assignment, domain roles, bulk labels, tenant tag definitions, tenant settings | [references/admin-remediate.md](references/admin-remediate.md) | ✅ |

Govern is a 2×2 grid — tier (which API surface the caller can reach) × action (audit vs
remediate) — covering the health, protect and trust pillars. **Choose the tier by API surface,
not job title**: the `admin-*` modes need the Fabric tenant administrator role (Fabric admin /
Power Platform admin / M365 global admin); domain, capacity and workspace admins who are not
tenant admins live entirely in the `dataowner-*` modes.

### Mode boundary rules

- **A direct curation request goes straight to curate.** Read the target item's current state —
  don't run a governance audit first. Curation needs neither tenant admin nor workspace Admin;
  each change has its own permission (see curate.md).
- **Governance starts with an audit.** Never remediate before establishing the current state;
  audit → remediate within the same tier unless the caller's rights change.
- **Curate is the only writer of item metadata.** Item descriptions and display names, applying
  or removing an item's tags, and table and column descriptions are written only in curate.
  Workspace tags stay in dataowner-remediate; tenant tag *definitions* in admin-remediate.
- **Govern finds, curate fixes.** Govern reports description and tag **coverage** — presence,
  with scope, denominator and freshness caveats, not proof the text is accurate; curate judges
  content and proposes. To fix selected gaps, hand off to curate with: a **bounded target** (an
  explicit item list with workspace ID, item ID and type, or one named workspace — never the whole
  tenant: ask the user to pick), the **observed gap** with its source and time (a candidate to
  recheck, not current truth), **only the fields the user chose** ("fix missing descriptions" =
  description only), and known access limits and owner contacts. A remediation is done only when
  curate has verified the write.
- **Audit modes never write.** If a write is asked for in an audit mode, switch explicitly to the
  matching remediate mode or to curate — don't improvise a write.
- **A dry run or preflight of a fix** loads that fix's remediate mode and stays read-only there —
  it isn't an audit. Moving one workspace to a domain is `dataowner-remediate`; bulk assignment
  is `admin-remediate`.
- **Finding items** when the workspace isn't known belongs to `search-consumption-cli`. Looking up
  a workspace or domain by name, or an item by name inside a known workspace, is not discovery:
  use the lookups in CRITICAL NOTES and don't load `search-consumption-cli` for it.

> ⚠️ **Known Fabric gap.** A domain or workspace admin who is not a tenant admin has **no API**
> for their scoped governance posture: `/v1/admin/*` rejects them and the Core API can't list a
> domain's workspaces. `dataowner-audit` covers only workspaces the caller can access — say so
> up front rather than routing into an `admin-*` mode that will 401/403.

## Terminal write — the step you must not skip

Reading a reference, drafting suggestions or building a dry run is NOT completing a write. Each
writing mode ends with the state-changing call(s) below, issued only after the gate for that
write passes. If you did not issue it, nothing changed — say so rather than reporting success.

| Mode | Terminal write |
|---|---|
| `curate` | `PATCH /v1/workspaces/{ws}/items/{id}` (description; display name in a **separate** call), `POST .../items/{id}/applyTags` or `unapplyTags`, and for a table `POST https://onelake.table.fabric.microsoft.com/common/v1/{ws}/{item}/schemas/{schema}/tables/{table}/additionalMetadata` with the **complete** set from a fresh read — only for suggestions the owner accepted |
| `dataowner-remediate` | `POST /v1/workspaces/{id}/assignToDomain` / `unassignFromDomain` (synchronous `200`), `assignToCapacity` (`202` — poll to a terminal state), `POST /v1/workspaces/{id}/applyTags` / `unapplyTags` (workspace tags), item identity, semantic model refresh |
| `admin-remediate` | `/v1/admin/*` writes — domains, bulk workspace assignment, domain roles, labels, tenant tag definitions, tenant settings |
| `dataowner-audit`, `admin-audit` | none — read-only |

Before reporting a write done, confirm an explicit success (`200`/`201`, or a terminal LRO
success for a `202`) and read the result back.

### Write gates — must pass first

| Write | Mode | Gate |
|---|---|---|
| Any curation write | curate | The owner saw a numbered current → proposed preview of **every** suggestion and explicitly approved; "apply all" covers only what was shown. Approving an audit or picking a remediation never approves text the owner hasn't seen. |
| Table and column descriptions | curate | A write **replaces** the table's whole additional metadata: re-read, change only the approved descriptions, send the complete set in the same command, read again. The API has no concurrency check — never claim concurrent edits were preserved. A **shortcut** table is written on its source — name it and get explicit confirmation. |
| **Delete a domain** | admin | Check subdomains (`parentDomainId`) and assigned-workspace counts for the domain and every subdomain; if workspaces would be orphaned, STOP and get explicit confirmation naming them. The API has **no** cascade-block. See [domain-crud.md](references/admin-remediate/domain-crud.md#deleting-a-domain--the-portal-vs-api-safety-gap). |
| **Delete a tag** definition | admin | Report how many items carry it first — deletion detaches it everywhere with **no undo**. |
| **Bulk-assign workspaces to a domain** | admin | Check each target's current `domainId` and warn before **silently overriding** an assignment. Dry-run the target list first. |
| **Remove a principal from a domain role** | admin | Confirm it will not leave the domain **ownerless**; name the principal being removed. |
| **Bulk sensitivity-label change** | admin | Dry-run: show the affected items and before/after label, get confirmation. **No service principal / managed identity** — the call will fail. |
| **Write a tenant setting** | admin | Read and show the current value, then the proposed value — tenant-wide blast radius. |
| **Assign / unassign one workspace to a domain** | dataowner | A move is a **reassignment** — confirm the current `domainId` and name the domain it leaves. Needs domain contributor **and** workspace Admin; say which is missing on failure. |
| **Reassign item ownership** (item identity, preview) | dataowner | Assigns to the **caller** only; needs Write on the item and its children. Confirm the intended identity. |
| **Assign a workspace to a capacity** | dataowner | Needs workspace Admin plus capacity Contributor/Admin. `202` is not success — poll to a terminal state. |
| **Apply / remove a workspace tag** (preview) | dataowner | Needs workspace Admin. Name the workspace and the tags, and confirm. Removing an applied tag is not deleting its definition. |

> **Don't promise a write that has no API.** Endorsement, DLP policies, an owner changing a
> sensitivity label, and tenant-admin item deletion have no write route — say so and name who can
> act ([no-write-api-escalation.md](references/admin-remediate/no-write-api-escalation.md#route-a-finding-to-someone-who-can-fix-it-escalation-lists)).
> A SQL Database's display name is fixed at creation: never send a rename for it, even when the
> owner asks for one — say it can't be renamed and offer the description and tags instead.

## Shared essentials (all modes)

- Prerequisites: [auth & tokens](../../common/COMMON-CORE.md#authentication--token-acquisition) ·
  [REST, pagination, LRO, rate limits](../../common/COMMON-CORE.md#core-control-plane-rest-apis) ·
  [CLI auth recipes](../../common/COMMON-CLI.md#authentication-recipes) ·
  [`az rest` (always pass `--resource`)](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) ·
  [OneLake via `curl` (Storage-audience token)](../../common/COMMON-CLI.md#onelake-data-access-via-curl) ·
  [OneLake shortcuts](../../common/COMMON-CLI.md#onelake-shortcuts).
- Resolve workspace and item IDs with the one-call lookups in CRITICAL NOTES 1–2.
- **Keep tool calls few.** Each call re-sends the whole conversation, so extra calls are slow and
  costly. Combine related reads in one script, and don't re-open a doc you've already read.
- **Read an item's definition in one command** that waits for the long-running operation itself
  (a semantic model usually returns `202`) — never poll it in separate calls. It waits as long as
  Fabric's `Retry-After` asks (often 20–30 s), so give the command up to 3 minutes: if your shell
  tool has a wait or timeout setting, raise it rather than letting the command move to the
  background. Only for types with a definition: Warehouse, SQL Database, SQL analytics endpoint,
  ML model/experiment and Datamart have none — read their schema instead. PowerShell 7 (bash:
  `fabric_lro` in COMMON-CLI.md):
  ```powershell
  $h = @{ Authorization = "Bearer $(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)"; 'x-ms-fabric-skill' = 'onelake-catalog-cli' }
  $st = @{ n = 0; end = (Get-Date).AddMinutes(3) }
  # Waits the full Retry-After (202 and 429); backs off 2-30 s only when the header is missing or invalid.
  function Wait-RetryAfter($r) { $ra = 0
    if (-not [int]::TryParse("$(@($r.Headers['Retry-After'])[0])", [ref]$ra) -or $ra -lt 1) { $ra = [Math]::Min(30, [Math]::Pow(2, ++$st.n)) }
    if ((Get-Date).AddSeconds($ra) -gt $st.end) { throw "Definition read did not finish within 3 minutes." }
    Start-Sleep -Seconds $ra }
  while (($r = Invoke-WebRequest -Method Post -Uri "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items/$ITEM_ID/getDefinition" -Headers $h -SkipHttpErrorCheck).StatusCode -eq 429) { Wait-RetryAfter $r }
  if ($r.StatusCode -ge 400) { throw "getDefinition returned $($r.StatusCode): $($r.Content)" }
  $def = if ($r.StatusCode -eq 202) {
    $op = [string]$r.Headers['Location']; $res = $r; $s = ''
    while ($s -notin 'Succeeded', 'Failed') {
      Wait-RetryAfter $res; $res = Invoke-WebRequest $op -Headers $h -SkipHttpErrorCheck
      if ($res.StatusCode -eq 200) { $s = ($res.Content | ConvertFrom-Json).status } elseif ($res.StatusCode -ne 429) { throw "Polling returned $($res.StatusCode): $($res.Content)" } }
    if ($s -ne 'Succeeded') { throw "Definition read failed: $($res.Content)" }
    while (($res = Invoke-WebRequest "$op/result" -Headers $h -SkipHttpErrorCheck).StatusCode -eq 429) { Wait-RetryAfter $res }
    if ($res.StatusCode -ge 400) { throw "Definition result returned $($res.StatusCode): $($res.Content)" }
    $res.Content | ConvertFrom-Json
  } else { $r.Content | ConvertFrom-Json }
  $dir = New-Item -ItemType Directory -Force -Path (Join-Path ([IO.Path]::GetTempPath()) "def-$ITEM_ID")
  foreach ($p in $def.definition.parts) {
    $t = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p.payload)); $f = Join-Path $dir ($p.path -replace '[\\/:]', '_'); Set-Content -LiteralPath $f -Value $t
    "== $($p.path) ($($t.Length) chars)"; if ($t.Length -le 4000) { $t } else { $t.Substring(0, 4000); "[first 4000 of $($t.Length) chars; full text in $f]" } }
  ```
  A part cut at 4,000 characters is saved in full: read the rest (one call) if what's shown isn't enough.
- Use the exact Fabric Admin, Core, Power BI, Graph or OneLake API surface the mode documents; a
  `401` or `403` is never permission to bypass RBAC.

## Rules

### MUST
- **Load exactly one mode reference** for the request and follow it end to end; come back to the
  index below when another procedure is needed. In curate, also read the suggestion guidance
  before drafting anything, and the table metadata reference before any table or column work.
- **(curate) Propose exactly what the owner asked for.** A specific request gets only that: "add a
  description" → the item description; "suggest tags" → tags; "describe the table" → the table
  description only; "describe the columns" → column descriptions only; "describe the item's
  objects" or "its tables and columns" → both. A general request ("curate this item", "make it
  more discoverable", "improve its metadata") gets the item's description, name and tags; an item
  with a OneLake Tables folder also gets its table and column descriptions. If the owner names
  several items, cover each one, and report each with only the fields it has.
- **(curate) Check the scope before any call.** Curate covers one item, an explicit list of items,
  or **one** named workspace at a time. For a tenant-wide request ("all my items", "every
  workspace"), say plainly that it isn't supported and offer one named workspace or an explicit
  list; for several named workspaces, ask which to start with. Don't list workspaces or items first.
- **(govern)** State scope, exclusions, pagination completeness, and freshness caveats with every
  governance statistic.

### PREFER
- Least-privileged Core or Power BI APIs for data-owner actions instead of requiring tenant-admin rights.
- Findings as evidence, consequence, recommended action, priority and effort — not an inventory dump.
- Sequencing ownership and access-scope fixes before bulk assignment or labeling.

### AVOID
- Mutating a tenant from an audit mode, or reporting an asynchronous `202` as completion.
- Inventing write APIs for endorsement, DLP policy, admin item deletion, or third-party item-identity assignment.
- **(curate) Volunteering anything about table or column descriptions for items without a OneLake
  Tables folder** (semantic models, reports, notebooks, pipelines, dataflows, …). For these items,
  description, name and tags are the complete list — present them without qualifiers in the
  preview and whenever you say what the skill can do (e.g. while declining a request, or offering
  what else you could review next). Don't add a note that table or column descriptions are N/A,
  don't apply or aren't covered, and don't offer them: the owner didn't ask. Only if they ask,
  answer that they aren't supported for that item type, then stop and let the owner choose — don't
  load another skill or draft those descriptions yourself.
- **(curate) Saying "sub-items"** — use the owner's words: "tables" and "columns", or "objects"
  when speaking generally.

## References

Each reference is one hop from this index; after loading one, return here when another is needed.

**Curate**
- [Curate](references/curate.md) — workflow, permission per change, preview format, examples, errors
- [Suggestion guidance](references/curate/metadata-suggestion-guidance.md) — drafting descriptions, names and tags from content
- [Tag taxonomy](references/curate/tag-taxonomy.md) — tenant/domain tag scope and name → ID resolution
- [Table metadata](references/curate/table-metadata.md) — table and column descriptions (OneLake table API, preview)
- [Curation API reference](references/curate/api-reference.md) — Update Item, Apply/Unapply Tags, List Tags

**Govern — shared**
- [Govern pillars](references/govern-pillars.md) — the three pillars, what "good" looks like, reporting conventions
- [Governance data sources](references/govern-data-sources.md) — verified API field coverage and blind spots
- [Governance roles](references/govern-roles.md) — permission tiers, domain/workspace roles, insight refresh lag
- [Catalog concepts](references/catalog-concepts.md) — the entity model and API-backed versus conceptual terms

**Govern — modes**
- [Admin audit](references/admin-audit.md) — tenant-wide read-only governance assessment
- [Admin audit scope](references/admin-audit-scope.md) — governable denominator (active workspaces of type Workspace), exclusions, and known blind spots
- [Admin audit assessment](references/admin-audit-assessment.md) — end-to-end evaluative workflow, prioritization, and deliverable contract
- [Admin remediate](references/admin-remediate.md) — tenant-wide guarded writes through Admin APIs
- [Data-owner audit](references/dataowner-audit.md) — caller-scoped read-only checks through Core APIs, including a workspace's domain assignment
- [Data-owner workspace health](references/dataowner-audit/health-workspaces.md) — empty and inactive workspaces within the caller's scope
- [Data-owner remediate](references/dataowner-remediate.md) — least-privileged Core and Power BI writes: moving one workspace to a domain, capacity, workspace tags, refresh, item identity

**Govern — admin audit procedures**: [domain health](references/admin-audit/health-domains.md) · [workspace health](references/admin-audit/health-workspaces.md) · [capacity health](references/admin-audit/health-capacity.md) · [item inventory](references/admin-audit/item-inventory.md) · [item health](references/admin-audit/health-item.md) · [protect coverage](references/admin-audit/protect-labels-dlp.md) · [trust curation](references/admin-audit/trust-curation.md)

**Govern — admin remediation procedures**: [domain lifecycle](references/admin-remediate/domain-crud.md) · [bulk workspace assignment (tenant admin)](references/admin-remediate/domain-assign-workspaces.md) · [domain roles](references/admin-remediate/domain-roles.md) · [tag definitions](references/admin-remediate/tags.md) · [item sensitivity labels](references/admin-remediate/item-sensitivity-label.md) · [domain default labels](references/admin-remediate/domain-default-label.md) · [trust remediation](references/admin-remediate/trust-curate.md) · [no-write escalation](references/admin-remediate/no-write-api-escalation.md)

## Examples

```text
I'm curating my items for the OneLake catalog. Propose a better description for the semantic model Sales Model in the Finance workspace.
```

```text
Make the lakehouse LSEGDemo more discoverable — describe its tables and columns too.
```

```text
Audit our tenant's OneLake catalog governance posture and prioritize the findings.
```

```text
Which workspaces I administer are not assigned to a domain?
```

```text
Show a dry run for assigning these workspaces to the Finance domain, including current assignments.
```

```text
Find unlabeled items tenant-wide and explain which remediations require a tenant admin versus a data owner.
```
