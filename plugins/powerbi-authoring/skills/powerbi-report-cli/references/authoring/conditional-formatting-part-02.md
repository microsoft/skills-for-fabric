# Conditional Formatting Patterns - Part 2

## Contents

  - [Chart target capability matrix](#chart-target-capability-matrix)
  - [Card](#card)
  - [KPI](#kpi)
  - [Azure Maps layers](#azure-maps-layers)


Continuation of `conditional-formatting.md`. Open this file directly from the skill reference index.

### Chart target capability matrix

Use this matrix to choose the formatting object and property. Confirm the
property against the installed CLI before authoring:

```bash
powerbi-report-author formatting describe-object <visualType> <objectName>
```

| Visual family | Direct conditional-color target | Gradient | Rules | Field value | Notes |
|---------------|---------------------------------|----------|-------|-------------|-------|
| Bar/column, stacked, clustered, 100% stacked, ribbon | `dataPoint.fill` | Yes | Yes | Yes | Controls bar/column/ribbon category or series color. |
| Full line/area series (non-combo) | `dataPoint.fill` | Yes | Yes | Yes | Historical PBIR path for the full line path and per-series line color. |
| Combo-chart line series | `dataPoint.fill` | No* | No* | No* | Use static series styling. Category-level conditional expressions resolve one color for the full line series. |
| Segments within one non-combo line/area series | `lineStyles.strokeColor` | Yes | Yes | Yes | Per-category segment color only. A categorical legend disables segment formatting. |
| Line/area markers (single-series non-combo) | `dataPoint.fill` | Yes | Yes | Yes | Use the Category-role selector and omit `lineStyles.markerColor`. Set `lineStyles.strokeColor` separately when the line must remain static. |
| Combo-chart markers | `lineStyles.markerColor` | No* | No* | No* | Use static series styling. Category-level conditional expressions resolve one marker color for the full series. |
| Scatter/bubble | `dataPoint.fill` | Yes | Yes | Yes | Controls bubble fill; marker border remains a separate static/inherited property. |
| Pie/donut | `dataPoint.fill` | Yes | Yes | Yes | Controls slice and corresponding legend-symbol color. |
| Treemap | `dataPoint.fill` | Yes | Yes | Yes | Controls rectangle/category color. |
| Funnel | `dataPoint.fill` | Yes | Yes | Yes | Controls funnel stage color. |
| Map, filled map, shape map | `dataPoint.fill` | Yes | Yes | Yes | Controls bubble, region, or shape fill color. |
| Chart data labels | `labels.color` | Yes | Yes | Yes | Available on bar/column, line/area, combo, pie/donut, and treemap families. |
| Scatter category labels | `categoryLabels.color` | No* | No* | No* | Supports one holistic static label color, not per-bubble or per-category conditional colors. |

*`No*` means value-driven conditional formatting is unsupported. Use static
styling instead; see the combo limitation below and the scatter-label row note.

> **Metadata boundary:** a property having CLI type `fill` proves the PBIR
> property path and value shape, but not that the Power BI UI offers the
> conditional-formatting **fx** button for that property. Use this matrix for
> the supported chart targets documented by Power BI; do not generalize it to
> other `fill` properties such as axes, reference lines, or visual-container
> colors.

> **Combo limitation:** treat Gradient, Rules, and Field Value as unsupported
> for combo lines and markers. Use static per-series styling instead.

> **Line-path routing:** use `dataPoint.fill` for a full line path and
> `lineStyles.strokeColor` for per-category segmented line coloring. Do not
> move a full-series line rule to `lineStyles.strokeColor`.

### Card

- Rule-based callout and label font colors use
  the `Conditional.Cases[]` expression structure from
  Type 2: Rules-Based Formatting.
- Constant callout and label font colors use a `Literal` color expression.
- Both `value.fontColor` and `label.fontColor` are `ConstantOrRule`; either
  property can use a constant or a rule.
- Both properties require `selector: { "id": "default" }`. Omitting it can
  validate but silently leave the card unchanged.
- These properties do not accept gradients; do not use `FillRule` or
  `linearGradient*`.

### KPI

- Rule-based indicator, goal, distance, and date font colors use
  the `Conditional.Cases[]` expression structure from
  Type 2: Rules-Based Formatting.
- Constant font colors use a `Literal` color expression.

Each supported property is `ConstantOrRule` and can independently use a
constant or a rule:

| Property | Use when |
|----------|----------|
| `indicator.fontColor` | Coloring the main KPI indicator value when no `Goal` projection is bound. |
| `goals.goalFontColor` | Coloring the displayed goal/target text when a `Goal` projection is bound and `goals.showGoal` is enabled. The configured label comes from `goals.goalText`. |
| `goals.distanceFontColor` | Coloring the distance-to-goal text when a `Goal` projection is bound and `goals.showDistance` is enabled. `goals.distanceLabel` chooses `Value`, `Percent`, or `Value, percent`. |
| `lastDate.lastDateFontColor` | Coloring the latest trend-axis date shown below the KPI when `lastDate.show` is enabled. Use it when the KPI has a `TrendLine` date/time field. |

- KPI formatting objects do not use a selector.
- These properties do not accept gradients; do not use `FillRule` or
  `linearGradient*`.
- `indicator.fontColor` is available only when the KPI has no `Goal`
  projection. When a goal is bound, use the KPI status behavior and supported
  `goals` color properties instead.

### Azure Maps layers

The Azure Maps visual (`visualType: "azureMap"`) supports conditional formatting
on **icon-marker fill color**, **3D-column fill color**, **choropleth fill
color**, and **marker rotation**. Image markers do not support fill-color
conditional formatting; use rotation for data-driven image-marker formatting.
Separately, **measure-driven magnitude** (marker size, 3D-column height, heat-map
weight) is driven only by the **Size** measure role. Marker border, heat-map
color ramp, baseline intensity, radius, and transparency have no conditional
formatting (no ƒx); author them as static literals.

Apply conditional fill color with the object for the target layer:

| Layer | Fill-CF object | Static color property |
|---|---|---|
| Icon marker | `bubbleLayer.fillColor` | `bubbleLayer.fillColor` |
| Image marker | Not supported | Image content from `bubbleLayer.imageData` / `bubbleLayer.imageUrl` |
| 3D column | `dataPoint.fill` | `barChart.defaultColor` (static-only) |
| Choropleth (filled map) | `dataPoint.fill` | `filledMap.defaultColor` (static-only) |

Set `bubbleLayer.markerType` to `"icon"` before authoring marker fill CF. Put
the CF expression on `bubbleLayer.fillColor` in a wildcard-selected
`bubbleLayer` entry. Keep `show`, `sizeByValue`, radius, marker shape, and other
static marker properties in a separate unselected `bubbleLayer` entry.

Do not add marker fill CF when `markerType` is `"image"`; Desktop disables the
entire marker Fill group for image markers.

Preserve `dataPoint.fill` when editing an older Desktop-authored marker rule.
Current custom-marker builds read that property as a backward-compatibility
fallback. Do not migrate or dual-write the rule unless the target Desktop
build has been tested with that shape.

Author 3D-column and choropleth conditional fill only on `dataPoint.fill`.
Author their static colors on `barChart.defaultColor` and
`filledMap.defaultColor`.

Supply the fill color as:

- **Field value** (a measure/column returning a color) →
  Type 6: Field-Driven Color
- **Rules** (`Conditional.Cases[]`) →
  Type 2: Rules-Based Formatting
- **Gradient** (`FillRule` / `linearGradient2|3`) →
  Type 1: Color Gradient (FillRule)

**Summarization (input field aggregation)** — the Rules/Gradient `Input` (or
`Comparison.Left`) and a Field-value column input must resolve to one scalar per
location: reference a **measure** directly, or wrap a **column** in an
`Aggregation` expression whose `Function` is the format pane's *Summarization*
dropdown. See
expressions.md § Aggregation Expression (see `expressions.md`, section `aggregation-expression`)
for the JSON shape and the full `Function` enum.

The choropleth (filled map) layer is **mutually exclusive with the `Size` role**
— while any field is bound to `Size` the Filled map layer is disabled and will
not render. Leave the `Size` projection empty to use the choropleth layer.

**Marker rotation** — bind `bubbleLayer.markerRotation` to a field producing
the angle in degrees under the wildcard selector. Use a direct `Measure`
expression for a measure. Wrap a column in `Aggregation` using the
summarization selected in Desktop; do not emit a raw `Column`. Keep the
rotation entry separate from the unselected static marker entry. The rotation
CF dialog supports only **Field value**; do not use a `FillRule` or
`Conditional` expression. Rotation renders only on directional icon/image
markers, not symmetric dots.

**Selector** — select fill CF and rotation with
`{ "data": [ { "dataViewWildcard": { "matchingOption": 1 } } ] }` (format pane
*Apply settings to → Locations: All*). Do not use a role selector
(`{ "roles": ["Category"] }`); it does not round-trip.

Use the same wildcard selector for an all-series rule when a `Legend` (Series)
field is bound and the target Desktop build exposes the all-series `fx`
control. If the target build does not expose that control, remove the Legend
for value-driven fill or author static per-series `metadata` colors (see
color-strategy.md § Per-Series Colors (see `color-strategy.md`, section `pattern-per-series-colors`)).

**Conditional-formatting support by layer**

Each row is a CF-capable property and the CF styles it accepts. Non-CF properties
(Size-role magnitude and static-only) are not listed here — author them in
map.md § Layers (see `map.md`, section `layers`).

| Layer | CF property | Target object | Field value | Rules | Gradient |
|---|---|---|:--:|:--:|:--:|
| Icon marker | Fill color | `bubbleLayer.fillColor` | ✅ | ✅ | ✅ |
| Icon or image marker | Rotation | `bubbleLayer.markerRotation` | ✅ | — | — |
| Image marker | Fill color | Not supported | — | — | — |
| 3D column | Column fill color | `dataPoint.fill` | ✅ | ✅ | ✅ |
| Choropleth (filled map) | Region fill color | `dataPoint.fill` *(requires empty `Size` role)* | ✅ | ✅ | ✅ |

**Magnitude and static properties are not conditional formatting.** Marker size,
3D-column height, and heat-map intensity are driven by the **`Size`** measure role
(with the `bubbleLayer.sizeByValue` / `barChart.heightByValue` /
`heatMapLayer.heatMapUseSize` toggles); marker shape/border, heat-map radius,
transparency, and the heat-map color ramp are static `Literal` values. None of
these accept `ƒx` (`Conditional` / `FillRule`) — author them in
map.md § Layers (see `map.md`, section `layers`).

**Example — gradient fill on an icon marker**:

```json
"objects": {
  "bubbleLayer": [
    {
      "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "markerType": { "expr": { "Literal": { "Value": "'icon'" } } }
      }
    },
    {
      "properties": {
        "fillColor": {
          "solid": {
            "color": {
              "expr": {
                "FillRule": {
                  "Input": {
                    "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Revenue YoY %" }
                  },
                  "FillRule": {
                    "linearGradient2": {
                      "min": { "color": { "Literal": { "Value": "'#D13438'" } } },
                      "max": { "color": { "Literal": { "Value": "'#107C10'" } } },
                      "nullColoringStrategy": { "strategy": { "Literal": { "Value": "'asZero'" } } }
                    }
                  }
                }
              }
            }
          }
        }
      },
      "selector": { "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }
    }
  ]
}
```

Swap the `FillRule` input for a `Conditional.Cases[]` block (Type 2)
for rules, or a field-value measure/column (Type 6)
for field-driven color. For an enabled 3D-column or choropleth layer, put the
same expression on `dataPoint.fill` instead. Do not put 3D-column or
choropleth CF on `barChart.defaultColor` or `filledMap.defaultColor`; use those
properties for static color only.

```json
"dataPoint": [
  {
    "properties": {
      "fill": {
        "solid": {
          "color": {
            "expr": {
              "FillRule": {
                "Input": {
                  "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Revenue YoY %" }
                },
                "FillRule": {
                  "linearGradient2": {
                    "min": { "color": { "Literal": { "Value": "'#D13438'" } } },
                    "max": { "color": { "Literal": { "Value": "'#107C10'" } } },
                    "nullColoringStrategy": { "strategy": { "Literal": { "Value": "'asZero'" } } }
                  }
                }
              }
            }
          }
        }
      }
    },
    "selector": { "data": [{ "dataViewWildcard": { "matchingOption": 1 } }] }
  }
]
```

**Marker rotation** is Field-only on a separate wildcard-selected `bubbleLayer`
entry. Use a direct measure:

```json
"markerRotation": { "expr": { "Measure": { "Expression": { "SourceRef": { "Entity": "Metrics" } }, "Property": "Heading °" } } }
```

For a column, use the summarization selected in Desktop:

```json
"markerRotation": {
  "expr": {
    "Aggregation": {
      "Expression": {
        "Column": {
          "Expression": { "SourceRef": { "Entity": "Routes" } },
          "Property": "Heading"
        }
      },
      "Function": 0
    }
  }
}
```
