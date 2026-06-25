# ONTOLOGY-AUTHORING-CORE.md — Fabric IQ Ontology (preview) Authoring Reference

> **Purpose**: Shared reference for authoring Fabric IQ Ontology (preview) items via the Fabric item-definition REST API. Covers the definition tree (entity types, data bindings, relationship types, contextualizations), schema constraints, value-type mappings, supported source kinds, and platform limitations.
> **Not a tutorial** — assumes familiarity with the Fabric control-plane REST API and base64-encoded item definitions. Focus is the JSON shapes and rules the skill must generate correctly.
> **Preview**: The Ontology item type is in public preview. Wire format and limitations may change; validate against the latest Microsoft docs before production use.

---

## Capability Matrix

| Capability | Lakehouse (OneLake) | Eventhouse (Kusto) |
|---|---|---|
| Entity type creation | ✅ | ✅ |
| Entity type **static** binding | ✅ | ❌ (OneLake only) |
| Entity type **time-series** binding | ✅ | ✅ |
| Multiple static bindings per entity type | ❌ (at most one) | n/a |
| Multiple time-series bindings per entity type | ✅ | ✅ |
| Relationship type creation | ✅ | ✅ |
| Relationship contextualization | ✅ (Lakehouse linking table) | ❌ |
| Ontology-scoped uniqueness for entity / property / relationship IDs | ✅ required | ✅ required |
| Refresh on upstream data changes | Manual refresh required | Manual refresh required |

---

## Definition Tree

All authoring flows produce or mutate a tree of JSON files carried as `parts[]` inside the Fabric item-definition envelope (`payloadType = "InlineBase64"`).

| Definition part path | Required | Shape |
|---|---|---|
| `.platform` | ✅ | `{"metadata":{"type":"Ontology","displayName":"<name>"}}` |
| `definition.json` | ✅ | `{}` (empty object) |
| `EntityTypes/{entityTypeId}/definition.json` | per entity type | EntityType file |
| `EntityTypes/{entityTypeId}/DataBindings/{guid}.json` | per binding | DataBinding file |
| `EntityTypes/{entityTypeId}/Documents/{name}.json` | optional | Document link |
| `EntityTypes/{entityTypeId}/Overviews/definition.json` | optional | Widgets layout |
| `EntityTypes/{entityTypeId}/ResourceLinks/definition.json` | optional | Power BI / item links |
| `RelationshipTypes/{relTypeId}/definition.json` | per relationship type | RelationshipType file |
| `RelationshipTypes/{relTypeId}/Contextualizations/{guid}.json` | per contextualization | Contextualization file |

`{entityTypeId}` and `{relTypeId}` are positive 64-bit integers (**BigInt**) that are **unique across the ontology**. Binding and contextualization IDs are GUIDs.

---

## EntityType file — `EntityTypes/{id}/definition.json`

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | BigInt | ✅ | Positive 64-bit integer, unique across the ontology |
| `namespace` | string | ✅ | Allowed value: `usertypes` |
| `baseEntityTypeId` | BigInt | ❌ | ID of base entity type (inheritance is limited; treat as null) |
| `name` | string | ✅ | Regex `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`. Portal UI additionally limits entity type names to 1–26 alphanumeric/hyphen/underscore and requires starting and ending with an alphanumeric character. |
| `entityIdParts` | BigInt[] | ❌ | Property IDs forming the entity key. Must all be `valueType` `String` or `BigInt` (integer) |
| `displayNamePropertyId` | BigInt | ❌ | Property ID used as the instance display name |
| `namespaceType` | string | ✅ | Allowed value: `Custom` |
| `visibility` | string | ❌ | Allowed value: `Visible` |
| `properties` | EntityTypeProperty[] | ❌ | Static / non-timeseries properties |
| `timeseriesProperties` | EntityTypeProperty[] | ❌ | Time-series properties (must include a timestamp property bound via `timestampColumnName`) |
| `untypedProperties` | UntypedEntityTypeProperty[] | ❌ | Properties whose `valueType` is `Any`. Use only when the source column type cannot be mapped to a concrete `valueType`; downstream consumers must treat the value as opaque |

### EntityTypeProperty

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | BigInt | ✅ | Positive 64-bit integer, unique across the ontology |
| `name` | string | ✅ | Regex `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$`. Portal custom property names additionally limited to 1–26 alphanumeric/hyphen/underscore. Property names are **unique across the ontology** — two entity types cannot share a property name unless both use the same `valueType` |
| `redefines` | string | ❌ | Pointer to inherited property being redefined |
| `baseTypeNamespaceType` | string | ❌ | Namespace of the base entity type |
| `valueType` | string | ✅ | **Allowed values (exact): `String`, `Boolean`, `DateTime`, `Object`, `BigInt`, `Double`** |

### UntypedEntityTypeProperty

Same shape as `EntityTypeProperty` except `valueType` is the literal string `Any`. Untyped properties cannot back keys (must not appear in `entityIdParts`) and are not safely queryable as scalars.

### Value-type mapping from source

Use this table when picking `valueType` based on the source column type:

| Ontology `valueType` | Lakehouse column types | Eventhouse column types |
|---|---|---|
| `BigInt` (integer) | `tinyint`, `smallint`, `bigint`, `integer`, `long`, `short` | `int`, `long` |
| `Boolean` | `boolean` | `bool` |
| `DateTime` | `datetime`, `date`, `timestamp` | `datetime` |
| `Double` | `double`, `decimal`, `float` | `decimal`, `real` |
| `String` | `char`, `decimal(p,s)`, `string`, `array`, `binary`, `binary16`, `byte`, `map`, `object`, `struct`, `timestampint64`, `timestamp_ntz` | `dynamic`, `string`, `guid`, `timespan` |

Timestamp for a time-series binding must map to `DateTime` (source of type `datetime`, `date`, or `timestamp`).

Entity type key (`entityIdParts`) may only reference properties whose `valueType` is `String` or `BigInt`.

---

## DataBinding file — `EntityTypes/{id}/DataBindings/{guid}.json`

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | Guid | ✅ | Unique per binding |
| `dataBindingConfiguration` | DataBindingConfiguration | ✅ | See below |

### DataBindingConfiguration

| Property | Type | Required | Notes |
|---|---|---|---|
| `dataBindingType` | string | ✅ | `NonTimeSeries` or `TimeSeries` |
| `timestampColumnName` | string | only for `TimeSeries` | Source column name carrying the timestamp |
| `propertyBindings` | EntityTypePropertyBinding[] | ❌ | Source-column → property-ID mappings |
| `sourceTableProperties` | Lakehouse…Properties **or** Eventhouse…Properties | ✅ | **Eventhouse sources are allowed only when `dataBindingType` is `TimeSeries`** |

### EntityTypePropertyBinding

| Property | Type | Required | Notes |
|---|---|---|---|
| `sourceColumnName` | string | ✅ | Column in the source table |
| `targetPropertyId` | string | ✅ | Property ID inside the entity type (matches a property from `properties[]` or `timeseriesProperties[]`) |

### LakehouseTableDataBindingProperties

| Property | Type | Required | Notes |
|---|---|---|---|
| `sourceType` | string | ✅ | `LakehouseTable` |
| `workspaceId` | Guid | ✅ | Workspace containing the lakehouse |
| `itemId` | Guid | ✅ | Lakehouse `ArtifactId` |
| `sourceTableName` | string | ✅ | Table name |
| `sourceSchema` | string | ❌ | Typically `dbo` |

### EventhouseTableDataBindingProperties

| Property | Type | Required | Notes |
|---|---|---|---|
| `sourceType` | string | ✅ | `KustoTable` |
| `workspaceId` | Guid | ✅ | Workspace containing the eventhouse |
| `itemId` | Guid | ✅ | Eventhouse `ArtifactId` |
| `clusterUri` | string | ✅ | Kusto cluster URL |
| `databaseName` | string | ✅ | Database name |
| `sourceTableName` | string | ✅ | Source table in the cluster |

### Binding rules

- **Each entity type has at most one `NonTimeSeries` (static) binding** sourced from a lakehouse table.
- **Entity types support multiple `TimeSeries` bindings** across lakehouse and eventhouse sources.
- **Static bindings must exist before time-series bindings** — the time-series binding needs a key property populated by static data.
- Lakehouse data sources must be **managed tables** (same OneLake directory as the lakehouse) — **external tables are not supported**.
- Lakehouses with **OneLake security enabled** cannot be used as data sources.
- Delta tables with **column mapping enabled** are not supported. Column mapping is enabled automatically on tables with column names that contain `,`, `;`, `{`, `}`, `(`, `)`, `\n`, `\t`, `=`, or space, and on delta tables used for import-mode semantic models.
- Renaming a lakehouse source table after bindings are created can break the preview experience.

### DataBinding examples

Non-timeseries (static) — lakehouse source:

```json
{
  "id": "66253a71-c26f-4c9d-877f-3af5632a4be2",
  "dataBindingConfiguration": {
    "dataBindingType": "NonTimeSeries",
    "propertyBindings": [
      { "sourceColumnName": "DisplayName",  "targetPropertyId": "3117068036374594013" },
      { "sourceColumnName": "Manufacturer", "targetPropertyId": "3117068031950000331" }
    ],
    "sourceTableProperties": {
      "sourceType": "LakehouseTable",
      "workspaceId": "580f410e-733d-43bd-8a87-be12b536f7ff",
      "itemId": "d0d863bc-48e1-45b2-8f4b-54795c97ba71",
      "sourceTableName": "equipment1nontimeseries",
      "sourceSchema": "dbo"
    }
  }
}
```

Time-series — lakehouse source (note: static binding must already exist on this entity type):

```json
{
  "id": "39a3889b-77e4-4851-8960-e3b779a5d9ba",
  "dataBindingConfiguration": {
    "dataBindingType": "TimeSeries",
    "timestampColumnName": "PreciseTimestamp",
    "propertyBindings": [
      { "sourceColumnName": "PreciseTimestamp", "targetPropertyId": "3114584981368796953" },
      { "sourceColumnName": "Name",             "targetPropertyId": "3114584979743320934" },
      { "sourceColumnName": "AltitudeFt",      "targetPropertyId": "3114584977562679672" },
      { "sourceColumnName": "Name",             "targetPropertyId": "3117068036374594013" }
    ],
    "sourceTableProperties": {
      "sourceType": "LakehouseTable",
      "workspaceId": "580f410e-733d-43bd-8a87-be12b536f7ff",
      "itemId": "d0d863bc-48e1-45b2-8f4b-54795c97ba71",
      "sourceTableName": "equipment1timeseries",
      "sourceSchema": "dbo"
    }
  }
}
```

Time-series — eventhouse source:

```json
{
  "id": "d8b4e4f5-12aa-4db7-b5c3-0f8b1f2ad7c1",
  "dataBindingConfiguration": {
    "dataBindingType": "TimeSeries",
    "timestampColumnName": "PreciseTimestamp",
    "propertyBindings": [
      { "sourceColumnName": "PreciseTimestamp", "targetPropertyId": "3114584981368796953" },
      { "sourceColumnName": "AltitudeFt",      "targetPropertyId": "3114584977562679672" }
    ],
    "sourceTableProperties": {
      "sourceType": "KustoTable",
      "workspaceId": "580f410e-733d-43bd-8a87-be12b536f7ff",
      "itemId": "a1f22aaa-b5c2-4d12-a3d4-8821c50a90cd",
      "clusterUri": "https://trd-xxxx.z0.kusto.fabric.microsoft.com",
      "databaseName": "Zava_Telemetry",
      "sourceTableName": "equipment_timeseries"
    }
  }
}
```

---

## RelationshipType file — `RelationshipTypes/{id}/definition.json`

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | BigInt | ✅ | Positive 64-bit integer, unique across the ontology |
| `namespace` | string | ✅ | `usertypes` |
| `name` | string | ✅ | Regex `^[a-zA-Z][a-zA-Z0-9_-]{0,127}$` |
| `namespaceType` | string | ✅ | `Custom` |
| `source` | RelationshipEnd | ✅ | `{ "entityTypeId": "<id>" }` |
| `target` | RelationshipEnd | ✅ | `{ "entityTypeId": "<id>" }` |

Rules:

- `source.entityTypeId` and `target.entityTypeId` must reference entity types that **already exist in the ontology parts list** and must be **distinct from each other**.
- The source data for the relationship must be a **OneLake lakehouse table** that contains keys for both the source and target entity types.

Example:

```json
{
  "namespace": "usertypes",
  "id": "3110733855942077719",
  "name": "contains",
  "namespaceType": "Custom",
  "source": { "entityTypeId": "8813598896083" },
  "target": { "entityTypeId": "159990879905613" }
}
```

---

## Contextualization file — `RelationshipTypes/{id}/Contextualizations/{guid}.json`

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | Guid | ✅ | Unique per contextualization |
| `dataBindingTable` | LakehouseTableDataBindingProperties | ✅ | The link table (lakehouse only) |
| `sourceKeyRefBindings` | EntityTypePropertyBinding[] | ✅ | Columns in the link table that form the source entity's key |
| `targetKeyRefBindings` | EntityTypePropertyBinding[] | ✅ | Columns in the link table that form the target entity's key |

Rules:

- Each `targetPropertyId` in `sourceKeyRefBindings` must be in the **source** entity type's `entityIdParts`. Same for `targetKeyRefBindings` and the target entity type.
- The link table must physically contain both sets of key columns — confirm with the data owner before generating.

Example:

```json
{
  "id": "62bbbf52-39a4-47ed-b7bf-651debaca6ab",
  "dataBindingTable": {
    "sourceType": "LakehouseTable",
    "workspaceId": "580f410e-733d-43bd-8a87-be12b536f7ff",
    "itemId": "d0d863bc-48e1-45b2-8f4b-54795c97ba71",
    "sourceTableName": "relationshiptable",
    "sourceSchema": "dbo"
  },
  "sourceKeyRefBindings": [
    { "sourceColumnName": "Equipment1Name", "targetPropertyId": "3117068036374594013" }
  ],
  "targetKeyRefBindings": [
    { "sourceColumnName": "Equipment2Name", "targetPropertyId": "3113493256674129151" }
  ]
}
```

---

## Optional parts

### Document — `EntityTypes/{id}/Documents/document{n}.json`

```json
{ "displayText": "Install guide", "url": "https://example.com/guide" }
```

`displayText` is optional; `url` is required.

### Overviews — `EntityTypes/{id}/Overviews/definition.json`

Widgets: `lineChart`, `barChart`, `file`, `graph`, `liveMap`. Settings `type`: `fixedTime` or `customTime`. `interval`: `OneMinute`, `FiveMinutes`, `FifteenMinutes`, `ThirtyMinutes`, `OneHour`, `SixHours`, `TwelveHours`, `OneDay`. `aggregation`: `Average`, `Count`, `Maximum`, `Minimum`, `Sum`, `LastKnownValue`. `fixedTimeRange`: `Last30Minutes`, `Last1Hour`, `Last4Hours`, `Last12Hours`, `Last24Hours`, `Last48Hours`, `Last3Days`, `Last7Days`, `Last30Days`.

### ResourceLinks — `EntityTypes/{id}/ResourceLinks/definition.json`

```json
{ "resourceLinks": [ { "type": "PowerBIReport", "workspaceId": "<ws>", "itemId": "<item>" } ] }
```

`type` allowed value: `PowerBIReport`.

---

## Item-management contract

| Operation | HTTP | URL | Notes |
|---|---|---|---|
| Create ontology item | `POST` | `/v1/workspaces/{ws}/items` | Body: `{"displayName","type":"Ontology","definition":{"parts":[...]}}`. Long-running; returns `202` with an `x-ms-operation-id` header — poll `/v1/operations/{operationId}` on `api.fabric.microsoft.com` (not the `Location` redirect host). Creation can also be done with only `.platform` + empty `definition.json`, then populate via `updateDefinition`. |
| Get ontology definition | `POST` | `/v1/workspaces/{ws}/items/{id}/getDefinition` | Long-running. `200` returns the envelope directly. `202` carries `x-ms-operation-id`; poll `/v1/operations/{operationId}` until `Succeeded`, then `GET /v1/operations/{operationId}/result` to retrieve the envelope. |
| Update ontology definition | `POST` | `/v1/workspaces/{ws}/items/{id}/updateDefinition` | Long-running. Replaces all included parts — always fetch, mutate locally, then send the full desired tree. To rename or change `.platform`, add `?updateMetadata=true`. |
| List items of type `Ontology` | `GET` | `/v1/workspaces/{ws}/items?type=Ontology` | Used to resolve the ontology `itemId` by name. |

All calls target `https://api.fabric.microsoft.com` and require the `https://api.fabric.microsoft.com` token audience.

---

## Platform limitations (preview)

- Names (entity type, relationship type, property) are **globally scoped inside the ontology**. A relationship type name must be unique within the ontology item; property names must be unique across entity types unless both share the same `valueType`.
- **Column mapping** on delta tables breaks bindings (see binding rules).
- **OneLake security** on a lakehouse breaks bindings.
- **External tables** are not supported as binding sources.
- **Upstream data changes require a manual graph-model refresh** before instance counts change in the preview experience.
- `Object` / nested JSON properties are not fully queryable like scalar properties — treat as opaque payload unless the consumer explicitly targets Fabric Graph/GraphQL.
- The Ontology item is in public preview; features and the above schema may change.

---

## ID generation guidance

- Entity type / property / relationship type IDs must be **positive 64-bit integers unique across the ontology**. Generate 15–18 digit random positive integers and persist the `name → id` map in source control so re-runs reuse the same IDs.
- Data binding and contextualization IDs are GUIDs; persist them too so `updateDefinition` doesn't orphan bindings.
- Never reuse an ID for a different concept. Never change the ID of an existing concept — add a new one and delete the old one if needed.

---

## Authoritative upstream references

- Ontology overview and core concepts — Fabric IQ Ontology (preview) docs on Microsoft Learn.
- Entity types, data binding, and relationship types how-to — Fabric IQ Ontology (preview) how-to articles.
- Item definition JSON schema — *Ontology definition* article under Fabric REST API item management.
- Create / Update / Get Item Definition — Fabric REST API core item management endpoints.
