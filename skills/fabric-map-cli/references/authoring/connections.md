# Connection source adapter

For authoring, read this after `../authoring.md` when a layer references a Fabric
Connection. For capability questions, read the summary without listing tenant
connections or running setup.

## Documented Map adapters

| Connection type (Fabric UI) | Data and rendering | Limits |
|---|---|---|
| Geospatial Web Services | External OGC WMS / WMTS raster imagery | HTTPS service endpoint; select a layer published by that service |
| Microsoft Planetary Computer | Microsoft Planetary Computer Pro (MPC Pro) GeoCatalog imagery through WMTS | Entra OAuth 2.0; connection creation requires GeoCatalog Reader access and a nonguest tenant account |

These are distinct documented UI connection types; do not derive REST connector
type identifiers from their labels. Resolve the existing connection's metadata.
WMS/WMTS imagery requires EPSG:3857 and JPEG or PNG images. A Map can reference
up to 100 external connections.

Both adapters provide imagery with opacity, visibility, and layer stacking,
not point/line/polygon features, vector heatmaps, or extrusions. They can be
combined with vector layers. These imagery integrations are documented preview
features; the presence of another provider in Fabric's general connector
catalog does not establish Map support.

To add imagery, obtain the existing connection identity, WMS/WMTS endpoint and
published layer/resource ID. For MPC Pro, also identify the GeoCatalog,
collection, and configured WMTS resource. Do not invent a resource ID from
the connection display name.

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
   using read-only metadata; report anything that cannot be verified.
5. Never print credentials, tokens, keys, or full secret-bearing connection
   payloads.

Connections are tenant-scoped resources; do not assume a workspace association
that the API does not expose.

## Definition fragments

Data source:

```json
{
  "itemType": "Connection",
  "connectionId": "<connection-guid>"
}
```

Connection layer source:

```json
{
  "id": "<stable-layer-source-guid>",
  "name": "<source name>",
  "type": "connection",
  "connectionId": "<connection-guid>",
  "connectionResourceId": "<provider resource identifier>",
  "refreshIntervalMs": 0
}
```

Use the exact source type and resource identifier supported by the selected
connection/provider and current schema. Do not infer them from a display name.
Render these sources with `layerSettings[].options.type: "raster"` and the
matching layer-source UUID; do not add vector-only `options.sourceLayer`.

Anonymous, Basic, and API-key authentication are documented for Geospatial
Web Services; MPC Pro requires Entra OAuth 2.0. Authentication stays in the
Fabric Connection, never in a Map definition.

## Security rules

- Do not retrieve or display secrets to resolve a connection.
- Do not embed secrets, SAS tokens, API keys, or bearer tokens in `map.json`.
- Stop if a provider requires a secret in the definition rather than a Fabric
  Connection reference.
- Treat connection replacement as a semantic source change and validate the
  provider resource before the Map update.

## Readback

After the shared terminal write, verify that the persisted data source and layer
source contain the intended connection ID and resource ID. Report connection
access or provider-resource failures separately from Map definition persistence.

## References

- [WMS/WMTS and MPC Pro capabilities](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/about-external-sourced-imagery)
- [Connection setup and MPC Pro prerequisites](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/add-external-sourced-imagery-layer)
- [List connections](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-connections)
