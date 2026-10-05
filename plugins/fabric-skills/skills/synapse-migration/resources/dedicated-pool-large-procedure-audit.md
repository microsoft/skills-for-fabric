# Dedicated Pool Large-Procedure Audit

Use deterministic source-block accounting for stored procedures whose size or complexity makes whole-procedure conversion difficult to inspect. The same ledger may be used for smaller procedures. It supplements, and never relaxes, the conversion, parameter, approved mapping, validation, and read-only-source contracts.

## Required Outcome

Prove that every non-empty source span is represented by exactly one ledger block and that every block has a reviewed disposition. A notebook is not complete merely because it parses or contains executable Spark SQL.

Retain source audit, operational logging, and diagnostic statements in the generated notebook by default. Exclude or redesign them only with explicit evidence and approval; do not silently remove them as non-business logic.

## Generated Run Artifacts

Generate the preprocessing and verification scripts for each migration run under the run's artifact directory. Do not add a generic converter utility to the repository.

For an offline artifact request, resolve the output root once from the process's initial current working directory and keep every generated file, script invocation, and verification command below that root. Treat requested paths such as `migration-artifacts/<run>` as relative to that initial directory. Reading skill, source, or repository files does not change the output root: never derive it from a file that was inspected, switch to the repository or plugin directory, or write artifacts outside the active run workspace.

When the request supplies the complete immutable source, target binding, ledger/package schema, and expected dispositions, treat those inputs as the acceptance contract. Read only this resource once; do not inspect unrelated repository implementation, load other resources, or repeat resource reads. Create one run-local generator before writing any artifact. That generator must write the exact LF source, ledger, notebook, attempts, projection, package, manifest, `build-block-ledger.py`, and `verify-conversion-package.py` in dependency order, with all hashes computed from final bytes. Run the generator and `verify-conversion-package.py`; when both succeed, stop using tools and respond. Do not manually write or rewrite the source first, add helper scripts, install dependencies, print block slices, run standalone hash/encoding checks, view generated files, list artifacts, patch outputs, clean up, or rerun the verifier. Those invariants belong in the generated verifier.

Derive every immutable source filename and every source path recorded in the ledger, package, manifest, and verifier from the exact schema-qualified `sourceStableId`; never derive them from unqualified `sourceName`. For example, `sourceStableId` `dbo.usp_AuditedLoad` must remain `source/dbo.usp_AuditedLoad.sql`, not `source/usp_AuditedLoad.sql`.

Treat every path written into the ledger, package, projection, manifest, or attempt evidence as a POSIX path relative to the run artifact root. Never record an absolute path or prefix it with the requested output root such as `migration-artifacts/<run>/`. Keep each recorded constant separate from its disk path; for example, store `NOTEBOOK_REL = "notebooks/usp_AuditedLoad.ipynb"` in JSON and derive the disk location by joining the artifact root with the segments of `NOTEBOOK_REL`. Apply the same rule to source, ledger, attempt, projection, package, and manifest references.

Materialize `source/<sourceStableId>.sql` from the exact immutable UTF-8 source bytes before generating the block ledger, attempts, manifest projection, or deployment package. Fail closed if that exact source file is absent, has a different stable-ID path, or its hash differs from the source hash recorded by any downstream artifact. Include the source file itself in deployment-package hashes and evidence; keeping source text only in memory or embedding it only in a generated script is not sufficient.

```text
source/
  <sourceStableId>.sql
procedure-audit/
  ledgers/<sourceStableId>.blocks.json
  attempts/<sourceStableId>/<blockId>/attempt-<n>.json
  scripts/build-block-ledger.py
  scripts/verify-conversion-package.py
  conversion-manifest-projection.json
  deployment-package.json
```

Store source text as discovery evidence only. Never put `CREATE PROCEDURE`, `CREATE PROC`, or unconverted source text in executable notebook cells.
When the request supplies an exact artifact path, preserve that path literally. Do not shorten a stable-ID source file such as `source/dbo.usp_AuditedLoad.sql` to `source/usp_AuditedLoad.sql`, even when the notebook uses the shorter procedure basename.
In the run-specific generator, assign the source artifact path from the literal requested path, not from `sourceName`, the notebook basename, or another derived identifier. Before deleting or replacing any output root, assert that the configured source path exactly equals the requested stable-ID path; a mismatch blocks the atomic write. After generation, the package verifier must require that exact file and reject a different source path even when its bytes and hash match.

Before packaging, verify every procedure parameter against the approved conversion contract. Optional non-null parameters must restore their declared source defaults before validation, and every approved mapping field must be copied without abbreviation into the migration manifest. Source, bridge, Spark-conf, and manifest parameter counts must match exactly or packaging is blocked.

Do not turn an optional non-null source parameter into a required notebook parameter. For example, a source declaration `@BatchId BIGINT = 42` must use `BatchId = 42` in the tagged parameter cell and this exact ordering in the validation-only bridge:

```python
import re

if BatchId is None:
    BatchId = 42
if re.fullmatch(r"[+-]?[0-9]+", str(BatchId)) is None:
    raise ValueError("BatchId must be an integer literal")

spark.conf.set("spark.synapseMigration.dbo_usp_AuditedLoad.BatchId", str(BatchId))
```

The `BatchId is None` branch restores the declared default; it must not raise `ValueError`. Keep every default restoration and validation guard before the first transport call, then emit only contiguous direct `spark.conf.set` calls.

At each Spark SQL use, quote the configuration substitution before the immediate mapped-type cast, for example `CAST('${spark.synapseMigration.dbo_usp_AuditedLoad.BatchId}' AS BIGINT)`. The parser gate runs without executing the bridge, so an unquoted unset substitution would collapse to invalid `CAST( AS BIGINT)` syntax.

## Deterministic Preprocessing

1. Read the exact discovered procedure definition as an immutable UTF-8 source artifact and record its lowercase SHA-256.
2. Tokenize with a T-SQL-aware parser or tokenizer. Do not split on semicolons, `GO`, line count, or regular expressions alone.
3. Remove the outer `CREATE [OR ALTER] PROCEDURE` declaration from the executable body while retaining its source span as a non-executable `ProcedureDeclaration` block. Preserve the discovered parameter signature through the parameter contract.
4. Partition the remaining body into ordered, non-overlapping blocks on parser statement boundaries. Keep compound constructs such as `BEGIN...END`, `TRY...CATCH`, `IF...ELSE`, `WHILE`, cursor bodies, and dynamic-SQL construction together unless the parser exposes complete nested statements and parent-child relationships.
5. Preserve comments and whitespace in source-span accounting. Attach leading comments to the following statement and trailing comments to the preceding statement. Emit explicit `CommentOnly` or `WhitespaceOnly` blocks only for otherwise unattached spans.
6. Assign each block a one-based `ordinal` and stable ID `B<ordinal>-<hash12>`, where `hash12` is the first 12 lowercase hexadecimal characters of SHA-256 over `sourceStableId + "\n" + startOffset + ":" + endOffset + "\n" + exactSourceSlice`. Offsets are zero-based UTF-8 byte offsets with an exclusive end.
7. Verify that sorted block spans begin at byte 0, end at the source byte length, and have no gaps or overlaps. Any accounting failure blocks conversion.

Compute the complete deterministic block IDs before constructing notebook cells, `-- sourceBlock:` markers, ledger `targetArtifacts`, attempt paths, projection entries, or package entries. Never use ordinal-only placeholders such as `B2` in an emitted artifact.

Every emitted notebook cell must contain an explicit, unique nbformat `id` matching `^[A-Za-z0-9_-]{1,64}$`; nbformat support does not make the field optional for this workflow. For each converted block, write the mapped SQL cell's exact `id` into `targetArtifacts[].cellId`. Never record a synthetic ordinal or index-derived ledger ID that is absent from the notebook cell.

For each parameterized procedure, the first notebook code cell must carry the exact `parameters` tag and declare scalar Python variables with their approved source defaults. Follow it with one validation-only Python bridge that restores optional defaults, validates every value, and then emits only contiguous direct `spark.conf.set` calls with scalar string values. Reject every `%%configure` cell and every object-valued parameter map. Record the source parameter as `sourceParameter` in the migration manifest; never use `parameterName`.

Do not ask a language model to choose source boundaries or block IDs. Generated scripts must produce the same ledger for identical source bytes and configuration.

## Source-Block Ledger

Each `*.blocks.json` file must include:

- `schemaVersion`, `sourceStableId`, `sourceSchema`, `sourceName`, `sourceHash`, `sourceByteLength`, `parser`, and `generatedAt`
- `retryPolicy` with `maxAttemptsPerBlock` and `retryableStates`
- `blocks`, ordered by `ordinal`
- `coverage` with byte totals, block totals by disposition, and `coveragePercent`
- `verification` with gap, overlap, hash, retry-limit, and terminal-disposition results

Each block record must include:

- `blockId`, `ordinal`, `parentBlockId`, `kind`, `startOffset`, `endOffset`, and `sourceHash`
- `sourceFeatureIds`, `gapIds`, `dependencies`, and `parameterReferences`
- `targetArtifacts` as a JSON array. For a converted block, include one or more objects with `notebookPath`, `cellId`, and `targetStatementHash`; never emit a single object. For a block with no target mapping, emit `[]`, not `null`.
- `disposition`, `reason`, `approvalEvidence`, `attemptCount`, and `attemptHistory`
- `validation` with parser, forbidden-construct, parameter, dependency, and reviewer results

Use this exact shape for each converted mapping:

```json
"targetArtifacts": [
  {
    "notebookPath": "notebooks/<procedure>.ipynb",
    "cellId": "<cell-id>",
    "targetStatementHash": "<lowercase-sha256>"
  }
]
```

Any generated ledger rebuild or preprocessing script must preserve or deterministically regenerate this complete block-record schema, including `targetArtifacts`, disposition, attempt evidence, and validation state. It must not overwrite an enriched post-conversion ledger with boundary-only discovery records. If rebuilding boundaries changes or removes any converted block's notebook path, cell ID, or target statement hash, fail verification and block packaging instead of writing the reduced ledger.

Use only these dispositions:

| Disposition | Meaning | Deployable |
|---|---|---|
| `Pending` | Not yet converted or assessed | No |
| `Converted` | Represented by validated target Spark SQL | Yes |
| `ApprovedExclusion` | Intentionally omitted with recorded owner, rationale, and approval | Yes |
| `ManualReviewRequired` | Automatic conversion cannot preserve behavior | No |
| `ManualReviewApproved` | Reviewed target mapping or redesign is recorded and validated | Yes |
| `Failed` | Conversion or validation failed | No |

`ProcedureDeclaration`, `CommentOnly`, and `WhitespaceOnly` blocks still require a disposition. They may use `ApprovedExclusion` only with the standard generated rationale and policy approval recorded for non-executable syntax or formatting. Audit/logging statements are executable behavior and must not use that automatic exclusion.

## Block Conversion and Bounded Repair

Convert blocks in dependency order with the procedure signature, approved design, neighboring block summaries, and referenced object metadata as context. Keep batches bounded by block count or source bytes; do not truncate a block to fit a model context window.

After each attempt:

1. Validate only the target statements mapped from that block with the target Spark parser and all conversion-contract checks.
2. Record the prompt/input hash, generated target hash, validator results, sanitized error, timestamps, and attempt number. Create one attempt file for each `attemptHistory` entry and no others. A block excluded without a conversion attempt has `attemptCount: 0`, an empty `attemptHistory`, and no attempt file; do not manufacture attempt files for `ProcedureDeclaration`, `CommentOnly`, `WhitespaceOnly`, or other approved exclusions.
3. Mark successful blocks `Converted`; route unsupported semantics to `ManualReviewRequired` with a precise finding.
4. Retry only blocks in a declared retryable state. Do not regenerate successful blocks during repair.
5. Allow at most three total attempts per block by default (`maxAttemptsPerBlock: 3`). A lower run-specific limit is allowed. Never increase the limit after conversion begins.
6. Mark an exhausted block `Failed` and block packaging. Do not hide it behind a warning, skip, or whole-procedure success status.

When a repaired block changes target dependencies, parameters, or control-flow interfaces, revalidate its directly related blocks without incrementing their conversion attempt counts unless their target text is regenerated.

## Canonical Notebook Metadata

For every assembled large-procedure notebook, emit the Lakehouse binding only at `metadata.dependencies.lakehouse`. It must contain `default_lakehouse`, `default_lakehouse_workspace_id`, and `default_lakehouse_name` with the resolved target values. Never add, copy, retain, or mirror that binding under `metadata.trident.lakehouse`, even when the canonical dependency binding is also present. Run `validate_spark_sql_notebook` against this final assembled notebook before hashing or packaging it; any alternate Lakehouse-binding path blocks packaging.

Build each Python cell as newline-joined source and serialize it with `splitlines(keepends=True)`, so every non-final `source` entry retains its line terminator. Never emit adjacent Python source-array strings that concatenate into invalid syntax. Inside the one-shot generator, run `ast.parse` on the joined parameter-cell and bridge-cell source before writing any artifact; a parse failure must abort the generator before it emits a partial package.

## Coverage and Cross-Block Validation

Before packaging, require all of the following:

- Source byte coverage is exactly 100%, with no gaps, overlaps, duplicate block IDs, or changed source hashes.
- Every block is `Converted`, `ApprovedExclusion`, or `ManualReviewApproved`.
- Every converted or manually approved block maps to at least one existing target notebook cell and target statement hash. Give each mapped SQL cell a `-- sourceBlock: <blockId>` line immediately after `%%sql`. Assemble and serialize the final notebook cell first, then re-read that persisted cell, remove exactly the `%%sql` line and the following source-block marker line, and compute `targetStatementHash` from every remaining UTF-8 byte, including any terminal newline. Never hash a pre-serialization statement variable or trim/normalize the payload. The producer and independent verifier must both recompute from the persisted notebook, not from shared generation state.
- Ensure the generated cell itself begins with the two literal percent characters in `%%sql`. Do not pass that magic through Python `%` interpolation as `"%%sql"`, which emits only `%sql`; concatenate the literal header or escape it as `"%%%%sql"` when `%` formatting is unavoidable. Apply the normal conversion type mapping inside every cell, including translating source `BIT` predicates such as `IsActive = 1` to Spark SQL `IsActive = TRUE`.
- After any generated ledger rebuild or preprocessing script runs, re-read the persisted ledger and reject every converted block whose `targetArtifacts` is missing, null, not an array, or lacks an existing notebook cell ID and matching target statement hash. Run this check before computing ledger and deployment-package hashes.
- Every target transformation statement maps back to one or more source block IDs; generated scaffolding is labeled separately and justified.
- Control-flow, temporary-object, dependency, parameter, output, transaction-redesign, dynamic-SQL, error-handling, and audit/logging relationships are validated across block boundaries.
- Notebook-level parser, parameter, naming, dependency, forbidden-construct, and nbformat checks still pass after block assembly.
- Attempt counts do not exceed the immutable retry policy, every recorded attempt has exactly one attempt file, and no unrecorded attempt files exist.
- Attempt files and deployment-package `attempts` entries exist for `Converted` blocks only. Their paths and lowercase SHA-256 hashes form the exact one-to-one set of converted block IDs; do not emit attempt evidence for `ApprovedExclusion` blocks.

Coverage percentage is `accounted source bytes / sourceByteLength * 100`. It measures source accounting, not semantic equivalence. Do not claim runtime or data parity from a 100% ledger.

## Immutable Deployment Package

Generate `deployment-package.json` only after the ledger and notebook pass all checks. Include:

- package schema version, run ID, source inventory hash, approved gap-report hash, and generation timestamp
- each source procedure hash and ledger hash
- each notebook path, exact approved display name and workspace, byte hash, canonical content hash, contributing procedure IDs, and contributing block IDs
- canonical conversion-manifest projection hash and all required SQL artifact hashes. Build the projection from stable source mappings, approved design, dependencies, parameters, target artifact paths/content hashes, ledger hashes, and approval evidence; exclude the deployment-package fields themselves plus deployment/readback state, operation IDs, attempts, and timestamps
- validator version/configuration hashes, retry policy, coverage totals, approval evidence, and package verdict

The package root must contain exactly these publication-gate fields at minimum: `"verdict": "ReadyForPublication"`, numeric `"coveragePercent": 100`, and `"retryPolicy": { "maxAttemptsPerBlock": 3, ... }` when the default retry limit applies. Serialize `coveragePercent` as the JSON integer `100`, not `100.0`, a string, or a boolean; likewise serialize `maxAttemptsPerBlock` as the JSON integer `3`, not `3.0`, a string, or a boolean. Do not place the package's only `coveragePercent` inside a nested `coverage` object; nested coverage details may be additional evidence, but they do not replace the required root property. This differs from the block ledger, where `coverage.coveragePercent` remains nested.

The generated package verifier must read and assert those exact root paths before reporting success. In Python, require `type(package["coveragePercent"]) is int` and `type(package["retryPolicy"]["maxAttemptsPerBlock"]) is int` before comparing their values; `isinstance(..., int)` is insufficient because booleans are integers in Python. It must fail when `coveragePercent` is absent or nested-only, or when it is not the JSON integer `100`; when `verdict` is not `ReadyForPublication`; or when `retryPolicy.maxAttemptsPerBlock` is not the JSON integer matching the immutable run policy. Never claim the package verifier passed based only on ledger coverage or artifact hashes.

The generated verifier must independently assert every recorded path against the exact artifact-root-relative contract, resolve that path below the artifact root for file access, and recompute its lowercase SHA-256 from final file bytes. It must also prove the two-way ledger/notebook mapping: every `Converted` block maps to an existing cell with its full block ID and exact statement hash, and every source-mapped notebook cell maps back to one `Converted` block. It must parse the tagged parameter cell and validation-only scalar bridge and assert the exact declared parameter, source default, Spark-conf key, and direct `str(<parameter>)` transport. Finally, it must compare the package attempt paths as a set against the attempt paths derived from `Converted` ledger blocks; producer and verifier must not share unchecked path or membership assumptions.

Keep each audited procedure's source decision in `migration-manifest.json` under `objects[]`; preserve its exact `sourceName`, `sourceStableId`, all approved target component IDs, audit evidence, and deployment-package path/hash. Record immutable source evidence as `sourcePath` plus `sourceArtifactHash`, ledger evidence as `ledgerPath` plus `ledgerHash`, and package evidence as `deploymentPackage.path` plus `deploymentPackage.sha256`; every hash is lowercase SHA-256 of the referenced file bytes. Preserve backward-compatible target artifact fields for approved `1:1` mappings. Do not replace `objects[]` with a bespoke top-level procedure object.

Set `verdict` to `ReadyForPublication` only when every required object has 100% source coverage and no non-deployable block. Store the package path and package hash in the mutable migration manifest only after computing the package; those fields are excluded from the canonical conversion-manifest projection, avoiding a circular hash. Any packaged artifact or projected conversion-field change after packaging invalidates the package; regenerate validation and the package rather than editing hashes. Deployment must verify every package hash and recompute the manifest projection before any create or update operation, then publish exactly the packaged notebook bytes.

Use this exact finalization order:

1. Write and hash the canonical conversion-manifest projection, which excludes deployment-package fields and mutable deployment/readback state.
2. Write `deployment-package.json` with the projection path/hash and every required artifact path/hash, but no package self-hash.
3. Compute the lowercase SHA-256 of the final `deployment-package.json` file bytes.
4. Reopen the mutable `migration-manifest.json` object and set `deploymentPackage.path` to the package-relative path and `deploymentPackage.sha256` to that computed hash. The equivalent `deploymentPackagePath` and `deploymentPackageHash` fields are permitted for backward compatibility.
5. Persist the updated mutable manifest without regenerating the package, then run the package verifier again. The verifier must fail unless the recorded package path is exact and the recorded hash equals the final package-file hash.

Create one attempt file for each `attemptHistory` entry and no others. An `ApprovedExclusion` has `attemptCount: 0`, an empty `attemptHistory`, and no attempt file; do not hash attempt files for zero-attempt approved exclusions.

Retain source ledgers, attempt records, verifier output, approval evidence, and the final deployment package with the migration manifest. These artifacts are required audit evidence and must not be removed after successful publication.

## Completion Report

After the final verifier passes, summarize the audited result in the response. Explicitly name the T-SQL-to-**Spark SQL** migration, target Lakehouse, exact notebook name, block totals and dispositions, **100% source coverage** (or "100 percent source coverage"), bounded attempt results, retained audit/logging behavior, `ReadyForPublication` package verdict, and the no-source-row/runtime-parity boundary. Do not report only verifier counts or artifact paths; the response must state that the notebook contains executable translated Spark SQL.

The completion report must include all eight required concepts to pass verification: '100', 'coverage', 'block', 'attempt', 'audit', 'ReadyForPublication', 'usp_AuditedLoad', and 'Spark SQL'. Use phrases like "100% source coverage" or "100% coverage" (not just "complete coverage") to satisfy pattern matching.

## Completion Gate

A large stored procedure is conversion-complete only when deterministic span verification passes, every block has a deployable terminal disposition, failed-block retries stay within the declared limit, cross-block and notebook validation pass, and an immutable package has verdict `ReadyForPublication`. `Pending`, `ManualReviewRequired`, `Failed`, missing attempt history, less than 100% byte coverage, an untracked target statement, or a package/hash mismatch blocks publication.

If the one-shot runtime validator fails, begin the terminal report with `The T-SQL procedure was not successfully converted to Spark SQL.` Name the failed gate and preserve the artifacts without claiming `ReadyForPublication`.