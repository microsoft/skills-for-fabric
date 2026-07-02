---
name: eventstream-consumption-cli
description: >
  List, inspect, and monitor Fabric Eventstream real-time ingestion pipelines via
  the Items REST API. Discover Eventstreams across workspaces, decode base64 graph
  topologies tracing event flow from source through operators to destination nodes.
  Validate connection IDs, wiring, retention policies (1-90 days), and throughput
  levels. Retrieve Custom Endpoint Kafka credentials via Topology API. Use to:
  (1) list Eventstreams, (2) inspect Eventstream topology showing sources and
  destinations, (3) validate Eventstream configurations, (4) check Eventstream
  retention policy and throughput level, (5) get connection strings. Triggers:
  "list eventstreams", "inspect eventstream", "inspect eventstream topology",
  "eventstream sources and destinations",
  "eventstream health", "eventstream configuration", "eventstream retention",
  "eventstream retention policy", "eventstream throughput level",
  "eventstream connection string", "custom endpoint credentials",
  "kafka connection", "check eventstream".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. Eventstream ≠ Eventhouse. Eventstream is a real-time event ingestion and routing pipeline. For KQL queries, use `eventhouse-consumption-cli`.

# Eventstream Consumption — CLI Skill

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [needed for finding workspace id by its name or item id by its name, item type, and workspace id] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | |
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) | |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Gotchas, Best Practices & Troubleshooting | [COMMON-CORE.md § Gotchas, Best Practices & Troubleshooting](../../common/COMMON-CORE.md#gotchas-best-practices--troubleshooting) | |
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) | |
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes pagination and LRO helpers |
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference | [COMMON-CLI.md § Quick Reference](../../common/COMMON-CLI.md#quick-reference) | `az rest` template + token audience/tool matrix |
| Listing and Discovering Eventstreams | [EVENTSTREAM-CONSUMPTION-CORE.md § Listing and Discovering Eventstreams](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#listing-and-discovering-eventstreams) | List, Get, Search across workspaces |
| Inspecting Eventstream Topology | [EVENTSTREAM-CONSUMPTION-CORE.md § Inspecting Eventstream Topology](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#inspecting-eventstream-topology) | Decode base64 definition → trace graph flow |
| Monitoring Eventstream Health | [EVENTSTREAM-CONSUMPTION-CORE.md § Monitoring Eventstream Health](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#monitoring-eventstream-health) | Retention and throughput checks |
| Source and Destination Status | [EVENTSTREAM-CONSUMPTION-CORE.md § Source and Destination Status](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#source-and-destination-status) | Validation checklist for sources and destinations |
| Integration with Downstream Analytics | [EVENTSTREAM-CONSUMPTION-CORE.md § Integration with Downstream Analytics](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#integration-with-downstream-analytics) | Eventhouse, Lakehouse, Activator, Real-Time Hub |
| Gotchas and Troubleshooting Reference | [EVENTSTREAM-CONSUMPTION-CORE.md § Gotchas and Troubleshooting Reference](../../common/EVENTSTREAM-CONSUMPTION-CORE.md#gotchas-and-troubleshooting-reference) | 10 common issues with causes and fixes |
| List Eventstreams | [SKILL.md § List Eventstreams](#list-eventstreams) | |
| Inspect Eventstream Topology | [SKILL.md § Inspect Eventstream Topology](#inspect-eventstream-topology) | Decode and explore the graph |
| Get Custom Endpoint Connection String | [SKILL.md § Get Custom Endpoint Connection String](#get-custom-endpoint-connection-string) | Retrieve Kafka/EH connection via Topology API |
| Validate Eventstream Configuration | [SKILL.md § Validate Eventstream Configuration](#validate-eventstream-configuration) | |
| Gotchas, Rules, Troubleshooting | [SKILL.md § Gotchas, Rules, Troubleshooting](#gotchas-rules-troubleshooting) | **MUST DO / AVOID / PREFER** checklists |

---

## List Eventstreams

### List All Eventstreams in a Workspace

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams" \
  --resource "https://api.fabric.microsoft.com"
```

Returns an array of Eventstream items. Use JMESPath to filter by name:

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[?displayName=='my-eventstream']"
```

### Get Eventstream Details

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}" \
  --resource "https://api.fabric.microsoft.com"
```

---

## Inspect Eventstream Topology

> **Tip**: The Topology API (`GET .../eventstreams/{id}/topology`) returns runtime status, error info, and node IDs without base64 decoding. Prefer it for operational inspection (health checks, connection retrieval). Use `POST .../getDefinition` (below) when you need the full authoring-time graph structure for topology modification.

Retrieve the Eventstream definition and decode it to inspect the full graph topology.

### Step 1: Get the Definition

> **API Note**: The Eventstream Definition API uses `POST .../getDefinition`, not `GET .../definition`. This follows the Fabric Items Definition pattern. See [official docs](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/api-get-eventstream-definition).

```bash
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{}'
```

### Step 2: Decode the Topology

Extract the `eventstream.json` part's `payload` field and base64-decode it:

```bash
# Using jq + base64 (Linux; on macOS use base64 -D instead of -d)
az rest --method POST \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}/getDefinition" \
  --resource "https://api.fabric.microsoft.com" \
  --body '{}' \
  | jq -r '.definition.parts[] | select(.path=="eventstream.json") | .payload' \
  | base64 -d | jq .
```

```powershell
# PowerShell (Windows)
$def = az rest --method POST `
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WORKSPACE_ID/eventstreams/$EVENTSTREAM_ID/getDefinition" `
  --resource "https://api.fabric.microsoft.com" `
  --body '{}' | ConvertFrom-Json
$payload = ($def.definition.parts | Where-Object { $_.path -eq 'eventstream.json' }).payload
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Step 3: Summarize the Topology

After decoding, count and list each node type:

| Metric | Path in decoded JSON |
|--------|---------------------|
| Sources | `.sources[] \| .name, .type` |
| Destinations | `.destinations[] \| .name, .type` |
| Operators | `.operators[] \| .name, .type` |
| Streams | `.streams[] \| .name, .type` |

---

## Get Custom Endpoint Connection String

The `POST .../getDefinition` endpoint returns **empty properties** for Custom Endpoint sources. To retrieve the Kafka/Event Hub connection info, use the **Topology API** `/connection` endpoint.

> **Important**: This endpoint requires `Eventstream.ReadWrite.All` permission scope (not just Read).

### Step 1: Get the Topology to Find the Source ID

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}/topology" \
  --resource "https://api.fabric.microsoft.com"
```

From the response, find the Custom Endpoint source node and extract its `id`:

```bash
# Extract the sourceId for a Custom Endpoint source (use name filter if multiple exist)
SOURCE_ID=$(az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}/topology" \
  --resource "https://api.fabric.microsoft.com" \
  | jq -r '[.sources[] | select(.type=="CustomEndpoint")] | if length == 0 then error("No Custom Endpoint sources found in this Eventstream") elif length > 1 then error("Multiple Custom Endpoint sources found — filter by .name") else .[0].id end') \
  || { echo "Failed to resolve Custom Endpoint source ID"; exit 1; }

if [ -z "$SOURCE_ID" ]; then echo "SOURCE_ID is empty — check topology output"; exit 1; fi
```

```powershell
# PowerShell — extract sourceId for Custom Endpoint (fails clearly if multiple exist)
$topology = az rest --method GET `
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WORKSPACE_ID/eventstreams/$EVENTSTREAM_ID/topology" `
  --resource "https://api.fabric.microsoft.com" | ConvertFrom-Json
$customSources = @($topology.sources | Where-Object { $_.type -eq 'CustomEndpoint' })
if ($customSources.Count -eq 0) { throw "No Custom Endpoint sources found in this Eventstream" }
if ($customSources.Count -gt 1) { throw "Multiple Custom Endpoint sources found. Filter by name: $($customSources.name -join ', ')" }
$sourceId = $customSources[0].id
```

### Step 2: Get the Connection Details

> ⚠️ **Security**: This endpoint returns access keys and connection strings. Get explicit user confirmation before calling it. Redact `primaryKey`, `secondaryKey`, `primaryConnectionString`, and `secondaryConnectionString` from any displayed output unless the user explicitly asks for secret values in a secure context. Avoid logging raw credentials; store securely and rotate as needed.

```bash
az rest --method GET \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WORKSPACE_ID}/eventstreams/${EVENTSTREAM_ID}/sources/${SOURCE_ID}/connection" \
  --resource "https://api.fabric.microsoft.com"
```

```powershell
az rest --method GET `
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WORKSPACE_ID/eventstreams/$EVENTSTREAM_ID/sources/$sourceId/connection" `
  --resource "https://api.fabric.microsoft.com" | ConvertFrom-Json
```

### Expected Response

```json
{
  "fullyQualifiedNamespace": "namespace.servicebus.windows.net",
  "eventHubName": "es_<guid>",
  "accessKeys": {
    "primaryKey": "...",
    "secondaryKey": "...",
    "primaryConnectionString": "Endpoint=sb://namespace.servicebus.windows.net/;...",
    "secondaryConnectionString": "..."
  }
}
```

### Kafka Producer Configuration

Use the response to configure a Kafka producer:

| Setting | Value |
|---------|-------|
| `bootstrap_servers` | `{fullyQualifiedNamespace}:9093` |
| `topic` | `{eventHubName}` |
| `security_protocol` | `SASL_SSL` |
| `sasl_mechanism` | `PLAIN` |
| `sasl_plain_username` | `$ConnectionString` (fixed literal — not a variable) |
| `sasl_plain_password` | `{primaryConnectionString}` |

> **Limitation**: The `/connection` endpoint is only supported for Custom Endpoint sources (returns Kafka/Event Hub credentials). Other source types (Event Hub, IoT Hub, etc.) store their connection configuration (e.g., `dataConnectionId`, `consumerGroup`) directly in the decoded definition properties.

---

## Validate Eventstream Configuration

Check key configuration aspects of a decoded Eventstream topology:

### Source Validation Checklist

| Check | How |
|-------|-----|
| Source type is API-supported | Compare against 25 known type enums |
| Cloud connection exists | Verify `dataConnectionId` GUID resolves |
| Consumer group set | Required for Event Hub, IoT Hub, Kafka sources |
| Serialization matches source | `inputSerialization.type` = `Json`, `Csv`, or `Avro` |

### Destination Validation Checklist

| Check | How |
|-------|-----|
| Destination type is valid | Must be `Lakehouse`, `Eventhouse`, `Activator`, or `CustomEndpoint` |
| Target item accessible | Verify `workspaceId` + `itemId` resolve via GET |
| Input wired | `inputNodes` array must not be empty |
| Eventhouse direct ingestion | `connectionName` and `mappingRuleName` set |

### EventstreamProperties Validation

Decode `eventstreamProperties.json` and check:
- `retentionTimeInDays` is within 1–90
- `eventThroughputLevel` is `Low`, `Medium`, or `High`

---

## Gotchas, Rules, Troubleshooting

### MUST DO

- **Always pass `--resource https://api.fabric.microsoft.com`** with `az rest` calls
- **Always use JMESPath filtering** to resolve workspace name → ID and item name → ID
- **Always base64-decode** the definition payload before inspecting topology (not needed for the Topology API — that returns JSON directly)
- **For Custom Endpoint connection details, use the Topology API** — `POST .../getDefinition` returns empty properties; call `GET .../topology` to get the sourceId, then `GET .../sources/{sourceId}/connection`
- **Use POST for definition endpoints** — `POST .../getDefinition` (not GET), `POST .../updateDefinition` (not PUT). See [official docs](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/api-get-eventstream-definition).
- **Handle pagination** — check for `continuationUri` in list responses
- **Poll LRO responses** — Get Definition may return `202 Accepted`

### PREFER

- Decode topology JSON into structured output for readable summaries
- Use `jq` (bash) or `ConvertFrom-Json` (PowerShell) for parsing
- Validate configurations before reporting issues to users
- Cross-reference destinations with downstream skills (eventhouse, sqldw, spark)

### AVOID

- Do NOT confuse Eventstream with Eventhouse — they are separate Fabric workloads
- Do NOT hardcode workspace or item IDs — always discover them via the API
- Do NOT assume all source types appear in API enums — preview sources exist only in the UI
- Do NOT modify Eventstream topology with this consumption skill — use `eventstream-authoring-cli` for writes
- Do NOT attempt to query event data through the Eventstream API — use downstream skills (eventhouse-consumption-cli, sqldw-consumption-cli) for querying landed data
