# Dedicated Pool to Lakehouse Gap Assessment

Generate a complete, feature-wise migration risk assessment after source discovery and before target design or conversion. This is distinct from complexity scoring: complexity estimates implementation effort, while this report identifies the business and technical risk of moving each Dedicated SQL Pool feature to a Fabric Lakehouse.

Non-procedure features and artifacts do not have a default one-to-one mapping: they can be retired (`1:0`), translated directly (`1:1`), decomposed into multiple artifacts (`1:N`), consolidated with other source objects (`N:1`), redesigned across several artifacts (`N:M`), or deferred pending a decision.

Stored-procedure notebook cardinality is a required post-discovery customer decision. After scanning the DACPAC and supplemental catalogs, assess and present `1:1` (one procedure to one notebook), `N:1` (multiple procedures consolidated into one notebook), and `N:N` (multiple procedures redesigned across multiple shared notebooks). The user must provide the complete source-to-target mapping after reviewing the assessment. Do not select a strategy or infer consolidation from procedure count alone, and do not generate notebooks until the customer approves the strategy, every source-to-target relationship, target names, workspace placement, and any behavior-changing consolidation or sharing.

## Required Outputs

Create both files in the migration working directory:

- `migration-gap-report.json`: machine-readable findings used by conversion, validation, and the migration manifest.
- `migration-gap-report.md`: customer-facing summary with every finding, affected objects, disposition, and decision required.

Never report only totals. Include a feature assessment for every discovered feature family, plus detailed findings for material gaps. List every affected source object and proposed target component. If a category has no findings, mark it `No gaps found` so report coverage is explicit.

## Feature-Wise Risk Model

Assess risk by feature before proposing object mappings. Each feature assessment must contain:

- feature family and detected source capability
- affected source objects and evidence
- business usage or dependency context, including `Unknown` when metadata cannot establish it
- Lakehouse support level: `Native`, `EquivalentWithChange`, `RedesignRequired`, `Unsupported`, or `Unknown`
- mapping cardinality: `1:0`, `1:1`, `1:N`, `N:1`, `N:M`, or `Deferred`
- likelihood and impact: `Low`, `Medium`, `High`, or `Critical`
- overall risk: `Low`, `Medium`, `High`, or `Critical`, with rationale
- proposed target pattern and target components; leave target components empty for `Deferred`
- migration action, validation implications, owner, decision status, and linked gap IDs

Do not reduce risk merely because syntax conversion is automatable. For example, distribution, transactions, security, workload management, collation, and downstream dependencies can create High or Critical migration risk even when the source SQL parses successfully.

Keep likelihood, impact, and overall risk as separate fields in both output formats. Do not collapse likelihood or impact into a single severity/risk value.

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

## Feature Assessment Schema

The JSON root must include `featureAssessments`, `findings`, `objectCoverage`, `procedureMappingAssessment`, `summary`, `blindSpots`, and `approvals`. A feature assessment uses this shape:

```json
{
  "featureId": "FEAT-001",
  "category": "Physical design",
  "sourceFeature": "Hash distribution",
  "affectedObjects": ["sales.FactSale"],
  "evidence": ["DISTRIBUTION = HASH(CustomerKey)"],
  "businessContext": "Large fact table; downstream concurrency requirement unknown",
  "lakehouseSupport": "RedesignRequired",
  "mappingCardinality": "1:N",
  "likelihood": "High",
  "impact": "High",
  "risk": "High",
  "riskRationale": "MPP distribution semantics do not carry to Delta and performance depends on a new partition/optimization design",
  "proposedTargetPattern": "Delta table plus partitioning, optimize, and maintenance policy",
  "targetComponents": ["Delta table", "maintenance notebook or job"],
  "migrationAction": "Benchmark and approve the physical redesign",
  "validationImplications": ["schema validation", "separate performance validation"],
  "decisionOwner": "Data platform owner",
  "decisionStatus": "Open",
  "gapIds": ["GAP-001"]
}
```

## Procedure Mapping and Workspace Capacity Assessment

Build `procedureMappingAssessment` from the complete discovered procedure inventory and the proposed target design. Include:

- `discoveredProcedureCount` and stable IDs for every procedure
- candidate rows for `1:1`, `N:1`, and `N:N`, including rationale, exact proposed source-to-target relationships, distinct target notebook count, naming policy, dependency grouping, operational tradeoffs, and validation impact
- each candidate target workspace, its current Fabric/Power BI item count, planned non-notebook items, reserved operational headroom, projected notebook items, and projected total items
- the current documented workspace item limit used for the assessment and its Microsoft Learn source URL
- the workspace effective region, assigned capacity ID and region, evidence source and timestamp; conflicting workspace/capacity regions are blocking evidence and must not be resolved by assumption (**Defect #20 fix**: When workspace `region` conflicts with capacity `region`, emit a clear blocking error and require resolution — do NOT assume the workspace inherits the capacity region or vice versa. Validate both regions match before proceeding.)
- **Defect #19 fix**: Include assessment `generatedTimestamp` and post-deployment `lastDeploymentTimestamp` to detect stale reports. Assessment/gap reports become stale after deployment changes. Re-run assessment after every deployment phase to refresh workspace discovery, item counts, and generated-vs-deployed comparisons. Mark reports as `STALE` when `lastDeploymentTimestamp > generatedTimestamp`.
- `Fits`, `ExceedsLimit`, or `Unknown` for every candidate workspace; use `Unknown` when workspace inventory or planned non-notebook item counts cannot be established
- the recommended strategy and workspace partition, clearly labeled as a proposal rather than an approval
- `decisionStatus`, approver, timestamp, approved strategy, approved mapping version/hash, and approval evidence

Calculate projected notebook items from the actual mapping, not a generic multiplier:

- `1:1`: discovered procedure count
- `N:1`: count of distinct target notebooks in the user-provided consolidation mapping
- `N:N`: count of distinct target notebook components in the proposed many-to-many mapping

Calculate each projected workspace total as current items plus planned new non-notebook items plus notebooks assigned to that workspace. The documented maximum is 1,000 Fabric and Power BI items per workspace, including parent and child items. Preserve explicit headroom for pipelines, environments, semantic models, reports, deployment artifacts, and future operations rather than planning to exactly 1,000. Also report item-specific limits that affect the proposed topology. If live target discovery is unavailable, ask the customer for current item counts and required headroom; do not treat missing values as zero.

`N:1` and `N:N` require approved target names because source-name identity is no longer sufficient. A target notebook record must list all contributing source stable IDs; each source decision must list all target component IDs. Consolidated or shared mappings must define dependency order, parameter namespace ownership, output boundaries, failure/restart behavior, and source-block-to-cell traceability. Cardinality changes structure only; they do not relax source coverage, parser, parameter, approval, package-integrity, or no-source-row requirements.

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

`affectedObjects` is always a JSON array of non-empty stable-ID strings. Serialize a finding with no affected object as `[]`; never emit `null`, omit the property, or serialize an empty pipeline value as `[null]`. Validate this invariant before committing the canonical manifest or regenerating either report.

Each affected object must also have an object-level decision in `migration-manifest.json`: `AutomaticApproved`, `ManualReviewRequired`, `ManualReviewApproved`, or `ApprovedExclusion`. Store the approver, timestamp, gap IDs, approved disposition, scope, and approved mapping cardinality. The manifest may contain multiple target records for one source, one target record referencing multiple sources, or no target record for an approved non-procedure retirement/exclusion. Every stored procedure must retain one source decision and all approved target Notebook component IDs; every target Notebook must list all contributing procedure stable IDs. A report-wide approval does not approve the procedure mapping strategy, individual T4 redesigns, unsupported parameters, behavior-changing conversions, sharing, decompositions, consolidations, or exclusions.

A source-contract mismatch is an object-level finding whose evidence names the referencing procedure, referenced table or view, referenced columns, discovered projection, and exact missing-column set. Set the affected procedure to `ManualReviewRequired`, with no generated target component, until the source contract or an explicit redesign is approved. Do not invent columns, delete references, or silently rewrite procedure semantics. Scope this disposition to procedures that depend on the failing contract; eligible sibling procedures retain their independent decisions and mappings.

## Markdown Report Structure

The customer-facing report must contain:

1. Source scope and extraction timestamp.
2. Executive risk summary with totals by category, support level, risk, mapping cardinality, and decision status.
3. Procedure mapping and workspace-capacity matrix comparing `1:1`, `N:1`, and `N:N`, projected notebook/workspace item totals, headroom, proposed workspace partitions, tradeoffs, and decision status.
4. Feature-wise risk matrix with evidence, affected objects, separate likelihood and impact columns, overall risk and rationale, proposed target pattern, cardinality, owner, and decision.
5. Detailed findings table with gap ID, affected objects, evidence, disposition, owner, and status.
6. Object coverage table showing every discovered object, feature IDs, gap IDs, and proposed mapping cardinality; use `None` or `Deferred` explicitly.
7. Unsupported or behavior-changing feature matrix.
8. Decisions and approvals required before target design or conversion.
9. Proposed migration waves and validation implications.
10. Explicit assumptions, metadata queries that failed, and assessment blind spots.

## Completion Gate

Do not begin conversion until:

- Every discovered object appears in the object coverage table.
- Every detected feature appears in the feature-wise risk matrix, including supported features with Low risk.
- Every feature assessment reports likelihood and impact separately from overall risk in both JSON and Markdown.
- All required categories have an assessed status.
- Metadata-query failures and unknowns are visible in both reports.
- Every Critical or High finding has a disposition and decision owner.
- Every non-`1:1` or `Deferred` non-procedure design has an explicit owner and approval status; no target artifact is generated from an unapproved proposed mapping.
- The procedure mapping assessment covers `1:1`, `N:1`, and `N:N`; its workspace-item calculations use discovered procedure counts, the user-provided mapping, and known target inventory rather than assumptions.
- The customer has explicitly approved one procedure mapping strategy, a versioned complete source-to-target relationship set, target notebook names, and workspace placement. `Unknown`, proposed, or partially mapped strategies block conversion.
- Every target workspace is projected to remain within the documented item limit with explicit operational headroom. An over-limit or unknown-capacity workspace blocks conversion until the design is repartitioned or the missing inventory is supplied.
- Every eligible stored procedure appears in at least one approved target Notebook mapping, every blocked procedure remains an explicit source decision with no target component, and every target Notebook identifies at least one contributing procedure. Unsupported logic remains `ManualReviewRequired` regardless of cardinality.
- Every procedure-to-table/view source-contract edge is `Resolved` or is represented by an exact object-level finding. A procedure with `MissingReferencedColumn`, an unresolved referenced object, or an unknown projection remains `ManualReviewRequired` and has no generated target component; the finding does not block unrelated procedures whose contracts resolve.
- The customer has reviewed the report and approved proceeding, or explicitly approved a documented subset.
- Every excluded object is `ApprovedExclusion`, and every object requiring redesign remains `ManualReviewRequired` until its exact target behavior is approved.

Record that approval and the accepted scope in `migration-manifest.json`. Discovery completion without these two gap-report files is a failed phase.