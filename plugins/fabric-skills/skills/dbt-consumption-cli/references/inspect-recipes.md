# Inspect & Monitor Recipes — `az rest` for Fabric dbt Jobs

Read-only (plus run) recipes. All calls pass `--resource https://api.fabric.microsoft.com`. Assumes:

```bash
API="https://api.fabric.microsoft.com/v1"
RES="https://api.fabric.microsoft.com"
WS="<workspace-id>"
```

See [DBT-CORE.md](../../../common/DBT-CORE.md) for the definition model.

## 1) List dbt jobs in a workspace

```bash
az rest --method GET --resource "$RES" \
  --url "$API/workspaces/$WS/items?type=DataBuildToolJob" \
  --query "value[].{name:displayName, id:id, description:description}" -o table
```

## 2) Decode a job's configuration (adapter, schema, command)

```bash
JOB_ID="<dbt-job-id>"
DEF=$(az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/getDefinition")     # poll Location if 202

CONTENT_PART=$(echo "$DEF" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
echo "$DEF" | jq -r --arg p "$CONTENT_PART" \
  '.definition.parts[] | select(.path==$p) | .payload' | base64 -d | jq '{
    projectType: .project.projectType,
    adapter:     .profile.profileType,
    schema:      .profile.schema,
    operation:   .command.operation,
    select:      .command.arguments.select,
    threads:     .command.arguments.threads,
    failFast:    .command.arguments.failFast
  }'
```

## 3) List the project files shipped with the job

```bash
echo "$DEF" | jq -r '.definition.parts[].path | select(startswith("Code/dbt/"))'
```

No `Code/dbt/*` parts usually means the job is **GitHub-sourced** (run-only) — the code lives in the
repo, not the definition. Check `project.projectType` from step 2.

## 4) Read a specific model or schema.yml (understand the data model)

```bash
# Decode schema.yml — the source of truth for the model's columns and tests.
echo "$DEF" | jq -r '.definition.parts[] | select(.path|endswith("schema.yml")) | .payload' \
  | base64 -d

# Decode a specific model
echo "$DEF" | jq -r '.definition.parts[] | select(.path=="Code/dbt/models/marts/fct_orders.sql") | .payload' \
  | base64 -d
```

## 5) Run history and failure diagnostics

```bash
az rest --method GET --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/jobs/instances" \
  --query "value[].{status:status, start:startTimeUtc, end:endTimeUtc, error:failureReason}" -o table
```

## 6) Trigger a run and monitor

```bash
RUN_LOCATION=$(az rest --method POST --resource "$RES" \
  --url "$API/workspaces/$WS/items/$JOB_ID/jobs/instances?jobType=Execute" \
  --headers "Content-Length=0" --output none --include-response-headers 2>&1 \
  | grep -i "^location:" | awk '{print $2}' | tr -d '\r')

while true; do
  RUN=$(az rest --method GET --resource "$RES" --url "$RUN_LOCATION")
  STATUS=$(echo "$RUN" | jq -r '.status'); echo "Status: $STATUS"
  [[ "$STATUS" =~ ^(Completed|Failed|Cancelled|Deduped)$ ]] && break
  sleep 15
done
[[ "$STATUS" == "Failed" ]] && echo "$RUN" | jq '.failureReason'
```

## 7) Compare dbt commands across jobs (governance)

```bash
for ID in $(az rest --method GET --resource "$RES" \
  --url "$API/workspaces/$WS/items?type=DataBuildToolJob" --query "value[].id" -o tsv); do
  echo "==== $ID ===="
  D=$(az rest --method POST --resource "$RES" --url "$API/workspaces/$WS/items/$ID/getDefinition")
  CP=$(echo "$D" | jq -r '.definition.parts[].path | select(test("dbt.?content\\.json"))')
  echo "$D" | jq -r --arg p "$CP" '.definition.parts[] | select(.path==$p) | .payload' \
    | base64 -d | jq '{adapter:.profile.profileType, operation:.command.operation, select:.command.arguments.select}'
done
```
