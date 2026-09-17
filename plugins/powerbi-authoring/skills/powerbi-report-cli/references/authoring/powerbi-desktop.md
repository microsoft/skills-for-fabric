# Power BI Desktop Verification

> Read this when you need to open Power BI Desktop, reload a PBIP/PBIR report,
> capture screenshots, choose a Desktop PID, or interpret `powerbi-desktop` CLI
> output. This file is the detailed runbook; `SKILL.md` keeps the short command
> loop because visual verification is a critical report-authoring step.

## Core Rule

For PBIR edits that affect rendered output, do not rely on JSON validation alone.
Power BI Desktop can reject or visually misrender definitions that are
structurally valid. Use this loop:

1. Edit PBIR files.
2. Run `powerbi-report-author validate "<path-to-.Report-dir>"`.
3. Run `powerbi-desktop status`.
4. Select the intended Desktop instance by PID.
5. Run `powerbi-desktop reload --pid <pid>` for PBIP/PBIR current files. This
   workflow is for report-definition changes. For semantic model/TMDL changes,
   use the semantic-model skill or Modeling MCP workflow and reopen the PBIP if
   model changes are not reflected.
6. Capture screenshots from the same PID.
7. Review screenshots; if anything is wrong, fix PBIR and restart at validation.

## Command Reference

### Setup

Ensure the latest Desktop Bridge CLI is installed globally:

```bash
npm install -g @microsoft/powerbi-desktop-bridge-cli@latest
powerbi-desktop --version
```

### Commands

```bash
powerbi-desktop open "<path.pbip>"
powerbi-desktop status
powerbi-desktop manifest --pid <pid>
powerbi-desktop reload --pid <pid>
powerbi-desktop screenshot <page-id> --pid <pid> --output screenshots/page.png
powerbi-desktop screenshot-all --pid <pid> --output-dir screenshots
```

`open <path>` is the only command that accepts a PBIP/PBIX path. Other commands
target a running Desktop Bridge instance. If exactly one instance is available,
`--pid` may be omitted, but passing the PID is safer and should be preferred in
agent workflows.

No command accepts `--report`. The same PBIP can be open in multiple Desktop
processes, so report path is not a safe selector. Use `status` and choose by PID.

`screenshot <page-id>` takes the PBIR page ID such as `ReportSection1a2b3c`, not the
display name shown in Desktop.

Screenshots default to scale `2` for readable visual review. Pass `--scale 1`
only when you need smaller files or faster captures; pass `--scale 3` only when
you need extra detail and can tolerate larger PNGs.

## Status and PID Selection

Run:

```bash
powerbi-desktop status
```

Use the returned `instances[]` list to choose the PID. Prefer an instance where:

- `bridgeStatus` is `connected`.
- `currentFilePath` matches the target PBIP/PBIX.
- `reportDir` resolves to the expected `.Report` folder for PBIP/PBIR reports.
- `diagnostics` is empty or only contains non-blocking warnings.

If multiple instances are present, never guess. Choose the PID from `status` and
reuse that same PID for `reload`, `screenshot`, and `screenshot-all`.

## Open and Reload

To start Desktop:

```bash
powerbi-desktop open "C:\Reports\Sales\Sales.pbip"
powerbi-desktop status
```

After editing PBIR files:

```bash
powerbi-report-author validate "C:\Reports\Sales\Sales.Report"
powerbi-desktop reload --pid <bridge-pid-from-status>
```

Reload is supported for the selected Desktop instance's current PBIP/PBIR file.
It is intended for report definition changes, not semantic model authoring. If
you changed TMDL/model files, use the semantic-model skill or Modeling MCP
workflow and reopen the PBIP if model changes are not reflected. `reload` is
supported only for PBIP-backed reports; if the selected PID has only a `.pbix`
open, `reload` returns `REPORT_DIR_REQUIRED`. If `reload` returns
`REPORT_DIR_REQUIRED`, choose a PID whose `status` output has a PBIP/PBIR
`currentFilePath` and resolved `reportDir`, or open the target PBIP first.

**Exception — theme JSON cache:** When editing an existing theme JSON file,
Desktop may not pick up the change on reload because theme files are cache-keyed
by file name. Either rename the theme file with a small random suffix and update
its registration in `report.json`, or close and reopen Desktop.

Fix all validation errors before reloading. Reloading invalid PBIR will usually
surface Desktop errors and can leave the report in a broken visual state until
the files are fixed and reloaded again.

## Screenshots

> **Capture scope:** Each screenshot captures the report page **AND** the right-hand filter pane (`outspacePane`) when the filter pane is enabled and expanded. Filter pane and filter card (`filterCard`) chrome are formattable PBIR surfaces — verify them alongside the on-page visuals.

Capture one page when the change is isolated:

```bash
powerbi-desktop screenshot ReportSection1a2b3c --pid <bridge-pid-from-status> --output screenshots/sales.png
```

Capture all pages when the change affects theme, shared formatting, page order,
navigation, or report-wide behavior:

```bash
powerbi-desktop screenshot-all --pid <bridge-pid-from-status> --output-dir screenshots
```

Run reload and screenshot operations serially for a given PID — never in
parallel against the same PID, even as a workaround for a slow or retryable
error. Discovery commands such as `status` and `manifest` are safe to run
concurrently. Parallel reload/screenshot calls produce `Cancelled` and slow
recovery.

Review screenshots for:

- visual error banners, blank visuals, or "Requires X fields" messages;
- clipped card/KPI values, truncated labels, hidden legends, or overlap;
- theme/background/font colors that do not match the requested design;
- insufficient contrast or indistinguishable chart series;
- slicers with no selectable values;
- unexpected blank/null values.

For non-trivial visual changes, use an independent review pass or sub-agent with
the screenshot paths, the expected outcome, and the checklist above.

## Common Outcomes

| Output/error | Meaning | Action |
|--------------|---------|--------|
| `"status": "not_connected"` | No Desktop Bridge instance is discoverable | Open the report with `powerbi-desktop open "<path.pbip>"` or ask the user to start Desktop |
| `NO_BRIDGE` or repeated `connect ENOENT \\.\pipe\pbi-desktop-bridge-<pid>` | Desktop is running, but the bridge pipe is not available | In Desktop, open **File > Options and settings > Options > Preview features**, enable **Enable external tool access to Power BI Desktop through secure local APIs**, restart Desktop, then retry `powerbi-desktop status --wait-seconds 30`. If the bridge is still unavailable, share [Power BI report authoring docs](https://aka.ms/Report_Authoring_skill_LearnDocs) for the current Desktop support story |
| `AMBIGUOUS_DESKTOP_INSTANCE` | More than one bridge instance is available | Run `powerbi-desktop status`, choose the intended PID, and retry with `--pid` |
| `METHOD_NOT_AVAILABLE` | Desktop build lacks a required production bridge method | Tell the user Desktop is stale/unsupported for this workflow and link [Power BI report authoring docs](https://aka.ms/Report_Authoring_skill_LearnDocs) for current support constraints |
| `HostNotReady` or retryable bridge error | Desktop is up but the report host isn't ready for this request yet (often a brief moment right after a reload) | The CLI auto-retries this; you usually won't see it. If you do, rerun the same command once — the host has typically settled. Do not add custom sleeps in agent code; rely on the CLI's retry path. |
| `Timeout` (bridge error) | A reload or screenshot attempt took longer than the CLI's retry budget allowed | Run `powerbi-desktop status` and confirm `bridgeStatus: "connected"`. If connected, rerun the same command once — a transient slow operation usually clears on the next attempt. If `Timeout` persists across two reruns, the report or model is genuinely slow on this machine: rerun with a larger budget, e.g. `powerbi-desktop reload --pid <pid> --wait-seconds 120`. If `status` shows `bridgeStatus: "error"` or stops responding, ask the user whether a Desktop modal dialog is blocking input. |
| `Cancelled` during screenshot/reload | A reload or screenshot was cancelled, usually because another reload/screenshot ran against the same PID concurrently. Distinct from `Timeout` (which means the operation ran too long) | Make sure you are running reload and screenshot serially per PID. Run `status`, wait for `bridgeStatus: "connected"`, then retry one operation at a time. |
| `ReportDefinitionValidationFailed` | Desktop rejected the PBIR definition | Fix PBIR, run `powerbi-report-author validate <path>`, then reload again |
| `REPORT_DIR_REQUIRED` | Selected PID does not expose a PBIP/PBIR current file; reload and screenshot-all need PBIP/PBIR state | Select the correct PID from `status` or open the target PBIP |
| Page not found / empty page screenshot | `<page-id>` used a display name or stale page ID | Read `definition/pages/pages.json` and retry with the PBIR page ID |

## Fix-Retry Pattern

When Desktop reports a load or render error:

1. Read the CLI error and Desktop diagnostic details.
2. Open the referenced PBIR JSON file and fix the offending property, visual, or
   page definition.
3. Run `powerbi-report-author validate <path-to-.Report-dir>`.
4. Run `powerbi-desktop reload --pid <same-pid>`.
5. Capture screenshots again from the same PID.

Do not switch PIDs mid-loop unless `status` shows the original Desktop instance
closed or the user explicitly asks you to verify a different Desktop process.
