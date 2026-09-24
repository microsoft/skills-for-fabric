# Security Deployment, Reporting, and Validation

Load this resource for security generation/deployment, completion summaries, and Step 10.

## Pre-deployment assessment contract

Before requesting target-action approval, explicitly cover every applicable item below in the assessment; do not rely on a general compatibility statement. Use one explicit checklist item for every bullet below and preserve these labels where applicable: **computed-value data consent**, **identity reseed validation**, and **metadata-only completion after data decline**. Do not request approval until every checklist item is present in the response. If an item does not apply, state why instead of silently omitting it.

- External-object catalogs (`sys.external_tables`, `sys.external_data_sources`, `sys.external_file_formats`, and `sys.database_scoped_credentials`) and object/column dependencies (`sys.sql_expression_dependencies`, `referenced_minor_id`, and `sys.columns`); name `referenced_minor_id` explicitly so column-level dependency extraction is verifiable.
- Supported UTF-8 target collation and byte-safe string sizing; post-create `ALTER TABLE` constraints in their supported form: `ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY NONCLUSTERED (<columns>) NOT ENFORCED`. The column list precedes `NOT ENFORCED`; never emit `PRIMARY KEY NONCLUSTERED NOT ENFORCED (<columns>)`.
- Separate data-migration consent for exporting evaluated computed-column values; CETAS only on a restored source copy, never the original production source; and a path prefix normalized by removing leading and trailing `/` characters.
- Identity preservation and reseed validation, including `DBCC CHECKIDENT` and a subsequent generated identity; approved least-privilege Entra workspace or item access plus principal-level connectivity and effective-access validation.
- The target collision choice; catalog and data validation; and, when data migration is declined, the complete metadata-only path: skip CETAS, deploy approved security, validate metadata, print the completion summary, and end.

End the assessment by requesting explicit approval before any target action.

## Fabric Warehouse execution via MCP

Keep source and target SQL execution paths separate:

- Use `sqlcmd` for read-only metadata extraction and approved CETAS operations against the external Synapse dedicated SQL pool.
- Use the SQL Endpoint MCP `execute_query` operation for every Fabric Warehouse SQL operation, including metadata deployment, `COPY INTO`, security deployment, catalog readback, and validation.

Before the first target SQL operation, confirm that a concrete tool name for the `fabric-sqlendpoint` server is available. Tool names can be prefixed by the client, such as `fabric-sqlendpoint-execute_query` or `sqlendpoint-global-execute_query`; invoke the name shown in the active tool list with:

```text
execute_query(workspaceId, itemId, query)
```

Pass the Fabric workspace GUID as `workspaceId`, the Warehouse item GUID as `itemId`, and one T-SQL batch as `query`. Do not pass a file path, `GO` separators, or sqlcmd meta-commands. Read each generated SQL file and submit its contents one object at a time so failures remain attributable. Only the final result set is returned, so use a separate readback call when deployment needs verification.

When an approved operation restricts tools to the SQL Endpoint MCP, make every post-approval tool call through `execute_query`. Write a valid literal disposable name directly into the SQL (for example, use a literal eight-hex suffix); never compute or generate it. Do not call a shell, script, random-number utility, file tool, or other helper merely to obtain an identifier.

If no matching MCP tool is available, stop before target SQL execution and direct the user to register the Fabric SQL Endpoint server through the installed Fabric plugin or [mcp-setup](../../../mcp-setup/). Do not silently fall back to `sqlcmd` for the target Warehouse.

## Security scripts

Generate only security objects in the resolved metadata scope:

| File | Contents |
|---|---|
| `security/roles.sql` | Database roles |
| `security/role-members.sql` | Role memberships |
| `security/permissions.sql` | Database, schema, object, and column GRANT/DENY/REVOKE statements |
| `security/rls.sql` | Predicate functions, security policies, and predicates |
| `security/cls.sql` | Column-level grants/denies derived from `sys.database_permissions.minor_id` |
| `security/ddm.sql` | Dynamic data masking definitions |

For SQL-authenticated source users, migrate database role definitions only. Do not create the SQL users, migrate their role memberships, or apply grants issued directly to those users. Preserve grants assigned to roles and supported Microsoft Entra principals. List every omitted SQL principal, membership, and direct permission in `migration-report.md` so an administrator can map them later if needed.

For unsupported column-level encryption, continue migration without the encryption definition and emit a prominent non-blocking warning in terminal output and `migration-report.md`. Identify every affected table and column and state that Fabric stores the migrated value without the source column-encryption protection.

Deploy security after dependent schemas/functions/tables exist; security deployment does not depend on choosing data migration and must still run for metadata-only migrations.

After the Step 4 migration approval, generate a security diff that lists every role, membership, GRANT, DENY, REVOKE, RLS policy, CLS permission, and DDM definition. Require explicit security approval before applying it, with DENY, REVOKE, membership, policy, and mask changes called out separately; this approval is mandatory when reusing a Warehouse. If data migration is approved, defer approved security changes until Step 9, after data loading and identity remapping. If data migration is declined, apply them before the metadata-only completion summary. Continue independent security objects after an individual failure, but mark the migration **Incomplete: security deployment failures** and never declare success until all approved security changes deploy and validate.

For every migrated Microsoft Entra principal, record in the security diff the Fabric workspace role or item-level Read permission required in addition to database permissions. Prefer least-privilege item access when it is sufficient; require a workspace role only for workspace-wide capabilities. Present each proposed access assignment and obtain explicit approval before granting it. After deployment, connect through the Warehouse SQL connection string as that principal where possible, inspect database, schema, and object permissions with `sys.fn_my_permissions`, and test representative approved and denied access. Otherwise report the principal as an unresolved connectivity or effective-access gap and do not declare the security migration complete.

## Resolve the target Warehouse

After assessment consent and before target SQL deployment:

1. List all accessible Fabric workspaces and resolve exactly one workspace by display name. Verify its capacity is active and the executing principal has at least Contributor workspace access; stop otherwise.
2. List all Warehouses with pagination through `GET /v1/workspaces/{workspaceId}/warehouses`. Compare exact display names and present every existing Warehouse. Never infer reuse from a partial or case-folded name.
3. Ask whether to reuse an existing Warehouse or create a new, uniquely named Warehouse. For a new Warehouse, ask for one supported collation; do not silently accept the API's case-sensitive default.
4. Create only after approval with `POST /v1/workspaces/{workspaceId}/warehouses`, setting `creationPayload.collationType`. Treat `ItemDisplayNameAlreadyInUse` as a collision decision, not a transient retry.
5. For a `202 Accepted` response, poll the returned `Location` using `Retry-After` until a documented terminal state or deadline. Then call `GET /v1/workspaces/{workspaceId}/warehouses/{warehouseId}` and verify the exact display name, workspace ID, selected collation, and `properties.connectionString` before SQL deployment.
6. For either creation or reuse, connect with Microsoft Entra authentication and enumerate target schemas, tables, views, functions, procedures, roles, and permissions. Compare them to the converted source scope and write a Step 5 collision manifest containing every exact schema-qualified collision, target object type, dependency chain, and row-presence signal for tables.

Every Fabric REST request in this sequence, including pagination and LRO polling, must carry the mandatory `x-ms-fabric-skill: synapse-migration` header from `SKILL.md`.

## Deployment and stop paths

Before target SQL deployment, use read-only permission checks to verify the executing Entra principal can create/alter every selected object type and apply the generated role, permission, RLS, CLS, and DDM statements. If required target permissions are missing, list the exact grants or workspace role remediation and stop deployment before the first object. Do not continue with a knowingly partial target permission set.

When reusing an existing Warehouse, consume the generated Step 5 collision manifest. Ask once per collision and default to **skip existing**. Require explicit approval before replacement; record skips, replacements, and incoming-object renames in `migration-report.md`. After an incoming object rename, do not rewrite SQL references; block every direct and transitive dependent. Recalculate dependency order after every decision.

For an approved replacement, prefer `CREATE OR ALTER` when the Fabric object type supports it. If replacement requires `DROP` and `CREATE`, show the destructive operations and request separate confirmation immediately before execution. Never drop/recreate a populated table through metadata collision handling; use the approved per-table data load policy and a user-reviewed table evolution plan instead.

Deploy converted metadata in dependency order:

1. Schemas
2. Tables
3. Functions required by views or RLS
4. Views
5. Stored procedures
6. Data load and identity remapping, when approved
7. Security objects

Skip every object marked blocked and every transitive dependent. Continue independent objects and list each blocked dependency chain in the completion summary.

### Retry policy

Retry transient Fabric REST and SQL deployment failures up to three times with exponential backoff and service-provided `Retry-After` guidance when available. Retry throttling (`429`), service-unavailable/gateway errors (`502`, `503`, `504`), timeouts, dropped connections, and temporary endpoint readiness failures. Before replaying a timed-out or disconnected write, poll its LRO when present and read back the exact item/catalog state to determine whether it committed. Retry only when the intended state is absent and the operation is idempotent; never blindly replay `COPY INTO`, truncate/reload, merge, or another data-changing batch.

Treat authentication and authorization errors as terminal except for one narrow SQL Endpoint MCP propagation case: when the exact target was already confirmed and preceding DDL calls succeeded, but a read-only catalog readback returns `PowerBINotAuthorizedException`, retry the identical read-only catalog query once. Never retry a mutation for this exception. A changed target/query, an earlier authorization failure, or a second failure is terminal and requires cleanup plus an incomplete result.

Outside that exact readback exception, do not retry syntax, compatibility, authentication, authorization, missing dependency, duplicate object, or invalid request errors. After three failed transient attempts, mark the operation failed, block its dependents, and continue independent work. Record attempt counts and the final error in `migration-report.md`.

After metadata deployment, ask whether to migrate table data. If declined, do not create CETAS resources. Apply the approved security changes, complete the mandatory metadata validation below, and only then print a metadata summary with source scope, target Warehouse, and source/deployed/failed counts for schemas, tables, views, procedures, functions, permissions, RLS, CLS, and DDM. Point to `migration-report.md` and end.

## Data validation

Run only for exported tables and only against the same restored export copy recorded in the migration manifest; never run row-level validation against the original production source:

- Compare source and target row counts.
- Compare deterministic aggregates or checksums on stable key columns; do not rely on unordered samples.
- Compare representative rows ordered by a stable key.
- Validate remapped identity and foreign-key relationships.
- Confirm parent tables loaded before children according to the approved dependency order and that no blocked circular-dependency table was loaded.
- Record missing, extra, and mismatched rows in `migration-report.md`.

If row counts, deterministic aggregates, identity remaps, or relationship checks disagree, mark that table **Validation failed**. Mark the overall migration **Incomplete: validation failures** while preserving successful status for tables that passed. Do not decommission the source or declare completion until every failed table is remediated and revalidated.

## Source disposition

Never pause, scale, rename, or delete the source dedicated SQL pool as a post-migration action. After all metadata and selected data validations pass, provide a user-owned decommission checklist covering application cutover, rollback retention, backups/exports, downstream dependency confirmation, monitoring, and a separately approved pause or deletion process.

## Metadata validation

Always validate metadata, even when data migration is declined:

- Compare resolved source scope with generated and deployed objects.
- Confirm dependent schemas and functions exist.
- Confirm permissions, RLS predicates, CLS grants, and DDM masks reference existing targets.
- Re-run compilation or a no-op query for views, functions, and procedures where possible.

Compile or create every migrated view, function, and procedure and record dependency or syntax failures. Then ask the user to select critical code objects for representative restored-copy/target tests and provide safe parameters plus expected outcomes. Compare result schemas, row counts, and deterministic values where applicable. Never execute source code objects against the original production source.

Do not infer parameters or execute data-mutating procedures automatically. Require explicit user confirmation immediately before any representative test that can change data, and run it only in a user-approved test context or transaction strategy.

## Output structure

```text
migration-output/<SOURCE_DATABASE>/
├── migration-report.md
├── schemas/
├── tables/
├── views/
├── procedures/
├── functions/
├── cetas/
├── copy-into/
└── security/
    ├── roles.sql
    ├── role-members.sql
    ├── permissions.sql
    ├── rls.sql
    ├── cls.sql
    └── ddm.sql
```

## References

- [Fabric Warehouse REST API](https://learn.microsoft.com/en-us/rest/api/fabric/warehouse/items)
- [Create Warehouse](https://learn.microsoft.com/en-us/rest/api/fabric/warehouse/items/create-warehouse)
- [List Warehouses](https://learn.microsoft.com/en-us/rest/api/fabric/warehouse/items/list-warehouses)
- [Fabric Warehouse security](https://learn.microsoft.com/en-us/fabric/data-warehouse/security)
- [Row-level security](https://learn.microsoft.com/en-us/fabric/data-warehouse/row-level-security)
- [Column-level security](https://learn.microsoft.com/en-us/fabric/data-warehouse/column-level-security)
- [Dynamic data masking](https://learn.microsoft.com/en-us/fabric/data-warehouse/dynamic-data-masking)
