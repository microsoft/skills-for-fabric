# Fabric Map authoring

This reference owns workspace/Map resolution, the definition envelope, common
styling, and the public REST lifecycle. Source adapters own source discovery,
data validation, and any additional definition parts.

## Requirements

Identify the operation and ask for missing values using the host's question
tool: workspace and new Map display name for creation; workspace and existing
Map identity for edits/deletion; the new value for an unspecified change.
Ask only for inputs needed by that operation. Do not require data for an empty
Map, or a source adapter for metadata or basemap edits.
If a required value is absent from the request and prior user context, ask and
wait; do not search unrelated local files for an implicit target.

For source/layer changes, read the relevant adapter and validate only the
affected sources before assembling the complete definition. Do not provision
prerequisite data or connections as a hidden side effect.

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

## Default schema and blank definitions

Use **2.0.0** for new Maps unless the user explicitly requests a different
version. Fetch that schema directly and validate locally, including formats
and documented bounds not enforced by the schema:

`https://developer.microsoft.com/json-schemas/fabric/item/map/definition/2.0.0/schema.json`

Use the JSON Schema dialect declared by the downloaded schema's own `$schema`,
not the Map definition version, to select the validator. The Map 2.0.0 schema
declares Draft 7. With Python `jsonschema`, explicitly use `Draft7Validator`
with a `FormatChecker`; automatic selection may not recognize the schema's
HTTPS Draft 7 dialect URI and may fall back to another draft. For other
schemas, select their declared dialect instead of forcing Draft 7. Stop and
report an unsupported dialect rather than silently falling back. Do not
rewrite either `$schema` URL to resolve a local validator compatibility issue.
Dialect selection does not replace the format and documented-bounds checks.

Normal authoring does not discover the highest published version, probe newer
versions, or retry with another schema. Version changes are separate, explicit
requests. On edits, preserve the existing Map's `$schema`; the default is not
permission to upgrade or downgrade an existing definition.

A request without sources creates an empty Map, not a source-selection
workflow. Use the default schema URL and empty arrays:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/map/definition/2.0.0/schema.json",
  "basemap": {},
  "dataSources": [],
  "iconSources": [],
  "layerSources": [],
  "layerSettings": []
}
```

Here "empty" means no data or layers; it does not require the `blank` basemap
style. `dataSources` identifies inputs, `iconSources` defines reusable symbols,
`layerSources` describes data retrieval, and `layerSettings` describes rendering.
Each layer's `sourceId` must resolve to a unique layer source. Preserve IDs on
updates; generate UUIDs only for genuinely new UUID-formatted entries.

### Required blank-Map completion response

After successful creation and readback, read the capability summaries in
[Lakehouse](authoring/lakehouse.md), [Eventhouse](authoring/eventhouse.md), and
[connections](authoring/connections.md). Do not run their source-discovery or
setup procedures. Even when the request only says "create a Map", the final
response must include all three parts below:

1. **Created:** actual workspace, Map name/ID, persisted schema, and confirmation
   that no data sources or layers exist. Qualify visual rendering separately.
2. **Add later:** say data and layers can be added later, then give a compact
   three-row source table using the coverage below and the adapters' limits.
3. **Needed for a follow-up:** source workspace/item or existing connection;
   file path/format, KQL entity/query, or published imagery layer/collection;
   spatial fields/geometry for vectors; desired rendering and refresh/styling
   preferences. State these as future inputs, not questions or prerequisites.

| Source row | Required coverage |
|---|---|
| Lakehouse | GeoJSON, vector/raster PMTiles, and COG; compatible points, lines, polygons, heatmaps, and extrusions versus raster imagery; key file/format limits |
| Eventhouse / KQL Database | Coordinates or GeoJSON geometry, compatible vector renderings, and result/function limits; distinguish direct table preview limits from general query results |
| External connections | Name Geospatial Web Services for WMS/WMTS and Microsoft Planetary Computer for MPC Pro; imagery-only rendering and projection/image-format limits, not arbitrary Fabric connectors |

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

Get and decode the existing definition first. Patch only requested properties;
create missing containers without replacing existing siblings. Do not migrate
`$schema`, reset arrays, or apply new defaults during an unrelated edit.

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
on `429`. Do not blindly retry a timed-out create: resolve whether it already
created the Map before attempting another mutation.

## Readback and completion

Complete each write's readback before the next mutation:

| Write | Required readback |
|---|---|
| Create | Get metadata and get/decode definition; compare name, schema, and intended content |
| Definition update | Get/decode definition; verify requested values and unchanged semantic fields, IDs, and part paths/payloads against the baseline |
| Metadata update | Get metadata; verify changed values and preservation of other user-set metadata |
| Delete | Verify ID absent from all active list pages and/or GET returns documented not-found/deleted state |

A `401`, `403`, network error, or incomplete list is not proof of deletion.
Report server normalization explicitly instead of hiding an unexpected diff.
REST persistence does not prove visual rendering. Report API error code,
message, request ID, and related resource when available. Stop on failed LROs,
validation errors, or readback mismatches; never discard unknown fields to
force a write. Clean up temporary request files, not users' source assets.

## References

- [Map REST operations](https://learn.microsoft.com/en-us/rest/api/fabric/map/items)
- [Definition contract](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/map-definition)
- [Default schema](https://developer.microsoft.com/json-schemas/fabric/item/map/definition/2.0.0/schema.json)
- [Customize a Map](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/customize-map)
- [Style IDs](https://learn.microsoft.com/en-us/azure/azure-maps/supported-map-styles)
- [Languages and geopolitical views](https://learn.microsoft.com/en-us/azure/azure-maps/supported-languages)
