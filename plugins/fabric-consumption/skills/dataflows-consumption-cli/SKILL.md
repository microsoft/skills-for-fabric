---
name: dataflows-consumption-cli
description: >
  Monitor, inspect, and query saved Fabric Dataflows Gen2 via read-only CLI.
  List dataflows, decode base64 definitions (mashup.pq, queryMetadata.json,
  .platform), discover parameters, retrieve refresh status and job history,
  classify queries by staging, and execute queries against saved dataflows via
  the read-side `executeQuery` mashup engine (Arrow IPC response). Runs
  persisted or ad-hoc read-only executeQuery requests; parses/renders Arrow
  results. For previewing
  candidate M before persisting, or for `supportedConnectionTypes`/`credentialType`
  discovery and connection configuration, use `dataflows-authoring-cli`
  (not this skill).
  Triggers: "list dataflows", "inspect dataflow", "decode dataflow definition",
  "dataflow parameters", "dataflow refresh status", "refresh history",
  "last refresh status", "dataflow job history", "execute dataflow query",
  "executeQuery saved query", "executeQuery fetch rows", "ad-hoc dataflow query",
  "parse Arrow response", "Arrow IPC", "dataflow staging analysis".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find a dataflow by name: list all dataflows in the workspace and filter by `displayName` client-side — there is no server-side name filter
> 3. `getDefinition` is a **POST**, not GET — even though it reads data

> **SCOPE BOUNDARY — READ-ONLY (mandatory)**
> This skill is **strictly read-only**. You **must never** create, update, or delete
> a dataflow or its definition — that means **no** `Delete Dataflow`, **no**
> `Create Dataflow`, **no** `updateDefinition`, and **no** other mutating/destructive
> call (e.g. `az rest --method delete/put/patch` against a dataflow, or a POST that
> creates/overwrites). The only permitted POSTs are the explicitly read-side
> `getDefinition` and `executeQuery` operations documented below.
> If the user asks to delete, create, modify, or persist a dataflow, **refuse the
> mutation** and route them to `dataflows-authoring-cli` — do not run the destructive
> command, even if the user provides the exact API call.

# dataflows-consumption-cli — Dataflows Gen2 Consumption via CLI

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) ||
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) ||
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; read before any auth issue |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Includes pagination, LRO polling, and rate-limiting patterns |
| Job Execution | [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution) ||
| Gotchas, Best Practices & Troubleshooting | [COMMON-CORE.md § Gotchas, Best Practices & Troubleshooting](../../common/COMMON-CORE.md#gotchas-best-practices--troubleshooting) ||
| Tool Selection Rationale | [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) ||
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource`**; includes pagination and LRO helpers |
| Job Execution (CLI) | [COMMON-CLI.md § Job Execution](../../common/COMMON-CLI.md#job-execution) ||
| Gotchas & Troubleshooting (CLI-Specific) | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | `az rest` audience, shell escaping, token expiry |
| Quick Reference | [COMMON-CLI.md § Quick Reference](../../common/COMMON-CLI.md#quick-reference) | `az rest` template + token audience/tool matrix |
| Consumption Capability Matrix | [DATAFLOWS-CONSUMPTION-CORE.md § Consumption Capability Matrix](../../common/DATAFLOWS-CONSUMPTION-CORE.md#consumption-capability-matrix) | **Read first** — shows what ops are available |
| REST API Surface (Consumption) | [DATAFLOWS-CONSUMPTION-CORE.md § REST API Surface](../../common/DATAFLOWS-CONSUMPTION-CORE.md#rest-api-surface-consumption) | List, Get, Parameters, getDefinition, Jobs |
| Dataflow Definition Exploration | [DATAFLOWS-CONSUMPTION-CORE.md § Dataflow Definition Exploration](../../common/DATAFLOWS-CONSUMPTION-CORE.md#dataflow-definition-exploration) | Decode mashup.pq, queryMetadata.json, .platform |
| Parameter Discovery and Analysis | [DATAFLOWS-CONSUMPTION-CORE.md § Parameter Discovery and Analysis](../../common/DATAFLOWS-CONSUMPTION-CORE.md#parameter-discovery-and-analysis) | Types, formats, M code patterns |
| Refresh and Job Monitoring | [DATAFLOWS-CONSUMPTION-CORE.md § Refresh and Job Monitoring](../../common/DATAFLOWS-CONSUMPTION-CORE.md#refresh-and-job-monitoring) | LRO pattern, job instances, polling best practices |
| Agentic Exploration Pattern | [DATAFLOWS-CONSUMPTION-CORE.md § Agentic Exploration Pattern](../../common/DATAFLOWS-CONSUMPTION-CORE.md#agentic-exploration-pattern-chat-with-my-dataflows) | 6-step discovery sequence |
| Security and Permissions Model | [DATAFLOWS-CONSUMPTION-CORE.md § Security and Permissions Model](../../common/DATAFLOWS-CONSUMPTION-CORE.md#security-and-permissions-model) | Permission matrix by operation |
| Common Errors | [DATAFLOWS-CONSUMPTION-CORE.md § Common Errors](../../common/DATAFLOWS-CONSUMPTION-CORE.md#common-errors) | Error codes and resolutions |
| Gotchas and Troubleshooting Reference | [DATAFLOWS-CONSUMPTION-CORE.md § Gotchas and Troubleshooting](../../common/DATAFLOWS-CONSUMPTION-CORE.md#gotchas-and-troubleshooting-reference) | 12 numbered issues with cause + resolution |
| Quick Reference One-Liners | [consumption-cli-quickref.md](references/consumption-cli-quickref.md) | `az rest` one-liners for all consumption ops |
| Discovery Patterns | [discovery-queries.md](references/discovery-queries.md) | Definition decoding, parameter extraction, connection analysis |
| Script Templates | [script-templates.md](references/script-templates.md) | Copy-paste bash and PowerShell templates |
| Preview Data Visualization | [chart-visualization.md](references/chart-visualization.md) | Render `executeQuery` results as ASCII line/bar/pie charts (dependency-free) |
| Tool Stack | [SKILL.md § Tool Stack](#tool-stack) ||
| Connection | [SKILL.md § Connection](#connection) ||
| Agentic Exploration ("Chat With My Dataflows") | [SKILL.md § Agentic Exploration](#agentic-exploration-chat-with-my-dataflows) | **Start here** for dataflow exploration |
| Query Execution | [SKILL.md § Query Evaluation](#query-evaluation) | Execute individual queries; responses are Apache Arrow binary |

---

## Tool Stack

| Tool | Role | Install |
|---|---|---|
| `az` CLI | **Primary**: Auth (`az login`), Fabric REST API via `az rest` | Pre-installed in most dev environments |
| `curl` | Alternative HTTP client for REST calls | Pre-installed |
| `jq` | Parse JSON responses, extract fields, format output | Pre-installed or trivial |
| `base64` | Decode definition parts from base64 | Built into bash; PowerShell uses `[Convert]::FromBase64String` |
| `bash`/`pwsh` | Script execution | Pre-installed |

> **Agent check** — verify before first operation:
> ```bash
> az account show >/dev/null 2>&1 || echo "RUN: az login"
> command -v jq >/dev/null 2>&1 || echo "INSTALL: apt-get install jq OR brew install jq"
> ```

---

## Connection

### Resolve Workspace ID and Dataflow ID

Per [COMMON-CLI.md](../../common/COMMON-CLI.md) Finding Workspaces and Items in Fabric:

```bash
# Find workspace ID by name
WS_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='My Workspace'].id" --output tsv)

# Find dataflow ID by name within workspace
DF_ID=$(az rest --method get \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/workspaces/$WS_ID/dataflows" \
  --query "value[?displayName=='Sales Data Pipeline'].id" --output tsv)
```

### Reusable Connection Variables

```bash
# Set once at script top
WS_ID="<workspaceId>"
DF_ID="<dataflowId>"
API="https://api.fabric.microsoft.com/v1"
AZ="az rest --resource https://api.fabric.microsoft.com"
```

---

## Agentic Exploration ("Chat With My Dataflows")

### Discovery Sequence

Run these in order to fully explore a workspace's dataflows. See [references/discovery-queries.md](references/discovery-queries.md) for extended patterns.

```bash
# 1. List workspaces → find target
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces" --query "value[].{name:displayName, id:id}" -o table

# 2. List dataflows → enumerate all
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows" \
  --query "value[].{name:displayName, id:id, desc:description}" -o table

# 3. Get dataflow properties
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID"

# 4. Discover parameters
#    Note: the /parameters endpoint returns DataflowNotParametricError (an HTTP 4xx)
#    for a non-parametric dataflow (no Power Query parameters). Treat that as
#    "this dataflow has no parameters" and report it plainly — do NOT surface the
#    raw error. Optionally confirm by checking mashup.pq for `IsParameterQuery`.
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/parameters" \
  --query "value[].{name:name, type:type, required:isRequired, default:defaultValue}" -o table

# 5. Get definition → decode mashup.pq
RESPONSE=$(az rest --method post --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/getDefinition")
echo "$RESPONSE" | jq -r '.definition.parts[] | select(.path=="mashup.pq") | .payload' | base64 --decode

# 6. Check job history
az rest --method get --resource "https://api.fabric.microsoft.com" \
  --url "$API/workspaces/$WS_ID/dataflows/$DF_ID/jobs/instances" \
  --query "value[].{status:status, type:invokeType, start:startTimeUtc, end:endTimeUtc, error:failureReason}" -o table
```

### Agentic Workflow

1. **Discover** → Run Steps 1–3 to list and identify dataflows.
2. **Parameters** → Step 4 to understand inputs and defaults.
3. **Definition** → Step 5 to inspect M queries, connections, staging config.
4. **Monitor** → Step 6 for refresh history and error patterns.
5. **Iterate** → Drill into specific queries or connection details.
6. **Present** → Summarize findings or generate a reusable script (see [script-templates.md](references/script-templates.md)).

---

## Gotchas, Rules, Troubleshooting

For full platform gotchas: [DATAFLOWS-CONSUMPTION-CORE.md](../../common/DATAFLOWS-CONSUMPTION-CORE.md) Gotchas and Troubleshooting Reference and [COMMON-CLI.md](../../common/COMMON-CLI.md) Gotchas & Troubleshooting (CLI-Specific).

### MUST DO

- **Always `az login` first** — `az rest` uses the active session. No session → cryptic failure.
- **Always `--resource "https://api.fabric.microsoft.com"`** — wrong audience = 401.
- **Handle pagination** — repeat requests with `continuationToken` until absent/null.
- **Handle LRO for `getDefinition`** — may return `202 Accepted` with `Location` header; poll until complete.
- **Decode base64 before inspecting** — definition parts are base64-encoded.
- **Use POST for `getDefinition`** — it is NOT a GET endpoint.

### AVOID

- **Hardcoded GUIDs** — always discover via list-then-filter pattern.
- **Assuming `getDefinition` is GET** — it is POST (common mistake).
- **Ignoring pagination** — list endpoints may return partial results.
- **Polling too aggressively** — respect `Retry-After` headers on 429s.
- **Expecting `getDefinition` with Viewer role** — requires Read+Write (Contributor+).

### PREFER

- **`az rest` over raw `curl`** — handles auth automatically.
- **List-then-filter pattern** — no server-side name filter for dataflows.
- **Exponential backoff** for job polling — 5s → 10s → 20s → 30s cap.
- **`jq` for response parsing** — cleaner than shell string manipulation.
- **JMESPath `--query`** for simple field extraction directly in `az rest`.
- **Env vars** (`WS_ID`, `DF_ID`, `API`) for script reuse.

### TROUBLESHOOTING

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token expired or wrong audience | `az login`; ensure `--resource "https://api.fabric.microsoft.com"` |
| `403 Forbidden` on `getDefinition` | Viewer role (Read-only) | Requires Contributor role or higher (Read+Write) |
| `404 Not Found` | Wrong workspace or dataflow ID | Re-discover via List Dataflows API |
| `getDefinition` returns `202` | Large definition or server load | Poll the `Location` header URL until operation completes |
| `DataflowNotParametricError` (4xx) on `/parameters` | Dataflow has no Power Query parameters (non-parametric) | Expected — report "this dataflow has no parameters"; do not surface the raw error. Optionally confirm via mashup.pq `IsParameterQuery` |
| Empty / absent `connections` array in `queryMetadata.json` | Queries use an inline/literal source (e.g. `#table()`), so there is no external connection to bind | Expected — report "no external data source connections (inline source)"; do not fabricate a binding |
| Base64 decode shows garbled text | BOM in encoded content | Strip UTF-8 BOM (`\xEF\xBB\xBF`) when decoding |
| `429 TooManyRequests` | Rate limited | Respect `Retry-After` header; implement exponential backoff |
| Duplicate results in list | Re-using stale continuationToken | Always use the token from the most recent response |
| `OperationNotSupportedForItem` | Wrong item type | Verify item is type `Dataflow` via Get Item |

---

## Examples

### Example 1: List All Dataflows in a Workspace

**Prompt**: "List all dataflows in this workspace."

**Agent response**:

```bash
az rest --method get \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/dataflows" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[].{Name:displayName, Id:id, Type:type}" -o table
```

### Example 2: Decode a Dataflow Definition

**Prompt**: "Show me the Power Query M code inside this dataflow."

**Agent response**:

```bash
# Step 1: Request definition (POST returns 202 with Location header).
# az rest cannot expose response headers, so capture Location via curl + az-acquired token.
TOKEN=$(az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv)
LOCATION=$(curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0" \
  "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/dataflows/${DF_ID}/getDefinition" \
  -o /dev/null -D - | tr -d '\r' | grep -i "^location:" | awk '{print $2}')

# Step 2: Poll until definition is ready
DEF=$(az rest --method get --url "${LOCATION}" \
  --resource "https://api.fabric.microsoft.com")

# Step 3: Decode mashup.pq to see the Power Query M code
echo "$DEF" | python3 -c "
import json, base64, sys
parts = json.load(sys.stdin)['definition']['parts']
for p in parts:
    if p['path'] == 'mashup.pq':
        print(base64.b64decode(p['payload']).decode('utf-8'))
"
```

### Example 3: Check Refresh Job History

**Prompt**: "Show me the recent refresh history for this dataflow."

**Agent response**:

```bash
# Get recent job instances for a dataflow
az rest --method get \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/dataflows/${DF_ID}/jobs/instances?limit=5" \
  --resource "https://api.fabric.microsoft.com" \
  --query "value[].{Status:status, Start:startTimeUtc, End:endTimeUtc, Id:id}" -o table
```

### Example 4: Discover Parameters from Definition

**Prompt**: "What parameters does this dataflow accept?"

**Agent response**:

```bash
# After decoding the definition (see Example 2), extract parameters:
echo "$DEF" | python3 -c "
import json, base64, sys
parts = json.load(sys.stdin)['definition']['parts']
for p in parts:
    if p['path'] == 'queryMetadata.json':
        meta = json.loads(base64.b64decode(p['payload']).decode('utf-8'))
        for qname, qmeta in meta.get('queriesMetadata', {}).items():
            if qmeta.get('queryGroupId') == 'parameters' or 'IsParameterQuery' in str(qmeta):
                print(f'Parameter: {qname}')
"
```

---

## Query Evaluation

Execute an individual query from a dataflow and inspect results. **Responses are a raw Apache Arrow IPC stream** with `Content-Type: application/vnd.apache.arrow.stream` — **not** a JSON envelope. The first four bytes of a valid stream are the IPC continuation marker `ff ff ff ff`. Parse with `pyarrow.ipc.open_stream()`.

> **Wire format**: `executeQuery` returns the raw Apache Arrow IPC byte stream (`Content-Type: application/vnd.apache.arrow.stream`) — **not JSON**. Don't try to parse it with `jq` — there is no JSON envelope to extract. Use `--output-file` to save the bytes and parse as Arrow (see Examples 5–7).

> **Failures return HTTP 200**: `executeQuery` returns `200 OK` with `application/vnd.apache.arrow.stream` even when the underlying source query fails (Kusto SEM0100, T-SQL syntax error, missing column, etc.). The error is embedded inside the stream's `PQ Arrow Metadata` section as `{"Error":"..."}` — see [dataflows-authoring-cli § mashup-preview.md → Detecting failures inside the Arrow body](../dataflows-authoring-cli/references/mashup-preview.md#detecting-failures-inside-the-arrow-body) for detector snippets. Naive HTTP-status checks will treat failures as success.

> **Intent split (canonical executeQuery reference is [mashup-preview.md](../dataflows-authoring-cli/references/mashup-preview.md))**: the same `executeQuery` endpoint serves two distinct intents. This skill covers the **consumption** intents:
> - **(a) Execute a persisted query** — body `{"QueryName":"<saved-shared>"}` only (no `customMashupDocument`).
> - **(b) Ad-hoc read-only `customMashupDocument`** — preview a candidate `section Section1; ...` document **with no intent to persist** via `updateDefinition` (Example 7).
>
> If you intend to **persist** the M, use [`dataflows-authoring-cli` § Workflow C (Preview-Driven Authoring Loop)](../dataflows-authoring-cli/SKILL.md#c-preview-driven-authoring-loop-pre-save-executequery--see-mashup-previewmd) — it adds the bootstrap-bind rule (chicken-and-egg connection binding for new credentialed dataflows), auto-wrap rule, hard-avoid for unbounded preview, and the post-preview persistence steps.

> **Auto-wrap caveat**: The Fabric REST API expects `customMashupDocument` to be a **complete `section Section1; ... shared X = ...;` document**. Raw `let ... in ...` expressions are **not** auto-wrapped server-side — send a full section document and ensure the `QueryName` request field matches a `shared` member declared inside it.

> **Body shape**: send a **flat object** with a top-level `QueryName` (field name is case-insensitive on the wire; PascalCase canonical). The `{"queries":[{...}]}` array shape always returns `400 DataflowExecuteQueryError: Invalid query name` regardless of inner casing. A wrong `QueryName` value returns `QueryNotFound` (different error code). See [dataflows-authoring-cli § mashup-preview.md → Request body](../dataflows-authoring-cli/references/mashup-preview.md#custommashupdocument-format).

> **`TimedOut` recovery for heavy persisted queries**: if the persisted `shared <Q>` member is too expensive for the server-side `executeQuery` budget (~90s observed; surfaces as `400 DataflowExecuteQueryError` → `InternalErrorCode: EvaluationError, Message: Evaluation result error code: TimedOut`), do **not** retry the same body — it is deterministic. Instead, re-issue with `customMashupDocument` set to the full persisted `mashup.pq` (decoded via Example 2) **plus** an appended probe `shared __PreviewCap = Table.FirstN(<Q>, 10);` and `QueryName: "__PreviewCap"`. The cap pushes down for most connectors (Kusto, SQL, OData, web tables) so the source returns only the sample. See [dataflows-authoring-cli § mashup-preview.md → Observed `InternalErrorCode` values](../dataflows-authoring-cli/references/mashup-preview.md#b-non-200-with-errorresponse-json-envelope).

### Prerequisites

- Dataflow must exist (verify via Example 1 above)
- Query name must exist in the dataflow (verify in mashup.pq via Example 2)
- User must have **Contributor role or higher** (read+write) on the dataflow
- **Optional**: Query parameters and custom M code modifications

### Example 5: Execute a Query and Save Results

**Prompt**: "Execute the SalesData query in this dataflow and save the results."

**Agent response**:

```bash
# Step 1: Identify the query to execute (must be a `shared` member of the dataflow's mashup)
QUERY_NAME="SalesData"  # Replace with your query name

# Step 2: Build the request body. To execute the persisted query as-is, send ONLY
#   QueryName — omit customMashupDocument. (Do NOT pass a self-referential
#   `shared X = let Source = #shared[X] in Source` — that recurses on itself
#   inside the candidate document.) For custom M, see Example 7.
jq -n --arg q "$QUERY_NAME" '{QueryName: $q}' > req.json

# Step 3: Execute the query (raw Apache Arrow IPC stream is written directly to disk)
az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/dataflows/${DF_ID}/executeQuery" \
  --resource "https://api.fabric.microsoft.com" \
  --body "@req.json" \
  --output-file "${QUERY_NAME}_results.arrow"

# Step 4: Check for embedded source errors (HTTP 200 does NOT mean success)
if grep -q '"Error":"' "${QUERY_NAME}_results.arrow"; then
  echo "Query execution failed (embedded in Arrow body):"
  python3 -c "import re,sys; raw=open(sys.argv[1],'rb').read().decode('utf-8','replace'); m=re.search(r'\\{\"Error\":\"[^\"]+\"\\}', raw); print(m.group(0) if m else '(marker present, JSON not parsed)')" "${QUERY_NAME}_results.arrow"
  exit 1
fi

echo "Query results saved to ${QUERY_NAME}_results.arrow"
```

> **Why `--output-file`?** Without it, `az rest` dumps raw bytes to stdout and prints the warning `Not a json response, outputting to stdout. For binary data suggest use "--output-file" to write to a file`. Always pass `--output-file` for `executeQuery` so the Arrow IPC stream is captured cleanly. The `jq -r '.data' | base64 --decode` pattern from earlier docs is **incorrect for `az rest`** — there is no JSON envelope to extract.

### Example 5b: Render Query Results as a Markdown Table

**Prompt**: "Show me the first 10 rows of those results."

**Agent response** — read the saved Arrow file and render `head(N)` as a markdown table in chat. **Always do this after `executeQuery`** (default `N=10`). The visual preview catches *silent-success* bugs that the embedded-error detector misses: filter dropped all rows, wrong column referenced, wrong cast, off-by-one filter, join key typo.

```bash
N=${N:-10}; ARROW_FILE="${QUERY_NAME}_results.arrow"
python3 - <<EOF
import json, sys, pyarrow as pa, pyarrow.ipc as ipc

with open("$ARROW_FILE", "rb") as f:
    try:
        reader = ipc.open_stream(f)
    except pa.lib.ArrowInvalid:
        f.seek(0); reader = ipc.open_file(f)
    # Surface any embedded engine error before rendering (mirrors mashup-preview.md § Error handling — A)
    for v in (reader.schema.metadata or {}).values():
        s = v.decode("utf-8", errors="replace")
        if '"Error"' in s:
            try:
                msg = json.loads(s)["Error"]
            except (ValueError, KeyError):
                msg = s[:200]
            sys.exit(f"Preview failed: {msg}")
    table = reader.read_all()

rows, cols = table.num_rows, table.num_columns
print(f"**{rows} rows × {cols} columns** · {', '.join(table.schema.names)}\n")
if rows == 0:
    sys.exit(0)

# Slice at the Arrow level before converting — avoids materialising the whole result.
df = table.slice(0, $N).to_pandas().copy()
# Truncate long string cells so the chat table stays readable.
for c in df.select_dtypes(include=["object", "string"]).columns:
    df[c] = df[c].astype(str).str.slice(0, 50)
try:
    print(df.to_markdown(index=False))           # requires the `tabulate` package
except ImportError:
    print(df.to_string(index=False))             # fallback: fixed-width text
EOF
```

> **Optional dep**: `pandas.DataFrame.to_markdown()` requires the `tabulate` package — install once via your environment's standard Python tooling, the same way you installed `pyarrow` / `pandas` for Example 6. If `tabulate` is absent, the snippet falls back to fixed-width `to_string()` so rendering still works.

> **When to skip rendering**: render `head(N)` by default. Skip only when (a) the user explicitly asked for the raw Arrow file with no preview, (b) the result row count exceeds ~1000 — in that case still render `head(N)` and add a one-line note about the total row count, or (c) the result is being streamed straight into another tool that will consume the Arrow file directly. In every other case, **render** — the saved file alone is not visible to the user in chat.

### Example 6: Convert Arrow Results to CSV

**Prompt**: "Convert my Arrow query results to CSV so I can open them in Excel."

**Agent response**:

> **Prerequisite (one-time client-side setup)**: This example uses `pyarrow` to decode the Arrow IPC stream and `pandas` to write CSV. Install them once via your environment's standard Python tooling. These are local client dependencies, **not** part of the Fabric recipe.

```bash
python3 <<EOF
import pyarrow as pa
import pandas as pd
import sys

ARROW_FILE = "${QUERY_NAME}_results.arrow"
CSV_FILE = "${QUERY_NAME}_results.csv"

# Open the Arrow IPC stream directly (raw on the wire, no envelope)
with open(ARROW_FILE, "rb") as f:
    reader = pa.ipc.open_stream(f)

    # Defensive: surface any error embedded in the stream's PQ Arrow Metadata
    md = reader.schema.metadata or {}
    for k, v in md.items():
        s = v.decode("utf-8", errors="replace")
        if '"Error"' in s:
            print(f"Preview failed: {s}", file=sys.stderr)
            sys.exit(1)

    table = reader.read_all()

# Convert to pandas and export as CSV
df = table.to_pandas()
df.to_csv(CSV_FILE, index=False)

print(f"Converted {len(df)} rows to CSV")
print("Columns:", list(df.columns))
EOF
```

### Example 7: Query with Custom M Code

**Prompt**: "Run a one-off ad-hoc M query against this dataflow without saving it."

> **Intent**: ad-hoc **read-only** execution. The `customMashupDocument` is **not** persisted. If you intend to save the M via `updateDefinition`, use [`dataflows-authoring-cli` § Workflow C](../dataflows-authoring-cli/SKILL.md#c-preview-driven-authoring-loop-pre-save-executequery--see-mashup-previewmd) instead — it adds bootstrap-bind, auto-wrap, and post-preview persistence rules.

**Agent response**:

```bash
# Execute a query with custom M code (e.g., filter, aggregate, transform).
# The customMashupDocument must be a complete `section` document; az rest does NOT auto-wrap raw expressions.
CUSTOM_M='section Section1;

shared CustomQuery = let
    Source = Table.FromRecords({[id=1, name="Alice"], [id=2, name="Bob"]}),
    Filtered = Table.SelectRows(Source, each [id] > 0)
in
    Filtered;'

jq -n --arg m "$CUSTOM_M" '{QueryName: "CustomQuery", customMashupDocument: $m}' > req.json

az rest --method post \
  --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/dataflows/${DF_ID}/executeQuery" \
  --resource "https://api.fabric.microsoft.com" \
  --body "@req.json" \
  --output-file custom_results.arrow

# Always check for embedded errors before treating the file as a success
if grep -q '"Error":"' custom_results.arrow; then
    echo "Custom query failed; inspect custom_results.arrow for the embedded {\"Error\":...} block."
    exit 1
fi
```

---

## Output Expectations

When this skill completes a task, the agent should return:

| Field | Convention |
|---|---|
| **Verbosity** | Concise summary (3–10 lines) for status; markdown table for list/inspect responses. |
| **Default format** | Markdown table for `list`-style queries; fenced JSON code block for single-resource responses; raw decoded `mashup.pq` in a fenced ` ```m ` block. For `executeQuery`: save the full Arrow stream to file **and** render `head(N)` (default `N=10`) as a markdown table in chat — see [Example 5b](#example-5b-render-query-results-as-a-markdown-table). Suppress rendering only on explicit user request, when `rows > 1000` (render head + total-count note), or when the result is being streamed into another tool. |
| **Side-effect disclosure** | This is a **read-only** skill — never imply mutation, and **refuse** any create/update/delete request (route to `dataflows-authoring-cli`). |
| **Verification** | Include the source URL (e.g., the `az rest --url` value) in the response so the user can reproduce the call. |
| **Error surfacing** | If `executeQuery` returns Arrow with embedded `{"Error":"..."}`, surface the error verbatim and do not present partial results as success. |
