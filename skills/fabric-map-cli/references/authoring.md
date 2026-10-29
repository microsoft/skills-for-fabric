# Fabric Map authoring

This reference owns workspace/Map resolution, the definition envelope, common
styling, and the public REST lifecycle. Source adapters own source discovery,
data validation, and any additional definition parts.

## Requirements

Creation requires a workspace and new Map display name; edits/deletion require
a workspace and existing Map identity. Clarify an unspecified change's intended
value. Reuse the request, prior user context, and verified existing configuration
before asking for missing values using the host's question tool.
Ask only for inputs needed by that operation. Do not require data when the
request explicitly asks for a blank/empty Map or generic item creation with
no data-backed goal. Do not require a source adapter for metadata or basemap
edits. If a data-backed goal is stated but its source is not identified in the
request or prior user context, ask which source to use and wait before
creation; do not default to an empty Map.

For source/layer changes, read the relevant adapter and validate only the
affected sources before assembling the complete definition. Do not provision
prerequisite data or connections as a hidden side effect.

For Ontology entities, read [Ontology](authoring/ontology.md). For variable-backed
sources, read [variable references](authoring/variables.md) and the underlying
source adapter. Apply their compatibility checks to the operation's selected
schema; do not migrate an existing Map just to enable a new source.

### Focused clarification

Source adapters describe what the agent must verify, not a questionnaire for
the user. Resolve details from supplied context, the existing Map definition
on edits, and documented read-only metadata within the identified source scope.
Do not search unrelated workspaces or local files for an implicit target.

- Ask only for a required value that remains unknown or a choice that metadata
  cannot resolve. Present verified names as choices when several candidates fit;
  do not choose the first result or require the user to supply internal IDs.
- Keep questions focused on the next blocking decision. Combine closely related
  missing values, but do not ask for the entire adapter checklist up front or
  request confirmation of every unambiguous resolved value.
- Do not make optional styling or refresh preferences prerequisites. On creation,
  omit optional settings when permitted and use documented, geometry-compatible
  defaults where a rendering choice is required. If a required choice has no
  verified default and remains unspecified, ask rather than guess. On edits,
  preserve existing settings unless the request requires a change.
- Discovery does not replace validation. Report access failures, incompatible
  sources, and missing bindings as blockers; user answers cannot substitute for
  required compatibility or permission checks.

## Resolve workspace and Map

Use Azure CLI authentication with audience `https://api.fabric.microsoft.com`.
All examples use `$base = "https://api.fabric.microsoft.com/v1"` and the
`x-ms-fabric-skill: fabric-map-cli` header.

| Lookup | Endpoint |
|---|---|
| Workspace by name | `GET /v1/workspaces` |
| Verify workspace ID | `GET /v1/workspaces/{workspaceId}` |
| Map by name | `GET /v1/workspaces/{workspaceId}/maps` |
| Verify Map ID / read metadata | `GET /v1/workspaces/{workspaceId}/maps/{mapId}` |

Prefer URL-encoding `continuationToken` on the same list endpoint while
preserving filters. Otherwise resolve `continuationUri` against the request
URL; for a service-provided regional URI, keep its documented `/v1/` path and
query on the public Fabric origin rather than forwarding credentials to an
arbitrary host. Exact-match display names after
collecting all pages. Zero matches means not found; multiple matches require
selection. Never guess IDs, choose the first match, or overwrite an existing
Map when asked to create a new one. Optional Map folder filters are
`rootFolderId` and `recursive`.
Continuation properties may be absent, not just null; guard property access
when using PowerShell strict mode.

```powershell
az rest --method get --resource "https://api.fabric.microsoft.com" `
  --url "$base/workspaces" `
  --headers "x-ms-fabric-skill=fabric-map-cli"
```

## Schema resolution and blank definitions

For each new-Map workflow, resolve the latest published schema at runtime from
the authoritative
[Map schema directory on main](https://github.com/microsoft/json-schemas/tree/main/fabric/item/map/definition).
Read any applicable repository/directory instructions and the selected schema;
do not copy a version from this skill, an older example, or a remembered URL.

1. List the version directories at that link. For programmatic discovery, use
   `GET https://api.github.com/repos/microsoft/json-schemas/contents/fabric/item/map/definition?ref=main`.
   Consider stable numeric `major.minor.patch` directories, comparing the
   numeric components rather than sorting their names lexicographically.
   Ignore non-version entries and preview versions unless explicitly requested.
2. Select the highest stable version and inspect its `schema.json`. If the user
   explicitly requests a version, verify that directory and use it instead;
   never invent a version or probe incremented version URLs.
3. Resolve the published URL from the selected directory:
   `https://developer.microsoft.com/json-schemas/fabric/item/map/definition/<discovered-version>/schema.json`.
   Fetch that exact schema and store its URL as `$resolvedSchemaUrl`. A GitHub
   `main` entry can precede live publication; confirm that the published URL
   returns the expected JSON Schema, not an error or HTML page. Do not use the
   GitHub page/raw URL as the Map's `$schema`.
4. Read the downloaded schema's required fields, definitions, and referenced
   schemas before assembling the Map. Use its declared JSON Schema dialect,
   enable format checking, and validate the complete definition locally,
   including documented bounds not enforced by the schema.

If discovery, publication checks, schema retrieval, or validation fails, stop
before mutation and report the failure. Do not silently use a cached default,
fall back to an older version, or retry a rejected write with another schema.
Resolve once for the workflow and use the same schema for assembly, validation,
submission, and readback.

For each version-dependent object, inspect the selected schema's alternatives
and choose the compatible branch with no deprecation notice. For a new Map,
prefer the current `datasourceId` plus item/connection-reference model when the
selected schema defines it; use a legacy `itemType`/`workspaceId`/`itemId` or
`connectionId` branch only when that schema does not provide the newer model.
Build layer and icon source links from the same selected branch. Do not infer a
new field name by analogy or copy a fragment whose branch was not verified.
Do not combine fields from incompatible reference branches.
On edits, preserve the existing representation unless the requested change
requires another compatible branch or the user explicitly requests migration.

Select the validator from the downloaded schema's own `$schema`, not the Map
definition version. Verify that it implements the declared dialect and enables
format checking; an automatic fallback to another dialect is not sufficient.
Report an unsupported dialect rather than changing either `$schema` URL or
silently validating against another contract.

On definition edits, fetch and validate against the existing Map's declared
`$schema`; do not apply the latest-schema selection to unrelated changes.
A schema migration requires an explicit request, review of the target schema,
and validation of the complete migrated definition while preserving unrelated
content. Metadata-only updates, deletion, and listing need no schema discovery.

Use the empty-Map workflow only for explicit blank/empty creation (including
an explicit request to add data later) or generic Map-item creation with no
data-backed goal. For example, "create a Map" needs no source selection, but
"create a Map showing our latest vehicle locations" requires clarification
when its source is not yet identified. Missing source details are not evidence
of blank-Map intent.

For the empty-Map workflow, after resolving `$resolvedSchemaUrl` above,
assemble the blank definition from the fetched contract. This starting shape
must still be checked against that schema, including any newly required
properties:

```powershell
$map = [ordered]@{
    '$schema' = $resolvedSchemaUrl
    basemap = @{}
    dataSources = @()
    iconSources = @()
    layerSources = @()
    layerSettings = @()
}
$mapJson = $map | ConvertTo-Json -Depth 100
```

Here "empty" means no data or layers; it does not require the `blank` basemap
style. `dataSources` identifies inputs, `iconSources` defines reusable symbols,
`layerSources` describes data retrieval, and `layerSettings` describes rendering.
Each layer's `sourceId` must resolve to a unique layer source. Preserve IDs on
updates and generate identifiers only for new entries. Validate IDs and links
against the selected schema; require UUIDs only for UUID-formatted fields.

### Required blank-Map completion response

After successful creation and readback, read the capability summaries in
[Lakehouse](authoring/lakehouse.md), [Eventhouse](authoring/eventhouse.md),
[connections](authoring/connections.md), [Ontology](authoring/ontology.md), and
[variable references](authoring/variables.md). Do not run their source-discovery or
setup procedures. Even when the request only says "create a Map", the final
response must include all three parts below:

1. **Created:** actual workspace, Map name/ID, persisted schema, and confirmation
   that no data sources or layers exist. Qualify visual rendering separately.
2. **Add later:** say data and layers can be added later, then give a compact
   source table using the coverage below and the adapters' limits.
3. **Needed for a follow-up:** identify the source and what to show, such as a
   file, KQL entity/query, imagery layer, or Ontology entity in the user's terms.
   For variables, a reference or library plus variable name identifies the
   source. Explain that metadata will be discovered and only unresolved choices
   will need clarification; styling and refresh preferences are optional.
   State this as future guidance, not a questionnaire or creation prerequisite.

| Source row | Required coverage |
|---|---|
| Lakehouse | GeoJSON, vector/raster PMTiles, and COG; compatible points, lines, polygons, heatmaps, and extrusions versus raster imagery; key file/format limits |
| Eventhouse / KQL Database | Coordinates or GeoJSON geometry, compatible vector renderings, and result/function limits; distinguish direct table preview limits from general query results |
| External connections | Name Geospatial Web Services for WMS/WMTS and Microsoft Planetary Computer for MPC Pro; imagery-only rendering and projection/image-format limits, not arbitrary Fabric connectors |
| Ontology (preview) | Entity-backed spatial layers; numeric coordinates or geometry properties; up to 100,000 returned features |
| Variable references | Parameterize supported item/connection sources, not geometry; selected-schema and variable-type compatibility, active value set, and underlying source permissions still apply |

Do not stop after metadata or replace the source table and follow-up inputs
with "data can be added later", documentation links, or an offer to explain.
Keep the table concise; omit setup steps, API payloads, and authentication
procedures. Before sending, check that all three parts are present. A failed
or partial creation still follows the failure-reporting rules, not this
success response.

## Definition envelope

`map.json` is required. Preserve all other parts, including optional `.platform`
metadata and adapter-owned parts. Every submitted part uses UTF-8 bytes encoded
as Base64 with `payloadType: "InlineBase64"`:

```json
{
  "definition": {
    "parts": [
      {
        "path": "map.json",
        "payload": "<base64-encoded UTF-8 JSON>",
        "payloadType": "InlineBase64"
      }
    ]
  }
}
```

Serialize without truncation (`ConvertTo-Json -Depth 100` on PowerShell), write
request bodies as UTF-8 without BOM, and pass `--body "@<body-file>"` to `az rest`.
Do not send raw JSON as a part payload. Retain untouched part payloads exactly.

## Common styling

For edits, get and decode the existing definition first. Patch only requested
properties; create missing containers without replacing existing siblings.
Do not migrate `$schema`, reset arrays, or apply new defaults during an unrelated
edit.

| Request | JSON location | Values / constraints |
|---|---|---|
| Basemap style | `basemap.options.style` | Use documented style IDs, not UI labels |
| Center | `basemap.options.center` | `[longitude, latitude]`; longitude -180..180, latitude -90..90 |
| Zoom | `basemap.options.zoom` | 1..22 |
| Pitch | `basemap.options.pitch` | 0..60 degrees |
| Bearing / compass | `basemap.options.bearing` | Degrees clockwise from north; UI range -180..180; normalize equivalent rotations if necessary |
| Theme | `basemap.theme` | `default`, `classic`, `innovate`, `storm`, `temperature`, `colorBlindSafe` |
| Label language | `basemap.options.language` | Supported render language code, e.g. `en-US`, `fr-FR`, or `auto`; check the applicable localization table |
| Geopolitical view | `basemap.options.view` | Supported region code, e.g. `IN` for India's view, independent of camera position |
| Label visibility | `basemap.options.showLabels` | Boolean; preserve when only changing language |

Documented basemap style IDs include `road`, `satellite`,
`satellite_road_labels` (Hybrid), `grayscale_light`, `grayscale_dark`, `night`,
`high_contrast_light`, `high_contrast_dark`, `blank`, and `blank_accessible`.
Check current customization/localization documentation when resolving a new
label or value. Theme is not a basemap style; "dark" is not a theme enum.

For a named place, resolve an unambiguous geographic center using an
authoritative geographic source, or ask for coordinates if ambiguous. Explain
approximate centers of large regions. Center and geopolitical view are separate:
changing the view must not recenter to that country. Preserve zoom, pitch,
bearing, language, and style unless requested. Do not call Azure Maps service
APIs solely to manage a Fabric Map.

For layer styling, use `options.type: "vector"` or `"raster"`. Point layers use
one `pointLayerType`: `bubble`, `marker`, or `heatmap`, with its corresponding
options. Lines use `lineOptions`; polygons use `polygonOptions`; extrusions use
`allowExtrusions` and `polygonExtrusionOptions` on compatible polygon data.
Imagery is raster, not vector geometry. Adapter capabilities determine which
renderings the source supports.

Keep opacity in 0..1 and fixed bubble size in 1..50. Filters need stable UUIDs,
an existing field, explicit `locked`, and a supported type (`text`, `boolean`,
`number`, `datetime`). Use spatial mappings at the locations accepted by the
Map's schema; preserve existing mappings on unrelated changes.

### Shared data-layer settings

GeoJSON and vector PMTiles use the same geometry-family styling.
Source adapters supply the source discriminator, path and any internal
tile-layer binding. Do not duplicate styling per format. Build settings from
verified fields and geometry, then validate the complete definition against
the selected schema before writing.

| Intent | Saved setting |
|---|---|
| Show/hide | `layerSettings[].options.visible`; retain the source, settings, and ID |
| Vector labels (points, lines, polygons) | `options.dataLabelOptions.enabled: true` and `options.dataLabelKeys: ["<real-field>"]` |
| Tooltips | `options.enablePopups: true` and `options.tooltipKeys: ["<real-field>", ...]` |
| Color by category | Geometry options' `enableSeriesGroup: true`, `seriesGroup: "<real-field>"`, `customColors`, and a matching color expression in `color`, `strokeColor`, or `fillColor` |
| Point size by data | `bubbleOptions.sizeType: "data-driven"` and `sizeProperty: "<numeric-field>"` |
| Line width | `lineOptions.strokeWidth` in pixels, nonnegative |
| Polygon fill | `polygonOptions.fillColor` and `polygonOptions.fillOpacity` |
| Imagery opacity | `options.opacity` (75% = `0.75`), not vector fill opacity |

Category metadata alone can populate the legend while the actual features
remain a single color after reopening. Persist a schema-valid color
expression alongside the grouping metadata, and verify the rendered expression.
Do not assume opening the style editor will repair a saved definition.

Use geometry-compatible settings from the current
[layer settings documentation](https://learn.microsoft.com/fabric/real-time-intelligence/map/customize-map)
and the selected schema. Report unsupported styling requests rather than
inventing settings or changing source geometry to make them appear supported.
For polygon overlays, use the existing polygon geometry, supported fill
settings, and requested layer order. Do not derive boundary-line layers.
If an outline request could mean either a polygon overlay or a border-only
style, clarify the intent unless prior context already resolves it.

Validate every requested label, tooltip, color, size, and filter field against
that exact file/internal layer, including actual scalar types and missing/null
values. Numeric styling requires numeric values, not numeric-looking text.
Suggest real fields on a miss; never invent an alias or silently substitute one.
Missing feature names remain missing; do not fill them from guesses. Use the
same category/color mapping when comparing equivalent files, independent of
feature order. Raster imagery has no feature labels, fields, or attribute filters.
For equivalent sources with different sampling coverage, use the same
explicit category-to-color mapping for both, based on the complete validated
source inventory. Sorting each sample independently is not enough:
missing categories can shift every later color. The expression must include
the shared palette, not just categories observed in one tile sample.
Do not generate a palette solely from truncated field values or an incomplete
PMTiles sample. Obtain a complete validated category inventory and ensure the
explicit palette covers it before writing; do not silently assign unobserved
categories a fallback color.

### Filters and draw order

Filters are layer-scoped, combined with AND, and do not alter source files.
Persist regional scope filters on every applicable layer; filtering one layer
does not filter the others. Keep identifier codes in their actual type:
string `"06"` must not become number `6`.

```json
{
  "id": "<new-filter-uuid>",
  "type": "text",
  "field": "<verified-text-field>",
  "locked": true,
  "value": ["<verified-value>"]
}
```

Numeric filters require **inclusive** `min` and `max`. For an integer count > 0,
first verify that the field contains integer counts; then use `min: 1` and
the verified upper bound. Do not translate a strict decimal comparison to
`min: 0`, guess an epsilon, or invent an upper bound. If the supported filter
cannot express the requested predicate, explain that limitation before writing.
GeoJSON and PMTiles do not support date/time filters. On edits, preserve
unrelated filters and reuse existing filter IDs when changing that filter.

The persisted `layerSettings` array is **top-to-bottom** (front-to-back), not
draw-first-to-last. "Counties first, points on top" therefore saves points
before counties. Save foreground layers before background layers, for example
`[annotations, overlay imagery, base imagery]`. `layerSources` order does not
control drawing. Preserve relative order of untouched layers during a reorder,
keep each layer's labels/tooltips/styles/filters attached to its ID, and verify
the reopened Map rather than relying on array shape alone.

### Initial view for data-backed Maps

Choose the view from the user's analytical focus, in this order:

1. Explicit region or selected feature: compute bounds from matching
   geometries, not the full unfiltered file or an unverified `bbox`.
2. Imagery-focused request: use the imagery footprint transformed to
   longitude/latitude, not an overlaid statewide/nationwide boundary extent.
3. Otherwise, use the relevant selected layers' verified geographic bounds.

Persist `basemap.options.center` and `zoom`; source bounds alone do not save
an initial view. Fit in Web Mercator with padding and a stated viewport
assumption. Never use a universal world/default zoom or average latitude as
a substitute for fitting bounds. Cap the fitted zoom at 16 by default so a
single point retains useful context. Use a higher zoom only when the requested
view needs more detail (up to the supported maximum of 22).
Check antimeridian, empty selections, point
extents, and PMTiles zoom availability explicitly. The browser canvas may be a
different size; check the reopened view at the observed viewport.

Contextual layers must not expand the requested focus region. Use selected
regional polygons rather than the full source extent, or the imagery footprint
for an imagery-focused request. Preserve the saved camera on
hide/style/filter/add-layer edits unless refocusing is requested. Do not change
the camera just because a tileset has a different header center or minimum zoom.

## Lifecycle and terminal writes

| Operation | Method and path | Body |
|---|---|---|
| Create | `POST /v1/workspaces/{workspaceId}/maps` | `displayName`, optional `description`, complete `definition` |
| Get metadata | `GET /v1/workspaces/{workspaceId}/maps/{mapId}` | None |
| Get definition | `POST /v1/workspaces/{workspaceId}/maps/{mapId}/getDefinition` | Empty |
| Update definition | `POST /v1/workspaces/{workspaceId}/maps/{mapId}/updateDefinition` | Complete `definition` |
| Update metadata | `PATCH /v1/workspaces/{workspaceId}/maps/{mapId}` | Only requested `displayName` and/or `description` |
| List | `GET /v1/workspaces/{workspaceId}/maps` | None |
| Delete | `DELETE /v1/workspaces/{workspaceId}/maps/{mapId}` | None |

Create with an inline validated definition, including for an empty Map, so the
schema is explicit. Do not stop after writing a local file. Metadata-first
creation is supported by the API, but requires a subsequent definition write
and readback to complete a requested explicit definition. Read back the
metadata-first creation before that definition write too. If applying the
requested schema fails, report the created item's ID and actual schema as a
partial result, not completed creation. Do not downgrade silently or repeat a
non-retriable failure using the same payload.
Do not use metadata-first creation as an automatic retry after a failed inline
create.

Get-definition is read-only despite POST and may require read/write item
permission and `Item.ReadWrite.All`. Decode every part; stop on malformed or
unsupported payloads rather than substituting an empty definition.

Update-definition **replaces**, rather than merges, the definition. Fetch the
current definition, retain a baseline, apply the smallest patch, validate,
re-encode the changed part, and submit every intended part. Use
`?updateMetadata=true` only for an intentional metadata change through `.platform`.
Prefer PATCH for name/description; the description limit is 256 characters.

Resolve and echo the exact name and ID before deletion. An explicit request to
delete that exact Map is confirmation; ask separately for an ambiguous target
or destructive scope. Omit `hardDelete` by default. Permanent deletion with
`hardDelete=true` needs explicit authorization. If soft deletion is unsupported,
report the failure; never silently escalate to hard deletion.

Creation requires workspace Contributor and a supported Fabric capacity; write
operations require `Item.ReadWrite.All`. Metadata reads use `Item.Read.All` or
`Item.ReadWrite.All`; list uses Viewer and `Workspace.Read.All` or
`Workspace.ReadWrite.All`. Do not assume authentication implies authorization.

## Transport and long-running operations

Use a client that captures response status **and headers** for create,
get-definition, and update-definition; `az rest` body output alone is
insufficient for `202`. For example, obtain the Fabric token using
`az account get-access-token --resource https://api.fabric.microsoft.com`, keep
it in memory, and use PowerShell `Invoke-WebRequest` with Authorization and the
skill header. Never print tokens or use verbose authentication logs.

On `202`, honor `Retry-After` and poll the supplied `Location` until
`Succeeded`, `Failed`, or `Cancelled`, with a bounded timeout. On success,
retrieve the result from the returned result Location or the documented
`GET /v1/operations/{operationId}/result`; status JSON is not the item/definition.
Handle synchronous `201` creation and `200` definition responses too.
PowerShell response-header values can be arrays: use their first string value.
Resolve relative Locations against the request URL. If Location names a
regional redirect host, use the validated `x-ms-operation-id` (or the UUID in
its documented operation path) with the public `/v1/operations/{operationId}`
and `/result` endpoints; do not send credentials to an unvalidated host.

Retain authentication and telemetry on every poll, result, retry, and page.
Only forward credentials to the trusted Fabric API host. Honor `Retry-After`
on `429`. Retain the submitted definition and returned item/operation IDs,
without credentials, so interrupted operations can be reconciled. Before
retrying an uncertain write, inspect its operation status and persisted state;
a client-side failure does not establish that the service rejected the write.

## Readback and completion

Complete each write's readback before the next mutation:

| Write | Required readback |
|---|---|
| Create | Get metadata and get/decode definition; compare name, schema, and intended content |
| Definition update | Get/decode definition; verify requested values and unchanged semantic fields, IDs, and part paths/payloads against the baseline |
| Metadata update | Get metadata; verify changed values and preservation of other user-set metadata |
| Delete | Verify ID absent from all active list pages and/or GET returns documented not-found/deleted state |

A `401`, `403`, network error, or incomplete list is not proof of deletion.
Compare changed JSON parts as parsed content, not by whitespace or property
order. Preserve untouched part paths and payloads exactly. Report server
normalization and accept it only when verified against the applicable contract;
retain returned fields and treat unexplained semantic differences as failures.
REST persistence does not prove visual rendering. Report API error code,
message, request ID, and related resource when available. Stop on failed LROs,
validation errors, or readback mismatches; never discard unknown fields to
force a write. Clean up temporary request files, not users' source assets.

## References

- [Map REST operations](https://learn.microsoft.com/rest/api/fabric/map/items)
- [Definition contract](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/map-definition)
- [Map schema versions and instructions](https://github.com/microsoft/json-schemas/tree/main/fabric/item/map/definition)
- [Customize a Map](https://learn.microsoft.com/fabric/real-time-intelligence/map/customize-map)
- [Style IDs](https://learn.microsoft.com/azure/azure-maps/supported-map-styles)
- [Languages and geopolitical views](https://learn.microsoft.com/azure/azure-maps/supported-languages)
