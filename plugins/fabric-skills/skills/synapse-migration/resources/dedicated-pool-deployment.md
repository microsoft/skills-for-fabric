# Dedicated Pool Deployment to Fabric

Convert approved source T-SQL stored-procedure logic into executable Spark SQL `%%sql` notebook cells before publication. Then create or resolve the target Lakehouse through Fabric REST, execute schema-only artifacts through Lakehouse-bound Livy, and publish the generated notebooks to the Fabric workspace without executing them.

## ⛔ CRITICAL: What NOT to Do

**These deployment patterns are EXPLICITLY FORBIDDEN and cause correctness/maintenance issues:**

1. ❌ **NEVER create "deployment notebooks" to hold table or view DDL**
   - Tables deploy via Livy: `POST /sessions/{id}/statements` with `{"kind":"sql","code":"CREATE TABLE..."}`
   - Views deploy via Livy: `POST /sessions/{id}/statements` with `{"kind":"sql","code":"CREATE VIEW..."}`
   - Creating notebooks like "01_Deploy_Tables.ipynb" or "02_Deploy_Views.ipynb" violates the deployment contract

2. ❌ **NEVER upload table/view SQL files via the Notebooks API**
   - `POST /workspaces/{id}/notebooks` is ONLY for stored procedures converted to notebooks
   - Schema objects (tables, views) are NOT notebooks — they are Spark SQL DDL executed via Livy

3. ❌ **NEVER wrap DDL in notebook magic (`%%sql`, `%%configure`) for deployment**
   - Livy payloads are pure Spark SQL: `{"kind":"sql","code":"CREATE TABLE dbo.FactSales (...)"}`
   - Notebook magic is only for interactive cells, not deployment automation

4. ❌ **NEVER create helper/utility notebooks for deployment orchestration**
   - Notebooks are converted stored procedures only
   - Deployment logic stays in CLI scripts (PowerShell/Python), not in workspace notebook items

**Before deployment, verify this checklist:**
- [ ] Zero notebooks created for tables (only Livy `CREATE TABLE` statements)
- [ ] Zero notebooks created for views (only Livy `CREATE VIEW` statements)
- [ ] One notebook per converted stored procedure (via `POST /notebooks` API)
- [ ] No "deployment helper" or "schema setup" notebooks in the workspace

## Generated Notebook Publication

Create or update each approved target Notebook component. An approved `1:1` component uses the exact source procedure name; approved `N:1` and `N:N` components use their approved target names and contain logic from multiple procedures according to the user-provided mapping. Every source procedure remains independently traceable, every notebook has an explicit default Lakehouse binding, and publication never invokes or uses the notebooks for orchestration.

## API Flow

**Defect #21 fix**: Use `scripts/dedicated_pool_runtime.py` as the maintained implementation for pagination, LRO handling, `kind: sql` Livy statement payloads, atomic manifest checkpoints, immutable run-context verification, schema readiness, orphan Notebook recovery, selectors, and capacity batches. **All helpers must accept caller-provided overrides** via command-line arguments or configuration (timeout values, retry limits, session configuration, headers). Never hardcode defaults that prevent caller customization.

**Defect #22 fix**: `await_lro` declares and enforces `max_poll_duration_seconds` (default 900s, configurable), `max_poll_attempts` (default 180, configurable), and `retry_after_seconds` (from the response header or default 5s). It accepts the legacy `deadline_seconds` and `max_polls` aliases for existing callers. Retryable HTTP failures (429, 500, 502, 503, 504) use bounded exponential backoff. Non-retryable failures (4xx except 429, terminal LRO states) fail immediately. The caller may inject a logger; all retry attempts and final timeout/failure are logged.

**Defect #27 fix**: Livy session recycling must distinguish retryable failures (HTTP 429, 500-504, transient network errors) from terminal failures (session dead, invalid credentials, quota exceeded). On retryable failure, wait (exponential backoff) and retry the statement with the same session. On terminal failure, close the session and create a new one. Never drop an active `idle` session on the first retryable error.

**Defect #28 fix**: Before creating or reusing a Livy session, validate Spark runtime version and library compatibility between the target Environment/Spark pool and generated artifacts. Check runtime version, required PySpark/Spark SQL features, and library dependencies. Block deployment when incompatibility detected.

Apply the skill-level `x-ms-fabric-skill: synapse-migration` telemetry header to every Fabric REST request and long-running-operation poll.
Persist all returned IDs through `record_checkpoint`; never copy them manually between commands.

1. Acquire a Fabric token for `https://api.fabric.microsoft.com`.
2. Resolve the workspace by display name.
3. List Lakehouses and resolve the target by display name.
4. **Defect #24 fix**: If absent and approved, create it with `POST /v1/workspaces/{workspaceId}/lakehouses`. After creation or resolution, **verify schema-enabled state** by checking lakehouse properties or attempting `CREATE SCHEMA IF NOT EXISTS <test_schema>` via Livy. Lakehouses without SQL Analytics Endpoint or schema support block deployment.
5. Handle synchronous `200`/`201` responses directly, accepting a documented empty success body without JSON parsing. When a success body is present, require a valid JSON object. For `202`, capture `Location` and `x-ms-operation-id`, honor `Retry-After`, and poll with a declared deadline until `Succeeded`, `Failed`, or `Cancelled`. Timeout, missing `Location`, terminal failure, malformed response, or exhausted bounded retries is a deployment failure and must be persisted; never poll indefinitely.
6. Verify the frozen `run-context.json`, then create or reuse the recorded Livy session bound to that exact workspace and Lakehouse. A changed target ID or artifact hash blocks mutation.
7. **Defect #23 fix**: Wait for the Livy session to become `idle` within a bounded deadline. **Submit artifacts in strict dependency order**: (a) schemas/tables (DDL), (b) views, (c) procedures-as-notebooks. Within each phase, follow manifest dependency order. Submit each raw schema-only Spark SQL object separately with payload `{"kind":"sql","code":"<statement>"}`; do not include notebook magic such as `%%sql`, and never submit all DDL as one batch. **Never submit procedures before their dependent tables/views are created and validated.** Record the object input hash, session/statement IDs, state, output hash, attempt, and sanitized error transactionally after each statement. A statement succeeds only when its state is `available` and `output.status` is `ok`. Treat `error`, `cancelled`, `dead`, timeout, missing output, or session termination as failure. Do not submit row inserts, CTAS materialization, DataFrame writes, or other data-loading statements.
8. **Defect #40 fix**: Before any Notebook create or update, verify `deployment-package.json` for every audited procedure:
   - **Required fields**: `projectionPath`, `projectionHash`, `artifacts[]` with `{ path, sha256 }`, `ledgerPath`, `ledgerHash`, verdict `ReadyForPublication`
   - **Hash verification sequence** (fail deployment on any mismatch):
     1. Recompute SHA-256 of `conversion-manifest-projection.json` file; compare with `projectionHash`
     2. Recompute SHA-256 of `source-block-ledger.json` file; compare with `ledgerHash`
     3. For each artifact in `artifacts[]`: recompute file SHA-256; compare with recorded `sha256`
     4. Recompute SHA-256 of `deployment-package.json` file; compare with `deploymentPackage.sha256` in mutable manifest
   - **Ledger disposition validation**: Every block must have deployable disposition (Converted, ApprovedExclusion, ManualReviewApproved). Block on Pending/Failed/ManualReviewRequired without recorded approval.
   - **Source coverage validation**: Sum all block byte spans; verify no gaps, no overlaps, complete source hash match (100% coverage).
   - **Never deploy with package drift** — hash mismatch or invalid verdict is terminal failure.
9. Compile each generated `.ipynb`: validate JSON/nbformat, the first-cell `%%configure` contract when parameters are present, parameter declarations, every `%%sql` cell, forbidden constructs, empty outputs, and Spark SQL parser compatibility.
10. Require all schema and metadata checkpoints to be `Succeeded` before resolving any Notebook. Resolve each approved target Notebook component by target component ID and verify its complete set of contributing source IDs. For `1:1`, require the display name to equal the exact discovered `sourceName`. For `N:1` and `N:N`, require the exact approved target display name and workspace; reject generated or unapproved names and placement. Create an empty Notebook only when the approved target mapping has no existing Notebook ID and no name collision exists. A collision blocks publication until an explicit target-name mapping is approved. Update content with `POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/updateDefinition` and this required body shape: `definition.format` is `ipynb`; the content part path is `notebook-content.ipynb`; its payload is the Base64-encoded notebook JSON; and `payloadType` is `InlineBase64`. For audited procedures, Base64-encode the exact packaged notebook bytes. **Defect #26 fix**: If create succeeds but update/readback fails, record the Notebook and operation IDs as `RecoveryRequired` in manifest with failure details, timestamp, and recovery options. **Never leave orphaned notebooks untracked.** Provide explicit recovery commands: (a) retry update with backoff, (b) delete orphan and recreate, (c) manual review. All recovery actions require recorded approval and must update manifest status atomically.
11. **Defect #25 fix**: Accept `200` or poll `202` as defined in step 5. Then perform **mandatory persisted readback** with `POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/getDefinition?format=ipynb` and body `{}`. Accept a direct `200`; for `202`, poll `Location`, then call `GET {Location}/result` after `Succeeded`. **Readback is not optional — deployment fails without it.**
12. **Defect #25 continued**: Locate the `notebook-content.ipynb` part, require `InlineBase64`, decode and parse it, and **validate binding correctness**: Compare canonical content with publish candidate and packaged content hash. Ignore only documented volatile metadata (kernel metadata, widget state); **never ignore** cells, sources, parameters, dependency binding, outputs, execution counts, or target naming. Verify the persisted Fabric item display name and workspace against the approved target component; for `1:1`, also verify the exact source procedure name. **Critically verify** `metadata.dependencies.lakehouse.default_lakehouse`, `default_lakehouse_workspace_id`, and `default_lakehouse_name` against the resolved target. Binding mismatch or missing lakehouse metadata is deployment failure.
13. Persist the stable source ID, source schema/name, target display name and Notebook ID, workspace/Lakehouse IDs, canonical content hash, package and ledger hashes, source coverage, operation ID/URL, status, attempts, timestamps, readback status/hash, approval evidence, and sanitized error in the manifest.
14. Close the Livy session.

Use the Fabric Spark consumption/authoring core documents for the current Livy endpoint and payload shape rather than duplicating version-sensitive API details here.

## Deployment Order

⚠️ **CRITICAL: Generated DDL files must be EXECUTED via Livy. Simply generating `.sql` files locally does NOT deploy anything to the Lakehouse.**

1. **Schemas and empty Delta tables** — **EXECUTE** via Livy using `POST /sessions/{id}/statements` with payload `{"kind":"sql","code":"CREATE TABLE IF NOT EXISTS..."}`. Read from generated `schema/*.sql` files, submit each statement separately, wait for `state: available` and `output.status: ok`.
   - ✅ Tables deployed when Livy confirms `ok` status
   - ❌ Tables NOT deployed if you only create local `.sql` files

2. **Non-materializing view definitions** — **EXECUTE** via Livy using `POST /sessions/{id}/statements` with payload `{"kind":"sql","code":"CREATE OR REPLACE VIEW..."}`. Read from generated `logic/*.sql` files, submit each statement separately.
   - Views are schema objects like tables and are NEVER converted to notebooks.
   - ✅ Views deployed when Livy confirms `ok` status
   - ❌ Views NOT deployed if you only create local `.sql` files

3. **Converted procedural logic as published Notebook items** — Create/update Fabric Notebooks via REST API. Only stored procedures become notebooks; publish `.ipynb` files from `notebooks/` directory using `POST /workspaces/{id}/notebooks` or `POST /notebooks/{id}/updateDefinition`.

**Critical distinction**: Views (step 2) and stored procedures (step 3) use completely different deployment methods. Views = Livy SQL execution (same as tables). Stored procedures = Notebook publication via REST API. Never convert a view to a notebook or publish a view via the Notebooks API.

**Validation checkpoint**: After steps 1-2, verify tables and views exist in Lakehouse by querying via Livy (`SHOW TABLES`, `SHOW VIEWS`). If objects don't exist, deployment failed.

Do not invoke generated notebooks or transformations as part of this skill.

## Idempotency and Recovery

- Check manifest status before submitting an artifact.
- Use `IF NOT EXISTS` and manifest checkpoints where appropriate, but compare the resulting target metadata with the expected schema after every create or no-op. A no-op against incompatible metadata is drift, not success.
- Bind each approved target component ID and its complete contributing source-ID set to exactly one target Notebook item ID. A source procedure may reference multiple target components and a target component may reference multiple procedures only when the approved mapping permits it. If the expected name belongs to another item or the mapped item has changed type/name/content, stop for artifact-specific replacement approval; do not create a duplicate or overwrite an unrelated item.
- Never replace an existing target schema/code artifact without recorded artifact-specific approval and a pre-update readback.
- On statement failure, capture state, output, and the affected object; stop dependent objects.
- Recreate an expired Livy session and resume from the first incomplete manifest item.
- Validate views through the primary Lakehouse metadata surface. When that surface does not expose views, use the maintained Spark-catalog fallback sequence `SHOW VIEWS IN <schema> LIKE <view>` followed by `DESCRIBE EXTENDED <schema>.<view>` and persist both results; do not infer view success from submission alone.
- Never call the Job Scheduler run endpoint, `notebookutils.notebook.run`, `%run`, or submit a generated notebook through Livy. Publication and readback are allowed; execution is not.
- Do not log access tokens, connection strings, or secrets.

**Defect #41 fix**: Recovery commands after partial failures must update manifest atomically:
- **Atomic manifest updates**: Use transactional write pattern: (1) load current manifest, (2) apply status update, (3) write to temp file, (4) atomic rename/replace original. Never update manifest in-place without backup.
- **Recovery command structure**: Every recovery action (retry update, delete orphan, manual review) must:
  1. Record pre-recovery manifest state (snapshot or hash)
  2. Execute the recovery operation
  3. Update manifest with new state: `RecoveryInProgress` → `RecoveryCompleted` or `RecoveryFailed`
  4. Verify post-recovery state and hash
  5. Record recovery timestamp, operation ID, and outcome
- **Recovery approval tracking**: All recovery actions require recorded approval (`RecoveryApproved` with timestamp, approver, and action description) before execution.
- **Never leave inconsistent state**: If recovery fails mid-operation, manifest must reflect `RecoveryFailed` state with exact failure point and rollback instructions — never leave undefined state.

## Completion Gate

Deployment completes only when all required manifest items have terminal success states, every Notebook has passed persisted readback and exact Lakehouse-binding checks, every audited procedure was published from a verified immutable package with 100% source-block coverage, and every behavior-changing object is `ManualReviewApproved`. Failed, skipped without `ApprovedExclusion`, unknown, review-required, unpackaged, or hash-mismatched items must be reported explicitly and block artifact readiness.
Deployment success means schema/code artifact readiness only; it does not establish data parity or production cutover readiness.
