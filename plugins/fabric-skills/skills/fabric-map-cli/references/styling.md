# Fabric Map styling and camera

Read this alongside the selected mode and source adapters through `SKILL.md`.
The authoring reference owns lifecycle, schema selection, encoding, and readback.
In consumption mode, inspect these settings without changing them.

## Contents

- [Common styling](#common-styling)
- [Shared data-layer settings](#shared-data-layer-settings)
- [Filters and draw order](#filters-and-draw-order)
- [Initial view for data-backed Maps](#initial-view-for-data-backed-maps)

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

## Shared data-layer settings

GeoJSON, vector PMTiles, Kusto results and external feature services use the same
geometry-family styling.
Source adapters supply the source discriminator, path/query part, spatial
mapping and any internal tile-layer binding. Do not duplicate styling per
format. Kusto uses either a latitude/longitude pair or one geometry column,
validated independently for each entity. Build settings from verified fields
and geometry, then validate the complete definition against the selected
schema before writing.

Use fixed styling for a uniform presentation and data-driven styling to compare
feature attributes: distinguish categorical values or reveal numerical spatial
patterns through supported ranges or gradients. This is shared vector-layer
behavior, independent of Lakehouse or Eventhouse sourcing; discover exact
bindings and supported renderings through the capability-discovery rule.
Clustering groups compatible point features for readability; verify support
for the source and rendering rather than assuming it applies to every vector
layer.

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
that exact file/internal layer, KQL entity result, or feature-service result,
including actual scalar types and missing/null values. Numeric styling requires
numeric values, not numeric-looking text.
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

## Filters and draw order

Filters are layer-scoped, combined with AND, and do not alter source files or
KQL entities. Region filters select features by attribute membership, not by
spatial overlap.
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

## Initial view for data-backed Maps

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
