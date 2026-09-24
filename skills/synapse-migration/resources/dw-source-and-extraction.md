# Source Resolution and Metadata Extraction

Load this resource for Steps 1-2 only.

## Resolve the source

Normalize both source modes to these values:

```text
<SOURCE_SQL_SERVER>
<SOURCE_DATABASE>
```

### Synapse workspace mode

Required inputs: Azure subscription ID, Synapse workspace name, and one explicit pool name. List workspaces and pools and validate an exact pool match. If it is paused, stop and ask the user to resume it through a separately approved operator workflow; never resume it automatically. Then set:

```text
<SOURCE_SQL_SERVER> = <SYNAPSE_WORKSPACE_NAME>.sql.azuresynapse.net
<SOURCE_DATABASE>   = <POOL_NAME>
```

Use Synapse ARM API version `2021-06-01`. Do not default to all pools.

### Standalone mode

Required inputs: SQL server FQDN and database name from a redacted connection string. Remove an optional `tcp:` prefix and port suffix. Never request or persist passwords. Set:

```text
<SOURCE_SQL_SERVER> = <user-provided-server-fqdn>
<SOURCE_DATABASE>   = <user-provided-database-name>
```

Skip Synapse workspace discovery. Ensure the database is online through its owning Azure service.

### Select source authentication and validate connectivity

Support both source authentication methods:

- **Microsoft Entra** (default): use `sqlcmd -G` and the authenticated Azure identity.
- **SQL authentication**: use a supplied SQL login name. Never request, print, log, or persist the password. Run `sqlcmd` without `-P` so it prompts for the password directly in the terminal, or use an equivalent secure client prompt.

Do not place passwords in command arguments, environment files, generated SQL, reports, or chat prompts. Fabric Warehouse target connections always use Microsoft Entra authentication.

Entra validation:

```bash
sqlcmd -S "<SOURCE_SQL_SERVER>" -d "<SOURCE_DATABASE>" -G -Q "SELECT DB_NAME();"
```

SQL authentication validation:

```bash
sqlcmd -S "<SOURCE_SQL_SERVER>" -d "<SOURCE_DATABASE>" -U "<SOURCE_SQL_USER>" -Q "SELECT DB_NAME();"
```

Allow the terminal to prompt securely for the password.

Stop unless the returned database exactly matches `<SOURCE_DATABASE>`.

## Permission preflight

Before inventory, run read-only permission checks for catalog visibility and definition access, including `VIEW DEFINITION` and SELECT access to required catalog views. If the source principal cannot see the complete supported object inventory, list the exact missing permissions and stop Steps 2-4. Do not continue with a partial or best-effort metadata inventory.

## Resolve metadata scope

Default to all supported objects in the source database:

- Schemas and tables, including constraints and identity properties
- Views
- Stored procedures
- Scalar, inline table-valued, and table-valued functions
- External tables
- External data sources
- External file formats
- Database-scoped credential references and access identity metadata
- Roles, role memberships, object/schema/database permissions
- Row-level security (RLS), column-level security (CLS), and dynamic data masking (DDM)

Allow narrowing by schema, object type, or typed schema-qualified object name such as `view:reporting.SalesSummary`. Validate names against source catalogs. Discover dependencies and ask whether to include missing dependencies or mark the dependent object as blocked.

If valid user filters resolve to zero metadata objects, continue automatically as an explicit no-op. Do not fall back to all objects. Record zero selected objects and the applied filters, skip extraction/conversion/deployment work, and produce the assessment/completion report.

## Catalog extraction

Use `sys.tables`, `sys.schemas`, `sys.columns`, `sys.types`, `sys.identity_columns`, `sys.computed_columns`, `sys.key_constraints`, `sys.foreign_keys`, `sys.foreign_key_columns`, `sys.default_constraints`, `sys.check_constraints`, and partition catalog views to reconstruct table DDL. Always extract computed-column expressions, DEFAULT, CHECK, and partition definitions for tables in scope so each can be assessed.

Use `sys.sql_modules` joined to `sys.objects` and `sys.schemas` for views, procedures, and functions. Include object types `V`, `P`, `FN`, `IF`, and `TF`.

Dedicated SQL pool does not support triggers. Do not query `sys.triggers`, inventory trigger objects, or count triggers as migration blockers.

Build the dependency graph from `sys.sql_expression_dependencies` before scanning definition text. Resolve `referencing_id` through `sys.objects` and `sys.schemas`. For `OBJECT_OR_COLUMN` references (`referenced_class = 1`), resolve a non-null `referenced_id` through `sys.objects` and `sys.schemas`; when `referenced_minor_id > 0`, also join `sys.columns` on `object_id = referenced_id` and `column_id = referenced_minor_id` to preserve the referenced column. Treat `referenced_minor_id = 0` as an object-level dependency, and preserve other referenced classes without forcing them through `sys.objects`.

Preserve catalog-supplied server, database, schema, and entity names when `referenced_id` is null. Record caller-dependent, ambiguous, and unresolved local references as assessment blind spots. Record any non-null object or column ID that does not resolve through its required catalog join as an extraction failure.

After catalog dependency extraction, scan definitions for three-part database names, four-part linked-server names, external object calls, and dynamic SQL that constructs remote references. Add these supplemental dependencies with their referencing objects, but do not use text scanning as a substitute for `sys.sql_expression_dependencies` or its column joins.

Inventory source external objects with explicit read-only catalog queries:

- Use `sys.external_tables` joined to `sys.schemas`, `sys.columns`, and `sys.types` for each external table's schema, columns, location, data-source ID, and file-format ID.
- Query all rows from `sys.external_data_sources`, then link external tables by data-source ID; capture each source's name, type, location, and nullable credential ID.
- Query all rows from `sys.external_file_formats`, then link external tables by file-format ID; capture each format's name and properties.
- Query all rows from `sys.database_scoped_credentials`, then link data sources by non-null credential ID only; capture the credential name and identity metadata, but never retrieve, request, or persist its secret.

Preserve unreferenced catalog objects as well as the complete external-table-to-data-source, file-format, and credential reference chain. Record a non-null ID that does not resolve as an extraction failure; a null optional credential ID is valid and is not a failed join. Include dependent objects, and do not treat definition-text scanning as a substitute for these catalogs.

Use these security catalogs:

- `sys.database_principals` and `sys.database_role_members` for roles and memberships; generate custom-role definitions only where `type = 'R'`, `is_fixed_role = 0`, and `name <> 'public'`
- `sys.database_permissions`; use `minor_id` joined to `sys.columns` for CLS
- `sys.security_policies` and `sys.security_predicates` plus predicate function definitions for RLS
- `sys.masked_columns` for DDM

Apply the resolved metadata filters to every extraction query. Write one SQL file per object under `migration-output/<SOURCE_DATABASE>/` and persist the final resolved scope in `migration-report.md`.

Ignore source statistics completely. Do not inventory `sys.stats`, generate statistics scripts, count statistics in reports, or classify them as review items or blockers.

Skip source sequence objects. Do not generate `CREATE SEQUENCE` scripts or special sequence migration recommendations.

## Source-management references

- [Dedicated SQL pool (formerly SQL DW)](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/sql-data-warehouse-overview-what-is)
- [Dedicated pool compute management and pause/resume](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/sql-data-warehouse-manage-compute-overview)
- [Synapse SQL feature matrix](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/overview-features)
