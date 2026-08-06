# Dedicated Pool to Lakehouse Gap Assessment

Generate a complete compatibility gap assessment after source discovery and before conversion. This is distinct from complexity scoring: complexity estimates conversion effort, while this report identifies behavior or capabilities that cannot move unchanged from a Synapse Dedicated SQL Pool to a Fabric Lakehouse.

## Required Outputs

Create both files in the migration working directory:

- `migration-gap-report.json`: machine-readable findings used by conversion, validation, and the migration manifest.
- `migration-gap-report.md`: customer-facing summary with every finding, affected objects, disposition, and decision required.

Never report only totals. Include one record per gap and list every affected source object. If a category has no findings, mark it `No gaps found` so report coverage is explicit.

## Required Gap Categories

| Category | Detect and report | Typical Lakehouse disposition |
|---|---|---|
| Physical design | `DISTRIBUTION`, partition clauses, clustered columnstore and other indexes, statistics, materialized views | Remove, redesign as Delta partitioning/optimization, or materialize through Spark |
| Relational enforcement | Primary/foreign/unique/check/default constraints, identity/sequence behavior, triggers | Document informational-only or application/notebook enforcement |
| Data types | Unsupported or behavior-changing SQL types, precision/scale limits, collation, timezone and string-length semantics | Map explicitly and record possible loss or normalization |
| T-SQL surface | Stored procedures, functions, dynamic SQL, cursors, loops, temp tables, table variables, transactions, TRY/CATCH, `MERGE`, `CTAS`, `PIVOT`, cross-database references | Convert, redesign, split into stages, or require manual review |
| Security | Users, roles, grants/denies, row-level security, dynamic data masking, column security, workload groups | Recreate with Fabric/OneLake controls or record unsupported behavior |
| Data movement | PolyBase/external tables, external data sources/file formats, linked services, credentials, COPY patterns | Inventory dependencies and mark row movement for a separate migration process; do not generate or execute data transfer |
| Operations | Workload management, resource classes, result-set caching, statistics maintenance, distribution skew, concurrency and transaction assumptions | Replace with Fabric capacity, Spark, and Delta operational patterns |
| Dependencies | Downstream views/procedures, pipelines, notebooks, reports, applications, three-part names, external consumers | Record owner and coordinated remediation/cutover action |
| Semantic behavior | Case sensitivity, collation, null ordering, implicit casts, date/time behavior, nondeterministic ordering | Record expected differences and static review criteria; runtime/data equivalence testing is outside this skill |

Discovery must query source metadata needed for these categories. Do not infer `No gaps found` merely because a DACPAC parser omitted an object class.

## Finding Schema

Each JSON finding must contain:

```json
{
  "id": "GAP-001",
  "category": "T-SQL surface",
  "severity": "High",
  "sourceFeature": "Multi-statement transaction",
  "affectedObjects": ["dbo.usp_LoadSales"],
  "evidence": ["BEGIN TRAN", "COMMIT"],
  "lakehouseGap": "No equivalent cross-table stored-procedure transaction boundary",
  "disposition": "Redesign as idempotent Delta stages",
  "automation": "ManualReview",
  "validationRequired": "Failure recovery and rerun test",
  "decisionOwner": "Data engineering owner",
  "status": "Open"
}
```

Allowed `automation` values are `Automatic`, `AutomaticWithReview`, `ManualReview`, and `NotMigrated`. Severity is `Critical`, `High`, `Medium`, or `Low` and must reflect business impact, not conversion difficulty alone.

## Markdown Report Structure

The customer-facing report must contain:

1. Source scope and extraction timestamp.
2. Executive summary with totals by category, severity, and automation status.
3. Detailed findings table with gap ID, affected objects, evidence, disposition, owner, and status.
4. Object coverage table showing every discovered object and its gap IDs, or `None`.
5. Unsupported or behavior-changing feature matrix.
6. Decisions and approvals required before conversion.
7. Proposed conversion waves and validation implications.
8. Explicit assumptions, metadata queries that failed, and assessment blind spots.

## Completion Gate

Do not begin conversion until:

- Every discovered object appears in the object coverage table.
- All required categories have an assessed status.
- Metadata-query failures and unknowns are visible in both reports.
- Every Critical or High finding has a disposition and decision owner.
- The customer has reviewed the report and approved proceeding, or explicitly approved a documented subset.

Record that approval and the accepted scope in `migration-manifest.json`. Discovery completion without these two gap-report files is a failed phase.