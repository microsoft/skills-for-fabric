# Notebook API Operations — Skill Resource

Principles and decision guidance for reading and updating Fabric notebook content via REST API.
Use this guide when the task requires modifying an **existing** notebook in a Fabric workspace
(e.g., adding new columns, updating SQL logic, changing cell code).

> This guide covers **service-mode** operations that require a workspace ID and a Fabric token.

---

## Quick Decision: Which Endpoint to Use?

| Goal | Endpoint | Notes |
|---|---|---|
| Read notebook content | `POST .../getDefinition` | Returns 202 LRO — must poll |
| Write/update notebook content | `POST .../updateDefinition` | Returns 202 LRO — must poll |
| Update display name / description only | `PATCH .../items/{id}` | Synchronous, no LRO |

---

## `.ipynb` Validation + Fabric Nuances

Use the official Jupyter schema for generic notebook structure validation, and keep this document focused on Fabric-specific behavior.

- Official schema (nbformat v4): https://github.com/jupyter/nbformat/blob/main/nbformat/v4/nbformat.v4.schema.json
- Validate against the schema before Base64 encoding and `updateDefinition` upload
- Prefer preserving the decoded notebook's existing structure and metadata shape, then apply minimal edits

### Fabric-Specific Nuances (keep these in this doc)

| Area | Fabric nuance | Why it matters |
|---|---|---|
| Code cell execution fields | Keep `outputs` and `execution_count` explicitly present on code cells (`[]` / `null` when not executed) | Missing fields commonly cause Fabric rejection or execution/runtime issues |
| Cell metadata | Keep `metadata` object on every cell (use `{}` when empty) | Missing metadata frequently breaks update/round-trip consistency |
| Source line endings | Ensure each source line ends with `\n` except the final line | Missing trailing newlines can make code appear merged in Fabric editor |
| Kernel/language metadata | Keep notebook kernel/language metadata consistent with notebook language/runtime | Inconsistent kernel metadata can lead to editor/runtime mismatch |
| Lakehouse dependency metadata | Preserve/maintain `metadata.dependencies.lakehouse` when notebook uses `spark.sql()` or relative lakehouse paths | Notebook execution needs data context; missing binding causes runtime failures |

### Principles
- **Schema-first for notebook JSON correctness** — rely on Jupyter schema for generic `.ipynb` compliance
- **Fabric-only rules here** — document only behaviors specific to Fabric API/runtime/editor
- **Round-trip safely** — when modifying existing notebooks, preserve non-target metadata and update only required cells/fields

---

## Workflow: Get → Decode → Modify → Encode → Upload

The notebook modification lifecycle always follows this six-step flow.
Generate implementation code on-demand using these principles — do not copy-paste templates.

### Step 1 — Retrieve (`getDefinition`)

**Endpoint:**
```text
POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/getDefinition?format=ipynb
```

**Principles:**
- Always append `?format=ipynb` — without it, the API may return `.py` source format instead of standard Jupyter JSON
- Always send `--body '{}'` — the API returns HTTP 411 (Length Required) if no request body is sent for POST endpoints
- This is an LRO (Long-Running Operation) — POST returns 202, poll the `Location` header URL until `status == "Succeeded"`
- After polling succeeds, append `/result` to the Location URL to retrieve the actual content — this is unique to `getDefinition` (other LROs return data in the poll response directly)

### Step 2 — Decode the Base64 Payload

**Principles:**
- The LRO result contains a `definition.parts[]` array; find the part whose `path` ends with `.ipynb`
- The `payload` field is Base64-encoded (standard encoding, not URL-safe) — decode it to get raw `.ipynb` JSON
- After decoding, **examine the actual JSON structure** to understand cell layout, metadata, and lakehouse dependencies before making changes — the decoded content is standard Jupyter `.ipynb` format (`nbformat`, `metadata`, `cells` array)
- When constructing or modifying cells, follow [`.ipynb` Validation + Fabric Nuances](#ipynb-validation--fabric-nuances) — especially the required fields for code cells (`outputs`, `execution_count`)

### Step 3 — Modify Notebook Cells

**Principles:**
- Cells live in the `cells` array — search by joining `cell['source']` and matching target text
- **Critical formatting rule:** every line in `cell['source']` must end with `\n` **except** the last line of a cell — missing newlines cause lines to visually merge in Fabric's notebook editor
- For insertions, iterate the source lines and append new lines after the match point
- For replacements, use list comprehension to swap matching lines
- Preserve existing cell metadata (`id`, `cell_type`, `metadata`, `outputs`, `execution_count`) — only modify `source`

### Step 4 — Re-encode and Upload (`updateDefinition`)

**Endpoint:**
```text
POST /v1/workspaces/{workspaceId}/notebooks/{notebookId}/updateDefinition
```

**Principles:**
- Serialize the modified notebook to JSON, then Base64-encode it (standard encoding)
- Build the request payload with `definition.format: "ipynb"` and a single part: `path: "notebook-content.ipynb"`, `payloadType: "InlineBase64"`
- **Do NOT include `updateMetadata: true`** unless also supplying a `.platform` file part — sending the flag without a `.platform` part causes HTTP 400
- This is an LRO — poll the `Location` header URL until `status == "Succeeded"`
- Unlike `getDefinition`, `updateDefinition` does **NOT** need a `/result` suffix — the poll response itself confirms success

### Step 5 — Verify the Update (Optional)

**Principles:**
- `updateDefinition` returning `Succeeded` (HTTP 202 → poll → Succeeded) **is sufficient confirmation** — the API accepted and persisted the payload. No further verification needed.
- **Do NOT call `getDefinition` after every update** — it is an async LRO (202 → poll → `/result`) and adds significant latency with no benefit when `updateDefinition` already succeeded.
- Only call `getDefinition` post-upload if you have a specific reason to suspect a silent failure (e.g., the LRO returned Succeeded but subsequent notebook execution fails with unexpected behaviour suggesting wrong content).

---

## Default Lakehouse Binding

A notebook must have a default lakehouse bound to it for `spark.sql()` and relative paths (e.g., `Tables/`, `Files/`) to resolve correctly at runtime. **Without a binding, the notebook has no data context.**

### When to Bind

- **Always** when creating a new notebook that reads from or writes to a lakehouse
- **When modifying** an existing notebook whose lakehouse binding is missing or needs to change
- **After verifying** the lakehouse ID exists in the target workspace — use the item listing API to discover the lakehouse ID dynamically (never hardcode)

### Binding in `.ipynb` Format

In `.ipynb` format (used when `?format=ipynb` is specified on `getDefinition`), the lakehouse binding lives in the notebook's top-level `metadata.dependencies` object:

- Set `metadata.dependencies.lakehouse.default_lakehouse` to the lakehouse GUID
- Set `metadata.dependencies.lakehouse.default_lakehouse_workspace_id` to the workspace GUID
- Set `metadata.dependencies.lakehouse.default_lakehouse_name` to the lakehouse display name
- Only **one** default lakehouse per notebook — additional lakehouses are accessible via SparkSQL three-part names at runtime
- After decoding the `.ipynb` payload, **inspect the existing `metadata` structure** to see if a binding already exists before modifying — preserve any other metadata keys

### Binding in `.py` Format (Fabric Native)

When `getDefinition` is called **without** `?format=ipynb`, the API returns Fabric's native `.py` format. In this format, metadata is embedded as a `# METADATA` comment block near the top of the file:

- The block is delimited by `# METADATA ********************` lines
- Each metadata line is prefixed with `# META`
- The content inside is JSON with the same `dependencies.lakehouse` structure as `.ipynb`
- When modifying `.py` format notebooks, **look for the existing `# METADATA` block** and update the lakehouse fields within it
- If no `# METADATA` block exists, add one after the initial comment header (e.g., after `# Fabric notebook source`)

### Principles

- **Discover lakehouse IDs dynamically** — list items in the workspace filtered by type `Lakehouse`, then match by display name
- **Trust `updateDefinition` success** — a `Succeeded` poll result confirms the lakehouse binding persisted. Do not call `getDefinition` to re-verify after upload.
- **Prefer `.ipynb` format** for programmatic modifications — the JSON structure is easier to parse and less error-prone than editing comment-embedded metadata in `.py` format
- If switching a notebook's default lakehouse, ensure the new lakehouse contains the tables/files the notebook references — otherwise the notebook will fail at runtime

---

## Public URL Data Ingestion (Spark)

When a user provides a real public dataset URL (HTTP/HTTPS), prefer ingesting the real data over generating synthetic rows.

### Principles

- **Do not generate synthetic inline data when a real public source is provided** for ingestion tasks
- **Stage external files into lakehouse `Files/` first**, then read from lakehouse paths in Spark
- **Do not rely on direct arbitrary URL reads in Spark as the default path**; network/runtime restrictions can be environment-dependent

### Recommended Flow

1. Download/copy the source file from public URL using Python (`urllib`/`requests`), OneLake API, or pipeline Copy activity
2. Write it to lakehouse `Files/` (for example `Files/nyc/`)
3. Read with Spark from lakehouse path (for example `spark.read.parquet("Files/nyc/yellow_tripdata_2024-01.parquet")`)
4. Persist to Delta table in Bronze and continue the medallion flow

---

## Error Reference

| HTTP | Error | Root Cause | Fix |
|---|---|---|---|
| 411 | Length Required | POST with no request body | Add `--body '{}'` to all `getDefinition` and `updateDefinition` calls |
| 400 | Bad Request: updateMetadata | `updateMetadata: true` sent without a `.platform` file part | Remove `updateMetadata` flag or set to `false` for content-only updates |
| 400 | Bad Request: invalid base64 | Malformed base64 or wrong encoding | Verify with `base64 --decode` before uploading; use standard Base64 (not URL-safe) |
| 400 | Invalid notebook format | `.ipynb` JSON is malformed | Validate JSON structure; ensure `nbformat`, `cells`, and `metadata` keys are present |
| 401 | Unauthorized | Expired or wrong token audience | Re-run `az login`; ensure `--resource https://api.fabric.microsoft.com` is set |
| 403 | Forbidden | Insufficient workspace permissions | Verify caller has Contributor or Admin role on the workspace |

---

## Gotchas

| # | Issue | Details |
|---|---|---|
| 1 | `getDefinition` LRO result needs `/result` suffix | Unlike most LROs (which return final data in the poll response), `getDefinition` requires an additional `GET {Location}/result` call after the poll shows `Succeeded` |
| 2 | `updateDefinition` LRO does NOT need `/result` | Polling `{Location}` is sufficient; no `/result` step |
| 3 | Empty body causes 411 | All `getDefinition` and `updateDefinition` POSTs require at minimum `--body '{}'` |
| 4 | `updateMetadata: true` requires `.platform` part | If you include this flag, you must also supply a `.platform` file in the `parts` array; for content-only updates, omit the flag entirely |
| 5 | Source lines must end with `\n` | Every line in `cell['source']` except the last must end with `\n`; missing newlines cause lines to visually merge in Fabric's notebook editor |
| 6 | `format=ipynb` query parameter matters | Without it, `getDefinition` may return `.py` source format; always append `?format=ipynb` |
