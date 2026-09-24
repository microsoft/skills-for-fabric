# Field Parameters (report-side pattern)

## Contents

- [Workflow](#workflow)
- [Recognizing an existing field parameter](#recognizing-an-existing-field-parameter)
- [Ensure a slicer and a visual exist on the page](#ensure-a-slicer-and-a-visual-exist-on-the-page)
- [Target-visual projection encoding](#target-visual-projection-encoding)


Read this when a request implies switching which field a visual uses through a
slicer — a "metric selector", "dynamic view", "view by" chart, or "let the user
pick what this visual shows". A field parameter is a dynamic field selector:
one slicer plus one visual can provide many views.

This skill owns the **report-side** of the pattern: wiring the slicer and
target visual in PBIR. The field-parameter table itself is a **semantic-model
object** — this skill never edits TMDL or `.SemanticModel` files directly.
Any model-side mutation (creating, editing, reordering, renaming, or deleting a
field parameter) is out of scope — delegate to the `semantic-model-authoring`
skill if available, otherwise try other model-authoring skills. If no
model-authoring capability is available, prompt the user. Reading TMDL directly
is acceptable only for **inspection** (recognizing an existing parameter), never
for mutating one.

## Workflow

1. Recognize that the request needs a field parameter.
2. Inspect the model for a matching parameter — read TMDL directly (read-only).
   See [Recognizing an existing field parameter](#recognizing-an-existing-field-parameter).
3. If a matching parameter exists, use its visible display column, then check
   the target page for the two pieces the pattern requires — a slicer bound to
   the parameter and a visual that consumes it. See
   [Ensure a slicer and a visual exist on the page](#ensure-a-slicer-and-a-visual-exist-on-the-page).
   Skip to step 5.
4. If the parameter is missing (or must be edited/deleted), delegate the
   model-side change to the `semantic-model-authoring` skill if available;
   otherwise try other model-authoring skills. If no model-authoring capability
   is available, stop and prompt the user that the model-side changes cannot be
   completed, then confirm before continuing. Do not silently fall back to a
   worse (static) visual, and do not hand-edit TMDL.
5. Build the slicer and target visual, validate PBIR, follow the host-specific
   workflow in preview.md (see `preview.md`), and review the rendered result.

## Recognizing an existing field parameter

Look for:

- A hidden column carrying `extendedProperty ParameterMetadata` with
  `"kind": 2`.
- A calculated partition whose source contains
  `("Name", NAMEOF('Table'[Field]), Order)` tuples.

Bind the visible display column, never the hidden `*Fields` or `*Order`
columns. The slicer should use `visualType: slicer`, `data.mode: "Basic"`, and
the visible parameter column in `Values`. Do not add
`drillFilterOtherVisuals` to the slicer.

## Ensure a slicer and a visual exist on the page

A field parameter only works as a "pick what this shows" control when the page
carries **both** halves of the pattern: a slicer bound to the parameter's
visible display column, and a target visual that consumes the parameter. Any
request touching an **existing** field parameter (use it, point it at a page,
"add the metric selector", "wire up the selector", etc.) must first inspect the
target page and confirm both are present.

1. Inspect the page's visuals. Identify:
   - A **slicer** whose `Values` projection is the parameter's visible display
     column.
   - A **target visual** that projects the parameter's underlying fields and
     carries the sibling `fieldParameters` array
     (see [Target-visual projection encoding](#target-visual-projection-encoding)).
2. If **either** is missing, add it so the page ends with both:
   - Missing slicer → add a `slicer` visual per
     [Recognizing an existing field parameter](#recognizing-an-existing-field-parameter).
   - Missing target visual → add a visual that consumes the parameter.
3. If **both** already exist, do not duplicate them — reuse or adjust in place.
4. Validate PBIR, follow the host-specific workflow in
   preview.md (see `preview.md`), and review the rendered result.

Never leave the page with only one half (a slicer with nothing to drive, or a
target visual with no way to switch it).

## Target-visual projection encoding

The target visual must not project the field-parameter display column directly.
Project every underlying measure or column selected by the parameter in the
correct role, in parameter order, and add a sibling `fieldParameters` array:

```json
"fieldParameters": [
  {
    "parameterExpr": {
      "Column": {
        "Expression": { "SourceRef": { "Entity": "Travel Analysis" } },
        "Property": "Parameter"
      }
    },
    "index": 0,
    "length": 4
  }
]
```

`parameterExpr` is the visible parameter column. `index` is the starting
projection offset and `length` is the number of underlying fields represented.
The projection set and order must match the parameter's `NAMEOF(...)` tuples.

Bad field references can pass `validate` but render an error icon, so always
complete the selected-host preview and screenshot review loop in
preview.md (see `preview.md`).
