# Dedicated Pool Execution Contracts

Load this file only after a Dedicated SQL Pool-to-Lakehouse request has been routed to a specialized workflow. The core source-read-only and no-row-movement boundaries in `SKILL.md` always apply.

## Contents

- [Dependent Procedure Callers](#dependent-procedure-callers)
- [Interactive Notebook Conversion](#interactive-notebook-conversion)
- [Completion Language](#completion-language)
- [Guidance-Only Incremental Deployment Hardening](#guidance-only-incremental-deployment-hardening)
- [Offline Local-Artifact Workflow](#offline-local-artifact-workflow)
- [Feature-Wise Risk or Mapping Assessment](#feature-wise-risk-or-mapping-assessment)
- [Large-Procedure Offline Package](#large-procedure-offline-package)

For large or complex stored procedures, prove conversion coverage with a deterministic source-block ledger. An offline Dedicated Pool artifact request still requires this skill. For a complete large-procedure request, read `../resources/dedicated-pool-large-procedure-audit.md` exactly once before generating artifacts.

For a Dedicated Pool request, read `../resources/dedicated-pool-to-lakehouse.md` once as the phase router. Load each phase-specific reference only when entering that phase, and use the manifest instead of rereading completed-phase guidance. Persist per-object evidence in the manifest and telemetry instead of repeating it in chat.

For phased guidance, use the literal heading `Phase 1 — Lake Database/HMS to Lakehouse: NotApplicable (none discovered)` when discovery finds no catalog; never collapse the plan to Phase 0 → Phase 2.

Do not carry `DISTRIBUTION`, `CLUSTERED COLUMNSTORE INDEX`, or other Dedicated SQL Pool storage hints into the target. Fabric Warehouse handles distribution and Delta-backed storage automatically.

## Dependent Procedure Callers

During assessment, recursively discover ADF or Synapse procedure callers. If callers exist, ask the user to select all closures, named complete closures, or none; parent migration approval is not pipeline approval. Only after notebook readback and explicit closure selection, read the complete `../resources/dedicated-pool-dependent-pipelines.md` sub-flow, including its Contract Schema, Deployment, and Resume sections.

- Before persistence, recursively inspect every source pipeline definition for credentials, connection strings, SAS/query/fragment secrets, authorization values, secure-string payloads, and ambiguous secret-like properties. If any are present or cannot be ruled out, block the complete selected closure, write no source artifact, and perform no target mutation; do not redact and proceed because that would break the complete-definition hash contract.
- Only after that inspection passes, retain each complete source pipeline definition and record its manifest-relative `sourceDefinitionArtifact` plus canonical `sourceDefinitionHash` in `pipelineMappings`.
- Include both in `handoffHash`. On resume, invalidate the checkpoint if the live ADF/Synapse source, retained artifact, or recorded hash differs.
- Hash the complete decoded persisted Notebook JSON using canonical JSON rules: recursively sort object keys, preserve arrays and every returned property, and never remove service-added metadata, cell IDs, or execution fields before hashing. Never hash raw notebook bytes.
- Preserve the complete documented `activityBindings`, including `sourceProcedure`, target workspace/Lakehouse/notebook identities, `parameterMappings`, and output contract. `activityBindings` contains only procedure-to-notebook bindings; record `ExecutePipeline` child references only in `pipelineMappings[].childBindings`, never as a second `activityBindings` entry.
- Before sending any dependent-pipeline response, verify that it contains this sentence verbatim: "Use a `TridentNotebook` activity with exact target identities `typeProperties.notebookId` and `typeProperties.workspaceId`, and pass inputs through `typeProperties.notebookParameters`." Naming only `TridentNotebook`, only the property paths, or generic GUIDs is incomplete.
- For every live Lakehouse, Notebook, or DataPipeline create/update or `getDefinition` call, write request JSON beneath the manifest directory and assign its absolute path to `$requestPath`. Use `az rest --method post --url "<resolved endpoint>" --resource https://api.fabric.microsoft.com --headers "x-ms-fabric-skill=synapse-migration" --body "@$requestPath"` for each mutation and POST-based `getDefinition` readback; never rely on the default GET verb. With `Invoke-WebRequest` or `Invoke-RestMethod`, specify the resolved endpoint, `-Method Post`, `-Headers @{ "x-ms-fabric-skill" = "synapse-migration" }`, and `-InFile $requestPath`.
- Immediately before each mutation or `getDefinition` call, emit only redacted request evidence: method, endpoint, absolute request-file path, SHA-256 hash, and a sanitized non-sensitive shape summary. Never emit the complete request body, connection details, credentials, or sensitive property values.
- A bare path without `@` is a string body, not a file body; do not depend on a preceding directory change or send an in-memory `$body` after writing an unused copy.
- Before the only Notebook mutation, parse that exact file and call `validate_notebook_definition_request` with `require_item_metadata=True` for create or `False` for update and the exact expected Lakehouse binding.
- A create body must already contain `displayName`, `type: "Notebook"`, and the validated definition. Block before mutation on rejection; never repair or rewrite a request after submitting it.
- Capture the first mutation response and its `Location` in the same invocation, then poll it without replaying the mutation because a response was not logged, filtered output was empty, or a file copy is wanted. The shell call that performs a mutation may contain only the REST invocation plus non-failing raw-response persistence; never append `Select-String`, JSON parsing, assertions, or another post-processing command that can make the shell call fail after Fabric accepted the mutation. Perform inspection in a later shell call. If any local command fails after an accepted mutation, treat acceptance as indeterminate, resolve the exact target, and read it back without replay. Never issue one mutation for debug headers and repeat the same mutation for its response body; capture both from the single HTTP call. Submit exactly one create/update per target and never retry a non-retriable authentication, conflict, or validation response.
- For `az rest`, include `--verbose` on that single mutation and capture its combined output and exit code. Exit code `0` with an empty response body still means the mutation was accepted: classify the result as accepted or indeterminate, resolve the exact target by listing items, and perform readback. Never replay the mutation to obtain a body or response file.
- Do not redo completed conversion work or execute notebooks or pipelines; do not invoke, load, consult, or route this conditional sub-flow to `pipeline-migration`. Reserve that skill for standalone pipeline requests.

## Interactive Notebook Conversion

Before saving or reporting a generated Dedicated Pool notebook in an interactive workflow that permits correction, run `validate_spark_sql_notebook` from `scripts/dedicated_pool_runtime.py`, repair every rejection, and rerun until it passes. Do not replace this maintained semantic gate with ad hoc JSON or cell-shape checks.

The repair loop does not apply to the one-shot offline local-artifact workflow below. In that workflow, the first validator failure is terminal for the run and must be reported without editing, regenerating, or retrying.

## Completion Language

Keep completion responses literal and concise.

- Publication guidance begins: "The stored procedures were converted from T-SQL to Spark SQL before publication."
- A Dedicated Pool-to-Lakehouse result names the resolved Fabric Lakehouse and states: "Generated stored-procedure notebooks use executable `%%sql` transformation cells."
- If notebook validation fails, state instead: "Generation was blocked: intended stored-procedure notebooks use executable `%%sql` transformation cells, but validation failed; do not publish." Never report successful generation or publication after a validator failure.
- A dependent-pipeline result states:
  - "Use a `TridentNotebook` activity with exact target identities `typeProperties.notebookId` and `typeProperties.workspaceId`, and pass inputs through `typeProperties.notebookParameters`."
  - "After deployment, read back each pipeline with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/getDefinition` and validate its canonical hash and structural bindings."
  - "Reject a partial selection when an excluded root reaches a selected shared child; include every sharing root and its complete closure."
  - "Before persisting a source definition, recursively reject secret-bearing or uncertain properties; write no source artifact and perform no target mutation for that closure."
  - "Only after recursive inspection proves a source definition secret-free, retain it as `sourceDefinitionArtifact`, record its canonical `sourceDefinitionHash`, include both in `handoffHash`, and invalidate resume when the live source, retained artifact, or recorded hash differs; blocked closures retain no source artifact or hash."
  - "The migration does not automatically execute notebooks or pipelines."
- After successful large-procedure validation, state: "The T-SQL procedure was converted to executable Spark SQL," report validator/package evidence, and stop without inspecting eval graders.
- On a terminal validator failure, state: "The T-SQL procedure was not successfully converted to Spark SQL," name the failed gate, and do not claim publication readiness.

## Guidance-Only Incremental Deployment Hardening

For a guidance-only incremental deployment-hardening request, answer directly from this checklist without searching scripts or loading phase references.
State every applicable safeguard explicitly in the final response; implementation details do not substitute for a checklist item.

1. Begin: "This migration converts T-SQL procedures to Spark SQL."
2. Record each script-backed DACPAC load attempt and its model-only fallback blind spots.
3. State: "For columns with special characters, enable Delta `columnMapping` selectively and only with approval."
4. Reuse an existing Fabric Lakehouse table or shortcut only when it is compatible. Block incompatible targets for manual review rather than altering them, and never auto-mutate, overwrite, or drop an existing target.
5. Create or reuse one Livy session for the deployment phase. Within that session, submit one object/statement per Livy request in dependency order so each failure remains attributable to a specific object or statement. Do not create a new Livy session per object.
6. State: "Resume only when the input hash and a fresh target-state readback hash match the successful checkpoint."
7. Build validated file-backed REST JSON with `InlineBase64`, verify the request/definition, and delete temporary files in `finally` cleanup.
8. Record phase/object start and end timestamps, duration, counts, and retries. Record token usage as `null`/unavailable rather than estimating it.
9. State: "Keep the source read-only; do not modify or rewrite the source."

## Offline Local-Artifact Workflow

Read `../resources/dedicated-pool-conversion.md` once. A caller-supplied read allow-list is a hard boundary: do not inspect any file outside it. Treat named validators as black boxes; do not inspect validator, runtime, grader, eval, or test implementation, run CLI help/preflight probes, or reread generated files.

- Write one run-specific generator that emits the complete approved artifact set atomically. Run it once, then run each required validator once.
- When PySpark is not explicitly provisioned, invoke `validate_dedicated_pool_spark.py --structure-only` first, exactly once per notebook.
- A validator failure is terminal for that run. Report it without debugging, editing, regenerating, or retrying.
- A parameterized notebook's first code cell must serialize `metadata.tags` as exactly `["parameters"]`. Assert the exact tag in the generator before it writes any artifact.
- Restore an optional non-null source default before lexical validation.
- Use separate direct guards for required-null and required-blank checks.
- Use direct two-positional-argument `re.fullmatch` guards with no flags or keyword arguments, not membership tests.
- For case-insensitive Boolean validation, use `re.fullmatch(r"(?i:true|false|1|0)", str(<parameter>))`.
- Place every validation/normalization statement before the contiguous literal-key `spark.conf.set` calls.

## Feature-Wise Risk or Mapping Assessment

State:

- "Use the discovered procedure count to calculate the projected notebook count and projected workspace total."
- "Block conversion until the procedure mapping decision is approved."
- "Procedure mapping approval must cover target notebook names and workspace placement."
- Every feature-wise risk row must report `Likelihood` and `Impact` as separate fields from overall `Risk`; a single severity or risk value is incomplete.

Keep complete source-to-target procedure traceability for every approved mapping.

## Large-Procedure Offline Package

Treat all identifiers, artifact paths, and binding values supplied by the request as authoritative.

- Bind each generator path constant to the literal requested path; never derive a stable-ID source path from the shorter `sourceName`.
- Before writing anything, assert that the source path exactly equals the requested path, such as `source/dbo.usp_AuditedLoad.sql`.
- Read `../resources/dedicated-pool-large-procedure-audit.md` and `../resources/dedicated-pool-conversion.md` once each, then stop discovery.
- Do not search tests, fixtures, eval files, runtime implementation, validators, or graders for additional values or implementation hints.
- Build every Python notebook cell as newline-joined source, serialize it with `splitlines(keepends=True)`, and run `ast.parse` on the joined parameter and bridge cell source inside the generator before writing any artifact.
- Never serialize adjacent source-array entries without line terminators.
- Ensure every generated transformation cell starts with literal `%%sql`. With Python `%` formatting, write `%%%%sql` or concatenate the header so interpolation cannot collapse it to `%sql`.
- Apply the conversion type mapping in those cells, including source `BIT` comparisons as Spark SQL Boolean comparisons.
- Generate the complete package in one atomic generator run, invoke the generated package verifier once and the requested repository validator once, clean up the generator, report the evidence, and stop.
