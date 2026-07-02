# executeQuery — Fabric Dataflow Mashup Preview API

## What this is

Fabric Dataflow Gen2 exposes a mashup engine endpoint that evaluates a Power Query M document against a **specific dataflow's bound connections** and returns the result as an Apache Arrow IPC byte stream. There is no persistence and no refresh; this is the read-side mashup engine, suitable both for ad-hoc query execution against a saved dataflow and for previewing candidate M before persisting it via `updateDefinition`.

This file is the **canonical API reference** for `executeQuery`. End-to-end recipes (bash + PowerShell smoke tests) live in [authoring-script-templates.md](authoring-script-templates.md); Arrow → CSV / pandas conversion lives in [dataflows-consumption-cli § Query Evaluation](../../dataflows-consumption-cli/SKILL.md#query-evaluation).

---

## Vocabulary -- name the things you send

When you explain or use this API, surface the **exact** literal names below; do not paraphrase, abbreviate, or invent variants. The smoke tests and reviewers grep for these literals.

| Literal | What it is | Where it appears |
|---|---|---|
| `executeQuery` (singular) | The preview endpoint path segment. **Not** `executeQueries`, **not** `ExecuteQuery`. | URL path: `.../dataflows/{dataflowId}/executeQuery` |
| `QueryName` | Top-level request-body field naming the `shared` member to evaluate. Microsoft Learn documents this field as `queryName`; it is case-insensitive on the wire, and the repo's live-verified examples use PascalCase `QueryName`. | JSON request body |
| `customMashupDocument` | Top-level request-body field carrying the **complete** `section Section1; ...` M document being previewed. **Not** `mashupDocument`, **not** `MashupDocument`, **not** `query`, **not** base64-encoded -- it is a plain UTF-8 string. | JSON request body |
| `mashup.pq` | The saved part path inside the dataflow definition. The M body you pass as `customMashupDocument` during preview is the same body you base64-encode into the `mashup.pq` part when you persist via `updateDefinition`. | Definition `parts[].path` |
| `queryMetadata.json` | The saved part holding `connections[]`, `queriesMetadata`, and `formatVersion`. | Definition `parts[].path` |

**Preview-vs-save loop in one sentence**: build candidate M -> POST it as `customMashupDocument` to `executeQuery` -> inspect Arrow + render `head(10)` -> on success, base64-encode the same M into the `mashup.pq` part and POST to `updateDefinition`.

---

## Endpoint

```
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/dataflows/{dataflowId}/executeQuery
```

| Header | Value |
|---|---|
| `Authorization` | `Bearer <fabric-aad-token>` |
| `Content-Type` | `application/json` |
| `Accept` | `application/vnd.apache.arrow.stream` (server may also accept `application/octet-stream`) |

**Timeout budget**: 30 s+ for synchronous responses (server-side evaluation can be slow on cold cache). Long-running evaluations return `202 Accepted` with a polling URL — see [Status codes](#status-codes).

---

## Auth

- AAD/Entra access token. Audience: **Power BI** (`https://analysis.windows.net/powerbi/api`, **no** trailing slash) for `ClusterId` lookups against `api.powerbi.com/v2.0/...`; **Fabric** (`https://api.fabric.microsoft.com/`) for `executeQuery` against `api.fabric.microsoft.com/v1/...`.
- The Fabric audience is **also accepted** for `api.powerbi.com` v2 calls in current tenants — convenient when a script already holds a Fabric token — but the Power BI audience is the safe default and the only form documented to always work. If a v2 call fails with `AADSTS500011`, the token audience is wrong (or carries a trailing slash).
- Token expiry is typically 1 h. Refresh before the request if less than 5 minutes remain.
- **Required permissions**: caller must have read access to the workspace **and** the dataflow's bound connections must be accessible to the caller's identity (cloud connections) or via a configured gateway (on-prem sources).

---

## Preconditions

<a id="bootstrap-branch--new-dataflow--new-credentialed-source"></a>

1. **Dataflow exists** in the target workspace.
2. **Connections bound** — every data source referenced by the M document must have a connection bound to the dataflow via its `queryMetadata.json connections[]` array. Binding is persisted through `updateDefinition`, **not** through this endpoint; `executeQuery` cannot accept ad-hoc credentials. See [connection-management.md](connection-management.md) for the create + bind workflow.
3. **Cloud connection JSON form** — each bound cloud connection is stored as a JSON string of the form `{"ClusterId":"<guid>","DatasourceId":"<guid>"}`. `ClusterId` is obtained from Power BI v2: `GET https://api.powerbi.com/v2.0/myorg/me/gatewayClusterDatasources` (list + filter; per-id v1.0 lookups are unreliable for cloud connections — see [authoring-cli-quickref.md § ClusterId resolution](../../dataflows-authoring-cli/references/authoring-cli-quickref.md)).
4. **Multi-source / privacy firewall** — for queries that combine multiple sources, declare the section attribute `[AllowCombine = true]` at the top of the `customMashupDocument`; otherwise the privacy firewall blocks evaluation. See [M document patterns § Multi-source](#m-document-patterns).

---

## Request body

<a id="custommashupdocument-format"></a>

| Field | Type | Required | Notes |
|---|---|---|---|
| `QueryName` | string | Yes | Must name a `shared` member declared in the dataflow's persisted `mashup.pq` (when `customMashupDocument` is omitted) or in the supplied `customMashupDocument`. The wire field is case-insensitive — `queryName` is also accepted. The repo standard is **PascalCase `QueryName`**; live-verified examples use that form. |
| `customMashupDocument` | string | Optional | When omitted, the endpoint executes the persisted query identified by `QueryName`. When provided, it must be a **complete `section Section1; …` document** — see below. |

> **Anti-pattern — `{"queries":[…]}` array body shape.** Wrapping the call in an array (`{"queries":[{"queryName":"X"}]}` or `{"queries":[{"QueryName":"X"}]}`) always returns `400 DataflowExecuteQueryError: Invalid query name`, regardless of inner casing — the endpoint accepts exactly one query per call and does **not** read fields nested inside a `queries` array. Live-verified 2026-05-19.

### The auto-wrap rule (client-side)

The endpoint does **not** auto-wrap raw expressions into a section document — clients must do so. Replicate this rule when assembling the body:

```text
if customMashupDocument starts with "section " (case-insensitive):
    send as-is
else:
    send: "section Section1;\n\nshared {QueryName} = {trimmed expression};"
```

### customMashupDocument requirements

- Begins with `section Section1;` (or another section name — `Section1` is conventional).
- Every `shared` member is terminated with `;`.
- The `QueryName` request field names a `shared` member declared in the document. Mismatch returns `DataflowExecuteQueryError`.
- Non-identifier names use quoted identifiers: `shared #"Sales Query" = ...;` with `"QueryName": "Sales Query"`.
- All dependencies (parameters, helper functions, other queries) must be declared in the same document. The persisted `mashup.pq` is **not** merged in at evaluation time; the supplied document is evaluated standalone.

---

## Response

- **200 OK** — response body is a raw Apache Arrow IPC byte stream. `Content-Type: application/vnd.apache.arrow.stream`. There is no JSON envelope; do not pipe through `jq`. Capture with `--output-file` (`az rest`) or `--output`/`-OutFile` (`curl` / `Invoke-WebRequest`). The first four bytes are the IPC continuation marker `FF FF FF FF`.
- **202 Accepted** — evaluation has been accepted but is running asynchronously. Headers carry `Location` (polling URL), `x-ms-operation-id` (correlation), and `Retry-After` (seconds). Poll the `Location` until it returns a terminal `200`.
- **`PQ Arrow Metadata` column** — every response carries a trailing column named `PQ Arrow Metadata`. On success it is empty (or carries non-error metadata only); on a 200-path execution error it carries the error JSON literal. See [Error handling — A](#error-handling).

### Decoding the Arrow stream

Try `pyarrow.ipc.open_stream` first. Some Fabric responses use the Arrow **file** format rather than the stream format — fall back to `pyarrow.ipc.open_file` if the stream reader rejects the header.

```python
import io, pyarrow as pa, pyarrow.ipc as ipc

buf = io.BytesIO(response_bytes)
try:
    reader = ipc.open_stream(buf)
except pa.lib.ArrowInvalid:
    buf.seek(0)
    reader = ipc.open_file(buf)
table = reader.read_all()
```

Each Arrow column maps to a column of the evaluated M query; types are Arrow primitives (`int32`, `int64`, `string`, `timestamp`, `decimal`, …). An empty table is a valid result — it means the M evaluated to a 0-row table, not an error.

> **Showing results to the user.** Decoding into a `pyarrow.Table` is only half the validation. After the embedded-error check passes, render `head(10)` as a markdown table in chat so the human can spot silent-success bugs (filter dropped all rows, wrong column, off-by-one, wrong cast). Canonical snippet + suppression rules: [dataflows-consumption-cli § Example 5b — Render Query Results as a Markdown Table](../../dataflows-consumption-cli/SKILL.md#example-5b-render-query-results-as-a-markdown-table).

---

## Status codes

| Code | Meaning | Action |
|---|---|---|
| **200 OK** | Synchronous result; body is the Arrow IPC stream | Parse; **also inspect the `PQ Arrow Metadata` column for embedded errors** ([§ Error handling — A](#error-handling)) |
| **202 Accepted** | Asynchronous evaluation in progress | Poll the `Location` URL until terminal; honor `Retry-After` between polls; use `x-ms-operation-id` for correlation |
| **400 Bad Request** | `DataflowExecuteQueryError` — invalid/empty `QueryName`, the **`{"queries":[…]}` array body shape** (always returns `"Invalid query name"`), invalid `customMashupDocument`, or `QueryName` not found in the persisted mashup (or in the supplied document; surfaced as `QueryNotFound` inside `message`) | Fix the request body; do **not** auto-retry |
| **401 Unauthorized** | Token expired or wrong audience | Refresh the token; retry **once** |
| **403 Forbidden** | Caller lacks access to the workspace, dataflow, or one of the bound connections | Fix permissions; do **not** auto-retry |
| **404 Not Found** | Workspace or dataflow ID does not exist | Fix the IDs; do **not** auto-retry |
| **429 Too Many Requests** | Throttled by the service rate limit | Wait `Retry-After` seconds; retry |
| **500 / 503** | Transient server-side failure | Exponential backoff `1s, 2s, 4s`; max 3 retries |

Non-200 responses carry a standard Fabric `ErrorResponse` JSON envelope; the most common `errorCode` is `DataflowExecuteQueryError`.

---

## Error handling

`executeQuery` exposes **two distinct error surfaces**. Naive callers that check only the HTTP status will silently treat in-stream failures as success.

<a id="detecting-failures-inside-the-arrow-body"></a>

### A. 200 OK with embedded `PQ Arrow Metadata` error

The trailing `PQ Arrow Metadata` column is present on every response. On a 200-path execution or streaming error it carries a JSON literal of the form `{"Error":"<engine message>"}`. On success the column is empty (or carries non-error metadata only). Naive callers that check only the HTTP status will silently treat in-stream failures as success.

Verified shape:

```text
{"Error":"Request is invalid and cannot be processed: Semantic error: SEM0100: 'where' operator: Failed to resolve column or scalar expression named 'TIMESTAMP_TYPO'"}
```

Detector — bash (fast scan, fragile on schemas containing a column literally named `Error`):

```bash
if grep -q '"Error":"' result.arrow; then
  python3 - <<'PY' result.arrow
import re, sys
raw = open(sys.argv[1], "rb").read().decode("utf-8", errors="replace")
m = re.search(r'\{"Error":"[^"]+"\}', raw)
print("PREVIEW FAILED:", m.group(0) if m else "(error marker present, JSON not parsed)")
PY
  exit 1
fi
```

Detector — PowerShell:

```powershell
$raw = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes("result.arrow"))
$err = [Regex]::Match($raw, '\{"Error":"[^"]+"\}').Value
if ($err) {
    Write-Error "Preview failed: $err"
    exit 1
}
```

Detector — Python with `pyarrow` (**canonical** — inspects schema metadata instead of scanning bytes):

```python
import json, pyarrow as pa, pyarrow.ipc as ipc

with open("result.arrow", "rb") as f:
    try:
        reader = ipc.open_stream(f)
    except pa.lib.ArrowInvalid:
        f.seek(0)
        reader = ipc.open_file(f)
    md = reader.schema.metadata or {}

for v in md.values():
    s = v.decode("utf-8", errors="replace")
    if '"Error"' in s:
        try:
            msg = json.loads(s)["Error"]
        except (ValueError, KeyError):
            msg = s[:200]
        raise SystemExit(f"Preview failed: {msg}")
```

### B. Non-200 with `ErrorResponse` JSON envelope

`400 / 401 / 403 / 404 / 429 / 5xx` responses carry a JSON `ErrorResponse` body with this shape:

```json
{
  "requestId": "<guid>",
  "errorCode": "DataflowExecuteQueryError",
  "message": "ErrorCode: PqoEvaluateStreamBadRequest, ErrorDetails: InternalErrorCode: <code>, Message: {...}",
  "isRetriable": false
}
```

The top-level `errorCode` is the broad classifier; nested inside `message` is a more specific `InternalErrorCode` that pinpoints the cause. Honor `isRetriable` directly when present — it is the service's own retry directive.

Observed `InternalErrorCode` values for `DataflowExecuteQueryError`:

| `InternalErrorCode` | Wire-level cause |
|---|---|
| `RewriteDocumentFailed` / `QueryNotFound` | `QueryName` field does not name a `shared` member in `customMashupDocument` (or in the persisted `mashup.pq` when `customMashupDocument` is omitted) |
| `ReinterpretRequestFailed` | `customMashupDocument` failed to parse — missing `section` header, missing `;` terminator, or other M syntax error |
| `EvaluationError` (`Message: Evaluation result error code: TimedOut`) | Underlying source evaluation exceeded the server-side `executeQuery` budget (~90s observed for Kusto-backed queries). **Recovery**: re-issue the request with `customMashupDocument` set to the full persisted `mashup.pq` **plus** an appended probe that caps the target query — `shared __PreviewCap = Table.FirstN(<TargetQuery>, 10);` — and `QueryName: "__PreviewCap"`. The cap pushes down for most connectors and avoids materialising the unbounded source. Use this whenever a heavy persisted query needs human-visible sampling (Example 5b in dataflows-consumption-cli) but is too expensive to evaluate end-to-end. |

### Retry policy

- **Auto-retry**: `401` (after refreshing the token, max 1 retry), `429` (honor `Retry-After`), `500/503` (exponential backoff `1s, 2s, 4s`, max 3 retries).
- **Do NOT auto-retry**: `400`, `403`, `404` — these are deterministic client errors. The service signals this directly via `"isRetriable": false` in the ErrorResponse body; clients can honor that flag instead of hard-coding status-code logic.
- **202 LRO**: poll `Location` until terminal; honor `Retry-After` between polls if returned.

---

## Sequencing constraints

1. Bind connections to the dataflow via `updateDefinition` **before** calling `executeQuery`. The endpoint cannot accept ad-hoc credentials.
2. **`customMashupDocument` is the only draft / preview mode.** When supplied, the endpoint evaluates the candidate document on demand against the dataflow's bound connection context.
3. Without `customMashupDocument`, `executeQuery` runs the latest **persisted** `shared <QueryName>` member. There is no implicit draft state for saved-but-not-committed changes.
4. `executeQuery` is **read-only**. To materialize results to a destination, trigger a refresh job afterward — see [dataflows-authoring-cli SKILL.md § Refresh](../SKILL.md).

---

## Examples

### 1. Basic call — 200 OK path

**bash / curl**

```bash
TOKEN=$(az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)
WS=<workspace-guid>
DF=<dataflow-guid>

jq -n --arg q "Probe" --arg m 'section Section1;

shared Probe = Table.RowCount(#"My Query");' \
  '{QueryName: $q, customMashupDocument: $m}' > req.json

curl -sS -X POST \
  "https://api.fabric.microsoft.com/v1/workspaces/$WS/dataflows/$DF/executeQuery" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.apache.arrow.stream" \
  --data @req.json \
  --output result.arrow
```

**PowerShell**

```powershell
$token = (az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv)
$body = @{
    QueryName            = "Probe"
    customMashupDocument = "section Section1;`n`nshared Probe = Table.RowCount(#""My Query"");"
} | ConvertTo-Json
Invoke-WebRequest -Method POST `
  -Uri "https://api.fabric.microsoft.com/v1/workspaces/$WS/dataflows/$DF/executeQuery" `
  -Headers @{ Authorization = "Bearer $token"; Accept = "application/vnd.apache.arrow.stream" } `
  -ContentType "application/json" `
  -Body $body -OutFile result.arrow
```

**Python (`httpx` + `pyarrow`)**

```python
import httpx, io
import pyarrow.ipc as ipc

resp = httpx.post(
    f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/dataflows/{df}/executeQuery",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.apache.arrow.stream",
    },
    json={
        "QueryName": "Probe",
        "customMashupDocument": 'section Section1;\n\nshared Probe = Table.RowCount(#"My Query");',
    },
    timeout=120,
)
resp.raise_for_status()

buf = io.BytesIO(resp.content)
try:
    reader = ipc.open_stream(buf)
except Exception:
    buf.seek(0)
    reader = ipc.open_file(buf)
table = reader.read_all()
```

### 2. Polling a 202 LRO response

**bash / curl**

```bash
STATUS=$(curl -sS -D headers.txt -o result.arrow -w '%{http_code}' \
  -X POST "https://api.fabric.microsoft.com/v1/workspaces/$WS/dataflows/$DF/executeQuery" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/vnd.apache.arrow.stream" \
  --data @req.json)

if [ "$STATUS" = "202" ]; then
  LOC=$(grep -i '^location:' headers.txt | awk '{print $2}' | tr -d '\r')
  RETRY=$(grep -i '^retry-after:' headers.txt | awk '{print $2}' | tr -d '\r')
  while :; do
    sleep "${RETRY:-2}"
    STATUS=$(curl -sS -D headers.txt -o result.arrow -w '%{http_code}' \
      "$LOC" -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.apache.arrow.stream")
    [ "$STATUS" = "200" ] && break
    [ "$STATUS" = "202" ] || { echo "Polling failed with HTTP $STATUS"; exit 1; }
    RETRY=$(grep -i '^retry-after:' headers.txt | awk '{print $2}' | tr -d '\r')
  done
fi
```

**PowerShell**

```powershell
$resp = Invoke-WebRequest -Method POST `
  -Uri "https://api.fabric.microsoft.com/v1/workspaces/$WS/dataflows/$DF/executeQuery" `
  -Headers @{ Authorization = "Bearer $token"; Accept = "application/vnd.apache.arrow.stream" } `
  -ContentType "application/json" -Body $body -OutFile result.arrow -PassThru

if ($resp.StatusCode -eq 202) {
    $location = $resp.Headers['Location']
    $retry    = [int]($resp.Headers['Retry-After'] | Select-Object -First 1)
    while ($true) {
        Start-Sleep -Seconds ([Math]::Max($retry, 2))
        $poll = Invoke-WebRequest -Method GET -Uri $location `
            -Headers @{ Authorization = "Bearer $token"; Accept = "application/vnd.apache.arrow.stream" } `
            -OutFile result.arrow -PassThru
        if ($poll.StatusCode -eq 200) { break }
        if ($poll.StatusCode -ne 202) { throw "Polling failed with HTTP $($poll.StatusCode)" }
        $retry = [int]($poll.Headers['Retry-After'] | Select-Object -First 1)
    }
}
```

**Python**

```python
import time, httpx

url = f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/dataflows/{df}/executeQuery"
hdr = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.apache.arrow.stream"}

resp = httpx.post(url, headers=hdr, json=body, timeout=120)
while resp.status_code == 202:
    time.sleep(int(resp.headers.get("Retry-After", "2")))
    resp = httpx.get(resp.headers["Location"], headers=hdr, timeout=120)
resp.raise_for_status()
arrow_bytes = resp.content
```

### 3. Detecting `PQ Arrow Metadata` errors on a 200 response

See [§ Error handling — A](#error-handling) for the three detector snippets (bash, PowerShell, and Python). The Python `pyarrow` schema-metadata inspector is the **canonical** path — the bash `grep` detector is fast but fragile on schemas containing a column literally named `Error`, and the PowerShell regex detector loads the entire file into memory.

---

## M document patterns

<a id="hard-avoid-unbounded-production-volume-preview"></a>

### Probe a connection

```m
section Section1;
shared Probe = Lakehouse.Contents(null);
```

### Count rows of an existing query

```m
section Section1;
shared RowCount = Table.RowCount(#"My Query");
```

### First page of a remote source (capped)

```m
section Section1;
shared Sample =
    let
        S = Sql.Database("server", "db"),
        T = S{[Schema="dbo", Item="Orders"]}[Data],
        F = Table.FirstN(T, 100)
    in
        F;
```

> `executeQuery` returns the **full** evaluated dataset, not a sample. For high-volume sources, cap with `Table.FirstN`, predicate-push with `Value.NativeQuery(... "SELECT TOP N ...")`, or filter by a date predicate. Strip the cap before persisting the production mashup via `updateDefinition`.

### Multi-source (privacy firewall)

```m
[AllowCombine = true]
section Section1;
shared Joined =
    let
        A = Sql.Database("srv-a", "db-a"){[Schema="dbo", Item="Customers"]}[Data],
        B = Sql.Database("srv-b", "db-b"){[Schema="dbo", Item="Orders"]}[Data],
        J = Table.NestedJoin(A, "Id", B, "CustomerId", "B", JoinKind.LeftOuter)
    in
        J;
```

---

## Common error codes

| Surface | Code / message | Likely cause | Fix |
|---|---|---|---|
| `ErrorResponse` 400 | `DataflowExecuteQueryError` + `InternalErrorCode: RewriteDocumentFailed` / `Code: QueryNotFound` | `QueryName` field does not match a `shared` member in `customMashupDocument` (or in the persisted `mashup.pq` if `customMashupDocument` is omitted) | Match exactly; use quoted identifiers (`shared #"Sales Query" = ...;` ↔ `"QueryName": "Sales Query"`) |
| `ErrorResponse` 400 | `DataflowExecuteQueryError` + `InternalErrorCode: ReinterpretRequestFailed` (often with nested `SyntaxError[(row,col)-...]`) | Missing `section Section1;` header, missing `;` terminator, or a referenced helper / parameter is not included in the document | Validate locally; ensure the document is self-contained — declare all parameters and helper functions in the same section |
| `ErrorResponse` 403 | Access denied | Caller lacks Contributor on the dataflow, or a bound connection is not shared with the caller | Confirm role assignment; verify connection sharing |
| 200 + embedded `{"Error":"Credentials are required to connect to the <source> source"}` | Connection not bound to the dataflow at evaluation time, or the bound `connectionId` is invalid | Bind the connection via `updateDefinition` first ([Preconditions § 2](#preconditions)); verify `connectionId` resolves via `GET /v1/connections` |
| 200 + embedded `{"Error":"Timeout..."}` | Unbounded evaluation against a high-volume source | Cap with `Table.FirstN`, push a `TOP N` predicate via `Value.NativeQuery`, or add a date filter |

---

## Preview-Driven Authoring Loop

<a id="preview-driven-authoring-loop"></a>

When the change touches Power Query M (new query, edited mashup, new source, changed parameters), preview the candidate `customMashupDocument` against the dataflow's bound connections **before** persisting. Catches syntax, schema, and credential errors at authoring time.

> **Intent split.** This workflow is for the *pre-save* intent. To execute a **saved** query (`QueryName` only) or run an **ad-hoc read-only** `customMashupDocument` with no intent to persist, use [`dataflows-consumption-cli`](../../dataflows-consumption-cli/SKILL.md#query-evaluation).

### Minimal ordered steps

1. **Locate or create the dataflow shell** — `POST /v1/workspaces/{ws}/dataflows` with `{"displayName":"…"}` (SKILL.md Workflow A step 4).
2. **Ensure connections are bound** — for new credentialed sources, do a minimal `updateDefinition` with `queryMetadata.json connections[]` first (the "bootstrap save"). A `connections[]` array declared only in the initial create payload is **not** yet visible to `executeQuery`. See [Bootstrap branch](#bootstrap-branch--new-dataflow--new-credentialed-source).
3. **Compose the candidate `customMashupDocument`** as a complete `section Section1; ...` document. The request's `QueryName` (top-level, PascalCase) must match a `shared` member in the document. See [customMashupDocument format](#custommashupdocument-format).
4. **Preview** — `POST /v1/workspaces/{ws}/dataflows/{df}/executeQuery` with body `{"QueryName": "<name>", "customMashupDocument": "<section>"}`. Pass `--output-file results.arrow` — `az rest` writes the raw Apache Arrow IPC stream to disk. Arrow → CSV/pandas: [dataflows-consumption-cli § Query Evaluation](../../dataflows-consumption-cli/SKILL.md#query-evaluation).
5. **Validate the preview (two-tier — both required before persisting):**
   - **a. Embedded-error check.** HTTP 200 is **not** proof of success; engine errors are embedded inside the stream as `{"Error":"..."}`. Quick scan: `grep -q '"Error":"' results.arrow`. Canonical pyarrow detector inspects schema metadata — see [§ Error handling — A](#detecting-failures-inside-the-arrow-body).
   - **b. Render `head(10)` as a markdown table to the user.** The embedded-error check only catches engine-level failures (column not found, cast errors, SEM0100, etc.). It does **not** catch *silent-success* bugs: filter dropped all rows, wrong column referenced, wrong join key, off-by-one filter, wrong cast producing epoch dates. The 10-row visual lets the human verify shape, row count, and value sanity in seconds. Snippet + suppression rules: [dataflows-consumption-cli § Example 5b](../../dataflows-consumption-cli/SKILL.md#example-5b-render-query-results-as-a-markdown-table).
   - **c. Probe for per-cell errors.** An errored cell serializes as an Arrow **null** — indistinguishable from a genuine null in the head(10) view. To disambiguate, wrap the cell in `try` and read the `[HasError]` field: `try <step>{N}[Col]` returns `[HasError = true, Error = [...]]` for an errored cell vs `[HasError = false, Value = ...]` otherwise; filter with `Table.SelectRows(<step>, each not (try [Col])[HasError])`. Detail: [m-language.md § Per-cell errors](../references/m-language.md#per-cell-errors-in-column-transformations).
6. **Persist via `updateDefinition`** — strip any preview-only `Table.FirstN` / `TOP N` / test-mode parameters from the saved mashup. Verify `queryMetadata.json connections[]` survived the full-replacement write before triggering refresh.

Skip the preview only for metadata-only edits (display name, schedule, `loadEnabled` toggle) or when the agent records an explicit skip reason (bootstrap, prohibitive cost, side-effecting source).

### ASCII chart preview (optional)

After the two-tier validation passes, optionally render the preview data as ASCII charts for visual validation:

- **Line chart** (time-series data): `references/charts/line_chart.py`
- **Horizontal bar chart** (categorical data): `references/charts/bar_chart.py`

Ask the user if they want chart visualizations before proceeding. If accepted, call `executeQuery` for each entity, parse the Arrow IPC stream, render the appropriate chart type, and ask the user to confirm before the final `updateDefinition`. Both chart scripts are pure Python 3 (no dependencies). For parameters and display guidelines, see [chart-visualization.md](../../dataflows-consumption-cli/references/chart-visualization.md).

---

## Related references

- [connection-management.md](connection-management.md) — create and bind connections (Preconditions step 2)
- [common/DATAFLOWS-AUTHORING-CORE.md § Power Query M Code Structure](../../../common/DATAFLOWS-AUTHORING-CORE.md#power-query-m-code-structure) — section documents, multi-query patterns, parameter declarations
- [dataflows-authoring-cli SKILL.md](../SKILL.md) — authoring workflow rules (when to preview, bootstrap-binding, hard-avoid for unbounded preview)
- [dataflows-consumption-cli SKILL.md § Query Evaluation](../../dataflows-consumption-cli/SKILL.md#query-evaluation) — Arrow → pandas, CSV conversion, custom-M variant
- [authoring-script-templates.md](authoring-script-templates.md) — end-to-end smoke test, executable PowerShell variant
