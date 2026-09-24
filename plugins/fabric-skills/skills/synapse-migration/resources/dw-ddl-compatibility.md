# DDL Compatibility and Conversion

Load this resource for Steps 3-4 only.

## Classification

- **Auto-fixed**: safe mechanical conversion.
- **Needs review**: add `-- MIGRATION REVIEW:` to the generated SQL and report it.
- **Blocker**: no safe conversion; do not deploy that object.

## Table conversion

- Remove `DISTRIBUTION = HASH(...)`, `ROUND_ROBIN`, and `REPLICATE`; Fabric manages distribution.
- Remove clustered columnstore, clustered, and nonclustered index definitions.
- Remove dedicated-pool partition clauses and create one regular Fabric table. If data migration is separately approved, export the selected source rows across every partition; otherwise preserve only the schema. Warn that partition boundaries, switching/maintenance operations, and source partition-based performance behavior are not preserved.
- Convert every computed column to a regular stored target column. Report the source table, column, expression, target type, and loss of automatic recomputation. If data migration and preservation of the computed value are separately approved, include its evaluated source value in the approved export projection; otherwise preserve only the stored target-column schema and do not read or export source row values. Ask whether the user wants a separate view that reproduces the original computed expression; generate that view only after validating the expression against Fabric T-SQL and receiving approval.
- Create all tables without inline source primary-key, unique-key, or foreign-key constraints. After every referenced table exists, emit separate `ALTER TABLE ... ADD CONSTRAINT` statements: primary and unique keys as `NONCLUSTERED NOT ENFORCED`, and foreign keys as `NOT ENFORCED`. Order these statements by the foreign-key dependency graph; for a cycle, create every table first and then apply the cycle's constraints. Record and block any constraint whose referenced table or columns did not deploy.
- Do not deploy DEFAULT or CHECK constraints: the current Fabric Warehouse table-constraint surface supports only primary, foreign, and unique keys in their documented unenforced forms, and explicitly does not support DEFAULT constraints. Record every source DEFAULT/CHECK definition. If equivalent behavior requires application, pipeline, or procedure logic, classify that redesign as Needs review; otherwise classify the missing invariant as a Blocker for dependent writes.
- Map unsupported persisted data types:

| Source | Fabric | Classification |
|---|---|---|
| `money` | `decimal(19,4)` | Auto-fixed |
| `smallmoney` | `decimal(10,4)` | Auto-fixed |
| `datetime`, `smalldatetime` | `datetime2(6)` | Auto-fixed |
| `tinyint` | `smallint` | Auto-fixed |
| `binary(n)` | `varbinary(n)` | Auto-fixed |
| `datetimeoffset` | `datetime2(6)` | Needs review: offset lost |
| `nchar(n)`, `nvarchar(n)` | `char(n)`, `varchar(n)` | Needs review: require a supported UTF-8 collation on the target Fabric Warehouse and size the target column from observed and worst-case UTF-8 byte requirements; ASCII is 1 byte and non-ASCII Unicode scalar values can require up to 4 bytes; widen with approval |
| `nvarchar(max)` | `varchar(max)` | Needs review: require a supported UTF-8 target collation and validate encoded byte size against the current 16 MB limit |

For any unsupported source type not listed above (for example geography, geometry, XML, hierarchyid, CLR/user-defined types, or another unsupported persisted type), propose documented Fabric alternatives per column and ask the user to approve a mapping. Do not default everything to `varchar` and do not silently drop columns. If no mapping is approved, block the table and its dependents and record the source type, proposed alternatives, and decision.

Do not convert `nchar` or `nvarchar` until the target Warehouse has an explicitly selected supported UTF-8 collation and the mapped width is byte-safe for the approved data domain. Measure representative encoded values, calculate the worst-case UTF-8 requirement, document truncation risk, and obtain approval for widening. Block the affected table when a safe supported width or collation cannot be established.

Fabric `IDENTITY` is preview, supports only `bigint IDENTITY`, and does not support custom seed/increment values. `SET IDENTITY_INSERT` supports explicit value insertion. Mark identity conversion as Needs review and require approval before preserving source keys through explicit insertion; validate key uniqueness, range, dependent foreign-key relationships, reseeding, and a subsequent generated value in an approved test context.

## Code object conversion

- Remove distribution clauses, index DDL, and `SET RESULT_SET_CACHING`.
- Remove workload-management definitions and resource-class references. Keep supported `OPTION (LABEL=...)` usage.
- Do not rewrite `NEXT VALUE FOR` or other sequence references. Sequence objects are excluded from migration; code objects retaining sequence references proceed through normal target compilation validation and fail there if unsupported or unresolved.
- For every cross-database or linked-server reference, ask the user to map the source server/database/object to a Fabric-accessible Warehouse, Lakehouse SQL endpoint, shortcut-backed table, or other approved target. Block the referencing object and its dependents until all mappings are approved. Rewrite only explicit, unambiguous references, then show the before/after mapping and validate target compilation. Never guess mappings or silently remove remote joins/calls.
- Dedicated SQL pools do not support DML or DDL triggers, so none are expected in this migration path. If discovery unexpectedly returns a trigger, stop and verify that the selected source is actually a dedicated SQL pool; report the trigger as a source-scope blocker and do not generate a target trigger definition.
- For each source external table, ask whether to keep the data in place through an approved OneLake shortcut/Lakehouse mapping or materialize it into a regular Fabric Warehouse table through a user-approved copy method. Remove Synapse external data source/file format DDL only after the replacement is selected. Block dependent objects until the shortcut target or materialized table exists and its schema is validated.
- Convert materialized views to regular views automatically. Remove materialized-view-only syntax, preserve the SELECT definition, and add a prominent warning that physical materialization, refresh behavior, storage, and source performance characteristics are not preserved. Record every conversion in `migration-report.md`.
- Block multi-statement TVFs and non-inlineable scalar UDFs pending redesign. Propagate the blocker to views, procedures, functions, RLS predicates, or other objects that depend on the blocked function. Continue converting independent objects; never generate a placeholder implementation.
- For SQL-authenticated users, generate role definitions only; omit user creation, memberships, and direct user grants, and report every omission.
- Column-level encryption is unsupported in Fabric Warehouse. Omit the encryption metadata, continue migrating the affected table, and add a prominent non-blocking assessment warning that the target column data will not retain source encryption protection.

## DMV conversion

Only auto-replace direct monitoring equivalents, and review column differences:

| Synapse | Fabric |
|---|---|
| `sys.dm_pdw_exec_requests` | `sys.dm_exec_requests` or `queryinsights.exec_requests_history` |
| `sys.dm_pdw_exec_sessions` | `sys.dm_exec_sessions` or `queryinsights.exec_sessions_history` |
| `sys.dm_pdw_exec_connections` | `sys.dm_exec_connections` |

Remove distribution and workload-management references that are unnecessary in Fabric. Treat these families as blockers unless manually rewritten:

- `sys.dm_pdw_request_steps`, `sys.dm_pdw_sql_requests`, `sys.dm_pdw_dms_*`
- `sys.dm_pdw_wait*`, `sys.dm_pdw_nodes*`, `sys.dm_pdw_resource_waits`, `sys.dm_pdw_errors`
- PolyBase compute/distributed/DMS/external DMVs
- `sys.pdw_nodes_*`, mapping, loader, and materialized-view catalog families

Use Fabric Query Insights for post-migration history and performance analysis.

## Assessment report

Compare source and selected target collations. Report case-sensitivity, UTF-8 byte semantics, string-comparison, uniqueness, and explicit `COLLATE` risks. Preserve only explicit collations supported by Fabric and flag unsupported clauses for review.

Report source inventory, resolved scope, converted/deployed counts by object type, DEFAULT/CHECK compatibility, collation risks, auto-fixes, review items, blockers, blocked dependency chains, every data-type conversion, security gaps, and DMV compatibility. Require explicit user confirmation before provisioning the Fabric Warehouse.

## References

- [Migration planning: dedicated SQL pool to Fabric Warehouse](https://learn.microsoft.com/en-us/fabric/data-warehouse/migration-synapse-dedicated-sql-pool-warehouse)
- [Fabric Warehouse T-SQL surface area](https://learn.microsoft.com/en-us/fabric/data-warehouse/tsql-surface-area)
- [Fabric Warehouse data types](https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types)
- [Fabric Warehouse limitations](https://learn.microsoft.com/en-us/fabric/data-warehouse/limitations)
- [Fabric Warehouse table constraints](https://learn.microsoft.com/en-us/fabric/data-warehouse/table-constraints)
- [Fabric Warehouse collation](https://learn.microsoft.com/en-us/fabric/data-warehouse/collation)
- [Migrate IDENTITY columns](https://learn.microsoft.com/en-us/fabric/data-warehouse/migrate-identity-columns)
