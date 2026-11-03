# Eventhouse source adapter

For authoring, read this after `../authoring.md` when a layer uses KQL results.
For capability questions, read the summary only; no source lookup is needed.
The shared reference owns lifecycle, encoding, styling, updates, and readback.

## Capabilities

Eventhouse layers use data from a KQL Database. Supported entities are tables,
materialized views, and stored, parameterless tabular functions. Spatial data
can use either of two modes:

- Numeric latitude and longitude columns for point locations.
- A dynamic GeoJSON geometry column for points, lines, or polygons.

Compatible results support bubbles, markers, heatmaps, line and polygon
styling, and polygon extrusions. These are vector layers, not raster imagery.
Automatic refresh updates query results while retaining saved layer settings.

Results must stay within the documented Kusto layer limits (currently up to
100,000 features and 20 MB; see References). Map display filters do not reduce
the source result counted against these limits. A table preview shows only a
subset of rows and does not establish the full layer count. Functions and
materialized views can provide aggregated or filtered results.

Identify the KQL Database from the request, existing Map, or resolved variable
target. Resolve the entity and inspect its output before asking for unresolved
entity or spatial-field choices. Discover metadata rather than requesting it
as setup input.

Map authoring does not modify KQL entities or source data. Report validation
and service errors with the affected entity or layer and the returned
code/message, when available. Stop the failed workflow without repairing data,
changing geometry, or substituting a different source. An existing compatible
entity can be suggested after verification; creating or changing one belongs
to a separately requested Eventhouse authoring workflow.

## Resolve the KQL Database and entity

Load [eventhouse-cli](../../../eventhouse-cli/SKILL.md) and follow its
**consumption** mode for workspace and item resolution, authentication,
endpoint and database-name discovery, `.show` inventories, and read-only KQL
execution. All source operations in this adapter are read-only; Map authoring
never switches eventhouse-cli to authoring mode.

Map-specific requirements on top of that workflow:

- The Map references the **KQL Database item**, not its parent Eventhouse or
  an Eventstream. When an Eventhouse is supplied, restrict selection to its
  child databases; ask only when the target remains ambiguous.
- Use the query endpoint and database name that eventhouse-cli resolves; do
  not construct them from display names.
- Determine the entity type (table, materialized view, or function) from the
  `.show` inventories, not from naming conventions. A function source must be
  stored, tabular, and parameterless; invoke it with parentheses. Confirm the
  actual output columns with `<entity> | getschema`.
- Request errors, partial-query failures, truncation, and malformed rows make
  a result incomplete and block writing, regardless of HTTP status.
- Name an unresolved entity and list the available entities after complete
  discovery. Access failures or incomplete inventories do not prove an entity
  is missing. Perform **no Map write** for unresolved sources.

## Inspect the selected sources

Inspect each entity independently. A schema or bounded sample helps discover
fields; it does not validate the complete result.

- Run a bounded sample to discover fields. Bound raw temporal queries with a
  time window that fits the request and the measured timestamp range; do not
  invent a timestamp for sources without one. Project only the fields the Map
  needs; avoid unbounded queries over raw tables.
- Measure the full intended result in Kusto, before any preview limit, geometry
  exclusion, or Map filter: row count with `count()` and estimated size with
  `sum(estimate_data_size(*))`. Report results that exceed a documented limit;
  verify any suggested alternative independently.
- Execute the complete result within those limits, projecting the spatial,
  identity, label, tooltip, color, size, and filter fields. Do not save a
  preview limit as a way to truncate an oversized source. Confirm the returned
  row count matches the measured count. If the source is still changing,
  revalidate the final query immediately before writing.
- Inventory field types, null/empty values, categories, and numeric ranges.
  Validate requested fields against the actual result. Suggest real fields
  on a miss; do not invent aliases or labels for unnamed features.
- Record full, usable, and Map-selected counts and bounds separately. Derive
  the initial view from selected valid geometry using the shared camera rules.
  Empty results or selections require clarification before an empty layer
  can be created.

For latest-state functions, verify the entity key, timestamp semantics, and
exact key uniqueness rather than approximate distinct counts. Preserve the
existing reduction and freshness policy; an additional time filter can remove
valid but inactive entities. Changing that policy requires clarification.

When no suitable latest-state entity exists, recommend one built with
`summarize arg_max(<timestamp>, *) by <entity key>` after a time predicate, with
a validated tie-breaker when deterministic selection matters. Creating it is
a separate Eventhouse authoring request.

### Latitude/longitude mode

Discover both columns and their Kusto types. Prefer an unambiguous existing
pair; names alone do not establish validity. Require numeric types, including
explicitly converted output from an existing function. Numeric-looking strings
are not numeric columns. Report conversion failures and usable counts before
recommending a verified conversion function; do not change or substitute the
source.

Validate coordinates with a server-side aggregate rather than downloading
rows. Use the verified numeric columns; the categories are mutually exclusive:

```kql
<verified entity>
| extend Issue = case(
    isnull(<lat>) or isnull(<lon>), "missing",
    not(isfinite(<lat>)) or not(isfinite(<lon>)), "non-finite",
    <lat> == 0 and <lon> == 0, "zero-placeholder",
    <lat> between (-90.0 .. 90.0) and <lon> between (-180.0 .. 180.0), "valid",
    <lon> between (-90.0 .. 90.0) and <lat> between (-180.0 .. 180.0), "possibly-reversed",
    "out-of-range")
| summarize Rows = count(), MinLat = min(<lat>), MaxLat = max(<lat>),
    MinLon = min(<lon>), MaxLon = max(<lon>) by Issue
```

Report counts per category and name affected rows using existing identifiers.
Confirm coordinate order from column meaning and expected geographic scope;
valid ranges alone do not resolve an ambiguous pair. Do not swap, clamp,
geocode, or invent coordinates.

Exclude invalid rows in the **Map-owned** query with a predicate using verified
numeric columns, for example:

```kql
<verified entity>
| where isfinite(Latitude) and isfinite(Longitude)
| where Latitude between (-90.0 .. 90.0) and Longitude between (-180.0 .. 180.0)
| where not(Latitude == 0 and Longitude == 0)
| project <verified required fields>
```

Only valid coordinates contribute to camera bounds. Set the latitude and
longitude column mappings defined by the selected schema (for example,
`latitudeColumnName` and `longitudeColumnName`) and omit the geometry-column
mapping. Coordinate pairs represent **points**, never lines/areas.

### Single geometry-column mode

Require a Kusto `dynamic` column containing GeoJSON geometry objects. Kusto may
return `dynamic` values as JSON text; parse them before validating. A `string`
column of WKT is not a geometry column. Prefer a verified function already
applying `geo_from_wkt` over raw WKT text. Inspect the function output, not merely
its body.

Validate geometry type, coordinate nesting, finite WGS84 positions, line/ring
lengths and closed polygon rings. Count null, empty and invalid shapes and name
the affected rows using existing identifiers/names. Do not repair shapes or
silently convert polygons/lines to points. Set the geometry-column mapping
defined by the selected schema (for example, `geometryColumnName`) and omit
both coordinate mappings.

Report counts per geometry family. A requested geometry family must match
**all** usable geometry before display filtering. For mixed-geometry Maps,
preserve every valid family and use its corresponding rendering settings.
Do not silently discard valid shapes to satisfy a different layer type.

Null geometry from failed WKT conversion can be excluded with
`where isnotnull(<geometry>)`; empty coordinates need a verified nonempty-array
check too. Exclusion predicates must remain valid on refresh; preview row
positions are not stable identifiers. Report malformed nonnull shapes and
stop when safe exclusion cannot be validated.

### Before writing

Complete source, geometry, field, filter, layer-order, and camera validation
before the first mutation. Execute and revalidate the final Map-owned query,
including projections and geometry exclusions. Retain the original invalid-row
counts and reasons alongside the final usable result. Confirm the final query's
feature count and estimated result size are within the documented limits;
report a size that cannot be measured as unverified.

Use read-only queries and available geometry readers; incomplete decoding or
validation blocks writing. Report errors and warnings rather than treating
them as a successful inspection. For multi-source requests, a failed input
blocks the whole intended write; do not create a partial or blank Map instead.

## Definition parts

Derive the reference branch from the operation's selected schema using the
shared schema-selection rules. For a new Map whose schema supports the
item-reference model, use the resolved KQL Database item ID as
the stable `datasourceId` for a direct database reference:

```json
{
  "datasourceId": "<resolved-kql-database-guid>",
  "item": {
    "workspaceId": "<workspace-guid>",
    "itemId": "<kql-database-guid>"
  }
}
```

Link the Kusto layer source through that same data source:

```json
{
  "id": "<stable-layer-source-id>",
  "name": "<source name>",
  "type": "kusto",
  "datasourceId": "<resolved-kql-database-guid>"
}
```

If the selected schema lacks that branch, use only the legacy workspace-item
and layer-link fields that its applicable alternatives require. Do not combine
the two representations. Preserve an existing Map's representation unless a
schema migration is explicitly requested.

Preserve existing aliases during unrelated edits; the direct-item convention
does not impose a UUID requirement on every string identifier.

The associated query is a separate UTF-8 definition part:

```text
queries/layerSource-<stable-layer-source-id>.kql
```

The identifier in the filename must exactly match `layerSources[].id`.
Base64-encode the KQL file like every other definition part.

Assemble the Kusto source and encoded query part from the **executed final
query** and its complete, valid inspection evidence. Reuse the geometry-family
styling, text/numeric filters and camera procedure in
[the shared authoring reference](../authoring.md#shared-data-layer-settings),
as for Lakehouse layers. Validate the complete document against the operation's
selected schema; source fragments alone do not establish validity.

Use a verified table/view reference or parameterless function invocation.
Do not create Queryset-backed layers; a query definition part is not a Queryset
item. Report service rejections without silently changing the source or using
a different definition contract.

## Layer settings and mixed sources

Regional and analytical filters live in `layerSettings[].filters`, not in
stored KQL entities. Preserve leading-zero text codes. Select administrative
areas by their membership field rather than bounding-box intersection, and
apply the intended scope to every relevant layer. Compute selected bounds
before fitting the camera; preserve the saved view on unrelated edits.

Use the shared geometry-compatible styling, filter, visibility, and draw-order
rules. Verify requested rendering against the selected schema and current
product capabilities. Report unsupported styling before writing; do not
change geometry or substitute another visual treatment to approximate it.

A mixed Eventhouse/Lakehouse Map keeps independent data sources, Kusto query
parts, and exact Lakehouse file paths. Each adapter validates its own input;
shared settings control styling, order, and the initial view.

For spatial comparisons, validate the requested relationship against the
actual geometries. Report data discrepancies separately from source-loading
or rendering errors. Preserve source locations and boundaries; Map authoring
does not correct disagreements between datasets.

## Refresh

Save requested refresh intervals in `layerSources[].refreshIntervalMs`, using
milliseconds. Omit an unspecified interval on creation and preserve it on
edits; zero does not mean continuous streaming.

Patch only requested refresh and layer settings in the retrieved full
definition. Preserve unrelated IDs, query parts, geometry mappings, styling,
labels, filters, visibility, order, and camera. Refresh is source-scoped:
confirm the intended scope when a change also affects other layers sharing
that source.

## Readback

After the shared terminal write:

- decode `map.json` and the matching `.kql` part;
- verify source item ID, selected data-source branch and link, layer source ID,
  query filename, and any configured refresh interval;
- compare the persisted query text semantically with the executed query;
- compare labels, tooltips, color/size fields and expressions, geometry mapping,
  filters, visibility, draw order and camera against the intended settings;
- on edits, compare all unrelated settings and part payloads to the baseline;
- verify the intended result count independently of a table preview.

REST readback proves saved configuration, not rendering or automatic refresh.
When the Map can be opened, verify layers at the saved view, observe a configured
refresh, and reopen to check persistence. A separate source query is not
evidence that the Map refreshed. Mark checks that cannot be observed as
unverified, and report service errors as returned without turning
environment-specific behavior into general capability restrictions.

## References

- [Kusto entities and limits](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-kusto-integration)
- [Geometry modes and Kusto layer limits](https://learn.microsoft.com/fabric/real-time-intelligence/map/create-layers-using-kusto-data)
- [Partial query failures](https://learn.microsoft.com/kusto/concepts/partial-query-failures)
- [Fabric Maps overview](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-fabric-maps)
- [Map definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/map-definition)
