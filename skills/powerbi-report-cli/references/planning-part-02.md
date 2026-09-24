# powerbi-report-cli planning mode -- Power BI Report Planning - Part 2

## Contents

- [Design Contract Gate](#design-contract-gate)
- [Locked Report Spec Output](#locked-report-spec-output)
  - [`report-spec.md` template](#report-specmd-template)
  - [Required acceptance checks before approval](#required-acceptance-checks-before-approval)
- [Approval Gate](#approval-gate)
- [Implementation After Approval](#implementation-after-approval)
- [Fabric Publish Rules](#fabric-publish-rules)
- [Validation Standards](#validation-standards)
- [Anti-Patterns and Pitfalls](#anti-patterns-and-pitfalls)


Continuation of `planning.md`. Open this file directly from the skill reference index.

## Design Contract Gate

Before producing `_brief/report-spec.md` for approval, get a canonical
`Design Brief:` YAML block from the `design` mode. The planner may provide
requirements, model inventory, page goals, and user constraints to the design
skill, but the planner must not author a competing detailed design skeleton.

The canonical design block must include:

- `generated_by: powerbi-report-cli`
- `contract_version`
- one `pages[]` entry for every page in the page plan
- `pages[].layout_contract.canvas`
- `pages[].layout_contract.grid.regions`
- `pages[].layout_contract.placements`
- `pages[].layout_contract.space_audit`
- one `page_title` textbox placement with non-empty title text per page
- slicer placements in a top-right `filters` region or a justified filter rail
- no bare single-value `cardVisual` occupying the largest/dominant hero region
  unless the design marks it as a composite KPI treatment with context and
  rationale
- no unresolved placeholders, ellipses, or prose-only wireframes

If the block is missing these items, stop and revise the design contract before
asking for approval or invoking the `authoring` mode.

## Locked Report Spec Output

After Rounds 0-4, produce one file and save it under `./_brief/` in the
current working directory:

- `./_brief/report-spec.md` — the single source of truth for approval and
  implementation handoff.

`report-spec.md` has two layers:

1. **Markdown sections** for user approval and readable context.
2. A fenced `yaml` block containing the exact `Design Brief:` returned by
   the `design` mode — the canonical implementation contract that
   the `authoring` mode consumes.

If Markdown prose and the embedded YAML disagree, fix `report-spec.md` before
building. Do not ask the authoring agent to choose between conflicting
instructions.

If the agent runtime exposes a dedicated session/scratch folder (for example a
`session-state` path injected by the harness), you may also write a copy there
for user visibility, but the canonical implementation handoff file remains
`./_brief/report-spec.md` unless every later authoring step carries the alternate
absolute path explicitly.

### `report-spec.md` template

The user-approval doc and agent handoff contract. The Markdown captures
sign-off granularity; the embedded YAML captures exact implementation intent.

````markdown
# Report Spec

## Report identity
- Report name:
- Semantic model:
- Audience:
- Primary purpose:
- Delivery target:

## Semantic model binding
<!-- The persisted binding contract consumed by the authoring mode. -->
- Entry mode:          <Local Model | Live Connected Model>
- Workspace name:      <Live Connected Model only>
- Workspace ID:        <Live Connected Model only>
- Model name:
- Model ID:            <Live Connected Model only>
- connectionString:    <Live Connected Model: assembled byConnection string — Data Source=…;Initial Catalog=…;Integrated Security=ClaimsToken;semanticModelId=… | Local Model: byPath ../<Project>.SemanticModel>

## User decisions and constraints
- Scope:
- Page count:
- Interactivity: <navigation model (page navigator | buttons | bookmark navigator); button actions; drillthrough targets; bookmarks; slicers>
- Design direction:
- Publishing:
- Tooling:
- Model edit permissions:
- Accessibility:
- Data caveats:

## Narrative
- Core story:
- Audience promise:
- Key questions answered:

## Design identity (from the `design` mode Step 1)
- Tone: <named entry from tone-catalog, e.g. "Editorial Newsroom">
- Signature: <one defining move, e.g. "tabular numerals + display serif headlines">
- Brownfield delta (if applicable): <current_tone → target_tone>

## Page plan (archetypes from the `design` mode Step 3)
1. Page name
   - Archetype:                      <Executive Summary | Analytical Canvas | …>
   - Layout variant (A/B/C):         <plus one-sentence variant_rationale>
   - Purpose:
   - Visuals:
   - Fields/measures:
   - Slicers/interactions:

## Design system summary
- Theme name + base palette (1–2 lines):
- Color semantics (which measure → which color, 1–2 lines):
- Typography pairing (display + body):
- Layout pattern (grid + gutter + density):
- Accessibility commitments:

## Model requirements
- Existing measures:
- New measures:
- New calculated columns:
- Relationship/sort requirements:

## Canonical design contract

Paste the exact fenced `yaml` block produced by the `design` mode here.
Do not rewrite it from planner memory and do not replace its mechanical
`layout_contract` with a freeform ASCII wireframe.

The YAML block is authoritative for implementation. the `authoring` mode
must implement this block; surrounding prose is context and conflict detection.

## Implementation notes

- Model changes:
- PBIR/report authoring:
- Validation:
- Desktop screenshot verification:
- Publishing boundary:
- Risks:
````

### Required acceptance checks before approval

Before writing the approval question, verify the spec meets all of the
following. If any check fails, fix `report-spec.md` and the embedded
`Design Brief:` block before asking for approval.

- The block begins with `Design Brief:`.
- It includes `generated_by: powerbi-report-cli` and `contract_version`.
- Every Markdown page has a matching `pages[]` entry.
- Every page has `layout_contract.canvas`, `layout_contract.grid.regions`, and
  `layout_contract.placements`.
- Every page has `layout_contract.space_audit` with empty `unplaced_regions`
  and an explicit empty-space/balance rationale.
- Every page has a `page_title` textbox placement with non-empty title text.
- Slicers are in a top-right `filters` region or a justified filter rail; no
  data visual starts under a slicer/header-band region.
- No bare single-value `cardVisual` is the largest/dominant hero region unless
  the YAML explicitly describes a composite KPI treatment with context.
- The approved YAML has no ellipses (`...`), unresolved placeholders, or
  pages/visuals promised in Markdown but omitted from the YAML.

## Approval Gate

After writing `report-spec.md`, ask exactly one approval question:

> Approve this report spec so I can start building?

Recommended choices:

1. Approve — start building
2. Revise audience/purpose
3. Revise scope/page plan
4. Revise design/delivery

Do not enter the authoring or management modes until the user approves.

## Implementation After Approval

When the user approves, execute this sequence:

1. Re-read the approved canonical report spec (normally `_brief/report-spec.md`,
   or the explicitly carried alternate absolute path) and extract the embedded
   `Design Brief:` YAML block. Verify it has `generated_by:
   powerbi-report-cli`, `contract_version`, one populated `layout_contract`
   per page, and `space_audit` per page before authoring. For greenfield, verify
   the canvas is FHD (`1920 x 1080`) unless the user chose another size, and
   verify the largest/dominant region is not a bare single-value `cardVisual`.
2. Mark the first implementation todo as in progress.
3. Connect to the semantic model.
4. Create/update required measures and calculated columns using whichever
   model-authoring path is available — a semantic-model authoring skill, a modeling
   MCP server, or direct TMDL edits — in that order of preference.
5. Validate each model change with DAX where possible.
6. After calculated-column or measure changes, trigger the lightweight
   recalculation supported by the chosen tool (e.g., XMLA refresh with
   `refreshType=Calculate`) unless a full source refresh is explicitly
   required and safe.
7. Export model changes to TMDL.
8. If the export writes a flat TMDL layout, reorganize into
   `definition/database.tmdl`, `definition/model.tmdl`,
   `definition/relationships.tmdl`, and `definition/tables/*.tmdl`.
9. Scaffold or copy the PBIP/PBIR report structure.
10. Author PBIR through the `authoring` mode guidance.
11. Generate report files.
12. Validate required files and JSON.
13. Open/reload in Power BI Desktop.
14. Screenshot pages.
15. Fix visual, slicer, data-binding, accessibility, and layout issues.
16. Publish only if the approved delivery target includes publishing.

## Fabric Publish Rules

Publish only when the approved delivery target includes publishing. Hand the
publish step to the `management` mode; do not author Fabric REST calls
or `definition.pbir` `byConnection` payloads from this skill. See
the `management` mode for the authoritative Fabric **API publish**
`byConnection` schema, LRO polling, and theme upload rules. For binding a local
PBIP to a live Fabric model (the full `byConnection` form used when opening in
Desktop), see the `authoring` mode.

Planner-level rules to respect when invoking the `management` mode:

- Resolve workspace, report, and semantic model dynamically; do not hardcode
  IDs.
- Include all PBIR definition parts on create/update; never send a partial
  definition.
- Match custom theme upload paths exactly to the paths referenced in
  `report.json`.
- Use `--verbose` for long-running operations and poll LROs to a terminal
  state (`Succeeded` / `Failed`).
- Clean up any temporary publish scripts or payload files after the operation
  completes.

## Validation Standards

A report is not complete until:

- Required PBIP/PBIR files exist.
- All JSON parses.
- `definition.pbir` points to the expected semantic model.
- Pages and visuals are generated in expected counts.
- Power BI Desktop opens the `.pbip`.
- Desktop reload succeeds.
- Screenshot capture succeeds for at least the cover and any newly authored
  pages.
- If published, Fabric LRO returns `Succeeded`.

## Anti-Patterns and Pitfalls

- Generated PBIR is safer than hand-editing individual visual JSON files.
- Model changes must be persisted before Desktop reload.
- DAX filter direction can break dimension aggregations from fact-side flags.
- High-cardinality slicers need search or prefix filtering.
- Desktop validation catches issues that JSON validation cannot.
- Fabric publishing is sensitive to `byConnection` schema and theme paths.
