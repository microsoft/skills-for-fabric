# Ontology Authoring — Examples

End-to-end worked examples composing the operations documented in [authoring-mechanics.md](authoring-mechanics.md).

> **Portability note for the bash snippets below:** GNU `base64 -w 0` and `base64 -d` are assumed. On macOS (BSD `base64`), use `base64 -D` to decode, and `base64 | tr -d '\n'` to encode without wrapping. See [definition-script-templates.md § Platform assumptions](definition-script-templates.md#platform-assumptions) for portable helpers. `/tmp` is Unix-only — on Windows use `$env:TEMP` (PowerShell) or an equivalent path.

---

## Schema Discovery Recipes

Before composing bindings, discover the source table schemas to avoid hallucinating column names. **Prefer companion skills** for speed — they return all schemas in a single call.

### Lakehouse table columns

```sql
-- FASTEST: Use the sqldw-consumption-cli skill to query the lakehouse SQL endpoint
-- This returns ALL tables and columns in one query:
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo'
ORDER BY TABLE_NAME, ORDINAL_POSITION
```

```bash
# Alternative: Fabric Tables API (table names only — no columns)
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/lakehouses/${LH_ID}/tables" \
  --resource "https://api.fabric.microsoft.com"

# Alternative: OneLake Table API (Iceberg metadata — full column schema, one table at a time)
# Use the Fabric MCP tool `fabric-onelake_get_table` with namespace="dbo" and table="<name>"
```

### Eventhouse / KQL table columns

```bash
TOKEN=$(az account get-access-token --resource "https://kusto.kusto.windows.net" --query accessToken -o tsv)

# FASTEST: get ALL table schemas in the database in one call
curl -s -X POST "${CLUSTER_URI}/v1/rest/query" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"db":"'"$DB_NAME"'","csl":".show database schema as json"}'

# Alternative: single table schema
# -d '{"db":"'"$DB_NAME"'","csl":".show table EquipmentTelemetry schema as json"}'

# Map CslType → ontology valueType:
#   string → String | datetime → DateTime | real/double → Double | long → BigInt | bool → Boolean
```

---

## Example 1: Create an empty ontology, then add a single entity type

```bash
# Prereqs: WS_ID, LH_ID resolved (see SKILL.md § Connection)
ONTO_NAME="zava_airlines_ontology"

# --- 1. Create empty ontology ---
PLATFORM_JSON='{"metadata":{"type":"Ontology","displayName":"'"$ONTO_NAME"'"}}'
PLATFORM_B64=$(printf '%s' "$PLATFORM_JSON" | base64 -w 0)
DEF_B64=$(printf '%s' '{}' | base64 -w 0)

cat > /tmp/create_onto.json <<EOF
{
  "displayName": "${ONTO_NAME}",
  "type": "Ontology",
  "definition": {
    "parts": [
      { "path": ".platform",       "payload": "${PLATFORM_B64}", "payloadType": "InlineBase64" },
      { "path": "definition.json", "payload": "${DEF_B64}",      "payloadType": "InlineBase64" }
    ]
  }
}
EOF
# To create inside a workspace folder, resolve FOLDER_ID per SKILL.md § Connection → Folder
# and add a top-level "folderId": "${FOLDER_ID}" field above (must be a GUID).

az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body @/tmp/create_onto.json
```

> Poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` (capture `x-ms-operation-id` via `--verbose`) until `Succeeded`, then resolve `ONTO_ID` by listing `Ontology` items in the workspace. Do not poll the raw `Location` header (analysis.windows.net redirect). See [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern).

---

## Example 2: Add a `Aircraft` entity type + non-timeseries binding via `updateDefinition`

```bash
# IDs (persist these in your repo; do not regenerate on every run)
AIRCRAFT_ET_ID=8813598896083
AIRCRAFT_KEY_PROP_ID=3117068036374594013
AIRCRAFT_MFR_PROP_ID=3117068031950000331
BINDING_GUID=$(uuidgen)

# --- Build the new parts ---
ET_JSON=$(jq -nc \
  --arg id "$AIRCRAFT_ET_ID" \
  --arg keyId "$AIRCRAFT_KEY_PROP_ID" \
  --arg mfrId "$AIRCRAFT_MFR_PROP_ID" \
  '{id:$id,namespace:"usertypes",namespaceType:"Custom",name:"Aircraft",baseEntityTypeId:null,
    visibility:"Visible",entityIdParts:[$keyId],displayNamePropertyId:$keyId,
    properties:[
      {id:$keyId,name:"TailNumber",redefines:null,baseTypeNamespaceType:null,valueType:"String"},
      {id:$mfrId,name:"Manufacturer",redefines:null,baseTypeNamespaceType:null,valueType:"String"}
    ],
    timeseriesProperties:[]}')

BIND_JSON=$(jq -nc \
  --arg id "$BINDING_GUID" \
  --arg ws "$WS_ID" \
  --arg lh "$LH_ID" \
  --arg keyId "$AIRCRAFT_KEY_PROP_ID" \
  --arg mfrId "$AIRCRAFT_MFR_PROP_ID" \
  '{id:$id,dataBindingConfiguration:{
      dataBindingType:"NonTimeSeries",
      propertyBindings:[
        {sourceColumnName:"TailNumber",targetPropertyId:$keyId},
        {sourceColumnName:"Manufacturer",targetPropertyId:$mfrId}
      ],
      sourceTableProperties:{sourceType:"LakehouseTable",workspaceId:$ws,itemId:$lh,
                             sourceTableName:"aircraft_static",sourceSchema:"dbo"}}}')

ET_B64=$(printf '%s' "$ET_JSON"   | base64 -w 0)
BD_B64=$(printf '%s' "$BIND_JSON" | base64 -w 0)

# Re-fetch current parts, splice in the new ones, then send:
# (pseudo — see definition-script-templates.md for the full splice script)
```

> See [definition-script-templates.md](definition-script-templates.md) for a complete fetch-mutate-send bash template.

---

## Example 3: Add a relationship type `operates` from `Hub` to `Aircraft`

```bash
HUB_ET_ID=159990879905613
HUB_KEY_PROP_ID=3117068036083000111      # persist alongside other ID maps
OPERATES_REL_ID=3110733855942077719
CTX_GUID=$(uuidgen)

REL_JSON=$(jq -nc --arg id "$OPERATES_REL_ID" --arg src "$HUB_ET_ID" --arg tgt "$AIRCRAFT_ET_ID" \
  '{namespace:"usertypes",id:$id,name:"operates",namespaceType:"Custom",
    source:{entityTypeId:$src},target:{entityTypeId:$tgt}}')

CTX_JSON=$(jq -nc \
  --arg id "$CTX_GUID" --arg ws "$WS_ID" --arg lh "$LH_ID" \
  --arg hubKey "$HUB_KEY_PROP_ID" --arg aircraftKey "$AIRCRAFT_KEY_PROP_ID" \
  '{id:$id,
    dataBindingTable:{sourceType:"LakehouseTable",workspaceId:$ws,itemId:$lh,
                      sourceTableName:"zava_hub_aircraft_link",sourceSchema:"dbo"},
    sourceKeyRefBindings:[{sourceColumnName:"HubId",targetPropertyId:$hubKey}],
    targetKeyRefBindings:[{sourceColumnName:"TailNumber",targetPropertyId:$aircraftKey}]}')
```

> Splice into the envelope alongside the existing entity type parts, then call `updateDefinition`.

---

## Example 4: Add a `AltitudeFt` timeseries property + Eventhouse binding on `Aircraft`

> Assumes Example 2 has already been applied (so `Aircraft` has a `NonTimeSeries` binding — required before any timeseries binding). `EH_ID`, `CLUSTER_URI`, `DB_NAME` are resolved per the SKILL.md § Connection → Eventhouse recipe.

```bash
# Prereqs: WS_ID, ONTO_ID, AIRCRAFT_ET_ID, AIRCRAFT_KEY_PROP_ID from Example 2;
#          EH_ID, CLUSTER_URI, DB_NAME from SKILL.md § Connection → Eventhouse.
AIRCRAFT_TS_TIMESTAMP_ID=3117068031950000443     # DateTime timeseries property id (persist in repo)
AIRCRAFT_TS_ALT_ID=3117068031950000444          # Double   timeseries property id
TS_BIND_GUID=$(uuidgen)

# --- Add the timestamp + value timeseries properties to the Aircraft entity type ---
# (Fetch the current EntityTypes/${AIRCRAFT_ET_ID}/definition.json, append the two
#  entries to timeseriesProperties[], base64-encode, splice back in. Pseudo
#  below; see definition-script-templates.md for the full splice.)
TS_PROPS_JSON=$(jq -nc \
  --arg tsId "$AIRCRAFT_TS_TIMESTAMP_ID" \
  --arg altId "$AIRCRAFT_TS_ALT_ID" \
  '[
     {id:$tsId,  name:"EventTimestamp", redefines:null, baseTypeNamespaceType:null, valueType:"DateTime"},
     {id:$altId, name:"AltitudeFt",    redefines:null, baseTypeNamespaceType:null, valueType:"Double"}
   ]')

# --- Build the KustoTable timeseries binding ---
# timestampColumnName plus a matching propertyBindings entry for that column
# are both required (CORE: timeseriesProperties must include a timestamp
# property bound via timestampColumnName).
TS_BIND_JSON=$(jq -nc \
  --arg id "$TS_BIND_GUID" \
  --arg ws "$WS_ID" \
  --arg eh "$EH_ID" \
  --arg cu "$CLUSTER_URI" \
  --arg db "$DB_NAME" \
  --arg tsId "$AIRCRAFT_TS_TIMESTAMP_ID" \
  --arg altId "$AIRCRAFT_TS_ALT_ID" \
  '{id:$id,dataBindingConfiguration:{
      dataBindingType:"TimeSeries",
      timestampColumnName:"EventEnqueuedUtcTime",
      propertyBindings:[
        {sourceColumnName:"EventEnqueuedUtcTime", targetPropertyId:$tsId},
        {sourceColumnName:"AltitudeFt",          targetPropertyId:$altId}
      ],
      sourceTableProperties:{sourceType:"KustoTable",workspaceId:$ws,itemId:$eh,
                             clusterUri:$cu,databaseName:$db,
                             sourceTableName:"AircraftTelemetry"}}}')

TS_BIND_B64=$(printf '%s' "$TS_BIND_JSON" | base64 -w 0)
# On macOS: TS_BIND_B64=$(printf '%s' "$TS_BIND_JSON" | base64 | tr -d '\n')

# Splice: append a new part at
#   EntityTypes/${AIRCRAFT_ET_ID}/DataBindings/${TS_BIND_GUID}.json
# alongside the existing NonTimeSeries binding part, then call updateDefinition (LRO).
```

> **Eventhouse binding invariants** the template must enforce before sending:
>
> - Entity type already has a `NonTimeSeries` binding (Eventhouse is timeseries-only). Example 2 above satisfies this for `Aircraft`.
> - `timeseriesProperties[]` includes a `DateTime` property corresponding to `timestampColumnName`, and `propertyBindings[]` maps that column to that property.
> - `KustoTable.itemId` is the **Eventhouse item ID** (from `/kqlDatabases/{id}/properties.parentEventhouseItemId` or `/eventhouses`), not the KQL database ID.
> - `clusterUri` matches the KQL database's `properties.queryServiceUri`; `databaseName` matches its `displayName`.
