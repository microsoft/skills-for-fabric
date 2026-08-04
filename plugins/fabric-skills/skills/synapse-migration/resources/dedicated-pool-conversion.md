# Dedicated Pool T-SQL Conversion

Convert extracted Synapse objects into Spark SQL/PySpark artifacts for Fabric Lakehouse execution and generated Fabric notebooks for stored procedures.

## Inputs and Outputs

**Inputs**
- Source SQL files or catalog definitions
- Object inventory, dependencies, and complexity tier
- Approved `migration-gap-report.json` with accepted scope and dispositions
- Target schema naming policy

**Outputs**
- `schema/*.sql`: idempotent Spark SQL Delta DDL
- `logic/*.py`: reusable PySpark modules generated from non-procedural source logic
- `notebooks/*.ipynb`: one parameterized Spark SQL/PySpark Fabric notebook per stored procedure
- `migration-manifest.json`: source object, target artifact, dependencies, tier, status, warnings, and validation cases

Generate notebook content only from discovered stored-procedure definitions, dependency metadata, and approved conversion dispositions.

## Conversion Rules

| Source pattern | Target pattern |
|---|---|
| `CREATE TABLE ... DISTRIBUTION` | `CREATE TABLE IF NOT EXISTS ... USING DELTA`; omit MPP distribution and index clauses |
| `CTAS` | Generate a non-executed Spark SQL/PySpark conversion artifact; do not materialize data |
| `MERGE` | Generate non-executed Delta `MERGE INTO` logic with explicit match clauses |
| Temp tables | Local DataFrames or uniquely named temporary views within one Livy session |
| Stored procedure parameters | Fabric parameter cell values with source-compatible types, consumed by Spark SQL/PySpark cells |
| Output parameters | Structured Python return values |
| Transactions | Idempotent stages and Delta atomic writes; redesign multi-statement transaction assumptions |
| Cursors and loops | Set-based DataFrame transformations; mark irreducible cases for redesign |
| Dynamic SQL | Resolve bounded variants explicitly; mark unbounded generation as manual review |
| Views | Spark SQL view definitions where supported; otherwise generate a non-executed redesign artifact |

Preserve decimal precision, nullability, timestamps, identifiers, and source dependencies. Record unsupported constraints instead of implying they are enforced.

## Tier Strategy

- **T1**: deterministic conversion; syntax validation required.
- **T2**: deterministic conversion plus schema mapping and parser tests.
- **T3**: convert one object at a time with dependency context and targeted static tests.
- **T4**: produce a redesign note and testable skeleton; do not claim automatic parity.

## Artifact Requirements

- Make schema DDL idempotent.
- Parameterize workspace, Lakehouse, schema, and environment values.
- Keep secrets out of generated artifacts.
- Emit one manifest record per source object.
- Include source-to-target type mappings and conversion warnings.
- Use valid nbformat v4 JSON with Fabric Lakehouse dependency metadata and explicit `outputs`, `execution_count`, and cell metadata.
- Validate notebook JSON, compile Python code cells with `ast.parse`, and validate Spark SQL cells against the target Spark parser before deployment.
- Publish each successful notebook as a Fabric Notebook item through a definition payload using `format: ipynb` and `notebook-content.ipynb`.
- Do not execute generated transformations or notebooks, export source rows, or populate target tables.

## Completion Gate

Do not start conversion when either migration gap report is missing or unapproved. An object is deployable only when its discovery gaps have dispositions, its dependencies are resolved, generated artifacts parse, and required review flags are acknowledged.
