# CETAS Export and COPY INTO

Load this resource for Step 5 only after the user explicitly approves table-data migration at the Step 4 consent gate.

## Resolve export scope and destination

Collect the ADLS Gen2 account, writable container, and optional path prefix (default `migration`). Normalize the prefix by removing leading and trailing `/` characters, reject an empty result, and use the normalized value as `<PATH_PREFIX>`; the URI templates supply their own separators. List eligible deployed tables and ask for all migrated tables (default), selected schemas, or selected `schema.table` names. Confirm the resolved list before generating scripts.

If valid data filters resolve to zero eligible tables, continue automatically as an explicit no-op. Do not fall back to all migrated tables. Record the filters and zero-table result, skip CETAS and COPY generation, and continue to security deployment and metadata validation.

## Consistent export source

Do not run a final multi-table CETAS export against a production database that continues to receive writes. Require the user to create a restore point and restore it to a separate user-managed dedicated SQL pool/database, then provide that restored server FQDN and database name. A restore uses a new pool/database name; it is not an in-place snapshot.

Validate `DB_NAME()` against the restored database and use the restored connection for all export setup DDL, CETAS statements, and source-side data/result validation. Record immutable original-source and mutable export-copy identities, the restore-point timestamp or label, restored server/database, and export start/end times in `migration-report.md`. Hard-block every setup or CETAS mutation when the resolved restored server/database equals the original source identity. The skill must not create, pause, or delete the restored copy; its lifecycle remains user-owned.

Generate scripts only for successfully deployed Fabric tables. Every CETAS folder must be empty, unique, end in `/`, and match its later `COPY INTO` path.

Before every initial or incremental export, verify that each resolved table folder is empty. If a folder already contains files or subfolders, stop CETAS for that table and ask the user to clear it manually or provide a different path. Never delete prior exports, generate an automatic run folder, or overwrite files.

## CETAS authentication

Ask the user to choose one authentication method after data-migration consent. For standalone dedicated SQL pools, support all four options in this preference order:

1. **Microsoft Entra passthrough** — preferred when the executing Entra principal can write to the destination. Do not create a database-scoped credential; omit `CREDENTIAL` from the external data source where passthrough is supported.
2. **Service principal** — use a database-scoped credential backed by an Entra application. Grant the service principal storage RBAC and required ADLS path ACLs.
3. **Shared access signature (SAS)** — use a database-scoped credential with `IDENTITY = 'SHARED ACCESS SIGNATURE'`. Remove the leading `?` and require Read, Create, Write, and List permissions.
4. **Storage account key** — use a database-scoped credential containing the account name and key. Treat this as the least-preferred fallback because it grants broad, long-lived access.

Source-specific options:

- Synapse workspace: workspace managed identity, service principal, SAS, storage key, or Entra passthrough where supported.
- Standalone dedicated SQL pool (formerly SQL DW): do not assume a workspace identity. Use the user's selected Entra passthrough, service principal, SAS, or storage key method.

Never request, print, log, or persist a service-principal secret, SAS token, or storage key. Have the user enter secret values directly into their terminal or SQL client; generated files must contain placeholders only. Confirm the selected principal can list and write the destination before generating CETAS scripts.

### Protected or cross-tenant ADLS

If the ADLS destination is firewall-protected or in a different Microsoft Entra tenant, do not generate or run CETAS for that destination. Mark the CETAS path unavailable and recommend **Fabric Copy Job** configured with a supported virtual network gateway, on-premises data gateway, or other approved network path. Let the user configure and run the Copy Job; record the fallback and affected tables in `migration-report.md`.

## CETAS setup

Only on the separately approved restored export copy, create or reuse a database master key, database-scoped credential, Parquet external file format, external data source, and staging schema, then create the CETAS external tables. Never run this setup against the original production source. For dedicated SQL pool CETAS to ADLS Gen2, use the documented dedicated-pool external-data-source syntax and selected credential. Do not blindly recreate existing objects.

Before generating setup, preflight `CREATE TABLE`, `ALTER SCHEMA`, `ADMINISTER BULK OPERATIONS`, `ALTER ANY EXTERNAL DATA SOURCE`, `ALTER ANY EXTERNAL FILE FORMAT`, SELECT on every source table, and access to the selected credential. If any permission is missing, list the exact missing grants and stop data export only; retain the completed metadata migration.

Generate authentication-specific setup from the selected method. For Entra passthrough, omit both the database-scoped credential and the external data source `CREDENTIAL` property. For service principal, SAS, storage key, or workspace managed identity, use the documented dedicated-pool credential identity and external-data-source form for that method; never substitute one method's template for another. Example credential-backed shape:

```sql
CREATE EXTERNAL FILE FORMAT [MigrationParquet]
WITH (FORMAT_TYPE = PARQUET, DATA_COMPRESSION = 'org.apache.hadoop.io.compress.SnappyCodec');

CREATE EXTERNAL DATA SOURCE [MigrationStaging]
WITH (
    TYPE = HADOOP,
    LOCATION = 'abfss://<CONTAINER>@<STORAGE_ACCOUNT>.dfs.core.windows.net/<PATH_PREFIX>/<SOURCE_DATABASE>',
    CREDENTIAL = [<SOURCE_STORAGE_CREDENTIAL>]
);
```

Generate one CETAS statement per selected source table and export all of its source rows across every source partition. Never treat a source partition boundary as a row-selection filter. Never use `SELECT *`: derive an explicit ordered projection from the approved conversion manifest. Cast mapped types, preserve legacy identity keys, and include any separately approved value needed to retain otherwise-lost semantics. Generate the target table and `COPY INTO` column mapping from the same manifest so the exported Parquet schema and target columns cannot drift.

```sql
CREATE EXTERNAL TABLE [staging].[dbo_FactSales_export]
WITH (
    LOCATION = 'dbo/FactSales/',
    DATA_SOURCE = [MigrationStaging],
    FILE_FORMAT = [MigrationParquet]
)
AS
SELECT
    [SaleId] AS [LegacySaleId],
    CAST([Amount] AS decimal(19,4)) AS [Amount],
    [SaleDate]
FROM [dbo].[FactSales];
```

CETAS writes Parquet to ADLS. Do not use CTAS and do not add a distribution clause.

### Source metadata cleanup

Generate `cetas/99-cleanup.sql` containing ordered `DROP EXTERNAL TABLE` statements for generated staging tables and, only when proven migration-owned and unshared, optional drops for the generated external data source, file format, credential, and staging schema. Never execute this cleanup script automatically and never delete ADLS export files. The user reviews and runs cleanup separately after validation.

### CETAS-incompatible tables

Before generating CETAS, identify tables with LOB values larger than 1 MB or documented Parquet character limitations. Exclude each affected table from CETAS and its matching `COPY INTO` generation, mark it blocked from the CETAS path, and show the exact reason.

Ask the user which alternative tool they want to use for each affected table. Recommend **Fabric Copy Job** because it supports Azure Synapse SQL Pool as a source, Fabric Warehouse as a destination, table/column selection, full or incremental copies, mappings, and append/overwrite/merge methods. Do not create or run a Copy Job without explicit user direction. Record the selected fallback tool and ownership in `migration-report.md`.

## COPY INTO

Preflight target-side source access separately from the CETAS writer's access. Choose the `COPY INTO` storage identity and verify that it can list and read the exact exported ADLS container and path before generating or executing any load statement:

- With no `CREDENTIAL` clause, verify that the Entra identity executing `execute_query` has **Storage Blob Data Reader** (or higher) and the required ADLS directory traverse/read ACLs.
- With `CREDENTIAL = (IDENTITY = 'Workspace Identity')`, verify that the resolved Fabric workspace identity has **Storage Blob Data Reader** (or higher) and the required ADLS directory traverse/read ACLs. Also verify that the executing user can use the workspace identity and has the required target-table `INSERT` permission.

Treat this read authorization as independent from the source-side CETAS write authorization; do not assume the CETAS credential or principal is available to Fabric Warehouse. If the selected target identity cannot list or read the exact export path, report the missing RBAC role or ACL and stop before `COPY INTO` without changing target data.

Generate one matching script per exported table:

```sql
COPY INTO [dbo].[FactSales]
FROM 'https://<STORAGE_ACCOUNT>.dfs.core.windows.net/<CONTAINER>/<PATH_PREFIX>/<SOURCE_DATABASE>/dbo/FactSales/*.parquet'
WITH (FILE_TYPE = 'PARQUET');
```

Execute the generated statement against the resolved Fabric Warehouse with the SQL Endpoint MCP `execute_query(workspaceId, itemId, query)` operation. Do not use `sqlcmd`, a TDS endpoint, or target Warehouse credentials for this step. Follow [SQLDW-AUTHORING-CORE.md](../../../common/SQLDW-AUTHORING-CORE.md) for `COPY INTO` semantics and Fabric Warehouse limitations.

### Existing target table policy

When the target table already exists, inspect whether it contains rows and ask the user to choose per table:

- **Skip** (default): do not load data; record the skip.
- **Append**: use `COPY INTO` and warn that duplicate prevention is the user's responsibility.
- **Truncate and reload**: require explicit destructive confirmation immediately before truncation, then load the full export.
- **Staged merge**: require user-provided stable business key columns and deduplication rules; load into a staging table, validate key uniqueness, then merge/update the target according to the approved rules.

If no answer is provided, skip the table. Never infer a merge key from an unenforced primary key without user confirmation. Record the selected policy, row counts, and any duplicate-key findings in `migration-report.md`.

For identity tables, stage and validate source keys as non-null, unique `bigint` values before loading. When explicit key preservation is approved, use `SET IDENTITY_INSERT` around the final insert, preserve the source identity values, validate parent/child relationships, and turn `IDENTITY_INSERT` off. Then run `DBCC CHECKIDENT ('schema.table', RESEED)`, record the result and maximum migrated key, and validate that a subsequently generated identity does not overlap any migrated value; do not require sequential values or a configured increment. Perform that validation insert against the migrated target only in an explicitly approved test context where it is rolled back or deleted afterward; never leave the probe row in the migrated target. Otherwise leave the identity migration incomplete. If explicit preservation is unsafe or declined, retain an approved legacy-key column, build and validate the parent legacy-to-target mapping, remap child foreign keys, and reject orphaned or duplicate mappings. Keep the legacy column unless the user separately approves a cleanup plan after all relationship validation passes.

## Referential load order

Build a table dependency graph from the resolved foreign-key metadata and load parent tables before child tables using a topological order. A child table that references a remapped identity key must wait until the parent legacy-to-target key mapping is complete and validated.

If the selected graph contains a circular dependency, do not choose an arbitrary order. Block every table in that cycle, show the cycle path and affected foreign keys, and ask the user to provide an approved cycle-breaking strategy. Continue loading independent acyclic tables. Record the final load order, blocked cycles, and identity-map dependencies in `migration-report.md`.

## References

- [Restore a Synapse workspace dedicated SQL pool](https://learn.microsoft.com/en-us/azure/synapse-analytics/backuprestore/restore-sql-pool)
- [Restore a standalone dedicated SQL pool](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/sql-data-warehouse-restore-active-paused-dw)
- [CETAS in Synapse SQL](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-tables-cetas)
- [CREATE EXTERNAL TABLE AS SELECT](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-external-table-as-select-transact-sql?view=azure-sqldw-latest&preserve-view=true)
- [CREATE EXTERNAL DATA SOURCE for dedicated SQL pool](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-external-data-source-transact-sql?view=azure-sqldw-latest&preserve-view=true)
- [Synapse storage authorization](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-storage-files-storage-access-control)
- [Dedicated-pool migration methods](https://learn.microsoft.com/en-us/fabric/data-warehouse/migration-synapse-dedicated-sql-pool-methods)
- [COPY INTO](https://learn.microsoft.com/en-us/sql/t-sql/statements/copy-into-transact-sql?view=fabric)
- [What is Fabric Copy Job](https://learn.microsoft.com/en-us/fabric/data-factory/what-is-copy-job)
- [Create a Fabric Copy Job](https://learn.microsoft.com/en-us/fabric/data-factory/create-copy-job)
