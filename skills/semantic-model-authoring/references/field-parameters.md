# Field Parameters Reference

A **field parameter** is a dynamic field selector: one slicer lets a report user
switch which column or measure a visual uses, so a single visual can provide
many views ("view by Product / Region / Customer", a metric selector, a "dynamic
view" chart). This reference covers the **model-side object** -- the
field-parameter calculated table -- which can be created, edited, renamed, or
deleted entirely from the model, independent of any report.

> **Scope.** The field-parameter calculated table is the whole job here and is
> fully self-contained model work. The matching report slicer and target visual
> are separate report (PBIR) work and out of scope for this skill.

## Contents

- [TMDL authoring](#tmdl-authoring)
- [Workflow: Create a field parameter](#workflow-create-a-field-parameter)
- [Workflow: Edit a field parameter](#workflow-edit-a-field-parameter)
- [Workflow: Rename or delete a field parameter](#workflow-rename-or-delete-a-field-parameter)
- [Common scenarios](#common-scenarios)
- [Must / Prefer / Avoid](#must--prefer--avoid)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

---

## TMDL authoring

When authoring or inspecting a field parameter as TMDL, load
the **Field parameter calculated tables** section of `tmdl-guidelines.md`.
That section is the single source of truth for the three-column table shape,
metadata, tuple expression, and escaping rules.

### Recognition

A table **is** a field parameter iff one column carries
`extendedProperty ParameterMetadata` whose JSON parses to `"kind": 2`. Read the
TMDL (or query the model) to detect an existing parameter before creating a
duplicate.

## Workflow: Create a field parameter

**When this applies:** User asks to create a metric selector / "view by" /
dynamic-view table, or explicitly asks to create a field parameter, and no
matching parameter exists yet.

Steps:

1. **Recognize & scope** - confirm the request is for a field-parameter table. Build the table here; the matching report slicer and visual, if any, are separate report work.
2. **Discover** - per [Recognition](#recognition), list existing tables and check for a field parameter that already fits (a column with `ParameterMetadata` `"kind": 2`). If one fits, switch to [Edit a field parameter](#workflow-edit-a-field-parameter) instead of creating a duplicate.
3. **Gather fields** - collect the ordered list of columns/measures and their slicer labels. If the fields are ambiguous, STOP and use `ask_user`.
4. **Build** per the skill's **Tool Selection Priority**:
   - **Tier 1 (MCP, preferred)** - use the `CreateFieldParameter` operation of `table_operations`. Follow the tool definition for the current request shape.
   - **Tier 2 (no MCP)** - hand-author the field parameter TMDL. Load `tmdl-guidelines.md` and, for PBIP, `pbip.md`; for a Fabric workspace source, round-trip via `getDefinition` -> edit -> `updateDefinition` as described in `semantic-model-rest-api.md`.
5. **Save & validate** - per the skill's **Saving Changes** and **Validation Checklist**. Confirm the visible label column, the hidden `Fields`/`Order` columns, and `ParameterMetadata` are all present. The visible label column is what a slicer binds to.

---

## Workflow: Edit a field parameter

**When this applies:** User asks to add, remove, reorder, or relabel the fields
an existing field parameter exposes.

> **No dedicated update operation.** The current MCP has **no**
> `UpdateFieldParameter`. The field set lives entirely in the calculated
> partition's tuple expression, so an edit is a **partition rewrite** — the three
> columns, visibility, sort-by, group-by, and `ParameterMetadata` are independent
> of the field set and must stay intact.

Steps:

1. **Locate the parameter** - per [Recognition](#recognition), find the table whose column carries `ParameterMetadata` `"kind": 2`. If the named table is not a field parameter, STOP and report it.
2. **Compute the full new set** - edits are **full replacement**, not merge: build the complete new ordered field list (omitting a field removes it). Re-derive `order` values zero-based and dense from the new field order.
3. **Rewrite the partition** per the skill's **Tool Selection Priority**:
   - **Tier 1 (MCP, preferred)** - use the `Update` operation of `partition_operations` to replace the calculated partition expression with the complete new tuple set. Follow the tool definition for the current request shape.
   - **Tier 2 (no MCP)** - rewrite the partition `source` in the field parameter TMDL; leave the three columns and `ParameterMetadata` untouched.
4. **Save & validate** - per the skill's **Saving Changes** and **Validation Checklist**. Confirm the columns and `ParameterMetadata` are unchanged and the new tuples materialize.

---

## Workflow: Rename or delete a field parameter

**When this applies:** User asks to rename a field-parameter table or its slicer
label, or to delete a field parameter entirely.

Steps:

1. **Locate the parameter** - per [Recognition](#recognition).
2. **Apply the change** (these do **not** touch the field set):
   - **Rename the table** - `table_operations`, `Operation: "Rename"` (Tier 1), or rename the `table` in TMDL (Tier 2).
   - **Rename the slicer label** - rename the visible label column with `column_operations` (Tier 1), or the visible `column` in TMDL (Tier 2).
   - **Delete** - `table_operations`, `Operation: "Delete"` (Tier 1), or remove the table's TMDL file (Tier 2).
3. **Save & validate** - per the skill's **Saving Changes** and **Validation Checklist**. Note that a rename changes the binding target, so any report slicer already bound to the old name will need to be repointed on the report side.

---

## Common scenarios

| Scenario | Approach |
| --- | --- |
| Create a "view by Product / Region / Customer" selector | [Create a field parameter](#workflow-create-a-field-parameter): one parameter over the dimension columns. |
| Create a metric selector (Sales / Profit / Margin) | [Create a field parameter](#workflow-create-a-field-parameter): one parameter over the measures. |
| Add a field to an existing parameter | [Edit a field parameter](#workflow-edit-a-field-parameter): rewrite the partition with the **full** new ordered set. |
| Reorder the slicer options | [Edit a field parameter](#workflow-edit-a-field-parameter): re-derive zero-based `order` from the new field order. |
| Delete an obsolete field parameter | [Rename or delete a field parameter](#workflow-rename-or-delete-a-field-parameter): `table_operations` Delete (Tier 1) or remove the TMDL file (Tier 2). |

---

## Must / Prefer / Avoid

### MUST

- Keep the three-column `[Value1]`/`[Value2]`/`[Value3]` shape and the
  `ParameterMetadata` `"kind": 2` extended property, or Desktop will not
  recognize the table as a field parameter.
- Use dense zero-based `order` values matching field order.
- Escape labels, table names, and object names in the tuple DAX.
- Treat edits as **full replacement** of the field set, not a merge.

### PREFER

- Tier 1 `table_operations` `CreateFieldParameter` over hand-editing TMDL when
  creating -- it generates the shape, metadata, and escaping for you.
- To edit an existing parameter, rewrite the calculated partition source with
  `partition_operations` (supply the complete new `{ ... }` set) over
  hand-diffing individual tuples, and preserve the columns and
  `ParameterMetadata`.

### AVOID

- Editing only the partition DAX while leaving `ParameterMetadata`, sort-by, or
  group-by out of sync (Tier 2 hand-edits).
- Silently building a static `SWITCH`-based table when a field parameter was
  requested.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| Desktop shows the table but not as a field parameter | The `ParameterMetadata` `"kind": 2` extended property is missing or malformed on the `Fields` column. Re-create via Tier 1 or restore the extended property. |
| Slicer options appear in the wrong order | `order` values are not dense/zero-based, or `sortByColumn` on the label/fields columns is not pointing at the `Order` column. |
| A tuple fails to parse / DAX error | A label, table, or object name was not escaped. Apply the field parameter TMDL escaping rules in `tmdl-guidelines.md`. |
| Edit dropped fields that should stay | Edits are full replacement — the new `Expression` must list **every** field to keep, not just the added one. |
| `UpdateFieldParameter` not recognized | There is no such operation. Edit via `partition_operations` (Tier 1) or TMDL (Tier 2) as in [Edit a field parameter](#workflow-edit-a-field-parameter). |
| Report slicer broke after rename | A rename changes the binding target; the slicer must be repointed to the new name on the report side. |

---

## Examples

### Create a field parameter (Tier 1, MCP)

Prompt: *"Create a field parameter 'Slice by' that switches between Product Name
and Revenue."*

Use the `CreateFieldParameter` operation of `table_operations` and describe the
ordered fields and display labels through the current tool schema.

### Reorder / add / remove fields (Tier 1, MCP)

Prompt: *"Add Category first, then keep Product Name and Revenue."* There is no
`UpdateFieldParameter` operation -- use the `Update` operation of
`partition_operations` to rewrite the calculated partition with the **complete**
new ordered set. Omitted fields are removed and order is re-derived zero-based.
Follow the current tool schema rather than constructing a cached payload.

The three columns, sort-by, group-by, and `ParameterMetadata` are unaffected by
the partition rewrite -- do not touch them. The visible `Slice by` column is the
one a report slicer would bind to.
