# Ontology Authoring — Mechanics Reference

Deep reference for each authoring operation. SKILL.md keeps the high-level decision content (workflows, Must/Prefer/Avoid, troubleshooting). This file holds the full JSON shapes, field-by-field contracts, and verification recipes.

For base64 encode/decode across GNU vs BSD, and for the full fetch-mutate-send scripts, see [definition-script-templates.md](definition-script-templates.md).

---

## Definition Envelope for Ontology

The envelope is the same as any other Fabric item definition — a `definition` object with a `parts[]` array. Each part has `path`, `payload` (base64-encoded file contents), and `payloadType` (use `InlineBase64`).

> **Part paths must always use forward slashes** (`EntityTypes/{id}/definition.json`), never backslashes. On Windows, avoid `Join-Path` or `\` operators for building part paths — use string interpolation with `/` instead. Backslashes cause `ALMOperationBadRequest`.

```json
{
  "displayName": "zava_airlines_ontology",
  "type": "Ontology",
  "definition": {
    "parts": [
      { "path": ".platform",       "payload": "<base64>", "payloadType": "InlineBase64" },
      { "path": "definition.json", "payload": "<base64>", "payloadType": "InlineBase64" }
    ]
  }
}
```

Shared base64 helpers (portable — the `-w 0` flag is GNU-only, and `-d` is not on macOS's BSD `base64`):

```bash
# Encode — Linux / GNU coreutils
b64()   { printf '%s' "$1" | base64 -w 0; }
# Encode — macOS (BSD base64 has no -w; strip trailing newlines manually)
# b64() { printf '%s' "$1" | base64 | tr -d '\n'; }

# Decode — Linux / GNU
b64d()  { printf '%s' "$1" | base64 -d; }
# Decode — macOS (BSD base64 uses -D, not -d)
# b64d() { printf '%s' "$1" | base64 -D; }
```

> If you need one snippet that works on both: `base64 | tr -d '\n'` for encode and `base64 -d` (GNU) / `base64 -D` (BSD) for decode.

See [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) for the generic pattern.

---

## ID Generation Pattern

Entity type, relationship type, and property IDs must be **positive 64-bit integers that are unique across the ontology instance**. Data binding and contextualization IDs are GUIDs.

**Guide the LLM to generate:**

- Entity/relationship/property IDs: random positive 15–18 digit integers (safely inside 2^62). **Persist the `name → id` map in source control** so subsequent updates reuse the same IDs.
- Data binding / contextualization IDs: UUID v4 (`uuidgen` / `[guid]::NewGuid()`).
- Avoid reusing an ID for a different concept — IDs are referenced by `displayNamePropertyId`, `entityIdParts`, `propertyBindings[].targetPropertyId`, and `source/target.entityTypeId`.

Preferred generators:

```bash
# Bash — 64-bit positive integer ID (requires $RANDOM or /dev/urandom)
ID=$(od -An -tu8 -N8 /dev/urandom | tr -d ' ' | head -c 18)
# Bash — GUID
GUID=$(uuidgen)
```

```powershell
# PowerShell — 64-bit positive integer ID
$ID = [string]([System.Math]::Abs([System.BitConverter]::ToInt64([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(8), 0)))
# PowerShell — GUID
$GUID = [guid]::NewGuid().ToString()
```

Avoid shell `RANDOM` — it is 15-bit on most shells and collides quickly across a handful of IDs.

---

## Create the Ontology Item

An empty ontology is created with just `.platform` and an empty `definition.json`. Entity/relationship types are added via subsequent `updateDefinition` calls (preferred) or included in the initial `createItem` payload.

**Guide the LLM to generate:**

1. A `.platform` JSON with `{ "metadata": { "type": "Ontology", "displayName": "<name>" } }`.
2. An empty `definition.json` of `{}`. The base64 encoding of `{}` is exactly `e30=` — do not add whitespace, newlines, or BOM.
3. Base64-encode each, build the envelope, `POST` to `https://api.fabric.microsoft.com/v1/workspaces/{WS_ID}/items`.
4. Poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` (from the `x-ms-operation-id` header) until `Succeeded`; capture the new ontology item ID.

> **`createItem` returns 202 with no response body** — `az rest` exits with code 0 and prints nothing. This is expected. After the LRO completes, list Ontology items in the workspace to capture the new item's ID:
>
> ```bash
> ONTO_ID=$(az rest --method GET \
>   --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items?type=Ontology" \
>   --resource "https://api.fabric.microsoft.com" \
>   --query "value[?displayName=='${ONTO_NAME}'] | [0].id" --output tsv)
> ```
>
> To capture the LRO operation id from `az rest`, use `--verbose` and parse the `x-ms-operation-id` header from stderr, then poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` — see [SKILL.md § LRO Header Capture](../SKILL.md#lro-header-capture-with-az-rest). Do not poll the raw `Location` header (it redirects to an `analysis.windows.net` host and fails auth).

Minimal envelope shape:

```json
{
  "displayName": "zava_airlines_ontology",
  "type": "Ontology",
  "definition": {
    "parts": [
      { "path": ".platform",       "payload": "<base64 of platform json>", "payloadType": "InlineBase64" },
      { "path": "definition.json", "payload": "e30=",                      "payloadType": "InlineBase64" }
    ]
  }
}
```

---

## Add an Entity Type

An entity type file declares:

- `id` — the 64-bit ID you generated
- `name` — regex `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`; the Fabric portal UI further caps custom names to 1–26 alphanumeric/hyphen/underscore characters that start and end alphanumerically, so prefer that stricter shape for portability
- `namespace` — `usertypes`; `namespaceType` — `Custom`
- `visibility` — `Visible` (only value documented for authoring)
- `entityIdParts` — array of property IDs that form the key. Every referenced property must have `valueType` of `String` or `BigInt` (integer)
- `displayNamePropertyId` — property ID used as the instance label
- `properties[]` — non-timeseries properties (id, name, valueType)
- `timeseriesProperties[]` — timeseries properties (id, name, valueType; typically includes a `DateTime` timestamp property)

See [ONTOLOGY-AUTHORING-CORE.md § EntityType file](ONTOLOGY-AUTHORING-CORE.md#entitytype-file--entitytypesiddefinitionjson) for the complete schema and the source-column → `valueType` mapping table.

Example entity type file (placed at `EntityTypes/{entityTypeId}/definition.json`):

```json
{
  "id": "8813598896083",
  "namespace": "usertypes",
  "namespaceType": "Custom",
  "name": "Aircraft",
  "baseEntityTypeId": null,
  "visibility": "Visible",
  "entityIdParts": [ "3117068036374594013" ],
  "displayNamePropertyId": "3117068036374594013",
  "properties": [
    { "id": "3117068036374594013", "name": "TailNumber",       "redefines": null, "baseTypeNamespaceType": null, "valueType": "String" },
    { "id": "3117068031950000331", "name": "Manufacturer", "redefines": null, "baseTypeNamespaceType": null, "valueType": "String" }
  ],
  "timeseriesProperties": [
    { "id": "3114584981368796953", "name": "PreciseTimestamp", "redefines": null, "baseTypeNamespaceType": null, "valueType": "DateTime" },
    { "id": "3114584977562679672", "name": "AltitudeFt",      "redefines": null, "baseTypeNamespaceType": null, "valueType": "Double" }
  ]
}
```

**Guide the LLM to generate:**

- One property with `valueType: String` to act as both key and display name unless the user specifies otherwise.
- Distinct IDs for each property; never reuse an ID across properties or entity types.
- A `DateTime` `PreciseTimestamp` property in `timeseriesProperties` when the source is a timeseries table.
- When altering an existing entity type, read the current definition first, mutate the `properties[]`/`timeseriesProperties[]`, and resend — **do not** reuse the same property ID for a different field.

---

## Bind an Entity Type to a Lakehouse or Eventhouse Table

Data binding files sit at `EntityTypes/{entityTypeId}/DataBindings/{guid}.json`. Two binding types:

- `NonTimeSeries` (static attributes) — **lakehouse only**, **at most one per entity type**. Must be added before any time-series binding.
- `TimeSeries` (streaming / historical) — lakehouse **or eventhouse**. An entity type may have multiple time-series bindings, across both source kinds.

Binding constraint checklist (see [ONTOLOGY-AUTHORING-CORE.md § Binding rules](ONTOLOGY-AUTHORING-CORE.md#binding-rules) for the full list):

- Each entity type has **at most one** `NonTimeSeries` binding, sourced from OneLake (lakehouse only); this static binding is required before any `TimeSeries` binding on the same entity type.
- Lakehouse source tables must be **managed** (not external), must not have **OneLake security** enabled, and must not have delta **column mapping** enabled.
- Column mapping is auto-enabled when column names contain `,`, `;`, `{`, `}`, `(`, `)`, `\n`, `\t`, `=`, or space — rename those columns upstream before binding.
- Entity type keys (`entityIdParts`) must reference properties whose `valueType` is `String` or `BigInt`.

Non-timeseries binding (lakehouse):

```json
{
  "id": "66253a71-c26f-4c9d-877f-3af5632a4be2",
  "dataBindingConfiguration": {
    "dataBindingType": "NonTimeSeries",
    "propertyBindings": [
      { "sourceColumnName": "TailNumber",       "targetPropertyId": "3117068036374594013" },
      { "sourceColumnName": "Manufacturer", "targetPropertyId": "3117068031950000331" }
    ],
    "sourceTableProperties": {
      "sourceType": "LakehouseTable",
      "workspaceId": "<WS_ID>",
      "itemId": "<LH_ID>",
      "sourceTableName": "aircraft_static",
      "sourceSchema": "dbo"
    }
  }
}
```

Timeseries binding (lakehouse):

```json
{
  "id": "39a3889b-77e4-4851-8960-e3b779a5d9ba",
  "dataBindingConfiguration": {
    "dataBindingType": "TimeSeries",
    "timestampColumnName": "PreciseTimestamp",
    "propertyBindings": [
      { "sourceColumnName": "PreciseTimestamp", "targetPropertyId": "3114584981368796953" },
      { "sourceColumnName": "AltitudeFt",      "targetPropertyId": "3114584977562679672" },
      { "sourceColumnName": "TailNumber",           "targetPropertyId": "3117068036374594013" }
    ],
    "sourceTableProperties": {
      "sourceType": "LakehouseTable",
      "workspaceId": "<WS_ID>",
      "itemId": "<LH_ID>",
      "sourceTableName": "zava_aircraft_timeseries",
      "sourceSchema": "dbo"
    }
  }
}
```

Timeseries binding (eventhouse / Kusto):

```json
{
  "id": "d8b4e4f5-12aa-4db7-b5c3-0f8b1f2ad7c1",
  "dataBindingConfiguration": {
    "dataBindingType": "TimeSeries",
    "timestampColumnName": "PreciseTimestamp",
    "propertyBindings": [
      { "sourceColumnName": "PreciseTimestamp", "targetPropertyId": "3114584981368796953" },
      { "sourceColumnName": "AltitudeFt",      "targetPropertyId": "3114584977562679672" },
      { "sourceColumnName": "TailNumber",           "targetPropertyId": "3117068036374594013" }
    ],
    "sourceTableProperties": {
      "sourceType": "KustoTable",
      "workspaceId": "<WS_ID>",
      "itemId": "<EH_ID>",
      "clusterUri": "<eventhouse-cluster-uri>",
      "databaseName": "<kql-database-name>",
      "sourceTableName": "zava_aircraft_timeseries"
    }
  }
}
```

**Guide the LLM to generate:**

- One `propertyBindings` entry per property the user wants populated, keyed on the correct `targetPropertyId`.
- `workspaceId` / `itemId` filled from resolved variables — never hardcoded GUIDs.
- `sourceSchema` = `dbo` for lakehouse tables unless the user specifies a schema.
- A fresh GUID per binding — never reuse a GUID across bindings.
- Eventhouse bindings: ask for the `clusterUri` and `databaseName` from the target KQL database item before composing; never infer these.

---

## Add a Relationship Type

A relationship type connects two **existing and distinct** entity types. File path: `RelationshipTypes/{relTypeId}/definition.json`.

```json
{
  "id": "3110733855942077719",
  "namespace": "usertypes",
  "namespaceType": "Custom",
  "name": "operates",
  "source": { "entityTypeId": "<hub_entity_type_id>" },
  "target": { "entityTypeId": "<aircraft_entity_type_id>" }
}
```

**Guide the LLM to generate:**

- `name` that matches `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`.
- `source.entityTypeId` and `target.entityTypeId` that reference entity types already present in the ontology parts list — **and are distinct from each other**.
- A new relationship type ID, unique across the ontology.

---

## Bind a Relationship Contextualization

A contextualization tells the ontology how rows in a lakehouse table map to relationship instances. File path: `RelationshipTypes/{relTypeId}/Contextualizations/{guid}.json`.

```json
{
  "id": "62bbbf52-39a4-47ed-b7bf-651debaca6ab",
  "dataBindingTable": {
    "sourceType": "LakehouseTable",
    "workspaceId": "<WS_ID>",
    "itemId": "<LH_ID>",
    "sourceTableName": "zava_hub_aircraft_link",
    "sourceSchema": "dbo"
  },
  "sourceKeyRefBindings": [
    { "sourceColumnName": "HubId", "targetPropertyId": "<hub_key_property_id>" }
  ],
  "targetKeyRefBindings": [
    { "sourceColumnName": "TailNumber", "targetPropertyId": "<aircraft_key_property_id>" }
  ]
}
```

**Guide the LLM to generate:**

- `sourceKeyRefBindings` with each `targetPropertyId` referencing a property in the **source** entity type's `entityIdParts`.
- `targetKeyRefBindings` with each `targetPropertyId` referencing a property in the **target** entity type's `entityIdParts`.
- A link table that actually contains both key columns (the user should confirm). Common mistake: pointing at a table that only contains one side's key.

---

## Apply a Definition Update

`updateDefinition` replaces the included parts wholesale. The safe workflow is **fetch → mutate → send**.

> **`getDefinition` typically returns 202 (LRO)**, not 200 with inline data. You must:
> 1. Capture the `x-ms-operation-id` header from the 202 response
> 2. Poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` until `status: "Succeeded"`
> 3. `GET https://api.fabric.microsoft.com/v1/operations/{operationId}/result` to retrieve the actual definition envelope
>
> Poll the Fabric `operations` endpoint on `api.fabric.microsoft.com` rather than following the raw `Location` header — the latter redirects to an `analysis.windows.net` host that fails `az rest --resource https://api.fabric.microsoft.com` auth. This pattern applies to both `az rest` (capture via `--verbose`) and `curl` (capture via `-D` headers file). See [definition-script-templates.md](definition-script-templates.md) for complete scripts that handle both 200 and 202.

```bash
# 1. Fetch current definition. getDefinition is LRO-capable: it MAY return 200
#    with the envelope inline, OR 202 with a Location header (operation URL).
#    The explicit '{}' body avoids HTTP 411 Length Required on empty POSTs.
#    For the 202 path (poll Location → GET {Location}/result), use the complete
#    script in definition-script-templates.md.
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${ONTO_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body '{}' \
  -o json > /tmp/onto_current.json

# 2. Mutate locally (script: decode base64 parts, patch JSON, re-encode)

# 3. Send the updated envelope (also LRO — poll the Location header)
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${ONTO_ID}/updateDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body @/tmp/onto_new_envelope.json
```

Both `createItem` and `updateDefinition` return **long-running operations**. `getDefinition` is also LRO-capable — it may return the envelope directly (`200 OK`) **or** a `202 Accepted` carrying an `x-ms-operation-id` header; in the 202 case, poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` until `Succeeded` and then `GET …/operations/{operationId}/result` to retrieve the envelope. Poll the Fabric `operations` endpoint, not the raw `Location` header (which redirects to an `analysis.windows.net` host and fails auth). See [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern) and the fetch-mutate-send script in [definition-script-templates.md](definition-script-templates.md), which handles both cases.

**When renaming the ontology**, add the `updateMetadata=true` query string to `updateDefinition` and include an updated `.platform` part. See [ONTOLOGY-AUTHORING-CORE.md § Item-management contract](ONTOLOGY-AUTHORING-CORE.md#item-management-contract).

---

## Verify and Inspect

After any authoring operation, re-fetch the definition and decode the parts you changed.

```bash
# Use '{}' body (POST with empty body can return 411 Length Required). If this
# returns 202, fall back to the LRO-aware script in definition-script-templates.md.
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${ONTO_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body '{}' \
  | jq -r '.definition.parts[] | select(.path | test("EntityTypes/.+/definition.json$")) | .payload' \
  | while read p; do echo "---"; echo "$p" | base64 -d | jq .; done
```

Additional sanity checks the LLM should run:

- Every `targetPropertyId` in any binding exists in the parent entity type's `properties[]` or `timeseriesProperties[]`.
- Every `entityIdParts[]` and `displayNamePropertyId` points at an existing property in the same entity type.
- Every relationship `source.entityTypeId` / `target.entityTypeId` references an entity type present in the parts list and the two are distinct.
- Every binding's `workspaceId` / `itemId` resolves to an existing source item: a **lakehouse** for `LakehouseTable` sources (static + timeseries), or an **Eventhouse** for `KustoTable` sources (timeseries only). For `KustoTable`, also verify `clusterUri` matches the KQL database's `properties.queryServiceUri` and `databaseName` matches its `displayName`.
