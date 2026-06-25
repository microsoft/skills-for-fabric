# Ontology Consumption — Graph Walks

How to resolve **all data N hops from an anchor entity instance** through an ontology — without writing a custom script per question.

This is the most common consumption ask after grounding ("show me everything related to Panel7", "what does aircraft N42ZA touch", "neighborhood of customer 1234"). The pattern below composes existing routing primitives into a fixed N-hop walk.

> **Speed-first:** every step in this file is a single REST call (one `az rest` or one `curl`). Do **not** distill into a Python script unless the user asks for a reusable artifact. See [SKILL.md § Snappy-Response Discipline](../SKILL.md#snappy-response-discipline).

---

## Pre-Walk Checklist (do this once per session, then never again)

Before the first walk, the in-memory grounding JSON must already contain — or you must populate — every metadata value you'll need. **Re-deriving these mid-walk is the #1 cause of call-count bloat.**

| Need | Where it lives in grounding | If missing |
|---|---|---|
| Workspace GUID | top-level `workspaceId` | Prompt user / `list workspaces` once |
| Ontology GUID | top-level `ontologyId` | `list items type=Ontology` once |
| Per-binding source-type & `itemId` (GUID) | `EntityTypes/{etId}/DataBindings/*.json → dataBindingConfiguration.sourceTableProperties.{sourceType,itemId,sourceTableName}` | Re-decode binding parts |
| Lakehouse SQL endpoint host (only for `LakehouseTable`) | Not in ontology — call `get item` on the LH once if you need SQL; otherwise read CSVs from OneLake DFS as staging fallback | `get item` on the LH once |
| Eventhouse `clusterUri` + `databaseName` (only for `KustoTable`) | `dataBindingConfiguration.sourceTableProperties.{clusterUri,databaseName}` (when `sourceType == "KustoTable"`) | `get eventhouse` once |
| Linking-table names per relationship | `RelationshipTypes/{relId}/Contextualizations/*.json → dataBindingTable.{sourceTableName,itemId,sourceType}` | Re-decode contextualization parts |
| Source column names per property | `dataBindingConfiguration.propertyBindings[].{sourceColumnName,targetPropertyId}` | Re-decode binding parts |
| Linking-table FK columns | `RelationshipTypes/{relId}/Contextualizations/*.json → sourceKeyRefBindings[0].sourceColumnName` and `targetKeyRefBindings[0].sourceColumnName` | Re-decode contextualization parts |
| EntityType id-property | `EntityTypes/{etId}/definition.json → entityIdParts[0]` (then map via `propertyBindings` to `sourceColumnName`) | Re-decode entity-type parts |
| Relationship endpoints | `RelationshipTypes/{relId}/definition.json → source.entityTypeId` and `target.entityTypeId` | Re-decode relationship parts |

**Rule:** every walk-time call is a *data* call (linking-table, entity-table, telemetry sweep). If you find yourself issuing a `list items`, `get eventhouse`, or schema-probe (`take 2`) call mid-walk, stop — that value should already be in grounding. Pull it from grounding instead.

### Shell hygiene

If your shell is **stateless across calls** (i.e., env vars set in one invocation are not visible in the next), either:

1. **Recompute the token inline** at the start of every shell call, or
2. **Reuse a persistent shell session** (e.g., a single `bash`/`pwsh` session held open for the whole walk) and `export` once.

Do **not** rely on `$env:STOK` / `$STOK` surviving between unrelated tool invocations — token is silently empty on the second call, every request returns `401 Unauthorized`, and you lose two more turns chasing it. Ask me how I know.

### Token acquisition — pick the in-process path

`az account get-access-token` spawns a Python subprocess and costs **~2.5s per call cold** on Windows. For a walk that needs 2+ resources (Fabric API + Storage, sometimes + Kusto), that's 5–7s of pure overhead.

**Preferred (PowerShell):** use the in-process `Get-AzAccessToken` from the `Az.Accounts` module. First call ~2s (MSAL warmup), every subsequent call **~200–500ms** (in-memory cache, including different resources). No subprocess.

```powershell
Import-Module Az.Accounts
$FTOK = (Get-AzAccessToken -ResourceUrl "https://api.fabric.microsoft.com" -WarningAction SilentlyContinue).Token
$STOK = (Get-AzAccessToken -ResourceUrl "https://storage.azure.com"        -WarningAction SilentlyContinue).Token
# Optional, for KQL: $KTOK = (Get-AzAccessToken -ResourceUrl "https://kusto.kusto.windows.net" ...).Token
```

If you must use `az`: fetch tokens **in parallel** (`Start-Job` / `&` background) — sequential is the most expensive thing in the whole walk.

### Parallel data reads

Once you have the linking-table + neighbor-entity-table list from grounding, the reads are **independent** — fire them concurrently. PowerShell 7+:

```powershell
$specs = @(@{key="anchor";lh=$lhId;tbl="panels"}) + $linkSpecs + $neighborSpecs
$results = $specs | ForEach-Object -Parallel {
  $u = "https://onelake.dfs.fabric.microsoft.com/$using:WS/$($_.lh)/Files/raw/$($_.tbl).csv"
  try { $rows = Invoke-RestMethod -Uri $u -Headers @{Authorization="Bearer $using:STOK"} | ConvertFrom-Csv } catch { $rows=@() }
  [pscustomobject]@{ key=$_.key; rows=$rows }
} -ThrottleLimit 8
```

A 7-rel walk that took ~5s sequentially completes in ~1.7s parallel. Same for sqlcmd / az rest — issue them as background jobs and `Wait-Job`.

---

## Walk Primitive

A graph walk has three inputs, no more:

| Input | Example | Source |
|---|---|---|
| **Anchor** = `(EntityType, KeyValue)` | `(Panel, "panel7")` | User intent |
| **Hops** = signed-integer | `1` (= immediate neighbors) | User intent (default `1`) |
| **Direction** = `out` / `in` / `both` | `both` | Default `both` |

Output: a flat list of `(EntityType, KeyValue, Properties, RelationshipName, Hop)` tuples — projectable, mergeable, presentable.

---

## Algorithm (one pass, no recursion needed for N≤2 in 99% of cases)

```text
1. From grounding JSON, find AnchorEntity → keyPropertyId → keyColumn → bindings.
2. Issue ONE source-table read for the anchor's own row (LH SQL or KQL).
3. Find every relationship where AnchorEntity is the source OR target.
4. For each matching relationship:
   a. Read the contextualization's linking table where the anchor-side key column = AnchorKey.
      → returns target keys.
   b. Group target keys by target EntityType.
5. For each (EntityType, [keys]) group, issue ONE source-table read with `WHERE key IN (...)`.
6. Hop = 2? Take every (entity, key) returned from step 5 and re-enter at step 3.
7. Concatenate. Done.
```

Step counts for hop=1: **1 anchor read + R contextualization reads + N entity reads** where `R = relationships touching anchor`, `N = distinct neighbor entity types found`. For most ontologies that's ≤ 10 round trips. All parallelizable.

---

## Worked Example — `Panel7` neighborhood, 1 hop, both directions

Grounding JSON has been fetched (see [grounding-extraction.md](grounding-extraction.md)). Anchor: `(Panel, "panel7")`. Six outgoing relationships (`contains_*` to 6 device types) + one incoming (`contains_Panel` from `DataCenter`).

### Step 1 — Anchor row (1 call)

```bash
# Use GUIDs (workspaceId, itemId) — friendly names like "MyLH.Lakehouse"
# silently fail on tenants with FriendlyNameSupportDisabled.
WS_ID="<workspace-guid>"           # from grounding
LH_ID="<lakehouse-guid>"           # from grounding (binding.source.itemId)

# Delegate this read to sqldw-consumption-cli (Lakehouse SQL endpoint default) and run:
#   SELECT TOP 1 * FROM dbo.panels WHERE id = 'panel7';
```

> **Lakehouse read path note.** The canonical path is the SQL endpoint via `sqlcmd` / ODBC 18 / `az rest` against the SQL endpoint host. If the local environment lacks ODBC 18 and the data was *just seeded*, the source CSVs may still be parked at `Files/raw/` in OneLake DFS — that's a **staging fallback**, not the primary read path. Don't write that fallback into reusable recipes.

### Step 2 — Relationships touching the anchor (in-memory filter on grounding JSON, 0 calls)

```bash
# Pseudocode against the grounding JSON, not a REST call
RELS=$(jq '.relationshipTypes[] | select(.sourceEt == "<Panel-ET-id>" or .targetEt == "<Panel-ET-id>")' grounding.json)
```

### Step 3 — Linking-table reads (one call per relationship — fan out in parallel)

```bash
# All 7 in parallel (& backgrounding, then `wait`)
az rest ... -- "SELECT child_id FROM panel_contains_gateway         WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT child_id FROM panel_contains_circuit_breaker WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT child_id FROM panel_contains_power_meter     WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT child_id FROM panel_contains_io_device       WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT child_id FROM panel_contains_io_channel      WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT child_id FROM panel_contains_generic_asset   WHERE panel_id = 'panel7'" &
az rest ... -- "SELECT data_center_id FROM data_center_contains_panel WHERE panel_id = 'panel7'" &
wait
```

### Step 4 — Neighbor entity reads (one call per entity type with non-empty key list)

```bash
# E.g. CircuitBreaker neighbors:
az rest ... -- "SELECT id, brand, commercial_ref, family, model FROM circuit_breakers WHERE id IN ('cb_3','cb_4')"
```

### Step 5 — (Optional) Telemetry pass for KustoTable bindings

If any neighbor entity has a `KustoTable` `TimeSeries` binding, issue **one** KQL call per such EntityType across all its discovered keys:

```kql
device_telemetry
| where device_id in ("gateway_2", "cb_3", "cb_4")
| where timestamp_utc > ago(1h)
| summarize n=count(), latest=arg_max(timestamp_utc, value) by device_id
```

### Step 6 — Render

Group by EntityType, header per group, project bound columns only. Done.

---

## Hop > 1

Re-enter at step 2 using the **set of neighbors found in the previous hop** as the new anchor set. The linking-table queries become `WHERE source_key IN (...)` instead of `=`. Keep hops ≤ 2 unless the user explicitly asks — the working set explodes geometrically.

**Hop budget** (soft caps before asking the user to narrow):
- Hop 1: ≤ 100 anchors
- Hop 2: ≤ 1,000 keys per relationship
- Hop 3+: surface as a graph problem; suggest a Spark notebook (out of scope here).

---

## When to Use This vs. Single-Entity Query

| User intent | Pattern |
|---|---|
| "Show me CircuitBreaker `cb_3`" | Single-entity → [routing.md § Eventhouse / SQL endpoint](routing.md#field-mapping--ontology--delegate-input) |
| "All telemetry for `cb_3` last hour" | Single-entity + time filter |
| "Everything in `panel7`" | **Graph walk, hop=1, direction=out** |
| "Which DataCenter does `panel7` live in" | **Graph walk, hop=1, direction=in** |
| "Full neighborhood of `panel7`" | **Graph walk, hop=1, direction=both** ← this file |
| "Devices in any panel in `dc_east_1`" | **Graph walk, hop=2, direction=out** |
| "All paths between `dc_east_1` and `cb_3`" | Out of scope — surface to user; needs path-finding, not walks |

---

## Performance Rules

1. **Parallelize step 3 fan-out.** Linking-table reads are independent. `&` + `wait` in bash, `Promise.all` in JS, `asyncio.gather` in Python — pick whatever the local shell supports.
2. **Single round trip per entity type in step 4.** `WHERE key IN (...)` not `WHERE key = '...' OR key = '...'` — flatter plan, smaller text.
3. **Project bound columns only.** Never `SELECT *` — the binding is the column whitelist (see [SKILL.md § Prefer](../SKILL.md#prefer)).
4. **Read metadata from grounding, not from the API.** Item GUIDs, cluster URIs, source-column names, linking-table names, and `databaseName` are all in the in-memory grounding JSON the moment you decoded the ontology. A walk that issues `list items` / `get eventhouse` / `take 2` mid-flight is a walk that hasn't done its [Pre-Walk Checklist](#pre-walk-checklist-do-this-once-per-session-then-never-again). The one exception is the Lakehouse SQL endpoint host (not in the ontology) — resolve it once via `get item` on the lakehouse and cache for the session.
5. **Skip empty groups.** If step 3 returns no keys for a given relationship, skip step 4 for it — don't issue `WHERE id IN ()`.

---

## Anti-Patterns

- ❌ Writing a Python script to do steps 1–6. Each step is a single REST call composed in the shell or one `az rest` invocation. Reach for a script only if the user explicitly says "save this as something I can re-run" or hops > 2.
- ❌ Recursing through relationships before deduplicating keys. A walk can revisit the same entity through two paths; dedupe before step 4 to halve the round trips.
- ❌ Using `JOIN` across the linking table and the entity table in step 3+4 combined. The two tables may live in different LH items; join in the agent, not in source.
- ❌ Issuing per-key reads in step 4 (`WHERE id = 'cb_3'` followed by `WHERE id = 'cb_4'`). One `IN`-list per EntityType.
- ❌ **Mid-walk metadata fetches** — `list items` to find a Lakehouse GUID, `get eventhouse` to find a cluster URI, `take 2` to find a column name. Every one of those values is in grounding. If grounding doesn't have it, fix grounding-extraction; don't paper over it with a metadata call.
- ❌ **Friendly-name URLs** — `…/MyLakehouse.Lakehouse/…` looks fine in a hello-world tenant but returns `FriendlyNameSupportDisabled` on most enterprise tenants. Always substitute the GUID.

---

## Composing With Other Skills

- **Anchor lookup ambiguity** ("show me everything for Panel 7") → ground first via [grounding-extraction.md](grounding-extraction.md), confirm `Panel.PanelId == "panel7"` is the intended interpretation.
- **Each linking-table / entity-table read** → delegate to `sqldw-consumption-cli` (default) or `spark-consumption-cli` per [routing.md § Lakehouse](routing.md#lakehouse-lakehousetable--sqldw-consumption-cli-default-or-spark-consumption-cli).
- **Each KustoTable telemetry sweep** → delegate to `eventhouse-consumption-cli` per [routing.md § Eventhouse](routing.md#eventhouse-kustotable--timeseries--eventhouse-consumption-cli).
- **Schema gaps surfaced during walk** (missing relationship, mis-typed binding) → escalate to `fabriciq-ontology-authoring-cli`, do not patch in-flight.
