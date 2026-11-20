<!-- Mode reference for the `activator-cli` skill. Loaded on demand from `skills/activator-cli/SKILL.md` when the request matches the `consumption` mode. -->

# activator-cli consumption mode — Read-Only Activator Exploration via CLI

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | Optional background — workspace/item ID resolution detail; skip if `common/` is unavailable |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../../common/COMMON-CORE.md#fabric-topology--key-concepts) | |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401 |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../../common/COMMON-CORE.md#core-control-plane-rest-apis) | |
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../../common/COMMON-CORE.md#long-running-operations-lro) | `getDefinition` may return 202 |
| Rate Limiting & Throttling | [COMMON-CORE.md § Rate Limiting & Throttling](../../../common/COMMON-CORE.md#rate-limiting--throttling) | |
| Fabric Item Definitions | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Base64 payload structure |
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** |
| LRO Pattern | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern) | |
| Pagination Pattern | [COMMON-CLI.md § Pagination Pattern](../../../common/COMMON-CLI.md#pagination-pattern) | |
| Tool Stack | [Consumption mode § Tool Stack](#tool-stack) | |
| Connection | [Consumption mode § Connection](#connection) | |
| Listing Activator Items | [Consumption mode § Listing Activator Items](#listing-activator-items) | |
| Inspecting a Single Activator | [Consumption mode § Inspecting a Single Activator](#inspecting-a-single-activator) | |
| Reading the Definition | [Consumption mode § Reading the Definition](#reading-the-definition) | |
| Exploring Rules, Sources, and Actions | [Consumption mode § Exploring Rules, Sources, and Actions](#exploring-rules-sources-and-actions) | |
| Inspecting Power BI Sources | [Consumption mode § Inspecting Power BI Sources](#inspecting-power-bi-sources) | `powerBiSource-v1`, stored query JSON, `metricDefinition`, report/model lineage |
| Querying Activation History | [Consumption mode § Querying Activation History](#querying-activation-history) | Pointer — the `queryActivations` guidance is in its own reference |
| Must / Prefer / Avoid | [Consumption mode § Must / Prefer / Avoid](#must--prefer--avoid) | |
| Examples | [Consumption mode § Examples](#examples) | |

---

## Tool Stack

| Tool | Purpose | Install |
|---|---|---|
| **az cli** | Fabric REST API calls for reading Activator items and definitions | `winget install Microsoft.AzureCLI` |
| **jq** | JSON processing, Base64 decoding, definition inspection | `winget install jqlang.jq` |

---

## Connection

Use the shared authentication guidance in [COMMON-CLI.md § Authentication Recipes](../../../common/COMMON-CLI.md#authentication-recipes). Resolve workspace and item IDs per [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric). Examples below assume `WS_ID` and `REFLEX_ID` are already resolved.

---

## Listing Activator Items

### List All Activators in a Workspace

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes" \
  --resource "https://api.fabric.microsoft.com" \
  | jq '.value[] | {id, displayName, description}'
```

Required scopes: `Workspace.Read.All` or `Workspace.ReadWrite.All`

### Paginated Listing

For workspaces with many items, follow the `continuationUri` returned in each response:

```bash
NEXT_URL="https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes"
while [ -n "$NEXT_URL" ]; do
  RESPONSE=$(az rest --method GET \
    --url "$NEXT_URL" \
    --resource "https://api.fabric.microsoft.com")
  echo "$RESPONSE" | jq '.value[] | {id, displayName, description}'
  NEXT_URL=$(echo "$RESPONSE" | jq -r '.continuationUri // empty')
done
```

### Filter by Folder

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes?recursive=true&rootFolderId=${FOLDER_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  | jq '.value[] | {id, displayName}'
```

---

## Inspecting a Single Activator

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}" \
  --resource "https://api.fabric.microsoft.com" \
  | jq '{id, displayName, description, type, workspaceId}'
```

---

## Reading the Definition

> `getDefinition` is a **POST** (not GET), requires **ReadWrite** scopes (`Reflex.ReadWrite.All` or `Item.ReadWrite.All`) even for read-only inspection, and may return **202 LRO**. Use the `fabric_lro` helper from [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../../common/COMMON-CLI.md#long-running-operations-lro-pattern) so 202 responses can be polled via the `Location` header before decoding.

### Decode the Full Definition

```bash
DEFINITION=$(fabric_lro POST \
  "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}/getDefinition" \
  '{}')

echo "$DEFINITION" \
  | jq '.definition.parts[] | select(.path=="ReflexEntities.json") | .payload' -r \
  | base64 -d | jq .
```

### Save Definition to File

```bash
DEFINITION=$(fabric_lro POST \
  "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}/getDefinition" \
  '{}')

echo "$DEFINITION" \
  | jq '.definition.parts[] | select(.path=="ReflexEntities.json") | .payload' -r \
  | base64 -d | jq . > reflex-entities.json
```

---

## Exploring Rules, Sources, and Actions

Once you have the decoded `ReflexEntities.json`, use `jq` to extract specific components.

### List All Entity Types

```bash
cat reflex-entities.json | jq '[.[] | .type] | sort | group_by(.) | map({type: .[0], count: length})'
```

### List Data Sources

```bash
cat reflex-entities.json | jq '.[] | select(.type | endswith("Source-v1")) | {name: .payload.name, type: .type, id: .uniqueIdentifier}'
```

### List Rules

```bash
cat reflex-entities.json | jq '.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Rule") | {name: .payload.name, id: .uniqueIdentifier, shouldRun: .payload.definition.settings.shouldRun}'
```

### List Objects and Their Attributes

```bash
# Objects
cat reflex-entities.json | jq '.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Object") | {name: .payload.name, id: .uniqueIdentifier}'

# Attributes for a specific object
OBJECT_ID="<object-guid>"
cat reflex-entities.json | jq --arg oid "$OBJECT_ID" '.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Attribute" and .payload.parentObject.targetUniqueIdentifier == $oid) | {name: .payload.name, id: .uniqueIdentifier}'
```

### Inspect a Rule's Condition

```bash
RULE_ID="<rule-guid>"
cat reflex-entities.json \
  | jq --arg rid "$RULE_ID" '.[] | select(.uniqueIdentifier == $rid) | .payload.definition.instance' -r \
  | jq '.steps[] | {step: .name, rows: [.rows[] | .kind]}'
```

### List Actions (Fabric Item Actions)

```bash
cat reflex-entities.json | jq '.[] | select(.type == "fabricItemAction-v1") | {name: .payload.name, itemType: .payload.fabricItem.itemType, itemId: .payload.fabricItem.itemId}'
```

### Summary View

Get a high-level overview of an Activator's configuration:

```bash
cat reflex-entities.json | jq '{
  containers: [.[] | select(.type == "container-v1") | .payload.name],
  sources: [.[] | select(.type | endswith("Source-v1")) | {name: .payload.name, type: .type}],
  objects: [.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Object") | .payload.name],
  rules: [.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Rule") | {name: .payload.name, active: .payload.definition.settings.shouldRun}],
  actions: [.[] | select(.type == "fabricItemAction-v1") | {name: .payload.name, type: .payload.fabricItem.itemType}]
}'
```

---

## Inspecting Power BI Sources

Power BI-backed Activator sources use `powerBiSource-v1`. The source's parent
`container-v1` must use exact case-sensitive `payload.type: "pbiMetrics"`.
The source `query.queryString` is a JSON-string Power BI source query payload,
and `metricDefinition` describes the same semantic model metric,
dimensions, filters, and report visual lineage. The Activator API does not
accept semantic-model query text in `query.queryString`.

> **Current public API limitation:** Power BI-backed Activator definitions
> cannot currently be relied on for public ALM readback. `getDefinition` can
> reject an artifact that was imported successfully when PBI ALM export is
> disabled. Preserve the exact response and request/correlation ID, describe
> inspection as unavailable, and do not claim that persistence failed or that
> the source is absent solely because the definition cannot be exported.

Flag a missing parent container or any container type other than `pbiMetrics`.
In particular, `powerBiQueries` is invalid.

### Parse the Stored Query and Metric Definition

```bash
jq -r '.[] | select(.type == "powerBiSource-v1")
  | .payload.query.queryString' reflex-entities.json | jq .
```

`metricDefinition` can be either a JSON string or an object. Parse both forms
before explaining the metric:

```python
import json
from pathlib import Path

entities = json.loads(Path("reflex-entities.json").read_text(encoding="utf-8"))
for entity in entities:
    if entity.get("type") != "powerBiSource-v1":
        continue
    payload = entity["payload"]
    metric = payload.get("metricDefinition")
    if isinstance(metric, str):
        metric = json.loads(metric)
    print(json.dumps({
        "sourceName": payload.get("name"),
        "datasetId": payload.get("datasetId") or payload.get("metadata", {}).get("datasetId"),
        "reportId": payload.get("reportId") or payload.get("metadata", {}).get("reportId"),
        "pageId": payload.get("pageId") or payload.get("metadata", {}).get("pageId"),
        "visualId": payload.get("visualId") or payload.get("metadata", {}).get("visualId"),
        "measureName": payload.get("measureName") or payload.get("metadata", {}).get("measureName"),
        "dimensionValue": payload.get("dimensionValue"),
        "metricDefinition": metric,
    }, indent=2))
```

Persisted Power BI source queries should omit `top`.

### Consistency Checks

Call out any of these issues:

- `getDefinition` is blocked because PBI ALM export is disabled. Report the
  limitation rather than fabricating source details.
- `query.queryString` or `metricDefinition` is not parseable JSON.
- The parent container is missing or is not exact `pbiMetrics`.
- `metricDefinition.type` is not `DatasetMetric`.
- Source `datasetId`, query `provider.datasetId`, and
  `metricDefinition.definition.datasetId` disagree.
- The persisted query includes `top`.
- A personalized source has `dimensionValue`, but the same value is absent
  from the query filters or `metricDefinition.definition.filter`.
- `metricDefinition.definition.filter` uses `BasicFilter` instead of the
  semantic-query `Version` / `From` / `Where` contract.
- Report, page, visual, or measure lineage is missing.

---

## Must / Prefer / Avoid

### MUST DO

- **Always use `--resource https://api.fabric.microsoft.com`** with `az rest`
- **Always send `--body '{}'`** for `getDefinition` — it is a POST and omitting the body can cause 411 errors
- **Handle LRO responses** — `getDefinition` may return 202; poll the `Location` header
- **Base64-decode** the `ReflexEntities.json` payload before inspection — it is Base64-encoded in the API response
- **JSON-parse** the `definition.instance` field in rule entities — it is a JSON-encoded string, not a nested object
- **For Power BI sources, JSON-parse** both `query.queryString` and `metricDefinition` before explaining metrics, dimensions, or filters

### PREFER

- **Summary view first** — give users a high-level overview before diving into individual entities
- **Save to file** when the definition is large — decode once and explore with `jq` locally
- **Discover IDs dynamically** via workspace and item listing + JMESPath filtering
- **Paginated listing** for workspaces with many Activator items
- **Report Power BI lineage** — include dataset/report/page/visual/measure metadata when available
- **Flag Power BI filter inconsistencies** — especially missing personalized dimension values

### AVOID

- **Hardcoded workspace or item IDs** — always resolve dynamically
- **Using GET for `getDefinition`** — it is a POST endpoint; GET will return 405
- **Attempting to read definitions of items with encrypted sensitivity labels** — it will be blocked
- **Modifying data** — this is a read-only skill; use [authoring mode](authoring.md) for write operations
- **Treating Power BI source queries as semantic-model query text** — they are source payloads stored as JSON strings
- **Querying the Eventhouse or the MCP endpoint for activation history** — use `queryActivations` as described in `references/consumption/activation-history.md`

---

## Examples

### List All Activators and Show Their Rules

```bash
# Step 1: List activators
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes" \
  --resource "https://api.fabric.microsoft.com" \
  | jq '.value[] | {id, displayName}'

# Step 2: For a specific activator, get and decode its definition
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body '{}' \
  | jq '.definition.parts[] | select(.path=="ReflexEntities.json") | .payload' -r \
  | base64 -d \
  | jq '.[] | select(.type == "timeSeriesView-v1" and .payload.definition.type == "Rule") | {name: .payload.name, active: .payload.definition.settings.shouldRun}'
```

### Inspect a Specific Rule's Full Configuration

```bash
# Decode definition and extract rule details
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" \
  --body '{}' \
  | jq '.definition.parts[] | select(.path=="ReflexEntities.json") | .payload' -r \
  | base64 -d \
  | jq '.[] | select(.payload.name == "Too hot for medicine") | .payload.definition.instance' -r \
  | jq '.steps[] | {step: .name, details: .rows}'
```

---

## Querying Activation History

Activation history — when each rule fired — lives in its own reference,
`references/consumption/activation-history.md`, linked from `SKILL.md`. Read it end to end before calling `queryActivations`.

---

## Agent Integration Notes

- This skill uses the Fabric Items API (`/reflexes`) for listing and `getDefinition` for inspection
- No additional data-plane protocols are needed for item/rule inspection — all use `az rest` with the Fabric API audience
- `getDefinition` requires **ReadWrite** scopes even for read-only access — this is a known API requirement
- **Activation history** uses the public `queryActivations` endpoint (`POST /v1/workspaces/{ws}/reflexes/{id}/queryActivations`) with the same `az rest` audience — no MCP connection or Eventhouse access is needed
- For **creating or modifying** Activator items and rules, use the [authoring mode](authoring.md) skill
