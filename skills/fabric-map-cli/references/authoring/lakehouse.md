# Lakehouse source adapter

For authoring, read this after `../authoring.md` when a layer uses Lakehouse
files. For capability questions, read the summary only; no source lookup is
needed. The shared reference owns lifecycle, encoding, update, and readback.

## Capabilities and follow-up inputs

Lakehouse layers are file-backed and best suited to reference, boundary, vector
tile, and imagery data. Supported documented formats include:

- GeoJSON for point, line, and polygon features, up to 100,000 features per file.
- PMTiles for vector tiles or raster imagery. Fabric can consume both, but its
  tileset generation supports vector tiles only.
- Cloud Optimized GeoTIFF (COG) for raster imagery. Current documented support
  requires EPSG:3857 and three-band RGB or four-band RGBA.
- Image files used by `iconSources`.

Compatible vector geometry supports points (bubbles or markers), lines,
polygons, and point heatmaps; compatible polygons can use 3D extrusions.
MultiPoint, MultiLineString, and MultiPolygon follow their geometry family.
Vector PMTiles rendering depends on the geometries and named source layers
encoded in the archive; do not promise point clustering or heatmaps for every
tileset. Raster PMTiles and COG provide imagery, not interactive vector features,
heatmaps, or extrusions. Arbitrary TIFF files are not a substitute for COG.
This adapter does not query Lakehouse SQL/Delta tables directly.

To add a layer, obtain the source workspace, Lakehouse identity, file path and
format, geometry/properties, desired rendering, and optional refresh/styling.

Do not create, transform, upload, or delete Lakehouse files unless the user
separately requests that data-plane work and the owning Lakehouse/Spark skill is
loaded.

## Resolution and validation

1. Resolve the source workspace by exact name.
2. Resolve the Lakehouse by exact display name and type `Lakehouse`.
3. Verify the requested `Files/...` path exists in OneLake.
4. Confirm file type, the GeoJSON feature limit, PMTiles tile kind
   (vector/raster), and applicable geometry/projection/band requirements.
5. Reuse the resolved workspace and item IDs in `map.json`; never derive IDs
   from names.

## Definition fragments

Data source:

```json
{
  "itemType": "Lakehouse",
  "workspaceId": "<workspace-guid>",
  "itemId": "<lakehouse-guid>"
}
```

GeoJSON layer source:

```json
{
  "id": "<stable-layer-source-guid>",
  "name": "<source name>",
  "type": "geojson",
  "itemId": "<lakehouse-guid>",
  "relativePath": "Files/path/data.geojson",
  "refreshIntervalMs": 0
}
```

PMTiles uses `type: "pmtiles"` and a `.pmtiles` relative path. COG uses the
currently documented raster source type and must be validated against the live
schema/documentation before authoring because raster support can evolve.

Layer settings must reference the layer source UUID. For PMTiles, choose
`options.type: "vector"` or `"raster"` to match the archive's tile kind. Vector
PMTiles can require a `sourceLayerId`/`options.sourceLayer` present in the
tileset; do not add vector-only source-layer mappings to raster imagery.

## Readback

After the shared terminal write, verify:

- the Lakehouse data source has the expected workspace and item IDs;
- the layer source has the exact relative path and type;
- the layer setting resolves to that source;
- the source file still exists.

REST readback proves configuration persistence, not successful rendering of a
malformed or unsupported geospatial file.

## References

- [Lakehouse capabilities](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/about-lakehouse-layers)
- [File limits and layer setup](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/add-lakehouse-layer)
- [Vector and raster PMTiles](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/about-tile-sets)
