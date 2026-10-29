# Metadata Suggestion Guidance

How to turn an item's real content into high-quality, discoverable metadata.

## Contents

- [Principle: ground every suggestion in content](#principle-ground-every-suggestion-in-content)
- [Description formula (high-level & durable, ≤ 256 characters)](#description-formula-high-level--durable--256-characters)
- [Validate an existing description against content](#validate-an-existing-description-against-content--dont-trust-it-blindly)
- [Display name suggestions](#display-name-suggestions)
- [Tag suggestions](#tag-suggestions)
- [Table and column descriptions](#table-and-column-descriptions)
- [Owner language](#owner-language)

## Principle: ground every suggestion in content

Never invent facts about an item. Base each suggestion on signals actually retrieved:

| Signal | Source |
|--------|--------|
| Item type & display name | `GET /v1/workspaces/{ws}/items/{id}` |
| Item definition (structure, queries, model) | `POST .../items/{id}/getDefinition` — not for Warehouse, SQL Database, SQL analytics endpoint, ML model/experiment or Datamart, which have none |
| Tables & schema (OneLake tabular items: Lakehouse, Warehouse, SQL Database, Mirrored Database, KQL) | list-tables (`GET .../lakehouses/{id}/tables`), SQL analytics endpoint `INFORMATION_SCHEMA`, or Kusto `.show tables` (KQL) |
| Existing description / tags | `GET items/{id}` (**validate against content first**; preserve & improve if backed by content, flag if contradicted/empty — don't discard, but don't trust blindly) |
| Data sources | `GET .../items/{id}/connections` |

If a signal is unavailable, do not guess — reduce the suggestion's specificity and note it.

## Description formula (high-level & durable, ≤ 256 characters)

An owner **description** is durable metadata: it should stay accurate over the long run, so
keep it **high-level** — say *what the item contains* and *what it's for*, not its current
shape. A good description answers two things:

1. **Subject / contents** — what real-world entity, domain, or data the item holds.
2. **Purpose** — what it's used for (who consumes it and for what analysis).

**Template:** `<Item type> holding <subject/contents> for <durable purpose>.`

**Examples**
- `Sales Lakehouse containing public holiday reference data by country/region, used for holiday-aware sales and calendar analysis.`
- `Customer dimension holding conformed customer attributes (segment, geography), used as the shared customer lookup for BI.`

**Durability test:** would the description still be accurate if a **column is renamed**, a
**table is added**, or the **refresh cadence changes**? If not, it's too specific — raise it to
a higher level.

**Rules**
- Stay high-level; length is not the goal, durability is (a sentence or two is fine).
- **Avoid volatile specifics** — column names, exact table/row counts, refresh cadence, table
  grain, or detailed schema shape. Those belong in a point-in-time summary, not in durable
  owner metadata.
- Hard limit 256 chars (Update Item constraint). Trim before proposing.
- No marketing language; be specific about *what it is*, general about *its shape*.
- If the current description is non-empty, **offer to improve/merge**, not overwrite.

## Validate an existing description against content — don't trust it blindly

A non-empty description is a **claim to verify**, not a fact to preserve. Before deciding to
keep ("leave-alone / improve") an existing description, check it against the item's real content
signal. Description quality is **content-relative** — "is it non-empty?" is the wrong test.

- **Backed by content** — the description matches what `getDefinition` / schema actually shows →
  keep it; offer to improve/merge, don't overwrite.
- **Contradicted or unsubstantiated by content** — the description asserts contents or behavior
  the item does **not** have (e.g. an **empty** DataPipeline with `activities: []` whose
  description claims it "ingests source data into the bronze layer") → the description is **not
  representative** (stale, aspirational, or copied). Do **not** silently keep it: **flag the
  mismatch** and let the owner decide (the item may be a placeholder the content
  is coming to, or the description may simply be wrong).
- **Partially configured / incomplete** — the item has *some* real content but isn't fully wired
  up (e.g. an Eventstream with a source but **no destination** and no transformations, or a
  pipeline with one activity and no sink). Describe **only what actually exists** and **explicitly
  note what's missing** ("…no destinations or transformations are configured yet") so the catalog
  doesn't over-promise end-to-end behavior the item can't yet deliver. Don't infer the finished
  pipeline from a half-built one.
- **Empty item, no content signal at all** — nothing can be truthfully inferred, so no
  description can be *validated*. If one exists, mark it **unverified against content**; if none
  exists, say no description can be written yet — **never fabricate** one from an empty definition.

An empty item can never have a "good" description in the sense of *representing its contents* —
it has none. Treat an existing description as evidence to check, not authority to trust.

### Remediation for a contradicted / empty item — offer to *remove*, not just flag

**Misleading metadata is worse than none.** A catalog consumer searching OneLake will find the
item by its description and tags and expect data or behavior that isn't there — **false
anticipation**. So when content is empty and the description/tags claim otherwise, don't stop at
flagging: **proactively suggest removing the unsubstantiated metadata** (write-gated — the owner
confirms). Present it as the owner's choice between two readings:

- *Placeholder, real content is coming* → **keep** the metadata as forward-looking intent (the
  owner accepts the mismatch knowingly).
- *Stale / misleading, no content planned* → **clear the description** (`PATCH` with
  `"description": ""`) and **remove the tags** (`POST .../unapplyTags` with the tag IDs) so the
  item stops surfacing false promises to other users.

The **display name stays** either way (it's required and can't be blanked) — propose no rename on
an empty item, just note it's unverified. Never remove metadata without explicit confirmation.

### Type-specific note: a Report's description propagates to Power BI

Setting a **Report** item's `description` via Update Item also updates the underlying **Power BI
report object's** `description` (visible through the Power BI REST API, token audience
`https://analysis.windows.net/powerbi/api`). One `PATCH` on the Fabric item updates both the
catalog entry and the Power BI object — no separate Power BI call is needed to keep them in sync.

## Display name suggestions

**First, check whether the item type even allows a rename.** Some types have an **immutable display
name** — notably **SQLDatabase**, whose name is fixed at creation (Update Item returns
`400 SQLDatabaseDisplayNameCannotBeChanged`). For those, do **not** propose a rename; say it
can't be renamed and let the **description** carry the meaning. Only if the name is writable, evaluate it on
the **two** axes below:

1. **Weak / placeholder** — the name is cryptic or auto-generated (`lh_tmp2`, `Untitled`,
   `Lakehouse 1`, GUID-like). Propose a readable, convention-consistent rename.
2. **Content-mismatched** — the name looks well-formed but **doesn't reflect what the item
   actually contains** (e.g., `SalesLakehouse` that currently holds only a public-holidays
   reference table). Do **not** stay silent just because the name isn't a placeholder, and do
   **not** rename automatically — the mismatch may be intentional. Instead **flag it and let
   the owner's intent decide**, presenting both readings:
   - *If the item really is (and will stay) that content* → the name misleads; propose a rename
     that matches the contents (e.g., `Public Holidays` / `HolidaysReferenceLakehouse`) so
     people can find and understand it.
   - *If the current content is just a seed and the named subject is coming* (e.g., a sales
     lakehouse seeded with a holiday table) → **keep** the name — it's durable and
     forward-looking — and let the **description** carry the point-in-time nuance. Renaming to
     match today's contents would be wrong the moment the intended data lands.

Always show current → proposed and require confirmation; **never rename silently**. When it's a
content-mismatch, ask the owner which reading is true rather than guessing.

## Tag suggestions

- Derive 2–5 candidate tags from subject area, data domain, sensitivity theme, and lifecycle
  (see `tag-taxonomy.md`).
- Map each candidate to an **existing applicable tag** from `GET /v1/tags`: any tenant-scoped
  tag, or a domain-scoped tag whose `scope.domainId` matches the workspace's current domain.
  Apply Tags takes tag **IDs**, not names.
- A candidate found only in another domain is not applicable and must be excluded. A candidate
  with no definition can't be applied: say the appropriate Fabric or domain admin would need
  to create it, and exclude it from `applyTags`.

## Table and column descriptions

Tables and columns get **descriptions only** — tags exist only on items. The rules for item
descriptions still apply (ground in content, validate existing text, never fabricate), with a
different level of detail:

- **Table** — what the table holds and what it is used for, in plain business language. A
  sentence or two. Template: `<What the table holds> used for <purpose>.` e.g. `Taxi trips with
  pickup, drop-off and fare details, used for trip volume, fare, and route analysis.` Avoid
  technical phrasing such as "one row per".
- **Column** — what the value **means**, plus units or allowed codes when the name doesn't make it
  obvious. One short sentence. e.g. `Total amount charged to the passenger, in US dollars.`
- Ground suggestions in column **names and types** only. Never read rows, and never put sample
  values, ranges, counts, or statistics in a description.
- Propose only for tables and columns whose description is empty or doesn't match the schema;
  report the ones that are already fine. Skip columns whose meaning you can't infer from the
  name and type — list them for the owner to describe.
- Column names are fine to mention in a **table** description when they define the table's key;
  the item-level "no column names" rule is about the item description only.

## Owner language

Show suggestions in the preview's Proposed column and report results as Saved, Skipped or Not
saved. Don't use bracket tags such as `[DATA]`, `[INFERENCE]` or `[GAP]`: say in plain words
what can't be done, why, and who can act.
