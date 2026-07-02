---
name: search-consumption-cli
description: >
  Search the Microsoft Fabric catalog to find an item by name across all workspaces
  when you don't know which workspace it is in, using the Fabric Catalog Search API.
  Use when the user wants to: (1) search the catalog for an item by name across workspaces,
  (2) discover or list items of a specific type across the tenant,
  (3) identify which workspace contains an item,
  (4) return item/workspace IDs for downstream API calls.
  Triggers: "search for an item", "search the catalog", "catalog search",
  "search Fabric for an item", "search for item", "find an item by name across workspaces",
  "which workspace has", "discover items across the tenant".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare it against the remote version via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If the remote version is newer, show the changelog and update instructions.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. The Catalog Search API finds **items**, not workspaces. To find a workspace by name, use `GET /v1/workspaces` (see [COMMON-CLI.md § Resolve Workspace Properties by Name](../../common/COMMON-CLI.md#resolve-workspace-properties-by-name)).
> 2. The search text matches against item **display name**, **description**, and **workspace name**.
> 3. Dataflow (Gen1) and Dataflow (Gen2) are not supported.

# Catalog Search — CLI Skill

## Prerequisite Knowledge

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — Fabric REST API patterns, auth
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — CLI implementation (az, curl, jq)

## Table of Contents

| Task | Reference | Notes |
|---|---|---|
| Search for an Item | [SKILL.md § Search for an Item](#search-for-an-item) | By name, description, or workspace name |
| List All Items of a Type | [SKILL.md § List All Items of a Type](#list-all-items-of-a-type) | Empty search + type filter |
| Pagination | [SKILL.md § Pagination](#pagination) | Continuation token pattern |
| Agentic Workflow | [SKILL.md § Agentic Workflow](#agentic-workflow) | |
| Examples | [SKILL.md § Examples](#examples) | |
| Gotchas and Troubleshooting | [SKILL.md § Gotchas and Troubleshooting](#gotchas-and-troubleshooting) | |

---

## Must/Prefer/Avoid

### MUST DO

- **Authenticate first** — see [COMMON-CORE.md § Authentication & Token Acquisition](../../common/COMMON-CORE.md#authentication--token-acquisition) and [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes). The Catalog Search API requires `Catalog.Read.All` scope.
- **Write the JSON body to a temp file** — avoids shell quoting issues with filter strings.
- **Disambiguate** — if multiple results match, present display name, type, and workspace name and ask the user to confirm.

### PREFER

- **Catalog Search over list-and-filter** — single cross-workspace call, no need to resolve workspace first.
- **Type filters** — narrow results with `"filter": "Type eq 'Lakehouse'"` to reduce noise.
- **Empty search with type filter** — to list all items of a type across workspaces.
- **`jq`** for extracting IDs from the response — cleaner than JMESPath for nested `hierarchy.workspace`.

### AVOID

- **Searching for workspaces** — the Catalog Search API returns items, not workspaces. Use `GET /v1/workspaces` instead (see [COMMON-CLI.md § Resolve Workspace Properties by Name](../../common/COMMON-CLI.md#resolve-workspace-properties-by-name)).
- **Inventing filter syntax** — only `eq`, `ne`, `or`, and parentheses are supported.
- **Assuming all item types are supported** — Dataflow (Gen1) and Dataflow (Gen2) are not returned yet.

---

## Search for an Item

```bash
cat > /tmp/body.json << 'EOF'
{"search": "SalesLakehouse", "filter": "Type eq 'Lakehouse'", "pageSize": 10}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json
```

The search text matches against item display name, description and workspace name. Type filtering is optional. The response includes `id`, `type`, `displayName`, `description`, and `hierarchy.workspace` (with `id` and `displayName`) for each match.

### Extract item and workspace IDs

```bash
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json \
  --query "value[0].{itemId:id, workspaceId:hierarchy.workspace.id, name:displayName}" \
  --output json
```

---

### Filter Examples

| Goal | Filter |
|---|---|
| Only lakehouses | `Type eq 'Lakehouse'` |
| Reports or semantic models | `Type eq 'Report' or Type eq 'SemanticModel'` |
| Exclude notebooks | `Type ne 'Notebook'` |

For the full list of supported item types, see the [Catalog Search API reference](https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search).

---

## List All Items of a Type

Use an empty search string with a type filter (`pageSize` max is 1000):

```bash
cat > /tmp/body.json << 'EOF'
{"search": "", "filter": "Type eq 'Lakehouse'", "pageSize": 100}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json
```

---

## Pagination

If the response includes a non-null `continuationToken`, pass it in the next request:

```bash
cat > /tmp/body.json << 'EOF'
{"search": "", "filter": "Type eq 'Lakehouse'", "pageSize": 100, "continuationToken": "<token>"}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json
```

Continue until `continuationToken` is null.

---

## Agentic Workflow

1. **Ask** — user provides an item name, type, or description keywords.
2. **Search** — call Catalog Search with the user's input and optional type filter.
3. **Disambiguate** — if multiple matches, present results (name, type, workspace) and ask the user to pick.
4. **Return** — provide the search results, include the item `id` and `hierarchy.workspace.id` for downstream use.

---

## Examples

### Find a specific report
```bash
cat > /tmp/body.json << 'EOF'
{"search": "Monthly Sales Revenue", "filter": "Type eq 'Report'", "pageSize": 10}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json \
  --query "value[].{name:displayName, type:type, workspace:hierarchy.workspace.displayName}" \
  --output table
```

### List all semantic models across workspaces
```bash
cat > /tmp/body.json << 'EOF'
{"search": "", "filter": "Type eq 'SemanticModel'", "pageSize": 1000}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json
```

### Save search results to file
```bash
cat > /tmp/body.json << 'EOF'
{"search": "", "filter": "Type eq 'Lakehouse'", "pageSize": 1000}
EOF
az rest --method post \
  --resource "https://api.fabric.microsoft.com" \
  --url "https://api.fabric.microsoft.com/v1/catalog/search" \
  --body @/tmp/body.json \
  --query "value[].{name:displayName, type:type, workspace:hierarchy.workspace.displayName, id:id}" \
  --output json > /tmp/search_results.json
```

---

## Gotchas and Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Wrong token audience or expired session | Verify `--resource "https://api.fabric.microsoft.com"`. Run `az login`. |
| `InvalidPageSize` | `pageSize` outside 1–1000 | Use a value between 1 and 1000. |
| `InvalidFilter` | Bad filter syntax | Only `eq`, `ne`, `or`, and parentheses. Don't mix `eq` with `and`, or `ne` with `or`. Don't mix `eq` and `ne` in the same filter. |
| `TypeNotFound` | Unrecognized item type in filter | Check spelling (case-sensitive). See [API reference](https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search) for valid types. |
| `FilterTooManyValues` | Filter has more than 500 values | Reduce the number of type values in the filter. |
| `InvalidRequest` | Missing request body | Ensure `--body` points to a valid JSON file. |
| Empty results for known item | Item type not supported | Dataflow Gen1/Gen2 are excluded. Use `GET /v1/workspaces/{id}/items` instead. |
| New item not found | Catalog index propagation delay | Indexing lag is variable and not yet near-real-time — usually minutes, but not guaranteed. A just-created item may not appear in search results yet; verify it exists via `GET /v1/workspaces/{id}/items` instead. |
| Too many results | Search text too broad | Add a type filter or use more specific search text. |
