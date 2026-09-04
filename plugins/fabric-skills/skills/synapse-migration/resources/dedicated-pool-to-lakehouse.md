# Dedicated SQL Pool Schema and Code to Fabric Lakehouse

Migrate Synapse Dedicated SQL Pool metadata and executable logic to Delta Lake through CLI, REST, and Livy APIs. Source table data is not migrated.

## Migration Phase Sequence (MANDATORY)

⛔ **You MUST complete these phases in strict order. Do NOT skip phases or assume approval:**

1. **Phase 1: Discovery** — Extract source metadata (tables, views, procedures, dependencies) per `dedicated-pool-discovery.md`
2. **Phase 1b: Gap Assessment (REQUIRED BEFORE CONVERSION)** — Run compatibility check per `dedicated-pool-gap-assessment.md` to identify blockers, unsupported features, and migration risks
3. **Phase 1c: User Approval (REQUIRED)** — Present mapping strategies (`1:1`, `N:1`, `N:N`), wait for explicit user approval, record approval evidence in manifest
4. **Phase 2: Conversion** — Generate artifacts ONLY after gap assessment and user approval are complete
5. **Phase 2b: Large-Procedure Audit** — Audit coverage for complex procedures per `dedicated-pool-large-procedure-audit.md`
6. **Phase 3: Deployment** — EXECUTE DDL via Livy, publish notebooks via REST per `dedicated-pool-deployment.md`
7. **Phase 4: Validation** — Verify deployment success per `dedicated-pool-validation.md`

**If the user has NOT completed gap assessment (Phase 1b) or NOT provided explicit approval (Phase 1c), STOP and guide them through those phases first. Never skip to conversion without these gates.**

---

## Execution Contract

- Use `scripts/Invoke-DedicatedPoolTool.ps1` for DACPAC discovery, including a DACPAC packaged in a ZIP, `scripts/validate_dedicated_pool_spark.py` for the target-parser gate, and `scripts/dedicated_pool_runtime.py` for Fabric pagination, bounded LRO handling, transactional checkpoints, freeze verification, and portfolio planning. SQL-project compilation executes arbitrary MSBuild targets and is disabled by default. Prefer building the project in an isolated trusted environment and passing its DACPAC. Use `-AllowTrustedProjectBuild` only after reviewing and explicitly trusting the project. Do not replace these maintained helpers with run-specific polling or manual JSON edits.
- Drive every migration run from dynamic source discovery and the approved compatibility report.
- Generate target artifacts only from the approved feature-risk assessment and target design. After discovery, compare `1:1`, `N:1`, and `N:N` stored-procedure notebook strategies against the projected workspace item footprint. Do not generate notebooks until the user provides and approves the complete source-to-target mapping, target names, dependency grouping, and workspace placement. Generated notebooks are published outputs and are not used to orchestrate migration.
- Treat the source Dedicated Pool as read-only. Never add sample or synthetic data or create/alter/drop source objects, permissions, or security principals.
- Do not execute source stored procedures or issue source DDL/DML. Limit source activity to metadata discovery and metadata-based validation. A requested source mutation belongs in a separate, explicitly scoped workflow and is never performed by this skill.
- Do not export, stage, copy, upload, shortcut, transfer, or load source table rows. Do not generate or execute a data-migration plan.
- Do not run row-count, aggregate, sample-hash, business-result, or other source-to-target data-equivalence queries. Data parity and cutover validation belong to a separately approved process outside this skill.
- Use SqlPackage or source catalog queries for discovery.
- Store converted schema and reusable logic as `.sql`, stored-procedure logic as `.ipynb`, and all object mappings in a machine-readable migration manifest.
- Use Fabric REST APIs for workspace and Lakehouse lifecycle operations.
- Use Fabric Livy sessions for schema execution and Fabric Notebook item definitions for stored-procedure deployment.
- Validate source-to-target schema mappings, generated artifact syntax, notebook definitions, dependencies, and publication status without reading or comparing table rows.
- Print structured status before and after every workflow step and for every object-level operation.

## Status Reporting Contract

Keep the user informed throughout execution; do not wait until a phase ends to report progress.

- Before each step, print: `[Phase X][Step Y/N][STARTED] action; next=expected operation`.
- After each object or restartable checkpoint, print: `[Phase X][i/N][COMPLETED|FAILED|SKIPPED] object; elapsed=...; rows=n/a; next=...`.
- For operations running longer than 30 seconds, print a heartbeat every 30-60 seconds with the current service state and elapsed time. Report state changes immediately. Do not repeatedly print an unchanged state more often than this interval.
- After each phase, print completed, failed, skipped, and pending counts plus the next phase or approval gate.
- On retry or recovery, print the failed operation, bounded retry action, checkpoint used, and whether duplicate writes are prevented.
- Persist the latest status and per-object result in the migration manifest so execution can resume safely.
- Never include passwords, access tokens, connection strings, or source row values in status output.

Example:

```text
[Phase 3][12/45][COMPLETED] migration_scale.dimcustomer; elapsed=18s; rows=n/a; next=migration_scale.dimproduct
```

## Phase Routing

| Phase | Action | Resource |
|---|---|---|
| 1 | Extract and classify source objects | [dedicated-pool-discovery.md](dedicated-pool-discovery.md) |
| 1b | Assess compatibility, workspace capacity, and procedure mapping options; obtain approval | [dedicated-pool-gap-assessment.md](dedicated-pool-gap-assessment.md) |
| 1c | Validate source object/column contracts and isolate affected procedures | [dedicated-pool-validation.md](dedicated-pool-validation.md) |
| 2 | Convert DDL and procedural logic | [dedicated-pool-conversion.md](dedicated-pool-conversion.md) |
| 2b | Audit large-procedure source-block coverage and package validated artifacts | [dedicated-pool-large-procedure-audit.md](dedicated-pool-large-procedure-audit.md) |
| 3 | Create the Lakehouse and deploy schema/code artifacts | [dedicated-pool-deployment.md](dedicated-pool-deployment.md) |
| 4 | Validate schema and generated artifacts | [dedicated-pool-validation.md](dedicated-pool-validation.md) |

## Required Inputs

- Synapse server and Dedicated Pool database
- Source authentication mode and metadata permissions (`CONNECT`, `VIEW DEFINITION`)
- Fabric workspace and target Lakehouse names
- Scope: selected schemas/code objects or the full schema/code workload

Discover workspace and item IDs through Fabric APIs. Ask only for values that cannot be discovered.

Use a source identity limited to database `CONNECT` and `VIEW DEFINITION` whenever possible. This schema/code-only workflow does not require `db_datareader`. If the supplied identity has broader rights, the read-only execution contract still applies.

## Ordered Workflow

### Local artifact fast path

When the request supplies the complete discovered procedure inventory, target binding, approval dispositions, and manifest contract, and explicitly forbids live source or Fabric calls:

1. Treat the supplied inventory as the completed discovery input only when it includes procedure-to-table/view referenced-column contracts and referenced projections. Validate those contracts before generation; retain each failing procedure as `ManualReviewRequired` with no notebook and continue only with independently eligible procedures. **Do not load** the discovery or gap-assessment resources unless an object or contract is ambiguous or unsupported.
2. Read [dedicated-pool-conversion.md](dedicated-pool-conversion.md), then generate every requested notebook and the manifest before expanding the narrative. Prefer one atomic generation pass so notebook hashes and manifest records stay consistent.
3. Do not load deployment guidance for a conversion-only request. When the user also requests publication/readback guidance, read [dedicated-pool-deployment.md](dedicated-pool-deployment.md) only after all local artifacts exist. Read [dedicated-pool-validation.md](dedicated-pool-validation.md) only when the requested report needs validation details not already present in the supplied contract. Do not perform those live operations in a local-only exercise.
4. Validate the local artifacts and return the phase summary. Do not defer the manifest until after the narrative. When conversion succeeds, explicitly state that the generated notebooks contain executable translated Spark SQL; do not describe them only as generated notebooks or transformation logic.

For live or partially specified migrations, use the full workflow below.

1. Authenticate Azure CLI and verify source and Fabric access.
2. Extract a DACPAC or query source catalog views.
3. Build an inventory, dependency graph, and T1-T4 complexity assessment.
4. Generate feature-wise `migration-gap-report.json` and `migration-gap-report.md` for all SQL Pool to Lakehouse capabilities. Report support level, likelihood, impact, overall risk, target pattern, and mapping cardinality. Use the discovered inventory and target workspace inventory to compare `1:1`, `N:1`, and `N:N` procedure-notebook mappings, projected item totals, headroom, names, dependency grouping, and workspace placement; then require the user to provide and explicitly approve the complete mapping.
4a. Before conversion, validate every discovered procedure-to-table/view object/column contract against the referenced object's discovered projection. Record each exact mismatch as an object-level finding. Mark only affected procedures `ManualReviewRequired`, generate no target notebook component for them, and keep unrelated procedures eligible when their own contracts and approvals pass. Do not invent a missing column, remove its reference, or redesign source logic implicitly.
5. Convert only the approved target design. Generate parameterized Spark SQL Fabric notebooks according to the approved procedure mapping. A `1:1` target retains the exact stored-procedure `sourceName`; `N:1` and `N:N` targets use explicitly approved names and collision-safe parameter namespaces. Preserve each procedure as an independent source decision and retain source-block-to-cell provenance across consolidated or shared notebooks. Apply the naming and bounded parameter contracts in [dedicated-pool-conversion.md](dedicated-pool-conversion.md). For every T3/T4 procedure, every definition with at least 1,000 physical lines, and any otherwise complex procedure, generate the deterministic block ledger, retry only failed blocks within the declared limit, verify complete source coverage, and build the immutable package defined in [dedicated-pool-large-procedure-audit.md](dedicated-pool-large-procedure-audit.md). Do not convert stored-procedure logic to PySpark or the DataFrame API.
5a. Run the maintained target Spark parser gate over every schema/view SQL artifact and generated notebook. Then freeze the complete approved artifact set and resolved datamart/workspace/Lakehouse IDs into `run-context.json`. Any parser failure, source-contract blocker, unresolved mapping, or post-freeze hash change blocks all Fabric mutation for that datamart.
6. Resolve or create the target Lakehouse through Fabric REST.
7. Create a Livy session bound to the Lakehouse.
8. Submit schema statements in dependency order and publish only approved, compiled stored-procedure notebooks without executing them. For audited procedures, verify all package hashes first and publish exactly the packaged notebook bytes; record each request, LRO result, target ID, and readback result in the manifest.
9. Compare source metadata with target schemas and validate generated code, source-block coverage, retry history, package integrity, dependencies, decoded persisted notebook definitions, exact Lakehouse bindings, and publication status.
10. Report completed, failed, skipped, and manual-review objects, including the disposition of every discovery gap and an explicit statement that data migration and data parity were not performed.

For multiple datamarts, require a portfolio JSON registry with one entry per datamart and unique workspace/Lakehouse target and artifact root. Record `capacityId`, workspace `region`, `capacityRegion`, current item count, planned notebook and non-notebook counts, reserved headroom, and the workspace item limit. Reject effective-region conflicts and projected item totals above the limit before mutation. Use `dedicated_pool_runtime.py --dry-run` with optional `--datamart`, `--wave`, or `--resume-failed` selectors before mutation. Evaluate workspace item limits per workspace, but batch remote Spark work by `capacityId` across workspaces that share capacity. A failed datamart becomes `Quarantined`; it does not change successful peer manifests or block independently promotable peers. Report aggregate elapsed and projected remaining seconds with success, failure, blocker, retry, and quarantine totals.

Apply the status reporting contract to all 10 steps. For batch operations, use the discovered object count as `N`; for service operations such as Livy startup, report service state and elapsed time until ready or failed.

Never seed an empty or small source pool to test migration. Report the discovered source as-is; use target-side fixtures or isolated local tests when conversion testing needs representative data.

## Approval Gates

Require explicit approval after the gap report and before conversion. The user must provide a procedure mapping strategy (`1:1`, `N:1`, or `N:N`) and the complete versioned source-to-target mapping, target names, workspace placement, and required operational headroom. Record per-object `ManualReviewApproved` decisions for every T4 redesign, unsupported parameter, behavior-changing conversion, consolidation/sharing decision, or approved exclusion before deployment. Also require artifact-specific approval before replacing target schema/code artifacts or source decommissioning. This skill cannot approve production cutover because it does not migrate or validate data.
