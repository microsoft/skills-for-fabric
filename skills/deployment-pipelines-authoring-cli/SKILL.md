---
name: deployment-pipelines-authoring-cli
description: "Manages Fabric deployment pipelines for ALM promotion across dev, test, and prod stages, including stage creation, workspace assignment, selective forward or backward deploys, operation polling, stage role assignments, and the pipeline and workspace permissions each action requires. For Git sync use git-integration-operations-cli."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: deployment-pipelines-authoring-cli` (`az rest`: `--headers "x-ms-fabric-skill=deployment-pipelines-authoring-cli"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
> 3. To find a deployment pipeline or stage ID: list deployment pipelines (then stages) and filter by `displayName` with JMESPath — never guess IDs.

# Fabric Deployment Pipelines Authoring — CLI Skill

Automates Fabric Application Lifecycle Management (ALM) with **deployment pipelines**: promote Fabric
content between stages (typically Development → Test → Production) using the Fabric core control-plane
REST API. This skill covers pipeline/stage lifecycle, workspace assignment, and stage-to-stage deployment
(a long-running operation).

## Prerequisite Knowledge

Read these companion documents first — this skill assumes their patterns and does **not** repeat them:

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — resolve workspace/item IDs by name via list + JMESPath |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Token audience must be `https://api.fabric.microsoft.com`; wrong audience = 401 |
| Authentication Recipes | [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes) | `az login` flows and token acquisition |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | Pagination, LRO polling, rate-limiting patterns |
| Long-Running Operations (LRO) | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern) | **Deploy is an LRO** — poll `/v1/operations/{id}` until terminal |
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) | Sovereign/gov clouds use different hosts |
| Supported item types | [references/supported-item-types.md](references/supported-item-types.md) | Living list of item types a deploy can copy (per category, with preview flags) — reconcile from the **official Microsoft docs** (source of truth); don't guess |
| Diff two item definitions (token-efficient) | [references/scripts/diff_item_definitions.py](references/scripts/diff_item_definitions.py) | Local tool that decodes both `getDefinition` payloads, normalizes auto-rebound fields, and prints **only the diffs** — feed the diff (not the full definitions) to the model. `python references/scripts/diff_item_definitions.py source.json target.json` (exit `0`=same, `1`=changed) |

This skill adds: **how to drive the deployment-pipelines REST surface** from an agentic terminal.

## Concepts

- A **deployment pipeline** contains **2–10 ordered stages** (`order` starts at 0). Each stage may have at
  most **one assigned workspace**, and a workspace can be assigned to at most one stage.
- **Deployment** copies supported item content from a **source stage** to an **adjacent target stage**.
  Forward deploys (dev→test→prod) work between any adjacent stages. **Backward** deploys (e.g. prod→test)
  are currently supported **only when the target stage is empty** (no assigned workspace) — you cannot
  backward-deploy over a stage that already has a workspace.
- **Item pairing (autobinding).** During deployment Fabric records a **connection between a source item and
  its clone** in the target stage; this pairing is how later deploys know which target item to overwrite,
  and how related items (e.g. a report and its semantic model) stay bound. There is **no REST API to _set_
  pairing** — it is maintained automatically — but you can **observe** the current pairing via the
  `sourceItemId` / `targetItemId` fields returned by `List stage items`. See the *Fix a broken item pairing*
  workflow below for the only supported repair.
- Deploy is an **asynchronous long-running operation (LRO)**: the API returns `202 Accepted` with an
  operation ID; you poll for completion.
- **Deployment rules** and **parameter rules** (e.g. repoint a data source per stage) are configured in the
  Fabric **portal UI** — there is **no REST API to create rules**. Do not claim otherwise.
- Only **supported item types** are copied by a deploy; unsupported items are skipped (not an error). The
  supported set changes over time — see [references/supported-item-types.md](references/supported-item-types.md).
- There is **no "what changed" / compare REST API**. `List stage items` returns item **identity + pairing**
  (`itemId`, `itemDisplayName`, `itemType`, `sourceItemId`, `targetItemId`, `lastDeploymentTime`) — but **no
  change status**, and `lastDeploymentTime` is the last **deployment** time, **not** the last edit time, so
  it is not a reliable change signal. To deploy only changed items you must **diff the two stages yourself**
  and build the `items` list (see the *Deploy only changed items* workflow below). The portal's "Compare"
  view is server-side and not exposed via API.

## Must/Prefer/Avoid

### MUST DO
- Resolve pipeline, stage, and workspace **IDs by name** via list + JMESPath before any mutating call. Never fabricate GUIDs.
- Target the correct base URL: `https://api.fabric.microsoft.com/v1/deploymentPipelines` and acquire a token for the `https://api.fabric.microsoft.com` audience.
- Treat **Deploy Stage Content** as an LRO: on `202`, capture the operation ID and poll `/v1/operations/{operationId}` until the state is `Succeeded`/`Failed`, then surface the result.
- When the **target stage has no assigned workspace**, include `createdWorkspaceDetails` (name, and `capacityId` when needed) in the deploy body, or the deploy fails.
- Confirm destructive intent (delete pipeline, unassign workspace, backward deploy over prod) with the user before executing.
- Verify the caller has the **required permissions** before a mutating call (see *Required permissions* below): pipeline **Admin** for every pipeline operation, plus the appropriate **workspace** role for assign/deploy. Surface a clear, actionable message on `401`/`403` rather than retrying blindly.

### PREFER
- Selective deploys via the `items` array (`{ sourceItemId, itemType }`) when the user names specific items; omit `items` to deploy **all** supported items.
- A human-readable `note` on every deploy — but know it is **write-only**: the API accepts it and never
  returns it (it appears only in the portal UI). For a programmatic audit trail, also record the deploy
  externally (CI/CD logs or a Git commit message).
- `List Deployment Pipeline Stage Items` to preview what will move before deploying.
- Idempotent scripting: check whether a pipeline/stage/assignment already exists before creating it.

### AVOID
- Inventing a "create deployment rule" or "parameter rule" REST call — those are UI-only today.
- Assigning a workspace during an **active deployment** (the assign call fails) or to a stage/workspace that is already paired.
- Hardcoding `api.fabric.microsoft.com` in sovereign clouds — resolve the host from environment config.
- Using a service principal without first confirming the Fabric admin enabled SP creation of deployment pipelines.
- **Hashing raw `getDefinition` output to detect changes without normalizing.** Deployment **auto-rebinds**
  embedded references in the target (pipeline `notebookId`/`workspaceId`, report→model id, Direct Lake
  server/db), so a paired target's definition legitimately differs from the source even when nothing was
  edited — naive hashing reports **false "changed"**. Strip/normalize those binding fields before comparing.
- **Diffing by dumping every item definition into the agent's context.** A full two-stage content diff can be
  dozens of `getDefinition` calls and >100 KB — do the compare in a script
  ([references/scripts/diff_item_definitions.py](references/scripts/diff_item_definitions.py)) and surface only
  the resulting change list, and for a changed item forward **only the emitted diff**, never the two full
  definitions, to the model.
- Unassigning a workspace to repair a broken pairing **without first warning the user** that unassign
  **permanently deletes that stage's deployment history and its configured deployment/parameter rules** —
  always ask whether the stage has rules before unassigning (see *Fix a broken item pairing*).

## REST API Reference

Base: `https://api.fabric.microsoft.com/v1`. Delegated scopes are **per operation** — provision a service
principal with least privilege:

| Operation | Required delegated scope |
|---|---|
| List / Get (pipelines, stages, stage items, operations) | `Pipeline.Read.All` **or** `Pipeline.ReadWrite.All` |
| Create / Update / Delete pipeline, Update stage | `Pipeline.ReadWrite.All` |
| Assign / Unassign workspace | `Pipeline.ReadWrite.All` **and** `Workspace.ReadWrite.All` |
| **Deploy stage content** | **`Pipeline.Deploy`** |

Deploy uses its own `Pipeline.Deploy` scope — an app scoped only to `Pipeline.ReadWrite.All` gets a **403**
on `POST .../deploy`.

| Operation | Method + Path |
|---|---|
| List pipelines | `GET /deploymentPipelines` |
| Create pipeline | `POST /deploymentPipelines` |
| Get / Update / Delete pipeline | `GET|PATCH|DELETE /deploymentPipelines/{id}` |
| List / Get stages | `GET /deploymentPipelines/{id}/stages[/{stageId}]` |
| Update stage | `PATCH /deploymentPipelines/{id}/stages/{stageId}` |
| List stage items | `GET /deploymentPipelines/{id}/stages/{stageId}/items` |
| Assign workspace to stage | `POST /deploymentPipelines/{id}/stages/{stageId}/assignWorkspace` |
| Unassign workspace from stage | `POST /deploymentPipelines/{id}/stages/{stageId}/unassignWorkspace` |
| **Deploy stage content (LRO)** | `POST /deploymentPipelines/{id}/deploy` |
| List operations (≤20 recent) | `GET /deploymentPipelines/{id}/operations` |
| Get operation (with execution plan) | `GET /deploymentPipelines/{id}/operations/{operationId}` |
| Role assignments | `GET|POST|DELETE /deploymentPipelines/{id}/roleAssignments[/{principalId}]` |

### Request-body shapes (guidance)

- **Create**: `{ "displayName", "description"?, "stages": [ { "displayName", "description"?, "isPublic" } ] }` — 2–10 stages.
- **Assign workspace**: `{ "workspaceId" }`.
- **Deploy**: `{ "sourceStageId", "targetStageId", "items"?: [ { "sourceItemId", "itemType" } ], "note"?, "options"?: { "allowCrossRegionDeployment": false }, "createdWorkspaceDetails"?: { "name", "capacityId"? } }`.

## Required permissions

Deployment pipeline operations are governed by **two** independent permission systems: your role on the
**pipeline** (its own `roleAssignments`) and your role on each **workspace** involved. You generally need
**both**. Deployment pipelines require a Fabric capacity/subscription, and the pipeline creator becomes the
pipeline **Admin**.

| Operation | Pipeline role | Workspace role(s) |
|---|---|---|
| Create a pipeline | — (becomes **Admin** on create) | **Admin** of a Fabric workspace (feature access prerequisite) |
| Get / list pipeline, stages, items, operations | **Admin** (shared access) | — |
| Update / delete pipeline; manage `roleAssignments` | **Admin** | — |
| **Assign / unassign** a workspace to a stage | **Admin** | **Admin** of the workspace being (un)assigned |
| **Deploy** stage content | **Admin** | at least **Contributor/Member** on **both** the source and target stage workspaces (higher role if the target items require it) |
| Deploy to an **empty** target stage (creates a workspace) | **Admin** | capacity-assignment permission to place the new workspace on a capacity; the deploying user becomes the **only Admin** of the newly created workspace and owner of cloned semantic models |

Notes:
- Sharing a pipeline grants the pipeline **Admin** role — there is no lower "viewer-only" pipeline write role for these operations.
- A **service principal** can drive these APIs only if the Fabric admin enabled *service principals can create deployment pipelines* (and the SP holds the same pipeline + workspace roles above).
- On `403`, distinguish *missing pipeline role* from *missing workspace role* in the message so the user knows which access to request.



**Create a pipeline** → POST the display name + ordered stages; capture the returned stage IDs (they are
what you deploy between).

**Assign a workspace to a stage** → resolve stage ID and workspace ID by name, verify both are unassigned,
then POST `assignWorkspace`. Requires admin on both the pipeline and the workspace.

**Deploy content** → resolve source/target stage IDs, optionally preview stage items, POST `deploy` (all
items or a selected `items` list) with a `note`, then poll the returned operation to completion and report
which items moved.

**Deploy only changed items** → there is no diff/compare API, so compute the delta yourself. `List stage
items` gives identity + pairing only (no timestamps, no change status), so change detection means comparing
**item definitions**:
1. Resolve the source and target **stage** IDs and the workspace assigned to each.
2. List items in **both** stages (`GET .../stages/{stageId}/items`) — each source row carries `sourceItemId`
   (as `itemId`) and its paired `targetItemId` (absent = **new/unpaired**). Also list the target stage to find
   **deleted** items (present in target, not paired from any source). Pair by `targetItemId`; fall back to
   `(itemType, displayName)` only when no pipeline pairing exists (name-matching can't detect renames).
3. **Filter out system-managed children** — a `SQLEndpoint` is auto-created per Lakehouse/Warehouse and should
   not be diffed or deployed on its own; it follows its parent.
4. Classify each paired item:
   - **New** (no `targetItemId`) → deploy.
   - **Changed** → detect via `POST .../items/{id}/getDefinition` on **both** stages, then diff. Run
     [references/scripts/diff_item_definitions.py](references/scripts/diff_item_definitions.py) on the two
     responses: it decodes each part, **normalizes** the auto-rebound fields (pipeline `notebookId`/
     `workspaceId`, report model id, Direct Lake server/db) for you, and prints only the differing parts
     (exit `1` = changed, `0` = identical) — so you don't hand-roll hashing or false-positive on unedited
     items. Note the `getDefinition` contract differs by type:
     `Notebook`/`SemanticModel`/`Report` are **LRO** (`202` → poll → `GET .../result`);
     `DataPipeline` returns **`200` synchronously**.
   - **Warehouse** does have a definition API:
     [Get Warehouse Definition](https://learn.microsoft.com/en-us/rest/api/fabric/warehouse/items/get-warehouse-definition)
     is `POST .../workspaces/{workspaceId}/warehouses/{warehouseId}/getDefinition`, with `format=sqlproj`
     (default) or `format=dacpac`. Accept `200`; for `202`, follow the documented LRO to its result,
     carrying the skill telemetry header on every request. The API requires Warehouse read/write
     permissions even though it retrieves a definition. Compare SQL-project/schema content with
     appropriate tooling; the generic JSON diff helper is **not** a schema-aware binary DACPAC comparer.
     Definitions do not include table data. If schema equality is unproven, report that limitation
     rather than claiming the API does not exist or declaring the item unchanged.
   - `Lakehouse` / `Environment` expose `getDefinition` but capture structure/metadata only
     (not table data or most content edits); diff by **presence**, flag user-reported content changes,
     and state the limits of any equality claim.
   - When you cannot prove equality, treat the item as **changed** (safe default).
5. Do the comparison **in a script** (parallelize the independent `getDefinition` calls; they dominate
   latency) and surface only the computed change list. To let the model reason about *what* changed in an
   item, forward **only the emitted diff** (`diff_item_definitions.py` output), not the two full definitions —
   a normalized diff is typically a few lines versus the >100 KB of raw payloads.
6. Filter to **supported item types** (see references), show the user the change list, confirm, then POST a
   **selective** `deploy` with the `{ sourceItemId, itemType }` array and a `note`, and poll to completion.

> Deletions do **not** propagate via a selective `items` deploy — an item removed from the source stage is not
> removed from the target by a selective deploy. Use a **full** deploy (omit `items`) to propagate deletions,
> or delete the target item manually, and warn the user of this before promoting.

**Fix a broken item pairing** → pairing (the source↔target connection Fabric maintains, a.k.a. autobinding)
is **not settable via any REST API**. When two items that should be paired across stages are not — surfaced
by a deploy that duplicates an item instead of overwriting it, an autobind/dependency failure, or the user
reporting it — the **only supported repair is to unassign the affected stage's workspace and re-assign it**,
which forces Fabric to rebuild the pairing on the next deploy. This is destructive:
1. **Warn the user first.** Unassigning a workspace **permanently deletes that stage's deployment history and
   all its configured deployment/parameter rules** — they cannot be recovered by re-assigning.
2. **Ask whether the stage has rules.** Because rules are UI-only (no REST API to read or recreate them),
   explicitly ask the user whether the stage has deployment/parameter rules configured **before** unassigning.
   If it does, have them record the rules (or recreate them in the portal afterward) and get explicit
   confirmation to proceed.
3. Only after confirmation, `POST .../stages/{stageId}/unassignWorkspace`, then
   `POST .../stages/{stageId}/assignWorkspace` with the same `workspaceId`, and re-run the deploy so the
   pairing is re-established.

**Track / audit** → `List operations` for recent history; `Get operation` to inspect the execution plan and
per-item status of a specific deployment.

### Deploy operational caveats & common errors

- **One deploy per pipeline at a time.** A pipeline runs a single operation at a time; starting another while
  one is in flight fails with **`WorkspaceMigrationOperationInProgress` (HTTP 400)**. Always poll the current
  operation to a terminal state before starting the next stage promotion (this is also why the *assign*
  workspace call fails during an active deployment).
- **First deploy after assigning a workspace can fail with `Alm_InvalidRequest_WorkloadUnavailable`.** Newly
  assigned workspaces need **~60–120 s** for workload services (Lakehouse, Notebook, etc.) to initialize.
  Mitigate by waiting before the first deploy, or deploy Power BI items (`SemanticModel`, `Report`) first and
  Fabric-native items (`Lakehouse`, `Notebook`) after a short delay; retry on this error. Subsequent deploys
  are reliable once workloads are warm.
- **The operation ID is returned in the `x-ms-operation-id` response header** (alongside `Location`), not the
  `202` body. `az rest` does not surface response headers cleanly — for reliable header capture in automation,
  issue the deploy with `curl -i` (or Python `requests`) and parse the header, then poll
  `/v1/operations/{operationId}` with `az rest`.
- **Deploy copies definitions, not data.** Only item metadata/definitions are promoted; table data, query
  results, and caches are not. Trigger refreshes/loads in the target stage after a deploy.
- **Maximum 300 items per deploy request.** A selective (or full) deploy is capped at **300 deployed items**;
  batch larger promotions across multiple deploy calls.

## Examples

### Create a three-stage pipeline
Deployment-pipeline `displayName` is **unique tenant-wide** — a create for a name
already in use fails with `Alm_InvalidRequest_DuplicateAlmPipelineName` (HTTP 400,
"pipeline name ... is already in use"). To make a create re-runnable, drop any
existing pipeline of that name first, then create. Write the JSON body to a file
and pass it with `--body @file.json` — an inline multi-line `--body '{...}'` is
mangled into an empty body on Windows/PowerShell (`az` is `az.cmd`), which the API
rejects with `InvalidInput: Unexpected end when reading JSON`.
```bash
# Idempotent: delete an existing "Sales Analytics ALM" if present, then create.
EXISTING=$(az rest --method GET --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines" \
  --query "value[?displayName=='Sales Analytics ALM'].id | [0]" --output tsv)
if [ -n "$EXISTING" ]; then
  az rest --method DELETE --resource https://api.fabric.microsoft.com \
    --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$EXISTING"
fi

cat > /tmp/create-pipeline.json << 'EOF'
{
  "displayName": "Sales Analytics ALM",
  "description": "Dev/Test/Prod promotion for Sales Analytics",
  "stages": [
    { "displayName": "Development", "isPublic": false },
    { "displayName": "Test",        "isPublic": false },
    { "displayName": "Production",  "isPublic": true }
  ]
}
EOF
az rest --method POST \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines" \
  --headers "Content-Type=application/json" \
  --body @/tmp/create-pipeline.json
```

### Assign a workspace to the Development stage
```bash
# $PIPELINE_ID and $DEV_STAGE_ID resolved via list + JMESPath; $WS_ID resolved from workspace name.
az rest --method POST \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/stages/$DEV_STAGE_ID/assignWorkspace" \
  --headers "Content-Type=application/json" \
  --body "{ \"workspaceId\": \"$WS_ID\" }"
```

### Deploy all items dev → test and wait for the LRO
```bash
# Kick off the deployment (returns 202 + an operation id header).
az rest --method POST \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/deploy" \
  --headers "Content-Type=application/json" \
  --body "{ \"sourceStageId\": \"$DEV_STAGE_ID\", \"targetStageId\": \"$TEST_STAGE_ID\", \"note\": \"Promote validated dev build\" }" \
  --verbose
# Then poll /v1/operations/{operationId} until state is Succeeded or Failed
# (see COMMON-CLI § Long-Running Operations pattern).
```

### Deploy only selected items
```bash
az rest --method POST \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/deploy" \
  --headers "Content-Type=application/json" \
  --body '{
    "sourceStageId": "'"$TEST_STAGE_ID"'",
    "targetStageId": "'"$PROD_STAGE_ID"'",
    "items": [
      { "sourceItemId": "'"$MODEL_ID"'", "itemType": "SemanticModel" },
      { "sourceItemId": "'"$REPORT_ID"'", "itemType": "Report" }
    ],
    "note": "Promote reviewed model + report to production"
  }'
```

### Deploy only the items that changed (compute the diff first)
```bash
# 1. List paired items for BOTH stages. Each source row carries itemId (= sourceItemId)
#    and its paired targetItemId (absent = new/unpaired). There is NO timestamp or
#    change-status field, so "changed" must be detected from item definitions.
az rest --method GET --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/stages/$SOURCE_STAGE_ID/items" \
  > source-items.json

# 2. NEW items = unpaired (no targetItemId). Exclude system-managed SQLEndpoint children.
NEW=$(jq '[.value[]
  | select(.itemType != "SQLEndpoint")
  | select(has("targetItemId") | not)
  | { sourceItemId: .itemId, itemType: .itemType }]' source-items.json)

# 3. CHANGED items (paired): fetch getDefinition from BOTH stages, then diff with
#    references/scripts/diff_item_definitions.py. It decodes each part, NORMALIZES the
#    auto-rebound fields (notebookId/workspaceId in pipelines, model id in reports,
#    server/db in Direct Lake models) and prints ONLY the differing parts. Notebook/
#    SemanticModel/Report are LRO (202 -> poll -> /result); DataPipeline returns 200 sync.
#    Parallelize the independent getDefinition calls. Per paired definition-backed item:
#      getDefinition SOURCE_WS id            > src.json
#      getDefinition TARGET_WS targetItemId  > tgt.json
#      python references/scripts/diff_item_definitions.py src.json tgt.json > diff.json
#      # exit 1 = changed -> add { sourceItemId, itemType } to $ITEMS; exit 0 = unchanged.
#      # Forward diff.json (NOT src.json/tgt.json) to the model to explain the change.
#    Merge NEW + CHANGED into $ITEMS. When equality can't be proven, include the item.

# 4. Selective deploy of just the changed set.
az rest --method POST --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/$PIPELINE_ID/deploy" \
  --headers "Content-Type=application/json" \
  --body "$(jq -n --arg s "$SOURCE_STAGE_ID" --arg t "$TARGET_STAGE_ID" --argjson items "$ITEMS" \
    '{ sourceStageId: $s, targetStageId: $t, items: $items, note: "Deploy only changed items" }')"
# Then poll /v1/operations/{operationId} until terminal.
# NOTE: a selective deploy does NOT propagate deletions — use a full deploy (omit items) for those.
```

### Prompt/response

**User:** "Promote my Sales dev workspace to the Test stage and tell me when it's done."

**Assistant (behavior):**
1. Lists deployment pipelines → filters to the one whose Development stage holds the Sales dev workspace; captures `sourceStageId` (Development) and `targetStageId` (Test).
2. Confirms the Test stage has an assigned workspace (or asks for a name + capacity to create one).
3. POSTs `deploy` with a `note`, receives `202`, extracts the operation ID.
4. Polls `/v1/operations/{operationId}` until terminal, then reports success and the list of deployed items (or the failure reason).
