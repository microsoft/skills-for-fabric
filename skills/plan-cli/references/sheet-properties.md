# Saved Sheet and Visual Configuration

Read saved sheet and visual configuration only from decoded Get Plan Definition parts.

## Sheet inspection

Resolve the requested sheet uniquely in `definition.json`, then inspect `sheets/{sheetId}/sheet.json`. Preserve the returned object rather than projecting unknown fields away. Relevant configuration can include canvas style, variables, filter pane state, assignments, groups, and source-visual metadata.

An absent matching part is missing configuration, not an empty sheet. Do not call a runtime properties endpoint to fill the gap.

## Visual inspection

Resolve each visual through the selected sheet's `workloadItemEntityVisuals`, then inspect matching parts under:

`sheets/{sheetId}/visuals/{visualId}/`

Every visual has `properties.json`. Planning visuals add `dataInput.json`; PowerTable visuals add `columnConfigs.json`, `source.json` and `sourceSettings.json` (see the path table in the Plan definition parts reference). Preserve unsupported or unfamiliar parts and state that their interpretation is unknown.

A Planning `properties.json` can expose a direct `properties` bag, a `visuals`
map keyed by visual UUID, or both. Resolve only the exact selected UUID. If
direct and mapped bags conflict, or the selected key/configuration is absent,
inventory may report the saved absence but a data query must stop.

### Chart type for narrative headings

Retain the selected visual's chart-type provenance with its title and fields.
For a supported chart, inspect its resolved `properties.chartType` and, when
present, `properties.visualState.chartType`. They must agree before claiming
that type. `COLUMN_VERTICAL` can be described as "Vertical column chart";
other labels require their verified saved type, not a guess from the data.
Do not infer stacked/overlapped/combo variants from a generic family alone.

`ANALYTICS_PLUS` is a visual family, and a numeric `visualType` is not a
human-readable chart type. A Year field does not imply a line chart.
If chart metadata is absent, unrecognized or contradictory, retain the visual's
field/title label and state "Chart type unavailable." Do not query an unrelated
runtime inventory or relabel another visual to fill the gap. Missing display
metadata alone need not block a query whose required data context is complete.

## Saved versus effective state

Definition properties are saved configuration. They are not:

- measured semantic values,
- proof of current model freshness,
- guaranteed browser-only selections or drill state,
- unsaved edits,
- proof that a filter is currently effective in the user's open browser session.

For a configuration request, report from the decoded definition and stop. For current values, use only a suitable registered read capability whose actual contract can supply the required data context and query-affecting inputs. Follow the Data fetcher procedure; if no suitable capability is available, ask for the data or report the missing capability.

Narrating supplied data or completed authorized read results does not require
a saved-definition projection. Retain the evidence's own source attribution,
filters and coverage. Saved properties cannot fill gaps in effective read
context or authorize an independent query. Configuration-only inspection may
still report other requested saved properties.

## Source handling

Classify a selected visual from its complete saved source/assignment data. Mixed, PowerTable, Infobridge, blend, unknown, or partially bound sources remain visible in the answer but are not silently removed to make a semantic-only query appear eligible.

Never infer a runtime numeric visual ID from a definition GUID.
