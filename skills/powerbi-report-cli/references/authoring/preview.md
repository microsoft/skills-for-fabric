# Report Preview

## Contents

- [Core workflow](#core-workflow)
- [Host selection](#host-selection)
  - [Desktop operation routing](#desktop-operation-routing)
- [Argument selection](#argument-selection)


Use this runbook for rendered inspection after PBIR validation. Always route
through `powerbi-report-author preview`; do not invoke or describe an underlying
Desktop or service host implementation directly.

## Core workflow

1. Edit the report files.
2. Run `powerbi-report-author validate "<folder>"`.
3. Derive the preview host and arguments from the request, conversation, and
   report context.
4. Open or reload the preview so it contains the latest PBIR.
5. Select and create the temporary validation screenshot directory.
6. Capture every affected page and review the screenshot files. Fix issues,
   validate, and repeat.
7. When the selected host is service and review passes, automatically display
   the validated report in a visible service preview.
8. Delete the workflow-owned screenshot directory.
9. Accept the result only after review. Keep the changes local. Never publish
   or overwrite the remote report with local changes until the user explicitly
   gives permission; if the request does not ask to publish, or you are unsure,
   do not publish. Discard local changes only when explicitly requested.

Step 2 never ends the workflow on success. Every schema validation must
continue through loading the validated PBIR and screenshot validation of every
affected page.

Preview is inspection. Service preview renders the local edited PBIR layout
against a published semantic model's live data. It does not publish or persist
local report edits, and it does not require a published report ID.

Successful service screenshot review always continues to visible display,
without requiring the user to ask. Reuse the validated folder and the same
`--group` and `--dataset`; run visible-mode status first, then open/attach
without `--headless` when permitted. Headless and visible service previews are
separate instances, so this final display does not alter or repeat the completed
screenshot validation. Leave the visible instance open. If it cannot be
displayed, report that display is blocked without invalidating screenshots that
already passed review. This automatic display step applies only to the service
host. It adds no Desktop command and does not change any Desktop routing,
operation, failure handling, or lifecycle rule.

For an authoring task, screenshot capture and review are mandatory completion
steps, not optional user-requested output. Page-scoped edits require screenshots
of each affected page; report-wide changes require `--all-pages`. Load/reload
and screenshot must be separate CLI invocations because combining rendering and
capture can exceed the 30-second command timeout. A standalone request to
capture the current warm view still follows the direct screenshot routing below
and does not implicitly open, reload, or run status.

## Host selection

Use `--host desktop` when the request identifies local Desktop. The preview
command is the source of truth for Desktop availability, capabilities, instance
matching, and errors. These can vary with the installed CLI, bridge, Desktop
build, and live instances. Do not bypass the preview command by calling
`powerbi-desktop` directly.

Desktop preview requires the owning `.pbip` project file for the selected
`.Report` folder. If no owning project file exists, report that prerequisite;
do not silently switch to service preview.

Desktop preview resolves the report from `<folder>`. It never terminates
Desktop. The plain command is open/attach and has no lifecycle flag; issue it
only when the unsaved-changes preflight in *Unsaved host changes* passes with
boolean `false`. When an instance already holds the report it attaches and
re-reads PBIR into that window. The public
preview command resolves the Desktop instance from `<folder>`; it does not accept
`--pid`. The positional argument accepts the `.Report` folder, the directory
containing `definition/`, or the owning `.pbip` file itself; an explicit `.pbip`
always wins over folder-based resolution, which is how you proceed once the user
has told you which project owns an otherwise unresolvable folder.

### Desktop operation routing

Once the user selects Desktop and requests a specific operation, execute only
that operation, preceded only by the unsaved-changes `--status` preflight when
the exception list below requires it:

> **Construction rule:** Every Desktop command explicitly contains
> `--host desktop` and never contains `--pid`. Every screenshot contains
> `--screenshot "<path>"`, with the output path supplied as the value of
> `--screenshot` rather than as a separate positional argument.
> During a screenshot request, every executed `preview` command must contain
> that flag with its destination. This includes a structured-correction retry; never replace
> the screenshot with attach, reload, status, help, or host discovery.
>
> **Terminal rule (the single retry policy):** After that command runs, any
> failure without an explicit machine-readable `correction` object ends the
> Desktop workflow. Make no more tool calls. An error message, hint, usage
> output, unknown-option response, or suggestion to run help is not a structured
> correction. When a `correction` object *is* present, retry the same operation
> **once**: patch the original command with only the named correction, keeping
> the operation, host, folder, screenshot destination, bindings, headless mode,
> and screenshot modifiers unchanged — so a screenshot retry still carries
> `--screenshot "<same-path>"`. If the correction asks you to
> change one of those requested values, stop instead. This rule overrides every
> discovery, status, troubleshooting, and error-table instruction below, and
> applies equally to default-page, `--page`, `--all-pages`, and `--scale`
> screenshots. Do not inspect the folder, search for `.pbip`, change paths, or
> alter any screenshot modifier after failure.
> The requested host and operation are immutable. Never switch Desktop to
> service or replace attach/reload/screenshot with another lifecycle operation,
> even when a correction recommends it.
>
> **What counts as a failure here:** an `ok: false` envelope — the command did
> not do its job. A capture that returns `ok: true` with `status: "partial"` is
> **not** a failure for this rule, even though it exits non-zero and carries
> per-page entries in `failures[]`: the command ran, and the captures it returned
> are valid. Report every capture and every failure, and see *Preview
> lifecycle* below for the one per-page cause you may act on.

| Requested operation | Command shape |
|---|---|
| Attach/open | `powerbi-report-author preview "<folder>" --host desktop` |
| Reload | `powerbi-report-author preview "<folder>" --host desktop --reload` |
| Reload report and model | `powerbi-report-author preview "<folder>" --host desktop --reload-with-model` |
| Screenshot | `powerbi-report-author preview "<folder>" --host desktop --screenshot "<path>" [--page <id> | --all-pages] [--scale <1-3>]` |

Every screenshot contains `--screenshot "<path>"`, whose value is the output
destination. A selected-page screenshot adds `--page <id>` and writes one PNG.
An all-pages screenshot adds `--all-pages` and writes to a directory. The output
path is the value of `--screenshot`; it is never a separate positional operand.
For example:

```bash
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>" --all-pages --scale 2
```

Desktop screenshot is a warm capture: it snapshots the current window as-is and
does not reload PBIR. Use a separate explicit `--reload` operation before
capture when the latest on-disk edits must be rendered. A reload reports
`LIVE_WINDOW_RELOADED`; a `--screenshot` always reports
`LIVE_WINDOW_NOT_RELOADED`, which describes only the screenshot operation and
says nothing about whether a prior reload succeeded. Establish freshness from a
reload's `LIVE_WINDOW_RELOADED`, not from the screenshot marker.

The `LIVE_WINDOW_NOT_RELOADED` advisory text suggests refreshing with the plain
`preview <folder> --host desktop` form. Use `--reload` instead: the plain form
is attach/open in this skill's protocol, and the rule below against translating
attach into reload takes precedence over the advisory's wording.

Treat **attach**, **open**, **connect**, and **show** as attach/open. Never
append `--reload`. Use `--reload` for PBIR-only **reload** or **refresh**.
When TMDL/model files changed, follow Semantic-model reload workflow (see
`preview-part-04.md`, section `semantic-model-reload-workflow`) and use
`--reload-with-model`; never substitute plain `--reload`. It is a standalone
Desktop operation; never combine it with `--reload` or another operation flag.
Do not add `--pid`; instance selection is resolved from `<folder>`.

Do not run validation, `--help`, `--list-hosts`, `--reload`, or any other
lifecycle command before the requested operation, and do not switch to service
or call `powerbi-desktop` directly. **Exactly two exceptions exist**, and nothing
else is one:

1. The unsaved-changes `--status` preflight required before `--reload`,
   `--reload-with-model`, and a bare `preview` — the forms that re-read files
   into a live window. For open/attach, proceed on explicit boolean `false` or
   structured `HOST_UNAVAILABLE`. For either reload form, proceed only on
   explicit boolean `false`; `HOST_UNAVAILABLE` is terminal. On `true`,
   missing, invalid, or any other failed status read, stop and report the
   safety-gate failure without running open/reload. For a standalone preview
   request, stop; never ask whether automatic open/reload should proceed
   despite the failed safety gate.
   During mandatory post-edit validation, explicit boolean `true` instead uses
   the manual-resolution resume path under *Unsaved host changes*. The
   preflight is never run before a screenshot on either host. See *Unsaved host
   changes*.
2. The partial-capture recovery described under *Preview lifecycle*, which runs
   as a new sequence *after* a partial returns, never fronted onto the original
   capture.

In particular, a screenshot request is capture only: never reload or check
status first.

Execute the constructed Desktop command once. Retry the same operation once only
when the structured result contains an explicit machine-readable `correction`
object, patched as the Terminal rule above describes. Without that object, stop
and report the failure immediately without another tool call. Do not diagnose it
with `--help`, `--list-hosts`, `--status`, `--reload`, another preview
operation, validation, a different host, or `powerbi-desktop`.

Use `--host service` when service rendering is requested. Service preview
requires both `--group <workspace-guid>` and
`--dataset <semantic-model-guid>`. Ask for either missing identifier; never
infer tenant-scoped GUIDs.

If the user already selected service but omitted either identifier, ask
immediately and stop before running any command or searching project files. Ask
only for the missing workspace GUID used by `--group` and/or semantic-model GUID
used by `--dataset`. Do not run `--list-hosts`, validation, status, or preview
first, and do not inspect the report for tenant-scoped IDs. Do not add offers
about headless mode, screenshots, pages, name resolution, publication, or
unrelated validation.

When the service host, both identifiers, and a specific operation are supplied,
preserve both binding flags unchanged. Execute service status or screenshot
directly. Before service open/attach or reload, run service status with the same
binding and instance mode, then follow *Unsaved host changes*. For a service
screenshot, use `--screenshot "<path>"`. The service host supports default-page
capture, `--page <id>`, `--all-pages`, and `--scale <1-3>`. Use a PNG
destination for one page and a directory for `--all-pages`.
Preserve `--headless` when the existing instance is headless. Host and operation
are immutable.

Before a host is selected, when host availability or capabilities are unknown,
run:

```bash
powerbi-report-author preview --list-hosts
```

Use `--list-hosts` to choose a host, not as a replacement for status on a host
the user already named and never to diagnose a failed selected-Desktop
operation. For example, a request to check Desktop preview status uses:

```bash
powerbi-report-author preview "<folder>" --host desktop --status
```

Do not guess a host when the request distinguishes Desktop from service. Do not
infer workspace or semantic-model IDs.

Always pass `--host` for report operations. Omitting it relies on a default that
may select the wrong rendering environment for the request.

## Argument selection

Derive every argument already established by the request, conversation, or
report context. Ask only when a required value is missing or ambiguous.

- `--host desktop|service`: required host selection.
- `--group <id>`: service workspace GUID; required for every service command.
- `--dataset <id>`: published semantic-model GUID; required for every service
  command.
- `--headless`: service agent mode with no visible browser window.
- `--status`: inspect an existing live preview instance for the selected host.
- `--reload`: re-read edited PBIR files into an existing preview instance.
  For a headless service instance, include `--headless`. On every host, run the
  status preflight under *Unsaved host changes* first.
- `--reload-with-model`: Desktop only. Re-read edited PBIR and TMDL/model files.
  Use only through Semantic-model reload workflow (see `preview-part-04.md`,
  section `semantic-model-reload-workflow`), including the required processing
  and DAX verification. Run the status preflight first.
- `--screenshot <path>`: capture to a PNG file for a
  default-page or `--page` capture and a directory for `--all-pages`.
- `--page <id>`: capture one page by ID or display name. Read the ID from
  `powerbi-report-author preview-pages "<folder>"`, whose `name` field is the
  page ID and `displayName` the label; it reads the report from disk and needs
  no running Desktop instance. Supported by both hosts. Do not combine with
  `--all-pages`.
- `--all-pages`: capture every page into the `--screenshot` directory.
  Supported by both hosts.
- `--scale <1-3>`: optional capture scale on both hosts; host default is 2.
- `--close`: tear down the service browser preview instance. Do not use it to
  close Power BI Desktop; Desktop is owned by the user.

Both hosts use `--screenshot <path>` and support page selection (`--page`,
`--all-pages`) plus `--scale`. Service binding remains `--group` and
`--dataset`. Do not invent `--workspace` or `--report-id`.
For mandatory authoring validation, select `<validation-screenshot-dir>` through
Screenshot artifact lifecycle (see `preview-part-03.md`, section
`screenshot-artifact-lifecycle`). Use
`<validation-screenshot-dir>\<descriptive-name>.png` for one page and the
directory itself for `--all-pages`. Never use a current-directory-relative
path or a path inside the PBIP project.

For operations that open or capture a service instance, keep visible/headless
mode consistent. If the live instance was opened with `--headless`, include
`--headless` on `--screenshot` as well; otherwise the binding is replaced with
a visible instance.
