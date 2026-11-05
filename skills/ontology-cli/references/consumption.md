<!-- Mode reference for the `ontology-cli` skill. Loaded on demand from `skills/ontology-cli/SKILL.md` when the request matches the `consumption` mode. -->

> **CRITICAL NOTES**
> 1. Fabric IQ Ontology is **preview**. The item type value is `Ontology`. Wire format, tool names and feature gating may change; validate against the current docs before production use.
> 2. This mode is **read-only** and answers questions **only** through the Ontology Agent MCP server. It never decodes an item definition and never composes KQL / T-SQL / Spark SQL itself. Going around the MCP layer loses the agent's grounding **and** its metered-consumption accounting.
> 3. Natural-language consumption supports **only new-experience (V2) Ontologies**. **Always call `tools/list` before `tools/call`** and continue only when `ask_ontology` is present. If it is absent, report that V1 natural-language queries are unsupported and the Ontology must be upgraded or recreated in the new experience. Do not call `search_ontology`.
> 4. A tool failure arrives as **HTTP 200** with `result.isError: true`. Check that field; HTTP status alone will not tell you the call failed.
> 5. To find the workspace details (including its ID) from workspace name: list all workspaces and use JMESPath filtering.
> 6. To find the ontology item ID from workspace ID and item name: list all items of type `Ontology` in that workspace and use JMESPath filtering.
> 7. Every call to a `*.fabric.microsoft.com` host — including the MCP `tools/list` and `tools/call` — must carry `x-ms-fabric-skill: ontology-cli`.

# ontology-cli consumption mode — Natural-language questions via the Ontology Agent MCP

## Contents

| Section | Covers |
|---|---|
| [Why the MCP layer](#why-the-mcp-layer) | What this mode does, and what it refuses to do |
| [Endpoint](#endpoint) | URL shapes, host, auth, JSON-RPC envelope |
| [Tool Catalog](#tool-catalog) | Tool names, schemas, version gating, selection tree |
| [Workflow](#workflow) | Resolve, discover, ask, present |
| [Writing a Good request](#writing-a-good-request) | The single biggest quality lever |
| [Code Generation](#code-generation) | `queryLanguage` plus an execution target |
| [Response Contract](#response-contract) | `isError`, `conversationId`, latency budget |
| [Must / Prefer / Avoid](#must--prefer--avoid) | Decision rules |

Shared prerequisites — `az login`, the `az rest` template, CLI escaping — are indexed in this
skill's `SKILL.md` under **Shared essentials**. One of them is not optional here:
**COMMON-CLI.md § Finding Workspaces and Items in Fabric** is **mandatory** before you resolve
any ID — load it from the `SKILL.md` index, then follow [Workflow](#workflow) step 1. Verified
calls and the troubleshooting table live in the `consumption/examples.md` reference.

---

## Why the MCP layer

The Ontology Agent MCP server is the **supported and metered** query path. It grounds business terms, composes, executes and validates queries across bound sources, and returns answers with evidence.

This mode answers business questions, returns grounded runnable code, and inspects entities and rules — all through the tools in the [Tool Catalog](#tool-catalog). Creating, altering or rebinding an ontology belongs to the `authoring` mode.

> **Do not bypass MCP.** Never decode definitions, map physical columns, or hand off source queries to sibling skills. That loses grounding, validation and metered accounting. If `ask_ontology` cannot answer, report the failure and stop.

---

## Endpoint

The MCP server is **item-scoped**: one instance per ontology, addressed by workspace ID and ontology item ID. There is no "which ontology" tool parameter — the URL *is* the scope.

### URL shape

```text
POST {host}/v1/mcp/dataPlane/workspaces/{workspaceId}/items/{ontologyItemId}/ontologyEndpoint
```

Use this data-plane form in Fabric production. Do not substitute legacy route aliases.

The two 404 texts mean different things — `consumption/examples.md` has the full table.

### Host

Use `https://api.fabric.microsoft.com`. Resolve workspace and ontology IDs through that same
host. If Catalog Search does not find the ontology, verify the signed-in tenant and identity,
then ask for the workspace ID rather than probing alternate hosts.

### Auth

Use delegated user authentication: `az login`, then `az rest --resource "https://api.fabric.microsoft.com"`. The caller needs read access to the ontology item. Due to a [documented preview limitation](https://learn.microsoft.com/fabric/iq/ontology/how-to-use-ontology-mcp-server), Ontology MCP access does **not** currently support service principals; stop and request an interactive user sign-in instead of retrying a service-principal token.

### JSON-RPC envelope

The endpoint speaks JSON-RPC 2.0 over a single `POST`: `tools/list` to discover, then `tools/call`
carrying `params.name` and `params.arguments`. Send `Content-Type: application/json` and
`Accept: application/json, text/event-stream`. Handle either a raw JSON response or the final
JSON-RPC response carried by an SSE `data:` frame. Ignore progress notifications,
including those after the response; recover the answer from the saved file rather than
repeating the call. The exact payloads for each tool are in
`consumption/examples.md`.

**Always pass the body with `--body @file.json`, never inline.** Business questions contain quotes, apostrophes and commas that break under shell escaping — this is the most common self-inflicted failure in this mode.

**PowerShell: write, validate, and POST the same absolute file.** Recreate variables in fresh shells; follow `consumption/request-files.md`, indexed in `SKILL.md`.

---

## Tool Catalog

These names and schemas are verified against a live V2 ontology. Treat this table as a guide to *interpreting* `tools/list`, not as a substitute for calling it.

| Tool | Arguments | Available on | Purpose |
|---|---|---|---|
| `ask_ontology` | `request` (string, **required**, 3-10000 chars) | **V2 only** | Answers a business question over the ontology and its bound data, or returns grounded, validated, runnable code. **This is the tool for natural-language questions.** |
| `list_ontology_entities` | `entityName` (string, optional, exact match) | **V2 only** | Entities with properties, keys, backing tables, synonyms and annotations. |
| `list_ontology_rules` | `entityNames` (array of string, optional, 1-100 items) | **V2 only** | Business rule definitions, including the natural-language statement and referenced entities. |

### V2 support gate

The presence of `ask_ontology` is the support check. If `tools/list` omits it, the Ontology is not
on the supported new experience. Stop before `tools/call`, tell the user that V1 natural-language
queries are unsupported, and ask them to upgrade or recreate the Ontology in the new experience.
Do not try `search_ontology`, even if the server advertises it.

### Tool selection

```text
tools/list
   |- ask_ontology absent?             -> stop; report V1 unsupported and request upgrade/recreation
   |- explicit entity/schema request?  -> list_ontology_entities with a targeted entityName when possible
   |- explicit business-rules request? -> list_ontology_rules with targeted entityNames when possible
   |- otherwise                        -> ask_ontology for business questions and code generation
```

Do **not** call a `list_*` tool as a warm-up before `ask_ontology`. The agent does its own grounding, and the listing is large — a 13-entity ontology returned roughly 44,000 characters. Call a `list_*` tool only when the user actually asked a schema question, or when `ask_ontology` reported that it could not find an entity and you need to show the user what does exist.

---

## Workflow

1. **Resolve scope.** You need a workspace ID and an ontology item ID on a host that serves both. Follow **COMMON-CLI.md § Finding Workspaces and Items in Fabric** (indexed in `SKILL.md`): when the user supplied a workspace, resolve that workspace and list/filter its Ontology items; use Catalog Search only when no workspace was specified.

   | You were given | Call | Cost |
   |---|---|---|
   | Workspace ID **and** ontology ID | nothing — use them as given | 0 |
   | Workspace ID + ontology name | `GET {host}/v1/workspaces/{ws}/items?type=Ontology`, then exact-filter locally | 1 |
   | Workspace name + ontology name | `GET {host}/v1/workspaces`, exact-filter workspace, then `GET .../items?type=Ontology` and exact-filter item | 2 |
   | No workspace + ontology name/partial name | `POST {host}/v1/catalog/search` with `{"search":"<name>","filter":"Type eq 'Ontology'"}` | 1 |
   | No workspace + bare ontology GUID | Catalog Search with `{"filter":"Type eq 'Ontology'","pageSize":100}`, then match `id` locally | 1 per 100 ontologies **in the whole tenant** |

   Every Catalog Search hit carries `hierarchy.workspace.id` beside `id`, so a no-workspace search yields both halves of the MCP URL.

   - **Never put a GUID in `search`.** It matches artefacts *named* after the ontology (`<name>_lh_<guid>`) and misses the ontology itself. Filter by type and compare `id` yourself.
   - **`search` is a case-insensitive word-prefix match over name *and* description** — not exact, not typo-tolerant. Multiple hits are normal; list them and ask which one. Never silently take the first.
   - **Cap the bare-GUID scan at 3 pages.** Pages 2+ send only `continuationToken`; repeating `filter` fails. If unmatched, **stop and ask for the workspace ID**.
   - **Not found is rarely an indexing problem.** Most often you are signed in to the wrong **tenant or identity**. Name the suspect and ask; a wider scan fixes neither. When a workspace was specified, do not broaden to tenant-wide Catalog Search. Catalog Search can lag up to 24 h for a brand-new item.
2. **Discover tools.** `tools/list` against the item's MCP URL. One call per ontology per session — cache the result; the surface does not change mid-session.
3. **Pick the tool** using the decision tree above.
4. **Compose the request** — see the next section. This is where answer quality is won or lost.
5. **Call** `tools/call` with `--body "@file.json"` and allow a **generous timeout**. Capture mistakes can cost another billed call:
   - **For text-producing clients (`az rest`, `curl`), redirect the response to a file with `1>`, then read that file back in the same command.** For `Invoke-RestMethod`, never use `1>` on the returned object: PowerShell's formatter destroys nested `content[]` as `System.Object[]`. Assign the response object and serialize it in the same process: `$response = Invoke-RestMethod ...; $response | ConvertTo-Json -Depth 30 | Set-Content response.json`.
   - Save the **complete response before any `--query` or field projection**. Read both `isError` and content from that file, never with separate service calls.
   - Do not branch on captured `az rest` stdout being empty; read the saved response file instead.
   - **Never name a shell variable `$host`.** It is a reserved PowerShell automatic variable, the assignment fails, and you will re-run the whole call. Use `$apiHost`.
6. **Check `result.isError`** before reading the text.
7. **Present the complete result in the final message**, even if printed earlier. Lead with the finding in the user's vocabulary, bold key numbers, and use tables for rows. If too large, give the total, show as many rows as reasonably possible, and state the shown/omitted counts. Hide unrequested transport and cleanup details. For unsupported V1, state the new-experience requirement and upgrade/recreation action without narrating the plumbing.

   **An explicit verbatim request overrides summaries/tables.** Copy the saved
   `result.content[].text` into a reply draft programmatically, machine-check it, then
   deliver that draft unchanged in chat. Do not re-author its JSON afterward or
   silently switch to file-only delivery. See `consumption/examples.md`, "Verbatim JSON replies".

### Multi-turn questions

`ask_ontology` has **no** conversation parameter: each call is independent. Restate follow-up context in `request`; `result._meta.conversationId` cannot be passed back. See `consumption/examples.md`.

---

## Writing a Good request

`request` is the only input. Everything the agent needs has to be in that one string. A vague request is the number-one cause of a weak answer.

Include, when the user implied them:

- **The metric or object** asked for, in business language ("number of overdue appointments", not "count of rows").
- **Scope and filters** — entity, location, status, category.
- **Time range**, stated absolutely or relatively ("in the last 30 days", "for calendar year 2025").
- **Grouping and ordering** ("per department, highest first"). When the user says "for each X", group by X's **identifier** — prefer the ID when the entity has one — and ask for that ID in the output. Display names repeat: two departments in different sites can both be called `Radiology`, and grouping on the name silently merges them into one row.
- **Desired output** — a number, a table of rows, a short explanation, or runnable code.

Keep the user's domain vocabulary. The ontology exists so that business terms resolve; translating "practitioners" into a guessed table name works against the agent. Weak and strong phrasings of the same question are in `consumption/examples.md`.

Constraints: 3 to 10000 characters. **One question per call** — a compound request produces a blurred answer and costs the same as two clean ones.

---

## Code Generation

`ask_ontology` generates grounded, validated, runnable code when `request` names `queryLanguage` and an **execution target**. This is slower than a plain answer and uses real connection details, not placeholder tables.

**Show the generated code to the user and let them decide whether to run it.** Executing it belongs to the owning endpoint skill — `eventhouse-cli`, `sqldw-cli`, `spark-cli` or `semantic-model-authoring`. Never auto-execute generated code that writes.

Supported languages and a worked request are in the `consumption/examples.md` reference.

---

## Response Contract

Success:

```json
{ "jsonrpc": "2.0", "id": 2,
  "result": {
    "_meta": { "conversationId": "8b319d38-6472-4bd8-8351-80959687c0d3" },
    "content": [ { "type": "text", "text": "There are **5 clinics**." } ],
    "isError": false } }
```

- The answer is `result.content[]`, filtered to the single `type: "text"` entry. Schema tools return JSON in that text: parse a copy for analysis; keep the original string for verbatim delivery.
- `result.isError: true` means the tool failed, even though HTTP said 200.
- A JSON-RPC-level `error` object instead of `result` means the request itself was rejected — bad tool name, bad arguments, unknown method.
- Responses are capped at roughly 512 KB.

### Latency — plan for it

These calls run a real agent conversation and are **slow**: measured 34-77 s for a simple aggregate on a live ontology, longer for code generation. Budget at least 120 s and raise your client timeout. Asynchronous task polling is not yet plumbed through the public gateway, so use the plain synchronous `tools/call` today.

**Never re-send a request you have already paid for.** Every `tools/call` opens a fresh agent conversation and is billed again. That includes re-sending the same body file just to reformat or re-extract the output: if you want a different view of the answer, read the response you already captured. On a timeout, tell the user the call exceeded the budget and ask whether to narrow the question — a retry may also still be racing the first call.

---

## Must / Prefer / Avoid

### Must

- **Require explicit ontology context.** Route here only when the prompt names an ontology, by name or item ID, or is clearly a follow-up in an ontology session. A bare "Fabric IQ" or a Power BI report / semantic-model question is **not** an ontology task — `fabriciq` owns those.
- **Call `tools/list` before the first `tools/call`** on an ontology, and pick from what it actually returned.
- **Resolve IDs within the requested scope**, per COMMON-CLI: list/filter inside a user-specified workspace, and use Catalog Search only when no workspace was specified. Never invent a GUID or broaden a scoped request tenant-wide.
- **Use absolute, locally validated UTF-8-without-BOM payload files.** Write and parse the same path, then use quoted `--body "@$payloadPath"`; never use a relative .NET writer after changing directories.
- **Check `result.isError`** before you trust the text.
- **Carry the telemetry header** `x-ms-fabric-skill: ontology-cli` on every call, `tools/list` included.
- **Report the real answer.** Run the call and report what came back; describing what the tool would do is not an answer.
- **Machine-check verbatim reply drafts against the saved text.** Recheck any edit; never retype or abbreviate identifiers, including `lineageTag`, after checking.
- **Reject unsupported Ontologies clearly.** If `ask_ontology` is absent, say that natural-language consumption supports only new-experience (V2) Ontologies and ask the user to upgrade or recreate the item **outside this legacy V1 authoring flow**. Do not call another ontology tool.
- **Say so when you cannot answer.** If the tool is gated or the agent returns an error, state that plainly instead of substituting a hand-built query. When you *did* answer, do not explain which path served it.

### Prefer

- **`ask_ontology` for supported business questions and code generation**; use the targeted `list_ontology_entities` or `list_ontology_rules` tool for explicit schema or rule requests after the V2 support gate passes.
- **One rich, self-contained request** over several thin ones.
- **The user's domain vocabulary** inside the request.
- **Caching the `tools/list` result** for the life of the session.
- **A targeted `entityName` or `entityNames` filter** when you genuinely need a schema listing — the unfiltered form is large.

### Avoid

- **Decoding the ontology item definition to hand-compose a query.** It loses grounding and validation, and it does not meter. There is no approved fallback to `eventhouse-cli`, `sqldw-cli` or `spark-cli` for ontology data questions.
- **Calling a `list_*` tool as a routine prelude** to `ask_ontology`.
- **Re-sending a request you already paid for** — to reformat the output, or blindly after a timeout or an `isError` response.
- **Calling `search_ontology` as a V1 fallback.** V1 natural-language queries are unsupported.
- **Blind retries** after a timeout or an `isError` response.
- **Auto-running generated code**, especially anything that writes.
- **Compound, multi-part questions** in one request.
- **Mutating the ontology from this mode** — that is the `authoring` mode.
- **Unrequested transport details** — host, tool names, workspace/item GUIDs. Keep identifiers intact inside explicitly requested raw payloads.
- **Answering by reference** — "the table above", "as shown earlier". The final message has to carry the result itself, in full.
- **Narrating the plumbing** in the final message — which host, which tool served it, or which temp files you removed. Give the answer instead. For unsupported V1 items, give only the user-relevant new-experience requirement and upgrade/recreation action.
