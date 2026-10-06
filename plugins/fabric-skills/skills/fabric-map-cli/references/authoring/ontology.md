# Ontology source adapter

For authoring, read this after `../authoring.md` when a layer uses Ontology
entities. For capability questions, read the summary only; no source lookup is
needed. The shared reference owns Map lifecycle, encoding, and readback.

## Capabilities and follow-up inputs

Ontology-backed Map layers are in preview. They render entity instances using
numeric latitude/longitude or a supported geometry property. Points, lines,
and polygons depend on the entity's actual spatial data; coordinates alone do
not define routes or areas. These are entity-backed spatial layers, not an
imagery connector or permission to traverse all relationships.

The documented result limit is 100,000 features returned by the selected
entity. A small sample does not establish that the full result meets the limit.
Check the current official Map/Ontology documentation for changed limits and
availability; schema publication alone does not prove tenant availability.
Map compatibility depends on the Ontology's generation and definition format,
not just the selected Map schema. Verify the source-specific binding contract.

Start with the Ontology name/reference and what the user wants to show.
Ask for its workspace only when unresolved from the supplied reference or
source context. Discover generation, entity IDs, and spatial bindings from
metadata; do not request these as setup inputs. Resolve entities and mappings
from the user's goal when unambiguous; otherwise offer the relevant named
choices.

## Scope and source validation

Reference an existing Ontology; do not create entities, change bindings, or
modify underlying Lakehouse/Eventhouse data as a side effect of Map authoring.

1. Resolve the workspace and exact Ontology display name using paginated
   `GET /v1/workspaces/{workspaceId}/ontologies`; verify a supplied ID with
   `GET /v1/workspaces/{workspaceId}/ontologies/{ontologyId}`.
2. Inspect the entity types and bindings with the read-only
   `POST /v1/workspaces/{workspaceId}/ontologies/{ontologyId}/getDefinition`.
   Use the shared authentication, telemetry, LRO, and UTF-8/Base64 procedures.
   This read requires Ontology read/write permission and `Item.ReadWrite.All`;
   report permission or encrypted-label restrictions rather than guessing.
3. Match `properties.generation` and the returned parts to the corresponding
   Ontology definition documentation. Generation 1 JSON identifies entities in
   `EntityTypes/{ID}/definition.json`; preserve those non-UUID identifiers as
   exact strings, including large integer IDs. Generation 2 uses TMDL and
   requires its own verified Map binding contract. Do not infer entity IDs
   from names or apply one format's parser to another. If the format or binding
   is unsupported or inconsistent, report the compatibility gap and stop.
4. Resolve the entity and spatial mapping from the inspected definition. Use a
   unique compatible match to the user's goal without asking for its IDs or
   property names. If several entities or mappings fit, ask only which to use.
   Verify numeric coordinates or a supported geometry property and their
   bindings; names alone do not establish spatial semantics, and a display label
   is not necessarily the field identifier consumed by the Map. If a binding or
   required property cannot be verified, stop before mutation and explain the
   blocker.
5. Definition metadata is sufficient for normal source resolution. When the
   user requests data validation, use the owning source workflow and a
   documented read-only interface compatible with that source's format.
   Check representative spatial values and the full result limit; report
   unverified results separately. Do not provision or modify source resources
   to work around a validation failure without separate authorization.

## Definition fragments and compatibility

Use the schema selected by the shared workflow. Inspect its data-source
alternatives and choose the compatible nondeprecated item-reference branch.
The fragment below applies when that schema provides the `datasourceId` plus
`item` model; it is not permission to force this branch into another schema.
Verify `ontologyEntityId` and every other field against the selected contract.

Data source:

```json
{
  "datasourceId": "ontology-source",
  "item": {
    "workspaceId": "<workspace-guid>",
    "itemId": "<ontology-guid>"
  }
}
```

Layer source template:

```json
{
  "id": "<stable-layer-source-id>",
  "name": "<source name>",
  "type": "ontology",
  "datasourceId": "ontology-source",
  "ontologyEntityId": "<resolved-entity-type-id>"
}
```

`ontology` is the layer-source discriminator. Where the schema permits any
string for `type`, schema validation alone cannot establish source support.
Verify the discriminator and entity binding against the current Map contract
for the resolved Ontology format; do not derive them from display names.

When the selected schema instead requires a legacy workspace-item branch,
construct only the fields required by that branch, including
`itemType: "Ontology"` when specified, and use its corresponding layer link.
Do not combine legacy fields with the newer data-source object, infer a legacy
shape from this example, or silently migrate an existing definition.
For a variable-backed item, also follow [variable references](variables.md).

Set `layerSettings[].sourceId` to the layer source ID and use
`options.type: "vector"`. Set the verified `latitudeColumnName` and
`longitudeColumnName`, or `geometryColumnName`, as accepted by the Map schema.
Use geometry-compatible styling from the shared reference. Add a refresh
interval only when requested and supported; do not synthesize a KQL part for
an Ontology layer.

## Readback

After the shared terminal write, verify the Ontology reference, entity ID,
layer-source type and links, spatial mappings, and requested styling/refresh.
For variable-backed sources, also verify that the expression was preserved.
Preserve all unrelated definition parts and settings. Readback proves Map
configuration persistence, not successful Ontology evaluation or rendering.

## References

- [Ontology Map capabilities](https://learn.microsoft.com/fabric/real-time-intelligence/map/about-ontology-layers)
- [Add Ontology layers and limits](https://learn.microsoft.com/fabric/real-time-intelligence/map/add-ontology-layer)
- [Ontology REST operations](https://learn.microsoft.com/rest/api/fabric/ontology/items)
- [Get Ontology definition](https://learn.microsoft.com/rest/api/fabric/ontology/items/get-ontology-definition)
- [Generation 1 JSON definition and entity IDs](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/ontology-old-definition)
- [Generation 2 TMDL definition](https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/ontology-definition)
- [Map schema versions](https://github.com/microsoft/json-schemas/tree/main/fabric/item/map/definition)
