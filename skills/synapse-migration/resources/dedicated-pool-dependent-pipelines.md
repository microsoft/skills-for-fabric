# Dedicated Pool Dependent Pipelines

Use this internal sub-flow only when an approved Dedicated SQL Pool-to-Lakehouse migration has ADF or Synapse pipelines that call converted stored procedures. This skill owns the complete conditional flow; do not invoke, load, consult, or delegate to `pipeline-migration`. Standalone pipeline migrations remain owned by `pipeline-migration`.

Begin every response for this sub-flow with `Target: Fabric Lakehouse.` In every response for this sub-flow, name the Fabric replacement as a `TridentNotebook` activity. Include this response checklist verbatim; do not shorten property paths or replace pipeline readback with a generic validation statement:

- "Use a `TridentNotebook` activity with exact target identities `typeProperties.notebookId` and `typeProperties.workspaceId`, and pass inputs through `typeProperties.notebookParameters`."
- "After deployment, read back each pipeline with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/getDefinition` and validate its canonical hash and structural bindings."
- "Reject a partial selection when an excluded root reaches a selected shared child; include every sharing root and its complete closure."
- "Before persisting a source definition, recursively reject secret-bearing or uncertain properties; write no source artifact and perform no target mutation for that closure."
- "Only after recursive inspection proves a source definition secret-free, retain it as `sourceDefinitionArtifact`, record its canonical `sourceDefinitionHash`, include both in `handoffHash`, and invalidate resume when the live source, retained artifact, or recorded hash differs; blocked closures retain no source artifact or hash."
- "The migration does not automatically execute notebooks or pipelines."

Before sending the response, verify that all six checklist sentences appear verbatim. A response that mentions `typeProperties.notebookId`, `typeProperties.workspaceId`, or `typeProperties.notebookParameters` separately but omits `TridentNotebook` is incomplete; add the full first sentence rather than paraphrasing it. A response that says only "after each deploy, read back the definition" is also incomplete; add the full second sentence so the pipeline identity, `getDefinition` endpoint, canonical-hash validation, and structural-binding validation remain explicit.

If the procedures are already converted and published, treat that conversion as a prerequisite; do not re-narrate or redo T-SQL-to-Spark-SQL conversion.

## Activation And Ownership

Enter this sub-flow only when all of these conditions are true:

1. The parent request is a Synapse Dedicated SQL Pool-to-Fabric Lakehouse migration.
2. The approved migration scope contains stored procedures converted to Fabric notebooks.
3. Recursive discovery during assessment finds an ADF or Synapse pipeline activity that calls one of those in-scope procedures.

If condition 1 or 2 is false, do not include this sub-flow. Route a standalone pipeline migration to `pipeline-migration`. If only condition 3 is false, record `NotApplicable` in the parent migration manifest and continue the Lakehouse migration without pipeline transformation.

When condition 3 is true, present the discovered pipeline roots, their recursively resolved child closures, and the exact in-scope procedure calls. Then ask the user to choose one option:

1. migrate all discovered pipeline closures;
2. migrate specific named pipeline roots, automatically including each selected root's complete child closure; or
3. skip ADF/Synapse pipeline migration.

Discovery does not grant mutation approval. Do not infer consent from the parent Dedicated Pool-to-Lakehouse request, a prior procedure mapping approval, or a request to "proceed." If the user has not answered this pipeline-specific question, pause before transformation and deployment. An explicit skip records `ExcludedByUser` and continues the Lakehouse migration without changing pipelines. Before accepting a partial selection, compute reverse references from every pipeline outside the selected closures to every selected child. If an excluded root can still reach a selected child, require the user to include every sharing root and its complete closure or block the partial selection; never deploy a shared child while recording one of its roots as excluded. Only after this check passes may unselected pipelines remain unchanged and be recorded as excluded evidence while the complete selected closures are assessed and deployed.

Persist this contract at `migration-manifest.json.dependentPipelines` and record exactly one `state` there:

| State | Meaning |
|---|---|
| `NotApplicable` | Recursive discovery found no caller of an in-scope procedure. |
| `ExcludedByUser` | The user excluded the complete discovered closure. |
| `Blocked` | A dynamic, ambiguous, unsupported, or incomplete binding prevents a safe rewrite. |
| `Ready` | Every target notebook passed persisted-definition readback, including top-level `metadata.language_info.name: python`, and every selected call has an exact binding. |

`synapse-migration` owns discovery, normalization, transformation, deployment, validation, and resume for this conditional sub-flow. Do not delegate it to another skill.

## Readiness Gate

Do not transform or deploy a pipeline until every referenced target notebook has:

- a Fabric workspace GUID and notebook item GUID;
- a persisted definition read back from Fabric;
- top-level `metadata.language_info.name` equal to `python` in that persisted definition; do not infer notebook readiness from `%%sql`, cell-level language metadata, or `kernelspec`;
- a `definitionHash` calculated from the exact persisted notebook definition;
- an approved procedure mapping and complete supported input contract.

If any dependency is missing, record `Blocked`, list the affected activity paths, and stop before pipeline mutation. Never execute a generated notebook as part of migration.

## Recursive Discovery And Normalization

1. Enumerate approved ADF and Synapse pipeline roots.
2. Normalize both ARM shapes into one internal representation containing source kind, pipeline name, activity path, activity type, linked service, procedure or script text, parameters, outputs, and child-pipeline references.
3. Follow child-pipeline references recursively. Detect cycles and retain each deterministic activity path, including nested container activities.
4. Build an index from normalized procedure identity to the approved procedure/notebook mapping.
5. Select only native stored-procedure activities with an exact procedure name or script activities containing one deterministic `EXEC`/`EXECUTE` call after SQL comments are removed.
6. Assess every activity, dataset, connection, expression, and child reference in the selected closure for Fabric compatibility, even when it does not call a converted procedure. A selected pipeline is deployable only when the complete generated definition is Fabric-compatible.

Preserve unrelated behavior and retain the original source definitions byte-for-byte as evidence; do not claim the generated Fabric definition is byte-identical when source-only fields require normalization. Block deployment of the affected closure when an unrelated activity or dependency is unsupported or unresolved. Do not rewrite dynamic SQL, expressions that construct procedure names, scripts with multiple executable statements, ambiguous aliases, unresolved child references, or calls outside the approved mapping. Record each as `Blocked` with evidence.

## Version 1.0 Contract

Persist the contract below inside the manifest. Use GUIDs for Fabric workspace, pipeline, lakehouse, and notebook item identifiers.

`activityBindings` contains only source procedure-to-`TridentNotebook` bindings. Record `ExecutePipeline` relationships exclusively in the owning pipeline mapping's `childBindings`; never duplicate a child-pipeline call as an `activityBindings` entry.

```json
{
	"dependentPipelines": {
		"schemaVersion": "1.0",
		"state": "Ready",
		"sourceKind": "ADF|Synapse",
		"migrationId": "<stable migration id>",
		"targetWorkspaceId": "<guid>",
		"targetLakehouseId": "<guid>",
		"pipelineMappings": [
			{
				"sourcePipeline": "Parent",
				"sourceDefinitionArtifact": "source-pipelines/Parent.json",
				"sourceDefinitionHash": "sha256:<lowercase hex>",
				"targetPipelineId": "<guid>",
				"generatedDefinitionHash": "sha256:<lowercase hex>",
				"rollbackEvidence": {
					"definitionArtifact": "rollback/<targetPipelineId>/pipeline-content.json",
					"definitionHash": "sha256:<lowercase hex>"
				},
				"childBindings": [
					{
						"activityPath": "activities/RunChild",
						"sourceChildPipeline": "Child",
						"targetWorkspaceId": "<guid>",
						"targetPipelineId": "<guid>"
					}
				]
			}
		],
		"notebookReadiness": [
			{
				"sourceProcedure": "dbo.usp_LoadCustomer",
				"workspaceId": "<guid>",
				"notebookId": "<guid>",
				"definitionHash": "sha256:<lowercase hex>"
			}
		],
		"activityBindings": [
			{
				"sourcePipeline": "Parent",
				"activityPath": "activities/ForEach/activities/LoadCustomer",
				"sourceProcedure": "dbo.usp_LoadCustomer",
				"targetWorkspaceId": "<guid>",
				"targetLakehouseId": "<guid>",
				"targetNotebookId": "<guid>",
				"parameterMappings": [
					{
						"sourceParameter": "BatchId",
						"targetParameter": "BatchId",
						"type": "int",
						"required": true,
						"sourceDefaultPresent": false,
						"sourceDefault": null,
						"missingValueBehavior": "RejectBeforeMutation",
						"value": "@pipeline().parameters.BatchId"
					}
				],
				"outputContract": null
			}
		],
		"sessionReuse": {
			"choice": "Enable|Isolate|Defer",
			"disposition": "Compatible|NotCompatible|Isolated|Deferred",
			"evidence": [],
			"sessionTag": null
		},
		"handoffHash": "sha256:<lowercase hex>"
	}
}
```

Before writing any discovery-time JSON definition, recursively inspect every property name and value. Treat authorization values, connection strings, `SecureString` payloads, passwords, `pwd`, client/API/account/shared-access/secret-access keys, SAS signatures, access or refresh tokens, and secret-bearing URI query or fragment values as sensitive. Treat an ambiguous secret-like property as sensitive rather than guessing. If any selected pipeline definition contains or may contain a sensitive value, mark the complete selected closure `Blocked`, write no `sourceDefinitionArtifact` for that definition, and perform no target mutation. Do not redact and continue: a redacted copy is not the complete definition and cannot satisfy the source hash-binding contract.

Only after the recursive inspection proves the definition contains no sensitive or uncertain values, persist its complete discovery-time JSON beneath the manifest directory at the mapping's relative `sourceDefinitionArtifact` path and record its canonical `sourceDefinitionHash`. Derive the artifact path from the stable source identity, not an untrusted display name; reject absolute paths and traversal outside the manifest directory. Immediately before transformation or deployment and on every resume, re-read the source definition from ADF or Synapse, rerun the sensitive-value inspection, and require its canonical hash to match both the retained artifact and `sourceDefinitionHash`. If the source cannot be re-read, the inspection no longer passes, or either hash differs, invalidate the affected checkpoint and reassess that pipeline before any target mutation.

For a newly created pipeline, set `rollbackEvidence` to JSON `null`. Before replacing an existing exact-name pipeline, decode its pre-update `pipeline-content.json` readback to the relative `definitionArtifact` path shown above and record the canonical `definitionHash` of that JSON. Keep the artifact beneath the manifest directory and verify the file and hash before mutation and on resume.

Allow only supported scalar notebook parameter types and preserve source defaults and requiredness. Every `parameterMappings` entry must include `required`, `sourceDefaultPresent`, `sourceDefault`, and `missingValueBehavior` in addition to its source/target names, type, and value. `sourceParameter` is the discovered source name without a leading `@`; `targetParameter` must exactly equal the variable name in the notebook's tagged parameter cell. Populate the Fabric TridentNotebook activity's `typeProperties.notebookParameters` with those exact names, types, and pipeline expressions. Rename the legacy Synapse `typeProperties.parameters` key; do not preserve it or invent snake_case aliases. Block table-valued, output, cursor, or otherwise unsupported parameter contracts.

Normalize each dynamic expression into Fabric's nested expression envelope. The outer object carries the notebook scalar type; its `value` contains the canonical pipeline expression object. Never place a bare `@...` string directly in the outer `value`:

```json
{
	"notebookParameters": {
		"BatchId": {
			"value": {
				"value": "@pipeline().parameters.BatchId",
				"type": "Expression"
			},
			"type": "int"
		}
	}
}
```

Default `outputContract` to JSON `null`. Spark SQL result grids are not Fabric pipeline return values. Generated Dedicated Pool procedure notebooks do not emit `notebookutils.notebook.exit(...)`; record every caller that consumes a stored-procedure output as `Blocked` and require a separately authored and validated orchestration notebook redesign. Do not add a post-bridge Python exit cell to a generated procedure notebook. Never map stored-procedure results to `output.result` or `activity('<name>').output.runOutput` during automatic conversion.

Compute `handoffHash` over the `dependentPipelines` object only: omit only its `handoffHash` property, then calculate SHA-256 over canonical UTF-8 JSON with object keys sorted ordinally, array order preserved, and no insignificant whitespace. This hash binds `state`, source and rollback evidence, the target workspace, Lakehouse, pipeline, child-pipeline, and notebook GUIDs plus every recorded definition hash. Validate that `state` is exactly one allowed value and is consistent with the populated readiness/binding evidence; also validate the schema, GUIDs, duplicate activity paths, source artifacts and `sourceDefinitionHash` values, notebook `definitionHash` values, parameter completeness/types, output mappings, child bindings, rollback artifacts, and canonical hash before transformation and again before deployment.

## Selective Transformation

For each validated binding, replace only the bound activity with a Fabric `TridentNotebook` activity. When explaining this rewrite, state: "Use a `TridentNotebook` activity with exact target identities `typeProperties.notebookId` and `typeProperties.workspaceId`, and pass inputs through `typeProperties.notebookParameters`." Preserve activity name, dependencies, policy, user properties, annotations, and unrelated fields whenever Fabric supports them. Record unsupported source properties explicitly rather than silently dropping them.

The replacement must use `typeProperties.notebookId`, `typeProperties.workspaceId`, and, when inputs exist, `typeProperties.notebookParameters`. Remove source-only stored-procedure properties, linked-service references, Spark-pool references, session configuration, and the legacy Synapse `parameters` key from that activity. Cap a preserved notebook activity timeout at Fabric's supported maximum rather than copying an incompatible source timeout.

Also transform every `ExecutePipeline` edge in each selected closure. Replace the source child name in `typeProperties.pipeline.referenceName` with the exact Fabric child DataPipeline item GUID from `pipelineMappings[].childBindings[]`, preserve `type: "PipelineReference"`, and add `typeProperties.workspaceId` with the child workspace GUID even for same-workspace children. A missing, ambiguous, dynamic, or unselected child binding makes the closure `Blocked`; never leave a source child display name in a generated Fabric parent.

After transformation, verify that:

- every binding resolves to exactly one transformed activity;
- no unbound activity changed;
- each notebook reference and typed parameter matches the version 1.0 contract;
- all rewritten output consumers match the declared `outputContract`;
- no source stored-procedure activity remains for an approved binding.
- every selected `ExecutePipeline` edge resolves to exactly one hash-bound child mapping, contains the expected child pipeline GUID and workspace GUID, and retains no source child display name.

## Deployment, Validation, And Resume

Deploy only after Lakehouse schema objects and notebooks are published and read back. Deploy the pipeline dependency graph in reverse topological order: leaf/child pipelines before their parents. Refuse deployment on unresolved cycles.

Before creating or replacing a pipeline, list DataPipeline items in the target workspace and resolve the exact display name. If no exact match exists, create with `POST /v1/workspaces/{workspaceId}/items` and the exact create-body type `DataPipeline`, and record `rollbackEvidence: null`. If one exact match exists, read and hash its current definition with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/getDefinition` and an explicit empty JSON body `{}` (for `az rest`, use `--body '{}'`), require explicit replacement approval, write the decoded `pipeline-content.json` to `rollback/<targetPipelineId>/pipeline-content.json` beneath the manifest directory, record that relative path and canonical hash in `rollbackEvidence`, verify both, and only then update with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/updateDefinition`. More than one exact match is `Blocked`; never select the first match.

Send a DataPipeline definition whose `definition.parts` includes `pipeline-content.json` encoded as `InlineBase64`. For a definition-only replacement, send only `pipeline-content.json` and omit `.platform`. Include `.platform` together with `updateMetadata=true` only when intentionally updating item metadata; never send `.platform` to Update Item Definition without that query parameter. Treat `200`/`201` as synchronous success and `202` as an LRO; preserve and poll the first response's `Location` with bounded attempts and `Retry-After`, carrying `x-ms-fabric-skill: synapse-migration` on every request and poll. For `az rest`, specify `--resource https://api.fabric.microsoft.com` on the initial mutation as well as every poll. Do not pipe the mutation through debug or text filters that discard its status, headers, or exit code. Submit exactly one create/update mutation per target: never replay it because output was filtered or empty, and never retry a non-retriable authentication, conflict, or validation response. Re-resolve persisted state before deciding whether any later retry is safe. Do not start a pipeline job.

Read back every deployed pipeline definition with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/getDefinition` and an explicit empty JSON body `{}` (for `az rest`, use `--body '{}'`). Decode the single `pipeline-content.json` `InlineBase64` part, and compare its canonical definition hash and structural bindings with the planned artifact. Report selected, transformed, preserved, blocked, deployed, and validated counts, plus evidence by pipeline and activity path.

For every source `sourceDefinitionHash`, notebook `definitionHash`, pipeline `generatedDefinitionHash`, rollback hash, and resume hash, calculate SHA-256 over canonical JSON: recursively sort object keys using ordinal comparison, preserve array order and every returned property, encode as UTF-8, and omit only insignificant serialization whitespace. Never remove service-added Notebook metadata, cell IDs, execution fields, or other returned properties before hashing, and never hash the raw serialized file bytes. Formatting differences are not definition changes, but property removal is. Calculate source hashes from the complete source definitions read from ADF or Synapse and target hashes from the decoded persisted definitions returned by Fabric, not from pre-publication target files. For a target, the decoded persisted definition means the complete object returned by Fabric. For every mutation and `getDefinition` call, assign the request file's absolute path to `$requestPath`, emit only the method, endpoint, absolute path, SHA-256 hash, and a sanitized non-sensitive shape summary, and use `az rest --method post --url "<resolved endpoint>" --resource https://api.fabric.microsoft.com --headers "x-ms-fabric-skill=synapse-migration" --body "@$requestPath"`; never emit the complete body, connection details, credentials, or sensitive property values. A bare path without `@` sends the path text rather than the file contents. Do not rely on `cd` or another preceding directory change to interpret a relative `@file` or `-InFile` argument. Capture the first mutation response in that same invocation; never repeat a successful mutation merely to save or log its response.

Checkpoint after discovery, readiness, transformation, each deployment, and readback validation. Bind every checkpoint to `migrationId`, `handoffHash`, the target workspace/Lakehouse/pipeline/notebook GUIDs, notebook `definitionHash` values, source pipeline hashes, generated pipeline hashes, and any rollback artifact hashes. Resume only when all bound identities and hashes still match; otherwise invalidate the affected checkpoint and restart at the earliest changed phase. When recording `resumeEvidence` inside `dependentPipelines`, recompute that object's `handoffHash` afterward so the evidence is covered by the canonical hash; omit only `dependentPipelines.handoffHash` itself from the hash input. Never treat a previously deployed parent as valid when a child definition, rollback artifact, or target identity changed.

## Must / Prefer / Avoid

### MUST

- Ask the user whether to migrate all discovered pipeline closures, specific named roots, or no pipelines before transformation or deployment.
- Require explicit approval of the recursive pipeline closure.
- Require exact procedure and activity bindings before rewriting.
- Require complete Fabric compatibility for the selected recursive closure and preserve unrelated pipeline behavior.
- Include the mandatory `x-ms-fabric-skill: synapse-migration` header on every Fabric API call and LRO poll.

### PREFER

- Keep normalized source definitions and transformed artifacts in the migration package for review.
- Use deterministic ordering for discovery results, contracts, reports, and deployment plans.

### AVOID

- Do not delegate this conditional flow to `pipeline-migration`.
- Do not infer procedure identity from partial names or free-form text.
- Do not invent notebook parameter aliases or treat a Spark SQL result grid as pipeline output.
- Do not deploy parent pipelines before children.
- After mutating a child pipeline, read back and validate its persisted canonical hash and structural bindings before mutating any parent pipeline.
- Do not resume from a checkpoint whose contract or definition hashes changed.

## Example

An ADF child pipeline contains two native stored-procedure activities bound exactly to converted procedures, and its parent invokes that child. Present the discovered parent/child closure and ask whether to migrate all discovered closures, selected named roots, or none. After the user selects this closure and persisted-definition readbacks are complete, create the version 1.0 contract, replace only the bound activities with `TridentNotebook`, deploy and validate the child, then deploy and validate the parent. A separate request to migrate an unrelated ADF pipeline routes to `pipeline-migration`.
