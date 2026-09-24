# Azure Map Visual Authoring Guide

## Contents

- [Overview](#overview)
  - [When a Map Fails to Render](#when-a-map-fails-to-render)
- [Template](#template)
- [Roles](#roles)
- [Layers](#layers)
  - [Markers — icon, size, and clustering (`bubbleLayer`)](#markers--icon-size-and-clustering-bubblelayer)
  - [Heat map (`heatMapLayer`)](#heat-map-heatmaplayer)
  - [3D column (`barChart`)](#3d-column-barchart)
  - [Path / line (`pathLayer`)](#path--line-pathlayer)
  - [Reference layer — GeoJSON overlay (`referenceLayer`)](#reference-layer--geojson-overlay-referencelayer)
- [Add Data-Driven Formatting](#add-data-driven-formatting)


## Overview

Always use `azureMap` as the visual type for map visuals.

**Do not use `map` or `filledMap`** — they are legacy Bing Maps visuals and
must never be created. `powerbi-report-author validate` raises
`PBIR_VISUAL_TYPE_DEPRECATED` (warning) on these types.

### When a Map Fails to Render

Azure Maps can fail to geocode or render for a variety of reasons (unsupported
data format, ambiguous location names, missing coordinates). When this happens:

1. **Debug the problem** — check field names, data values, geocoding compatibility
2. **Try alternative geographic fields or coordinates** — try lat/lon columns, a
   more specific location column, or a different aggregation level (e.g., country
   instead of city)
3. **Ask the user for clarification** — if you cannot resolve the geocoding issue,
   use `ask_user` to describe the problem and ask which field to use or whether
   lat/lon columns are available
4. **Do not silently substitute a non-map visual** for data/geocoding issues — if
   the user explicitly requested a map and the underlying geography is workable,
   use `ask_user` before changing visual types. Substituting a non-map visual for a
   resolvable data problem violates the design brief.
5. **When Azure Maps is unavailable in the environment** (for example, disabled by
   tenant policy or unsupported region), fall back to a non-map encoding such as a
   `tableEx` of locations with conditional formatting or a `clusteredBarChart` by
   region, and tell the user why the map was replaced. Avoid the legacy `map`
   and `filledMap` visuals as fallbacks; `shapeMap` is a specialized supported
   visual for built-in or custom shape-based geographies, not a general-purpose
   substitute for Azure Maps.

---

## Template

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
  "name": "<20hexchars>",
  "position": { "x": 20, "y": 20, "z": 0, "height": 400, "width": 610, "tabOrder": 0 },
  "visual": {
    "visualType": "azureMap",
    "query": {
      "queryState": {
        "Category": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "<TableName>" } },
                  "Property": "<LocationColumnName>"
                }
              },
              "queryRef": "<TableName>.<LocationColumnName>",
              "nativeQueryRef": "<LocationColumnName>",
              "active": true
            }
          ]
        },
        "Size": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "<TableName>" } },
                  "Property": "<MeasureName>"
                }
              },
              "queryRef": "<TableName>.<MeasureName>",
              "nativeQueryRef": "<MeasureName>",
              "active": true
            }
          ]
        }
      }
    },
    "objects": {}
  }
}
```

## Roles

| Role | Display Name | Kind | Required | Max |
|------|-------------|------|----------|-----|
| Category | Location | Grouping | ✅ | — |
| Size | Size | Measure | — | 1 |
| Series | Legend | Grouping | — | 1 |
| Y | Latitude | GroupingOrMeasure | — | 1 |
| X | Longitude | GroupingOrMeasure | — | 1 |
| Tooltips | Tooltips | Measure | — | — |
| PathID | Path ID | Grouping | — | 1 |
| PointOrder | Point Order | Grouping | — | 1 |

> **Tip**: Bind a geographic column (country, state, city) to `Category`.
> Azure Maps handles geocoding automatically — no explicit lat/lon needed
> unless you have coordinate data.

`PathID` and `PointOrder` are only for the [path layer](#path--line-pathlayer).

## Layers

`azureMap` stacks several layers over the same `Category` locations. Each layer is a
formatting object with an enable toggle. The **bubble/marker layer is on by default**;
enable any other layer explicitly, and set `bubbleLayer.show` to `false` when only that
layer should show. The **path layer is the exception** — keep the marker layer on so the
points render, then enable `pathLayer` to connect them (see below). Discover exact
properties and enum values before authoring:

```bash
# object = bubbleLayer | heatMapLayer | barChart | pathLayer | referenceLayer
powerbi-report-author formatting describe-object azureMap <object>
powerbi-report-author formatting describe-property azureMap <object> <property>
```

Encode every value with
`powerbi-report-author expr encode --kind <bool|integer|number|string|color> <value>`.

| Layer | Object | Enable toggle | Extra roles |
|-------|--------|---------------|-------------|
| Markers | `bubbleLayer` | `show` | `Size` (optional, `sizeByValue`) |
| Heat map | `heatMapLayer` | `show` | `Size` (optional, `heatMapUseSize`) |
| 3D column | `barChart` | `showModern` | `Size` (optional, `heightByValue`) |
| Path (line) | `pathLayer` | `show` (keep `bubbleLayer` on) | `PathID` (required) + `PointOrder` |
| Reference (GeoJSON) | `referenceLayer` | `show` | none (external file) |

> Enable 3D columns with **`barChart.showModern`** (the modern renderer), not the
> legacy `barChart.show`; set height with **`heightPixels`/`heightMeters`** (+
> `heightUnit`), never the legacy `barHeight`.

**Layer compatibility.** Author one primary data layer per visual. The marker, heat map,
3D column, and filled map layers can be combined in one visual, but stacking them is
visually cluttered — prefer a single data layer per visual (or split layers across
visuals). One field-well constraint applies when combining: the **filled map layer
requires the `Size` field well to be empty** — binding `Size` disables it. The **path layer is exclusive with the other data layers**: enabling it
(binding `PathID`) automatically turns off the heat map, 3D column, and filled map layers
and disables bubble clustering. The path layer works only with the marker layer (which
renders its points) and a static `referenceLayer` overlay. The `referenceLayer` and
`tileLayer` are independent context overlays and can be layered on any data layer (only
data-bound reference-layer coloring is unavailable while the path layer is on).

The examples below configure each layer's appearance and magnitude, including
fixed and `Size`-driven scaling.

### Markers — icon, size, and clustering (`bubbleLayer`)

Markers render by default as circle icons. Size them two ways:

- **Fixed radius** — leave the `Size` field well empty, set `sizeByValue` to `false`,
  and set a literal `bubbleRadius`.
- **`Size`-driven** — bind the `Size` field well (see the Template) and set
  `sizeByValue` to `true` to scale bubbles by value.

**Fixed radius:**

```json
"bubbleLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "sizeByValue": { "expr": { "Literal": { "Value": "false" } } },
    "bubbleRadius": { "expr": { "Literal": { "Value": "10D" } } }
  } }
]
```

**`Size`-driven:**

```json
"bubbleLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "sizeByValue": { "expr": { "Literal": { "Value": "true" } } }
  } }
]
```

Cluster nearby points into aggregated bubbles (each labelled with a count) by setting
`clusteringEnabled` to `true`. Clustering requires the marker layer on, the default
`Circle` icon, and no `PathID` bound (custom icons/images and the path layer disable it).

```json
"bubbleLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "clusteringEnabled": { "expr": { "Literal": { "Value": "true" } } }
  } }
]
```

Image markers: set `markerType` to `image`, `imageSourceType` to `imageUrl`, and a valid
http/https URL in `imageUrl`. The map control loads the image cross-origin, so the URL
must be served with CORS (`Access-Control-Allow-Origin`) — a non-CORS URL renders a
broken-image placeholder. Static-authored image markers are unreliable in Power BI
Desktop (placeholder or render error); set marker images interactively in Desktop
instead, and default to `icon` markers for authored reports. Do not apply fill-color
conditional formatting to image markers; Desktop disables the marker Fill group for
`markerType: "image"`. Use Field-only `bubbleLayer.markerRotation` when an image marker
needs data-driven formatting.

### Heat map (`heatMapLayer`)

```json
"heatMapLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "heatMapRadius": { "expr": { "Literal": { "Value": "25D" } } },
    "heatMapRadiusUnit": { "expr": { "Literal": { "Value": "'pixels'" } } },
    "heatMapIntensity": { "expr": { "Literal": { "Value": "0.5D" } } },
    "heatMapUseSize": { "expr": { "Literal": { "Value": "true" } } }
  } }
],
"bubbleLayer": [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ]
```

`heatMapUseSize: true` weights intensity by the `Size` measure. For **fixed intensity**,
leave the `Size` field well empty, set `heatMapUseSize: false`, and use a literal
`heatMapIntensity`. Color stops (`heatMapColorLow` / `heatMapColorCenter` /
`heatMapColorHigh`) are static `fill`s.

### 3D column (`barChart`)

```json
"barChart": [
  { "properties": {
    "showModern": { "expr": { "Literal": { "Value": "true" } } },
    "heightUnit": { "expr": { "Literal": { "Value": "'pixels'" } } },
    "heightPixels": { "expr": { "Literal": { "Value": "80L" } } },
    "widthUnit": { "expr": { "Literal": { "Value": "'pixels'" } } },
    "widthPixels": { "expr": { "Literal": { "Value": "12L" } } },
    "heightByValue": { "expr": { "Literal": { "Value": "true" } } },
    "defaultColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1F77B4'" } } } } }
  } }
],
"bubbleLayer": [ { "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } } ]
```

`heightByValue: true` scales column height by the `Size` measure. For **fixed height**,
leave the `Size` field well empty, set `heightByValue: false`, and use a literal
`heightPixels` (or `heightMeters`). `barShape` is `'0'` (box) or `'1'` (cylinder).

### Path / line (`pathLayer`)

Draws ordered lines through locations. The path layer works **with the marker layer**:
`bubbleLayer` (on by default) renders the points and `pathLayer` draws the lines that
connect them — enable `pathLayer` and leave `bubbleLayer.show` on. **Requires a `PathID`
grouping** (one line per value) and normally a `PointOrder` grouping to sequence points.
Provide the point locations with the **required `Category`** role. `Category` is required
by `azureMap`: authoring with only `X`/`Y` coordinates and no `Category` fails validation
with `PBIR_ROLE_REQUIRED_MISSING`, and binding `Category` together with `X`/`Y` makes the
visual error — so bind `Category` (not `X`/`Y`) for path points. Add the roles to
`queryState`:

```json
"Category": { "projections": [ { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Routes" } }, "Property": "StopName" } }, "queryRef": "Routes.StopName", "nativeQueryRef": "StopName", "active": true } ] },
"PathID": { "projections": [ { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Routes" } }, "Property": "RouteId" } }, "queryRef": "Routes.RouteId", "nativeQueryRef": "RouteId", "active": true } ] },
"PointOrder": { "projections": [ { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Routes" } }, "Property": "Stop" } }, "queryRef": "Routes.Stop", "nativeQueryRef": "Stop" } ] }
```

```json
"pathLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#D13438'" } } } } },
    "strokeWidth": { "expr": { "Literal": { "Value": "3L" } } }
  } }
]
```

### Reference layer — GeoJSON overlay (`referenceLayer`)

Overlays an external boundary file (GeoJSON, KML, WKT, or a zipped shapefile) that is
independent of the visual's data roles. Set `datasourceType` to `url` with the file URL
in `referenceLayerUrl`; style polygons/lines/bubbles with the matching `*Color` /
`*Width` properties.

```json
"referenceLayer": [
  { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "datasourceType": { "expr": { "Literal": { "Value": "'url'" } } },
    "referenceLayerUrl": { "expr": { "Literal": { "Value": "'https://raw.githubusercontent.com/Azure-Samples/AzureMapsCodeSamples/main/Static/data/geojson/US_States_500k.json'" } } },
    "polygonFillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#88CCEE'" } } } } },
    "polygonStrokeColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#33445A'" } } } } }
  } }
]
```

## Add Data-Driven Formatting

After configuring the roles, target layer, magnitude, and static appearance,
follow Conditional formatting — Azure Maps layers (see `conditional-formatting.md`, section `azure-maps-layers`)
to add data-driven icon-marker fill, marker rotation, 3D-column fill, or
choropleth fill.
