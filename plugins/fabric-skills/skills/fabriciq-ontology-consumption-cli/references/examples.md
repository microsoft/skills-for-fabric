# Ontology Consumption — End-to-End Examples

Worked examples that exercise the **ground → route → query** pipeline end-to-end. Each example assumes `az login` has been done and that the user knows the workspace display name.

For the full fetch-and-decode scripts referenced here, see [grounding-extraction.md](grounding-extraction.md). For the per-binding-type invocation templates, see [routing.md](routing.md).

---

## Example 1 — Enumerate an ontology (read-only grounding pass)

> Produces a grounding JSON summary for the LLM to disambiguate later queries. No data is read from any source table.

```bash
# 0. Discover IDs
WS_NAME="My-Archimed-Workspace"
ONT_NAME="ZavaAirlinesOntology"

WS_ID=$(az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --resource "https://api.fabric.microsoft.com" \
  | jq -r --arg n "$WS_NAME" '.value[] | select(.displayName==$n) | .id')

ONT_ID=$(az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items?type=Ontology" \
  --resource "https://api.fabric.microsoft.com" \
  | jq -r --arg n "$ONT_NAME" '.value[] | select(.displayName==$n) | .id')

# 1. Fetch + decode (run the inline Bash script from grounding-extraction.md § "Bash — portable")
# → ./_ont/ now mirrors the ontology definition tree

# 2. Produce grounding JSON (run the inline Python snippet from grounding-extraction.md § "Tree Reconstruction")
# → write the JSON to ./_ont/grounding.json before continuing

# 3. Inspect
jq '{
  onto: .displayName,
  entityTypes: [.entityTypes[] | {name, keys: .keyPropertyIds, bindings: [.bindings[] | {kind: .source.kind, table: .source.sourceTableName}]}],
  relationships: [.relationshipTypes[] | {name, source: .source.entityTypeId, target: .target.entityTypeId}]
}' ./_ont/grounding.json
```

Expected shape of step 3:

```json
{
  "onto": "ZavaAirlinesOntology",
  "entityTypes": [
    { "name": "Airline", "keys": ["..."], "bindings": [ { "kind": "LakehouseTable", "table": "Airlines" } ] },
    { "name": "Aircraft",    "keys": ["..."], "bindings": [ { "kind": "LakehouseTable", "table": "Aircrafts" }, { "kind": "KustoTable", "table": "AircraftReadings" } ] }
  ],
  "relationships": [
    { "name": "operates", "source": "<Airline et id>", "target": "<Aircraft et id>" }
  ]
}
```

---

## Example 2 — Route a non-timeseries read to `sqldw-consumption-cli` (default)

> User intent: "list all aircraft manufactured by Contoso." Entity type `Aircraft` has a `NonTimeSeries` binding against Lakehouse `dbo.Aircrafts`. **Default route is SQL endpoint**; route to Spark only on explicit user preference.

### Extract routing inputs from grounding JSON

```bash
jq -c '
  .entityTypes[] | select(.name=="Aircraft")
  | .bindings[] | select(.dataBindingType=="NonTimeSeries" and .source.kind=="LakehouseTable")
  | {
      workspaceId: .source.workspaceId,
      itemId:      .source.itemId,
      schema:      .source.sourceSchema,
      table:       .source.sourceTableName,
      keyCol:      (.propertyBindings[] | select(.targetPropertyId == $key) | .sourceColumnName),
      mfrCol:      (.propertyBindings[] | select(.targetPropertyId == $mfr) | .sourceColumnName)
    }
' --argjson key '"<tankid-prop-id>"' --argjson mfr '"<manufacturer-prop-id>"' \
  ./_ont/grounding.json
```

### Compose the T-SQL and delegate (default path)

```sql
-- T-SQL — user intent mapped through propertyBindings
SELECT TOP 100 AssetId, Manufacturer
FROM   dbo.Aircrafts
WHERE  Manufacturer = 'Contoso';
```

Hand off to `sqldw-consumption-cli` with resolved `{ workspaceId, itemId, sourceSchema="dbo" }` and the composed T-SQL string.

### Spark alternate (only when user explicitly wants Spark)

```sql
-- Spark SQL — use Spark-native syntax; no DATEADD / SYSUTCDATETIME
SELECT AssetId, Manufacturer
FROM   dbo.Aircrafts
WHERE  Manufacturer = 'Contoso'
LIMIT  100
```

Hand off to `spark-consumption-cli` with the same resolved connection + this Spark SQL string.

---

## Example 3 — Route a timeseries read to `eventhouse-consumption-cli`

> User intent: "show altitude excursions on aircraft `N42ZA` in the last hour." Entity type `Aircraft` has a `TimeSeries` binding against Eventhouse table `AircraftReadings`.

### Extract routing inputs

```bash
jq -c '
  .entityTypes[] | select(.name=="Aircraft")
  | .bindings[] | select(.dataBindingType=="TimeSeries" and .source.kind=="KustoTable")
  | {
      clusterUri: .source.clusterUri,
      dbName:     .source.databaseName,
      table:      .source.sourceTableName,
      ts:         .timestampColumnName,
      keyCol:     (.propertyBindings[] | select(.targetPropertyId == $key) | .sourceColumnName),
      tempCol:    (.propertyBindings[] | select(.targetPropertyId == $temp) | .sourceColumnName)
    }
' --argjson key '"<tankid-prop-id>"' --argjson temp '"<altitude-prop-id>"' \
  ./_ont/grounding.json
```

### Compose KQL and delegate (pattern; `eventhouse-consumption-cli` owns the actual `az rest` call)

```kql
AircraftReadings
| where AssetId == "N42ZA"
| where PreciseTimestamp > ago(1h)
| where AltitudeFt > 35000
| project PreciseTimestamp, AltitudeFt
| order by PreciseTimestamp desc
```

Delegate payload:

```json
{ "clusterUri": "https://<cluster>.kusto.fabric.microsoft.com",
  "dbName":     "TelemetryDB",
  "kql":        "<the query above>" }
```

---

## Example 4 — Cross-source relationship traversal

> User intent: "Which aircraft does Airline `AC` operate, and what is the latest altitude readings for each?" The relationship `operates` has:
>
> - A Lakehouse contextualization on `dbo.HubAircraftAssignment (AirlineId, TailNumber)`
> - `Airline` entity type bound to Lakehouse `dbo.Airlines`
> - `Aircraft` entity type with a `TimeSeries` binding to Eventhouse `AircraftReadings`

### Step 1 — Lakehouse: list aircraft keys for `AC`

```sql
-- Delegated to sqldw-consumption-cli (Lakehouse SQL endpoint)
SELECT DISTINCT TailNumber
FROM   dbo.HubAircraftAssignment
WHERE  AirlineId = 'AC'
```

### Step 2 — Eventhouse: latest reading per aircraft

```kql
// Delegated to eventhouse-consumption-cli
let aircraft = dynamic([ "N42ZA", "T-43", "T-77" ]);    // from Step 1 results
AircraftReadings
| where AssetId in (aircraft)
| where PreciseTimestamp > ago(24h)
| summarize arg_max(PreciseTimestamp, *) by AssetId
| project AssetId, PreciseTimestamp, AltitudeFt
```

### Step 3 — Merge in the agent

Pair Step 1 output (aircraft IDs) with Step 2 output (latest readings) on `TailNumber`/`AssetId`, then render using ontology-level property names (`TailNumber`, `PreciseTimestamp`, `AltitudeFt`) — not the physical columns.

> **Size guard:** if Step 1 returns more than ~10,000 `TailNumber` values, fall back to narrowing Step 1 (add more filters), tightening the Kusto time window in Step 2, or batching the key list into multiple sub-10k Kusto calls. See [routing.md § Cross-Source Traversal](routing.md#cross-source-traversal-lakehouse--eventhouse).

---

## Example 5 — Detecting a mis-authored ontology

> Running the enumeration may reveal a `KustoTable` binding that claims `dataBindingType: "NonTimeSeries"` — this combination is not supported in preview.

```bash
jq '
  [.entityTypes[] | .bindings[]
    | select(.source.kind=="KustoTable" and .dataBindingType=="NonTimeSeries")
    | { et: input_line_number, binding: .bindingId }]
' ./_ont/grounding.json
```

If this returns a non-empty array, surface it to the user: *"This ontology has an invalid `KustoTable` + `NonTimeSeries` binding — Eventhouse sources are TimeSeries-only. I can forward the fix to `fabriciq-ontology-authoring-cli`."* Do **not** try to route a query through such a binding.

---

## Session cleanup

Grounding JSON, decoded tree, and `./_ont/` contain raw ontology schema — safe to share internally but may expose source table names / workspace IDs. Delete after a session if ephemeral:

```bash
rm -rf ./_ont
```

The ontology itself is not modified by any example in this file — all reads go through `Get Item Definition` and the sibling consumption skills.
