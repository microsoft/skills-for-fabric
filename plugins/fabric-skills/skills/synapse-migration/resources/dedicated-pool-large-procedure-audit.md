# Dedicated Pool Large-Procedure Audit

Use deterministic source-block accounting for stored procedures whose size or complexity makes whole-procedure conversion difficult to inspect. The same ledger may be used for smaller procedures. It supplements, and never relaxes, the conversion, parameter, approved mapping, validation, and read-only-source contracts.

## Required Outcome

Prove that every non-empty source span is represented by exactly one ledger block and that every block has a reviewed disposition. A notebook is not complete merely because it parses or contains executable Spark SQL.

Retain source audit, operational logging, and diagnostic statements in the generated notebook by default. Exclude or redesign them only with explicit evidence and approval; do not silently remove them as non-business logic.

## Generated Run Artifacts

Generate the preprocessing and verification scripts for each migration run under the run's artifact directory. Do not add a generic converter utility to the repository.

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

## Deterministic Preprocessing

1. Read the exact discovered procedure definition as an immutable UTF-8 source artifact and record its lowercase SHA-256.
2. Tokenize with a T-SQL-aware parser or tokenizer. Do not split on semicolons, `GO`, line count, or regular expressions alone.
3. Remove the outer `CREATE [OR ALTER] PROCEDURE` declaration from the executable body while retaining its source span as a non-executable `ProcedureDeclaration` block. Preserve the discovered parameter signature through the parameter contract.
4. Partition the remaining body into ordered, non-overlapping blocks on parser statement boundaries. Keep compound constructs such as `BEGIN...END`, `TRY...CATCH`, `IF...ELSE`, `WHILE`, cursor bodies, and dynamic-SQL construction together unless the parser exposes complete nested statements and parent-child relationships.
5. Preserve comments and whitespace in source-span accounting. Attach leading comments to the following statement and trailing comments to the preceding statement. Emit explicit `CommentOnly` or `WhitespaceOnly` blocks only for otherwise unattached spans.
6. Assign each block a one-based `ordinal` and stable ID `B<ordinal>-<hash12>`, where `hash12` is the first 12 lowercase hexadecimal characters of SHA-256 over `sourceStableId + "\n" + startOffset + ":" + endOffset + "\n" + exactSourceSlice`. Offsets are zero-based UTF-8 byte offsets with an exclusive end.
7. Verify that sorted block spans begin at byte 0, end at the source byte length, and have no gaps or overlaps. Any accounting failure blocks conversion.

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
- `targetArtifacts` with notebook path, cell ID, and target statement hash when converted
- `disposition`, `reason`, `approvalEvidence`, `attemptCount`, and `attemptHistory`
- `validation` with parser, forbidden-construct, parameter, dependency, and reviewer results

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
2. Record the prompt/input hash, generated target hash, validator results, sanitized error, timestamps, and attempt number.
3. Mark successful blocks `Converted`; route unsupported semantics to `ManualReviewRequired` with a precise finding.
4. Retry only blocks in a declared retryable state. Do not regenerate successful blocks during repair.
5. Allow at most three total attempts per block by default (`maxAttemptsPerBlock: 3`). A lower run-specific limit is allowed. Never increase the limit after conversion begins.
6. Mark an exhausted block `Failed` and block packaging. Do not hide it behind a warning, skip, or whole-procedure success status.

When a repaired block changes target dependencies, parameters, or control-flow interfaces, revalidate its directly related blocks without incrementing their conversion attempt counts unless their target text is regenerated.

## Coverage and Cross-Block Validation

Before packaging, require all of the following:

- Source byte coverage is exactly 100%, with no gaps, overlaps, duplicate block IDs, or changed source hashes.
- Every block is `Converted`, `ApprovedExclusion`, or `ManualReviewApproved`.
- Every converted or manually approved block maps to at least one existing target notebook cell and target statement hash. Give each mapped SQL cell a `-- sourceBlock: <blockId>` line immediately after `%%sql`; compute `targetStatementHash` from the exact UTF-8 bytes after those two lines, with no trimming or normalization, so the verifier can recompute it from the notebook.
- After any generated ledger rebuild or preprocessing script runs, re-read the persisted ledger and reject every converted block whose `targetArtifacts` is missing, null, not an array, or lacks an existing notebook cell ID and matching target statement hash. Run this check before computing ledger and deployment-package hashes.
- Every target transformation statement maps back to one or more source block IDs; generated scaffolding is labeled separately and justified.
- Control-flow, temporary-object, dependency, parameter, output, transaction-redesign, dynamic-SQL, error-handling, and audit/logging relationships are validated across block boundaries.
- Notebook-level parser, parameter, naming, dependency, forbidden-construct, and nbformat checks still pass after block assembly.
- Attempt counts do not exceed the immutable retry policy and all attempt records are present.

Coverage percentage is `accounted source bytes / sourceByteLength * 100`. It measures source accounting, not semantic equivalence. Do not claim runtime or data parity from a 100% ledger.

## Immutable Deployment Package

Generate `deployment-package.json` only after the ledger and notebook pass all checks. Include:

- package schema version, run ID, source inventory hash, approved gap-report hash, and generation timestamp
- each source procedure hash and ledger hash
- each notebook path, exact approved display name and workspace, byte hash, canonical content hash, contributing procedure IDs, and contributing block IDs
- canonical conversion-manifest projection hash and all required SQL artifact hashes. Build the projection from stable source mappings, approved design, dependencies, parameters, target artifact paths/content hashes, ledger hashes, and approval evidence; exclude the deployment-package fields themselves plus deployment/readback state, operation IDs, attempts, and timestamps
- validator version/configuration hashes, retry policy, coverage totals, approval evidence, and package verdict

The package root must contain exactly these publication-gate fields at minimum: `"verdict": "ReadyForPublication"`, numeric `"coveragePercent": 100`, and `"retryPolicy": { "maxAttemptsPerBlock": 3, ... }` when the default retry limit applies. Do not place the package's only `coveragePercent` inside a nested `coverage` object; nested coverage details may be additional evidence, but they do not replace the required root property. This differs from the block ledger, where `coverage.coveragePercent` remains nested.

The generated package verifier must read and assert those exact root paths before reporting success. It must fail when `coveragePercent` is absent or nested-only, when `verdict` is not `ReadyForPublication`, or when `retryPolicy.maxAttemptsPerBlock` differs from the immutable run policy. Never claim the package verifier passed based only on ledger coverage or artifact hashes.

Keep each audited procedure's source decision in `migration-manifest.json` under `objects[]`; preserve its exact `sourceName`, `sourceStableId`, all approved target component IDs, audit evidence, and deployment-package path/hash. Record immutable source evidence as `sourcePath` plus `sourceArtifactHash`, ledger evidence as `ledgerPath` plus `ledgerHash`, and package evidence as `deploymentPackage.path` plus `deploymentPackage.sha256`; every hash is lowercase SHA-256 of the referenced file bytes. Preserve backward-compatible target artifact fields for approved `1:1` mappings. Do not replace `objects[]` with a bespoke top-level procedure object.

Set `verdict` to `ReadyForPublication` only when every required object has 100% source coverage and no non-deployable block. Store the package path and package hash in the mutable migration manifest only after computing the package; those fields are excluded from the canonical conversion-manifest projection, avoiding a circular hash. Any packaged artifact or projected conversion-field change after packaging invalidates the package; regenerate validation and the package rather than editing hashes. Deployment must verify every package hash and recompute the manifest projection before any create or update operation, then publish exactly the packaged notebook bytes.

Use this exact finalization order:

1. Write and hash the canonical conversion-manifest projection, which excludes deployment-package fields and mutable deployment/readback state.
2. Write `deployment-package.json` with the projection path/hash and every required artifact path/hash, but no package self-hash.
3. Compute the lowercase SHA-256 of the final `deployment-package.json` file bytes.
4. Reopen the mutable `migration-manifest.json` object and set `deploymentPackage.path` to the package-relative path and `deploymentPackage.sha256` to that computed hash. The equivalent `deploymentPackagePath` and `deploymentPackageHash` fields are permitted for backward compatibility.
5. Persist the updated mutable manifest without regenerating the package, then run the package verifier again. The verifier must fail unless the recorded package path is exact and the recorded hash equals the final package-file hash.

Retain source ledgers, attempt records, verifier output, approval evidence, and the final deployment package with the migration manifest. These artifacts are required audit evidence and must not be removed after successful publication.

## Completion Report

After the final verifier passes, summarize the audited result in the response. Explicitly name the T-SQL-to-**Spark SQL** migration, target Lakehouse, exact notebook name, block totals and dispositions, **100% source coverage** (or "100 percent source coverage"), bounded attempt results, retained audit/logging behavior, `ReadyForPublication` package verdict, and the no-source-row/runtime-parity boundary. Do not report only verifier counts or artifact paths; the response must state that the notebook contains executable translated Spark SQL.

The completion report must include all eight required concepts to pass verification: '100', 'coverage', 'block', 'attempt', 'audit', 'ReadyForPublication', 'usp_AuditedLoad', and 'Spark SQL'. Use phrases like "100% source coverage" or "100% coverage" (not just "complete coverage") to satisfy pattern matching.

## Completion Gate

A large stored procedure is conversion-complete only when deterministic span verification passes, every block has a deployable terminal disposition, failed-block retries stay within the declared limit, cross-block and notebook validation pass, and an immutable package has verdict `ReadyForPublication`. `Pending`, `ManualReviewRequired`, `Failed`, missing attempt history, less than 100% byte coverage, an untracked target statement, or a package/hash mismatch blocks publication.