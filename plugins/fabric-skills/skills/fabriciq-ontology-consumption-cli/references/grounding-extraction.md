# Ontology Consumption — Grounding Extraction Reference

Deep reference for turning a Fabric Ontology item definition into an agent-ready **grounding JSON**. SKILL.md keeps the decision content (scope, routing, Must/Prefer/Avoid). This file holds the full fetch / decode / parse / summarise recipes.

See [ONTOLOGY-AUTHORING-CORE.md § Definition Tree](../../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#definition-tree) for the authoritative file-and-folder shape of the parts you will decode — reading it is the best way to understand every field the summary exposes.

---

## Fetch and Decode an Ontology Definition

`Get Item Definition` is a Long-Running Operation. Every part payload is base64-encoded text (`payloadType = "InlineBase64"`). The flow is always **POST → poll LRO → GET result → base64-decode each part**.

### Bash — portable (macOS + Linux + WSL)

```bash
# Prereq: WS_ID, ONT_ID, az login done
OUT_DIR="./ontology_${ONT_ID}"
mkdir -p "${OUT_DIR}"

# 1. Kick off the LRO, capture the operation id (stays on api.fabric.microsoft.com)
OP_ID=$(az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/items/${ONT_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --output none --only-show-errors --verbose 2>&1 \
  | grep -i 'x-ms-operation-id:' | head -n 1 | awk '{print $NF}' | tr -d '\r')

if [ -z "$OP_ID" ]; then
  echo "Failed to capture x-ms-operation-id from getDefinition" >&2
  exit 1
fi
OP_URL="https://api.fabric.microsoft.com/v1/operations/${OP_ID}"

# 2. Poll until Succeeded (prefer the operations endpoint; Location polling is also supported with the right audience)
while :; do
  STATE=$(az rest --method GET --url "$OP_URL" --resource "https://api.fabric.microsoft.com" | jq -r '.status')
  case "$STATE" in
    Succeeded) break ;;
    Failed|Cancelled) echo "LRO ended in state: $STATE" >&2; \
      az rest --method GET --url "$OP_URL" --resource "https://api.fabric.microsoft.com" | jq -r '.error' >&2; exit 1 ;;
    *) sleep 5 ;;
  esac
done

# 3. Retrieve the result
DEF=$(az rest --method GET --url "${OP_URL}/result" --resource "https://api.fabric.microsoft.com")
echo "$DEF" > "${OUT_DIR}/_raw_definition.json"
echo "Parts: $(echo "$DEF" | jq '.definition.parts | length')"

# 4. Decode each part → ${OUT_DIR}/<path>.json (cross-platform base64 via python3)
echo "$DEF" | jq -c '.definition.parts[]' | while read -r PART; do
  P_PATH=$(echo "$PART" | jq -r '.path')
  P_PAYLOAD=$(echo "$PART" | jq -r '.payload')
  mkdir -p "${OUT_DIR}/$(dirname "$P_PATH")"
  printf '%s' "$P_PAYLOAD" \
    | python3 -c "import sys,base64; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))" \
    > "${OUT_DIR}/${P_PATH}"
done

echo "Decoded tree at ${OUT_DIR}/"
```

> The `python3` base64 pipe is the portable choice: GNU `base64 -d` and BSD `base64 -D` disagree on the flag name and on how aggressively they reject whitespace. `python3 base64.b64decode` accepts the output both encoders produce.

### PowerShell

```powershell
param(
  [string]$WsId,
  [string]$OntId,
  [string]$OutDir = ".\ontology_$OntId"
)

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# 1. Kick off LRO; az rest emits the x-ms-operation-id header on the debug channel
$verbose = az rest --method POST `
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WsId/items/$OntId/getDefinition" `
  --resource "https://api.fabric.microsoft.com" `
  --verbose 2>&1 | Out-String

$opId = ($verbose -split "`n" | Where-Object { $_ -match 'x-ms-operation-id:\s*(\S+)' } | ForEach-Object { $matches[1] } | Select-Object -First 1)
if (-not $opId) { throw "No x-ms-operation-id captured from getDefinition" }
$opUrl = "https://api.fabric.microsoft.com/v1/operations/$opId"

# 2. Poll the operations endpoint (preferred; Location polling is also supported with the right audience)
while ($true) {
  $op = az rest --method GET --url $opUrl --resource "https://api.fabric.microsoft.com" | ConvertFrom-Json
  $state = $op.status
  switch ($state) {
    "Succeeded"         { break }
    { $_ -in @("Failed","Cancelled") } { throw "LRO ended: $state — $($op.error.errorCode) $($op.error.message)" }
    default             { Start-Sleep -Seconds 5 }
  }
  if ($state -eq "Succeeded") { break }
}

# 3. Retrieve result
$def = az rest --method GET --url "$opUrl/result" --resource "https://api.fabric.microsoft.com" | ConvertFrom-Json
$def | ConvertTo-Json -Depth 20 | Out-File "$OutDir\_raw_definition.json" -Encoding utf8NoBOM

# 4. Decode each part
foreach ($part in $def.definition.parts) {
  $target = Join-Path $OutDir $part.path
  New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
  $bytes = [Convert]::FromBase64String($part.payload)
  [IO.File]::WriteAllBytes($target, $bytes)
}

Write-Host "Decoded tree at $OutDir"
```

---

## Tree Reconstruction

After decoding, `${OUT_DIR}/` mirrors the authoring tree documented in [ONTOLOGY-AUTHORING-CORE.md § Definition Tree](../../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#definition-tree):

```
${OUT_DIR}/
├── .platform
├── definition.json
├── EntityTypes/
│   └── {entityTypeId}/
│       ├── definition.json
│       └── DataBindings/
│           └── {guid}.json
└── RelationshipTypes/
    └── {relTypeId}/
        ├── definition.json
        └── Contextualizations/
            └── {guid}.json
```

Reconstruction into a Python dict (useful when generating grounding summaries or diffs):

```python
# reconstruct.py ${OUT_DIR}  →  ontology dict
import json, os, sys
from pathlib import Path

root = Path(sys.argv[1])
ont = {"platform": {}, "entityTypes": {}, "relationshipTypes": {}}

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

if (root / ".platform").exists():
    ont["platform"] = read_json(root / ".platform")

for et_dir in (root / "EntityTypes").glob("*"):
    et = {"definition": read_json(et_dir / "definition.json"), "dataBindings": []}
    for b in (et_dir / "DataBindings").glob("*.json") if (et_dir / "DataBindings").exists() else []:
        et["dataBindings"].append(read_json(b))
    ont["entityTypes"][et_dir.name] = et

for rt_dir in (root / "RelationshipTypes").glob("*") if (root / "RelationshipTypes").exists() else []:
    rt = {"definition": read_json(rt_dir / "definition.json"), "contextualizations": []}
    for c in (rt_dir / "Contextualizations").glob("*.json") if (rt_dir / "Contextualizations").exists() else []:
        rt["contextualizations"].append(read_json(c))
    ont["relationshipTypes"][rt_dir.name] = rt

print(json.dumps(ont, indent=2))
```

Unknown part paths (future preview additions) should be recorded under an `other: { path: content }` bucket so the agent can surface them to the user without crashing.

---

## Grounding Summary Schema

The **grounding JSON** is the agent-facing projection of the reconstructed tree. Every downstream routing decision reads from this shape:

```jsonc
{
  "ontologyId": "<guid>",
  "displayName": "<from .platform.metadata.displayName>",
  "entityTypes": [
    {
      "id": "<BigInt string>",
      "name": "<regex ^[a-zA-Z][a-zA-Z0-9_-]{0,127}$>",
      "namespace": "usertypes",
      "keyPropertyIds": ["<propertyId>", "..."],        // entityIdParts
      "displayNamePropertyId": "<propertyId>",
      "properties": [
        { "id": "<id>", "name": "<name>", "valueType": "String|Boolean|DateTime|Object|BigInt|Double" }
      ],
      "timeseriesProperties": [
        { "id": "<id>", "name": "<name>", "valueType": "DateTime|Double|BigInt|..." }
      ],
      "bindings": [
        {
          "bindingId": "<guid>",
          "dataBindingType": "NonTimeSeries | TimeSeries",
          "source": {
            "kind": "LakehouseTable | KustoTable",

            // Common to both
            "workspaceId": "<guid>",
            "itemId": "<guid>",                          // lakehouse id OR eventhouse id
            "sourceTableName": "<string>",

            // LakehouseTable only
            "sourceSchema": "<string, e.g. dbo>",

            // KustoTable only
            "clusterUri": "https://<cluster>.kusto.fabric.microsoft.com",
            "databaseName": "<KQL database name>"
          },

          // TimeSeries only
          "timestampColumnName": "<source column>",

          "propertyBindings": [
            { "targetPropertyId": "<propertyId>", "sourceColumnName": "<physical column>" }
          ]
        }
      ]
    }
  ],
  "relationshipTypes": [
    {
      "id": "<BigInt string>",
      "name": "<string>",
      "source": { "entityTypeId": "<id>" },
      "target": { "entityTypeId": "<id>" },
      "contextualizations": [
        {
          "contextId": "<guid>",
          "source": {
            "kind": "LakehouseTable",
            "workspaceId": "<guid>", "itemId": "<guid>",
            "sourceSchema": "<string>", "sourceTableName": "<linking table>"
          },
          // Composite keys are legal — these are ARRAYS.
          "sourceKeyRefBindings": [ { "sourceColumnName": "<source-side key column>" } ],
          "targetKeyRefBindings": [ { "sourceColumnName": "<target-side key column>" } ]
        }
      ]
    }
  ]
}
```

Field-by-field contract:

| Field | Derived from | Why the agent cares |
|---|---|---|
| `entityTypes[].id` / `.name` | `EntityTypes/{id}/definition.json` | Pick which concept to query |
| `entityTypes[].keyPropertyIds` | `entityIdParts[]` | Generates the `WHERE`/`where` predicate |
| `entityTypes[].displayNamePropertyId` | `displayNamePropertyId` | Default label column for result rendering |
| `properties[]` / `timeseriesProperties[]` | `properties[]` + `timeseriesProperties[]` | Full property catalog; filter / project candidates |
| `bindings[].source.kind` | `source.type` (e.g. `LakehouseTable`) | Drives routing decision (see [routing.md](routing.md)) |
| `bindings[].source.clusterUri` + `.databaseName` | Eventhouse-only binding fields | Supplied straight to `eventhouse-consumption-cli` — do **not** rediscover |
| `bindings[].source.workspaceId` + `.itemId` + `.sourceSchema` + `.sourceTableName` | Lakehouse / Warehouse binding fields | Supplied straight to `spark-consumption-cli` / `sqldw-consumption-cli` |
| `bindings[].timestampColumnName` | `TimeSeries` bindings only | Required for time-range filters on KQL + SparkSQL reads |
| `bindings[].propertyBindings[]` | DataBinding `propertyBindings[]` | Ontology-property-name → physical-column-name remap — **always** apply before composing queries |
| `relationshipTypes[].contextualizations[]` | `RelationshipTypes/{id}/Contextualizations/{guid}.json` | Linking table + key column **arrays** (`sourceKeyRefBindings[]` / `targetKeyRefBindings[]`, composite-key safe) for realising the relationship |

### jq transform — raw definition → grounding JSON (abridged)

```bash
# Given $DEF from the getDefinition result, produce grounding.json
# (This is a sketch — real implementation should walk the reconstructed tree, not the base64 array.)
jq '
  {
    ontologyId: (.ontologyId // ""),
    displayName: (.displayName // ""),
    _note: "Real entity/relationship population requires base64-decoding each part — see reconstruct.py above."
  }
' <<< "$DEF"
```

In practice, do the base64 decode in Python (or PowerShell), build the grounding summary from the reconstructed Python dict, then emit as JSON. The grounding summary is ~1–10 KB vs the raw `definition.parts[]` which is often 50 KB+ of base64 — give agents the summary, not the raw parts.

---

## Diff Two Ontologies

Useful when the agent wants to explain "what changed since the last session" before re-grounding.

```bash
# Assume two decoded trees: ./ont_before  ./ont_after
diff -ru ./ont_before ./ont_after | head -n 200
```

For a semantic diff (entity types added / removed / retyped), decode both sides to grounding JSON and jq-diff:

```bash
jq -n --slurpfile a grounding_before.json --slurpfile b grounding_after.json '
  {
    entityTypesAdded:   [($b[0].entityTypes[]     | .name)] - [($a[0].entityTypes[] | .name)],
    entityTypesRemoved: [($a[0].entityTypes[]     | .name)] - [($b[0].entityTypes[] | .name)],
    relationshipsAdded: [($b[0].relationshipTypes[] | .name)] - [($a[0].relationshipTypes[] | .name)],
    relationshipsRemoved: [($a[0].relationshipTypes[] | .name)] - [($b[0].relationshipTypes[] | .name)]
  }
'
```

Deeper diffs (binding column renames, property-type changes) should walk the grounding JSON field by field and produce a structured changelog rather than a raw diff — much easier for the LLM to summarise back to the user.

---

## Gotchas

- **`itemId` in a binding is the source item ID, not the ontology's own ID.** For `KustoTable` bindings, it's the **Eventhouse** item ID; the `databaseName` lives alongside.
- **Cross-workspace bindings are legal.** A binding's `workspaceId` may differ from the ontology's workspace. Always pass the binding's own `workspaceId` to the delegate.
- **Part payloads are case-sensitive on path.** `EntityTypes/…` and `entityTypes/…` are different parts; enumerate with the exact casing returned.
- **`.platform` is JSON despite the absence of an extension.** Decode it as text and parse as JSON.
- **Empty `definition.json`** (`{}`) is valid and just means the ontology has no item-level metadata beyond platform.
- **Unknown `dataBindingType`** values — treat anything other than `NonTimeSeries` / `TimeSeries` as a forward-compat signal; log the value and skip routing decisions for that binding.
- **Timestamp column may not be present in `timeseriesProperties[]`.** It lives only in the binding's `timestampColumnName` — the ontology does not require an ontology-level property for it.
- **`entityIdParts` may include properties declared under `timeseriesProperties` in unusual models.** When composing a key filter, look up the property in both arrays.
