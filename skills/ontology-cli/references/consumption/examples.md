<!-- Sub-reference for the `ontology-cli` skill, `consumption` mode. Indexed directly from `skills/ontology-cli/SKILL.md`. -->

# ontology-cli consumption — Verified calls and troubleshooting

Verified Ontology Agent MCP calls and troubleshooting. Selection rules live in the
consumption mode reference indexed from `SKILL.md`.

## Contents

| Section | Covers |
|---|---|
| [Call template](#call-template) | The shape every example below reuses |
| [Verbatim JSON replies](#verbatim-json-replies) | A machine-checked reply draft that preserves opaque identifiers |
| [0. Resolve the IDs](#0-resolve-the-ids) | Workspace-scoped listing or Catalog Search |
| [1. Discover the surface](#1-discover-the-surface) | `tools/list` and reading the result |
| [2. Ask a business question](#2-ask-a-business-question) | The core `ask_ontology` call |
| [3. Ask for runnable code](#3-ask-for-runnable-code) | `queryLanguage` plus execution target |
| [4. An unsupported V1 ontology](#4-an-unsupported-v1-ontology) | Stop before `tools/call` and request upgrade |
| [5. Inspect the schema](#5-inspect-the-schema) | `list_ontology_entities`, filtered |
| [Troubleshooting](#troubleshooting) | Verified symptoms and fixes |

---

## Call template

`WS` and `ONT` are resolved workspace/item GUIDs, never guesses. Resolve within the named
workspace; use Catalog Search only when none was supplied (see [0. Resolve the IDs](#0-resolve-the-ids)).
`APIHOST` is `https://api.fabric.microsoft.com`. Use a body file: inline questions break shell quoting.

```bash
az rest --method post \
  --url "$APIHOST/v1/mcp/dataPlane/workspaces/$WS/items/$ONT/ontologyEndpoint" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "Content-Type=application/json" "Accept=application/json, text/event-stream" \
            "x-ms-fabric-skill=ontology-cli" \
  --body "@/tmp/payload.json" 1>ont_resp.json 2>ont_err.txt
cat ont_resp.json
```

The `--resource` audience is `https://api.fabric.microsoft.com`.
Allow at least 120 seconds per `ask_ontology` call.

PowerShell: prepare an absolute UTF-8-without-BOM payload and validate it locally
before POST, following `consumption/request-files.md`, indexed in `SKILL.md`. Pass the same
quoted `"@$payloadPath"` to the CLI; recreate variables in fresh shells.

> **Do not call the variable `HOST`.** In PowerShell `$host` is a reserved automatic variable,
> the assignment fails, and the call has to be re-issued -- which bills the agent twice.

### Capturing the answer without paying twice

Each `tools/call` is billed. Save the complete first response with `1>` and read it
in the same command. Never call once for `--query result.isError` and again for content:
Keep `$payloadPath` pointing to the actual request you prepared. In a fresh shell,
recreate that request's absolute path; do not replace it with a discovery filename.

```powershell
# correct -- the answer is on disk before anything tries to display it
$null = Get-Content -LiteralPath $payloadPath -Raw -ErrorAction Stop |
  ConvertFrom-Json -ErrorAction Stop
az rest --method post --url "$APIHOST/v1/mcp/dataPlane/workspaces/$WS/items/$ONT/ontologyEndpoint" `
  --resource "https://api.fabric.microsoft.com" `
  --headers "Content-Type=application/json" "Accept=application/json, text/event-stream" `
            "x-ms-fabric-skill=ontology-cli" `
  --body "@$payloadPath" 1>ont_resp.json 2>ont_err.txt
function ConvertFrom-McpResponseText([string]$text) {
  try {
    $json = $text | ConvertFrom-Json -ErrorAction Stop
    if ($null -ne $json.id -and ($json.PSObject.Properties['result'] -or $json.PSObject.Properties['error'])) {
      return $json
    }
  } catch {}
  $events = [regex]::Split($text.Trim(), '\r?\n\r?\n')
  for ($i = $events.Count - 1; $i -ge 0; $i--) {
    $data = @(($events[$i] -split '\r?\n') |
      Where-Object { $_ -match '^data:' } |
      ForEach-Object { $_ -replace '^data:\s?', '' }) -join "`n"
    if ($data -and $data -ne '[DONE]') {
      try {
        $json = $data | ConvertFrom-Json -ErrorAction Stop
        if ($null -ne $json.id -and ($json.PSObject.Properties['result'] -or $json.PSObject.Properties['error'])) {
          return $json
        }
      } catch {}
    }
  }
  throw 'Ontology MCP response contained neither JSON nor a valid SSE data frame.'
}
$j = ConvertFrom-McpResponseText (Get-Content ont_resp.json -Raw)
if ($j.PSObject.Properties['error']) {
  throw ("Ontology MCP JSON-RPC error: " + ($j.error | ConvertTo-Json -Depth 30 -Compress))
}
"isError=" + $j.result.isError
$j.result.content | Where-Object type -eq 'text' | ForEach-Object text
```

Do not capture stdout into `$resp`, guard on it being empty, then write it:
a wrapper can lose stdout after a successful slow call. Redirect to disk first.
Recover display or projections from that file; **never re-send the body**.

For PowerShell-native HTTP, use `Invoke-WebRequest` so either JSON or SSE remains raw text; do not
redirect an `Invoke-RestMethod` object through the table formatter:

```powershell
$headers.Accept = 'application/json, text/event-stream'
$response = Invoke-WebRequest -Method Post -Uri $uri -Headers $headers -Body $body
$response.Content | Set-Content response.txt
$j = ConvertFrom-McpResponseText $response.Content
```

### Verbatim JSON replies

For an explicit raw-schema request, do not reconstruct JSON or shorten identifiers
while composing the answer. In the same PowerShell invocation that parses the saved
response into `$j`, construct and check the exact reply draft:

```powershell
function Get-VerifiedOntologyReply([string]$serviceText, [string]$draftPath) {
  if ([string]::IsNullOrWhiteSpace($serviceText)) { throw 'Saved Ontology response has no text to deliver.' }
  $draft = Get-Content -LiteralPath $draftPath -Raw -Encoding UTF8 -ErrorAction Stop
  if (-not $draft.Contains($serviceText)) {
    throw 'Reply draft changed the service text. Rebuild it from the saved response and recheck.'
  }
  return $draft
}
$serviceText = @($j.result.content | Where-Object type -eq 'text' | ForEach-Object text) -join "`n"
$draftPath = Join-Path ([IO.Path]::GetTempPath()) ('ontology-answer-' + [guid]::NewGuid().ToString('N') + '.md')
$fence = '```'
$draft = "isError=$($j.result.isError)`n`n$fence" + "json`n$serviceText`n$fence"
try {
  [IO.File]::WriteAllText($draftPath, $draft, [Text.UTF8Encoding]::new($false))
  Get-VerifiedOntologyReply -serviceText $serviceText -draftPath $draftPath
} finally {
  if (Test-Path -LiteralPath $draftPath) { Remove-Item -LiteralPath $draftPath -ErrorAction Stop }
}
```

Use that checked draft unchanged for the final chat response. Do not retype its
JSON or identifiers after checking. Recheck any edited draft; if it fails, recover
the text from the saved response, never by issuing another `tools/call`. In a new
PowerShell invocation, redefine the helpers and reparse the saved response first.
Do not silently switch to file-only delivery when the user requested the content
in chat.

---

## 0. Resolve the IDs

Choose the path that preserves the user's scope:

- **Workspace supplied:** resolve that workspace, then list its Ontology items with
  `GET {host}/v1/workspaces/{WS}/items?type=Ontology` and exact-filter the name or ID locally.
  Do not broaden to tenant-wide Catalog Search.
- **No workspace supplied:** use Catalog Search. Every hit carries `hierarchy.workspace.id`
  beside `id`, so one result provides both halves of the MCP URL. This path requires the
  `Catalog.Read.All` delegated scope.

**Inside a supplied workspace** — exact-filter the item locally:

```bash
az rest --method get \
  --url "$APIHOST/v1/workspaces/$WS/items?type=Ontology" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=ontology-cli" \
  --query "value[?displayName=='ClinicNetwork'].{name:displayName,id:id}" -o table
```

**With no workspace supplied, by name** — the user said "the ClinicNetwork ontology":

```bash
cat > /tmp/find.json << 'EOF'
{"search": "ClinicNetwork", "filter": "Type eq 'Ontology'", "pageSize": 30}
EOF
az rest --method post --url "$APIHOST/v1/catalog/search" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=ontology-cli" \
  --body @/tmp/find.json \
  --query "value[].{name:displayName, id:id, ws:hierarchy.workspace.id}" -o table
```

**By bare GUID** — drop `search` entirely and match `id` yourself. Do **not** pass the GUID as
`search`; verified on a live tenant, that returns the derived `<name>_lh_<guid>` and
`<name>_graph_<guid>` artefacts plus unrelated noise, and **not** the ontology:

```bash
cat > /tmp/all.json << 'EOF'
{"filter": "Type eq 'Ontology'", "pageSize": 100}
EOF
az rest --method post --url "$APIHOST/v1/catalog/search" \
  --resource "https://api.fabric.microsoft.com" \
  --headers "x-ms-fabric-skill=ontology-cli" \
  --body @/tmp/all.json \
  --query "value[?id=='$ONT'].hierarchy.workspace.id | [0]" -o tsv
```

If the result is empty and `continuationToken` is non-empty, repeat with that token before
concluding the ontology is absent — but cap the walk at three pages and then ask for the
workspace instead.

### Verified `search` behaviour

`search` matches **case-insensitive word prefixes across name and description** — it is neither
an exact match nor typo-tolerant. The behaviour below was measured on a live tenant; the names
are illustrative, standing in for two ontologies called `ClinicNetwork` and `ClinicOperations`:

| Query | Hits | Why it matters |
|---|---|---|
| `Clinic`, `clinic`, `CLINIC` | 2 | case-insensitive |
| `Clin`, `Cli` | 2 | a prefix is enough — the user need not type the full name |
| `nic` | 0 | prefix, not substring |
| `Operati` | 4 | camel-case names are tokenised |
| `Clinnic` | 0 | no fuzzy matching; a typo finds nothing |
| `Operations` | 6 | matched half the tenant, several only via **description** |
| `radiology` | 1 | description-only match |

So more than one hit is the normal case. Show `displayName`, workspace and `id`, and let the
user choose; picking the first silently will eventually answer from the wrong ontology.

---

## 1. Discover the surface

```bash
cat > /tmp/payload.json <<'JSON'
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
JSON
```

Add `--query "result.tools[].name"` to the template to see just the names:

```json
["search_ontology", "ask_ontology", "list_ontology_rules", "list_ontology_entities"]
```

`ask_ontology` is present, so this is a supported new-experience (V2) Ontology and the rest of the
session may use it. If `ask_ontology` is absent, stop before `tools/call`.

---

## 2. Ask a business question

**User:** "Using the ClinicOperations ontology, how many clinics are there?"

```bash
cat > /tmp/payload.json <<'JSON'
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"ask_ontology","arguments":{"request":"How many clinics are there?"}}}
JSON
```

Response:

```json
{ "jsonrpc": "2.0", "id": 2,
  "result": {
    "_meta": { "conversationId": "8b319d38-6472-4bd8-8351-80959687c0d3" },
    "content": [ { "type": "text", "text": "There are **5 clinics**." } ],
    "isError": false } }
```

**Answer to the user:** There are **5 clinics** in the ClinicOperations ontology.

Note what is *not* here: no definition fetch, no base64 decode, no hand-written SQL, no delegation
to a sibling skill. One discovery call and one question.

---

## 3. Ask for runnable code

`queryLanguage` accepts KQL, SQL, DAX, Python, the ontology DSL, or Ontology/Eventhouse-runnable
KQL that joins KQL, SQL and DAX sources. Name it and the execution target inside `request`:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call",
 "params":{"name":"ask_ontology","arguments":{"request":
   "Generate runnable code that returns the number of appointments per practitioner. queryLanguage: KQL. Execution target: Eventhouse."}}}
```

The returned text is KQL grounded in the ontology's real bindings — a concrete connection string
and real table and column names, not placeholders. Present it to the user; hand execution to
`eventhouse-cli` only if they ask for it. This call is slower than a plain question.

---

## 4. An unsupported V1 ontology

When `tools/list` omits `ask_ontology` — for example, it returns only
`["list_ontology_entity_types", "search_ontology"]` — stop before `tools/call`. Do not use
`search_ontology` as a fallback.

Tell the user:

> Natural-language queries in `ontology-cli` support only new-experience (V2) Ontologies. This
> Ontology uses the earlier V1 experience, so I did not run the query. Upgrade or recreate it in
> the new Ontology experience, then try again.

---

## 5. Inspect the schema

Only when the user actually asked a schema question. Filter whenever you can — the unfiltered
form returned roughly 44,000 characters for a 13-entity ontology.

```json
{"jsonrpc":"2.0","id":5,"method":"tools/call",
 "params":{"name":"list_ontology_entities","arguments":{"entityName":"Appointment"}}}
```

`result.content[0].text` parses to:

```jsonc
{ "values": [ { "name": "Appointment", "lineageTag": "...", "keyProperties": [ ... ],
                "backingTable": { ... }, "additionalBackingTables": [ ... ],
                "properties": [ ... ], "synonyms": [ ... ], "annotations": [ ... ],
                "resourceLinks": [ ... ] } ] }
```

---

## 6. A follow-up question

Every `tools/call` is independent -- the server keeps no conversation, so a follow-up that
relies on the previous turn will be answered without that context. Fold the carried-over facts
into the new request:

| The user says | Send |
|---|---|
| "Of those 5, which is busiest?" | "Among the 5 clinics in this ontology, which one records the most appointments?" |
| "Now break that down by month" | "Break the 47 cancelled appointments in this ontology down by month." |

Keep `result._meta.conversationId` in your notes; it identifies the call in a support ticket even
though it cannot be replayed.

---

## Version gating, as observed

`tools/list` against two ontologies in the same workspace returns different sets:

```text
V2 ontology -> search_ontology, ask_ontology, list_ontology_rules, list_ontology_entities
V1 ontology -> list_ontology_entity_types, search_ontology
```

Only the first surface is supported for natural-language consumption. The V1 list is shown solely
so the client can recognize and reject it; do not call `search_ontology`.

Calling a gated tool anyway returns **HTTP 200** carrying:

```json
{ "result": { "content": [{ "type": "text",
  "text": "Tool 'ask_ontology' is not supported for this ontology artifact version." }],
  "isError": true } }
```

---

## Phrasing the request

`request` is the only input, so the whole question has to live in that one string.

| User said | Weak request | Strong request |
|---|---|---|
| "how many clinics" | `clinics` | `How many clinics are there?` |
| "cancellations last month" | `cancellations` | `How many appointments were cancelled during the previous calendar month, broken down by clinic, highest first?` |
| "busiest rooms" | `rooms` | `Which treatment rooms handled the most appointments? Return room, site and appointment count.` |
| "departments per site" | `departments by site` | `For each site, return the site ID, the site name and the number of departments.` |

The last row matters more than it looks: site names repeat, so a request that groups by
name merges distinct sites into one row. Ask for the identifier whenever the question says
"for each".

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Catalog Search by GUID returns `<name>_lh_<guid>` / `<name>_graph_<guid>` but not the ontology | The GUID was passed as `search`, which matches names, not IDs | Drop `search`, filter on `Type eq 'Ontology'`, and compare `id` locally |
| Catalog Search returns nothing for an ontology you know exists | Wrong tenant or identity, wrong host, missing access, or (rarely) the 24 h indexing lag | Check `az account show` against the tenant that owns the item before scanning wider; a bigger scan cannot fix an identity or environment mismatch |
| The bare-GUID scan keeps paging and never matches | `filter`-only walks every ontology in the tenant; large tenants run to hundreds | Stop after ~3 pages per host and ask for the workspace ID. Do not switch to workspace enumeration — it is more expensive, not less |
| Catalog Search returns many unrelated ontologies | `search` also matches the description, so common words are broad | Narrow the term, or show the hits and ask the user which one |
| `result.isError: true`, text `Tool 'ask_ontology' is not supported for this ontology artifact version.` | The ontology is V1 (feature level 1) | Stop; explain that only new-experience (V2) Ontologies support natural-language consumption and request upgrade/recreation |
| `tools/list` omits `ask_ontology` | The item is V1 or otherwise not on the supported new experience | Stop before `tools/call`; do not fall back to `search_ontology` |
| HTTP 404 with `The entity could not be found` | The route resolved but the workspace or ontology ID is wrong for this host, or you lack access | Re-resolve both IDs within the original requested scope on the **same host**; check item access |
| HTTP 404 with `The requested resource could not be found` | A legacy route alias was used, or the host does not match the environment | Use `/v1/mcp/dataPlane/workspaces/{ws}/items/{id}/ontologyEndpoint`, and confirm the host matches the environment the IDs came from |
| HTTP 401 | Not signed in, or wrong token audience | `az login`; confirm `--resource "https://api.fabric.microsoft.com"` |
| Service-principal token fails | Ontology MCP currently does not support service principals | Sign in interactively with `az login`; do not retry the service-principal token |
| HTTP 403 | The signed-in identity lacks read access to the ontology item | Ask for a role assignment on the item or the workspace |
| JSON-RPC `error` instead of `result` | Bad tool name, missing required argument, or a request outside 3-10000 characters | Re-read `tools/list` for the exact name and schema, then fix the argument |
| Shell reports an unterminated string, or the body arrives mangled | Inline `--body` with a quoted question | Write the payload to a file and use `--body @file.json` |
| The call hangs, then the client gives up | Normal agent latency exceeded the client timeout | Raise the timeout to 120 s or more. Do not retry blindly — narrow the question instead |
| The answer says an entity or property was not found | The wording did not resolve against the ontology model | Call the schema tool once, show the user the real entity names, and re-ask with corrected vocabulary |
| A schema tool response looks like an opaque string | The JSON payload is nested inside `content[0].text` | Parse `content[0].text` as JSON, then read `values[]` |
| The answer is vague or averages across everything | The request omitted scope, filters or a time range | Re-ask with one focused question that names the entity, the filter and the period |
