# `powerbi-report-author` CLI Reference - Part 2

## Contents

- [Fallback: the `powerbi-desktop` bridge CLI](#fallback-the-powerbi-desktop-bridge-cli)

Continuation of `powerbi-report-author-cli.md`. Open this file directly from
the skill reference index.

## Fallback: the `powerbi-desktop` bridge CLI

Two different CLIs drive Power BI Desktop, and their names are easy to confuse:

| | Package | Command | Role |
|---|---|---|---|
| Primary | `@microsoft/powerbi-report-authoring-cli` | `powerbi-report-author` | `preview --host desktop` — every Desktop operation |
| Direct | `@microsoft/powerbi-desktop-bridge-cli` | `powerbi-desktop` | direct Desktop Bridge automation |

The bridge is not a legacy surface: `powerbi-report-author` depends on it and
every Desktop preview operation already runs through it. What differs is the
level. `preview --host desktop` is the authored, guard-railed surface; the
`powerbi-desktop` CLI exposes the same bridge raw. If you are choosing between
them, you want `powerbi-report-author`.

This section is the **only** skill guidance that should use the
`powerbi-desktop` surface directly. Use it only when
`powerbi-report-author preview` cannot complete the task at all: a capability no
preview host exposes, or bridge-level `status`/`manifest` detail you need to
understand what Desktop is doing. A preview command that failed terminally is
not such a case — that is terminal, not a licence to switch surfaces. Neither is
several windows holding the same report, which `preview` reports with
`details.candidatePids` for the user to resolve.

Say which preview command fell short and why, and return to
`powerbi-report-author preview` for everything else. Do not install
or use it as the primary path.

Install only when the fallback is needed:

```bash
npm install -g @microsoft/powerbi-desktop-bridge-cli@beta
powerbi-desktop --version
```

Bridge commands — the read-only diagnostics first; the mutating forms below them
are documented for recognition, not as a way around a preview failure:

```bash
powerbi-desktop status
powerbi-desktop status --pid <pid>
powerbi-desktop manifest --pid <pid>
powerbi-desktop open "<path.pbip>"
powerbi-desktop reload --pid <pid>
powerbi-desktop screenshot <page-id> --pid <pid> --output "<validation-screenshot-dir>\page.png"
powerbi-desktop screenshot-all --pid <pid> --output-dir "<validation-screenshot-dir>"
```

The unsaved-changes gate never needs the bridge. Run
`powerbi-report-author preview <folder> --host <desktop|service> [service
binding] --status` before selected-host open/attach or reload. Current Desktop
status must report `details.hasUnsavedChanges` as explicit boolean `false`
before either operation; current service status has no unsaved-state field, so
its availability result controls the operation. Structured `HOST_UNAVAILABLE`
permits open/attach because no matching live instance can contain unsaved
changes; it is terminal for reload. An explicit boolean `true` blocks automatic
open/reload on any host. Never run this status preflight before a screenshot.
Full rule is in preview.md (see `preview.md`). Do not use
`powerbi-desktop reload --pid` or `screenshot --pid` to work around a preview
failure or the gate.
