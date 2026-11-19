<!-- Topic reference for the `activator-cli` skill. Loaded on demand from `skills/activator-cli/SKILL.md` only for activation-history requests ("when/how often did a rule fire") in `consumption` mode. Not needed for authoring. -->

# activator-cli consumption — Querying Activation History

Read-only. Answers "when did this alert fire?" and "how often did this rule fire?" with the public `queryActivations` API — a synchronous POST (no LRO) that runs read-only KQL over the Activator's per-rule activation tables. Scopes: `Reflex.Read.All`, `Reflex.ReadWrite.All`, `Item.Read.All`, or `Item.ReadWrite.All`, plus Read on the item. Resolving ids by listing workspaces and Activators also needs `Workspace.Read.All` (or `Workspace.ReadWrite.All`) and a Viewer workspace role. Do not query the Eventhouse or the MCP endpoint for this.

```text
POST https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/reflexes/{reflexId}/queryActivations
{"query": "<KQL>"}
```

## Tables and Response

- Each rule has a table `ruleactivations_<ruleId>` (`uniqueIdentifier` without dashes, 32 lowercase hex). Discover them with `.show tables` — columns `TableName, DatabaseName, Folder, DocString`, where `DocString` is the rule's display name. Never guess a name.
- Results are under `.tables[0]`: `columns[].columnName` and `rows` (positional arrays). A multi-statement query returns one table per statement, in order. No `.show tables` rows = the Activator has no rules (every rule has a table, fired or not) — say so plainly. No rows from a rule table = it did not fire in the window.
- **Scope every claim to the window you queried.** Say a rule "never fired" only from a query with no `___time` filter over that rule's table; a filtered query supports only "did not fire in the last 7 days" (name the window). This applies to table cells too: an empty `lastSeen` from a windowed query means "none in the window", not "never".
- A never-fired table has only base columns (`___time`, `System.IngestionTime`, `System.RuleId`, `Signal.Name`, ...); richer ones (`System.ActionType`, `System.ObjectId`, ...) appear after activations. Read `.show table <t> cslschema` (or `| getschema`) before using any column but `___time`; bracket-quote dotted names: `['System.RuleId']`.
- **Wrap time columns in `todatetime()`.** `cslschema` reports `___time` as `datetime`, but fired tables return its values as strings, so raw comparisons, `bin()` or `max()`/`min()` fail with 500.

## Commands

Resolve ids by listing and filtering on display name, following `continuationUri` when a list spans pages — never guess a GUID. Then define the helper:

```bash
FABRIC=(--resource "https://api.fabric.microsoft.com" --headers "x-ms-fabric-skill=activator-cli")
WS_ID=$(az rest --method GET --url "https://api.fabric.microsoft.com/v1/workspaces" "${FABRIC[@]}" \
  --query "value[?displayName=='My Workspace'].id | [0]" -o tsv)
REFLEX_ID=$(az rest --method GET --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes" "${FABRIC[@]}" \
  --query "value[?displayName=='My Activator'].id | [0]" -o tsv)

query_activations() {  # jq builds the body, so KQL quotes need no escaping
  az rest --method POST --resource "https://api.fabric.microsoft.com" \
    --url "https://api.fabric.microsoft.com/v1/workspaces/${WS_ID}/reflexes/${REFLEX_ID}/queryActivations" \
    --headers "Content-Type=application/json" "x-ms-fabric-skill=activator-cli" \
    --body "$(jq -nc --arg q "$1" '{query: $q}')"
}

# Rule tables, and one rule's table by display name
query_activations '.show tables' | jq '.tables[0].rows[] | {table: .[0], rule: .[3]}'
TABLE=$(query_activations '.show tables' | jq -r --arg n "Too hot for medicine" '.tables[0].rows[] | select(.[3] == $n) | .[0]' | head -n 1)
# Or from a decoded rule id: TABLE="ruleactivations_$(echo "$RULE_ID" | tr -d '-' | tr 'A-F' 'a-f')"
[ -n "$TABLE" ] || { echo "No such rule on this Activator"; exit 1; }

# Schema, recent rows, and last fired over all history (no ___time filter; never fired = 0 and "")
query_activations ".show table ${TABLE} cslschema" | jq -r '.tables[0].rows[0][1] | split(",")[]'
query_activations "${TABLE} | where todatetime(___time) > ago(24h) | order by todatetime(___time) desc | take 50"
query_activations "${TABLE} | summarize activations=count(), lastSeen=max(todatetime(___time))" \
  | jq '.tables[0].rows[] | {activations: .[0], lastSeen: .[1]}'
```

Counts across rules over a window (match the asked window — `ago(24h)` for "last 24 hours"): name every table (wildcard unions are rejected), summarize inside each leg so non-firing rules report `0`, and tag legs with a literal name — `withsource=` yields `union_argN`:

```bash
T=$(query_activations '.show tables')
LEGS=$(echo "$T" | jq -r '[.tables[0].rows[][0] | "(\(.) | where todatetime(___time) > ago(7d) | summarize activations=count(), lastSeen=max(todatetime(___time)) | extend RuleTable=\"\(.)\")"] | join(", ")')
[ -n "$LEGS" ] && query_activations "union ${LEGS}" | jq --argjson t "$T" \
  '($t.tables[0].rows | map({(.[0]): .[3]}) | add) as $n | .tables[0].rows[] | {rule: $n[.[2]], activations: .[0], lastSeen: .[1]}'
```

## Restrictions and Errors

- **Allowed:** `.show tables` and `.show table <t> cslschema` (optionally `| <operators>`); `let` and tabular operators (`where`, `project`, `extend`, `summarize`, `count`, `take`, `top`, `order`, `join`, `lookup`, `union` of named tables, `make-series`, `mv-expand`, `parse`, `getschema`) over this item's rule tables.
- **Rejected:** other mgmt commands (including `schema as json`), wildcard unions, `search`, `find`, `evaluate`, `fork`, `facet`, `partition`, `scan`, `invoke`, `reduce`, `externaldata`, `datatable`, `set`, `restrict`, `alias`, `declare query_parameters`, `pattern`, and queries referencing no rule table (bare `print`).
- Limits: 1 MB of query text, about 30 seconds per query, bounded result size — filter by `___time` and aggregate.

Errors are `{"requestId", "errorCode", "message", "isRetriable"}`; keep `requestId` for support. The public endpoint returns generic codes, so diagnose from the status and the query you sent:

| Status / `errorCode` | Typical causes | Fix |
|---|---|---|
| 400 `UnknownUserError` | KQL syntax error; a command or operator outside the allow-list; a malformed or unknown `ruleactivations_` name; query over 1 MB | Check the allow-list; re-run `.show tables` for exact names |
| 404 `ItemNotFound` | Wrong workspace or Activator id, or the item was deleted | Re-resolve ids by listing |
| 404, sovereign clouds (GCC, GCC High, DoD, Mooncake) | The API is not enabled there | Report activation history is unavailable there |
| 500 `InternalServerError` | Unknown column; alias `first`/`last`; unwrapped `___time` | Read `cslschema`, use `firstSeen`/`lastSeen`, add `todatetime()`; don't blind-retry |
| Timeout or result-size error (`QueryTimeout`, `ResultTooLarge`) | Query ran past about 30 seconds or returned too much | Narrow the `___time` window, aggregate, or `take` fewer rows |
| 401 / 403 | Wrong token audience or no permission on the item | Use `--resource https://api.fabric.microsoft.com`; check item permissions |

## Must / Prefer / Avoid

- **Must:** use `queryActivations`; resolve tables via `.show tables`; read `cslschema` before non-`___time` columns; parse `.tables[0]`; wrap `___time` in `todatetime()`; report non-firing rules as `0` and empty results honestly — never invent activations; scope each claim to the queried window ("never" needs an unfiltered query).
- **Prefer:** resolving a table by `DocString` matched in `jq`; filtering by `___time` and aggregating before returning rows.
- **Avoid:** wildcard unions; mgmt commands beyond the two allowed; `withsource=` for table names; blind retries of 500s; the Eventhouse or MCP endpoint.