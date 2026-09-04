# Dedicated Pool T-SQL Conversion

Convert extracted Synapse objects into Spark SQL artifacts for Fabric Lakehouse execution and generated Spark SQL Fabric notebooks for stored procedures. Keep the translated SQL approachable for customers familiar with Synapse Dedicated Pool T-SQL.

## Prerequisites: Gap Assessment and User Approval

⛔ **CRITICAL: Do NOT start conversion without these completed prerequisites:**

1. **Gap Assessment Complete**: User must have an approved `migration-gap-report.json` from `dedicated-pool-gap-assessment.md` that identifies:
   - Unsupported T-SQL features and compatibility issues
   - Migration blockers and risks per object
   - Approved dispositions for each gap

2. **User Approval Recorded**: User must explicitly approve:
   - Mapping strategy choice: `1:1` (one notebook per procedure), `N:1` (group related procedures), or `N:N` (complex mapping)
   - Target notebook names for ALL procedures
   - Workspace placement
   - Dependency grouping
   **Present options, wait for explicit approval, record approval timestamp and evidence in manifest.**

3. **Manifest Exists**: A `migration-manifest.json` must exist with:
   - Approval evidence (timestamp, approved strategy, approved mappings)
   - Source object inventory from discovery phase
   - Empty target component records ready to track conversion status

**If any prerequisite is missing, STOP and direct user to complete the missing phase first. Never assume approval or invent mappings.**

---

## Inputs and Outputs

**Inputs**
- Source SQL files or catalog definitions
- Object inventory, dependencies, and complexity tier
- **✅ Approved** `migration-gap-report.json` with accepted scope, procedure mapping strategy, versioned source-to-target relationships, workspace placement, and dispositions
- Target schema naming policy

**Outputs**
- `schema/*.sql`: idempotent Spark SQL Delta DDL
- `expected-schema.json`: converter-emitted target schema metadata derived directly from discovered source metadata
- `logic/*.sql`: reusable Spark SQL generated from non-procedural source logic
- `notebooks/*.ipynb`: Spark SQL Fabric notebook components defined by the approved `1:1`, `N:1`, or `N:N` procedure mapping
- `source/<sourceStableId>.sql`: immutable exact source evidence for each audited procedure
- `procedure-audit/`: source-block ledgers, bounded attempt records, generated run-specific scripts, conversion-manifest projection, and deployment package
- `migration-manifest.json`: source features/objects, approved target components, mapping cardinality, dependencies, tier, status, warnings, and validation cases

Generate artifacts only from discovered definitions, dependency metadata, the feature-wise risk assessment, and approved target-design dispositions. Do not infer, consolidate, split, or rename procedure notebook components beyond the approved versioned mapping.

## Conversion Rules

| Source pattern | Target pattern |
|---|---|
| `CREATE TABLE ... DISTRIBUTION` | `CREATE TABLE IF NOT EXISTS <schema>.<tableName> ... USING DELTA`; **preserve the source schema prefix** (e.g., `dbo.dimaccount` → `dbo.dimaccount`, not `dimaccount`). Omit MPP distribution and index clauses. **Defect #5 fix**: Emit nullable columns as `name TYPE` with **no nullability constraint** (omit both `NULL` and `NOT NULL`), and required columns as `name TYPE NOT NULL`. Never emit `TYPE NULL` — Spark SQL does not accept this syntax. |
| `CTAS` | Generate a non-executed Spark SQL conversion artifact; do not materialize data |
| `MERGE` | Generate non-executed Delta `MERGE INTO` logic with explicit match clauses |
| Temp tables | Spark SQL temporary views with unique names scoped to the notebook session |
| Stored procedure parameters | Externally overridable Fabric Notebook Activity parameters consumed through `%%configure` substitution in `%%sql` cells |
| Output parameters | Final Spark SQL result set with clearly named output columns |
| Transactions | Idempotent stages and Delta atomic writes; redesign multi-statement transaction assumptions |
| Cursors and loops | Set-based Spark SQL transformations; mark irreducible cases for redesign instead of falling back to PySpark |
| Dynamic SQL | Resolve bounded variants explicitly; mark unbounded generation as manual review |
| **Views** | **Views are schema objects like tables and MUST be deployed via Livy as SQL view definitions (deployment step 2). NEVER convert views to notebooks. Only stored procedures become notebooks (deployment step 3).** Generate `CREATE OR REPLACE VIEW` Spark SQL statements into `logic/*.sql`. Mark views requiring unsupported syntax features (e.g., indexed views) as `ManualReviewRequired` with a non-executed redesign artifact, but never convert them to notebooks. |

**Schema Prefix Preservation**: Every table reference in generated SQL—whether in DDL, DML, SELECT, JOIN, or procedure logic—must preserve the discovered source schema prefix (e.g., `dbo.dimaccount`, not `dimaccount`). Fabric Lakehouses support multiple schemas; dropping schema qualifiers causes `TABLE_OR_VIEW_NOT_FOUND` errors when tables exist in a non-default schema.

Preserve decimal precision, nullability, timestamps, identifiers, and source dependencies. **Defect #5 fix**: Spark SQL does not accept a `NULL` column constraint: **nullable columns must omit any nullability constraint** (write `name TYPE` with no `NULL` or `NOT NULL` token), and **required columns must explicitly include `NOT NULL`**. Never emit `TYPE NULL` (parser error). Never reverse this mapping or infer nullability from generated SQL. Record unsupported constraints instead of implying they are enforced.

**Defect #10 fix**: Do not reverse nullable semantics. When source metadata marks a column as nullable (`IsNullable = true`), generate `name TYPE` with **no constraint**. When source metadata marks a column as required (`IsNullable = false`), generate `name TYPE NOT NULL`.

**Defect #11 fix**: For `DECIMAL(p, s)` and `NUMERIC(p, s)` types, preserve exact precision `p` and scale `s` from source metadata. Emit `DECIMAL(p, s)` in generated DDL and record the complete `(typeName, precision, scale)` tuple in `expected-schema.json`. Validate precision and scale separately; a type match with different precision or scale is a validation failure.

Emit `expected-schema.json` during conversion, before writing DDL. Its root `objects` array contains one record per generated table or view. Every object record uses the exact keys `sourceStableId`, `targetIdentifier`, `objectType`, `columns`, and `dependencies`; do not substitute discovery-model aliases such as `sourceIdentifier` or `sourceType`. **The `targetIdentifier` must preserve the source schema prefix as a two-part name** (e.g., `"dbo.dimaccount"`, not `"dimaccount"`). Each column contains `ordinal`, `sourceName`, `targetName`, `sourceType`, `targetType`, `nullable`, `precision`, and `scale`; use JSON `null` when a numeric attribute does not apply. A character length remains part of source type text and is not numeric precision: for `NVARCHAR(100)` mapped to `STRING`, emit `sourceType: "NVARCHAR(100)"`, `targetType: "STRING"`, `precision: null`, and `scale: null`. Emit numeric precision and scale only when discovered numeric metadata supplies them, such as `19` and `4` for `DECIMAL(19,4)`. Preserve the discovered identifier spelling, column order, source type text, mapped target type text, nullability, precision, and scale exactly. Build this file from DacFx/catalog discovery records and the approved type mapping, never by parsing generated SQL. Treat it as an immutable deployment-package input and the sole expected-value source for local and deployed schema comparisons.

**Defect #3 & #4 fix**: Convert a procedure **only after** its discovered source object/column contracts resolve during the discovery phase. When a referenced table or view projection lacks a referenced column (example: `uspComplex_SalesExceptionScan` references `OrderDateKey`, `ProductKey`, `TotalProductCost` but `vwComplex_UnifiedSales` does not expose them), keep the exact source evidence, set only that procedure to `ManualReviewRequired` with the specific failing edges recorded in the gap assessment, and emit no notebook for it. Never fabricate the column, remove the reference, substitute a similarly named column, or silently redesign the procedure. Continue discovering and converting independently eligible sibling procedures according to their approved `1:1`, `N:1`, or `N:N` mappings.

**Critical Validation**: All generated SQL—whether in `schema/*.sql`, `logic/*.sql`, or notebook `%%sql` cells—must be **executable Spark SQL**, not wrapped Synapse T-SQL. The converter must **actually transform the SQL dialect**: remove Synapse-only syntax (`DISTRIBUTION`, `CLUSTERED COLUMNSTORE INDEX`, `HEAP`), add required Spark SQL syntax (`USING DELTA`, `IF NOT EXISTS`), and convert T-SQL functions to Spark SQL equivalents. **Do NOT simply wrap source T-SQL in notebook cells or SQL files**—this produces artifacts that fail at execution. Validate each generated statement against Spark SQL syntax rules before writing it. When a statement cannot be mechanically converted (e.g., uses unsupported features), mark the object `ManualReviewRequired` and emit a non-executed redesign artifact with clear conversion notes—never emit invalid SQL.

## Large-Procedure Source Audit

For every T3/T4 procedure and every source definition with at least 1,000 physical lines, apply [dedicated-pool-large-procedure-audit.md](dedicated-pool-large-procedure-audit.md). Also apply it below that threshold when complexity or whole-procedure review could conceal an omission. A run may apply the same audit to all procedures for consistency.

Generate a T-SQL-aware preprocessing script and verifier under the migration artifact directory. Partition the exact discovered source into deterministic, gap-free, non-overlapping source blocks; do not use an LLM, line count, semicolon split, or regular expression alone to choose boundaries. Map every converted target statement back to source block IDs and preserve source audit/logging statements by default.

Convert in bounded block batches and retry only failed retryable blocks. Declare `maxAttemptsPerBlock` before conversion, default it to three total attempts, and never regenerate successful blocks merely to repair another block. Packaging is blocked until byte coverage is exactly 100%, every block is `Converted`, `ApprovedExclusion`, or `ManualReviewApproved`, cross-block validation passes, and `deployment-package.json` has verdict `ReadyForPublication`.

## Stored-Procedure Parameter Contract

Fabric documents pipeline substitution inside a first-cell `%%configure`, but does not document arbitrary Python-variable interpolation into `%%sql`. Generated stored-procedure notebooks therefore use this bounded SQL-only contract:

1. Preserve the discovered source signature before conversion. For every supported source input, record its name, source type, mapped Spark SQL type, whether a source default exists, and the exact source default. Do not invent an interactive, sample, sentinel, or preview default.
2. Put bare `%%configure` (with no flags such as `-f`) in the first code cell. Under `conf`, map each supported source input exactly once to a unique `spark.synapseMigration.<procedure-key>.<parameter-key>` property whose value is an object containing `parameterName` and `defaultValue`; a scalar configuration value is invalid. Retain the procedure key even when a notebook has multiple contributing procedures so parameter namespaces cannot collide. `parameterName` is the externally overridable Fabric Notebook Activity base-parameter name. When the source declares a default, `defaultValue` must equal it without semantic coercion. When the source declares no default, emit JSON `null` as an absence marker, never as an executable fallback value.

    Build `conf` as one flat object: each fully qualified configuration key is a direct property of `conf`, never a nested procedure object or a map keyed only by parameter name. For example:

    ```json
    {
      "conf": {
        "spark.synapseMigration.dbo_usp_LoadFilteredCustomers.MinCustomerId": { "parameterName": "MinCustomerId", "defaultValue": 1000 },
        "spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RunDate": { "parameterName": "RunDate", "defaultValue": null }
      }
    }
    ```

3. Reference that property at every semantic use of the source input in later `%%sql` cells as `${spark.synapseMigration.<procedure-key>.<parameter-key>}` and immediately cast the substitution to the mapped Spark SQL type, for example `CAST(${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.MinCustomerId} AS BIGINT)`. Never replace a parameter reference with its default, a fixture value, a literal in a predicate, or a one-row temporary view containing constants.
    Preserve every discovered target, source, projection, join, and predicate in the translated transformation. Apply the approved type mapping consistently to literals and predicates: for example, when a source `BIT` column maps to Spark `BOOLEAN`, translate `IsActive = 1` to the semantically equivalent `IsActive = TRUE` rather than retaining an integer comparison or dropping the branch. After lexical validation, consume a mapped Boolean input through an immediate typed cast, for example `(CAST('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.IncludeInactive}' AS BOOLEAN) = TRUE OR IsActive = TRUE)`; do not replace that predicate cast with `LOWER(...) IN (...)` or another string comparison. Validate the generated transformation against the discovered procedure's statement structure and parameter-use inventory, not only by checking that parameter tokens occur somewhere in the notebook.
4. Treat a source input without a source default as required, not unsupported. Permit conversion and publication when the approved caller contract supplies it through a Fabric Pipeline Notebook activity or parent-notebook invocation. Before execution, the caller must reject a missing value and validate the supplied value against the source type; the generated notebook has no interactive fallback. Do not manufacture a sample, sentinel, empty-string, zero, or preview default merely to make the notebook runnable.
    When the generated notebook is also required to enforce the contract, emit an executable `%%sql` validation cell before the first mutating statement. Use `assert_true` against the same fully qualified substitutions to reject missing/blank required values and `try_cast(... AS <mapped-type>) IS NOT NULL` to reject invalid typed values. For every required string, assert the substitution itself is non-empty; for example, validate `RegionCode` with `assert_true('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RegionCode}' <> '', 'RegionCode is required and must be non-blank')`. A length check or comparison with a textual `null` sentinel does not replace this explicit empty-string rejection. Apply the exact `try_cast` rule to required dates as well as numeric and decimal values: for example, validate `RunDate` with `assert_true(try_cast('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RunDate}' AS DATE) IS NOT NULL, 'RunDate is required and must be DATE')`. Do not substitute `to_date`, `date_format`, or another permissive date conversion for the required DATE `try_cast` validation. Validate accepted Boolean lexical forms explicitly. Only after those assertions pass may transformation predicates consume the substitutions, with numeric, date, decimal, and Boolean substitutions immediately cast to their mapped Spark SQL types.
5. Permit automatic runtime substitution for integers, fixed-scale decimals, dates/timestamps, bounded strings, and booleans only when an approved caller contract validates the mapped source type **before starting the notebook** and the generated pre-mutation validation cell repeats every validation that remains parse-safe. Validate signed base-10 digits for integers, signed base-10 digits plus the declared scale for decimals, and parseable canonical values for dates/timestamps. A string is bounded only when its contract defines a business-specific character allow-list that excludes SQL delimiters and control characters; the default safe-string allow-list is ASCII letters, digits, spaces, underscore, hyphen, and period (`^[A-Za-z0-9 _.-]+$` for required strings and `^[A-Za-z0-9 _.-]*$` for optional non-null strings). The caller must reject apostrophes, quotes, semicolons, comment markers, backslashes, newlines, and any other out-of-allow-list character before notebook invocation. Do not rely on an `assert_true` inside the SQL cell as the security boundary: textual substitution occurs before Spark parses that assertion. Preserve accepted string content exactly; do not escape, strip, or normalize it. If the business value requires a character outside the approved allow-list, mark the procedure `ManualReviewRequired` and redesign parameter transport rather than widening the list ad hoc. Accept Boolean spellings `true`, `false`, `1`, and `0` case-insensitively when the approved contract declares those forms. Record every caller-side and notebook-side validation control in the manifest. Interactive execution uses only the exact source default. Direct execution with arbitrary overrides is unsupported.
6. Resolve identifiers only from discovered, allow-listed metadata and quote them during generation. Never accept table, schema, column, expression, clause, or arbitrary SQL text through a runtime parameter.
7. Mark unbounded or unvalidated strings and dates/timestamps, strings whose valid business values require SQL delimiters or other characters outside the approved allow-list, binary values, table-valued parameters, output parameters that cannot be represented as a final result set, and any parameter used to construct dynamic SQL as `ManualReviewRequired`. A nullable scalar default may be automatic only when `required`, `missingValueBehavior`, and pre-mutation validation distinguish an omitted required value from an explicit source `NULL` default. Do not publish manual-review notebooks until the manifest records per-object approval and the approved redesign.

Do not add a Python parameter cell, Python escaping helper, `spark.sql(...)` wrapper, or DataFrame transformation to bypass these limits. The manifest must record each source parameter, mapped type, configuration key, whether it is required, source-default presence and value, emitted `defaultValue`, approved caller, missing-value behavior, validation rule, and disposition. For every automatically substituted string, also record `stringAllowList` as the full anchored regular expression, `validationBoundary: "CallerBeforeNotebook"`, and `outOfAllowListDisposition: "ManualReviewRequired"`; absence of any of these fields blocks publication. A parameterized procedure is not converted when its SQL no longer consumes the runtime mapping, even if the emitted literal equals the source default.

The manifest schema deliberately differs from the notebook configuration schema. In every manifest `parameterMappings` entry, use `sourceParameter` for the discovered source parameter name; never emit `parameterName` there. `parameterName` is reserved for the object-valued `conf` entry inside `%%configure`. Preserve JSON `null` for both absent required defaults and explicit nullable defaults, and use `required` plus `missingValueBehavior` to distinguish them. For example:

```json
[
	{
		"sourceParameter": "RunDate",
		"sourceDefault": null,
		"defaultValue": null,
		"required": true,
		"approvedCaller": "FabricPipelineOrParentNotebook",
		"missingValueBehavior": "RejectBeforeMutation",
		"validationRule": "Required DATE",
		"configurationKey": "spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RunDate"
	},
	{
		"sourceParameter": "OptionalNamePrefix",
		"sourceDefault": null,
		"defaultValue": null,
		"required": false,
		"missingValueBehavior": "UseSourceNullDefault",
		"validationRule": "Nullable STRING",
		"configurationKey": "spark.synapseMigration.dbo_usp_LoadFilteredCustomers.OptionalNamePrefix"
	}
]
```

## Tier Strategy

- **T1**: deterministic conversion; syntax validation required.
- **T2**: deterministic conversion plus schema mapping and parser tests.
- **T3**: convert one object at a time with dependency context and targeted static tests.
- **T4**: produce a redesign note and testable skeleton; do not claim automatic parity.

## Artifact Requirements

- Make schema DDL idempotent.
- Generate `expected-schema.json` directly from discovered metadata before DDL generation; never reconstruct expected names, types, precision, scale, or nullability from generated SQL.
- Parameterize workspace, Lakehouse, schema, and environment values.
- Keep secrets out of generated artifacts.
- For an approved `1:1` mapping, preserve the exact discovered `sourceName` as both the local notebook basename (`<sourceName>.ipynb`) and published Fabric Notebook display name (`<sourceName>`), including case and punctuation. For `N:1` or `N:N`, use only the explicitly approved target component names and paths; never derive a rename or grouping automatically. Keep every contributing `sourceSchema`, `sourceName`, and stable ID separately in the manifest.
- Emit `migration-manifest.json` with source-object decisions and target-component records. Each procedure source decision must include its stable source ID, feature IDs, gap IDs, approved mapping cardinality, disposition, approval evidence, and all target component IDs. Each Notebook target component must include all contributing source IDs, approved display name/workspace, artifact path, dependencies, tier, parameter mappings, source-block/cell provenance, deployment state, hashes, warnings, errors, and timestamps. **Defect #29 fix**: For versioned deployments, include `manifestVersion` (integer, starts at 1), `approvalHash` (SHA-256 of approved mapping graph + dispositions + target names), `previousManifestVersion` (if exists), and `structuredDiff` (array of changes: added/removed/modified procedures, target name changes, disposition changes, new gaps, resolved gaps). On each re-approval or re-deployment, increment `manifestVersion`, recompute `approvalHash`, and generate structured diff from previous manifest. Preserve `sourceStableId`, `targetArtifact`, and notebook lifecycle fields on a `1:1` notebook record for backward compatibility. Use only these state transitions: `Discovered` -> `Assessed` -> `DesignApproved` -> `Converted` -> `PublishPending` -> `Published` -> `ReadbackValidated`, with `ManualReviewRequired`, `ManualReviewApproved`, `ApprovedExclusion`, `Deferred`, or `Failed` as explicit gated states.
- For audited procedures, add the source hash, ledger path/hash, block totals by disposition, source-byte coverage, retry policy, attempt-record root, deployment-package path/hash, and package verdict to the manifest target component. Retain ledgers and attempt evidence after publication.
- Include source-to-target type mappings and conversion warnings.
- Emit at least one executable Spark SQL transformation cell for every converted stored procedure across its approved target components. Each transformation cell must start with `%%sql` and record its contributing source/block IDs. The magic command selects Spark SQL; do not depend on a particular `metadata.language` value. A notebook that only embeds, comments, or displays the source T-SQL is not a conversion.
- Do not emit PySpark, Python `spark.sql(...)` wrappers, or DataFrame API transformation logic for stored procedures. If Spark SQL cannot preserve a procedural construct, emit the supported SQL stages plus a precise manual-review/redesign finding rather than changing languages.
- Keep the original procedure text in the discovery evidence, not in executable notebook cells. Reject generated notebooks containing `CREATE PROCEDURE`, `CREATE PROC`, or a `source_procedure` placeholder.
- Use valid nbformat v4.5-or-newer JSON with top-level `cells`, `metadata`, `nbformat: 4`, and `nbformat_minor >= 5`. Every cell ID must be unique and match `^[A-Za-z0-9_-]{1,64}$`. Every code cell must have `cell_type: code`, `metadata`, `source`, `outputs: []`, and `execution_count: null`; markdown cells must have `cell_type: markdown`, `metadata`, and `source`.
- Set `metadata.dependencies.lakehouse.default_lakehouse`, `default_lakehouse_workspace_id`, and `default_lakehouse_name` to the resolved target values. Do not substitute `metadata.trident.lakehouse` or another alternate path for this required binding. Include Fabric-compatible kernel/language metadata copied from a newly created target-workspace Spark notebook; do not invent kernel identifiers.
- Require this order: optional introductory markdown; first code cell `%%configure` when runtime parameters or session configuration are needed; then one or more `%%sql` transformation cells. Generated notebooks must contain no saved outputs.
- Validate notebook JSON, validate every `%%sql` cell against the target Spark parser, reject PySpark/DataFrame code, verify parameter mappings against the discovered source signature, reject hardcoded replacements for source inputs, and assert each notebook has executable translated Spark SQL logic before deployment.
- Publish each successful notebook as a Fabric Notebook item through a definition payload using `format: "ipynb"`, part path `notebook-content.ipynb`, and `payloadType: "InlineBase64"`.
- Do not execute generated transformations or notebooks, export source rows, or populate target tables.

## Completion Gate

Do not start conversion when either migration gap report or the procedure mapping approval is missing or unapproved. An object is deployable only when its discovery gaps have dispositions, its dependencies and referenced-column contracts are resolved, generated artifacts parse, its approved target notebooks contain executable translated `%%sql` logic rather than pasted source T-SQL or PySpark/DataFrame code, every supported source input remains externally overridable with its exact source default, and the manifest records `ManualReviewApproved` for every behavior-changing redesign. The mapping must cover every eligible procedure and target component without missing, orphan, duplicate, or unapproved relationships; blocked source decisions remain present with no generated component. An audited procedure also requires 100% verified source-block coverage across all mapped target components, no non-deployable block or exhausted failure, and a hash-verified `ReadyForPublication` package. Missing mappings, invented defaults, hardcoded parameter uses, invalid `TYPE NULL` DDL, acknowledged/skipped/unknown states, package drift, and unresolved reviews are not deployable. In the completion response, explicitly name Fabric Lakehouse as the target and report the resolved Lakehouse name along with artifact validation and the no-source-row boundary.
