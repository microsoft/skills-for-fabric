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

Before writing generated artifacts, build one in-memory conversion contract per source object and use that same contract for the notebook, source evidence, and manifest. Fail artifact generation unless all of these checks pass:

- Write the exact immutable source bytes to the requested `source/<sourceStableId>.sql` path before building an audit ledger or deployment package. Preserve the complete stable ID in the file name and include the source artifact in package hashes and evidence.
- Preserve every approved source parameter exactly once in the notebook bridge and `migration-manifest.json`; do not abbreviate or independently reconstruct mappings for either artifact.
- For every optional non-null parameter, restore its declared source default when the runtime value is missing or `None` before lexical/type validation. This is a generic rule for every declared default, including `@MinCustomerId BIGINT = 1000` and `@BatchId BIGINT = 42`.
- Copy the complete approved parameter contract into each manifest mapping, including source and target names and types, default, requiredness, caller, missing-value behavior, validation rule, allow-list boundary, null-token handling, and manual-review fallback when applicable.
- Verify that source-parameter, bridge-parameter, `spark.conf.set`, and manifest-mapping cardinalities are equal before writing files. A missing, duplicate, or shortened mapping blocks artifact generation.

| Source pattern | Target pattern |
|---|---|
| `CREATE TABLE ... DISTRIBUTION` | `CREATE TABLE IF NOT EXISTS <schema>.<tableName> ... USING DELTA`; **preserve the source schema prefix** (e.g., `dbo.dimaccount` → `dbo.dimaccount`, not `dimaccount`). Omit MPP distribution and index clauses. **Defect #5 fix**: Emit nullable columns as `name TYPE` with **no nullability constraint** (omit both `NULL` and `NOT NULL`), and required columns as `name TYPE NOT NULL`. Never emit `TYPE NULL` — Spark SQL does not accept this syntax. |
| `CTAS` | Generate a non-executed Spark SQL conversion artifact; do not materialize data |
| `MERGE` | Generate non-executed Delta `MERGE INTO` logic with explicit match clauses |
| Temp tables | Spark SQL temporary views with unique names scoped to the notebook session |
| Stored procedure parameters | Externally overridable Fabric Notebook Activity parameters declared in a tagged parameter cell, validated by a Python bridge, and consumed through scalar Spark-conf substitution in `%%sql` cells |
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

Fabric Notebook activities inject base parameters into a code cell tagged `parameters`. When a generated stored-procedure notebook declares parameters, that tagged parameter cell is the first code cell and the validation-only Python bridge is the second code cell. Put `import re` and any other permitted validation import at the start of that same second bridge cell; never emit a separate import-only code cell between the parameter cell and bridge. Serialize the first cell with exact JSON metadata `"metadata": {"tags": ["parameters"]}`. A generic code-cell helper must accept and preserve this metadata rather than hardcoding `"metadata": {}`. Before an atomic generator writes any artifact, assert that the candidate notebook's first cell is a code cell and its `metadata.tags` value is exactly `["parameters"]`. This pre-write assertion supplements rather than replaces the maintained notebook validator. Every later code cell starts with exact `%%sql`; do not add later Python setup, normalization, display, or exit cells. A parameterless notebook starts directly with an exact `%%sql` code cell and has no parameter bridge.

Do not build object-valued `%%configure.conf` mappings. Use the tagged parameter cell and scalar bridge described below.

For an optional SQL `NULL` default, normalize and transport the declared parameter itself; never introduce an alias such as `normalized_optional_name_prefix`:

```python
import re

if OptionalNamePrefix == "::SYNAPSE_MIGRATION_NULL::":
	raise ValueError("reserved transport token")
if OptionalNamePrefix is not None and re.fullmatch(
	r"[A-Za-z0-9 _.-]*", str(OptionalNamePrefix)
) is None:
	raise ValueError("OptionalNamePrefix contains unsupported characters")
if OptionalNamePrefix is None:
	OptionalNamePrefix = "::SYNAPSE_MIGRATION_NULL::"
spark.conf.set(
	"spark.synapseMigration.dbo_usp_LoadFilteredCustomers.OptionalNamePrefix",
	str(OptionalNamePrefix),
)
```

1. Preserve the discovered source signature before conversion. For every supported source input, record its name, source type, mapped Spark SQL type, whether a source default exists, and the exact source default. Do not invent an interactive, sample, sentinel, or preview default.
2. Emit one Python code cell tagged `parameters`. Define each source input exactly once as a top-level variable whose name exactly matches the Fabric Notebook Activity base parameter. Preserve an exact source default; use Python `None` when a required source input has no default, so interactive execution fails rather than inventing a value. Do not emit object-valued `{parameterName, defaultValue}` entries under `%%configure.conf`: some Fabric pipeline startup paths parse `conf` as scalar Spark properties and reject those objects before the notebook starts.
3. Immediately after the parameter cell, emit one Python bridge cell. It may import only validation helpers and must reject missing and lexically invalid values with direct `if <reject-condition>: raise ...` guards before transport. Inline validation leaves the original value unchanged. The only permitted reassignments are replacing Python `None` with an optional parameter's exact non-null source default and the documented, collision-guarded normalization of Python `None` to the reserved SQL-null token; both must assign back to the exact declared parameter variable. Do not use `assert`, helper-based validation, or general parameter reassignment. After validation, emit exactly one direct call per declared parameter in this form: `spark.conf.set("spark.synapseMigration.<procedure-key>.<parameter-key>", str(<parameter-key>))`. Derive `<procedure-key>` from the complete discovered two-part source identifier by joining the exact source schema and procedure name with `_`; for example, `dbo.usp_LoadCustomer` becomes `dbo_usp_LoadCustomer`, never `usp_LoadCustomer`. Before generating any notebook, compute this key for every discovered procedure in the approved mapping. If two distinct two-part identifiers produce the same key, block every affected mapping for explicit redesign; never generate either notebook, invent an alias, or continue with the colliding namespace. For example, `a_b.c` and `a.b_c` both produce `a_b_c` and must be blocked. Record the source identifier, derived key, and collision set in the manifest. Use the preflight-approved procedure key consistently in every transport and SQL-substitution reference for the notebook. The key must be a literal string, and the scalar value expression must be exactly `str(<parameter-key>)`, directly referencing that declared parameter. Do not hide calls behind a helper, loop, dynamic key, formatted key, mapping, alias, pre-stringified variable, or unrelated constant. Do not hide validation behind those constructs either. For example, reject a required integer with `if BatchId is None: raise ValueError(...)` followed by `if re.fullmatch(r"[+-]?[0-9]+", str(BatchId)) is None: raise ValueError(...)`, then call `spark.conf.set("spark.synapseMigration.dbo_usp_LoadFilteredCustomers.BatchId", str(BatchId))`. For an optional SQL `NULL` default, assign the reserved scalar token to the declared parameter itself before its direct call. For a required input, reject Python `None`. For an optional input whose exact source default is non-null, replace Python `None` with that default before validation. For an optional input whose exact source default is SQL `NULL`, encode Python `None` as `::SYNAPSE_MIGRATION_NULL::`; reject that token as a caller-supplied string value using exact equality in a direct rejecting guard. Never pass Python `None` to `spark.conf.set`. This bridge is parameter transport, not transformation logic: it must not call `spark.sql`, read or write data, create DataFrames, or alter the generated SQL.
   For first-pass compatibility with the maintained AST gate, keep required-null and required-blank checks as separate direct guards. Express the required-blank guard exactly as `if not str(<parameter>).strip(): raise ValueError(...)`; do not rewrite it as `str(<parameter>).strip() == ""`. Express lexical checks with direct two-positional-argument `re.fullmatch` calls rather than `in`/`not in` membership tests, and never pass flags or keyword arguments to `re.fullmatch`. For case-insensitive Boolean validation, use `re.fullmatch(r"(?i:true|false|1|0)", str(<parameter>))`. Use `[0-9]` character classes instead of shorthand escapes, and restore an optional non-null source default before its lexical guard. Place all guards and permitted assignments before the first transport call, followed only by the contiguous `spark.conf.set` calls.
   Use these canonical maintained lexical patterns exactly: integer `r"[+-]?[0-9]+"`; date `r"[0-9]{4}-[0-9]{2}-[0-9]{2}"`; timestamp `r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?"`; Boolean `r"(?i:true|false|1|0)"`; required string `r"[A-Za-z0-9 _.-]+"`; nullable string `r"[A-Za-z0-9 _.-]*"`. For `DECIMAL(p,s)` where `p > s` and `s > 0`, use `r"[+-]?[0-9]{1,<p-s>}\.[0-9]{<s>}"`; for `s == 0`, use `r"[+-]?[0-9]{1,<p>}"`; for `p == s`, use `r"[+-]?0\.[0-9]{<s>}"`. Substitute the numeric bounds before emitting the direct `re.fullmatch` guard; for example, `DECIMAL(18,2)` must use `r"[+-]?[0-9]{1,16}\.[0-9]{2}"`. Do not expand quantified date digits or replace a fixed-scale decimal pattern with unbounded `[0-9]+` groups.
   An optional non-null source default must use a restoring assignment, never a rejecting guard. For example, `@MinCustomerId BIGINT = 1000` requires `if MinCustomerId is None: MinCustomerId = 1000` before lexical validation; `if MinCustomerId is None: raise ...` violates the source default and fails the maintained validator.
4. Before generating any notebook, call `assess_tsql_manual_redesign(source)` from `scripts/dedicated_pool_runtime.py`. If its disposition is `ManualReviewRequired`, copy its exact `features` and `reason` into the source decision and emit no automatic notebook. For an `AutomaticCandidate`, call `require_automatic_tsql_candidate(source)` as the fail-closed generation gate. That function raises `MigrationBlocked` for a blocked assessment rather than returning it, so catch that exception only after the assessment evidence has been persisted; never translate the exception into an automatic result.

5. Reference that property at every semantic use of the source input in later `%%sql` cells as `${spark.synapseMigration.<procedure-key>.<parameter-key>}`. Every `%%sql` cell must contain exactly one Spark SQL statement after the magic; never place semicolon-separated statements in one cell. When one validation cell must enforce several conditions, emit one `SELECT` statement whose projection contains a separate `assert_true(...)` expression for each condition. Single-quote numeric, date, timestamp, and Boolean substitutions and immediately cast them to their mapped Spark SQL types, for example `CAST('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.MinCustomerId}' AS BIGINT)`. The quotes are mandatory because the offline parser gate does not execute the Python bridge first; an unset unquoted substitution collapses to invalid SQL such as `CAST( AS BIGINT)`. Preserve a non-null STRING input as a directly quoted substitution such as `RegionCode = '${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RegionCode}'`; do not wrap it in `CAST(... AS STRING)`. For an optional SQL `NULL` STRING default, first recover null semantics with `NULLIF('${spark.synapseMigration.<procedure-key>.<parameter-key>}', '::SYNAPSE_MIGRATION_NULL::')` and use that expression directly. Never replace a parameter reference with its default, a fixture value, a literal in a predicate, or a one-row temporary view containing constants.
    Preserve every discovered target, source, projection, join, and predicate in the translated transformation. Apply the approved type mapping consistently to literals and predicates: for example, when a source `BIT` column maps to Spark `BOOLEAN`, translate `IsActive = 1` to the semantically equivalent `IsActive = TRUE` rather than retaining an integer comparison or dropping the branch. After lexical validation, consume a mapped Boolean input through this literal immediate-cast form: `(CAST('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.IncludeInactive}' AS BOOLEAN) = TRUE OR IsActive = TRUE)`. The substitution must be the direct argument to `CAST`; never generate `CAST(LOWER('${...}') AS BOOLEAN)`, `LOWER(...) IN (...)`, or another wrapper/string comparison in the transformation predicate. Case normalization belongs only in the preceding lexical-validation assertion. Validate the generated transformation against the discovered procedure's statement structure and parameter-use inventory, not only by checking that parameter tokens occur somewhere in the notebook.
6. Treat a source input without a source default as required, not unsupported. Permit conversion and publication when the approved caller contract supplies it through a Fabric Pipeline Notebook activity or parent-notebook invocation. Before execution, the Python bridge must reject a missing value and validate the supplied value against the source type; the generated notebook has no interactive fallback. Do not manufacture a sample, sentinel, empty-string, zero, or preview default merely to make the notebook runnable.
    When the generated notebook is also required to enforce the contract, emit an executable `%%sql` validation cell before the first mutating statement. Use `assert_true` against the same fully qualified substitutions to reject missing/blank required values and `try_cast(... AS <mapped-type>) IS NOT NULL` to reject invalid typed values. For every required string, assert the substitution itself is non-empty; for example, validate `RegionCode` with `assert_true('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RegionCode}' <> '', 'RegionCode is required and must be non-blank')`. A length check or comparison with a textual `null` sentinel does not replace this explicit empty-string rejection. Apply the exact `try_cast` rule to required dates as well as numeric and decimal values: for example, validate `RunDate` with `assert_true(try_cast('${spark.synapseMigration.dbo_usp_LoadFilteredCustomers.RunDate}' AS DATE) IS NOT NULL, 'RunDate is required and must be DATE')`. Do not substitute `to_date`, `date_format`, or another permissive date conversion for the required DATE `try_cast` validation. Validate accepted Boolean lexical forms explicitly. Only after those assertions pass may transformation predicates consume the substitutions, with numeric, date, decimal, and Boolean substitutions immediately cast to their mapped Spark SQL types.
7. Permit automatic runtime substitution for integers, fixed-scale decimals, dates/timestamps, bounded strings, and booleans only when an approved caller contract validates the mapped source type before starting the notebook, the Python bridge repeats that validation before calling `spark.conf.set`, and the generated pre-mutation SQL validation cell repeats every validation that remains parse-safe. Validate signed base-10 integers, fixed-scale decimals, canonical dates/timestamps, and Boolean spellings `true`, `false`, `1`, and `0` case-insensitively. A string is bounded only when its contract defines a business-specific character allow-list that excludes SQL delimiters and control characters; the default required-string allow-list is `^[A-Za-z0-9 _.-]+$`. The caller and bridge must reject apostrophes, quotes, semicolons, comment markers, backslashes, newlines, and every other out-of-allow-list character. Do not rely on an `assert_true` inside SQL as the security boundary: textual substitution occurs before Spark parses that assertion. Preserve accepted content exactly; do not escape, strip, or normalize it. When a valid business value requires a character outside the approved allow-list, mark the procedure `ManualReviewRequired` and redesign parameter transport rather than widening the allow-list ad hoc. Record every caller-side and notebook-side validation control in the manifest.
8. Resolve identifiers only from discovered, allow-listed metadata and quote them during generation. Never accept table, schema, column, expression, clause, or arbitrary SQL text through a runtime parameter.
9. Mark unbounded or unvalidated strings and dates/timestamps, binary values, table-valued parameters, unsupported outputs, and parameters used to construct dynamic SQL as `ManualReviewRequired`. Do not publish manual-review notebooks until the manifest records per-object approval and the approved redesign.

Do not add a Python `spark.sql(...)` wrapper or DataFrame transformation. The manifest must record each source parameter, mapped type, configuration key, whether it is required, source-default presence and value, approved caller, missing-value behavior, validation rule, and disposition. For every automatically substituted string, also record `stringAllowList` as the full anchored regular expression, `validationBoundary: "CallerBeforeNotebook"`, and `outOfAllowListDisposition: "ManualReviewRequired"`; absence of any of these fields blocks publication. A parameterized procedure is not converted when its SQL no longer consumes the runtime mapping, even if an emitted literal equals the source default.

In every manifest `parameterMappings` entry, use `sourceParameter` for the discovered source parameter name; never emit `parameterName` there. Pass the generated manifest to every parser-gate invocation with `--manifest <path-to-migration-manifest.json>`; a manifest that contains `parameterName`, omits a non-empty `sourceParameter`, or has non-array `objects` / `parameterMappings` is blocking even when the notebook structure passes. Preserve JSON `null` for both absent required defaults and explicit nullable defaults, and use `required` plus `missingValueBehavior` to distinguish them. For example:

```json
[
	{
		"sourceParameter": "RunDate",
		"sourceDefault": null,
		"sourceDefaultPresent": false,
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
		"sourceDefaultPresent": true,
		"defaultValue": null,
		"required": false,
		"missingValueBehavior": "UseSourceNullDefault",
		"nullTransportToken": "::SYNAPSE_MIGRATION_NULL::",
		"nullTokenCollisionCheck": "ProvenOutsideSourceDomain",
		"validationRule": "Nullable STRING",
		"stringAllowList": "^[A-Za-z0-9 _.-]*$",
		"validationBoundary": "CallerBeforeNotebook",
		"outOfAllowListDisposition": "ManualReviewRequired",
		"configurationKey": "spark.synapseMigration.dbo_usp_LoadFilteredCustomers.OptionalNamePrefix"
	}
]
```

Before approving a nullable mapping, prove that the fixed `nullTransportToken` value `::SYNAPSE_MIGRATION_NULL::` is outside the parameter's valid source domain, including every non-null source default, and record `nullTokenCollisionCheck: "ProvenOutsideSourceDomain"`. The lexical allow-list alone is not proof when it admits the token. The parser gate and CLI support only this fixed token; do not choose a per-mapping alternative. If the source contract can legitimately supply the fixed token, set the mapping and procedure to `ManualReviewRequired`. Pass each approved nullable mapping to the parser gate with `--nullable-parameter <exact-parameter-name>`; required parameters must never receive that option.

Derive one parser-gate `--parameter-validation <sourceParameter>=<kind>` option from every approved manifest `validationRule`; do not infer it from notebook text. Use `integer`, `decimal:<precision>:<scale>`, `date`, `timestamp`, `boolean`, `string`, or `nullable-string`. For example, `Required DATE` maps to `RunDate=date`, a required `DECIMAL(18,2)` maps to `Amount=decimal:18:2`, and `Nullable STRING` maps to `OptionalNamePrefix=nullable-string`. A decimal bridge must use an exact-scale regex whose integer component admits at most precision minus scale digits, such as `[+-]?[0-9]{1,16}\.[0-9]{2}` for `DECIMAL(18,2)`. When scale equals precision, require the canonical zero-integral form `[+-]?0\.[0-9]{<scale>}`, such as `[+-]?0\.[0-9]{38}` for `DECIMAL(38,38)`. When any parameter-validation option is supplied, the options must cover every declared parameter exactly once. An unsupported or ambiguous rule is `ManualReviewRequired`, not grounds to omit that parameter from the contract.

## Tier Strategy

- **T1**: deterministic conversion; syntax validation required.
- **T2**: deterministic conversion plus schema mapping and parser tests.
- **T3**: convert one object at a time with dependency context and targeted static tests.
- **T4**: produce a redesign note and testable skeleton; do not claim automatic parity.

## Artifact Requirements

- Make schema DDL idempotent.
- Before rendering each new Delta table, call the maintained `plan_delta_column_mapping` policy with the discovered logical column names and the incremental target inventory. Emit `TBLPROPERTIES ('delta.columnMapping.mode' = 'name')` only when at least one logical name contains a space or another Delta-restricted character and downstream name-mapping compatibility has been explicitly approved. Record the offending names and decision in `expected-schema.json` and the manifest.
- Never enable column mapping globally. Reuse an existing compatible target or shortcut without changing it. If an existing table has restricted logical names but no compatible `name` or `id` mapping mode, or its protocol/mapping metadata is uncertain, mark that object `ManualReviewRequired` instead of altering it.
- Generate `expected-schema.json` directly from discovered metadata before DDL generation; never reconstruct expected names, types, precision, scale, or nullability from generated SQL.
- Parameterize workspace, Lakehouse, schema, and environment values.
- Keep secrets out of generated artifacts.
- For an approved `1:1` mapping, preserve the exact discovered `sourceName` as both the local notebook basename (`<sourceName>.ipynb`) and published Fabric Notebook display name (`<sourceName>`), including case and punctuation. For `N:1` or `N:N`, use only the explicitly approved target component names and paths; never derive a rename or grouping automatically. Keep every contributing `sourceSchema`, `sourceName`, and stable ID separately in the manifest.
- Emit `migration-manifest.json` with source-object decisions and target-component records. Each procedure source decision must include its stable source ID, feature IDs, gap IDs, approved mapping cardinality, disposition, approval evidence, and all target component IDs. Each Notebook target component must include all contributing source IDs, approved display name/workspace, artifact path, dependencies, tier, parameter mappings, source-block/cell provenance, deployment state, hashes, warnings, errors, and timestamps. **Defect #29 fix**: For versioned deployments, include `manifestVersion` (integer, starts at 1), `approvalHash` (SHA-256 of approved mapping graph + dispositions + target names), `previousManifestVersion` (if exists), and `structuredDiff` (array of changes: added/removed/modified procedures, target name changes, disposition changes, new gaps, resolved gaps). On each re-approval or re-deployment, increment `manifestVersion`, recompute `approvalHash`, and generate structured diff from previous manifest. Preserve `sourceStableId`, `targetArtifact`, and notebook lifecycle fields on a `1:1` notebook record for backward compatibility. Use only these state transitions: `Discovered` -> `Assessed` -> `DesignApproved` -> `Converted` -> `PublishPending` -> `Published` -> `ReadbackValidated`, with `ManualReviewRequired`, `ManualReviewApproved`, `ApprovedExclusion`, `Deferred`, or `Failed` as explicit gated states.
- For audited procedures, add the source hash, ledger path/hash, block totals by disposition, source-byte coverage, retry policy, attempt-record root, deployment-package path/hash, and package verdict to the manifest target component. Retain ledgers and attempt evidence after publication.
- Include source-to-target type mappings and conversion warnings.
- Emit at least one executable Spark SQL transformation cell for every converted stored procedure across its approved target components. Each transformation cell must start with `%%sql` and record its contributing source/block IDs. The magic command selects Spark SQL for the cell, but it does not replace the notebook-level runtime language required by Fabric pipeline execution. A notebook that only embeds, comments, or displays the source T-SQL is not a conversion.
- Do not emit PySpark, Python `spark.sql(...)` wrappers, or DataFrame API transformation logic for stored procedures. If Spark SQL cannot preserve a procedural construct, emit the supported SQL stages plus a precise manual-review/redesign finding rather than changing languages.
- Keep the original procedure text in the discovery evidence, not in executable notebook cells. Reject generated notebooks containing `CREATE PROCEDURE`, `CREATE PROC`, or a `source_procedure` placeholder.
- Use valid nbformat v4.5-or-newer JSON with top-level `cells`, `metadata`, `nbformat: 4`, and `nbformat_minor >= 5`. Set top-level `metadata.language_info.name` to `python` for these Python-kernel notebooks whose transformation cells use `%%sql`; reject a missing, blank, or unsupported value. Every cell ID must be unique and match `^[A-Za-z0-9_-]{1,64}$`. Every code cell must have `cell_type: code`, `metadata`, `source`, `outputs: []`, and `execution_count: null`; markdown cells must have `cell_type: markdown`, `metadata`, and `source`.
- Set `metadata.dependencies.lakehouse.default_lakehouse`, `default_lakehouse_workspace_id`, and `default_lakehouse_name` to the resolved target values. Do not substitute `metadata.trident.lakehouse` or another alternate path for this required binding. Preserve a verified Fabric-compatible `metadata.kernelspec` when one is available from a target-workspace Spark notebook, but do not invent a kernel identifier when the API returns null metadata. The required `metadata.language_info.name: python` is independent of optional `kernelspec` metadata and must still be emitted.
- Require this order for parameterized notebooks: optional introductory markdown; first code cell is the Python parameter cell tagged `parameters`; second code cell is the validation-only Python Spark-conf bridge; every later code cell starts with exact `%%sql`. Do not emit any later Python setup, normalization, display, or exit cell. Generated notebooks must contain no saved outputs.
- Validate notebook JSON and require `metadata.language_info.name: python`; reject object-valued `%%configure.conf` parameter mappings; validate parameter declarations and bridge allow-lists against the discovered source signature; validate every `%%sql` cell against the target Spark parser; reject Python transformation/DataFrame code; reject hardcoded replacements for source inputs; and assert each notebook has executable translated Spark SQL logic before deployment.
- Publish each successful notebook as a Fabric Notebook item through a definition payload using `format: "ipynb"`, part path `notebook-content.ipynb`, and `payloadType: "InlineBase64"`.
- Do not execute generated transformations or notebooks, export source rows, or populate target tables.

## Completion Gate

Do not start conversion when either migration gap report or the procedure mapping approval is missing or unapproved. An object is deployable only when its discovery gaps have dispositions, its dependencies and referenced-column contracts are resolved, generated artifacts parse, its approved target notebooks contain executable translated `%%sql` logic rather than pasted source T-SQL or PySpark/DataFrame code, every supported source input remains externally overridable with its exact source default, and the manifest records `ManualReviewApproved` for every behavior-changing redesign. The mapping must cover every eligible procedure and target component without missing, orphan, duplicate, or unapproved relationships; blocked source decisions remain present with no generated component. An audited procedure also requires 100% verified source-block coverage across all mapped target components, no non-deployable block or exhausted failure, and a hash-verified `ReadyForPublication` package. Missing mappings, invented defaults, hardcoded parameter uses, invalid `TYPE NULL` DDL, acknowledged/skipped/unknown states, package drift, and unresolved reviews are not deployable. In an interactive workflow that permits correction, repair each maintained structure-validator failure and rerun until validation passes. Only the one-shot offline local-artifact fixture makes the first structure-validator failure terminal; in that fixture, after the failure execute no further command, probe, read, parser, or validator invocation, do not regenerate any artifact, and report that exact failure. In every completion response, including a terminal validator failure, explicitly state whether T-SQL was converted to Spark SQL; use the literal phrase **Spark SQL**, name Fabric Lakehouse as the target, and report the resolved Lakehouse name along with artifact validation and the no-source-row boundary. The response must also identify the stored-procedure scope explicitly. When conversion artifacts were emitted, include `Stored-procedure T-SQL was converted to Spark SQL for Fabric Lakehouse <resolvedLakehouseName>.` and `Each emitted stored-procedure notebook contains executable %%sql transformation cells.` When no conversion artifacts were emitted, include `Stored-procedure T-SQL was not converted to Spark SQL.`
