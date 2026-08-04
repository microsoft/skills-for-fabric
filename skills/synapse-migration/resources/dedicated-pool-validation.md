# Dedicated Pool Validation

Validate converted artifacts locally and compare deployed Lakehouse schema metadata with the Synapse source catalog. Validation does not create or execute notebooks and does not read or compare source/target table rows.

## Validation Layers

| Layer | Check | Execution surface | Blocking |
|---|---|---|---|
| L1 | Python and SQL syntax | Local AST plus target Spark parser | Yes |
| L2 | Schema names, types, precision, scale, nullability | Source catalog plus Livy/SQL endpoint | Yes |
| L3 | Object coverage, dependencies, parameters, and conversion dispositions | Manifest plus generated artifacts | Yes |
| L4 | Notebook definition and publication status | Fabric Items API | Yes |

## Local Checks

- Parse every `.py` artifact with Python `ast.parse`.
- Reject unresolved placeholders, embedded secrets, and hardcoded workspace or item IDs.
- Confirm every manifest dependency exists.
- Verify every source object has a target, skip reason, or manual-review status.

## Source-to-Target Schema Comparison

For each converted table definition, compare metadata only:

- Column count and ordered schema mapping
- Column names, mapped types, precision, and scale
- Nullability and supported defaults
- Table, schema, view, and dependency names
- Unsupported constraints and physical-design features recorded in the gap report

Do not run row-count, aggregate, sample, hash, or business-result queries.

## Logic Artifact Validation

Validate generated Python with `ast.parse`, Spark SQL with the target parser, notebook JSON with nbformat rules, parameter declarations against source metadata, and dependencies against the manifest. Query the Fabric Items API to confirm that notebooks published during deployment have the expected definition and Lakehouse binding; do not create, update, or execute notebooks during validation. Record unsupported behavior and manual-review requirements without claiming behavioral equivalence.

## Report

Produce a concise report containing:

- Source and target identifiers
- Object totals by status and complexity tier
- Schema comparison and artifact-validation results
- Conversion warnings and accepted structural differences
- Manual-review items
- Artifact-readiness verdict
- Explicit statement that data migration, data parity, runtime behavior, and cutover readiness were not validated

## Completion Gate

Artifact readiness is blocked by syntax failures, missing required objects, schema mismatches, publication failures, or unresolved T4 redesigns. Production cutover is always outside this skill because data migration and data-equivalence validation are excluded.
