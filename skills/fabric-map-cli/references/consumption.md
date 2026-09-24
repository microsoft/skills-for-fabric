<!-- Consumption mode reference for fabric-map-cli. -->

> **SCOPE BOUNDARY -- READ-ONLY**
> This mode may list, resolve, get, decode, validate, summarize, or compare
> Fabric Maps. It must not create, update, rename, restyle, or delete anything.

# fabric-map-cli consumption mode

## Capability questions

General questions about supported sources or connections need no workspace,
Map lookup, or authentication. Read the relevant source adapter's capability
summary: [Lakehouse](authoring/lakehouse.md),
[Eventhouse](authoring/eventhouse.md), or
[connections](authoring/connections.md). These documentation reads remain in
consumption mode; do not run the adapters' authoring or source-validation steps.
Distinguish documented Map adapters from the broader Fabric connector catalog.

## Resolve the workspace

For artifact inspection, ask for missing workspace and Map identity rather
than guessing. Listing requires only the workspace.

Use the Fabric API audience and attribution header on every request:

```powershell
$base = "https://api.fabric.microsoft.com/v1"
$skill = "fabric-map-cli"

az rest --method get `
  --resource "https://api.fabric.microsoft.com" `
  --url "$base/workspaces" `
  --headers "x-ms-fabric-skill=$skill"
```

Follow all pages, exact-match `displayName`, and stop for user disambiguation if
more than one workspace matches. If a workspace ID is supplied, verify it with
`GET /v1/workspaces/{workspaceId}` rather than trusting a guessed name.

## List and resolve Maps

```powershell
az rest --method get `
  --resource "https://api.fabric.microsoft.com" `
  --url "$base/workspaces/$workspaceId/maps" `
  --headers "x-ms-fabric-skill=$skill"
```

Prefer `continuationToken` on the original list endpoint until exhausted;
otherwise resolve a relative `continuationUri` against the request URL. Keep
service-provided regional `/v1/` continuation paths on the public Fabric
origin rather than forwarding credentials to an unvalidated host. Optional
`rootFolderId` and `recursive` parameters can narrow folder scope. Resolve a Map
by exact display name; zero matches means not found, and multiple matches
require user selection.
Absent or null continuation fields end pagination; guard absent properties
under PowerShell strict mode.

For metadata:

```http
GET /v1/workspaces/{workspaceId}/maps/{mapId}
```

Metadata inspection requires read permission and `Item.Read.All` or
`Item.ReadWrite.All`.

## Read and decode a definition

```http
POST /v1/workspaces/{workspaceId}/maps/{mapId}/getDefinition
```

This is a read-only action even though it uses POST. It can return `202
Accepted`; poll `Location` using `Retry-After`, then obtain the operation result.
Capture HTTP status and headers (for example with `Invoke-WebRequest` and an
in-memory Azure CLI Fabric token), not just `az rest` body output. Preserve the
skill header on every poll and result GET. Handle synchronous `200` too; stop
on failed/cancelled operations or a bounded timeout. Only forward authentication
to the trusted Fabric API host.
Normalize PowerShell header arrays to their first string value. For a regional
LRO Location, use the validated operation UUID with public
`/v1/operations/{operationId}` and `/result` endpoints.
The public API currently requires read/write permission and
`Item.ReadWrite.All` for this operation. If the caller has only read permission,
report that metadata can be inspected but the public definition cannot be
retrieved with the current identity.

Decode every `InlineBase64` part as UTF-8. `map.json` is required; `.platform`
and source-specific parts are optional. For source-specific integrity checks,
consult the relevant adapter without entering its authoring workflow.

Never execute embedded queries merely to inspect a definition. Treat them as
configuration unless the user separately asks to validate results through the
source's read-only workflow.

## Summary shape

Use real metadata and decoded definition, never a sample or inferred default.
If retrieval fails, report the limitation and summarize only what was obtained.

Present the Map in this order:

1. Item metadata: name, description, workspace, Map ID.
2. Basemap: style, theme, center/zoom/pitch/bearing, language, geopolitical view,
   and enabled controls; distinguish omitted settings from explicit values.
3. Data sources: item type and resolved display name when available.
4. Layer sources: name, type, refresh interval, source item/connection.
5. Layers: visibility, geometry/point rendering, spatial columns, filters,
   labels, and tooltips.
6. Definition integrity findings.

Redact credentials and sensitive connection details. IDs may be shown when
useful for administration, but do not mistake an ID for a display name.

## Read-only integrity checks

- `map.json` exists, decodes as UTF-8 JSON, and references a known schema.
- Each UUID-formatted field is valid.
- Every `layerSettings[].sourceId` resolves to exactly one layer source.
- Adapter-owned parts and spatial mappings agree with their source types.
- Distinguish definition references from independently verified source access;
  inspect source metadata only when needed, not credentials or underlying data.
- Refresh intervals are nonnegative.
- Opacity and numeric style ranges satisfy the published schema.
- Unknown fields are reported, not removed.

Schema validation is read-only. A valid definition does not guarantee that data
currently exists or that the UI can render every feature.

## Rules

### MUST

- Perform only GETs and the read-only `POST .../getDefinition`.
- Handle pagination and LROs.
- Preserve and inspect all definition parts.
- Say explicitly when permissions prevent definition retrieval.
- Switch to authoring mode before any proposed fix is applied.

### AVOID

- Updating a definition as a way to test whether it is valid.
- Executing source queries without the user's request.
- Fetching connection credentials.
- Treating Azure Maps resources or Power BI map visuals as Fabric Map items.

## Authoritative references

- List Maps:
  https://learn.microsoft.com/en-us/rest/api/fabric/map/items/list-maps
- Get Map:
  https://learn.microsoft.com/en-us/rest/api/fabric/map/items/get-map
- Get Map Definition:
  https://learn.microsoft.com/en-us/rest/api/fabric/map/items/get-map-definition
