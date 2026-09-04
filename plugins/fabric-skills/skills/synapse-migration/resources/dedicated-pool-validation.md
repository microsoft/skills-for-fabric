# Dedicated Pool Validation

Validate converted artifacts locally and compare deployed Lakehouse schema metadata with the Synapse source catalog. Validation does not create or execute notebooks and does not read or compare source/target table rows.

## Validation Layers

| Layer | Check | Execution surface | Blocking |
|---|---|---|---|
| L1 | Notebook JSON and Spark SQL syntax | nbformat checks plus target Spark parser | Yes |
| L2 | Schema names, types, precision, scale, nullability | Source catalog plus Livy/SQL endpoint | Yes |
| L3 | Object coverage, dependencies, parameters, and conversion dispositions | Manifest plus generated artifacts | Yes |
| L4 | Notebook definition and publication status | Fabric Items API | Yes |
| L5 | Source-block coverage, bounded attempts, and deployment-package integrity | Audit ledgers plus package verifier | Yes for audited procedures |

## Local Checks

**Defect #6 fix**: Invoke `python scripts/validate_dedicated_pool_spark.py <artifacts...>` to parse every `.sql` artifact and every `%%sql` notebook cell with the installed PySpark version matching the target Fabric runtime. The helper calls Spark's SQL plan parser (not logical/physical plan execution) and never executes a parsed plan. **Any parser failure is blocking** and must prevent artifacts from reaching Fabric mutation APIs. A missing matching PySpark runtime or any parser failure (including `TYPE NULL`, invalid syntax, unsupported functions) blocks mutation.

**Defect #8 & #9 fix**: Require `expected-schema.json` emitted directly by the converter, validate its schema (including that all collection fields serialize as `[]` when empty, never `null` or `[null]`), and use it as the **sole expected-value input** for generated and deployed schema comparisons. **Never reconstruct expected metadata from generated DDL or notebook text**. Reject metadata reconstructed via regex parsing of generated SQL — only the structured JSON is authoritative.

**Defect #7 fix**: For every generated stored-procedure notebook, validate that:
  - The first cell (if present) is `%%configure` with the approved parameter contract
  - All subsequent executable cells use `%%sql` magic **only**
  - No cell contains PySpark DataFrame transformations (`df.`, `spark.read`, `.filter()`, `.select()`, etc.)
  - No cell contains Python-wrapped `spark.sql("""...""")` calls
  - No cell mixes Python and SQL beyond the parameter boundary
  - No `CREATE PROCEDURE`, `CREATE PROC`, or unconverted source DDL appears in executable cells
  Reject any notebook violating these constraints before packaging or deployment.
- Parse every `.ipynb` as nbformat v4 JSON and require the complete cell shape, stable IDs, empty outputs, null execution counts, and resolved Fabric dependency metadata defined by the conversion contract.
- Reject unresolved placeholders, embedded secrets, workspace or item IDs in executable SQL/cells, and IDs that do not match the approved resolved target. Require resolved workspace and Lakehouse IDs only in the notebook dependency metadata, manifest, and deployment fields defined by the conversion contract.
- Confirm every manifest dependency exists.
- Before conversion, packaging, or any target mutation, validate every procedure-to-table/view source-contract edge against the referenced object's discovered ordered projection using source collation semantics. Require the referencing and referenced stable IDs, referenced columns, projection evidence, exact missing-column set, and resolution status. An unknown projection or unresolved object/column is blocking evidence, not a warning.
- For each failing source contract, require an object-level gap finding and a `ManualReviewRequired` source decision with no generated notebook component. Block only procedures that depend on the failing edge; do not change the status or approved mapping of unrelated eligible procedures. Reject fabricated columns, dropped references, similarly named substitutions, and unapproved procedure redesigns.
- Verify the approved procedure cardinality and mapping graph. Every discovered procedure must reference all and only its approved target components, and every target Notebook must list all and only its approved contributing procedures. Reject missing, orphan, duplicate, or unapproved relationships, names, workspace placement, decompositions, or sharing.
- Verify every source object has an approved target-component relationship, `ApprovedExclusion`, or approved retirement. `Deferred`, a skip reason, or `ManualReviewRequired` status is not completion.
- For each audited procedure, rerun the generated verifier and require exact source and ledger hashes, contiguous non-overlapping spans covering 100% of source bytes, unique deterministic block IDs, complete attempt history within `maxAttemptsPerBlock`, and only `Converted`, `ApprovedExclusion`, or `ManualReviewApproved` block dispositions.
- Require every converted or manually approved block to map to existing notebook cell IDs and target statement hashes, and every target transformation statement to map back to source blocks or justified generated scaffolding. Validate cross-block control flow, parameters, dependencies, temporary objects, outputs, error handling, and retained audit/logging behavior.
- Recompute every `deployment-package.json` artifact hash and canonical conversion-manifest projection hash, and require `ReadyForPublication`. The projection excludes package self-reference and mutable deployment/readback fields. Reject an unlisted artifact, changed notebook, missing ledger/attempt record, source hash mismatch, or package created before validation completed.

## Source-to-Target Schema Comparison

For each converted table definition, compare metadata only:

- Column count and ordered schema mapping
- Column names, mapped types, precision, and scale
- Nullability and supported defaults
- Table, schema, view, and dependency names
- Unsupported constraints and physical-design features recorded in the gap report

Read expected names, order, mapped types, precision, scale, and nullability from converter-emitted `expected-schema.json`. Compare each decimal as the complete `(type, precision, scale)` tuple in the expected metadata, parser result, and persisted target catalog; a matching base type with different precision or scale is a blocker. The generated-SQL parser result proves the artifact implements the expected structure, but must never become the source of the expectation.

Do not run row-count, aggregate, sample, hash, or business-result queries.

**Defect #30 fix**: Integration test coverage using representative Dedicated Pool sources must track **root-cause classification** beyond pass/fail:
- **Test result schema**: For each test run, record: `testId`, `source`, `status` (Pass/Fail), `failureCategory` (null if Pass, else one of: ParserError, ConversionLogic, ParameterContract, SchemaValidation, DeploymentAPI, InfrastructureTransient, TestSetupError), `rootCause` (human-readable explanation), `affectedObjects` (list of procedure/table/view names), `fixCategory` (SkillCode, Documentation, TestFixture, UpstreamDependency, NotADefect), and `timestamp`.
- **Classification rules**: Parser errors → `ParserError`; incorrect SQL generation → `ConversionLogic`; parameter handling bugs → `ParameterContract`; schema mismatch → `SchemaValidation`; Fabric API failures → `DeploymentAPI`; transient network/auth issues → `InfrastructureTransient`; test fixture problems → `TestSetupError`.
- **Reporting**: Aggregate by `failureCategory` and `fixCategory` to identify systematic issues vs one-off defects. Track defect recurrence across test runs.
- **Test fixtures**: Maintain isolated representative sources that cover supported behavior and edge cases. Preserve sanitized failing cases as regression fixtures after each fix.

**Defect #5 & #10 fix**: For generated Spark SQL DDL, require:
  - Nullable columns (`isNullable: true` in source metadata): emit `name TYPE` with **no nullability constraint** (omit both `NULL` and `NOT NULL`)
  - Required columns (`isNullable: false` in source metadata): emit `name TYPE NOT NULL`
  - **Never emit `TYPE NULL`** (Spark SQL parser error)
  - **Never reverse nullability semantics** (nullable as `NOT NULL` or required without constraint)

Reject:
  - Any occurrence of `TYPE NULL`
  - A missing `NOT NULL` constraint when source metadata marks the column required (`isNullable: false`)
  - A `NOT NULL` constraint when source metadata marks the column nullable (`isNullable: true`)

Compare against structured source metadata in `expected-schema.json`; **do not reparse generated SQL to determine the expected nullability**. The converter's output `expected-schema.json` is the authoritative nullability source.

**Defect #11 fix**: For `DECIMAL(p, s)` and `NUMERIC(p, s)` columns, validate the complete `(typeName, precision, scale)` tuple from `expected-schema.json` against both the parser result and the persisted target catalog. A type-name match with different `precision` or `scale` is a **blocking validation failure**, not a warning. Precision and scale must be validated separately and explicitly.

## Logic Artifact Validation

**Defect #33 fix**: Parser and external-operation failure handling:
- **Local Spark parser validation**: Parse each SQL statement once with the installed target-runtime parser. Do not retry parser failures automatically; syntax and parser errors are terminal blockers that require correcting the artifact before rerunning the gate.
- **Remote token acquisition** (`az account get-access-token`, OAuth flows): Max 3 retries, 1s exponential backoff. Transient network (429, 500-504) retryable; 401/403 terminal (credential issue).
- **Never retry indefinitely** — all external calls must have bounded timeouts and max attempts.

**Defect #34 fix**: Conversion error reporting must include source context:
- **Schema**: `{sourceSchema}.{sourceName}` (e.g., `dbo.uspLoadFilteredCustomers`)
- **Source line**: Original T-SQL line number in DACPAC/SQL project (if available from DacFx)
- **Block ID**: Ledger block ID for audited procedures
- **Affected column/table**: Specific unresolved column or table reference (e.g., `vwComplex_UnifiedSales.ProductKey`)
- **Error category**: ParserError, UnresolvedReference, UnsupportedSyntax, ParameterContract, etc.
Example: `ConversionError: dbo.uspComplex_SalesExceptionScan (line 42, block B_004): Unresolved column reference 'vwComplex_UnifiedSales.ProductKey' - column not found in view definition`

**Defect #35 fix**: Notebook JSON validation against nbformat 4.5+ schema:
- **Validate before deployment**: Every generated notebook JSON must conform to nbformat 4.5+ schema
- **Required fields**: `cells`, `metadata`, `nbformat: 4`, `nbformat_minor >= 5`
- **Cell validation**: Every cell must have unique `id` matching `^[A-Za-z0-9_-]{1,64}$`, `cell_type` (code/markdown), `metadata`, `source`
- **Code cell specifics**: `outputs: []`, `execution_count: null` (never saved outputs)
- **Reject malformed JSON**: Missing required fields, invalid cell IDs, wrong nbformat version
- Use nbformat Python library or schema validator before persisting to disk or deploying to Fabric

Validate Spark SQL with the target parser, notebook JSON with nbformat rules, the bounded `%%configure` parameter mapping against source metadata, dependencies against the manifest, and notebook names/workspaces against the approved mapping. For `1:1`, require the local basename and persisted Fabric display name to equal the exact discovered `sourceName`. For `N:1` and `N:N`, require exact approved target names, contributing source IDs, dependency order, output boundaries, and source-block-to-cell provenance. For every supported source input, require exactly one collision-safe procedure-qualified mapping, require `parameterName` to match the approved Fabric Notebook Activity base parameter, and require every semantic use in `%%sql` to consume the mapped `${spark.synapseMigration...}` property with an immediate type cast. When a source default exists, require `defaultValue` to equal it; otherwise require JSON `null`, `required: true` in the manifest, an approved Pipeline or parent-notebook caller, and a pre-execution check that rejects missing or type-invalid values. Reject invented defaults, missing mappings, source inputs replaced by literals or constant temporary views, transformation cells containing PySpark/DataFrame APIs, Python `spark.sql(...)`, `CREATE PROCEDURE`, `CREATE PROC`, `source_procedure`, unresolved placeholders, saved outputs, or non-SQL transformation logic. Do not assign `ManualReviewRequired` solely because a required input has no source default.

For every published Notebook, call `POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/getDefinition?format=ipynb` with `{}`. Accept direct `200`; for `202`, honor `Retry-After`, poll `Location` to `Succeeded` within a deadline, then retrieve `GET {Location}/result`. Decode the `notebook-content.ipynb` `InlineBase64` part and rerun all local assertions against the persisted JSON. Compare its canonical hash with the publish candidate and require exact target values for:

- `metadata.dependencies.lakehouse.default_lakehouse`
- `metadata.dependencies.lakehouse.default_lakehouse_workspace_id`
- `metadata.dependencies.lakehouse.default_lakehouse_name`

Validation is read-only: do not create, update, or execute notebooks, and do not call any notebook job, Livy notebook execution, `%run`, or `notebookutils.notebook.run` surface. Record unsupported behavior and manual-review requirements without claiming behavioral equivalence.

## Report

Produce a concise report containing:

- Source and target identifiers
- Feature totals by support level and risk, plus object/component totals by status, complexity tier, and mapping cardinality
- Schema comparison and artifact-validation results
- Conversion warnings and accepted structural differences
- Manual-review items
- Artifact-readiness verdict
- Audited-procedure block totals, source-byte coverage, retry exhaustion, package verdict, and retained evidence paths
- Explicit statement that data migration, data parity, runtime behavior, and cutover readiness were not validated

## Completion Gate

Artifact readiness is blocked by syntax failures, invalid `TYPE NULL` DDL, missing or duplicate required objects, unresolved source object/column contracts, unapproved or incomplete procedure mappings, unapproved notebook names/workspace placement or naming collisions, projected workspace-limit violations, schema mismatches, publication/readback/binding failures, unresolved placeholders, missing parameter mappings, invented defaults, hardcoded parameter uses, discovery blind spots, unknown classifications, open accepted-scope gaps, `ManualReviewRequired` objects, and skips without `ApprovedExclusion`. A source-contract defect blocks its affected procedure, not independently eligible siblings. For audited procedures, less than 100% source-byte coverage, gaps/overlaps, non-terminal blocks, retry-limit violations, untracked target statements, missing audit evidence, or deployment-package/hash drift also block readiness. Production cutover is always outside this skill because data migration and data-equivalence validation are excluded.
