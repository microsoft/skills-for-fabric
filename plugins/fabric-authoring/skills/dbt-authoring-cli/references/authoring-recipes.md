# Authoring Recipes — `az rest` for Fabric dbt Jobs

Copy/paste `az rest` recipes for the full dbt job lifecycle. All calls pass
`--resource https://api.fabric.microsoft.com`. Assumes:

```bash
API="https://api.fabric.microsoft.com/v1"
RES="https://api.fabric.microsoft.com"
WS="<workspace-id>"
```

See [DBT-CORE.md](../../../common/DBT-CORE.md) for the definition model and the no-secrets rule. Confirm writes with
the user first (see SKILL.md § Preview & Confirm).

## Create a dbt job

```bash
JOB_ID=$(az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/dataBuildToolJobs" \
  --headers "Content-Type=application/json" \
  --body '{"displayName":"Sales dbt job","description":"Builds sales marts"}' \
  --query "id" -o tsv)
echo "Job: $JOB_ID"
```

## Discover the config-part name (never hardcode)

```bash
# getDefinition (LRO — poll Location if 202; see COMMON-CLI.md § LRO Pattern)
DEF=$(az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/getDefinition")
CONTENT_PART=$(echo "$DEF" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
CONTENT_PART="${CONTENT_PART:-dbt-content.json}"     # default for a brand-new job
echo "Config part: $CONTENT_PART"
```

## Deploy a local project into `Code/dbt/*` (read-modify-write)

`updateDefinition` replaces the whole part list, so rebuild it from the **existing** parts plus your
files. This packs everything under `./my_dbt_project` as `Code/dbt/<relpath>` and keeps any config /
`.platform` part already present.

```bash
ROOT="./my_dbt_project"

# Start from existing parts EXCEPT the project files we're about to replace.
PARTS=$(echo "$DEF" | jq '[.definition.parts[] | select(.path | startswith("Code/dbt/") | not)]')

# Add each project file as a Code/dbt/* part.
while IFS= read -r f; do
  rel="${f#"$ROOT"/}"
  b64=$(base64 -w0 < "$f" 2>/dev/null || base64 < "$f" | tr -d '\n')   # macOS has no -w0
  PARTS=$(echo "$PARTS" | jq --arg p "Code/dbt/$rel" --arg pl "$b64" \
    '. + [{path:$p, payload:$pl, payloadType:"InlineBase64"}]')
done < <(find "$ROOT" -type f -not -path '*/target/*' -not -path '*/.git/*')

az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/updateDefinition" \
  --headers "Content-Type=application/json" \
  --body "$(jq -n --argjson parts "$PARTS" '{definition:{parts:$parts}}')"
```

## Set the config part (connection GUID + schema + command)

Binds a **Fabric Warehouse** by workspace/artifact GUID. For Postgres/Snowflake/SQL Server, replace
`connectionSettings` with `"externalReferences": {"connection":"<conn-guid>"}` and set `profileType`
accordingly (`PostgreSql`/`Snowflake`/`SqlServer`). No credentials appear anywhere.

```bash
WH_ID="<warehouse-item-id>"
WH_FQDN=$(az rest --method GET --resource "$RES" \
  --url "$API/workspaces/$WS/items/$WH_ID" --query "properties.connectionString" -o tsv)

cat > /tmp/dbt-content.json << EOF
{
  "project": { "projectType": "OneLake", "folderPath": "dbt" },
  "profile": {
    "profileType": "DataWarehouse",
    "schema": "gold",
    "connectionSettings": {
      "name": "SalesWarehouse",
      "properties": {
        "type": "DataWarehouse",
        "typeProperties": { "workspaceId": "$WS", "artifactId": "$WH_ID", "endPoint": "$WH_FQDN" }
      }
    }
  },
  "command": { "operation": "build", "arguments": { "threads": 4, "failFast": true } }
}
EOF

# RMW: keep all existing parts, replace only the config part.
CONTENT_B64=$(base64 -w0 < /tmp/dbt-content.json 2>/dev/null || base64 < /tmp/dbt-content.json | tr -d '\n')
PARTS=$(echo "$DEF" | jq --arg cp "$CONTENT_PART" \
  '[.definition.parts[] | select(.path != $cp)]')
PARTS=$(echo "$PARTS" | jq --arg cp "$CONTENT_PART" --arg pl "$CONTENT_B64" \
  '. + [{path:$cp, payload:$pl, payloadType:"InlineBase64"}]')

az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/updateDefinition" \
  --headers "Content-Type=application/json" \
  --body "$(jq -n --argjson parts "$PARTS" '{definition:{parts:$parts}}')"
```

## Trigger a run and monitor

```bash
RUN_LOCATION=$(az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/jobs/instances?jobType=Execute" \
  --headers "Content-Length=0" --output none --include-response-headers 2>&1 \
  | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

while true; do
  RUN=$(az rest --method GET --resource "$RES" --url "$RUN_LOCATION")
  STATUS=$(echo "$RUN" | jq -r '.status')
  echo "Status: $STATUS"
  [[ "$STATUS" =~ ^(Completed|Failed|Cancelled|Deduped)$ ]] && break
  sleep 15
done
[[ "$STATUS" == "Failed" ]] && echo "$RUN" | jq '.failureReason'
```

## End-to-end

Create → deploy `Code/dbt/*` → set config → run, in order: run the four blocks above with the same
`$JOB_ID` and `$DEF` (re-fetch `$DEF` with getDefinition before each RMW so you always start from the
current parts).

---

## GitHub source

Connect a job to an existing GitHub repo instead of storing files in Fabric. **Run-only** — you can't
edit models in Fabric; commit to the repo and Fabric pulls on the next run. The classic PAT lives
only in the connection.

### 1) Create the GitHub source-control connection (PAT from env)

```bash
# Read the PAT from the environment so it never appears in shell history / files.
read -rs GITHUB_PAT    # or: export GITHUB_PAT before running

CONN_ID=$(az rest --method POST --resource "$RES" --url "$API/connections" \
  --headers "Content-Type=application/json" \
  --body "$(jq -n --arg url 'https://github.com/<owner>/<repo>' --arg pat "$GITHUB_PAT" '{
    connectivityType:"ShareableCloud",
    displayName:"MyGitHubPAT",
    connectionDetails:{ type:"GitHubSourceControl", creationMethod:"GitHubSourceControl.Contents",
      parameters:[{dataType:"Text", name:"url", value:$url}] },
    credentialDetails:{ credentials:{ credentialType:"Key", key:$pat } }
  }')" \
  --query "id" -o tsv)
echo "GitHub connection: $CONN_ID"
```

Response `connectionDetails.type` is `GitHubSourceControl`. Omitting the repo in `parameters.url`
scopes the connection to all repos the PAT can read.

### 2) Bind the dbt job to the GitHub source

Project points at the GitHub connection + branch; **profile and command stay the normal warehouse
binding** (a GitHub-sourced job still has an adapter + warehouse + schema). Push with `updateDefinition`.

> The git-source `project` block below is **inferred** (the portal writes it inside an iframe that
> can't be captured) — verify against your tenant. If rejected, capture a working job's definition
> with dbt-consumption-cli and copy the exact `project` shape.

```jsonc
{
  "project": {
    "projectType": "GitHubSourceControl",
    "connectionSettings": {
      "type": "GitHubSourceControl",
      "properties": { "connection": "<github-connection-guid>", "branch": "main", "rootFolder": "" }
    }
  },
  "profile": { "profileType": "DataWarehouse", "schema": "jaffle_shop",
    "connectionSettings": { "name": "jaffle_shop_dw", "properties": { "type":"DataWarehouse",
      "typeProperties": { "workspaceId":"<ws>", "artifactId":"<warehouse>", "endPoint":"<fqdn>" } } } },
  "command": { "operation": "build", "arguments": { "threads": 4 } }
}
```

### 3) Run

Identical to any dbt job — see [Trigger a run and monitor](#trigger-a-run-and-monitor).
