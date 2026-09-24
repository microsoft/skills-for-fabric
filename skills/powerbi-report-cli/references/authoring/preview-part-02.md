# Report Preview - Part 2

## Contents

- [Exact command examples](#exact-command-examples)
- [Status and ambiguity](#status-and-ambiguity)
- [Preview lifecycle](#preview-lifecycle)
  - [Unsaved host changes](#unsaved-host-changes)
- [Errors and fix/retry](#errors-and-fixretry)


Continuation of `preview.md`. Open this file directly from the skill reference index.

## Exact command examples

Discover hosts and capabilities:

```bash
powerbi-report-author preview --list-hosts
```

Check Desktop status through the selected Desktop host:

```bash
powerbi-report-author preview "<folder>" --host desktop --status
```

Use the returned structured status or error as the source of truth. If the
installed host reports unavailable or unsupported behavior, surface that result
rather than using the underlying bridge directly.

Attach/open the matching Desktop instance with no lifecycle flag:

```bash
powerbi-report-author preview "<folder>" --host desktop
```

Reload edited PBIR into the matching Desktop instance:

```bash
powerbi-report-author preview "<folder>" --host desktop --reload
```

For TMDL/model changes, follow Semantic-model reload workflow (see
`preview-part-04.md`, section `semantic-model-reload-workflow`) instead of
using plain `--reload`.

Capture through the matching Desktop instance:

```bash
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>\page.png"
```

Capture a selected Desktop page:

```bash
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>\page.png" --page "<page-id>"
```

Capture all Desktop pages:

```bash
powerbi-report-author preview "<folder>" --host desktop --screenshot "<validation-screenshot-dir>" --all-pages
```

Open a visible service preview:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>"
```

Open a headless service preview for an agent:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless
```

Reload edited files into the live service instance:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --reload
```

Reload an existing headless instance:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --reload
```

Capture the default service page:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --screenshot "<validation-screenshot-dir>\page.png"
```

For an existing headless instance:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --headless --screenshot "<validation-screenshot-dir>\page.png"
```

Capture one selected service page:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --screenshot "<validation-screenshot-dir>\page.png" --page "<page-id>" --scale 2
```

Capture all service pages:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --screenshot "<validation-screenshot-dir>" --all-pages --scale 2
```

Do not add `--pid` to service commands.

Check service preview status:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --status
```

Close the service preview:

```bash
powerbi-report-author preview "<folder>" --host service --group "<workspace-guid>" --dataset "<semantic-model-guid>" --close
```

## Status and ambiguity

| Requested operation | Run `--status` first? |
|---|---|
| Selected-host open/attach | Yes |
| Selected-host reload | Yes |
| Selected-host screenshot | No |
| Selected-host status | No; status is the requested operation |

Before open/attach or reload, run `--status` against the same selected host,
report folder, service binding, and instance mode. Interpret the result under
*Unsaved host changes* and the selected host's current capabilities. Use
`--list-hosts` only before a host is selected. Status is a read-only preflight,
not a diagnostic follow-up to a failed selected-host operation.

- If the user says a matching preview is already running, still run the
  selected-host status preflight before open/attach or reload.
- Once the host and operation are selected, run no help, discovery, or
  alternative operation before the required status preflight and requested
  operation. Handle failures under the terminal rule above; never switch hosts
  or invoke a direct host CLI.
- If service context is incomplete, ask only for the missing workspace
  (`--group`) and/or semantic-model (`--dataset`) GUID. Run no command first.
- If no suitable host is available, report that fact rather than falling back
  to a direct host CLI.

## Preview lifecycle

Keep the lifecycle explicit:

1. **Load** the validated state into the selected host.
2. **Capture every affected page** and inspect screenshots plus structured
   diagnostics.
3. **Iterate** by editing, validating, and previewing again.
4. **For the service host only, display** a clean result in a visible service
   preview automatically. Run visible status, then visible open/attach; keep it
   open. Skip this step for Desktop; its workflow is unchanged.
5. **Accept** only after the requested result is approved.
6. **Commit locally** only after approval.
7. **Publish remotely** only when the user explicitly asks to publish, upload,
   push, or deploy the current local changes. Never publish or overwrite the
   remote report with local changes until the user explicitly gives permission.
   If the request does not ask to publish, or you are unsure, keep the changes
   local and do not publish.
8. **Discard** only on an explicit user request.
9. **Close** a headless service validation instance when no further iteration
   is expected. Do not close the final visible service preview. For a direct
   preview request, execute only the named operation and add `--close` only when
   explicitly requested. Leave Power BI Desktop open.

Service preview renders unpublished local PBIR layout changes against the
published semantic model's live data without publishing or persisting those
local edits. For an existing instance, run `--reload` before `--screenshot`;
screenshot capture alone does not re-read edited files. A screenshot request
does render before capture when it has to launch a fresh instance.

For authoring verification, run selected-host status, then open/attach or
reload, then screenshot as separate commands. If the selected host reports
unsaved changes and blocks loading the latest PBIR, a screenshot may document
the current host state but cannot validate the new edits; report screenshot
validation as blocked.

Apply the current host-specific status contract under *Unsaved host changes*.
Desktop open/attach leaves Desktop running after the command completes, and a
separately requested reload updates only the report definition.
`--reload-with-model` updates the report definition and requests
model-definition reload, but it does not refresh model data or prove freshness.
Screenshot results can be partial. Report every returned capture and failure
rather than flattening a partial result into success:

- **Partial envelope.** A partial capture still writes the success envelope with
  `status: "partial"` but exits non-zero, so a non-zero exit alongside
  `status: "partial"` marks a partial capture, not a total failure; keep and
  review the captures it returned.
- **Unknown-page `RENDER_FAILED`.** A per-page `RENDER_FAILED` whose message says
  the page id is unknown to the open window means the page exists on disk but not
  in the live window, usually because it was added after the last reload.
- **`bridgeCode` is optional, non-authoritative.** Some Desktop builds also set
  `details.bridgeCode` inside that failure's `error.details` rather than at the
  top of the error object, but its value varies by build — `"BRIDGE_ERROR"`,
  `"PageNotFound"`, or absent entirely. Never key the diagnosis on a particular
  `bridgeCode` value; read it only as a weak confirming detail. The
  authoritative signal is the `RENDER_FAILED` code plus the unknown-page id
  message above.
- **Distinct from `PAGE_NOT_FOUND`.** `PAGE_NOT_FOUND` is raised before capture
  when the requested page is absent from the report definition it resolved; a
  reload cannot conjure a page the definition does not contain.
- **Recovery is narrow.** That one self-explaining case, and only it, may be
  recovered, and only when recovery is already authorized — you initiated the
  capture inside your own edit-then-review loop, or the user asked you to handle
  the capture's result. The recovery is a new operation sequence run *after* the
  partial envelope returns, not a reload or status call chained onto or
  preceding the original screenshot request: it is the second of the two
  exceptions under *Desktop operation routing*, which still forbids fronting a
  screenshot with `--reload` or `--status`. Recover by running the
  unsaved-changes preflight, reloading, then recapturing only the pages that
  failed instead of rerunning the whole `--all-pages` batch — one `--page`
  capture per failed page, or the whole batch again only when the user asked for
  a verified complete set. When the user asked only for the capture and nothing
  further, do not substitute a reload, a status call or any other operation for
  it; report the partial, name the pages that failed and why, and stop. Any
  other per-page failure, and any `ok: false` failure envelope, stays terminal
  under the rule above.

### Unsaved host changes

A preview host may hold report edits in memory that are not yet represented in
the PBIR files on disk. Open/attach, report reload, or report-plus-model reload
can replace that host state with the disk definition, so every selected host
uses a status preflight before these operations. This is the canonical
statement of the safety gate; other files state it by reference rather than
restating it.

**Which operations it gates.** The gate applies to any selected-host
open/attach or reload that can re-read PBIR into a live instance. A request to
refresh is not authorization to discard unsaved edits. `--screenshot` is never
gated because it captures the host as it stands and replaces no state. Neither
is `--status` itself or `--list-hosts`.

Current Desktop status exposes unsaved state; current service preview is
read-only and does not. When service editing adds the same state, the common
rule below applies without changing the authoring workflow.

```bash
powerbi-report-author preview "<folder>" --host <desktop|service> [service binding] --status
```

```json
{"data":{"state":"ready","reports":[{"folder":"...","hostInstanceId":"12345"}],
 "details":{"hasUnsavedChanges":true}}}
```

Drive this read through `powerbi-report-author preview`. A host that supports
editing reports the selected instance's unsaved state at
`details.hasUnsavedChanges` (under `data`), resolved from the same report folder
and binding the operation will act on. Read it as follows:

- **`false`** — run the requested reload or bare `preview`.
- **Field not provided by a host that currently has no editing capability** —
  use the returned availability state to continue the requested open/attach or
  reload. This is the current service behavior.
- **Structured `HOST_UNAVAILABLE`** — run bare `preview` because no existing
  host instance can contain unsaved changes. Do not run reload; report the
  failure and stop.
- **`true`, `null`, a missing or non-boolean field, or any other failed status
  call from a host whose contract exposes unsaved state** — the safety gate
  failed. Report the failure and stop the requested open/reload. Do not
  reinterpret the result as `false`. For standalone preview requests, do not ask
  whether automatic open/reload should proceed anyway. During mandatory
  post-edit validation, only explicit boolean `true` uses the recovery below;
  missing, invalid, and failed reads remain terminal.

Boolean `false` permits either operation. Structured `HOST_UNAVAILABLE` permits
only open/attach.

**Mandatory post-edit validation recovery.** When a selected host reports
explicit boolean `true` and blocks the load required after agent-authored PBIR
edits, preserve the disk edits and do not finish the authoring task:

1. Do not run open/reload automatically, and do not use a stale warm-window
   screenshot as validation.
2. Ask the user to resolve the unsaved state manually in the selected host and
   confirm that the latest PBIR is loaded.
3. After confirmation, resume directly with screenshots of every affected page
   and review them. Do not rerun the PBIR edits, schema validation, status, or
   reload.
4. If the user does not complete the manual refresh, report schema validation
   as passed and screenshot validation as blocked.

This recovery applies only to mandatory validation initiated by an authoring
workflow. It does not authorize the agent to discard host changes, weaken the
gate for a direct open/reload request, or turn a standalone operation into a
multi-command workflow.

"Stop" here scopes to the reload, not to the whole task. A blocked reload does
not forbid `--screenshot`: a warm capture changes nothing and stays permitted,
though what it captures is the window as it stands, which may be stale relative
to disk. Say so when reporting the result. This applies only to a reload that
was never issued because the gate blocked it; a reload that ran and returned
`ok: false` is a host failure — report it and do not capture.

This read is a **read-only precondition on selected-host operations that re-read
PBIR into a live instance**, never a replacement for the operation itself and
never a license for any other diagnostic. Return to
`powerbi-report-author preview` for the operation itself.

`DESKTOP_UNSAVED_CHANGES` is declared in the preview error contract but no code
path emits it, so never wait for that error to signal unsaved work.

## Errors and fix/retry

| Error | Meaning | Code-specific correction |
|---|---|---|
| `HOST_UNAVAILABLE` | Requested host or matching live instance is unavailable | During the mandatory status preflight, proceed to plain open/attach when the result establishes that no matching Desktop instance exists; for reload, report the failure and stop. Before host selection, run `preview --list-hosts` when the host is unknown. After a selected Desktop operation, report that no match exists. When the message is "Several Power BI Desktop instances have this report open.", several windows hold the same report and `details.candidatePids` lists them: report the candidate pids and ask the user to close the others so exactly one window holds the report, then retry only after they confirm they have done so. Never close or kill a Desktop window yourself |
| `REPORT_NOT_PUBLISHED` | Required semantic model is unavailable or has no embed URL | Resolve or publish the model prerequisite only when explicitly authorized; never publish local report WIP as a preview side effect |
| `CAPABILITY_UNSUPPORTED` | Host lacks the requested capability | The capability does not exist on that host; report it rather than substituting another host or operation |
| `WORKSPACE_REQUIRED` | Service needs workspace context | Ask for the workspace GUID and pass it with `--group` |
| `INVALID_OPTION` | Required or supported arguments are wrong | For service, supply both `--group` and `--dataset` or correct the flagged option. For Desktop, parser text is not a correction |
| `AUTH_REQUIRED` | Service authentication is unavailable or expired | Report the authentication requirement |
| `PAGE_NOT_FOUND` | Requested page is unavailable | Correct the requested `--page` ID, reading the valid IDs from `preview-pages`, or omit it to capture the default page |
| `REPORT_PATH_INVALID` | Folder cannot resolve to the required report project | Ensure the owning `.pbip` exists before the initial command |
| `PARAMETER_FORMAT_INVALID` | A supplied option has an invalid format | Fix the flagged value to the `expected` shape — for example `--scale` must be an integer from 1 to 3 |
| `RENDER_FAILED` | Host could not render the request | Nothing in the command shape is at fault; report the host-side failure (a per-page `RENDER_FAILED` inside a partial capture is handled under *Preview lifecycle* above) |

Every row is subject to the terminal rule except the open/attach preflight
`HOST_UNAVAILABLE` case above: apply a supplied `correction` object to that same
operation and retry once; without one, report the failure and stop with no
further tool call. Never insert validation or another lifecycle command.
The multi-instance `HOST_UNAVAILABLE` retry is user-mediated: the user changes
the environment, not the command, so it is not a retry under the terminal rule.
Review successful images with screenshot-review.md (see `screenshot-review.md`).
