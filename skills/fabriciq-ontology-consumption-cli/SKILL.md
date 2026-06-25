---
name: fabriciq-ontology-consumption-cli
description: >
  Explore Fabric IQ Ontology (preview) items (read-only) from the CLI to ground an agent before it
  queries data. Explore, describe, and summarize what an ontology exposes — its entity types, keys,
  relationships, and the bindings that map each concept onto a lakehouse or Eventhouse source — then
  route the underlying data query to the matching per-datasource consumption skill
  (eventhouse-consumption-cli, spark-consumption-cli, sqldw-consumption-cli). Read-only discovery via
  Get Item Definition; never writes to or alters an ontology. Use to explore or summarize an ontology,
  describe its schema and data lineage, build agent grounding context, or run an ontology-backed
  query over the source records.
  Triggers: "query fabric ontology", "explore fabric ontology", "list ontology entities",
  "enumerate ontology entity types", "describe ontology", "ontology grounding context",
  "ground query with ontology", "query ontology entity data", "fabric iq ontology consumption",
  "ontology-backed query", "ontology entity bindings"
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare against remote via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If remote is newer, show the changelog and update instructions.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. Ontology is **preview**. The item type value is `Ontology`. Wire format and limitations may change; validate against the current docs before production use.
> 2. This skill is **read-only**. It never calls `createItem` or `updateDefinition`. For schema changes, delegate to **`fabriciq-ontology-authoring-cli`**.
> 3. This skill does **not** query source data directly. It enumerates ontology grounding context, then **delegates** the actual data read to the per-datasource consumption skill that matches the binding source kind (see [Query Routing](#query-routing)).
> 4. Projections (a semantic query layer over ontology entities) are **not yet GA**. Until they ship, all data queries run against the **source** table (`LakehouseTable` or `KustoTable`) using the columns declared in the binding's `propertyBindings[]`.
> 5. To find the workspace details (including its ID) from workspace name: list all workspaces and use JMESPath filtering.
> 6. To find the ontology item ID from workspace ID and item name: list all items of type `Ontology` in that workspace and use JMESPath filtering.

# fabriciq-ontology-consumption-cli — Fabric Ontology Consumption via CLI

## Table of Contents

| Task                                             | Reference                                                                                                                    | Notes                                                             |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Finding Workspaces and Items in Fabric           | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric)  | **Mandatory** — resolve workspace/item IDs before enumerating     |
| Fabric Topology & Key Concepts                   | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts)                 | Workspace → Item hierarchy                                        |
| Authentication & Token Acquisition               | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition)         | Use `https://api.fabric.microsoft.com` audience for control plane |
| Core Control-Plane REST APIs                     | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis)                    | Get Item Definition                                               |
| Long-Running Operations (LRO)                    | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro)                    | `getDefinition` returns an LRO                                    |
| Rate Limiting & Throttling                       | [COMMON-CORE.md § Rate Limiting & Throttling](../../common/COMMON-CORE.md#rate-limiting--throttling)                         |                                                                   |
| Authentication Recipes                           | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes)                                  | `az login`; token acquisition                                     |
| Fabric Control-Plane API via `az rest`           | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest)      | **Always** pass `--resource https://api.fabric.microsoft.com`     |
| Long-Running Operations (LRO) Pattern            | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern)      | Poll `operations/{x-ms-operation-id}` until `Succeeded`          |
| Gotchas & Troubleshooting (CLI-Specific)         | [COMMON-CLI.md § Gotchas & Troubleshooting (CLI-Specific)](../../common/COMMON-CLI.md#gotchas--troubleshooting-cli-specific) | Token audience, shell escaping                                    |
| Definition Envelope (parts, payloadType)         | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope)                  | `InlineBase64` parts pattern — the ontology returns this shape    |
| Ontology Definition Tree                         | [ONTOLOGY-AUTHORING-CORE.md § Definition Tree](../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#definition-tree)                      | Authoritative file/folder layout of parts you will decode         |
| EntityType & EntityTypeProperty schema           | [ONTOLOGY-AUTHORING-CORE.md § EntityType file](../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#entitytype-file--entitytypesiddefinitionjson) | `valueType` catalog, key / display-name contracts                 |
| DataBinding schema + source-type mapping         | [ONTOLOGY-AUTHORING-CORE.md § DataBinding file](../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#databinding-file--entitytypesiddatabindingsguidjson) | `LakehouseTable` vs `KustoTable`; `propertyBindings[]` shape       |
| RelationshipType + Contextualization             | [ONTOLOGY-AUTHORING-CORE.md § RelationshipType file](../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#relationshiptype-file--relationshiptypesiddefinitionjson) | Source/target + linking-table contract                            |
| Connection Fundamentals (EH source queries)      | [EVENTHOUSE-CONSUMPTION-CORE.md § Connection Fundamentals](../../common/EVENTHOUSE-CONSUMPTION-CORE.md#connection-fundamentals) | Cluster URI + DB discovery for `KustoTable` bindings              |
| Performance Best Practices (EH source queries)   | [EVENTHOUSE-CONSUMPTION-CORE.md § Performance Best Practices](../../common/EVENTHOUSE-CONSUMPTION-CORE.md#performance-best-practices) | Time filters, `has` vs `contains`                                 |
| Spark consumption patterns (Lakehouse sources)   | [SPARK-CONSUMPTION-CORE.md](../../common/SPARK-CONSUMPTION-CORE.md)                                                          | For `LakehouseTable` bindings, delegate read                      |
| SQL consumption patterns (SQL endpoint / DW)     | [SQLDW-CONSUMPTION-CORE.md](../../common/SQLDW-CONSUMPTION-CORE.md)                                                          | For `LakehouseTable` SQL-endpoint reads and Warehouse reads       |
| Ontology Concepts                                | [SKILL.md § Ontology Consumption Concepts](#ontology-consumption-concepts)                                                   | Entity / relationship / binding / grounding context               |
| Tool Stack                                       | [SKILL.md § Tool Stack](#tool-stack)                                                                                         |                                                                   |
| Connection                                       | [SKILL.md § Connection](#connection)                                                                                         | Discover workspace, ontology ID; Get Item Definition              |
| Consumption Scope                                | [SKILL.md § Consumption Scope](#consumption-scope)                                                                           | What this skill does / does not do                                |
| Grounding Context Extraction (deep reference)    | [grounding-extraction.md](references/grounding-extraction.md)                                                                | Decode parts → grounding JSON for agents                          |
| Query Routing (deep reference)                   | [routing.md](references/routing.md)                                                                                          | Binding kind → per-datasource skill + query shape                 |
| Worked Examples                                  | [examples.md](references/examples.md)                                                                                        | End-to-end bash recipes (enumerate → route → query)               |
| Graph Walks (N-hop neighborhood from anchor)     | [graph-walks.md](references/graph-walks.md)                                                                                  | Anchor entity + hop budget → composed inline reads, no scripts    |
| Snappy-Response Discipline                       | [SKILL.md § Snappy-Response Discipline](#snappy-response-discipline)                                                         | Inline-first; script only when stateful or re-runnable            |
| Must / Prefer / Avoid / Troubleshooting          | [SKILL.md § Must / Prefer / Avoid / Troubleshooting](#must--prefer--avoid--troubleshooting)                                  | LLM decision rules                                                |
| Agentic Workflows                                | [SKILL.md § Agentic Workflows](#agentic-workflows)                                                                           | Ground-then-query loop, schema-aware query generation             |
| Agent Integration Notes                          | [SKILL.md § Agent Integration Notes](#agent-integration-notes)                                                               | How this skill composes with authoring / per-datasource skills    |

---

## Ontology Consumption Concepts

A Fabric Ontology item carries its schema as a **tree of JSON files** inside the item definition (same shape as authoring). `Get Item Definition` returns the parts as base64-encoded payloads; the consumption flow is always: **fetch → decode → parse → ground → delegate**.

| Concept | Definition part | What it tells an agent |
|---|---|---|
| Entity type | `EntityTypes/{entityTypeId}/definition.json` | Logical type name, key properties (`entityIdParts`), display-name property, static `properties[]`, `timeseriesProperties[]`, value-type catalog |
| Data binding | `EntityTypes/{entityTypeId}/DataBindings/{guid}.json` | Which physical table backs this entity type, the source kind (`LakehouseTable` / `KustoTable`), `dataBindingType` (`NonTimeSeries` / `TimeSeries`), column-to-property map, and — for timeseries — the timestamp column |
| Relationship type | `RelationshipTypes/{relTypeId}/definition.json` | Link between two entity types (source/target); name; cardinality hints |
| Contextualization | `RelationshipTypes/{relTypeId}/Contextualizations/{guid}.json` | Which Lakehouse linking table holds the (source key, target key) pairs to realize the relationship |

**Grounding context** = the flattened, agent-ready projection of that tree: a JSON summary an LLM can read to decide *which entity type to query*, *which column holds the key*, *which table to hit*, and *which consumption skill to invoke*. Full shape + extraction recipe: [grounding-extraction.md](references/grounding-extraction.md).

Property `valueType` allowed values (exact): `String`, `Boolean`, `DateTime`, `Object`, `BigInt`, `Double`. Integers are `BigInt` (not `Int64`); GUIDs are modelled as `String`. See [ONTOLOGY-AUTHORING-CORE.md § EntityTypeProperty](../fabriciq-ontology-authoring-cli/references/ONTOLOGY-AUTHORING-CORE.md#entitytypeproperty) for the full source-column → `valueType` mapping.

---

## Tool Stack

Ontology consumption uses the same Fabric control-plane tool stack as every other CLI skill — see [COMMON-CLI.md § Tool Selection Rationale](../../common/COMMON-CLI.md#tool-selection-rationale) for the canonical list (install commands, prerequisite checks, base64 helpers, JSON tooling) and [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) for `az login` + token acquisition.

Per-datasource reads are delegated — you do **not** need the Kusto, Spark, or SQL CLI tools installed to use this skill for enumeration. They are only needed if you also invoke the downstream consumption skill in the same session.

---

## Connection

Ontology consumption targets the Fabric control plane. You need the **workspace ID** and the **ontology item ID**; everything else (entity types, bindings, source tables, cluster URIs) is recovered by decoding the definition.

- Sign in + acquire the Fabric control-plane token → [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) (always `--resource https://api.fabric.microsoft.com`).
- Resolve workspace ID by `displayName` and the ontology item ID via `GET /v1/workspaces/{WS_ID}/items?type=Ontology` filtered by `displayName` → [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) (covers pagination + JMESPath filtering).
- Generic `az rest` invocation template → [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest).

### Fetching the definition (Ontology-preview LRO gotcha)

`Get Item Definition` is Long-Running-Operation-capable. Depending on tenant/SKU, the POST may return the definition envelope inline (`200 OK`) **or** return `202 Accepted` with an `x-ms-operation-id` header; for the 202 case, poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` until `Succeeded`, then GET `…/operations/{operationId}/result` to receive the `parts[]` array. The generic LRO recipe (capture `x-ms-operation-id`, poll, fetch result) is in [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern).

> **Ontology-preview gotcha — prefer polling the `operations/{id}` endpoint over the `Location` header.** The public Fabric LRO contract supports either, but on this Ontology LRO the `Location` header has been observed redirecting to an `*.analysis.windows.net` host; polling it with a Fabric-audience token is flaky (intermittent `401/403`). Poll `https://api.fabric.microsoft.com/v1/operations/{operationId}` on the Fabric host instead. If you must follow `Location`, use the audience required by that URL. If a poll ever returns a non-2xx, **read the operation `.error` and stop — never blind-retry the POST**.

The full fetch-and-decode flow for this skill (LRO capture + part decode + tree reconstruction, Bash + PowerShell + Python helpers) lives in [grounding-extraction.md § Fetch and Decode](references/grounding-extraction.md#fetch-and-decode-an-ontology-definition). The sibling `fabriciq-ontology-authoring-cli` documents the same redirect-host workaround in its [LRO Header Capture section](../fabriciq-ontology-authoring-cli/SKILL.md#lro-header-capture-with-az-rest) — keep the two in sync if you change one.

### Source-data connections (delegated)

Running the data query itself (KQL / Spark SQL / T-SQL) uses the connection patterns owned by the sibling consumption skills:

- **Eventhouse** (`KustoTable` bindings) → [EVENTHOUSE-CONSUMPTION-CORE.md § Connection Fundamentals](../../common/EVENTHOUSE-CONSUMPTION-CORE.md#connection-fundamentals) + `eventhouse-consumption-cli`
- **Lakehouse** (`LakehouseTable` bindings) → `sqldw-consumption-cli` (default, SQL analytics endpoint) or `spark-consumption-cli` (only when user explicitly wants PySpark / DataFrame work)
- **Warehouse bindings** → ❓ not documented in the current shared ontology schema (`LakehouseTable` and `KustoTable` only); if encountered, surface to user rather than silently assuming `sqldw-consumption-cli`

The `clusterUri`, `databaseName`, `workspaceId`, and `itemId` your delegate needs are all already inside the decoded binding payload — do **not** rediscover them via the item APIs.

---

## Consumption Scope

| Operation | This skill | Delegate to |
|---|---|---|
| Enumerate entity types, properties, keys, display names | ✅ | — |
| Enumerate bindings (source kind, target item, property map, timestamp) | ✅ | — |
| Enumerate relationships and contextualizations | ✅ | — |
| Produce an LLM-facing grounding JSON | ✅ | — |
| Decode the full definition tree for diff / review | ✅ | — |
| Query ontology-backed **data** in an Eventhouse | Route | `eventhouse-consumption-cli` |
| Query ontology-backed **data** in a Lakehouse via SQL endpoint (default) | Route | `sqldw-consumption-cli` |
| Query ontology-backed **data** in a Lakehouse via Spark (explicit Spark ask only) | Route | `spark-consumption-cli` |
| Query ontology-backed **data** in a Warehouse | Surface (❓ binding shape not in shared schema) | — |
| Create / alter / rebind entity types / relationships | ❌ | `fabriciq-ontology-authoring-cli` |
| Refresh an ontology's indexed state | ❌ | Not in preview CLI scope |

> Until projections ship, all data reads are **source queries** — they run against the physical `LakehouseTable` or `KustoTable` using the columns listed in `propertyBindings[]`. Semantic features (inferred joins, derived measures) that require projections are **not available** from this skill; flag them to the user and proceed with source-level filtering.

---

## Grounding Context

Deep recipe + full JSON shape: [grounding-extraction.md](references/grounding-extraction.md). Quick index:

| Topic | Reference |
|---|---|
| Fetch + LRO + decode parts | [grounding-extraction.md § Fetch and Decode](references/grounding-extraction.md#fetch-and-decode-an-ontology-definition) |
| Reconstruct the definition tree in memory | [grounding-extraction.md § Tree Reconstruction](references/grounding-extraction.md#tree-reconstruction) |
| Produce a grounding JSON summary (entities + bindings + relationships) | [grounding-extraction.md § Grounding Summary Schema](references/grounding-extraction.md#grounding-summary-schema) |
| Diff two ontology versions | [grounding-extraction.md § Diff Two Ontologies](references/grounding-extraction.md#diff-two-ontologies) |

**Grounding JSON contract** — the authoritative shape lives in [grounding-extraction.md § Grounding Summary Schema](references/grounding-extraction.md#grounding-summary-schema). Routing decisions read these fields per binding:

- `source.kind` (`LakehouseTable` | `KustoTable`) — picks the delegate family.
- `source.workspaceId` + `source.itemId` — **read from the binding, not the ontology** (cross-workspace bindings are legal).
- `source.sourceSchema` + `source.sourceTableName` — Lakehouse-only has schema.
- `source.clusterUri` + `source.databaseName` — Kusto-only.
- `dataBindingType` (`NonTimeSeries` | `TimeSeries`) + `timestampColumnName` — required for TS routing.
- `propertyBindings[].sourceColumnName` — the ontology-property → physical-column remap; applied before any query is composed.
- `relationshipTypes[].contextualizations[].sourceKeyRefBindings[]` / `targetKeyRefBindings[]` — **arrays**; composite keys are legal. Join on **all** entries.

Hand a trimmed subset of this JSON (not the raw base64 `definition.parts[]`) to downstream skills.

---

## Query Routing

Deep recipe + per-skill invocation templates: [routing.md](references/routing.md). Quick decision table:

| Binding source kind | `dataBindingType` | Delegate (default / alternate) | Query shape |
|---|---|---|---|
| `LakehouseTable` | `NonTimeSeries` | `sqldw-consumption-cli` (default, SQL endpoint) — `spark-consumption-cli` only when user explicitly wants PySpark / DataFrames | `SELECT <propertyColumns> FROM <schema>.<sourceTableName> WHERE <keyColumn> = <value>` |
| `LakehouseTable` | `TimeSeries` | `sqldw-consumption-cli` (default) — `spark-consumption-cli` for Spark-only features | `SELECT ..., <timestampColumn> FROM <schema>.<sourceTableName> WHERE <keyColumn> = <v> AND <timestampColumn> >= DATEADD(hour,-1,SYSUTCDATETIME())` |
| `KustoTable` | `TimeSeries` | `eventhouse-consumption-cli` | `<sourceTableName> \| where <keyColumn> == "<v>" \| where <timestampColumn> > ago(1h) \| project <propertyColumns>` |
| `KustoTable` | `NonTimeSeries` | **Invalid** — preview forbids this | Reject and tell the user the ontology is mis-bound |
| Any relationship contextualization | — | `sqldw-consumption-cli` (default; linking tables are Lakehouse, joins cleaner in T-SQL) — `spark-consumption-cli` alternate | `SELECT <targetKeyColumns> FROM <linkTable> WHERE <sourceKeyColumns> = <source-values>` then join target-side bindings in a follow-up call |

**Invocation contract when handing off** — this skill resolves the source metadata and **composes the query in the target dialect**, then hands both to the delegate. The delegate (sibling skill) owns the actual connection + execution.

- **Eventhouse delegate** → resolved connection (`clusterUri`, `databaseName`) + **composed KQL text** targeting `sourceTableName` with `timestampColumnName` filter + key predicate.
- **SQL endpoint delegate** (default for Lakehouse) → resolved connection (`workspaceId`, `itemId`, `sourceSchema`) + **composed T-SQL text**.
- **Spark delegate** (alternate for Lakehouse) → same resolved connection + **composed Spark SQL text** — use Spark-native time functions (`current_timestamp() - INTERVAL 1 HOUR`); do **not** emit T-SQL `DATEADD` / `SYSUTCDATETIME` to Spark.
- **Always** translate ontology property names → `propertyBindings[].sourceColumnName` inside the composed query text. The delegate sees only physical columns and will not resolve ontology identifiers.
- **Always** pass composite `sourceKeyRefBindings[]` / `targetKeyRefBindings[]` — join on **every** element, not just the first.

> Because projections are not yet GA (see Critical Note #4), always translate the **ontology property names** the user mentions back into **physical source column names** (via `propertyBindings[]`) before composing the delegate query. Do not pass ontology property names to the sibling skill — it will not resolve them.

---

## Must / Prefer / Avoid / Troubleshooting

### Must

- **Require explicit ontology context before routing here** — the prompt must mention an "ontology" (or reference an ontology item by ID/name). Generic "Fabric IQ" or report/dataset prompts without ontology context are **not** ontology tasks; defer those to the matching data skill (e.g. `powerbi-consumption-cli` for Power BI reports). This keeps the shared "Fabric IQ" brand from over-triggering this skill.
- **Clarify before routing ambiguous prompts** — if the user asks "show me aircraft readings" and multiple entity types bind to aircraft-like tables, ask which entity type / binding to use. Silent guessing produces wrong data.
- **Resolve `WS_ID` and `ONT_ID` before fetching the definition** — hardcoded GUIDs are a top failure mode.
- **Follow the LRO pattern on `getDefinition`** — a `202` with `x-ms-operation-id` is normal; do not treat it as success. Poll `operations/{operationId}` until `Succeeded`, then GET `…/operations/{operationId}/result`. Prefer `operations/{operationId}` over raw `Location` polling (analysis.windows.net redirect can be flaky with a Fabric-audience token); if you follow `Location`, use the audience required by that URL. On a Failed/non-2xx poll, read `.error` and stop — never blind-retry.
- **Decode every relevant part before answering** — never respond from a cached partial view of the ontology. The caller may have added / altered entity types since you last read.
- **Translate ontology property names → source column names via `propertyBindings[]`** before generating any KQL / Spark SQL / T-SQL. The sibling consumption skills see only physical columns.
- **Respect the binding type** — `TimeSeries` requires a time filter on `timestampColumnName`. Omitting it is a full scan and often rejected by the downstream skill.
- **Preserve `workspaceId` + `itemId` per binding** — ontology bindings can reference source items in **different workspaces** from the ontology itself; do not assume collocation.
- **Consult the in-memory grounding before issuing metadata calls** — once the grounding JSON is decoded for the session, every subsequent walk / query reads source-column names, linking-table names, item GUIDs, `clusterUri`, and `databaseName` **from grounding**, not from a fresh `list items` / `get eventhouse` round trip. Re-fetching metadata you already have is the #1 cause of bloated call counts.
- **Use GUIDs, not friendly names, in source URLs** — many tenants run with `FriendlyNameSupportDisabled`, which silently rejects names like `MyLakehouse.Lakehouse` in OneLake DFS / Fabric REST URLs. Always pull the GUID from grounding and substitute it into the URL.

### Prefer

- **`az rest` with `--body @file.json`** for any downstream KQL / SQL payload that contains `|`, `"`, or newlines. Inline `--body` breaks under shell escaping — see [EVENTHOUSE-CONSUMPTION-CORE.md](../../common/EVENTHOUSE-CONSUMPTION-CORE.md).
- **Grounding summary JSON** (see schema above) over raw `definition.json` dumps when handing context to another agent.
- **`take 100` / `TOP 100`** on first read of any entity's data, then refine.
- **Inline `az rest` / `curl` over Python scripts** for read-only consumption work — graph walks, single-entity lookups, and ad-hoc fan-out reads should compose ≤ ~15 REST calls in the shell. Reach for a script only when the work is **stateful** (envelope assembly, ID maps, LROs that the user wants re-runnable). See [Snappy-Response Discipline](#snappy-response-discipline) and [graph-walks.md](references/graph-walks.md).
- **Cache the decoded definition for the life of one session** — the ontology definition is orders of magnitude smaller than the source data and rarely changes mid-task. Refetch if the user mentions authoring activity.
- **`project` / `SELECT` only the bound source columns**, not the full physical table — ontology bindings imply an explicit column whitelist.

### Avoid

- **Querying the source table using ontology property names** — those do not exist in the physical schema. Always go through `propertyBindings[]`.
- **Dropping `where <timestampColumn> > ago(...)`** on `TimeSeries` / `KustoTable` reads — full scans on streaming tables are the #1 query failure.
- **Joining across datasource kinds in one delegate call** — if a relationship's two sides live in different source kinds, the delegate cannot express the join. Fetch both sides separately and join in the agent.
- **Mutating the ontology** from this skill — route all schema changes to `fabriciq-ontology-authoring-cli`.
- **Passing raw base64 parts to downstream skills / models** — always decode and reshape into a grounding JSON first.
- **Silently ignoring unknown part paths** — a new preview release may add part kinds; log-and-continue is fine but surface the new part name to the user.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `az rest` returns `401 Unauthorized` | `az login`; confirm `--resource "https://api.fabric.microsoft.com"` on the control-plane call (and the matching downstream audience when delegating — `https://kusto.kusto.windows.net` for EH). |
| `getDefinition` returns 202 with no body | Expected — follow the LRO pattern; capture `x-ms-operation-id` and poll `operations/{operationId}` until `Succeeded`, then GET `…/operations/{operationId}/result`. Prefer `operations/{operationId}`; if polling `Location`, use the audience required by that URL (analysis.windows.net redirects can fail with a Fabric-audience token). |
| `403 Forbidden` on `getDefinition` | Ontology requires **Contributor** or **Reader on the ontology item** plus workspace access. Ask for role assignment. |
| `definition.parts[]` is empty | The item was created but no entity types were added. Tell the user and suggest running `fabriciq-ontology-authoring-cli` first. |
| Downstream KQL returns 0 rows but source table has data | Check the binding's `sourceTableName` casing and that `clusterUri` / `databaseName` in the binding match the live cluster. Casing mismatches cause silent empty results. |
| `SELECT <propertyName>` fails with "invalid column" | You passed an ontology property name, not a source column name. Remap via `propertyBindings[].sourceColumnName`. |
| Relationship traversal returns unexpectedly few rows | Contextualization's `sourceTableName` (Lakehouse linking table) may be empty or stale; inspect via `sqldw-consumption-cli` before blaming the ontology. |
| Mismatched `itemId` / `clusterUri` between binding and live Eventhouse | The backing Eventhouse was recreated; the ontology needs an authoring update. Hand off to `fabriciq-ontology-authoring-cli`. |
| Base64 decode produces binary junk | Part payload was not `InlineBase64`; check `payloadType`. If it's `VsixPackage` or an unknown kind, skip and warn. |

---

## Agentic Workflows

### Snappy-Response Discipline

Consumption is read-only and should *feel* fast. The default mode is **inline composition** in the shell — not a Python wrapper. Use this checklist before reaching for a script:

| Situation | Inline (`az rest` / `curl`) | Python / shell script |
|---|:-:|:-:|
| Single-entity lookup | ✅ | ❌ |
| Time-series window read | ✅ | ❌ |
| Graph walk, hop ≤ 2 (see [graph-walks.md](references/graph-walks.md)) | ✅ | ❌ |
| Cross-source relationship traversal (LH keys → KQL fan-out) | ✅ | ❌ |
| Grounding-JSON extraction (one-shot) | ✅ | ❌ |
| LRO `getDefinition` poll loop the user wants to re-run | ➖ | ✅ |
| Ontology authoring / mutation (35-part envelope, ID cross-refs) | ❌ | ✅ (handoff to `fabriciq-ontology-authoring-cli`) |
| Long-lived seeding / batch loads with retry & checkpoint | ❌ | ✅ |

**Inline-first principles**

1. **Compose, don't script.** Each REST call is independently meaningful; chain with `&&` / `|` / `jq` rather than wrapping in a `.py`.
2. **Parallelize fan-out.** Independent reads (linking-table queries, per-entity-type IN-list reads) go in `&` with `wait`, not sequential `for` loops.
3. **One round trip per group.** `WHERE id IN (...)` not N×`WHERE id = '...'`.
4. **Cache the grounding JSON** for the session — it does not change between queries, and refetching it doubles every walk's latency.
5. **Stream early.** Show the anchor row and first neighbor group as soon as they return; don't block presentation on the full walk.
6. **No script unless asked.** If the user says "save this for later" or "re-run nightly", *then* package as a script. Otherwise keep the work in chat-replayable shell.

If a task starts to look like it needs > ~20 REST calls, > 2 hops, or persistent state across calls, surface this to the user before scripting — it usually means the question should be narrowed, not automated.

### "Ground then Query" Sequence

When the user asks to query data through an ontology lens:

```text
Step 1 → Resolve WS_ID + ONT_ID (list workspaces, list items type=Ontology)
Step 2 → getDefinition (LRO) → decode all parts → reconstruct tree
Step 3 → Build grounding JSON (entities, properties, bindings, relationships)
Step 4 → Disambiguate with the user if multiple entity types / bindings could satisfy the intent
Step 5 → For the chosen entity type + binding:
           a. Remap ontology property names → source column names
           b. Compose the source query (KQL / Spark SQL / T-SQL)
           c. Hand off to the matching sibling consumption skill with minimal fields
Step 6 → Post-process results back into ontology-property naming for the user (optional but helpful)
```

### Schema-Aware Query Generation

After a grounding pass, generate queries using the physical columns recorded in `propertyBindings[]`, never the ontology names:

```text
Entity type "Aircraft" with binding:
  source kind = KustoTable
  sourceTableName = "AircraftReadings"
  timestampColumnName = "PreciseTimestamp"
  propertyBindings: { AltitudeFt → SourceColumn "Temp_C", TailNumber → SourceColumn "AssetId" }

User intent: "show altitude excursions on aircraft N42ZA in the last hour"

Generated KQL (delegated to eventhouse-consumption-cli):
  AircraftReadings
  | where AssetId == "N42ZA"
  | where PreciseTimestamp > ago(1h)
  | project PreciseTimestamp, Temp_C
  | where Temp_C > 80
```

### Relationship Traversal

```text
Relationship "operates" (Airline → Aircraft)
Contextualization: LakehouseTable "HubAircraftAssignment" with (AirlineId, TailNumber) columns
  AND two entity-type bindings (Airline on LakehouseTable "Airlines", Aircraft on KustoTable "AircraftReadings")

User intent: "which aircraft does Airline 'ZA' operate and what's their latest reading?"

Step 1: sqldw-consumption-cli → SELECT TailNumber FROM HubAircraftAssignment WHERE AirlineId = 'ZA'
Step 2: eventhouse-consumption-cli → AircraftReadings | where AssetId in (<TankIds>) | summarize arg_max(PreciseTimestamp, *) by AssetId
Step 3: Merge results in the agent; present with ontology-level column names.
```

Full end-to-end bash recipes (enumerate → ground → route → query) live in [examples.md](references/examples.md). For "show me everything related to X" prompts, jump straight to the N-hop walk in [graph-walks.md](references/graph-walks.md).

### Graph Walks (N-hop from an anchor)

When the user gives an instance ("Panel7", "aircraft N42ZA", "customer 1234") and asks for *its neighborhood* — not a single column — use the dedicated **graph walk** pattern instead of inventing a recipe per question.

```text
Anchor → relationships touching anchor (from grounding JSON, in-memory)
       → linking-table reads (parallel, one per relationship)
       → IN-list reads of neighbor entities (one per EntityType)
       → optional KustoTable telemetry sweep (one per EntityType with TS binding)
```

For hop=1 this is typically ≤ 10 round trips and stays inline. Full algorithm, fan-out template, hop budget, and a worked Panel7 example live in [graph-walks.md](references/graph-walks.md).

---

## Examples

End-to-end worked examples (enumerate an ontology → build grounding JSON → route a source-table query to the correct sibling consumption skill → traverse a relationship across Lakehouse + Eventhouse) live in [examples.md](references/examples.md). N-hop neighborhood walks from an anchor instance (Panel7-style) live in [graph-walks.md](references/graph-walks.md). Complete fetch-and-decode scripts live in [grounding-extraction.md](references/grounding-extraction.md). Per-binding-type invocation templates live in [routing.md](references/routing.md).

---

## Agent Integration Notes

- This skill is **read-only** on the ontology item. All authoring operations (create, alter, rebind, rename) belong to **`fabriciq-ontology-authoring-cli`** — delegate there.
- This skill **does not execute data queries itself**. It produces grounding context and a routing decision; the actual source query runs inside the per-datasource consumption skill you delegate to.
- Supported downstream skills (preview): **`eventhouse-consumption-cli`**, **`spark-consumption-cli`**, **`sqldw-consumption-cli`**. A standalone graph consumption skill does **not** yet exist — if the user asks for a graph-shaped query over relationships, surface that limitation and fall back to per-edge joins via Lakehouse / SQL.
- Orchestrator agents should hand this skill the **workspace name / ID** and the **ontology display name / ID**; it will return a grounding JSON they can reuse for subsequent delegate calls without re-fetching the definition.
- When authoring activity is suspected mid-session (e.g., the user runs `fabriciq-ontology-authoring-cli` and then comes back to query), **re-run the grounding pass** — the cached definition is stale.
- If a **Fabric KQL MCP server** is configured in the user's environment, it can substitute for `az rest` on the Eventhouse delegate leg. The repo's default `mcp-setup/mcp-config-template.json` does **not** register a `fabric-kql` server, so do not assume that name exists. Either way it does **not** cover ontology control-plane calls, so the fetch / grounding step still uses `az rest`.
