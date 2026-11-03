# Connection source adapter

For authoring, read this after `../authoring.md` when a layer references a Fabric
Connection. For capability questions, read the summary without listing tenant
connections or running setup.

## Documented Map adapters

| Connection type (Fabric UI) | Data and rendering | Limits |
|---|---|---|
| Geospatial Web Services | External OGC WMS / WMTS raster imagery, or WFS, OGC API - Features, and Esri Feature Service vector features | HTTPS service endpoint; select a layer or collection published by that service |
| Microsoft Planetary Computer | Microsoft Planetary Computer Pro (MPC Pro) GeoCatalog imagery through WMTS | Entra OAuth 2.0; connection creation requires GeoCatalog Reader access and a nonguest tenant account |

These are distinct documented UI connection types; do not derive REST connector
type identifiers from their labels. Resolve the existing connection's metadata.
WMS/WMTS imagery requires EPSG:3857 and JPEG or PNG images. A Map can reference
up to 100 external connections.

Imagery sources provide opacity, visibility, and layer stacking, not
point/line/polygon features, vector heatmaps, or extrusions. Feature services
provide read-only points, lines, and polygons with attributes, styled through the
shared data-layer settings. Both can be combined with other layers. These
external integrations are documented preview features; the presence of another
provider in Fabric's general connector catalog does not establish Map support.

Identify the existing connection from the request, existing Map, or resolved
variable target. Inspect read-only metadata for its endpoint and published
resources, including the GeoCatalog, collection, and configured WMTS resource
for MPC Pro. Ask only for an unresolved imagery layer or feature
layer/collection selection; do not request discoverable endpoint details or
invent IDs from display names.

## Scope and ownership

This adapter references existing Fabric Connections. Creation, credential
replacement/rotation, and MPC Pro endpoint registration belong to an explicitly
authorized connection/provider administration workflow, not Map CRUD.
Never reveal credentials.

Fabric Map definitions store connection IDs and provider resource identifiers,
not secrets.

## Resolution and validation

1. List Fabric Connections with pagination using `GET /v1/connections`, the
   Fabric audience, and the skill telemetry header.
2. Exact-match the intended connection by display name and compatible
   connection type.
3. If more than one connection matches, ask the user to choose.
4. Validate the provider resource/layer and supported projection/image format
   using read-only metadata. For feature services, also validate geometry,
   response format, attribute types, requested output fields, and source filters
   against advertised query capabilities and current protocol requirements.
   Report anything that cannot be verified.
5. Never print credentials, tokens, keys, or full secret-bearing connection
   payloads.

Feature services require a publicly reachable HTTPS service root and EPSG:4326
features; WFS and Esri require GeoJSON output. Check mixed-geometry restrictions
in the feature-service references before selecting rendering options. Account
for viewport-based retrieval, provider paging, and the 100,000-feature layer
limit before claiming completeness.

Connections are tenant-scoped resources; do not assume a workspace association
that the API does not expose.

## Definition fragments

Derive the reference branch from the operation's selected schema using the
shared schema-selection rules. For a new Map whose schema supports the
nondeprecated connection-reference model, use a stable `datasourceId`:

```json
{
  "datasourceId": "imagery-source",
  "connection": {
    "connectionId": "<connection-guid>"
  }
}
```

Link the connection layer source through that same data source:

```json
{
  "id": "<stable-layer-source-id>",
  "name": "<source name>",
  "type": "connection",
  "datasourceId": "imagery-source",
  "connectionResourceId": "<provider resource identifier>"
}
```

If the selected schema lacks that branch, use only the legacy connection and
layer-link fields that its applicable alternatives require. Do not combine the
two representations. Preserve an existing Map's representation unless a schema
migration is explicitly requested.

Use the exact source type and resource identifier supported by the selected
connection/provider and current schema. Do not infer them from a display name.
Render imagery sources with `layerSettings[].options.type: "raster"` and the
matching layer-source ID; do not add vector-only `options.sourceLayer`. Render
feature-service sources as vector layers through the shared
[data-layer settings](../authoring.md#shared-data-layer-settings). Store source
queries and output fields in the selected schema's source-query structure,
separate from Map display filters. Preserve them during visual edits; use the
documented source workflow for retrieval changes.

Anonymous, Basic, and API-key authentication are documented for WMS/WMTS, WFS,
and OGC API - Features; Esri Feature Service supports Anonymous and API key,
not Basic. MPC Pro requires Entra OAuth 2.0. Authentication stays in the
Fabric Connection, never in a Map definition.

## Security rules

- Do not retrieve or display secrets to resolve a connection.
- Do not embed secrets, SAS tokens, API keys, or bearer tokens in `map.json`.
- Never send Fabric API credentials to provider endpoints.
- Stop if a provider requires a secret in the definition rather than a Fabric
  Connection reference.
- Treat connection replacement as a semantic source change and validate the
  provider resource before the Map update.

## Readback

After the shared terminal write, verify that the persisted data source and layer
source contain the intended connection ID, selected reference branch and link,
and resource ID, plus any feature-service source query and output fields.
Report connection access or provider-resource failures separately from Map
definition persistence.

## References

- [WMS/WMTS and MPC Pro capabilities](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-external-sourced-imagery)
- [Connection setup and MPC Pro prerequisites](https://learn.microsoft.com/fabric/real-time-intelligence/map/add-external-sourced-imagery-layer)
- [Feature-service capabilities and restrictions](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-external-feature-services)
- [Feature-service setup and metadata checks](https://learn.microsoft.com/fabric/real-time-intelligence/map/add-external-feature-service-layer)
- [List connections](https://learn.microsoft.com/rest/api/fabric/core/connections/list-connections)
