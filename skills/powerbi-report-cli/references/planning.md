<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `planning` mode. -->

# powerbi-report-cli planning mode -- Power BI Report Planning

This skill orchestrates the full lifecycle for a new Power BI report:

**Define -> Inspect -> Spec -> Approve** | *user replies* | **Build -> Validate -> Publish**

`Approve` is a TURN BOUNDARY, not a step you walk past. Everything to its left
happens in this turn; everything to its right happens only in a LATER turn, after
the user has actually answered. This mode does continue into implementation, but
never in the same turn that asked for approval -- if no reply has arrived, you are
not approved. Running the arrow end to end as one pipeline is the most common way
this mode fails.

## Must/Prefer/Avoid

### MUST

- Use this skill for broad report creation workflows that need requirements, dependency checks, approval, and build sequencing.
- Ask focused clarification questions one at a time and stop after the required decision is clear.
- Lock `_brief/report-spec.md`, ask for approval, then end the turn. Your own question is not an approval.
- Route design decisions through the `design` mode and file mechanics through the `authoring` mode.

### PREFER

- Infer obvious answers from the prompt, model, existing PBIP files, or earlier rounds instead of re-asking.
- Inspect the semantic model before finalizing page scope or visual recommendations.
- Treat publishing as optional and only proceed when approved.

### AVOID

- Do not use this skill for small, surgical edits to existing PBIR files.
- Do not build before the user approves the locked report spec.
- Do not duplicate detailed visual-design or PBIR-authoring guidance that belongs to companion skills.

## Examples of When to Use

Use this skill when the user wants to create a new Power BI report and needs
both:

1. A guided requirements workflow.
2. A path to implementation after approval.

Examples:

- "Let's create a new Power BI report from this semantic model."
- "Help me define and then build a Power BI report."
- "Use the report playbook to start a new report."
- "Create a reusable workflow for new Power BI reports."

Do **not** use this mode for a small edit to an existing report page. For
direct PBIR authoring tasks, use the `authoring` mode. For visual critique or
greenfield design guidance **without the full guided workflow** (a one-off
"redesign this" or "what should this look like?"), use
the `design` mode directly. This mode *uses* the `design` mode during
Rounds 3–4 — it does not replace it.

## Required Operating Rules

1. **Ask one question at a time.** Use `ask_user` for each clarification.
2. **Run 3-5 clarification rounds maximum.** Each round may have one primary
   question and, only if absolutely necessary, one follow-up.
3. **Inspect the semantic model before locking the spec.** Use the semantic
   model skill or an MCP server when available; otherwise inspect local
   TMDL/PBIP files directly.
4. **Check dependencies explicitly.** Do not assume Desktop, MCP, authoring, or
   Fabric publishing are available.
5. **Produce one locked `_brief/report-spec.md` before building.**
6. **Ask for approval before implementation, then END YOUR TURN.** Do not build
   until the user has explicitly approved in a reply. Your own question does not
   count as approval, and neither does the absence of an objection.
7. **When approved, build end-to-end.** Only once that reply has arrived: model
   changes, PBIR generation, validation, Desktop preview, screenshot loop, and
   optional Fabric publish.
8. **Local edits stay local unless publishing is approved.**
9. **Do not re-ask known answers.** If the original prompt, inspected files, or
   a prior round already provides audience, page count, delivery target, scope,
   or design direction, capture it in working notes and move on. Ask only for
   genuine ambiguity or risky tradeoffs.

## Dependency Checklist

Before implementation, capture this status:

| Dependency | Purpose | Required When |
|---|---|---|
| Power BI Desktop | Open/reload PBIP and visually validate report | Always for local preview |
| PBIP/PBIR project | File-based report authoring | Always for generated reports |
| TMDL semantic model | Model persistence and source control | Required for model edits |
| `powerbi-modeling-mcp` | Inspect tables, columns, measures; create measures/columns; deploy semantic model | Required for live model authoring |
| `authoring` mode | Validate PBIR, reload Desktop, screenshot pages | Required for report authoring validation |
| `management` mode | Create/update/download Fabric reports | Required only for Fabric publishing |
| Node.js | Generator-based PBIR authoring | Recommended for reproducible reports |

If a dependency is unavailable, continue planning and mark the affected phase as
blocked/manual. Do not pretend it is available.

## Round Structure

### Round 0 — Setup and Dependency Check

Goal: identify the semantic model, report target, and available tooling.

Ask only what cannot be inspected automatically:

> What semantic model or dataset should this report use?

Recommended choices should be concrete if candidates are discoverable. Enumerate
existing Fabric semantic models and local `.SemanticModel` folders in scope,
then present them as options and mark the best match as recommended. Example:

- `<DiscoveredSemanticModelName>` (Recommended)
- Another existing Fabric semantic model
- A new local dataset

Then inspect/check:

- Existing `.pbip`, `.Report`, `.SemanticModel` folders.
- Whether TMDL files exist.
- Whether Power BI Desktop automation script exists.
- Whether MCP connection is available or can be established.
- Whether Fabric publishing is requested.

Output working notes:

```markdown
Dependency status:
- Semantic model:
- PBIP/PBIR:
- Desktop preview:
- Modeling MCP:
- Report-authoring skill:
- Fabric publishing:
- Node generator:
```

### Round 1 — Audience and Job

Goal: understand who the report is for and what decision/job it supports.

If both audience and job-to-be-done are already clear from the prompt, summarize
the inferred answer instead of asking. Otherwise ask for the missing piece(s),
one at a time.

Ask when audience is unclear:

> Who is this report primarily for?

Recommended choices:

1. Executives / leadership — concise KPIs, trends, risks, decisions
2. Analysts — exploration, drilldowns, comparisons, tables
3. Operators — monitoring, exceptions, status, action queues
4. External audience — polished story, guided narrative, minimal slicers
5. Enthusiasts / fans — magazine-style narrative, rich visuals, rankings

Then ask only if the job-to-be-done is still unclear:

> What should the report help them do?

Recommended choices:

1. Understand the overall story
2. Track performance
3. Find outliers or opportunities
4. Compare entities or segments
5. Explore individual records/profiles
6. Prepare for a recurring business review

Capture:

```markdown
Audience:
Primary purpose:
Tone:
Success criteria:
```

### Round 2 — Model Inventory and Scope

Goal: inspect the model and define the first-build scope boundary without
re-asking for scope the user already gave.

Use whatever model-inspection capability is available — pick the first that
applies, in order of preference:

1. A semantic-model authoring skill, if installed.
2. A modeling MCP server (e.g., `powerbi-modeling-mcp-*`) — connect to the
   live model, list tables/columns/measures/relationships, and run DAX for
   live validation.
3. Direct reads of local TMDL files (`definition/model.tmdl`,
   `definition/tables/*.tmdl`, `definition/relationships.tmdl`) when no live
   connection is available.

Do not hardcode tool names in user-facing prompts — describe the inspection
intent and let the agent pick the available tool.

Summarize:

```markdown
Facts:
- table, grain, keys, useful measures

Dimensions:
- date/time, geography, entity, category, owner, status, segment

Existing measures:
- core available measures

Likely missing model work:
- measures
- calculated columns
- relationship fixes
- sort columns
- helper fields for slicers/search

Risks:
- nulls/sparsity
- inactive relationships
- high-cardinality slicers
- fields that will not filter as expected
```

After inspection, infer the first-build scope from the original request and
prior answers. Do not ask a standalone scope question if the user already gave a
page count, report type, or content boundary (for example, "build a 4 page
dashboard"). Instead, summarize the boundary in working notes:

```markdown
First-build scope:
- <focused first build / standard report / operational app / narrative report>
- inferred from: <user prompt | prior answer | model shape>
- included now:
- deferred:
```

Ask a scope question only when the boundary is unclear, too broad, or risky. If
asking, present tailored choices from the inspected model rather than generic
first-build options. Example:

> The model supports sales, products, geography, discounts, and profitability.
> For this first build, should we keep it focused on executive performance, or
> include a deeper product/customer exploration too?

### Round 3 — Narrative and Page Plan

Goal: turn the model and scope into page architecture.

Invoke or explicitly consult the `design` mode for page-level archetype
routing and composition guidance. The design skill owns visual routing; do not
duplicate its routing table here. Use the data shape from Round 2 to surface
2-3 report shape options for user sign-off.

The five archetypes the design skill ships are: **Executive Summary**,
**Operational Monitor**, **Analytical Canvas**, **Narrative Story**,
**Comparative Benchmark**. Use the design skill's archetype and composition
guidance for layout variants, multi-archetype reports, and cross-page variant
rotation.

Ask only after applying the inferred first-build scope from Round 2:

> Which report shape should we use?

Present 2–3 named compositions (e.g., *Executive landing + Analytical
exploration + Comparative ranking* for a multi-domain ask, or *Single
executive landing* for a focused ask). Recommend one based on Rounds 1–2
and mark it `(Recommended)`.

Draft page list in the answer after the user chooses:

```markdown
Proposed pages:
1. <Page> — archetype — purpose — core visuals — fields/measures
2. <Page> — archetype — purpose — core visuals — fields/measures
<repeat for each approved page>
```

Capture slicers and interactions:

- Global slicers
- Page-specific slicers
- Search/prefix slicers for high-cardinality dimensions
- Drillthrough/profile pages
- Bookmarks/navigation if needed

### Round 4 — Design Identity, Accessibility, and Delivery

Goal: lock the design identity, accessibility baseline, and delivery target.

Invoke or explicitly consult the `design` mode for design identity and
theme direction. Design identity (tone + signature) is owned by the design skill
— do not invent a parallel vocabulary here. Use the design skill's identity
guidance to pick a tone+signature combination, then surface it to the user.

Ask:

> What should this report feel like?

Present 2–3 concrete identity options adapted to the audience and domain from
Rounds 1–2. Each option names a report feel and the one signature visual move
it implies. Recommend one and mark it `(Recommended)`.

If the user has brand guidelines, make one option brand-forward rather than
picking a generic tone.

Then ask delivery only if unclear:

> Where should the finished report end up?

Recommended choices:

1. Local PBIP only first
2. Publish to an existing Fabric workspace
3. Create new semantic model + report in Fabric
4. Update an existing Fabric report
5. Build local first, decide publishing later

Design defaults (these come from the design skill's gotchas + base theme;
applied automatically unless the user overrides):

- Use accessible contrast (WCAG AA minimum on every text/background pair).
- Avoid red-on-red and low-contrast palettes.
- Prefer Azure Map over deprecated map/filledMap visuals.
- Add alt text to every chart.
- Use searchable dropdown slicers for high-cardinality fields.
- Use tile/list slicers only for short categorical fields.
- Place detailed tables near the bottom of the page.
- Keep report interactions predictable and consistent.

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

## User decisions and constraints
- Scope:
- Page count:
- Interactivity:
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

The YAML block is authoritative for implementation. The `authoring` mode
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

Do not invoke authoring or publishing skills until the user approves.

Then stop and end your turn. A request that said "build it" or "publish it" is what
brought you here; it is not the approval, because the spec it would approve did not
exist yet. If no reply has arrived, the correct final state of this turn is the
written spec plus the question above -- nothing built, nothing published.

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
the `management` mode for the authoritative `byConnection` schemas
(minimal API form and full XMLA form for local Desktop validation), LRO
polling, and theme upload rules.

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
