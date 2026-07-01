# DBT-CORE.md — dbt Job Model, Adapters & Project Reference

Shared reference for the dbt (data build tool) skills. Covers the Fabric dbt job execution model,
the item-definition structure, the supportability matrix, per-adapter SQL generation for dbt Core
1.9, and dbt project layout. The consumption skill links here for the execution model; the authoring
skill links here for SQL generation and project structure.

## Table of contents
- [Execution model](#execution-model)
- [Supportability matrix](#supportability-matrix)
- [Adapter SQL](#adapter-sql)
- [Project structure](#project-structure)
- [Security: never write credentials](#security-never-write-credentials)

---

## Execution model

- A dbt job is a Fabric item of type **`DataBuildToolJob`** (preview).
- Its **definition** is a list of base64 parts:
  - the **config part** — `dbt-content.json` on the live API / `dbtjob-content.json` in docs;
    holds `project`, `profile`, and `command` settings. **Discover the name** from `getDefinition`
    (regex `dbt[\w-]*content\.json`) — do not hardcode.
  - **`Code/dbt/...`** — the dbt project files (`dbt_project.yml`, `models/*.sql`, `schema.yml`,
    `seeds/`, `snapshots/`), one part per file. (Absent for GitHub-sourced jobs.)
  - **`.platform`** — item metadata.
- `updateDefinition` **replaces the whole part list** → every change is read-modify-write.
- Runs are triggered with `POST .../items/{id}/jobs/instances?jobType=Execute` and polled to a
  terminal status (`Completed`/`Failed`/`Cancelled`/`Deduped`).

### Config part (`ContentDetails`) shape
```jsonc
{
  "project": {
    "projectType": "OneLake",              // "OneLake" | "Lakehouse" | "GitHubSourceControl"
    "folderPath": "dbt"
  },
  "profile": {
    "profileType": "DataWarehouse",        // DataWarehouse | SqlServer | PostgreSql | Snowflake
    "schema": "gold",
    // bind by GUID — either an external connection or workspace/artifact of the warehouse:
    "connectionSettings": {
      "name": "MyWarehouse",
      "properties": {
        "type": "DataWarehouse",
        "typeProperties": {
          "workspaceId": "<ws-guid>", "artifactId": "<warehouse-guid>",
          "endPoint": "<name>.datawarehouse.fabric.microsoft.com"
        }
      }
    }
    // or: "externalReferences": { "connection": "<connection-guid>" }
  },
  "command": { "operation": "build", "arguments": { "threads": 4, "failFast": true } }
}
```
`operation` ∈ `run | build | show | seed | compile | test | snapshot`. Command arguments:
`select`, `exclude`, `fullRefresh`, `failFast`, `threads`, `selectorName`.

---

## Supportability matrix

dbt Job Runtime **v1.0**, dbt Core **1.9**, Python **3.12**. Generate Core-1.9 SQL for all four.

| Target | Adapter (pip) | Adapter version | `profiles.yml` type | `profileType` |
|---|---|---|---|---|
| Fabric Warehouse | `dbt-fabric` | 1.9.0 | `fabric` | `DataWarehouse` |
| PostgreSQL | `dbt-postgres` | 1.9.0 | `postgres` | `PostgreSql` |
| Snowflake | `dbt-snowflake` | 1.9.0 | `snowflake` | `Snowflake` |
| Azure SQL Database | `dbt-sqlserver` | 1.8.5 | `sqlserver` | `SqlServer` |

Azure SQL pins adapter **1.8.5** (Core-1.9-only features like `microbatch` may be unavailable there —
prefer `delete+insert`/`merge`). Adapters evolve; verify edge cases at https://docs.getdbt.com.

---

## Adapter SQL

dbt mechanics are shared: models are `SELECT`s, dependencies use `{{ ref() }}`/`{{ source() }}`,
materialization comes from `{{ config() }}`, incremental models use `is_incremental()`. Only the
**dialect** and **supported strategies** differ.

**Incremental strategy support:**

| Strategy | Fabric DW | Azure SQL (1.8.5) | PostgreSQL | Snowflake |
|---|---|---|---|---|
| `append` | ✅ | ✅ | ✅ | ✅ |
| `delete+insert` | ✅ | ✅ | ✅ (default) | ✅ |
| `merge` | ⚠️ verify | ✅ | ✅ (PG 15+) | ✅ (default) |
| `insert_overwrite` | ❌ | ❌ | ❌ | ✅ |
| `microbatch` (1.9) | ⚠️ verify | ⚠️ likely no | ✅ | ✅ |

**Fabric Warehouse (`dbt-fabric`)** — restricted T-SQL. Use `varchar`/`char` (UTF-8),
`int/bigint`, `decimal(p,s)`, `float`, `bit`, `date`, `time`, `datetime2`, `uniqueidentifier`,
`varbinary`. **Avoid** `nvarchar`/`ntext`/`text`, `datetime`/`smalldatetime`, `money`, `xml`,
`geography`. No enforced constraints/identity. `table` builds via CTAS. Incremental: `append` /
`delete+insert`; treat `merge`/`microbatch` as "verify".

**Azure SQL / SQL Server (`dbt-sqlserver`)** — full T-SQL: `nvarchar`, `datetime2`, `MERGE`,
enforced constraints. Incremental: `append`/`delete+insert`/`merge`. Avoid relying on `microbatch`.

**PostgreSQL (`dbt-postgres`)** — `text`/`varchar`, `numeric`, `boolean`, `timestamptz`, `jsonb`,
`||` concat. Incremental: `append`/`delete+insert`(default)/`merge`(PG15+)/`microbatch`.

**Snowflake (`dbt-snowflake`)** — `varchar`/`number`/`variant`/`timestamp_ntz`; `qualify`, `::`
casts, `transient`, `cluster_by`. Incremental: `merge`(default)/`append`/`delete+insert`/
`insert_overwrite`/`microbatch`.

**Porting checklist:** switch `profiles.yml` type + `profileType`; re-map types (classic Fabric
fixes: `nvarchar`→`varchar`, `datetime`→`datetime2`, `money`→`decimal(19,4)`); confirm the
incremental strategy is supported (downgrade to `delete+insert` when unsure); translate dialect
functions (`||` vs `+` vs `concat`, `qualify`, `iff`); re-validate.

---

## Project structure

Standard dbt layout (Core 1.9):
```text
<project>/
├── dbt_project.yml     # name, profile, model-paths, per-folder materialization defaults
├── profiles.yml        # ADAPTER TYPE + env_var() placeholders only — NO secrets
├── models/
│   ├── staging/        # 1:1 with sources, usually views
│   ├── marts/          # business entities, usually tables/incremental
│   └── schema.yml      # sources, model docs, tests (this is the data-model schema)
├── seeds/              # optional CSV reference data
└── snapshots/          # optional SCD-2 (YAML snapshots in 1.9)
```
- Pin the project: `require-dbt-version: [">=1.9.0", "<1.10.0"]`.
- `schema.yml` uses the Core-1.9 `data_tests:` key; built-ins: `not_null`, `unique`,
  `accepted_values`, `relationships`. Parse it first when updating a project.
- Core 1.9 features: `microbatch` incremental strategy, YAML snapshots, `dbt_valid_to_current`.

---

## Security: never write credentials

The Fabric **Connection** object holds every secret; the dbt job references targets **by connection
GUID**. Therefore:
- `dbt-content.json` binds via `externalReferences.connection` or `typeProperties.{workspaceId,
  artifactId}` — never a username/password/account/host secret/connection string.
- `profiles.yml` (needed only for local `dbt parse`/`compile`) uses `{{ env_var('DBT_...') }}` for
  every sensitive field, left unset in the file.
- GitHub sourcing: the classic **PAT** lives only in the `GitHubSourceControl` connection, never in
  a file. If it rotates, update the connection.
