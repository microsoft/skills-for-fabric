---
name: dbt-consumption-cli
description: >
  Discover, inspect, and monitor Fabric dbt jobs (DataBuildToolJob) via `az rest` — read-only and
  run-focused operations. List dbt jobs, decode their configuration and project files from the item
  definition, review model schema (schema.yml), trigger runs, and inspect run history and failures.
  Use when the user wants to:
    1. List the dbt jobs in a workspace
    2. Inspect a dbt job's adapter, schema, connection, and run command
    3. See which project files (models, schema.yml) ship with a job
    4. Trigger a dbt run and monitor it, or review run history / failure reasons
    5. Compare dbt command/profile settings across jobs (governance)
  Triggers: "list dbt jobs", "inspect dbt job", "show dbt config", "dbt run history",
  "why did my dbt job fail", "monitor dbt run", "which models are in my dbt job", "dbt consumption"
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering.
> 2. To find dbt jobs: list items with `type=DataBuildToolJob`, then filter by `displayName`.
> 3. **Decode before inspecting** — definition parts are base64; the config-part name varies by API version (discover it via `dbt[\w-]*content\.json`).

# dbt-consumption-cli — Inspect & Monitor Fabric dbt Jobs via CLI

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Finding Workspaces and Items in Fabric | [COMMON-CLI.md § Finding Workspaces and Items in Fabric](../../common/COMMON-CLI.md#finding-workspaces-and-items-in-fabric) | **Mandatory** — *READ link first* [use `type=DataBuildToolJob`] |
| Authentication & Token Acquisition | [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) | Wrong audience = 401 |
| Core Control-Plane REST APIs | [COMMON-CORE.md § Core Control-Plane REST APIs](../../common/COMMON-CORE.md#core-control-plane-rest-apis) | List Items, getDefinition |
| Long-Running Operations (LRO) | [COMMON-CORE.md § Long-Running Operations (LRO)](../../common/COMMON-CORE.md#long-running-operations-lro) | getDefinition can be a 202 LRO |
| Fabric Control-Plane API via `az rest` | [COMMON-CLI.md § Fabric Control-Plane API via az rest](../../common/COMMON-CLI.md#fabric-control-plane-api-via-az-rest) | **Always pass `--resource https://api.fabric.microsoft.com`** |
| Long-Running Operations (LRO) Pattern | [COMMON-CLI.md § Long-Running Operations (LRO) Pattern](../../common/COMMON-CLI.md#long-running-operations-lro-pattern) | Poll `Location` |
| dbt job execution model & definition | [DBT-CORE.md § Execution model](../../common/DBT-CORE.md#execution-model) | Item type, `Code/dbt/*` parts, config-part name |
| Adapter reference | [DBT-CORE.md § Supportability matrix](../../common/DBT-CORE.md#supportability-matrix) | Interpreting `profileType` |
| Inspect & monitor recipes (`az rest`) | [inspect-recipes.md](references/inspect-recipes.md) | List, decode config, list Code/dbt parts, run history |
| Discovery Scope | [SKILL.md § Discovery Scope](#discovery-scope) | |
| Must / Prefer / Avoid | [SKILL.md § Must / Prefer / Avoid](#must--prefer--avoid) | |
| Troubleshooting | [SKILL.md § Troubleshooting](#troubleshooting) | |
| Agent Integration Notes | [SKILL.md § Agent Integration Notes](#agent-integration-notes) | |

---

## Discovery Scope

| Operation | Endpoint (via `az rest`, `--resource https://api.fabric.microsoft.com`) |
|---|---|
| List dbt jobs | `GET  /v1/workspaces/{ws}/items?type=DataBuildToolJob` |
| Get item | `GET  /v1/workspaces/{ws}/dataBuildToolJobs/{id}` |
| Get definition (decode) | `POST /v1/workspaces/{ws}/items/{id}/getDefinition` |
| Run history | `GET  /v1/workspaces/{ws}/items/{id}/jobs/instances` |
| Trigger run | `POST /v1/workspaces/{ws}/items/{id}/jobs/instances?jobType=Execute` |

All read-only except triggering a run. See [inspect-recipes.md](references/inspect-recipes.md) for
copy/paste commands, and [DBT-CORE.md](../../common/DBT-CORE.md) for the definition model.

---

## Must / Prefer / Avoid

### Must
- Use `type=DataBuildToolJob` when listing (not `dbtJob`).
- **Discover** the config-part name from `getDefinition` (`dbt[\w-]*content\.json`) before decoding.
- Decode base64 parts before inspecting; handle `getDefinition` 202 by polling `Location`.

### Prefer
- Inspect a job's config + `schema.yml` **before** triggering a run or handing off to authoring.
- Filter run history by status/time; read `failureReason` on failures.
- `jq` / JMESPath for compact diagnostics.

### Avoid
- Assuming the config-part name (`dbt-content.json` vs `dbtjob-content.json`).
- Editing anything here — this skill is read-only. For changes, delegate to **dbt-authoring-cli**.
- Polling runs without a backoff.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty job list | Wrong item type filter | Use `type=DataBuildToolJob` |
| 401 on API calls | Wrong/expired token | Re-login; keep `--resource https://api.fabric.microsoft.com` |
| Missing content part | Hardcoded part name | Discover via `getDefinition` regex `dbt.?content\.json` |
| No `Code/dbt/*` parts | GitHub-sourced (run-only) job | Code lives in GitHub; inspect the repo, not the definition |
| 400 on run trigger | Wrong `jobType` | Use `jobType=Execute` |

---

## Agent Integration Notes

- This skill is **read-only + run** — discover, inspect, monitor. It never edits a job.
- For create/configure/update/deploy and SQL generation, delegate to **dbt-authoring-cli**.
- Inspecting `schema.yml` here is the first step of the authoring skill's update workflow.
