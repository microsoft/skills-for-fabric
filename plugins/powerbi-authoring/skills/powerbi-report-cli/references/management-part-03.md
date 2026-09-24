# powerbi-report-cli management mode -- Power BI Report Items in Fabric - Part 3

Continuation of `management.md`. Open this file directly from the skill reference index.

## Must/Prefer/Avoid

### MUST

- **ALL PBIR content MUST go through the `authoring` mode** — this is the single most important rule. Whether creating a brand-new report or modifying an existing one, every PBIR file (`definition.pbir`, `report.json`, `version.json`, `pages.json`, page configs, visuals, filters, formatting, themes, expressions) must be authored using the `authoring` mode. Follow its guidance for correct PBIR structure, schemas, and field values. Use its CLI tools for validation. Never construct any PBIR JSON from memory or guesswork — not even "simple" files like `definition.pbir` or `version.json`. This mode is strictly for API transport (download, encode, upload) — it does not author PBIR content.
- **Always pass `--resource "https://api.fabric.microsoft.com"`** to `az rest` — omitting it causes silent auth failures.
- **Always pass `?format=PBIR`** on `getDefinition` — without it, older reports return PBIR-Legacy format which is not supported by this skill.
- **Only work with PBIR format** — if a definition comes back with `"format": "PBIR-Legacy"`, stop and tell the user that PBIR-Legacy is not supported.
- **Include ALL definition parts** in `updateDefinition` — modified + unmodified. The API replaces the entire definition; omitting parts deletes them.
- **Base64-encode all part payloads** — every `payload` value must be base64-encoded.
- **Use `powerbi-report-author pack`/`unpack` for every base64 + directory-walk transport step** — `powerbi-report-author >= 0.3.0-beta.0` is a hard requirement for this skill's primary workflows. Management invokes these deterministic transport helpers but still never authors PBIR content. The fallback section is conceptual safety guidance only, not an executable non-CLI workflow.
- **Use `byConnection`** in `definition.pbir` for Fabric API — `byPath` is for local/Git scenarios only.
- **Poll LRO to completion** — `Create`, `getDefinition`, and `updateDefinition` return `202 Accepted`. Poll until terminal state.
- **Always use `--verbose` on LRO operations** — `az rest` does not expose response headers by default. Without `--verbose`, you cannot capture the `x-ms-operation-id` header needed for polling, and there is no other way to retrieve it after the fact.
- **Clean up temporary files** — delete any local temp directories and files (decoded definitions, JSON payloads) created during the workflow once the operation completes. These can be large and accumulate on the user's machine.
- **Verify semantic-model bindings after the target model is resolved** — once the report's target semantic model is known (whether by a fresh deploy through an available semantic-model authoring skill or by selecting an existing workspace model), download its TMDL and compare all PBIR bindings (`Entity`, `queryRef`, `nativeQueryRef`, filter `Source`/`Entity` references) against the model's table/column/measure names. This applies to **both** branches: even a hand-off deploy may rename or transform the model during publish, so the diff is not optional. If names differ but models are structurally equivalent (same columns/measures), remap all table-qualified bindings via the `authoring` mode. If the models are not structurally equivalent, prompt the user before attempting to re-author — explain which tables/columns/measures don't match and ask whether to proceed.
- **Local edits stay local by default** — when a user requests changes to a
  local `.pbip` report, apply the changes to the local files only. Never publish
  or overwrite the remote report with local changes until the user explicitly
  gives permission to do it. Do not publish to Fabric unless the current request
  explicitly asks to publish, upload, push, or deploy those local changes. Never
  infer publish permission from approval of the report design, edits, validation,
  screenshots, preview, or an earlier publish. If intent is absent, ambiguous, or
  you are unsure, keep the changes local and do not publish — do not pack, make a
  remote write, or ask to publish. For example, if the user only asks to modify a
  report against the service host, make the local changes, validate, and show the
  preview; do not publish until the user later asks you to. Even with a publish
  request, never call `updateDefinition` until the user confirms they agree to
  overwrite the existing remote report. **When the user does
  request publishing a local `.pbip`**, follow the
  **Publishing a local .pbip** workflow in `management-part-04.md`
  workflow: (a) confirm the target workspace once up front, (b) prompt
  publish-the-local-model vs. connect-to-an-existing-workspace-model, (c) on
  the publish-model branch, check whether a semantic-model authoring skill is
  available in the current session and degrade gracefully if not, (d) confirm
  create-new vs. update-existing for the report itself.

### PREFER

- **Soft delete** over hard delete — allows recovery.
- **`az rest` with JMESPath `--query`** for filtering — built-in JSON parsing, no extra tools needed.
- **File-based pack/unpack handoff** for any shell with uncertain pipe encoding — save the synchronous 200 response body or terminal LRO result body with `az rest --output-file payload.json` before `unpack --input payload.json`, and `pack --raw --out body.json` then `az rest --body @body.json`.

### AVOID

- **Hand-writing or directly constructing PBIR JSON** — whether creating new files or modifying existing ones, all PBIR content (`definition.pbir`, `report.json`, `version.json`, pages, visuals, filters, formatting, themes, expressions) must go through the `authoring` mode. Never construct any PBIR JSON from memory or guesswork — not even "simple" structural files. No exceptions.
- **PBIR-Legacy format** — do not create, read, or update PBIR-Legacy definitions. Only modern PBIR format is supported.
- **Sending only modified parts** in `updateDefinition` — the API replaces the full definition; missing parts are deleted.
- **Using `byPath`** in `definition.pbir` for API payloads — only works for local/Git scenarios.
- **Hardcoded workspace/report IDs** — resolve dynamically via the List APIs.
- **Skipping LRO polling** — definition operations may be async; always check for 202 responses.
- **Omitting `?format=PBIR`** on `getDefinition` — may return unusable PBIR-Legacy format.
- **Retrying a create POST after receiving 202** — risks creating duplicates. See **Long-Running Operations (LRO)** in `management-part-02.md` for the correct recovery pattern.
- **Using jq/base64/find/PowerShell hand-walking instead of installing or upgrading `powerbi-report-author`** — the fallback section documents conceptual safety requirements only; it is not a supported executable workflow in this skill.
