# Report Preview - Part 4

## Contents

- [Semantic-model reload workflow](#semantic-model-reload-workflow)

Continuation of `preview.md`. Open this file directly from the skill reference
index.

## Semantic-model reload workflow

Treat file reload and live-model processing as separate operations.
`--reload-with-model` loads the report and TMDL definitions into Desktop. A
successful response does not mean that calculated objects are ready, import
data was refreshed, or report visuals contain current values.

Choose the workflow from what changed:

| Change | Desktop operation | Required model processing |
|---|---|---|
| PBIR only | `--reload` | None |
| TMDL metadata, measure, relationship, calculated column/table, or other calculated field | `--reload-with-model` | Power BI Modeling MCP `RefreshWithXMLA` with `refreshType: Calculate` |
| New or changed imported source column, M expression, import partition, or import table | `--reload-with-model` | Targeted `RefreshWithXMLA` with `refreshType: Full` on each affected table or partition |
| New or changed field in a non-Import storage mode | `--reload-with-model` | Follow the semantic-model workflow for that storage mode; do not apply the Import `Full` rule by default |
| Source-data refresh with no TMDL edit | No report reload | Targeted `RefreshWithXMLA` with `refreshType: Full` |

For a TMDL edit:

1. Finish and validate all PBIR and TMDL file edits before changing the live
   model.
2. Run the Desktop `--status` safety preflight. Continue only when
   `details.hasUnsavedChanges` is explicit boolean `false`.
3. Run `powerbi-report-author preview "<folder>" --host desktop
   --reload-with-model` once. If it fails, follow the terminal failure rule in
   `preview.md`; do not process a model that did not load.
4. Use the semantic-model authoring workflow or Power BI Modeling MCP to run the
   processing action from the table above. Prefer targeted `Full` processing
   over model-wide `Full`.
5. Run reload and model processing serially. Wait for each operation to finish
   before starting the next one.
6. Verify the expected model values with a DAX query, then capture and review
   every affected report page.

Model processing can set `details.hasUnsavedChanges` to `true`. Screenshots may
still verify that live state, but do not run another Desktop reload. If more
file edits are needed, ask the user to save or discard the live Desktop changes
first. Do not claim that the updated model is valid from reload success alone.
