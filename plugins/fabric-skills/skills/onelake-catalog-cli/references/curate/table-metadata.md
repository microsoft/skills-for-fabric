# Table & Column Descriptions (OneLake Table API, preview)

How to read and write descriptions for the tables and columns inside an item. Descriptions are
the owner-curated field the OneLake catalog uses for tables and columns, so they directly help
people understand the data.

Tables and columns can carry **two different fields** — read both before proposing anything:

1. **Delta comments** stored in the table itself, usually technical notes from whoever built the
   table (for example `COMMENT` / `ALTER TABLE ... ALTER COLUMN ... COMMENT` in a notebook). Read
   them with the OneLake **Delta metadata API** (read-only). The skill never changes them.
2. **Descriptions** stored as additional metadata by the OneLake table API (preview). This is the
   owner-curated field the skill proposes and writes.

A comment does **not** replace a description.

## Contents

- [Scope](#scope)
- [Endpoint and authentication](#endpoint-and-authentication)
- [Read comments and descriptions](#read-comments-and-descriptions)
- [Find tables and shortcuts](#find-tables-and-shortcuts)
- [Read-modify-write (mandatory)](#read-modify-write-mandatory)
- [Shortcut tables](#shortcut-tables)
- [Review flow for many tables and columns](#review-flow-for-many-tables-and-columns)
- [Limits](#limits)
- [Errors](#errors)
- [Example](#example)

## Scope

- Only items with a top-level OneLake **Tables** folder, such as a Lakehouse. For any other item
  (semantic models, reports, notebooks, pipelines, …) this file doesn't apply. Don't bring up
  table or column descriptions for them; only if the owner asks, say this skill doesn't support
  them for that item type.
- **Descriptions only** — the table description and column descriptions.
- Fabric tags exist only on items. The API also stores a `tags` field per table and column; it is
  **not** Fabric tags. Never propose, edit, or mention it to the owner — keep it exactly as read.
- The API is in **public preview**; say so when a write fails and fall back to item-level curation.

## Endpoint and authentication

```text
GET  https://onelake.table.fabric.microsoft.com/common/v1/{workspaceId}/{itemId}/schemas/{schema}/tables/{table}/additionalMetadata
POST https://onelake.table.fabric.microsoft.com/common/v1/{workspaceId}/{itemId}/schemas/{schema}/tables/{table}/additionalMetadata
```

- Use GUIDs for workspace and item. URL-encode the schema and table names as separate segments.
- Token audience is **Azure Storage** (`https://storage.azure.com`), the same as OneLake file access
  (see `COMMON-CLI.md` § OneLake Data Access via curl, linked from `SKILL.md`). Use `curl`, not
  `az rest`. A Fabric API token returns `401`.
- The `x-ms-fabric-skill` header is not needed: this host is not `api.fabric.microsoft.com`.
- `POST` needs `Content-Type: application/json`. Both return `200 OK` with the full metadata.

Response / request shape (fields may be absent):

```json
{
  "description": "Sales transactions used for revenue reporting.",
  "tags": { "owner": "sales-analytics" },
  "columns": [
    { "columnName": "customer_id", "description": "Identifier of the customer on the sale.", "tags": {} }
  ]
}
```

## Read comments and descriptions

**Delta comments** — one read-only call per table returns the table comment and every column's
name, type, and comment (same Storage token):

```text
GET https://onelake.table.fabric.microsoft.com/delta/{workspaceId}/{itemId}/api/2.1/unity-catalog/tables/{itemId}.{schema}.{table}
```

Use `comment` (table) and `columns[].name` / `type_name` / `comment`. List a schema's tables with
`GET .../unity-catalog/tables?catalog_name={itemId}&schema_name={schema}` (that list omits
columns and comments, so get each table).

**Descriptions** — `GET .../additionalMetadata` (above); an empty `{}` means none stored.

How to decide:

- Judge the **description** on its own. Propose one where it is empty or doesn't match the schema,
  even if a Delta comment exists. Report good descriptions as already curated.
- A table with **no columns** is empty: say so and propose nothing for it. A table with columns
  is described from its columns even if it has no rows yet — never read rows to find out.
- Use an existing comment as an internal content signal: build the proposed description on it,
  and if it already reads well as a description, propose it as is. Ignore a comment that doesn't
  match the schema. **Don't show or mention comments to the owner** — they see only descriptions.
- **Never suggest changing a comment.** Comments are out of scope; only descriptions are
  proposed and written.

## Find tables and shortcuts

- List schemas and tables with the Delta metadata API (above); its `columns` give names and
  types. Use only names and types — never read table rows.
- List the item's shortcuts (`GET /v1/workspaces/{ws}/items/{id}/shortcuts`). Join each
  shortcut's `path` and `name` into a full path. Table `{schema}.{table}` is behind a shortcut
  when that full path is `Tables/{schema}/{table}`, `Tables/{schema}` (a **schema** shortcut —
  every table under it), or, in a lakehouse without schemas, `Tables/{table}`.

## Read-modify-write (mandatory)

A `POST` **replaces** all of the table's additional metadata. A body with only `description`
deletes every column description and any stored `tags`. So, per table:

1. `GET` the current metadata **after** the owner approves, immediately before writing — never
   reuse the read from the preview. If the read fails, stop: don't write that table.
2. Change only the descriptions the owner accepted. Keep every other field, column entry, and
   `tags` value exactly as read. Add a column entry only for an accepted new column description.
3. `POST` the complete updated document — in the **same command** as the `GET` in step 1 (see the
   example), so nothing waits between them.
4. `GET` again and confirm the accepted descriptions are present and nothing else changed.

Write one table at a time. If the second `GET` shows something you did not intend, report it.

**No concurrency check.** The API has no ETag or version check, so a change someone else makes
between your `GET` and `POST` is overwritten, and the second `GET` can't reveal it. Read-modify-write
protects the fields you read, not concurrent edits. Don't write a table the owner says someone else
is editing right now, and never claim concurrent changes were preserved.

## Shortcut tables

A shortcut is a pointer to a table stored somewhere else — often another lakehouse, workspace,
or owner. There is only **one** set of descriptions, and it belongs to the **source** table.
Writing through the shortcut changes the source table's descriptions, which everyone using the
source (and any other shortcut to it) will see.

- In the preview, mark the table as a shortcut and name the source item and workspace.
- Default to **not** writing it; write only if the owner explicitly confirms that table.
- Writing needs permission on **both** the shortcut and the source table — say so in the preview.
  Others (the source's owner, or users of other shortcuts to it) may also edit its descriptions:
  ask the owner to confirm no one is editing them right now, and don't write if they're unsure.
  If the write is refused (`403`), tell the owner plainly that they don't have permission to
  change the source table's descriptions, name the source item and workspace, and suggest asking
  its owner. Then continue with the remaining tables.

## Review flow for many tables and columns

- Number every suggestion: the table description and each column description.
- Propose descriptions only for tables and columns whose description is empty or doesn't match
  the schema; say which ones are already fine.
- With many tables, review **one table at a time** — its description and its columns — and
  write that table only after its review. Never write suggestions the owner hasn't seen.
- The owner can accept, edit, or reject each suggestion, or skip the whole table.

## Limits

| Field | Limit |
|---|---|
| Table description | 1,024 characters (keep it to a sentence or two) |
| Column description | 1,024 characters (keep it to one short sentence) |

## Errors

| Response | Meaning / action |
|---|---|
| `401` | Wrong token audience — use a Storage token. |
| `403` | Tell the owner plainly they don't have permission to change this table's descriptions. For a shortcut, name the source item and workspace and suggest asking its owner. Skip the table and continue. |
| `404` | Table, schema, or route not found, or the API isn't available for this item — say that table's descriptions can't be read or changed. |
| Other | Error body is `{ "error": { "code", "message", "target"?, "details"? } }`. Report the message and the `x-ms-root-activity-id` response header; never log the token. |

## Example

```bash
URL="https://onelake.table.fabric.microsoft.com/common/v1/$WS_ID/$ITEM_ID/schemas/dbo/tables/sales/additionalMetadata"

# After approval: fresh read, then write. -f and && stop the chain on any failed read or write,
# so an error body is never turned into a replacement document.
# Owner accepted: table description + description for customer_id. Everything else is kept as read.
curl -fsS -H "Authorization: Bearer $STORAGE_TOKEN" -H "Accept: application/json" "$URL" -o /tmp/current.json \
&& jq -e 'type == "object"' /tmp/current.json > /dev/null \
&& jq --arg d "Sales transactions used for revenue reporting." \
      --arg c "customer_id" --arg cd "Identifier of the customer on the sale." '
     .description = $d
     | .columns = ((.columns // []) as $cols
         | if any($cols[]; .columnName == $c)
           then $cols | map(if .columnName == $c then .description = $cd else . end)
           else $cols + [{columnName: $c, description: $cd}] end)
   ' /tmp/current.json > /tmp/updated.json \
&& curl -fsS -X POST -H "Authorization: Bearer $STORAGE_TOKEN" -H "Content-Type: application/json" \
     -H "Accept: application/json" --data @/tmp/updated.json "$URL" \
&& curl -fsS -H "Authorization: Bearer $STORAGE_TOKEN" -H "Accept: application/json" "$URL"
```
