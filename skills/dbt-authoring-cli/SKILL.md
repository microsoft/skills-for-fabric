---
name: dbt-authoring-cli
description: >
  Create, configure, update, deploy, and run dbt (data build tool) jobs (DataBuildToolJob) in
  Microsoft Fabric via `az rest`, and generate dbt Core 1.9 SQL models for the supported adapters
  (Fabric Warehouse, Azure SQL Database, PostgreSQL, Snowflake).
  Use when the user wants to:
    1. Create or configure a Fabric dbt job (connection, schema, run command)
    2. Generate or port dbt models (.sql) / schema.yml / dbt_project.yml for a specific adapter
    3. Deploy a local dbt project into a job (Code/dbt/* definition parts) with read-modify-write
    4. Add tests, sources, incremental logic, or snapshots to a dbt project
    5. Connect a dbt job to an existing GitHub repository as the code source (run-only)
    6. Trigger a dbt run (build/run/test/seed/snapshot/compile) and monitor it
  Triggers: "create dbt job", "set up dbt in Fabric", "make a dbt model for my Fabric warehouse",
  "port this dbt model to Snowflake", "add an incremental model", "deploy dbt project",
  "update my dbt job", "connect dbt job to github", "run dbt build in Fabric", "dbt authoring"
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering.
> 2. To find the item details (including its ID) from workspace ID, item type (`DataBuildToolJob`), and item name: list all items of that type in that workspace and, then, use JMESPath filtering.
> 3. **Never write credentials into config.** A dbt job binds its target and its GitHub source **by connection GUID**; the secret lives in the Fabric Connection object. No password, account, token, or connection string ever goes into `dbtjob-content.json`, `profiles.yml`, or any project file.
> 4. **`updateDefinition` replaces the entire part list.** Read-modify-write every time (getDefinition → keep all existing parts → change what you need → updateDefinition) or you will delete the project files.

# dbt-authoring-cli — Author, Deploy & Run Fabric dbt Jobs via CLI

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [resolve workspace/item IDs; use `type=DataBuildToolJob`] |
| Fabric Topology & Key Concepts | [COMMON-CORE.md § Fabric Topology & Key Concepts](../../common/COMMON-CORE.md#fabric-topology--key-concepts) | |
| Environment URLs | [COMMON-CORE.md § Environment URLs](../../common/COMMON-CORE.md#environment-urls) | |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401; use `https://api.fabric.microsoft.com` |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | List Items, Item Creation, definition APIs |
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro) | Create/getDefinition/updateDefinition/run are LROs |
| Item Definitions envelope | [ITEM-DEFINITIONS-CORE.md § Definition Envelope](../../common/ITEM-DEFINITIONS-CORE.md#definition-envelope) | Base64 parts, `.platform` file |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** |
| Long-Running Operations (LRO) Pattern | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern) | Poll `Location` / `operations/{id}` |
| dbt job execution model & definition | [DBT-CORE.md § Execution model](../../common/DBT-CORE.md#execution-model) | Item type, `Code/dbt/*` parts, content part name, connection binding |
| Supportability matrix (adapters) | [DBT-CORE.md § Supportability matrix](../../common/DBT-CORE.md#supportability-matrix) | dbt Core 1.9; adapter versions & profileType per target |
| Adapter SQL generation | [DBT-CORE.md § Adapter SQL](../../common/DBT-CORE.md#adapter-sql) | Types, materializations, incremental strategies, porting |
| dbt project structure | [DBT-CORE.md § Project structure](../../common/DBT-CORE.md#project-structure) | dbt_project.yml, profiles.yml (no secrets), schema.yml, 1.9 features |
| Authoring recipes (`az rest`) | [authoring-recipes.md](references/authoring-recipes.md) | Create job, deploy project, set config, run — copy/paste `az rest` |
| GitHub source (run-only) | [authoring-recipes.md § GitHub source](references/authoring-recipes.md#github-source) | Create GitHubSourceControl connection + bind job to repo/branch |
| Tool Stack | [SKILL.md § Tool Stack](#tool-stack) | |
| Authoring Scope | [SKILL.md § Authoring Scope](#authoring-scope) | |
| Core Workflow | [SKILL.md § Core Workflow](#core-workflow) | Create → generate SQL → deploy → configure → run |
| Preview & Confirm (writes) | [SKILL.md § Preview & Confirm](#preview--confirm) | **Human-in-the-loop before any write/run** |
| Must / Prefer / Avoid | [SKILL.md § Must / Prefer / Avoid](#must--prefer--avoid) | |
| Examples | [SKILL.md § Examples](#examples) | |
| Agent Integration Notes | [SKILL.md § Agent Integration Notes](#agent-integration-notes) | |

---

## Tool Stack

| Tool | Purpose | Install |
|---|---|---|
| **az cli** | Fabric control-plane REST + item definition + run via `az rest` | `winget install Microsoft.AzureCLI` |
| **jq** | JSON processing / decoding base64 definition parts | `winget install jqlang.jq` |
| **base64** | Encode project files into definition parts (coreutils / built-in) | preinstalled on Linux/macOS |

Authenticate once (see [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes)):

```bash
az login
API="https://api.fabric.microsoft.com/v1"
RES="https://api.fabric.microsoft.com"
```

---

## Authoring Scope

| Operation | Endpoint (via `az rest`, `--resource $RES`) |
|---|---|
| Create dbt job | `POST $API/workspaces/{ws}/dataBuildToolJobs` |
| List dbt jobs | `GET  $API/workspaces/{ws}/items?type=DataBuildToolJob` |
| Get definition (all parts) | `POST $API/workspaces/{ws}/items/{id}/getDefinition` |
| Update definition (RMW) | `POST $API/workspaces/{ws}/items/{id}/updateDefinition` |
| Trigger run | `POST $API/workspaces/{ws}/items/{id}/jobs/instances?jobType=Execute` |
| Create GitHub connection | `POST $API/connections` (type `GitHubSourceControl`) |

The dbt **project files** ship inside the definition as parts under `Code/dbt/*`; the **config**
part (`dbt-content.json` / `dbtjob-content.json`) holds project/profile/command settings. See
[DBT-CORE.md](../../common/DBT-CORE.md) for the full model.

---

## Core Workflow

For a new, in-Fabric dbt job:

1. **Confirm intent** — target adapter (Fabric DW / Azure SQL / PostgreSQL / Snowflake), what the
   models should do, and the target connection/schema. If ambiguous, ask (see *Preview & Confirm*).
2. **Generate the project** — `dbt_project.yml`, `models/*.sql`, `schema.yml`, seeds. Write
   Core-1.9 SQL for the chosen adapter using [DBT-CORE.md § Adapter SQL](../../common/DBT-CORE.md#adapter-sql).
   Keep `profiles.yml` secret-free (`env_var()` placeholders only).
3. **Create the job** and **deploy** the project into `Code/dbt/*`
   ([authoring-recipes.md](references/authoring-recipes.md)).
4. **Set the config** — bind the warehouse **by connection GUID**, set schema and run command.
5. **Run** and confirm the instance reaches `Completed` (never treat a 202 as success).

To use an existing **GitHub** repo instead of storing files in Fabric, skip steps 2–3 and follow
[authoring-recipes.md § GitHub source](references/authoring-recipes.md#github-source) — these jobs
are **run-only** (edit models in GitHub).

To **update an existing** job's models, delegate discovery to **dbt-consumption-cli** (decode the
definition + parse `schema.yml`), then redeploy with read-modify-write.

---

## Preview & Confirm

Writes and runs have side effects (they create items, overwrite definitions, and execute SQL against
a warehouse), so treat them like any irreversible operation:

- If the request is ambiguous (no adapter, no target, "set up my dbt job"), **ask first** — offer
  the concrete options rather than inferring.
- Before `updateDefinition` or a run, **show the plan**: which job, which parts change, the resolved
  `dbt-content.json` (connection GUID + schema + command), and the operation. Proceed on explicit
  confirmation.
- Before `updateDefinition`, **always** `getDefinition` first and preserve every existing part —
  a partial part list deletes the project files.

---

## Must / Prefer / Avoid

### Must
- Bind targets **by connection GUID** (`externalReferences.connection` or workspace/artifact GUIDs).
  Never put a credential in any file. For GitHub sourcing, the classic PAT lives only in the
  `GitHubSourceControl` connection.
- Read-modify-write for every `updateDefinition` (preserve `Code/dbt/*` + `.platform`).
- **Discover** the config-part name from `getDefinition` (`dbt[\w-]*content\.json`) — it differs by
  API version (`dbt-content.json` live vs `dbtjob-content.json` in docs).
- Poll LROs / run instances to a terminal state before reporting success.

### Prefer
- `dbt build` as the default command (models + tests + seeds + snapshots).
- `delete+insert` incremental strategy for portability; upgrade to `merge`/`microbatch` only where
  the adapter supports it (see [DBT-CORE.md](../../common/DBT-CORE.md#adapter-sql)).
- Fabric-Warehouse-safe types (`varchar` not `nvarchar`, `datetime2` not `datetime`, `decimal` not
  `money`).

### Avoid
- Hand-building `updateDefinition` with a partial part list (drops files).
- Hardcoding three-part table names in models — use `{{ ref() }}` / `{{ source() }}`.
- Writing `profiles.yml` with real host/user/password — use `env_var()` placeholders.
- Deploying `Code/dbt/*` to a GitHub-connected (run-only) job — edit in the repo instead.

---

## Examples

### Example 1 — New Fabric DW job, deploy + run
See [authoring-recipes.md § End-to-end](references/authoring-recipes.md#end-to-end): create the job,
`base64`-pack `./my_dbt_project` into `Code/dbt/*`, set `profileType=DataWarehouse` bound to the
warehouse GUID + schema `gold`, `operation=build`, then trigger and poll a run.

### Example 2 — Generate an incremental model for Fabric DW
```sql
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='order_id') }}
select
    cast(order_id as bigint)      as order_id,
    cast(amount   as decimal(19,4)) as amount,   -- not money
    cast(status   as varchar(50)) as status      -- not nvarchar
from {{ ref('stg_orders') }}
{% if is_incremental() %}
where order_date > (select max(order_date) from {{ this }})
{% endif %}
```

### Example 3 — Connect a job to a GitHub repo (run-only)
See [authoring-recipes.md § GitHub source](references/authoring-recipes.md#github-source): create a
`GitHubSourceControl` connection from a classic PAT, bind the job's project to that connection +
branch (profile/command unchanged), then run.

---

## Agent Integration Notes

- This skill covers **authoring** — create/configure/update/deploy/run dbt jobs and generate SQL.
- For **read-only** discovery, run-history, and monitoring, delegate to **dbt-consumption-cli**.
- For end-to-end lakehouse patterns, see **e2e-medallion-architecture**; for warehouse T-SQL, see
  **sqldw-authoring-cli**.
- All writes require a Contributor workspace role and read/write on the target warehouse/connection.
