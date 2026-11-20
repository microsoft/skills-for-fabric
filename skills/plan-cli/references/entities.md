# Plan Definition Parts and Identity

Get Plan Definition returns an envelope whose `definition.parts` hold the saved Plan configuration. Every part used by this skill must have `payloadType: InlineBase64`; decode its payload as UTF-8 JSON and index it by exact path.

## Required root

`definition.json` is the root instance document. Its `$schema` URL describes the shape only. Use the returned fields for the actual Plan:

- `workloadItemName`
- `sheets[]`
- each sheet's `recordGuid`, `displayName`, `sheetType`, and `workloadItemEntityVisuals[]`
- each visual reference's `visualId` and `visualType`

Reject duplicate part paths and duplicate sheet or visual identifiers. Preserve identifier strings exactly.

## Path mapping

For a sheet `recordGuid` of `{sheetId}` and a visual reference `visualId` of `{visualId}`, map only matching returned paths. Part names and required flags follow the [Plan definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/plan-definition) article:

| Scope | Path | Required |
|---|---|---|
| Plan | `definition.json`, `planProperties.json`, `.platform` | yes |
| Plan | `connectedPlanning/infobridge.json` (Connected Planning), `cube/cube.json` (cube-based writeback) | when used |
| Sheet | `sheets/{sheetId}/sheet.json` | yes |
| Sheet | `sheets/{sheetId}/commentSettings.json` | for PLANNING and POWERTABLE sheets |
| Planning visual | `dataInput.json`, `properties.json` | yes |
| Planning visual | `writeback.json`, `insertRows.json`, `scenarios.json`, `modelTemplate.json` | no |
| PowerTable visual | `columnConfigs.json`, `properties.json`, `source.json`, `sourceSettings.json` | yes |
| PowerTable visual | `approvals.json`, `automations.json`, `forms.json` | no |
| Intelligence visual | `properties.json` | yes |

Visual files live under `sheets/{sheetId}/visuals/{visualId}/`. `sheetType` is one of `PLANNING`, `REPORTING`, `POWERTABLE`, `INFOBRIDGE`, `SUPER_FILTER`, `BI_REPORTING`, `BI_ADHOC_ANALYSIS` or `BI_DASHBOARD`.

Do not associate a part by array order, display name, substring, or a copied identifier from another Plan. Extra parts under a declared sheet or visual are preserved and listed in `partPaths`, not silently discarded. A visual part whose sheet and visual are not declared in `definition.json` is rejected; report it rather than guessing its owner.

## Identity rules

- Workspace ID and Plan ID come from public Fabric item resolution.
- Sheet and visual definition IDs come from the decoded root and matching paths.
- Source/model/connection identifiers come only from their decoded source/configuration fields.

## Completeness and state

Missing and empty are different. A returned empty `sheets` array is a saved empty state only when the root and envelope are valid and complete. A missing root, malformed part, duplicate path, unsupported payload type, or incomplete LRO result is a failed definition read.

Definitions may not contain browser-only filter, drill, selection, or unsaved state. Never claim exact current-canvas reproduction when those inputs are absent.

## Offline validation

The bundled helper validates strict base64/JSON decoding, path uniqueness, and sheet/visual path identity. Run it from the skill directory with Python 3.9 or later:

```bash
python3 scripts/plan_definition.py path/to/get-definition-envelope.json
```

It performs no authentication or network calls.
