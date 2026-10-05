---
name: synapse-migration
description: "Converts Synapse workspaces to Fabric: Spark items, Lake Databases, Linked Services, and Dedicated SQL Pool schema/procedures for Lakehouse or Warehouse. During Pool-to-Lakehouse migration only, can migrate approved dependent procedure callers after notebook readiness. Excludes standalone pipelines and Warehouse administration. Triggers: Synapse workspace to Fabric, Dedicated SQL Pool to Lakehouse, Dedicated SQL Pool to Fabric Warehouse."
---

> **Telemetry — MANDATORY.** Every `api.fabric.microsoft.com` call must carry
> `x-ms-fabric-skill: synapse-migration` (`az rest`: `--headers "x-ms-fabric-skill=synapse-migration"`),
> including every LRO poll, `fabric_lro` and retry. Snippets omit it — add it anyway.

> **OFFLINE LAKEHOUSE ARTIFACT FAST PATH — DECIDE FIRST.** For a no-live-call request with complete supplied inputs and contracts, load only the [fast path](resources/dedicated-pool-to-lakehouse.md#offline-lakehouse-artifact-fast-path); do not load `migration-planning-reference.md`, `dedicated-pool-conversion.md`, or implementation scripts. Use one generator for artifacts and final-byte hashes, then one verifier. Do not inspect generated files or run post-pass spot checks. For every optional non-null source default, set `missingValueBehavior` to `UseSourceDefault` and restore that default before validation. Do not use this path for a Warehouse target; incomplete and large-procedure requests use their own routes.

> **CRITICAL NOTES**
> 1. To find workspace details (including its ID) from a workspace name: list all workspaces, then use JMESPath filtering.
> 2. To find item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace, then use JMESPath filtering.
> 3. Treat a source Dedicated SQL Pool as read-only. Do not run source DDL, DML, stored procedures, or create sample objects.
> 4. Dedicated Pool-to-Lakehouse data movement is out of scope. Migrate schema and executable code artifacts only; do not copy source rows or run row-level/business-result equivalence queries. The separate Warehouse route may move data only from a separately approved restored export copy under its own consent gate and restored-source contract.
> 5. For Dedicated Pool-to-Lakehouse requests, complete gap assessment, explicit mapping approval, manifest creation, conversion, deployment, and validation in order. Read [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) once as the router, then load only the current phase reference.
> 6. Stored-procedure `1:1`, `N:1`, and `N:N` mappings never apply to views. Views remain schema objects; procedures become traceable Spark SQL notebooks with executable `%%sql` transformation cells.
> 7. Dependent ADF/Synapse callers are conditional scope, not automatic scope. Discover them during assessment, require a separate complete-closure approval, and migrate them only after notebook readiness. Route standalone pipeline requests to `pipeline-migration`.
> 8. Before executing a specialized Dedicated Pool workflow, read the matching contract in [dedicated-pool-execution-contracts.md](references/dedicated-pool-execution-contracts.md). Its validation, hashing, request-body, resume, and completion-language requirements are mandatory.
> 9. Keep Lakehouse and Warehouse paths separate. If the target is unclear, ask before loading path-specific resources. Lakehouse conversion never moves source rows; Warehouse data migration requires its own explicit consent gate and restored-source contract.
> 10. For a Fabric Warehouse target, explicitly state that the complete `DISTRIBUTION` and `CLUSTERED COLUMNSTORE INDEX` declarations are removed because Fabric manages distribution, storage, and indexing; a bare mention of either source clause is insufficient.
> 11. Run setup DDL and CETAS only against the separately approved restored export copy after proving it is not the original production source.

# Synapse Analytics to Microsoft Fabric Migration

## Core Workflow

1. **Discover** the Synapse workspace and classify every source artifact.
2. **Choose targets** using [workload-routing.md](references/workload-routing.md).
3. **Assess gaps before conversion**, including runtime, library, connectivity, T-SQL, security, and capacity constraints.
4. **Obtain approval** for behavior-changing decisions, target placement, and every stored-procedure-to-notebook mapping.
5. **Create or update `migration-manifest.json`** and persist approval, per-object status, hashes, and checkpoints atomically.
6. **Convert and deploy in dependency order**, loading only the current phase resource.
7. **Validate persisted definitions and artifacts** without executing generated notebooks or pipelines unless a separately approved workflow explicitly requires execution.
8. **Report** completed, blocked, skipped, and pending objects without exposing credentials or sensitive values.

For full-workspace orchestration, read [migration-orchestrator.md](resources/migration-orchestrator.md). For a Dedicated Pool-to-Lakehouse migration, use [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) as the phase router. For a Warehouse target, load only the matching `dw-*` resource.

## Scope Routing

| Request | Action | Load |
|---|---|---|
| Full Synapse workspace migration | Run phased discovery and migration | [migration-orchestrator.md](resources/migration-orchestrator.md) |
| Dedicated SQL Pool schema/code to Lakehouse | Run the strict assessment-to-validation workflow. For guidance-only notebook publication, explicitly state: "The stored procedures were converted from T-SQL to Spark SQL before publication." | [dedicated-pool-to-lakehouse.md](resources/dedicated-pool-to-lakehouse.md) |
| Guidance-only Dedicated Pool incremental deployment hardening | Answer directly from the focused checklist; do not search scripts or load phase resources. State: "For columns with special characters, enable Delta `columnMapping` selectively and only with approval." | [dedicated-pool-execution-contracts.md](references/dedicated-pool-execution-contracts.md#guidance-only-incremental-deployment-hardening) |
| Large or complex stored procedure | For a complete offline contract, read only the audit resource once, use one run-local generator and one verifier, do not inspect implementation scripts or generated outputs, and stop after successful verification | [dedicated-pool-large-procedure-audit.md](resources/dedicated-pool-large-procedure-audit.md) |
| Spark pool | Convert configuration and libraries to a Fabric Environment | [spark-pool-migration.md](resources/spark-pool-migration.md) |
| Lake Database or HMS | Create or bind the target Lakehouse | [lake-database-migration.md](resources/lake-database-migration.md) or [external-hms-migration.md](resources/external-hms-migration.md) |
| Notebook or Spark Job Definition | Port code, bindings, parameters, and runtime settings | [spark-item-migration.md](resources/spark-item-migration.md) |
| Linked Service | Choose a Fabric Data Connection for external services or a OneLake Shortcut for ADLS Gen2/Blob | [connectivity-migration.md](resources/connectivity-migration.md) |
| Approved dependent procedure callers | Run the internal closure-preserving sub-flow after notebook readback | [dedicated-pool-dependent-pipelines.md](resources/dedicated-pool-dependent-pipelines.md) |
| Standalone pipeline migration | Delegate | `pipeline-migration` |
| Dedicated SQL Pool to Fabric Warehouse | Run the source extraction, DDL compatibility, approval, optional data, security, and validation route | [dw-source-and-extraction.md](resources/dw-source-and-extraction.md), then the matching `dw-*` phase resource |
| Standalone Fabric Warehouse administration | Delegate | `sqldw-cli` |
| Synapse Link | Use Fabric Mirroring; not covered here | — |

Always report the Lake Database/HMS phase. If none is discovered, mark it `NotApplicable (none discovered)` while retaining the required target Lakehouse binding.

## Load References On Demand

Do not preload all files. Load only the references needed for the current phase:

| Need | Reference |
|---|---|
| Routing, phase order, API audiences, quick examples, troubleshooting, or post-migration handoff | [workload-routing.md](references/workload-routing.md) |
| Dedicated Pool execution variants and response contracts | [dedicated-pool-execution-contracts.md](references/dedicated-pool-execution-contracts.md) |
| Dedicated Pool discovery | [dedicated-pool-discovery.md](resources/dedicated-pool-discovery.md) |
| Gap assessment and mapping approval | [dedicated-pool-gap-assessment.md](resources/dedicated-pool-gap-assessment.md) |
| Procedure conversion and notebook shape | [dedicated-pool-conversion.md](resources/dedicated-pool-conversion.md) |
| Schema/notebook deployment | [dedicated-pool-deployment.md](resources/dedicated-pool-deployment.md) |
| Dedicated Pool validation | [dedicated-pool-validation.md](resources/dedicated-pool-validation.md) |
| Runtime/library compatibility | [feature-parity.md](resources/feature-parity.md) and [library-compatibility.md](resources/library-compatibility.md) |
| `mssparkutils` and connector refactoring | [utility-api-mapping.md](resources/utility-api-mapping.md), [connector-refactoring.md](resources/connector-refactoring.md), and [code-patterns.md](resources/code-patterns.md) |
| Capacity planning | [capacity-sizing.md](resources/capacity-sizing.md) |
| Dedicated Pool-to-Warehouse source discovery and extraction | [dw-source-and-extraction.md](resources/dw-source-and-extraction.md) |
| Warehouse DDL compatibility and deployment | [dw-ddl-compatibility.md](resources/dw-ddl-compatibility.md) |
| Separately approved Warehouse data migration | [dw-data-migration.md](resources/dw-data-migration.md) |
| Warehouse security and validation | [dw-security-validation.md](resources/dw-security-validation.md) |
| Validation, reporting, and production readiness | [validation-testing.md](resources/validation-testing.md), [migration-report.md](resources/migration-report.md), and [security-governance.md](resources/security-governance.md) |

Use [COMMON-CLI.md](../../common/COMMON-CLI.md) only for shared authentication and `az rest` mechanics not already covered by the phase resource. Use [COMMON-CORE.md](../../common/COMMON-CORE.md) only for shared Fabric REST patterns.

## Must

- Preserve every stored-procedure input contract, source default, source decision, and approved target mapping.
- Block conversion until gap dispositions, notebook names, dependency grouping, and target workspace placement are explicitly approved.
- Use SqlPackage/DMVs for source discovery, Fabric REST for item management, and Fabric Livy statements for Lakehouse schema and Delta execution.
- Run the maintained validators required by the selected execution contract; never replace them with ad hoc JSON or cell-shape checks.
- Choose the Lakehouse or Warehouse target before loading implementation resources; never apply Warehouse data-movement rules to Lakehouse artifact conversion.
- Before persisting any dependent-pipeline source definition, recursively inspect it for secret-bearing or uncertain properties; block the complete selected closure without writing the artifact or mutating a target when any are found.
- In every dependent-pipeline response, including guidance-only and pre-approval explanations, state: "Use a `TridentNotebook` activity with exact target identities `typeProperties.notebookId` and `typeProperties.workspaceId`, and pass inputs through `typeProperties.notebookParameters`." Then state: "After deployment, read back each pipeline with `POST /v1/workspaces/{workspaceId}/items/{dataPipelineId}/getDefinition` and validate its canonical hash and structural bindings."
- For every Linked Service response, first state both replacement classes: Fabric Data Connections for external databases/services and OneLake Shortcuts for ADLS Gen2/Blob storage; then identify which class applies.
- Replace `mssparkutils` with `notebookutils`, Linked Services with the correct Fabric connection class, and `spark.read.synapsesql()` with a supported OneLake or JDBC pattern.
- Externalize workspace and item IDs through parameters or Variable Libraries.
- Keep phase status concise, emit bounded heartbeats for long operations, and persist per-object evidence in the manifest.

## Prefer

- OneLake Shortcuts over copying data.
- Fabric Environments for reproducible libraries and Spark settings.
- Incremental, dependency-ordered migration over big-bang cutover.
- Parameterized notebooks and Variable Libraries for environment promotion.
- Lakehouse SQL Endpoint for compatible Serverless SQL Pool read workloads.

## Avoid

- Do not execute generated notebooks or pipelines as part of artifact migration.
- Do not broaden a selected dependent-pipeline closure or route that internal sub-flow to `pipeline-migration`.
- Do not use `sqlcmd` against the target Fabric Warehouse; use the registered SQL endpoint tooling required by the Warehouse resource.
- Do not preserve Synapse distribution/storage hints, PolyBase DDL, Linked Service connection strings, or pool-level library installation patterns verbatim.
- Do not use target notebooks to orchestrate the migration itself.
- Do not hardcode workspace IDs, item IDs, credentials, connection strings, or environment-specific paths.

## Examples

**Prompt:** "Migrate this Dedicated SQL Pool DACPAC to a Fabric Lakehouse and convert the procedures."

**Response behavior:** Assess gaps first, present and obtain approval for the complete procedure-to-notebook mapping and workspace placement, create the manifest, convert approved schema/code artifacts without moving source rows, validate persisted definitions, and report the resolved Lakehouse and artifact evidence.

**Prompt:** "Migrate this ADF pipeline to Fabric."

**Response behavior:** Route to `pipeline-migration`. Keep it here only when the pipeline is an explicitly approved dependent caller discovered inside an active Dedicated Pool-to-Lakehouse migration.

**Prompt:** "Migrate this Dedicated SQL Pool to Fabric Warehouse."

**Response behavior:** Keep this inside `synapse-migration`, assess DDL compatibility, remove unsupported distribution and columnstore declarations, obtain provisioning consent, and ask separately before any restored-source data migration.

For code transformations and edge cases, load [workload-routing.md](references/workload-routing.md) and the phase-specific resource rather than expanding the main instructions.
