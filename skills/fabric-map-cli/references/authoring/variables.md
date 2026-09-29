# Variable-backed source references

For authoring, read this after `../authoring.md` and alongside the adapter for
the resolved source. For capability questions, read the summary without
listing libraries or resolving variable values.

## Capabilities and follow-up inputs

Some published Map schemas support variable references in `dataSources[].item`
and `dataSources[].connection` through reference-or-variable alternatives such
as `ItemReferenceOrVar` and `ConnectionReferenceOrVar`. Confirm those branches
in the operation's selected schema instead of assuming support from a version
mentioned in this guide. Variables parameterize an existing supported item or
connection; they are not a new geometry provider or `type: "variable"` layer.
They do not make arbitrary Fabric items or connectors valid Map inputs.

Start with a variable reference or the library and variable name in the Map's
workspace; do not ask for both forms. Discover the declared type, current active
value set, and effective target from the library rather than requesting them
from the user. If only the library is identified, offer compatible variable
names without exposing their values. Reuse the resolved target in its source
adapter; do not ask the user to identify the source again. Ask for a file, query,
entity, or imagery resource only when the user's goal and scoped discovery
leave that selection unresolved. Rendering and limits come from that adapter.

Use the selected Map schema and its referenced schemas as the contract.
Schema support does not guarantee service rollout, variable permissions, or
runtime resolution. Do not claim universal Map availability from the general
Variable Library supported-items list. If the service rejects this capability,
report that failure; do not silently replace the variable with a literal ID.

## Resolve and validate

1. Check the operation's selected schema for variable-backed item/connection
   branches. Fetch its linked reference schemas once for this operation; select
   the matching branch after discovering the variable type. If an existing
   Map's schema cannot express the request, stop and ask whether migration is
   wanted; do not upgrade implicitly.
2. Resolve the existing library by exact name with paginated
   `GET /v1/workspaces/{workspaceId}/variableLibraries`. Read its metadata with
   `GET /v1/workspaces/{workspaceId}/variableLibraries/{variableLibraryId}` and
   its definition using the read-only
   `POST /v1/workspaces/{workspaceId}/variableLibraries/{variableLibraryId}/getDefinition`.
   Apply shared authentication, telemetry, LRO, and part-decoding procedures.
   Observe the endpoint's documented permissions and report denied access.
3. Match the variable in `variables.json`. Read
   `properties.activeValueSetName` from library metadata and resolve its
   override from the corresponding value-set definition; otherwise use the
   variable's documented default. Do not infer the active set from file order,
   pick an arbitrary set, or treat a missing/unreadable set as the default.
   Use the current active set without asking the user to select or confirm it;
   other value sets matter only when the request explicitly includes them.
4. Verify the declared variable type and effective value: an item reference
   resolves to `workspaceId` plus `itemId`; a connection reference resolves to
   `connectionId`. A String variable containing a GUID is not an item or
   connection reference. Follow the library's published type contract rather
   than guessing type-name casing, and verify that the selected Map reference
   branch accepts the discovered type.
5. Verify the resolved target and required access through its source adapter.
   For item references, check the actual item type; for connections, check the
   supported provider and resource. Validate the requested file, query, entity,
   and spatial mappings against that target. For multiple deployment contexts,
   validate each requested context; one active value set proves nothing about
   uninspected sets.

If resolution, type, access, or required source validation fails, report the
specific failure and stop before changing the Map. Resolve only the requested
variables; do not print unrelated library values or credentials. Creating or
editing libraries, variables, connections, or active value sets is separate
administration and is not authorized by a Map source change.

## Definition fragments

The examples use the documented `$(/**/LibraryName/VariableName)` expression
form. Replace names with verified references; do not invent escaping rules for
unusual names. Preserve expressions as literal JSON strings: PowerShell
double-quoted strings evaluate `$()`, so use single-quoted strings or a
single-quoted here-string when assembling these values.

Item reference:

```json
{
  "datasourceId": "item-source",
  "item": "$(/**/MapSources/SourceItem)"
}
```

Connection reference:

```json
{
  "datasourceId": "imagery-source",
  "connection": "$(/**/MapSources/ImageryConnection)"
}
```

Each object is a `dataSources` entry. Use either `item` or `connection`, not
both; do not add legacy `itemType`, `itemId`, or `connectionId` to that object.
Keep each `datasourceId` unique and stable.

For a variable-backed layer, retain the underlying adapter's source type and
source-specific properties, but replace its direct `itemId`/`connectionId`
link with `datasourceId` matching the corresponding entry. For example, a
Lakehouse GeoJSON layer can use:

```json
{
  "id": "<stable-layer-source-id>",
  "name": "<source name>",
  "type": "geojson",
  "datasourceId": "item-source",
  "relativePath": "Files/path/data.geojson"
}
```

Keep `layerSettings[].sourceId` linked to the layer-source ID, not the
`datasourceId`. Keep any KQL part associated with the unchanged layer-source
ID; preserve Ontology entity IDs and connection resource IDs. Do not replace
these source-specific properties with expressions unless the selected schema
explicitly permits it.

Validate the complete Map against the pinned schema and referenced schemas
with format checking. The custom `varRef` annotation and expression pattern
do not make a generic JSON Schema validator resolve variables or enforce
their runtime types; the semantic checks above are still required.

## Validation boundary

The checks above establish the declared reference and its effective target.
Additional runtime validation requires the user's request and the owning
consumer or source workflow; it does not authorize resource provisioning or
library changes. Use that workflow's documented interfaces and result types.
Keep reference resolution, source access, Map persistence, and rendering as
separate conclusions. Evidence from one consumer, reference type, or value set
does not establish support in another.

## Readback and consumption

After the shared Map write, compare the persisted expressions, `datasourceId`
links, and source-specific properties with the intended definition. Recheck
the library's active set and the relevant effective values; if they changed
during the operation, report the mismatch rather than claiming a stable target.
Do not freeze an expression into its currently resolved IDs.

In consumption mode, preserve expressions and distinguish declared references,
verified targets, and unverified resolution. Never change the library or Map
to test a reference. Successful persistence is not proof of runtime rendering.

## References

- [Map schema versions](https://github.com/microsoft/json-schemas/tree/main/fabric/item/map/definition)
- [Item reference schema](https://developer.microsoft.com/json-schemas/fabric/common/itemReference/1.0.0/schema.json)
- [Connection reference schema](https://developer.microsoft.com/json-schemas/fabric/common/connectionReference/1.0.0/schema.json)
- [Variable expression schema](https://developer.microsoft.com/json-schemas/fabric/common/variableReference/1.0.0/schema.json)
- [Variable Library overview and value sets](https://learn.microsoft.com/en-us/fabric/cicd/variable-library/variable-library-overview)
- [Item reference variables](https://learn.microsoft.com/en-us/fabric/cicd/variable-library/item-reference-variable-type)
- [Connection reference variables](https://learn.microsoft.com/en-us/fabric/cicd/variable-library/connection-reference-variable-type)
- [Variable Library APIs](https://learn.microsoft.com/en-us/fabric/cicd/variable-library/automate-variable-library)
- [Variable Library definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/variable-library-definition)
