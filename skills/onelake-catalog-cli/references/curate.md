# Curate mode — owner curation of catalog metadata

An item **owner** raises discoverability by reviewing suggested **descriptions**, **display
names** and **tags**, plus **table and column descriptions** for items with a OneLake Tables
folder (such as a Lakehouse); approved changes are written **only on explicit confirmation**.

SKILL.md holds the ID lookups, the one-command definition read, the write gates and terminal
writes, and indexes the curate references (`curate/metadata-suggestion-guidance.md`,
`curate/tag-taxonomy.md`, `curate/table-metadata.md`, `curate/api-reference.md`). Auth and
pagination: `common/COMMON-CLI.md` (always pass `--resource` to `az rest`; the OneLake table
API needs a Storage-audience token).

## Contents

- [Scope](#scope)
- [Permission per change](#permission-per-change)
- [Rules](#rules)
- [Inputs](#inputs)
- [Workflow](#workflow)
- [Handoff from a governance audit](#handoff-from-a-governance-audit)
- [Output format](#output-format)
- [Examples](#examples)
- [Error handling](#error-handling)

## Scope

- **Bulk** — one item, an explicit list (may span workspaces), or one named workspace: list its
  items (`GET /v1/workspaces/{ws}/items`, following `continuationToken`), keep those lacking good
  metadata (empty description, weak/placeholder name, no tags), and **exclude Dataflows Gen2
  staging artifacts** (`StagingLakehouseForDataflows*` / `StagingWarehouseForDataflows*` and
  their SQL endpoints — system plumbing).
- **Tables & columns (preview API)** — only items with a OneLake Tables folder; a write
  **replaces all** of a table's additional metadata. Descriptions only: tags exist only on items.

## Permission per change

| Actor | Required permission | Scope |
|---|---|---|
| Item owner / creator | Read and write on the item | Change the item's description and display name |
| Item owner / creator | Contributor or higher on the workspace | Apply or remove the item's tags |
| Item owner / creator | Write access on the item, or **ReadWrite** through a OneLake data access role | Curate its table and column descriptions |
| Reader | Read only | Cannot apply — explain what would change and suggest asking the owner for access |

MUST check the permission for each operation before proposing to apply it; offer only the
changes the caller can make. Curation needs neither tenant admin nor workspace Admin.

## Rules

### MUST
- **Read `curate/metadata-suggestion-guidance.md` before drafting any suggestion**, and
  `curate/table-metadata.md` before any table or column work.
- **Read the current metadata first** (`GET items/{id}`) and preserve fields you are not changing.
- **Base suggestions on real content** (the definition read from SKILL.md, table/schema
  listing) — never invent facts about the item.
- **Show a current → proposed diff** and get explicit confirmation before any write.
- **Resolve tag names to applicable tag IDs** via `GET /tags` before `applyTags` (Apply Tags
  takes IDs, not names). Tenant tags apply tenant-wide; domain tags are eligible for new
  application only when `scope.domainId` matches the workspace's current domain.
- **Respect limits** — description ≤ 256 characters; at most 10 tags per item; `applyTags`
  ≤ 25 requests/minute (throttle bulk).
- **Always work from fresh state, and honor re-run requests** — re-read the item's current
  metadata + content and the live tag definitions and workspace domain on **every** run. If the
  owner asks to try again, re-analyze from scratch — never treat a repeat as an automatic no-op.
- **Let the owner review every suggestion** — item, table, and column. Number each one; the
  owner can accept, edit, or reject it, or exclude a whole item or table. Write only accepted
  suggestions; on partial failure, continue the rest and report per item.

### PREFER
- High-level, durable descriptions that state what the item contains and its purpose — accurate
  over the long run, not tied to the item's current shape.
- Reusing existing applicable tenant or domain tags over proposing new ones an admin must create.
- Updating only the fields that need it (skip the display name if it's already clear **and**
  matches the item's contents; if it's well-formed but mismatched, flag it rather than skip).

### AVOID
- Writing anything the owner did not approve.
- Overwriting a non-empty description with a generic one — offer to merge/improve instead.
- **Trusting a non-empty description the content doesn't back** — an empty item whose
  description claims contents/behavior it lacks is a mismatch to **flag**, not a "good"
  description to leave alone. Never fabricate a description for an empty item.
- Volatile specifics in an **item** description (column names, row/table counts, refresh
  cadence, table grain) — those belong in a point-in-time summary, not durable owner metadata.
- **Copying data values into table or column descriptions** — describe what a column *means*,
  never sample rows, example values, or statistics. Don't read table rows to draft descriptions.
- **Writing through a shortcut without saying so** — a shortcut table's descriptions live on the
  source table; name the source and get explicit confirmation before changing it.
- Proposing, editing, or mentioning table/column tags — Fabric tags exist only on items. Keep
  any stored `tags` values exactly as read.
- **Putting sensitive or confidential content into metadata** — a description or tag is broadly
  discoverable in catalog search, visible to people who may **not** have access to the item's
  data. Never copy raw values, secrets, personal data, or restricted names into it. Don't try to
  auto-classify what's sensitive — **the owner knows, so surface the proposed text and let them
  redact or reject anything at the confirm step**.
- Proposing tags that do not exist or domain tags that are not applicable to the target
  workspace (flag them clearly and exclude them from the apply call).
- Pasting auth tokens into commands — acquire them at run time.

## Inputs

| Input | Source | Required |
|---|---|---|
| Workspace(s) (name or ID) | user / handoff | yes |
| Item(s) (name+type or ID) — explicit set | user / handoff | one of these |
| Named workspace (curate its weakly-described items) | user names a workspace | one of these |
| Fields to curate | user / handoff | no (default: all weak fields) |
| Tables / columns to describe | user | no (only for items with a OneLake Tables folder; default: tables and columns without a good description) |
| Owner-provided edits / exclusions | user | no (applied over suggestions) |

## Workflow

1. **Resolve scope** — build the target item list with the one-call lookups in SKILL.md. A
   single item is a batch of size 1; an explicit list is that batch. For a **named workspace**,
   confirm the caller has write access on it, enumerate its items and filter as in
   [Scope](#scope). Set aside items whose metadata already looks complete, but **still validate
   them in step 4** — only metadata that accurately and durably reflects the item counts as
   **well-curated** and is reported as *skipped (already curated)*, not re-proposed.
2. **Per item, read baseline** — `GET /v1/workspaces/{ws}/items/{id}`; capture current `type`,
   `displayName`, `description`, `tags`, `sensitivityLabel`; also read the workspace's current
   domain assignment so domain-tag applicability can be evaluated.
3. **Per item, gather content signal** — for types with a definition, read it with the
   **one-command recipe in SKILL.md § Shared essentials** (never poll in separate calls); a part
   cut at 4,000 characters is saved in full — read the rest (one call) if needed. **Warehouse,
   SQL Database, SQL analytics endpoint, ML model/experiment and Datamart have no definition
   export: never call `getDefinition` for them.** For **OneLake tabular items** (Lakehouse,
   Warehouse, SQL Database, Mirrored Database, KQL) read the tables/schema — list-tables
   (`GET .../lakehouses/{id}/tables`), `INFORMATION_SCHEMA` via SQL, or Kusto `.show tables`.
4. **Per item, draft suggestions**, following
   `curate/metadata-suggestion-guidance.md` — don't draft from memory.
   - `description` — ≤ 256 chars; **high-level & durable**: what the item contains + its
     purpose. **Validate any existing description against the content signal** — if the item is
     empty or the content contradicts it (e.g. an empty pipeline whose description claims it
     ingests data), **flag the mismatch**. If the item is only **partially configured** (e.g. an
     Eventstream with a source but no destination), describe only what exists and **note what's
     missing**. An empty item with **no** description gets none — say so. For a **contradicted/empty**
     item, also **offer to remove** the misleading description (`PATCH` `"description":""`) and
     tags (`unapplyTags`) — owner confirms; keep only if it's a known placeholder.
   - `displayName` — propose a rename if the current name is **weak/placeholder** (`lh_tmp2`,
     `Untitled`) **or content-mismatched**. For a mismatch, flag it and let owner intent decide
     rename-vs-keep — never rename silently. **Skip rename for item types with an immutable name
     (e.g. SQLDatabase, which rejects it with `SQLDatabaseDisplayNameCannotBeChanged`) — say
     it can't be renamed; know this from the item type — never send a trial rename to find out.**
   - `tags` — pick from applicable definitions returned by `GET /v1/tags` (every page, following
     `continuationUri`): all tenant-scoped tags plus domain-scoped tags whose `scope.domainId`
     matches the workspace's current domain; resolve to IDs per `curate/tag-taxonomy.md`. A tag
     found only in another domain is not applicable; a tag not found at all can't be applied.
     Preserve an already-applied out-of-domain tag left after a workspace move unless the owner
     explicitly approves removal.
   - **Tables & columns** (only for items with a top-level OneLake **Tables** folder; for any
     other item this step doesn't exist) — per table, read its descriptions **and** its Delta
     comments (a separate field the skill never changes or suggests changing), and check whether
     it is a shortcut; propose descriptions where they are empty or don't match the schema, using
     any comment as a signal. Follow `curate/table-metadata.md`.
5. **Present the preview & confirm — the owner reviews every suggestion.** Show current vs
   proposed for each suggestion and number them. **Descriptions and display names** can be
   **accepted, edited, or rejected**; each suggested **tag** can be **accepted or rejected**
   (picked from existing applicable tags — no free-text). The owner may also **exclude any item
   or table**. With many tables or columns, review **one table at a time** so no suggestion is
   buried. **Wait for an explicit "apply".** "Apply all" accepts every suggestion currently
   shown — never ones not yet shown.
6. **Apply (only approved items/fields):**
   - `PATCH /v1/workspaces/{ws}/items/{id}` with only the changed keys. **`PATCH` is atomic** —
     send `displayName` and `description` in **separate** calls (a rejected rename fails the
     whole call) and report a rejected rename as not saved.
   - `POST /v1/workspaces/{ws}/items/{id}/applyTags` (or `unapplyTags`) with the resolved tag ID
     array — **throttle to ≤ 25 requests/min** for larger batches.
   - Per approved table: re-read its additional metadata, change only the accepted table and
     column descriptions, and `POST` the complete set (`curate/table-metadata.md`).
7. **Verify & report** — re-`GET` each item and each written table; confirm applied values.
   Report each change as saved, skipped or not saved (with the reason). On partial failure,
   continue the rest — never abort the whole batch silently.

## Handoff from a governance audit

When govern hands off gaps it found, treat them as **candidates to recheck**, not current truth:

- Work only on the **bounded target** handed over (explicit items, or one named workspace) and
  only the **fields the user chose** — "fix missing descriptions" means descriptions only.
- Re-read each item (step 2) — it may have been fixed or changed since the audit.
- Approving the audit or the remediation never approves suggestion text: the owner still reviews
  every suggestion here (step 5).
- Where the caller lacks the permission for a change, don't attempt it — name the owner or
  contact govern passed along.
- Report back per item; the handoff is done only when step 7 has verified the write.

## Output format

> **Always be informative and clear** — for *every* curation, single item or bulk. Say plainly
> what state each item is in (already well-curated vs needs work), what you propose and why, and
> what will change. Never leave the owner guessing; never bury the items that need attention.

1. **Answer first** — e.g. `Read "wh_fact_sales" (Warehouse). Proposing 1 description, 1 rename, 3 tags.` For a workspace, lead with a clear tally: `Workspace 'Sales': 27 items — 8 already well-curated, 16 need attention, 3 staging artifacts skipped.`
2. **Diff table** — `# | item | object | field | current | proposed` where `object` is the item itself, a table, or `table.column`. (For a single item, `item` may be omitted.) No label column or bracket tags (`[DATA]`, `[INFERENCE]`, `[GAP]`) — owners don't know them.
3. **Confirmation prompt** — "Apply these changes? (accept/edit/reject each numbered suggestion, exclude any item or table, or reply 'apply all' to accept everything shown)". No write until confirmed.
4. **Post-apply report** — per item and table, each change as **Saved**, **Skipped** or **Not saved** (with the reason); anything you can't do is one plain sentence: what, why, who can act.
5. **Speak plain owner language, never API jargon.** Describe every proposed action in words
   the owner understands — e.g. "add a description", "clear the description", "add the tag
   *Sales*", "remove the tag *Sales*", "rename the item to *X*", "keep the current name",
   "describe the column *customer_id*". **Never** surface raw REST calls, HTTP verbs,
   endpoints, or internal property names (`PATCH items/{id}`, `applyTags`/`unapplyTags`,
   `getDefinition`, `additionalMetadata`, `displayName`). Don't mention table or column
   comments either; they're only an internal signal. For an item without a OneLake Tables
   folder, go straight from the diff table to the confirmation prompt (see the semantic model
   example below).
6. **Be explicit about what's already good.** For a single item, say clearly whether it's
   already well-curated or what specifically needs work (e.g. *"description is solid; only the
   tags are missing"*). For a workspace scan, state up front which items are already
   well-curated and name the ones needing work — e.g. *"All 27 items are already well-described
   except 3, which need attention: X, Y, Z"*. **A filled-in description, tag, or name does not
   by itself mean "good"** — flag filled-but-inaccurate metadata as needing work.

## Examples

### Preview for a semantic model

```text
Read "sales_model" (Semantic Model). Proposing 1 description; name and tags are fine.

| # | Field       | Current      | Proposed                                                                  |
|---|-------------|--------------|---------------------------------------------------------------------------|
| 1 | Description | "Sales data" | "Order and revenue measures by region, used for monthly sales reporting." |
| 2 | Name        | sales_model  | (keep)                                                                    |
| 3 | Tags        | Sales        | (keep)                                                                    |

Apply these changes? (accept/edit/reject each numbered suggestion, or reply 'apply all')
```

For a named workspace, list its items once, drop staging artifacts, then preview every
candidate. Request bodies for the item writes are in `curate/api-reference.md`; the table and
column chain (fresh read → change only accepted descriptions → write the complete set → read
again) is in `curate/table-metadata.md` § Example.

## Error handling

> **When you can't do something, say so clearly** — state plainly what isn't supported, *why*,
> and the closest thing that **is** supported, so the owner can proceed in one step. Never fail
> silently, half-do an unsupported request, or leave the owner guessing what to try next. When
> you name what the skill can do, name only what applies to this item.

| Scenario | Behavior |
|---|---|
| Caller lacks the permission for a change | Say clearly which changes they **can't make** and why: the description and name need read and write on the item, tags need Contributor or higher on the workspace, and table descriptions need write access on the item or OneLake ReadWrite. Don't attempt those writes; offer the changes they can make, and suggest asking the owner/admin for access. In a workspace scan, **name the items skipped for missing permission**. |
| More than one workspace named for a bulk scan | Say clearly you curate **one workspace at a time**; ask which to start with, then offer to do the others one by one after each finishes. |
| Whole-tenant / "all my items everywhere" request | Say clearly a tenant-wide scan isn't supported; suggest curating **one named workspace** or an **explicit list of items** instead, and offer to start with one. |
| `GET items/{id}` fails | Say the item couldn't be read and why; do not proceed. |
| Description > 256 chars | Trim/rewrite to ≤ 256 before proposing; never send an over-limit value. |
| Suggested tag not in `/tags` | Say "There's no *<name>* tag yet — ask a Fabric admin to create it"; skip it in `applyTags`. |
| `applyTags` 429 (rate limit) | Honor `Retry-After`; batch ≤ 25 requests/min. |
| Bulk: one item fails mid-batch | Continue the remaining items; record the failure in the batch report; never abort silently. |
| Workspace scan surfaces Dataflows staging artifacts | Exclude them — system plumbing, never propose curation. |
| Sensitivity label / endorsement change requested | Say it can't be done here — there's no owner-facing write API (`curate/api-reference.md`); do not attempt. Offer what curation can do for that item (for a semantic model or report: "its description, name and tags", with no note about tables or columns). |
| `PATCH items` rejects a `displayName` change (e.g. `SQLDatabaseDisplayNameCannotBeChanged`) | Report the rename as not saved; retry with `description` only (PATCH is atomic — never bundle the two). Curate description + tags instead. |
| Table metadata read fails (`404`, unsupported item, preview not available) | Say that table's descriptions can't be read or changed; continue with item-level curation. Never write without a successful fresh read. |
| Owner asks to change a table or column comment | Explain curation covers descriptions, not comments, and offer to propose a description instead. |
| Owner asks for table or column descriptions on an item without a OneLake Tables folder | Say briefly that they aren't supported for that item type. For a semantic model, add that the model's own table and column descriptions are edited with the `semantic-model-authoring` skill, then stop and let the owner choose — don't switch to that skill or draft those descriptions unless they ask. |
| Table is a shortcut | Name the source table and its workspace, explain the change is made on the source, and write only after the owner explicitly confirms that table. If the write is refused, say plainly they lack permission on the source table and suggest asking its owner. |
| Table/column tags requested | Explain that tags exist only on items; offer table and column descriptions instead. |
| Governance audit or admin remediation requested (domains, capacity, labels, certification, tag definitions, workspace tags) | Leave curate mode: that's govern — pick the govern mode in SKILL.md. |
