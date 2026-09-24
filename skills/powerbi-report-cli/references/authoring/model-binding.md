# `definition.pbir` — Report → Semantic Model Binding

## Contents

- [Pick the right form first](#pick-the-right-form-first)
- [Form 1 — `byPath` (local co-located model)](#form-1--bypath-local-co-located-model)
- [Form 2 — `byConnection` live to a remote Fabric model (report host)](#form-2--byconnection-live-to-a-remote-fabric-model-report-host)
- [Form 3 — `byConnection` for Fabric REST API publish](#form-3--byconnection-for-fabric-rest-api-publish)
- [Error → fix quick reference (Desktop connection dialogs)](#error--fix-quick-reference-desktop-connection-dialogs)
- [See also](#see-also)


> Referenced from SKILL.md. Read this when **creating, repointing, or repairing**
> the `definition.pbir` binding — greenfield scaffolds, rebinds to a different
> model, or fixing a Desktop "can't connect" dialog. `definition.pbir` is a
> **report** artifact and is owned by this skill, not by the semantic-model
> tooling. The model side only supplies the identifiers (workspace name, model
> name, model GUID); this skill assembles them into the correct binding.

## Pick the right form first

There are three valid bindings and they are **not interchangeable**. Using the
wrong one is the most common cause of a Desktop connection error dialog. Choose
by *where the model lives* and *what you are doing*:

| Situation | Form | `connectionString` / `path` |
|-----------|------|------------------------------|
| Local PBIP with the model **co-located on disk** (`../X.SemanticModel`) | `byPath` | `"path": "../<Project>.SemanticModel"` |
| Local PBIP bound **live to a remote Fabric model**, opened/verified in a **report host** | `byConnection` (full) | `Data Source=…;Initial Catalog=…;Integrated Security=ClaimsToken;semanticModelId=…` |
| **Publishing** to a Fabric workspace via the **REST API** | `byConnection` (API) | `semanticmodelid=<id>` — see the `management` mode |

Constant fields in every form:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": { /* one of byPath / byConnection below */ }
}
```

> **`$schema`:** the version above is illustrative. Use whatever `$schema` is
> already in the file you're working on — the scaffolded value for a new report,
> or the existing value for an existing one. Don't invent, bump, or downgrade it;
> binding changes never require touching `$schema`.

---

## Form 1 — `byPath` (local co-located model)

For a local PBIP project that ships the report and model together on disk:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../<Project>.SemanticModel"
    }
  }
}
```

- Path is relative from the `.Report/` directory.
- Do **not** include `"byConnection": null` alongside `byPath` — it can cause
  parse errors. Include only the one form you are using.

---

## Form 2 — `byConnection` live to a remote Fabric model (report host)

Use this when the model lives in a Fabric/Power BI workspace and you want a
**local PBIP** to open against it live.

> **When to choose Form 2.** This binds a local PBIP live to a remote model so you
> can author it in the report host. Writing the binding itself only needs the
>  three identifiers (below); but authoring the report's visuals also needs to read
> the remote model's tables, columns, and measures — so choose this form only when
> you can inspect the live model's schema through Power BI Modeling MCP.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byConnection": {
      "connectionString": "Data Source=powerbi://api.powerbi.com/v1.0/myorg/<WorkspaceName>;Initial Catalog=<ModelName>;Integrated Security=ClaimsToken;semanticModelId=<ModelGuid>"
    }
  }
}
```

| Part | Example | Supplies | Omitting it causes |
|------|---------|----------|--------------------|
| `Data Source=powerbi://api.powerbi.com/v1.0/myorg/<WorkspaceName>` | XMLA endpoint for the workspace | the **serverName** | `Non-empty assertion failure: serverName` |
| `Initial Catalog=<ModelName>` | the model/database name | the catalog | binding cannot resolve the database |
| `Integrated Security=ClaimsToken` | token auth mode | auth | auth failure |
| `semanticModelId=<ModelGuid>` | the Fabric model GUID | model identity | `missing required 'semanticModelId' parameter` |

**The three model-supplied values.** The binding needs the workspace name, model
name, and model GUID (slotted as `Data Source`, `Initial Catalog`, and
`semanticModelId` above; the fourth part is the constant below). Use them if
they're already available in context — passed in when this skill was invoked, or
read from a live connection to the model (which reports `serverName` /
`databaseName` / `semanticModelId`). Otherwise, prompt the user for the workspace
name, model name, and model GUID.

The fourth part, `Integrated Security=ClaimsToken`, is a **constant literal** you
always add — the modern AAD/Entra **interactive** auth clause for the `powerbi://`
XMLA endpoint the report host uses (it connects with the signed-in user's
identity); a model connection does not report it. So the string is **three model-supplied
values + one constant**.

---

## Form 3 — `byConnection` for Fabric REST API publish

When publishing through the Fabric API, the binding uses the **minimal** form:

```json
{
  "datasetReference": {
    "byConnection": {
      "connectionString": "semanticmodelid=<SemanticModelId>"
    }
  }
}
```

This form is **API-only**. It will **not** open in a local report host (it has no
server → `serverName` assertion failure). For the publish/rebind workflow, LRO
polling, and theme upload rules, defer to the `management` mode.

---

## Error → fix quick reference (Desktop connection dialogs)

These can appear during Desktop-hosted preview when the binding is wrong. The
Desktop host reloads the PBIR layout into the matching running Desktop instance
without reloading the semantic model. Use the preview capability and error
results for that selected host as the source of truth. The dialogs surface
**in sequence** — each fix can reveal the next missing piece, because schema
validation runs first and the runtime connection parser runs after.

| Dialog message | Cause | Fix |
|----------------|-------|-----|
| Schema error naming an extra property (e.g. `pbiServiceModelId`) | `byConnection` had siblings other than `connectionString` | Remove all siblings; keep only `connectionString` |
| `missing required 'semanticModelId' parameter` | Connection string has `Data Source`/XMLA but no Fabric model id | Add `;semanticModelId=<ModelGuid>` (use **Form 2**) |
| `Non-empty assertion failure: serverName` | Connection string has `semanticModelId` (or `semanticmodelid=<id>`) but no server | Add the `Data Source=powerbi://…/myorg/<Workspace>;Initial Catalog=<Model>` prefix (use **Form 2**) — do not use the API-only Form 3 for a local report host |

The last two are mirror images: "I have a server, no model id" vs. "I have a
model id, no server." The fix for a local live report-host binding is always the
**full Form 2 string** — provide both halves, do not choose between them.

---

## See also

- SKILL.md § PBIR File Layout (see `../authoring.md`, section `pbir-file-layout`) — file layout and
  `$schema` versioning rules.
- `preview.md` (see `preview.md`) — Desktop/service status, rendering, and
  screenshot guidance.
- the `management` mode — Fabric REST publish, the API-only `byConnection`
  form, `byPath → byConnection` rebind on publish, and LRO polling.
