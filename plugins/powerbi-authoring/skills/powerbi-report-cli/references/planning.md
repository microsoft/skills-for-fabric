
## Contents

- [Must/Prefer/Avoid](#mustpreferavoid)
  - [MUST](#must)
  - [PREFER](#prefer)
  - [AVOID](#avoid)
- [Examples of When to Use](#examples-of-when-to-use)
- [Required Operating Rules](#required-operating-rules)
- [Dependency Checklist](#dependency-checklist)
- [Round Structure](#round-structure)
  - [Round 0 — Setup and Dependency Check](#round-0--setup-and-dependency-check)
  - [Round 1 — Audience and Job](#round-1--audience-and-job)
  - [Round 2 — Model Inventory and Scope](#round-2--model-inventory-and-scope)
  - [Round 3 — Narrative and Page Plan](#round-3--narrative-and-page-plan)
  - [Round 4 — Design Identity, Accessibility, and Delivery](#round-4--design-identity-accessibility-and-delivery)

<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `planning` mode. -->

# powerbi-report-cli planning mode -- Power BI Report Planning

> **Required continuation.** After this file, open
> `skills/powerbi-report-cli/references/planning-part-02.md` directly from the
> complete reference index before producing `_brief/report-spec.md`.

This skill orchestrates the full lifecycle for a new Power BI report:

**Define -> Inspect -> Spec -> Approve -> Build -> Validate -> Publish**

It is intentionally broader than a pure requirements-gathering flow: it captures
the report spec **and** continues into implementation after the user approves.

## Must/Prefer/Avoid

### MUST

- Use this skill for broad report creation workflows that need requirements, dependency checks, approval, and build sequencing.
- Ask focused clarification questions one at a time and stop after the required decision is clear.
- Lock `_brief/report-spec.md` and get approval before implementation.
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

Do **not** use this skill for a small edit to an existing report page. For
direct PBIR authoring tasks, use the `authoring` mode. For visual critique or
greenfield design guidance **without the full guided workflow** (a one-off
"redesign this" or "what should this look like?"), use
the `design` mode directly. This skill *uses* the design skill during
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
6. **Ask for approval before implementation.** Do not build until the user
   explicitly approves.
7. **When approved, build end-to-end.** Model changes, PBIR generation,
   validation, Desktop preview, screenshot loop, and optional Fabric publish.
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
| powerbi-modeling-mcp | Inspect tables, columns, measures; create measures/columns; deploy semantic model | Required only for the **`Live Connected Model`** entry mode (remote Fabric model) — not needed for **`Local Model`** mode |
| the `authoring` mode | Validate PBIR, reload Desktop, screenshot pages | Required for report authoring validation |
| the `management` mode | Create/update/download Fabric reports | Required only for Fabric publishing |
| Node.js | Generator-based PBIR authoring | Recommended for reproducible reports |

If a dependency is unavailable, continue planning and mark the affected phase as
blocked/manual. Do not pretend it is available.

## Round Structure

### Round 0 — Setup and Dependency Check

Goal: identify the semantic model, report target, and available tooling.

#### Entry modes — how the user is starting

A report always sits on top of a semantic model, so the first job is to locate
that model. There are multiple entry modes; detect which one the user is starting
from and follow the matching path. All three converge on the same working-notes
block below.

| Entry mode | The user is starting from |
|------------|---------------------------|
| `Local Model` | Model files already on disk (`.pbip` / `.SemanticModel` / `.Report`) |
| `Live Connected Model` | A model that lives in a Fabric/Power BI workspace (link, ID, or name) |
| `No Model` | No model anywhere — only raw data or an idea |

If the prompt doesn't make the starting point obvious, ask one question to decide
which mode applies — but only when it can't be inferred or inspected:

> What semantic model or dataset should this report use?

A local-folder answer is `Local Model`, a Fabric model/workspace reference is
`Live Connected Model`, and "no model yet" is `No Model`.

**`Local Model`.** The user already has a `.pbip` / `.SemanticModel` /
`.Report` folder on disk.

- Enumerate local `.SemanticModel` and `.pbip` folders in scope and confirm
  which one to use. This is the default path.

**`Live Connected Model`.** The user points at an
existing semantic model in a Fabric/Power BI workspace by any means. All forms
funnel into one resolution procedure that ends with the **canonical identifier
tuple** — `{ workspaceName, workspaceId, modelName, modelId }` — which is what
both report binding and live model inspection consume.

*Step 1 — Detect the input shape and extract what you can:*

- **Portal URL** (shape varies). Parse GUIDs out of the path: `workspaceId` =
  the segment after `/groups/`, `modelId` = the segment after `/datasets/` or
  `/modeling/`. Ignore the tenant subdomain (`app.`, `msit.`, …). `/groups/me`
  means *My workspace*. Example `modelView` link — both values are **GUIDs**:
  `https://<tenant>.powerbi.com/groups/<workspace-id>/modeling/<model-id>/modelView?...`.
- **GUID or name with the kind clear from context** — the user or a URL says it
  is a *model* vs a *workspace* (e.g. "the *evSales* model in the *Sales*
  workspace") → assign to `modelId`/`modelName` or `workspaceId`/`workspaceName`
  accordingly.
- **Kind unspecified** — a bare GUID or name with no indication whether it refers
  to a model or a workspace → **ask the user which it is** before resolving; do
  not assume.
- **A piece is missing** — once the kind is known, ask the user for anything the
  resolution still needs (e.g. a model reference with no workspace).

*Step 2 — Resolve to the full tuple.* This skill does **not** own connection
mechanics — prefer handing the reference to the modeling capability (the Power BI
modeling MCP `powerbi-modeling-mcp` / `semantic-model-authoring` skill) to
resolve and connect. Note the live connect needs the workspace and model
**names**, so if you only have a GUID or URL you must resolve names first. To do
that, use the read-only Fabric workspace/item lookups in
`COMMON-CLI.md § Finding Workspaces and Items` (see `../../../common/COMMON-CLI.md`, section `finding-workspaces-and-items-in-fabric`),
including the **reverse** (ID → name) direction:

- `workspaceId → workspaceName`: get the workspace by ID and read `displayName`.
- `modelId → modelName` (or `modelName → modelId`): list `SemanticModel` items
  in the workspace and match on `id`/`displayName`.
- **Bare `modelId`, no workspace**: the model GUID alone cannot be located
  without a workspace — search accessible workspaces' semantic models for the
  id, or ask the user which workspace it lives in.

*Step 3 — Disambiguate lookup results.* After resolving, if a name or GUID
matches **zero** items (not found or no access) or **more than one** (e.g. a
common name that recurs across workspaces), **ask the user** to pick the intended
workspace/model before continuing. Never guess silently.

*Then:*

- If no live model-inspection capability (modeling MCP) is connected, this mode
  cannot proceed: tell the user the reference requires the modeling MCP and
  either connect it or fall back to `Local Model` mode with local files.
- Model inspection happens in Round 2 against the live model — no local TMDL is
  required.
- **Persist the binding:** record the resolved tuple (`workspaceName`,
  `workspaceId`, `modelName`, `modelId`) and the assembled `connectionString` in
  the brief's **Semantic model binding** section so later steps can reuse it
  without re-resolving.
- **Bind the report:** hand the resolved `workspaceName`, `modelName`, and
  `modelId` to the `authoring` mode, which authors `definition.pbir` using
  the live `byConnection` form. Do not author the connection string here.

**`No Model`.** The user has only raw data or an idea and no model
anywhere. This is **out of scope for report planning** — model creation belongs
to the `semantic-model-authoring` skill and the modeling MCP. Do not attempt to
build a model here. Recognize the situation, point the user to
`semantic-model-authoring` to create the model first, and resume report planning
once a model exists (then re-enter via `Local Model` or `Live Connected Model`).

Once the model is identified, inspect/check the remaining tooling:

- Existing `.pbip`, `.Report`, `.SemanticModel` folders.
- Whether TMDL files exist.
- Whether Power BI Desktop preview automation via `powerbi-report-author preview --host desktop` is available.
- Whether the modeling MCP (`powerbi-modeling-mcp`) connection is available or can be established.
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
- Navigation model: page navigator vs. custom buttons vs. bookmark navigator (pick one primary)
- Button actions needed: Back, page navigation, bookmark, drillthrough, apply/clear all slicers, Web URL, Q&A
- Bookmarks: named saved states for narrative steps or view toggles

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
