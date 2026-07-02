# Discovery Patterns and Queries

Extended discovery patterns beyond the basics in SKILL.md Agentic Exploration. All patterns use `az rest` with JMESPath queries and `jq` for JSON processing.

## Listing and Filtering Dataflows

### List All Dataflows with Full Details

```bash
# All dataflows with description and type
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows" \
  --query "value[].{id:id, name:displayName, desc:description, type:type}" -o table
```

### List with Pagination (Handling continuationToken)

```bash
# Paginate through all dataflows
URL="$API/workspaces/$WS_ID/dataflows"
while [ -n "$URL" ]; do
  RESPONSE=$(az rest --method get --resource "https://api.fabric.microsoft.com" --url "$URL")
  echo "$RESPONSE" | jq -r '.value[] | [.id, .displayName] | @tsv'
  TOKEN=$(echo "$RESPONSE" | jq -r '.continuationToken // empty')
  if [ -n "$TOKEN" ]; then
    URL="$API/workspaces/$WS_ID/dataflows?continuationToken=$TOKEN"
  else
    URL=""
  fi
done
```

### Cross-Workspace Dataflow Inventory

```bash
# Find dataflows across all accessible workspaces
for ws in $(az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces" --query "value[].id" -o tsv); do
  WS_NAME=$(az rest --method get --resource "https://api.fabric.microsoft.com" \
    --url "$API/workspaces/$ws" --query "displayName" -o tsv 2>/dev/null)
  DATAFLOWS=$(az rest --method get --resource "https://api.fabric.microsoft.com" \
    --url "$API/workspaces/$ws/dataflows" --query "value[].displayName" -o tsv 2>/dev/null)
  if [ -n "$DATAFLOWS" ]; then
    echo "=== $WS_NAME ($ws) ==="
    echo "$DATAFLOWS"
  fi
done
```

## Definition Decoding

### Decode All Definition Parts

```bash
RESPONSE=$(az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition")

# Decode each part
for PART_PATH in "mashup.pq" "queryMetadata.json" ".platform"; do
  echo "=== $PART_PATH ==="
  echo "$RESPONSE" | jq -r ".definition.parts[] | select(.path==\"$PART_PATH\") | .payload" | base64 --decode
  echo ""
done
```

### Handle LRO for getDefinition

```bash
# getDefinition may return 202 with Location header
HTTP_CODE=$(curl -s -o /tmp/df_def.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $(az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv)" \
  "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition")

if [ "$HTTP_CODE" = "202" ]; then
  LOCATION=$(grep -i "location:" /tmp/df_def_headers.txt | tr -d '\r' | awk '{print $2}')
  echo "LRO started. Polling $LOCATION ..."
  while true; do
    STATUS=$(az rest --method get --resource "https://api.fabric.microsoft.com" \
      --url "$LOCATION" --query "status" -o tsv)
    echo "Status: $STATUS"
    [ "$STATUS" = "Succeeded" ] || [ "$STATUS" = "Failed" ] && break
    sleep 5
  done
  # Get the result
  az rest --method get --resource "https://api.fabric.microsoft.com" \
    --url "${LOCATION}/result"
fi
```

### Extract Query Names from mashup.pq

```bash
# Decode mashup.pq and list all shared queries
az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition" | \
  jq -r '.definition.parts[] | select(.path=="mashup.pq") | .payload' | \
  base64 --decode | grep -oP '(?<=shared )\w+(?= =)'
```

### Analyze Connections from queryMetadata.json

> **Inline / literal-source dataflows:** queries built from an inline expression
> (e.g. `#table(...)`, hardcoded literals) have **no external data source**, so
> `queryMetadata.json` contains no `connections` entries (empty/absent array).
> Report "this dataflow has no external data source connections (inline source)"
> rather than implying a binding exists.

```bash
# Decode queryMetadata.json and list connections
az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition" | \
  jq -r '.definition.parts[] | select(.path=="queryMetadata.json") | .payload' | \
  base64 --decode | jq '.connections // [] | if length == 0 then "No external connections (inline/literal source)" else .[] | {path, kind, connectionId} end'
```

### Identify Load-Enabled vs Helper Queries

```bash
# Decode queryMetadata.json and classify queries
az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition" | \
  jq -r '.definition.parts[] | select(.path=="queryMetadata.json") | .payload' | \
  base64 --decode | jq '.queriesMetadata | to_entries[] | {
    name: .key,
    loadEnabled: .value.loadEnabled,
    isHidden: .value.isHidden,
    role: (if .value.loadEnabled then "OUTPUT" elif .value.isHidden then "HELPER (hidden)" else "STAGING" end)
  }'
```

## Parameter Discovery

> **Non-parametric dataflows:** the `/parameters` endpoint returns
> `DataflowNotParametricError` (HTTP 4xx) when a dataflow has no Power Query
> parameters. Handle it gracefully — report "this dataflow has no parameters"
> rather than surfacing the raw error — and optionally confirm by scanning
> mashup.pq for `IsParameterQuery` (see "Find Parameters in mashup.pq" below).

### Format Parameters as Report

```bash
# Tabular parameter report
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/parameters" | \
  jq -r '.value[] | "Parameter: \(.name)\n  Type:     \(.type)\n  Required: \(.isRequired)\n  Default:  \(.defaultValue // "none")\n  Desc:     \(.description // "none")\n"'
```

### Find Parameters in mashup.pq

```bash
# Extract parameter definitions from M code
az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition" | \
  jq -r '.definition.parts[] | select(.path=="mashup.pq") | .payload' | \
  base64 --decode | grep "IsParameterQuery"
```

## Job History Analysis

### Summarize Recent Job Results

```bash
# Count jobs by status
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/jobs/instances" | \
  jq '[.value[] | .status] | group_by(.) | map({status: .[0], count: length})'
```

### Calculate Average Refresh Duration

```bash
# Average duration of completed jobs (in seconds)
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/jobs/instances" | \
  jq '[.value[] | select(.status=="Completed" and .endTimeUtc != null) |
    (((.endTimeUtc | fromdateiso8601) - (.startTimeUtc | fromdateiso8601)))] |
    if length > 0 then (add / length | round) else 0 end' | \
  xargs -I{} echo "Average refresh duration: {} seconds"
```

### Extract Failure Reasons

```bash
# List all failures with reasons
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/jobs/instances" | \
  jq -r '.value[] | select(.status=="Failed") | "\(.startTimeUtc) | \(.failureReason // "unknown")"'
```
