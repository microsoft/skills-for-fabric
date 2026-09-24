
## Contents

- [Critical notes](#critical-notes)
- [Must/Prefer/Avoid](#mustpreferavoid)
  - [MUST](#must)
  - [PREFER](#prefer)
  - [AVOID](#avoid)
- [Quick Start Workflow](#quick-start-workflow)

<!-- Mode reference for the `powerbi-report-cli` skill. Loaded on demand from `skills/powerbi-report-cli/SKILL.md` when the request matches the `authoring` mode. -->

> **AUTHORING COMPLETION GATE — MANDATORY FOR REPORT EDITS**
>
> **Schema validation and screenshot validation are paired. Whenever this skill
> runs `powerbi-report-author validate` on a report, a successful schema result
> MUST immediately continue to loading the validated PBIR, capturing every
> affected page, and reviewing the screenshots. Schema success alone is never
> task completion, even when the user did not explicitly request a screenshot.**
>
> Any task that creates or modifies rendered report content is incomplete until:
>
> 1. `powerbi-report-author validate "<folder>"` succeeds.
> 2. The latest edited PBIR is loaded into the selected preview host.
> 3. Every affected page is captured to a screenshot.
> 4. The screenshot files are reviewed using
>    `references/authoring/screenshot-review.md`.
> 5. Visible issues are fixed and the validate → load → screenshot → review loop
>    is repeated.
>
> Capture each page changed by page, visual, filter, slicer, bookmark, or layout
> edits. Use `--all-pages` for report-wide changes such as themes or global
> formatting. Do not report the authoring task complete without successful,
> fresh screenshot review. If the latest PBIR cannot be loaded, the affected
> pages cannot be captured, or the screenshots cannot be reviewed, report
> screenshot validation as blocked rather than claiming completion.
>
> **SCREENSHOT DESTINATION GATE — BEFORE THE FIRST MANDATORY CAPTURE**
>
> Before constructing or running the first screenshot command for mandatory
> authoring validation, read and follow Screenshot artifact
> lifecycle (see `authoring/preview.md`, section `screenshot-artifact-lifecycle`). Do not
> capture until that lifecycle has been loaded and the user has approved the
> screenshot parent. Use only the workflow-owned validation directory created
> by that lifecycle; never invent or hard-code another destination.
>
> **After screenshot review passes on the service host, automatically display
> the validated report in a visible service preview, even when the user did not
> separately request it.** Reuse the same folder, workspace GUID, and semantic-
> model GUID. Run visible-mode service status first, then open/attach under the
> normal safety contract. A headless validation instance and a visible instance
> are separate; do not change or repeat the completed screenshot operation.
> Leave the visible preview open for the user. If display fails, preserve the
> successful validation result but report visible service display as blocked.
> This automatic display step is service-only. It adds no Desktop command and
> does not change Desktop status, open/attach, reload, screenshot, failure, or
> lifecycle behavior.
>
> Loading and screenshot capture are separate CLI invocations. Never combine
> `--reload` and `--screenshot` in one command; rendering and capture together
> can exceed the 30-second command timeout. For authoring verification, follow
> the selected host's `status` → open/attach or reload → screenshot flow. If the
> selected host reports unsaved changes and blocks loading the latest PBIR, do
> not use a stale screenshot to validate the edits.
>
> When the selected host's status reports explicit boolean
> `details.hasUnsavedChanges: true` during **mandatory post-edit validation**,
> do not end the authoring workflow or repeat the PBIR edits. Ask the user to
> resolve the unsaved host state manually and confirm that the latest PBIR is
> loaded. After confirmation, resume directly with screenshot capture and review
> of every affected page. Do not run another status or reload before that
> capture. If the user does not complete the manual step, report screenshot
> validation as blocked.
>
> **DIRECT PREVIEW ROUTING — HIGHEST PRIORITY FOR STANDALONE PREVIEW REQUESTS**
>
> | Operation | Required sequence |
> |---|---|
> | Selected-host open/attach | `status` → open when the host's safety and availability contract permits it |
> | Selected-host reload | `status` → reload when the host's safety and availability contract permits it |
> | Selected-host screenshot | Screenshot only; never status |
> | Selected-host status | Status only |
> | Missing service IDs | Ask immediately; execute no tools |
>
> Open/attach and reload are mandatory two-command sequences for the selected
> host. The first command MUST be:
>
> `powerbi-report-author preview "<folder>" --host <desktop|service> [service binding] --status`
>
> **Open/attach and reload always begin with selected-host status, even when the
> user directly requests the operation. Screenshot operations never begin with
> status, including all-pages captures on either host.**
>
> Never execute open/attach or reload as the first command. After status:
>
> - Follow the selected host's current safety and availability contract in
>   `references/authoring/preview.md`.
> - If status reports explicit boolean `details.hasUnsavedChanges: true`, do not
>   run open/reload automatically.
> - Structured `HOST_UNAVAILABLE` permits open/attach because no matching live
>   instance exists; it does not permit reload.
> - Any invalid required safety field or other status failure stops the
>   operation.
>
> **`details.hasUnsavedChanges: true` is a hard stop and cannot be overridden
> by the user's requested operation.** This rule applies to any host that
> reports unsaved state. It prevents the agent from running open/reload; it does
> not prohibit the manual-resolution resume path above during mandatory
> post-edit validation. Standalone preview requests never use that recovery
> path.

## Critical notes

> 1. **Immutable preview request:** once the user supplies a host and operation,
>    never change either. Preserve the folder, `--group`, `--dataset`,
>    `--headless`, screenshot destination, and supported host-specific modifiers
>    such as `--page`, `--all-pages`, and `--scale` across every
>    permitted retry. If a correction asks to change any of these
>    requested values, stop instead of following it. Never switch hosts.
> 2. **Construct one Desktop command:** every Desktop command must contain
>    `--host desktop`. The public preview command resolves the Desktop instance
>    from `<folder>`; do not add `--pid`. For screenshot, use
>    `--screenshot "<path>"`, where the output path is the value of
>    `--screenshot`; never pass that path as a separate positional argument.
>    Preserve requested `--page`, `--all-pages`, and `--scale` modifiers on the
>    screenshot and any correction-based retry.
> 3. **After a requested Desktop operation returns:** if and only if its machine-readable
>    result contains a `correction` object, retry once by changing only the named
>    value when it is outside the immutable request above. Otherwise **end the
>    current turn immediately**: make zero
>    additional tool calls and report only that failure. Never diagnose, add
>    reload, inspect files, read references, or try a fallback.
> 4. **Service binding:** every service command must
>    include both `--group <workspace-guid>` and `--dataset
>    <semantic-model-guid>` on open, reload, screenshot, status, and close.
> 5. **Service screenshot contract:** use `--screenshot "<path>"`; it supports
>    default-page capture, `--page <id>`, `--all-pages`, and `--scale <1-3>`.
>    Use a PNG destination for one page and a directory for `--all-pages`.
>    Never add `--pid` to a service command.
>    Preserve both binding flags and existing `--headless`. After failure, retry
>    only from an explicit
>    machine-readable `correction` object while keeping host and operation
>    unchanged; otherwise end the turn with zero additional tool calls. Never
>    run `--help` as recovery.
> 6. **Management workflows only:** when managing Fabric resources, find
>    workspace details (including its ID) from a workspace name by listing
>    workspaces and using JMESPath filtering. This discovery rule does not apply
>    to preview requests; if preview is missing `--group`, ask for it immediately.
> 7. **Management workflows only:** when managing Fabric resources, find item
>    details (including its ID) from a workspace ID, item type, and item name by
>    listing items of that type and using JMESPath filtering. This discovery
>    rule does not apply to preview requests; if preview is missing `--dataset`,
>    ask for it immediately.

# powerbi-report-cli authoring mode -- Power BI Report Authoring (PBIR/PBIP)

This skill enables reading, editing, and creation of Power BI report
definition files in the **PBIR (Power BI Report)** format used by **PBIP
(Power BI Project)** files.

## Must/Prefer/Avoid

### MUST

- **Desktop terminal rule (highest priority):** after executing a selected
  Desktop attach/open, reload, status, or screenshot command, a failure without
  an explicit machine-readable `correction` object ends the current turn. Emit
  zero further tool calls. Parser errors, usage text, hints, suggested help, and
  unknown-option messages are not structured corrections. This rule overrides
  all host discovery, status, troubleshooting, retry, validation, file
  inspection, reference-reading, and general error guidance. The sole exception
  is structured `HOST_UNAVAILABLE` from the mandatory status preflight for
  open/attach, which proceeds to the plain open/attach command as specified in
  the top-level routing table; the same result remains terminal for reload.
- The Desktop terminal rule covers every screenshot form: default page,
  `--page`, `--all-pages`, `--scale`, and any combination allowed by the CLI.
  Never alter the folder, screenshot destination, page, scale, or all-pages
  choice after failure.
- Desktop screenshot uses `--screenshot <path>`; the output path is the value
  of `--screenshot`. It is a warm capture of the
  current Desktop window and does not reload PBIR. Service screenshot uses the
  same `--screenshot <path>` flag and supports default-page, selected-page,
  all-pages, and scale capture.
- Every preview command executed for a screenshot request must retain that
  host's exact screenshot operation and destination. This includes the only
  permitted correction-based retry.
- Use this skill only for concrete PBIR/PBIP report-file mechanics such as pages, visuals, filters, slicers, navigation, bookmarks, themes, formatting, validation, previews, and screenshots.
- Validate PBIR with `powerbi-report-author validate` after each logical batch.
  Every successful schema validation must continue into fresh screenshot
  capture and review; never stop at the validation result.
- Use the `powerbi-report-author preview` command for rendered-output
  inspection. Always pass `--host`; never rely on the command's default host.
- Classify the Desktop operation from the user's verb. **Attach**, **open**,
  **connect**, or **show** means the plain command with no lifecycle flag. Add
  `--reload` only when the user explicitly requests **reload** or **refresh**.
  Never translate attach/open into reload because the host may synchronize
  files internally.
- After a requested Desktop operation fails, retry once only when its structured
  result contains an explicit machine-readable `correction` object. Apply only
  its named correction to the same host and operation and preserve every other
  selected argument. Never follow a correction that switches Desktop to
  service or changes the operation. In particular, never add `--reload` to
  attach or drop screenshot arguments. Otherwise stop and report the failure
  immediately with no additional tool call. Do not diagnose the failure by
  running `--help`, `--list-hosts`, `--status`, `--reload`, another preview
  operation, validation, a different host, or `powerbi-desktop`.
- Follow the top-level **Direct preview routing** table exactly. Detailed command
  construction and error handling for standalone preview requests are in
  `preview.md` (see `authoring/preview.md`).
- Derive preview arguments from the request, conversation, and report context.
  Ask only when required information is missing or ambiguous; never infer
  tenant-scoped workspace or semantic-model IDs.
- Treat preview as inspection: service preview does not publish local work in
  progress. Never treat approval of edits, validation, screenshots, or preview
  as permission to publish. Never publish or overwrite the remote report with
  local changes until the user explicitly gives permission to do it. Publish
  only when the current request explicitly asks to publish, upload, push, or
  deploy the local changes. If that intent is absent, ambiguous, or you are
  unsure, keep the changes local and do not publish — do not ask to publish
  and do not make any remote write. Modifying a report with the service host
  means local edits plus validate plus preview only; never publish as part of
  that flow. Discard changes only when explicitly requested.
- Treat host availability and capabilities as runtime facts. Respect
  `HOST_UNAVAILABLE` and `CAPABILITY_UNSUPPORTED`; do not bypass the preview
  command by calling an underlying host CLI directly.
- Use CLI capability lookup before writing visual roles, formatting objects, enum values, selectors, or expression encodings.

### PREFER

- Start from an approved `Design Brief:` or `_brief/report-spec.md` for greenfield report builds.
- Route visual-design uncertainty to the `design` mode before writing files.
- For semantic model metadata or model-side changes, use a semantic-model authoring skill, Power BI Modeling MCP, or local TMDL files when available.

### AVOID

- Do not guess PBIR JSON from memory when CLI metadata or reference files are available.
- Do not use only this skill for open-ended design, report planning, or Fabric report item CRUD; pair it with the `design` mode, the `planning` mode, or the `management` mode.

## Quick Start Workflow

0. **Plan/design routing** → for greenfield builds, read the `planning` mode
   first; for theming, visual style, layout, redesigns, or critiques, read
   the `design` mode. Return here for PBIR mechanics. Before authoring,
   use the `Design Brief:` yaml block from `_brief/report-spec.md` (or an
   approved inline `Design Brief:` block in the conversation) as implementation
   context.
1. **Set up/update CLI** → before first use, confirm `powerbi-report-author`
   is available; see **CLI Setup** in `authoring-part-02.md`.
2. **Understand the model** → use the Semantic Model MCP Server/skill if available,
   or read TMDL files directly for table/column/measure names
3. **Preview context** → if Desktop and an operation are already selected,
   execute the Critical Notes protocol immediately. Otherwise derive the host
   and required arguments from available context; see **Edit → Validate →
   Preview → Review** in `authoring-part-03.md`.
4. **Route by intent** → use **Topic Files and Examples** in
   `authoring-part-02.md` to pick the relevant guide.
5. **Use CLI metadata** → use **Authoring Metadata & Validation CLI** in
   `authoring-part-03.md`
   for exact visual roles, formatting objects, property names, enum values, and
   selector requirements; do not infer these from memory.
6. **Check common pitfalls** → read **Anti-Patterns and Pitfalls** in
   `authoring-part-04.md`
   before editing or validating when the change touches visuals, bindings,
   filters, formatting, layout, or rendered output.
7. **Validate** → run `powerbi-report-author validate <path-to-.Report-dir>`
   after every logical batch of PBIR changes, then always continue to step 8;
   see **Validation** in `authoring-part-03.md`.
8. **Verify rendering** → for every rendered-output change, load the latest
     PBIR, capture every affected page, and review the screenshot files using
     the `powerbi-report-author preview` surface with an explicit `--host`; see
     **Edit → Validate → Preview → Review** in `authoring-part-03.md`
     and Screenshot Review (see `authoring/screenshot-review.md`). Do not proceed until both
     validation and visual review pass. For dashboard/report builds, page
     scaffolding is not completion — each requested page needs data-bound visuals.
9. **Report back** → give the user a concise summary of what was done and any
      issues encountered (major and minor).
