# Dedicated SQL Pool Schema and Code to Fabric Lakehouse

Migrate Synapse Dedicated SQL Pool metadata and executable logic to Delta Lake through CLI, REST, and Livy APIs. Source table data is not migrated.

## Execution Contract

- Drive every migration run from dynamic source discovery and the approved compatibility report.
- Generate one target Fabric notebook per discovered stored procedure; generated notebooks are published outputs and are not used to orchestrate migration.
- Treat the source Dedicated Pool as read-only. Never add sample or synthetic data or create/alter/drop source objects, permissions, or security principals.
- Do not execute source stored procedures or issue source DDL/DML. Limit source activity to metadata discovery and metadata-based validation unless the user separately gives explicit approval for a specific source mutation.
- Do not export, stage, copy, upload, shortcut, transfer, or load source table rows. Do not generate or execute a data-migration plan.
- Do not run row-count, aggregate, sample-hash, business-result, or other source-to-target data-equivalence queries. Data parity and cutover validation belong to a separately approved process outside this skill.
- Use SqlPackage or source catalog queries for discovery.
- Store converted schema and reusable logic as `.sql`/`.py`, stored-procedure logic as `.ipynb`, and all object mappings in a machine-readable migration manifest.
- Use Fabric REST APIs for workspace and Lakehouse lifecycle operations.
- Use Fabric Livy sessions for schema execution and Fabric Notebook item definitions for stored-procedure deployment.
- Validate source-to-target schema mappings, generated artifact syntax, notebook definitions, dependencies, and publication status without reading or comparing table rows.
- Print structured status before and after every workflow step and for every object-level operation.

## Status Reporting Contract

Keep the user informed throughout execution; do not wait until a phase ends to report progress.

- Before each step, print: `[Phase X][Step Y/N][STARTED] action; next=expected operation`.
- After each object or restartable checkpoint, print: `[Phase X][i/N][COMPLETED|FAILED|SKIPPED] object; elapsed=...; rows=... when known; next=...`.
- For operations running longer than 30 seconds, print a heartbeat every 30-60 seconds with the current service state and elapsed time. Report state changes immediately. Do not repeatedly print an unchanged state more often than this interval.
- After each phase, print completed, failed, skipped, and pending counts plus the next phase or approval gate.
- On retry or recovery, print the failed operation, bounded retry action, checkpoint used, and whether duplicate writes are prevented.
- Persist the latest status and per-object result in the migration manifest so execution can resume safely.
- Never include passwords, access tokens, connection strings, or source row values in status output.

Example:

```text
[Phase 3][12/45][COMPLETED] migration_scale.dimcustomer; elapsed=18s; rows=1000; next=migration_scale.dimproduct
```

## Phase Routing

| Phase | Action | Resource |
|---|---|---|
| 1 | Extract and classify source objects | [dedicated-pool-discovery.md](dedicated-pool-discovery.md) |
| 1b | Assess SQL Pool to Lakehouse compatibility gaps | [dedicated-pool-gap-assessment.md](dedicated-pool-gap-assessment.md) |
| 2 | Convert DDL and procedural logic | [dedicated-pool-conversion.md](dedicated-pool-conversion.md) |
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

1. Authenticate Azure CLI and verify source and Fabric access.
2. Extract a DACPAC or query source catalog views.
3. Build an inventory, dependency graph, and T1-T4 complexity assessment.
4. Generate `migration-gap-report.json` and `migration-gap-report.md` for all SQL Pool to Lakehouse compatibility gaps, present the report, and obtain approval to proceed.
5. Convert tables to Spark SQL Delta DDL and each stored procedure to a parameterized Spark SQL/PySpark Fabric notebook.
6. Resolve or create the target Lakehouse through Fabric REST.
7. Create a Livy session bound to the Lakehouse.
8. Submit schema statements in dependency order and publish compiled stored-procedure notebooks without executing them; record each result in the manifest.
9. Compare source metadata with target schemas and validate generated code, dependencies, notebook definitions, and publication status.
10. Report completed, failed, skipped, and manual-review objects, including the disposition of every discovery gap and an explicit statement that data migration and data parity were not performed.

Apply the status reporting contract to all 10 steps. For batch operations, use the discovered object count as `N`; for service operations such as Livy startup, report service state and elapsed time until ready or failed.

Never seed an empty or small source pool to test migration. Report the discovered source as-is; use target-side fixtures or isolated local tests when conversion testing needs representative data.

## Approval Gates

Require explicit approval after the gap report and before conversion. Also require approval before replacing target schema/code artifacts or source decommissioning. This skill cannot approve production cutover because it does not migrate or validate data.
