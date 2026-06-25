---
name: fabriciq-ontology-authoring-cli
description: 'Create and evolve Fabric IQ Ontology (preview) items from CLI — define entity types, properties (including timeseries), relationship types, and bind them to OneLake lakehouse tables (static + timeseries) or Eventhouse / KQL database tables (timeseries only). Uses the Fabric item-definition REST API (Create Item / Update Item Definition) with `InlineBase64` parts. Use to create a Fabric Ontology item; add or alter entity types, properties, or keys; add timeseries properties and bindings; bind an entity type to a lakehouse or Eventhouse table; add relationship types and contextualizations; or script ontology deployment from source. Triggers: "create fabric ontology", "add ontology entity type", "bind entity type to lakehouse", "bind entity type to eventhouse", "ontology timeseries binding", "add ontology relationship type", "ontology contextualization", "fabric iq ontology authoring", "update ontology definition"'
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare against remote via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If remote is newer, show the changelog and update instructions.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. Ontology is **preview**. The item type value is `Ontology`. Features and wire format may change; validate against the current docs before production use.
> 2. To find the workspace details (including its ID) from workspace name: list all workspaces and use JMESPath filtering.
> 3. To find the item details (including its ID) from workspace ID, item type (`Ontology`), and item name: list all items of that type in that workspace and use JMESPath filtering.
> 4. Authoring a relationship type requires **two distinct entity types** that already exist in the ontology. The `source.entityTypeId` and `target.entityTypeId` values are the **entity type IDs you assigned**, not item IDs.
> 5. Data bindings reference a source table by `workspaceId`, `itemId`, `sourceTableName`, and — for lakehouse sources — `sourceSchema`. Lakehouse (`LakehouseTable`) sources carry the lakehouse item ID; Eventhouse (`KustoTable`) sources carry the **Eventhouse item ID** plus `clusterUri` and `databaseName`. Key column(s) on the source side must match the entity type's key property(ies). Eventhouse sources are `TimeSeries`-only; the static (`NonTimeSeries`) binding must come from a lakehouse.

# fabriciq-ontology-authoring-cli — Fabric Ontology Authoring via CLI

## Table of Contents

| Task                                           | Reference                                                                                                                                              | Notes                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Finding Workspaces and Items in Fabric         | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)                            | **Mandatory** — resolve workspace/item IDs before authoring                  |
| Fabric Topology & Key Concepts                 | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts)                                           | Workspace → Item hierarchy                                                   |
| Authentication & Token Acquisition             | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition)                                   | Use `https://api.fabric.microsoft.com` audience for control plane            |
| Core Control-Plane REST APIs                   | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis)                                              | Create Item, Get/Update Item Definition                                      |
| Long-Running Operations (LRO)                  | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro)                                              | Item create/update returns an LRO                                            |
| Rate Limiting & Throttling                     | [COMMON-CORE.md § Rate Limiting & Throttling](../../common/COMMON-CORE.md#rate-limiting--throttling)                                                   |                                                                              |
| Authentication Recipes                         | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes)                                                            | `az login`; token acquisition                                                |
| Fabric Control-Plane API via `az rest`         | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest)                                | **Always** pass `--resource https://api.fabric.microsoft.com`                |
| Long-Running Operations (LRO) Pattern          | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern)                                | For Ontology create/update, poll `/v1/operations/{x-ms-operation-id}` on the Fabric host — see [LRO Header Capture](#lro-header-capture-with-az-rest) |
| Gotchas & Troubleshooting (CLI-Specific)       | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific)                           | Token audience, shell escaping                                               |
| `az rest` Template                             | [COMMON-CLI.md § `az rest` Template](../../common/COMMON-CLI.md#az-rest-template)                                                                      |                                                                              |
| Definition Envelope (parts, payloadType)       | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope)                                            | `InlineBase64` parts pattern used for Ontology                               |
| Ontology Definition Reference                  | [ONTOLOGY-AUTHORING-CORE.md § Definition Tree](references/ONTOLOGY-AUTHORING-CORE.md#definition-tree)                                                | Authoritative file/folder layout for the ontology item                       |
| EntityType & EntityTypeProperty schema         | [ONTOLOGY-AUTHORING-CORE.md § EntityType file](references/ONTOLOGY-AUTHORING-CORE.md#entitytype-file--entitytypesiddefinitionjson)                   | Allowed `valueType` values, key constraints, name regex                      |
| DataBinding schema + source-type mapping       | [ONTOLOGY-AUTHORING-CORE.md § DataBinding file](references/ONTOLOGY-AUTHORING-CORE.md#databinding-file--entitytypesiddatabindingsguidjson)           | Lakehouse & Eventhouse shapes; value-type mapping; binding rules             |
| RelationshipType + Contextualization schema    | [ONTOLOGY-AUTHORING-CORE.md § RelationshipType file](references/ONTOLOGY-AUTHORING-CORE.md#relationshiptype-file--relationshiptypesiddefinitionjson) | Source/target constraints, link table requirements                           |
| Ontology Concepts                              | [SKILL.md § Ontology Item Concepts](#ontology-item-concepts)                                                                                           | Entity types, properties, bindings, relationship types                       |
| Tool Stack                                     | [SKILL.md § Tool Stack](#tool-stack)                                                                                                                   |                                                                              |
| Connection                                     | [SKILL.md § Connection](#connection)                                                                                                                   | Discover workspace, lakehouse, ontology IDs                                  |
| Authoring Scope                                | [SKILL.md § Authoring Scope](#authoring-scope)                                                                                                         | Supported operations at a glance                                             |
| Authoring Mechanics (full reference)           | [authoring-mechanics.md](references/authoring-mechanics.md)                                                                                            | Envelope, IDs, create, entity types, bindings, relationships, update, verify |
| Worked Examples                                | [examples.md](references/examples.md)                                                                                                                  | End-to-end bash recipes (create → bind → relationship → timeseries)          |
| Preview & Confirm (mandatory before LRO write) | [preview-and-confirm.md](references/preview-and-confirm.md)                                                                                            | ASCII proposal (greenfield) / change-set diff (brownfield)                   |
| Script Templates                               | [definition-script-templates.md](references/definition-script-templates.md)                                                                            | Bash / PowerShell fetch-mutate-send scaffolds                                |
| Must / Prefer / Avoid / Troubleshooting        | [SKILL.md § Must / Prefer / Avoid / Troubleshooting](#must--prefer--avoid--troubleshooting)                                                            | LLM decision rules                                                           |
| Agentic Workflows                              | [SKILL.md § Agentic Workflows](#agentic-workflows)                                                                                                     | Exploration-before-authoring, script generation                              |
| Agent Integration Notes                        | [SKILL.md § Agent Integration Notes](#agent-integration-notes)                                                                                         | How this skill composes with agents / other skills                           |

---

## Ontology Item Concepts

A Fabric Ontology item is authored as a **tree of JSON files** inside the item definition. Each file is carried as a part in the `parts[]` array of the Create/Update definition envelope (payloadType `InlineBase64`).

| Concept | Definition file path | Purpose |
|---|---|---|
| Ontology envelope | `definition.json` | Empty `{}`; required |
| Platform metadata | `.platform` | `{ "metadata": { "type": "Ontology", "displayName": "<name>" } }` |
| Entity type | `EntityTypes/{entityTypeId}/definition.json` | Name, namespace, key(s), display name property, properties[], timeseriesProperties[] |
| Entity type data binding | `EntityTypes/{entityTypeId}/DataBindings/{guid}.json` | Maps a lakehouse **or eventhouse** table to properties; `dataBindingType` = `NonTimeSeries` or `TimeSeries`. Eventhouse (`KustoTable`) sources are allowed **only** for `TimeSeries` |
| Entity type documents | `EntityTypes/{entityTypeId}/Documents/{name}.json` | Optional doc links |
| Entity type overviews | `EntityTypes/{entityTypeId}/Overviews/definition.json` | Optional widgets layout |
| Entity type resource links | `EntityTypes/{entityTypeId}/ResourceLinks/definition.json` | Optional Power BI / item links |
| Relationship type | `RelationshipTypes/{relTypeId}/definition.json` | Source + target entity type IDs, name |
| Relationship contextualization | `RelationshipTypes/{relTypeId}/Contextualizations/{guid}.json` | Source/target key bindings onto a lakehouse table |

Property `valueType` allowed values (exact): `String`, `Boolean`, `DateTime`, `Object`, `BigInt`, `Double`. Use `BigInt` — **not** `Int64` — for integers; there is no `Guid` value type (model GUIDs as `String`). Timeseries bindings require a timestamp column (source type `datetime` / `date` / `timestamp`) and a `TimeSeries` binding with `timestampColumnName`. See [ONTOLOGY-AUTHORING-CORE.md § EntityTypeProperty](references/ONTOLOGY-AUTHORING-CORE.md#entitytypeproperty) for the full source-column → `valueType` mapping.

> **⚠️ Property names must be unique across both `properties[]` and `timeseriesProperties[]`** within a single entity type. If a lakehouse table and an Eventhouse table both contain a column with the same name (e.g., `tenant_id`), you **must** rename one of the ontology property names to avoid a collision. The `sourceColumnName` in the binding can still point to the original column — only the ontology property `name` must be unique. For example, keep the static property as `TenantId` and name the timeseries one `TsTenantId`.
>
> **⚠️ Property names with the same `name` across different entity types must share the same `valueType`** — the ontology enforces name-level type consistency across the entire definition. If `SerialNum` is `String` on one entity type, it cannot be `BigInt` on another. Either use the same `valueType` everywhere, or disambiguate with a prefix (e.g., `SerialNumStr` vs `SerialNumInt`).
>
> **⚠️ Part paths must always use forward slashes** (`EntityTypes/{id}/definition.json`), never backslashes. On Windows, PowerShell path-joining operators (`Join-Path`, `\`) produce backslashes that the Fabric API rejects with `ALMOperationBadRequest`. Always build part paths with string interpolation using `/`.

---

## Tool Stack

Ontology authoring uses the same Fabric control-plane tool stack as every other CLI skill — see [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) for the canonical list (install commands, prerequisite checks, base64 helpers, JSON tooling) and [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) for `az login` + token acquisition.

Ontology-specific tool guidance below covers only the gotchas that hit `createItem` / `updateDefinition` payloads.

> **⚠️ PowerShell `ConvertTo-Json` Warning**: PowerShell's `ConvertTo-Json` can silently reorder keys and serialize `$null` differently than JSON `null`, which can cause `ALMOperationImportFailed` errors on `updateDefinition`. To avoid this:
>
> 1. **Always use `[System.IO.File]::WriteAllText`** with `[System.Text.UTF8Encoding]::new($false)` to write JSON files — `Out-File` and `Set-Content` add a BOM that corrupts the payload.
> 2. **Build JSON with `jq`** instead of `ConvertTo-Json` where possible — `jq -nc` produces deterministic, compact JSON without PowerShell serialization quirks:
>    ```powershell
>    $json = '{}' | jq -nc --arg id "$ET_ID" --arg name "Site" '{id:$id,name:$name}'
>    ```
> 3. **Validate** the JSON before sending: `Get-Content envelope.json | jq .` — if `jq` fails, the payload is malformed.
> 4. **Use `-Depth 10`** on `ConvertTo-Json` — the default depth of 2 silently truncates nested objects.

> **⚠️ Avoid `certutil -encode` for `InlineBase64` parts.** Its output is line-wrapped with a header/footer and must be post-processed before use. On Windows, use PowerShell's `[Convert]::ToBase64String([IO.File]::ReadAllBytes($path))` instead.

---

## Connection

Ontology authoring targets the Fabric control plane. Before composing the definition you need: `WS_ID` (workspace), `LH_ID` (lakehouse item ID for static + lakehouse-timeseries bindings), and — for Eventhouse-backed timeseries — the Eventhouse item ID, KQL cluster URI, and KQL database name.

- Sign in + acquire the Fabric control-plane token → [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) (always `--resource https://api.fabric.microsoft.com`).
- Resolve workspace, folder, lakehouse, and ontology item IDs by `displayName` → [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) (covers pagination + JMESPath filtering).
- Generic `az rest` invocation template → [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest).

The Ontology-specific resolution gotchas (folder GUID vs. portal numeric ID, Eventhouse ID field mapping, schema discovery for bindings, LRO header capture on the preview redirect host) follow.

### Folder (Ontology-specific gotcha)

The `folderId` field on the Ontology create payload requires the **folder GUID** — not the numeric `subfolderId` shown in portal URLs. Passing the portal number fails with `400 InvalidParameter … cannot convert "<numeric>" to Guid … Path 'folderId'`. Resolve the GUID by listing `GET /v1/workspaces/{WS_ID}/folders` (per [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)) and filter by `displayName`.

### Eventhouse / KQL Database (for TimeSeries bindings)

Ontology `TimeSeries` bindings backed by Eventhouse require three fields in the `KustoTable` data-binding payload — sourced from the KQL database record returned by `GET /v1/workspaces/{WS_ID}/kqlDatabases`:

| KustoTable binding field | Source field on the KQL-database record |
|---|---|
| `itemId`        | `properties.parentEventhouseItemId` — **the Eventhouse item ID, not the KQL database's own `id`** |
| `clusterUri`    | `properties.queryServiceUri` |
| `databaseName`  | `displayName` (use the canonical casing returned by the API) |

> **Eventhouse tables can back `TimeSeries` bindings only.** The entity type's static (`NonTimeSeries`) binding must still come from a managed lakehouse table.

> **Common mistake**: passing the KQL database's own `id` as the `KustoTable.itemId`. Use `parentEventhouseItemId` from the same record.

For the generic `kqlDatabases` listing call (pagination + JMESPath filter by `displayName`), see [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric).

### Schema Discovery

Before composing bindings, discover the source table schemas so you map the correct column names. **Use companion skills for schema discovery** — they are faster and more reliable than raw REST calls.

- **Lakehouse tables** → route to the `sqldw-consumption-cli` skill and query `INFORMATION_SCHEMA.COLUMNS` against the lakehouse SQL endpoint (returns all tables + columns in one query). If unavailable, fall back to the Fabric Tables REST API plus the OneLake Table API for Iceberg metadata.
- **Eventhouse / KQL tables** → route to the `eventhouse-consumption-cli` skill and run `.show database schema as json` (returns every table + column in a single response). For a single table, use `.show table <name> schema as json`.

Use the column types returned here to fill `valueType` on each `EntityTypeProperty` — see the source-column → `valueType` mapping in [ONTOLOGY-AUTHORING-CORE.md § EntityTypeProperty](references/ONTOLOGY-AUTHORING-CORE.md#entitytypeproperty).

### LRO Header Capture with `az rest`

`az rest` does not expose response headers by default. Both `createItem` and `updateDefinition` return **202 Accepted** with an `x-ms-operation-id` header (and a `Location` header). Use `--verbose` and parse stderr to capture the operation id:

> **Prefer polling with `x-ms-operation-id` over the raw `Location` header for Ontology create/update.** The public [Fabric LRO contract](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation) supports polling either the `Location` header or `https://api.fabric.microsoft.com/v1/operations/{operationId}` (from `x-ms-operation-id`). In **current Ontology preview behavior**, observed `Location` values point at an `analysis.windows.net` redirect host (e.g. `https://df-…-redirect.analysis.windows.net/v1/operations/{id}`), not `api.fabric.microsoft.com`; polling that URL with `az rest --resource https://api.fabric.microsoft.com` re-authenticates against the wrong audience and fails with 401/403 — which hides the LRO status/error and leads to blind-retry loops. So capture `x-ms-operation-id` and poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` (Fabric host, Fabric token). If you do follow `Location`, use the audience that URL requires.

```bash
# Bash — capture x-ms-operation-id from az rest --verbose stderr
OP_ID=$(az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body @envelope.json --verbose 2>&1 \
  | grep -oiP "(?<=x-ms-operation-id': ')[^']+")

# Poll the Fabric operations endpoint (stays on api.fabric.microsoft.com)
while :; do
  OP=$(az rest --method GET \
    --url "https://api.fabric.microsoft.com/v1/operations/${OP_ID}" \
    --resource "https://api.fabric.microsoft.com")
  STATUS=$(printf '%s' "$OP" | jq -r .status)
  case "$STATUS" in
    Succeeded) break ;;
    Failed|Cancelled)
      # Read the error and FIX the payload — never blind-retry the same body.
      printf '%s' "$OP" | jq -r '.error | "\(.errorCode // .code): \(.message)"' >&2
      exit 1 ;;
    *) sleep 5 ;;
  esac
done
```

```powershell
# PowerShell — capture x-ms-operation-id from az rest --verbose stderr
$result = az rest --method POST `
  --resource "https://api.fabric.microsoft.com" `
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/items" `
  --headers "Content-Type=application/json" `
  --body "@envelope.json" --verbose 2>&1
$opId = ($result | Select-String -Pattern "x-ms-operation-id': '([^']+)'" |
  ForEach-Object { $_.Matches[0].Groups[1].Value })

# Poll the Fabric operations endpoint (stays on api.fabric.microsoft.com)
do {
  Start-Sleep -Seconds 5
  $op = az rest --method GET `
    --url "https://api.fabric.microsoft.com/v1/operations/$opId" `
    --resource "https://api.fabric.microsoft.com" | ConvertFrom-Json
} while ($op.status -notin 'Succeeded','Failed','Cancelled')
if ($op.status -ne 'Succeeded') {
  # Read .error and FIX the payload — never blind-retry the same body.
  throw "createItem LRO $($op.status): $($op.error.errorCode) $($op.error.message)"
}
```

> **Important**: `createItem` returns 202 with **no response body** — `az rest` exits with code 0 and prints nothing. This is normal. After the operation reaches `Succeeded`, list items to capture the new item ID. If `status` is `Failed`, the `error` field names the cause (e.g. a malformed entity-type part) — fix the payload and submit a corrected request rather than re-sending the same body.

---

## Authoring Scope

| Operation | Fabric REST Call | Definition Parts Touched |
|---|---|---|
| Create empty ontology | `POST /v1/workspaces/{ws}/items` with `type=Ontology` | `.platform`, `definition.json` |
| Add / alter entity type | `POST /v1/workspaces/{ws}/items/{id}/updateDefinition` | `EntityTypes/{id}/definition.json` |
| Bind entity type to table (non-timeseries) | `updateDefinition` | `EntityTypes/{id}/DataBindings/{guid}.json` with `NonTimeSeries` |
| Bind entity type to table (timeseries) | `updateDefinition` | `EntityTypes/{id}/DataBindings/{guid}.json` with `TimeSeries` + `timestampColumnName` |
| Add relationship type | `updateDefinition` | `RelationshipTypes/{id}/definition.json` |
| Bind relationship (contextualization) | `updateDefinition` | `RelationshipTypes/{id}/Contextualizations/{guid}.json` |
| Delete entity / relationship | `updateDefinition` with that path omitted from parts | — |
| Rename ontology | `updateDefinition` with `updateMetadata=true` and new `.platform` | `.platform` |

> **Update Item Definition replaces the full tree of included parts.** Always fetch the current definition via `Get Item Definition`, mutate the parts locally, and resend the complete desired set.

---

## Authoring Reference

Full JSON shapes, field contracts, and verification recipes for each operation live in [authoring-mechanics.md](references/authoring-mechanics.md). Worked end-to-end bash recipes live in [examples.md](references/examples.md). Use the sections below as a quick index:

| Topic | Reference |
|---|---|
| Definition envelope (`parts[]`, `InlineBase64`, base64 helpers) | [authoring-mechanics.md § Definition Envelope](references/authoring-mechanics.md#definition-envelope-for-ontology) |
| ID generation (64-bit ints, GUIDs, `name → id` map) | [authoring-mechanics.md § ID Generation Pattern](references/authoring-mechanics.md#id-generation-pattern) |
| Create empty ontology | [authoring-mechanics.md § Create the Ontology Item](references/authoring-mechanics.md#create-the-ontology-item) |
| Add an entity type | [authoring-mechanics.md § Add an Entity Type](references/authoring-mechanics.md#add-an-entity-type) |
| Bind to lakehouse / eventhouse | [authoring-mechanics.md § Bind an Entity Type](references/authoring-mechanics.md#bind-an-entity-type-to-a-lakehouse-or-eventhouse-table) |
| Relationship types + contextualizations | [authoring-mechanics.md § Add a Relationship Type](references/authoring-mechanics.md#add-a-relationship-type) |
| Apply a definition update (fetch → mutate → send) | [authoring-mechanics.md § Apply a Definition Update](references/authoring-mechanics.md#apply-a-definition-update) |
| Verify and inspect | [authoring-mechanics.md § Verify and Inspect](references/authoring-mechanics.md#verify-and-inspect) |
| Complete Bash / PowerShell scaffolds | [definition-script-templates.md](references/definition-script-templates.md) |

**Core invariants to keep in mind when authoring (full detail in the reference files):**

- Envelope shape: `{ "displayName", "type": "Ontology", "definition": { "parts": [ { "path", "payload", "payloadType": "InlineBase64" } ] } }`; `definition.json` is literally `{}`; `.platform` carries `metadata.type: "Ontology"` + `displayName`.
- IDs: entity / relationship / property IDs are **positive 64-bit integers**, data binding / contextualization IDs are **GUIDs**. Persist the `name → id` map in source control; never reuse an ID for a different concept.

**ID map template** — persist this alongside your deployment scripts (JSON or YAML):

```json
{
  "ontologyName": "SkillTest_Fleet",
  "entityTypes": {
    "Site":      { "id": "1048860412765431174", "properties": { "SiteId": "1428056703884423742", "SiteName": "4251708967918658190" } },
    "Equipment": { "id": "3332700945676096991", "properties": { "EquipmentId": "4585483423451989345" } }
  },
  "relationshipTypes": {
    "EquipmentAtSite": { "id": "4242053467032157032" }
  },
  "bindings": {
    "Site_static":      "25e3a44a-b62a-40e3-a64a-a43caaa92d19",
    "Equipment_static": "5dc4cadd-3700-4c96-bb1e-41e4c909ae4d"
  }
}
```
- Bindings: `NonTimeSeries` is **lakehouse-only** and at most one per entity type; a `NonTimeSeries` binding is required **before** any `TimeSeries` binding on the same entity type; `TimeSeries` can be lakehouse or Eventhouse; for `KustoTable`, `itemId` is the **Eventhouse item ID** (not the KQL database ID).
- Relationships: `source.entityTypeId` and `target.entityTypeId` must be distinct and must reference entity types present in the parts tree.
- Updates replace the included parts wholesale — **always** fetch the current definition, mutate locally, then send.

---

## Must / Prefer / Avoid / Troubleshooting

### Must

- **Require explicit ontology context before routing here** — the prompt must ask to create or change an "ontology" (or reference an ontology item). Generic "Fabric IQ" prompts without ontology context are not ontology-authoring tasks; defer them to the matching skill. This keeps the shared "Fabric IQ" brand from over-triggering this skill.
- **Clarify before acting on ambiguous prompts** — never infer schema or bindings. If the user says "create an ontology for airline data" without naming entity types, their keys, or the lakehouse tables, ask what entities, what keys, and which lakehouse tables. Irreversible side-effects (replacing an ontology definition) require explicit user intent.
- **Resolve `WS_ID` and source item IDs before composing any binding** — hardcoded GUIDs are a top-3 failure mode. Lakehouse bindings need the lakehouse `itemId`; eventhouse bindings need the eventhouse `itemId`, cluster URI, and database name.
- **Fetch the current definition before any update** — `updateDefinition` replaces included parts wholesale. Merging with stale local state silently drops recent changes. Handle the LRO 202 on `getDefinition` (poll and retrieve via the operation's `result` endpoint).
- **Persist the `name → id` map** for entity types, relationship types, and properties in source control alongside the skill consumer's repo. Regenerating IDs on every run creates duplicates and breaks references.
- **Add the static (`NonTimeSeries`) binding before any timeseries binding** on an entity type — each entity type supports at most one static binding, and timeseries binding requires the static key property to already be populated.
- **Bind only to managed lakehouse tables** — external tables, lakehouses with OneLake security enabled, and delta tables with column mapping enabled are not supported.
- **Ensure property names are unique across `properties[]` and `timeseriesProperties[]`** within each entity type. When a lakehouse table and an Eventhouse table share a column name (e.g., `tenant_id`, `device_id`), rename the ontology timeseries property (e.g., `TsTenantId`) while keeping `sourceColumnName` pointing at the original column. Duplicate property names cause `ALMOperationImportFailed`.
- **Observed (preview): restrict entity keys (`entityIdParts`) to properties whose `valueType` is `String` or `BigInt`** — other value types have not been accepted as keys in current preview behavior. This restriction is not documented on public Microsoft Learn; verify against your tenant before relying on it.
- **Use forward slashes in all part paths** — `EntityTypes/{id}/definition.json`, never `EntityTypes\{id}\definition.json`. On Windows, `Join-Path` and `\` produce backslashes that the Fabric API rejects. Build paths with string interpolation: `"EntityTypes/$ET_ID/definition.json"`.
- **Verify permissions** — authoring requires at least `Contributor` on the workspace.
- **Treat the item type as `Ontology`** (not `OntologyPreview` or similar) in both the envelope's `type` and the `.platform` metadata.
- **Render a Preview & Confirm gate before every LRO write** — render an ASCII proposal (greenfield) or a change-set diff vs. `getDefinition` (brownfield) and obtain explicit `yes` from the user before calling `createItem` or `updateDefinition`. See [preview-and-confirm.md](references/preview-and-confirm.md). Anything other than `yes` means stop and revise; never partially apply.

### Prefer

- **Building the definition tree on disk** (one JSON per logical part, mirroring the `EntityTypes/{id}/...` layout) and base64-encoding each file just before sending. This keeps diffs reviewable.
- **Starting from a `getDefinition` dump** of an existing known-good ontology when onboarding, then mutating.
- **Lakehouse-first static binding; Eventhouse for time-series** — OneLake (lakehouse) is the only supported source for `NonTimeSeries` bindings. Use Eventhouse (`KustoTable`) for high-volume telemetry on `TimeSeries` bindings, or mirror/shortcut the data into a lakehouse table if the team prefers a single source kind.
- **Idempotent deploy scripts** — re-running the script with unchanged inputs should produce an unchanged ontology.
- **Scripted workflow over UI** when more than one entity type or environment is involved.
- **Triggering a manual graph-model refresh** after upstream data writes — new rows in bound sources are not visible in the preview experience until the ontology is refreshed.

### Avoid

- **Generating monolithic `.ps1` or `.sh` script files** — execute commands directly in the shell. Large generated scripts introduce escaping bugs, PowerShell parse errors, and are hard to debug when a single line fails. Build JSON with `jq -nc`, write to a temp file, and pass to `az rest --body @file`.
- **Hand-editing base64 payloads** — always decode, edit the JSON, then re-encode.
- **Reusing a property/entity/relationship ID** for a different concept.
- **Relying on relationship-name uniqueness outside the ontology scope** — today, relationship names appear to be unique within an ontology (observed behavior); collect the full set of desired relationship names up front so you can disambiguate with prefixes if needed. Confirm naming collisions with the consumer rather than guessing.
- **Embedding secrets, SAS tokens, or user tokens** in `.platform` or any part.
- **Creating relationship types before their source and target entity types exist in the parts list**.
- **Treating `Object` / JSON properties as fully queryable** — observed behavior today is that nested JSON bound to an `Object` property surfaces as an opaque payload rather than being addressable like a scalar. For nested payloads, keep the raw data in Eventhouse and bind only the addressable scalar fields. Verify with a `getDefinition` round-trip before promising downstream consumers a specific query shape.
- **Relying on "delete by omission"** — parts not included in the `updateDefinition` body are observed to be removed, but the skill should tell the user this is destructive and confirm before generating an envelope that drops parts.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `400 Bad Request` on create — "Invalid item type" | Wrong item type string | Use `"type": "Ontology"` and `metadata.type: Ontology` in `.platform` |
| `400 InvalidItemType` on createItem with `type: Ontology` | Tenant / workspace does not have Fabric IQ Ontology (preview) enabled | Surface to the user — do **not** retry. Ontology preview enrollment is required at the tenant level. |
| `400 InvalidParameter` on create — `Error converting value "<number>" to … Guid … Path 'folderId'` | Passed the numeric `subfolderId` from a portal URL instead of the folder GUID | Resolve the folder GUID via `GET /v1/workspaces/{WS_ID}/folders` (see Connection § Folder) and pass that |
| `400` — "Invalid value type" on property | Using `Int64` / `Guid` / `Float` as `valueType` | Allowed values are exactly `String`, `Boolean`, `DateTime`, `Object`, `BigInt`, `Double` |
| `400` — "Invalid identifier" on entity type / property | Name violates regex | Match `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`; prefer the stricter 1–26 char portal rule to stay portable |
| `400` — "Source and target must differ" | Relationship points at the same entity type twice | Choose distinct source/target entity types |
| `400` — "Referenced property not found" | `targetPropertyId` doesn't match any property in the entity type | Check IDs; ensure property was added in the same update |
| `400` — "Time series binding requires existing static binding" | Timeseries binding added before the static binding on an entity type | Add a `NonTimeSeries` binding with the key property first, then the `TimeSeries` binding |
| `400` — key column issue | Key property `valueType` is not `String` or `BigInt` | Change the property to `String` / `BigInt`, or choose a different key |
| `404` on binding | `workspaceId` / `itemId` wrong, or source item deleted | Re-resolve IDs via `list items` / `list lakehouses` / `list eventhouses` |
| Binding accepted but no instances appear | Source is external table, column-mapped delta, or OneLake-secured | Rebuild the table as a managed delta table without column mapping; remove OneLake security on the lakehouse |
| Instances empty after binding | `propertyBindings` column names don't match source columns | Inspect the source schema and fix `sourceColumnName` / `sourceSchema` |
| New upstream rows not appearing | No refresh performed | Trigger a manual graph-model refresh on the ontology item |
| Timeseries widget shows no data | `timestampColumnName` not set, or timestamp column is not a supported date/time type | Set `timestampColumnName` in the TimeSeries binding; ensure column type is `datetime` / `date` / `timestamp` |
| `getDefinition` returns `200` or `202` | LRO-capable response (may be inline envelope or operation-id) | If `202`, poll the operation until `Succeeded`, then `GET https://api.fabric.microsoft.com/v1/operations/{operationId}/result`; if `200`, parse the returned envelope directly — see [LRO Header Capture](#lro-header-capture-with-az-rest) |
| LRO poll returns `401`/`403`, or the `Location` header host is `*.analysis.windows.net` | The create/update `Location` redirects to an Analysis Services host; polling it with `az rest --resource https://api.fabric.microsoft.com` re-auths against the wrong audience | Poll `https://api.fabric.microsoft.com/v1/operations/{x-ms-operation-id}` on the Fabric host instead of following the `Location` URL — see [LRO Header Capture](#lro-header-capture-with-az-rest). Do not blind-retry the create while the poll is failing |
| `Conflict` on `updateDefinition` | Concurrent edit from the portal | Re-fetch definition, re-apply mutations, resend |
| `ALMOperationImportFailed` on `updateDefinition` | Malformed JSON payload — often caused by PowerShell `ConvertTo-Json` serialization quirks (`$null` vs `null`, key reordering, BOM in file) | Build JSON with `jq -nc` instead of `ConvertTo-Json`; write files with `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` to avoid BOM; validate with `jq .` before sending — see [Tool Stack § PowerShell Warning](#tool-stack) |
| `ALMOperationImportFailed` on `createItem` or `updateDefinition` — duplicate property name | A property name appears in both `properties[]` and `timeseriesProperties[]` on the same entity type | Property names must be unique across both arrays. If a lakehouse and Eventhouse table share a column name, rename the timeseries ontology property (e.g., `TenantId` → `TsTenantId`) — the binding's `sourceColumnName` can still reference the original column |
| `ALMOperationImportFailed` — "Property 'X' has conflicting value types" | The same property `name` appears on two different entity types with different `valueType` values (e.g., `String` on one, `BigInt` on another) | Property names are unique across the entire ontology — if two entity types share a property name, both must use the same `valueType`. Disambiguate with a prefix (e.g., `SerialNumStr` vs `SerialNumInt`) or unify the type |
| `ALMOperationBadRequest` — "directory name … is not valid for EntityType" | Part `path` uses backslashes (`EntityTypes\\{id}\\definition.json`) instead of forward slashes | Always use forward slashes in part paths: `EntityTypes/{id}/definition.json`. On Windows, avoid `Join-Path` or `\` for part paths — use string interpolation with `/` |
| `createItem` returns exit code 0 but no output | Normal — `createItem` returns `202 Accepted` with no body; `az rest` treats this as success | List items after the LRO completes to capture the new item ID; use `--verbose` to capture the `x-ms-operation-id` header for LRO polling |
| `409 ItemDisplayNameAlreadyInUse` on `createItem` | Ontology with the same `displayName` already exists in the workspace | List existing ontologies first; delete or rename the existing one, or choose a different name |
| `definition.json` payload causes import error | Extra whitespace, BOM, or newlines in the base64 payload | `definition.json` must be exactly `{}` — its base64 is `e30=`. On Windows, ensure no BOM by using `[System.IO.File]::WriteAllText` with `UTF8Encoding($false)` |

---

## Agentic Workflows

> **⚠️ Do NOT generate monolithic `.ps1` / `.sh` script files.** Execute each step directly in the shell as individual commands. Generating a large script file introduces escaping bugs, parse errors, and property-access issues that are hard to debug. Instead:
> - Run `az rest`, `jq`, and PowerShell commands **directly** in the terminal
> - Build JSON payloads incrementally using `jq -nc` piped through variables
> - Write the final envelope to a temp file, then pass it to `az rest --body @file`
> - If a step fails, fix it and re-run — don't regenerate the entire script

### Exploration Before Authoring

> **Greenfield vs brownfield execution strategy:**
>
> - **Greenfield (new ontology)**: Build the **complete** definition — entity types, bindings, relationships, contextualizations, timeseries — as a single `createItem` call with all parts in one envelope. This is faster and avoids intermediate states. The `createItem` payload accepts the full `definition.parts[]` array, not just `.platform` + `definition.json`.
> - **Brownfield (updating existing)**: Execute **incrementally** — fetch the current definition, mutate, send. Verify with `getDefinition` after each `updateDefinition` to catch errors early. A failure partway through preserves prior progress.

#### Parallel Schema Discovery

When the ontology binds to **multiple data sources** (lakehouse tables + Eventhouse tables), discover schemas in parallel rather than sequentially. Launch separate discovery tasks that run concurrently:

```text
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (this skill)                                       │
│                                                                   │
│  Step 0 → Resolve workspace, folder, lakehouse ID, eventhouse ID │
│                                                                   │
│  Step 1 → Fan out schema discovery (parallel):                   │
│     ┌──────────────────────────┐  ┌────────────────────────────┐ │
│     │ TASK A: Lakehouse schemas │  │ TASK B: Eventhouse schemas │ │
│     │ sqldw-consumption-cli     │  │ eventhouse-consumption-cli │ │
│     │ or INFORMATION_SCHEMA     │  │ or .show database schema   │ │
│     │ → all tables + columns    │  │ → all tables + columns     │ │
│     └──────────┬───────────────┘  └──────────┬─────────────────┘ │
│                │                              │                   │
│  Step 2 → Merge schemas ◄────────────────────┘                   │
│     - Match entity tables (lakehouse) to telemetry (eventhouse)  │
│     - Detect property name collisions across sources             │
│     - Detect property type conflicts across entity types         │
│     - Rename collisions (e.g., TenantId → TsTenantId)           │
│                                                                   │
│  Step 3 → Propose model → PREVIEW & CONFIRM                     │
│                                                                   │
│  Step 4 → Build full envelope → createItem (single call)         │
└─────────────────────────────────────────────────────────────────┘
```

**How to fan out** (agent-specific):
- **GitHub Copilot CLI / Claude Code**: launch two background `task` agents — one for lakehouse (`sqldw-consumption-cli` or `INFORMATION_SCHEMA.COLUMNS` query), one for Eventhouse (`.show database schema as json`). Read both results when they complete.
- **Single-threaded environments**: run the two discovery queries sequentially — each is a single call, so the overhead is minimal.

The merge step (Step 2) is where most authoring bugs are caught — deduplicate property names, unify `valueType` across entities, and prefix timeseries properties that collide with static ones.

#### Detailed Step Flow

```text
Step 0 → Is the request specific? Are the entity types, keys, and lakehouse tables named?
         → NO  → Ask: "Which entity types? What is the key of each? Which lakehouse table binds to each?
                  Any timeseries properties? Any relationships and their link tables?"
                  STOP — do not proceed until the user answers.
         → YES → Continue.
Step 1 → Resolve IDs: workspace, folder, lakehouse, eventhouse     [COMMON-CLI.md]
Step 2 → Discover source schemas (parallel where possible):
           a. Lakehouse: invoke `sqldw-consumption-cli` or query INFORMATION_SCHEMA.COLUMNS
           b. Eventhouse: invoke `eventhouse-consumption-cli` or run `.show database schema as json`
Step 3 → Merge schemas: detect property name collisions + type conflicts; rename as needed
Step 4 → If ontology exists: getDefinition → decode parts              (capture current IDs)
         Else: plan `createItem` with the FULL definition (all parts in one call).
Step 5 → For each entity type:
           a. Generate/reuse 64-bit IDs for entity + properties
           b. Build EntityTypes/{id}/definition.json
           c. Build one or two DataBindings/{guid}.json files
Step 6 → For each relationship:
           a. Confirm both entity types exist in Step 5 output
           b. Generate/reuse relationship type ID
           c. Build RelationshipTypes/{id}/definition.json
           d. Build RelationshipTypes/{id}/Contextualizations/{guid}.json
Step 7 → Base64-encode all parts; assemble envelope
Step 8 → **PREVIEW & CONFIRM** — render proposal (greenfield) or change-set diff (brownfield)
         and obtain explicit `yes` from the user. See [preview-and-confirm.md](references/preview-and-confirm.md).
         Do not proceed on anything other than `yes`.
Step 9 → createItem OR updateDefinition (LRO)
Step 10 → Poll LRO until Succeeded; getDefinition; verify IDs and bindings; persist post-write snapshot for next-run diff
```

### Script Generation Workflow

```text
Step 1 → Capture user intent (entity types, keys, properties, relationships, source tables)
Step 2 → Save intent as a YAML/JSON spec in the consumer's repo — single source of truth
Step 3 → Generate: (a) the ID map, (b) per-file JSON parts, (c) the composite envelope
Step 4 → **PREVIEW & CONFIRM** — render proposal/diff and require explicit `yes`
         (see [preview-and-confirm.md](references/preview-and-confirm.md)). The textual
         diff against the last-applied envelope snapshot feeds the brownfield change-set.
Step 5 → Apply via az rest --body @envelope.json (createItem or updateDefinition)
Step 6 → Poll LRO; on success, commit the envelope snapshot + ID map
```

---

## Examples

End-to-end worked examples (create empty ontology → add entity type + non-timeseries binding → add relationship type + contextualization → add timeseries property + Eventhouse binding) live in [examples.md](references/examples.md). Complete fetch-mutate-send bash and PowerShell scripts live in [definition-script-templates.md](references/definition-script-templates.md).


---

## Agent Integration Notes

- This skill is authoring-focused. Pair with a consumption skill (e.g., a Fabric Graph query skill) to validate the ontology end-to-end.
- **Parallelize schema discovery** when the ontology binds to multiple source types:
  - Launch a background `sqldw-consumption-cli` task for lakehouse schemas (`INFORMATION_SCHEMA.COLUMNS`) — returns all tables + columns in one query.
  - Launch a background `eventhouse-consumption-cli` task for Eventhouse schemas (`.show database schema as json`) — returns all tables + columns in one call.
  - Both run concurrently. Merge results when both complete, then build the ontology model.
- **Merge step is critical** — after discovery, deduplicate property names across `properties[]` and `timeseriesProperties[]`, unify `valueType` for same-named properties across entity types, and prefix collisions before building the envelope.
- When orchestrating multi-step customer workstreams that span Ontology + Eventhouse + Lakehouse, route via an agent (e.g., `FabricDataEngineer`) rather than chaining skills directly.
- Reasonable upstream dependencies to assume: lakehouse tables already exist and have the key columns the user described. If not, the caller should invoke a lakehouse authoring skill first.
