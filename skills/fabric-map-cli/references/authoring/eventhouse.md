# Eventhouse source adapter

For authoring, read this after `../authoring.md` when a layer uses KQL results.
For capability questions, read the summary without querying or creating data.

## Capabilities and follow-up inputs

Eventhouse / KQL Database layers use query results containing numeric
longitude/latitude or supported GeoJSON geometry. Compatible results can
render points as bubbles, markers, or heatmaps; line and polygon geometry
supports line/fill styling, with extrusions for suitable polygon data.
Coordinates alone do not define lines or polygons. These are vector layers,
not WMS/WMTS or COG imagery.

Results must not exceed 20 MB. Supported source entities are tables,
materialized views, and stored, user-defined tabular functions without
parameters. Direct **Show Table** previews display only the last 100 ingested
rows; this is not a universal 100-row limit on KQL results. Use functions or
materialized views for aggregated or filtered layers.

To add a layer, obtain the workspace, KQL Database identity, source entity or
query, spatial fields, desired rendering, and refresh interval. Latest-location
queries also need an entity key, timestamp, and time window.

## Scope

The Map references the **KQL Database item**, not the Eventstream that may feed
it and not merely the parent Eventhouse container. Use:

- `eventhouse-cli` consumption mode to resolve the KQL Database, inspect schema,
  validate fields, and observe representative results;
- `eventhouse-cli` authoring mode only if the user explicitly requests creation
  or modification of tables, functions, materialized views, policies, or data.

The Map skill owns only the Map data-source entry, Kusto layer source, query
definition part, refresh behavior, and visualization.

## Source validation gate

Before authoring:

1. Resolve the workspace, Eventhouse, and KQL Database without guessing IDs.
2. Confirm the intended table, function, or materialized view exists; a function
   used as a source must be stored, user-defined, tabular, and parameterless.
3. Confirm latitude/longitude or geometry columns exist and have usable types.
4. Run a bounded, read-only KQL sample with a time filter where a time column
   exists; for static geometry without one, use an explicit row limit instead
   of inventing a timestamp.
5. For "latest location" scenarios, verify the entity key and event-time column
   and confirm the query returns at most one current row per entity.
6. Reject unbounded queries, `*` projections over large datasets, and layer
   results exceeding 20 MB. A bounded sample does not prove the full layer
   result meets that limit; report unverified result size explicitly.

If required source fields or data are absent, stop before creating or updating
the Map.

## Definition parts

Data source:

```json
{
  "itemType": "KqlDatabase",
  "workspaceId": "<workspace-guid>",
  "itemId": "<kql-database-guid>"
}
```

Kusto layer source:

```json
{
  "id": "<stable-layer-source-guid>",
  "name": "<source name>",
  "type": "kusto",
  "itemId": "<kql-database-guid>",
  "refreshIntervalMs": 5000
}
```

The associated query is a separate UTF-8 definition part:

```text
queries/layerSource-<stable-layer-source-guid>.kql
```

Its UUID must exactly match `layerSources[].id`. Base64-encode the KQL file like
every other definition part.

## Query rules

- Bound temporal queries with a time predicate and samples with a row limit.
  For static sources without timestamps, use an explicit row limit.
- Project only fields needed for geometry, labels, tooltips, filters, and
  styling.
- For current position by entity, use latest-row logic such as
  `summarize arg_max(EventTime, Latitude, Longitude) by EntityId`, after the
  time predicate. Resolve timestamp ties with a validated stable tie-breaker
  when deterministic selection is required; `arg_max` alone does not do this.
- Remove rows with null or invalid coordinates.
- Use the exact validated column names in layer spatial mappings.
- Choose a refresh interval appropriate to source cadence and capacity; do not
  assume zero means continuous streaming.

Query creation belongs in the local definition assembly. Changing Eventhouse
schema or data is a separate mutation and must not be hidden inside Map
authoring.

## Readback

After the shared terminal write:

- decode `map.json` and the matching `.kql` part;
- verify source item ID, layer source ID, query filename, and refresh interval;
- compare the persisted query text semantically with the intended query;
- optionally run the read-only query again through `eventhouse-cli` consumption
  mode when the user asks for data validation.

## References

- Kusto entities and limits:
  https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/about-kusto-integration
- Fabric Maps overview:
  https://learn.microsoft.com/en-us/fabric/real-time-intelligence/map/about-fabric-maps
- Map definition:
  https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/map-definition
