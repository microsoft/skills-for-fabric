# Lakehouse source adapter

For authoring, read this after `../authoring.md` when a layer uses Lakehouse
files. For capability questions, read the summary only; no source lookup is
needed. The shared reference owns lifecycle, encoding, update, and readback.

## Capabilities

Lakehouse layers are file-backed and best suited to reference, boundary, vector
tile, and imagery data. Supported documented formats include:

- GeoJSON for point, line, and polygon features in EPSG:4326
  (longitude/latitude), up to 100,000 features per file.
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

Identify the Lakehouse from the request, existing Map, or resolved variable
target. A variable identifies the item, not its file. Resolve the intended file
from the request, existing layer, or scoped file discovery; clarify unresolved
file or tileset-layer choices. Verify format and geometry/properties through
the validation below rather than requesting them as setup inputs.

Map authoring does not modify source data. Report local validation and service
errors with the affected file or layer and the returned code/message, when
available. Stop the failed workflow without offering reprojection, conversion,
simplification, or derived files as recovery. Source-data preparation belongs
to a separately requested Lakehouse/Spark workflow.

## Resolve workspace, Lakehouse, and exact file

Reuse IDs from a supplied Fabric URL or existing Map; verify the workspace with
`GET /v1/workspaces/{workspaceId}` and the Lakehouse with
`GET /v1/workspaces/{workspaceId}/lakehouses/{lakehouseId}`. For names, paginate
workspaces and that workspace's Lakehouses and exact-match `displayName`; stop
on ambiguity.

Use the verified Lakehouse's `properties.oneLakeFilesPath` and the workspace's
OneLake endpoint metadata, not a guessed hostname. Schemas-enabled Lakehouses
may reject the **table** listing API; this is not evidence that files are missing.
Discover files using the documented ADLS-compatible OneLake file interface:

```http
GET https://<verified-dfs-host>/<workspaceId>?resource=filesystem&directory=<lakehouseId>%2FFiles&recursive=true
Authorization: Bearer <in-memory Storage-audience token>
x-ms-version: 2023-11-03
```

Obtain the token with `az account get-access-token --resource
https://storage.azure.com/`; never print or save it. Follow the
`x-ms-continuation` response header until exhausted. For a supplied subdirectory,
narrow discovery to that directory. Exact-match the requested `Files/...` path
or basename among non-directory entries; duplicate basenames require selection,
not the first match. Preserve filename case and spaces. URL-encode path
segments for HTTP, but store the original `Files/...` path in the definition.
Reject traversal paths.

HEAD the resolved file and record length, ETag and modification time. Read its
content (or verified byte ranges for archives), using conditional reads when
available so validation and writing cannot mix different source versions.
Use Storage tokens only for the verified OneLake host, Fabric tokens only for
the public Fabric API, and never forward either to arbitrary redirects.

Name an unresolved file after complete discovery or a confirmed path-not-found
response. A permission error, timeout, or incomplete page is not "file missing."
Perform **no Map write** for unresolved sources.
Do not create a blank Map before source validation.

## Inspect the selected sources

Read content, not just the extension. Inspect each input independently even
when two filenames appear to describe the same data. Keep evidence outside
the Map definition; the schema does not accept arbitrary validation metadata.

Use available read-only format readers to inspect verified downloads or
authenticated byte ranges. Validate requested internal layers, geometry,
fields, and numeric bindings explicitly. Compute selected extents using typed
predicates without changing the source; serialize Map filters using the
shared authoring reference, not a reader's filter syntax.
Report inspection errors and stop before writing. Successful inspection
supports definition assembly; it does not guarantee service acceptance or
rendering. If a required reader is unavailable or decoding fails, report
inspection as incomplete rather than treating the source as validated.

### GeoJSON

- Validate the FeatureCollection, feature geometries, and finite coordinates.
  Report unsupported or malformed geometry; do not convert it. Count null and
  empty geometries separately rather than inventing locations.
- Check longitude/latitude coordinates and any declared CRS against EPSG:4326.
  Report an incompatible projection and stop; do not reinterpret projected
  coordinates as degrees or offer reprojection.
  Treat an explicit legacy `crs: null` conservatively as an
  unknown CRS, rather than assuming WGS84. An absent `crs` uses GeoJSON's
  longitude/latitude convention. Confirm the source CRS in a separately
  requested source-data workflow; Map authoring does not rewrite metadata.
- Count the **whole file**, not a sample, the current filter, or exploded
  MultiPolygon parts. More than **100,000 features per file** blocks normal
  GeoJSON creation. Report the measured count and recommend PMTiles. A filter
  is not a way around the file limit.
- Inventory properties across all features: scalar types, null/missing counts,
  real category values, numeric ranges, and usable name/description fields.
  Validate requested fields and values against the exact layer. Keep leading
  zero text codes. Labels on nameless features remain absent.
- Compute full and selected geographic bounds from actual coordinates. Clarify
  an empty or ambiguous feature selection before choosing the initial view.

### Vector PMTiles

- Check magic bytes, **archive version**, section
  offsets/lengths, compression, and the header tile type. This is independent
  of the Map schema version. Use a reader compatible with the archive version
  and compression. Require MVT for the vector path; route raster PMTiles to
  [Raster PMTiles](#raster-pmtiles), not vector styling or COG validation.
- Validate longitude/latitude bounds, center and zoom range. Check metadata
  against the header and report inconsistencies. An archive's suggested center
  zoom is not an instruction to reset an existing Map camera.
- Discover **all** `vector_layers[].id` values and fields; use `tilestats` when
  present, then decode actual MVT tiles to verify geometry and requested fields.
  Record the sample budget and observed types. Increase the sample budget
  or inspect targeted tiles if a requested layer/field is not
  observed. Sampling must not be presented as exhaustive coverage.
  Establish full-scan completion from reader exhaustion, not equality with an
  optional header count. Counts may be unknown, and addressed tiles can share
  the same stored payload.
- Resolve requested layers against the real inventory, including their geometry
  families. On a missing internal layer, name it and list the available choices;
  do not write. Add settings only for the selected internal layers and share
  one layer source per archive when appropriate.
- Do not sum tiles, fragments, vertices, or appearances at multiple zooms as
  logical features. For equivalent-file comparisons, compare archive metadata
  with the complete GeoJSON count and, when identity matters, deduplicate stable
  original feature IDs across tiles and compare IDs/properties. Disclose
  metadata-only or sampled evidence. Tiling can clip, simplify, and duplicate
  geometry without adding logical source features.
- Minimum source zoom can be higher than a regional camera. Do not copy that
  minimum into `options.minZoom` and accidentally hide a requested layer.
  Verify the actual runtime at the saved regional view; report unavailable
  detail rather than zooming to the wrong region or silently regenerating tiles.

### Raster PMTiles

- Validate PMTiles magic bytes, archive version, section offsets/lengths,
  compression, and header tile type with a compatible reader. Require a
  supported raster image tile type (such as PNG or JPEG), not MVT; decode
  sampled tiles to verify the image encoding matches the header and report
  the sample scope. Unknown or unsupported types block writing.
- Validate longitude/latitude bounds, center, zoom range, and metadata/header
  consistency. Use the imagery bounds and intended focus for the opening view;
  do not reset an existing camera from the archive's suggested center.
- Use imagery settings only: opacity, visibility, and order. Do not require
  `vector_layers`, vector fields, or geometry; attribute filtering, labels,
  tooltips, heatmaps, and extrusions do not apply.
- Do **not** apply the COG checks below: TIFF structure, EPSG:3857 metadata,
  RGB/RGBA band counts, and TIFF display-band types are not PMTiles validation.
  Continue to **Before writing** after this path succeeds.

### Cloud Optimized GeoTIFF

- Verify TIFF/BigTIFF content and **structural cloud optimization**, not `.tif`,
  a `LAYOUT=COG` tag, or "tiled" alone. Use strict structural validation to
  check IFD/overview ordering,
  internal tiling, and data layout. Surface errors and warnings.
- Check EPSG:3857, 3-band RGB or 4-band RGBA, and the display-band data types.
  Verify that the display-band types are supported by the direct RGB imagery
  path; do not infer compatibility from the file extension. Report incompatible
  projection, bands, or types without offering conversion.
- Record raster dimensions, blocks, overviews, projected extent and its
  geographic transform. Use the imagery footprint for an imagery-focused
  initial view, not the extent of contextual polygon layers.
- Choose the opening view from the validated imagery extent and the user's
  intended focus, accounting for applicable source and renderer constraints.
  Do not assume a fixed zoom or generalize one file's behavior to other COGs.
  Verify imagery at the saved view when rendering can be observed; otherwise
  report it as unverified. If the requested view cannot be supported, explain
  the limitation without silently changing the requested scope or source data.
- Validate every image independently. Opacity and order are saved per imagery
  layer. Attribute filtering, labels, tooltips and point styling do not apply.

### Before writing

Complete discovery, compatibility, field/geometry/filter selection, layer order,
camera selection, and full-schema validation **before the first mutation**.
For a multi-source create or update, a failed input blocks the whole requested
write. Do not silently omit it, create a partial Map, or substitute another
source. Report the failure without attempting source-data repair.

## Definition fragments

Derive the reference branch from the operation's selected schema using the
shared schema-selection rules. For a new Map whose schema supports the
nondeprecated item-reference model, use a stable `datasourceId`. For a direct
Lakehouse reference use the **resolved Lakehouse item ID** as that string:

```json
{
  "datasourceId": "<resolved-lakehouse-guid>",
  "item": {
    "workspaceId": "<workspace-guid>",
    "itemId": "<lakehouse-guid>"
  }
}
```

Link the layer source through that same data source:

```json
{
  "id": "<stable-layer-source-id>",
  "name": "<source name>",
  "type": "geojson",
  "datasourceId": "<resolved-lakehouse-guid>",
  "relativePath": "Files/path/data.geojson"
}
```

If the selected schema lacks that branch, use only the legacy workspace-item
and layer-link fields that its applicable alternatives require. Do not combine
the two representations. Preserve an existing Map's representation unless a
schema migration is explicitly requested.

Use the resolved item ID for new direct Lakehouse references so the source
also resolves during rendering. This does not impose a UUID requirement on
every string identifier. Preserve existing aliases during unrelated edits.

| Validated format | Layer source fragment | Layer settings fragment |
|---|---|---|
| GeoJSON | `type: "geojson"`, exact `Files/...geojson` path | `sourceId`, `options.type: "vector"`; no `sourceLayer` |
| Vector PMTiles | `type: "pmtiles"`, exact `Files/...pmtiles` path | `sourceLayerId: "<real-internal-id>"` **and** `options.sourceLayer` with the same value; `options.type: "vector"` |
| Raster PMTiles | `type: "pmtiles"`, exact `Files/...pmtiles` path | `sourceId`, `options.type: "raster"`, `options.opacity`; no vector source layer |
| COG | `type: "cog"`, exact `Files/...tif` or `.tiff` path | `sourceId`, `options.type: "raster"`, `options.opacity`; no vector source layer |

`cog` is the source discriminator, not `raster`, `tiff`, or `geotiff`; `raster`
is the layer rendering type. Check the selected schema and current product
support as in the shared reference; its permissive source `type` string alone
does not prove a discriminator works. Use the common styling/filter/order
settings from [authoring.md](../authoring.md#shared-data-layer-settings).
Assemble these fragments only from successful preflight results, then follow
the shared full-schema validation and read-modify-write procedure.

## Readback

After the shared terminal write, verify:

- the Lakehouse data source has the expected workspace and item IDs;
- the selected data-source branch and its layer link were preserved;
- the layer source has the exact relative path and type;
- the layer setting resolves to that source;
- the source file still exists;
- all intended internal layers, labels, fields, filters, opacity, visibility,
  top-to-bottom order, and initial camera persist;
- untouched layer/source/filter IDs and definition parts match the baseline;
- source ETags/lengths/modification times still match preflight (Map filtering
  and styling must not change the source).

REST readback proves configuration persistence, not successful rendering.
When the Map can be opened, check source-load errors, placement, stacking,
visibility, imagery, labels, and tooltips at the saved view. Report any service
error as returned, including the affected source and request ID when available;
do not encode environment-specific restrictions as new validation rules.
If a definition persisted but a layer failed to load, report both facts rather
than claiming completion. If rendering cannot be observed, mark it unverified.

## References

- [Lakehouse capabilities](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-lakehouse-layers)
- [File limits and layer setup](https://learn.microsoft.com/fabric/real-time-intelligence/map/add-lakehouse-layer)
- [Vector and raster PMTiles](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-tile-sets)
- [OneLake API access and Storage authentication](https://learn.microsoft.com/fabric/onelake/onelake-access-api)
- [PMTiles v3 contract](https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md)
- [Layer-scoped filtering](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-data-filtering)
