# Task page URL construction

Use this flow after every task starts. All users receive the Fabric task link;
no workspace or tenant enrollment signal is required.

Run `scripts/launch-task-page.py`; do not reimplement the URL or browser logic
inline. When a Fabric page or Lakehouse URL is available, pass it as
`--source-url` so the helper preserves the environment and all unowned query
tokens while replacing the task selection. Without a source URL, production
uses `https://app.fabric.microsoft.com`; private environments must pass a
trusted `--portal-base-url` instead of guessing a host. Production accepts only
the supported HTTPS public portal hosts (default port or 443), without URL
credentials. Private source/base URLs must already have been validated against
the active environment's trusted portal context by the caller.
Pass the environment token from routing, not a guessed label. Production
spelling is case-insensitive; `production` is also normalized to `prod`.

```text
<scheme>://<netloc>/groups/<workspace_id>/lakehouses/<lakehouse_id>?<query>
```

`<query>` is the original pasted query string, transformed as follows:

- **Swap `selectedPath`** - remove any existing `selectedPath=...` and
  append `selectedPath=ProjectOsmos%2F<task-id>`. This is the only
  per-task change (percent-encode the slash as `%2F`).
- **Force `projectOsmosUX=1`** - replace any existing `projectOsmosUX`
  value and add it if absent, so the Lakehouse task page renders.
- **Preserve everything else verbatim** - keep each remaining parameter
  exactly as pasted (`experience=power-bi`, other
  flags). Do **not** decode/re-encode values; a round-trip through a
  query parser could re-encode already-encoded
  slashes and can change the URL the user relies on.

Rebuild the path from the validated `workspace_id` / `lakehouse_id` so any
table or sub-path in the pasted URL (e.g. `/tables/Invoice`) is dropped,
and preserve the original scheme and netloc.

Print `task_page_url` as `Task page` in the run card and surface it in chat.
The helper attempts to open it in the default browser unless `--no-open` is
needed. Browser opening is bounded to three seconds; a failed or timed-out
launch is non-fatal: print the warning
and URL and continue bounded task monitoring. The Fabric link is
the only browser target; no local HTML fallback is created or opened.
Opening is best-effort: the timeout bounds the helper's wait and stops its
direct browser controller, not every descendant an OS or custom launcher may
start. The helper does not manage the browser's process tree.
The browser subprocess environment excludes `MWC_TOKEN`, `PBI_TOKEN`, and
`BEARER` (case-insensitively), while retaining normal settings such as `BROWSER`
and `DISPLAY`. The caller's environment is unchanged.
If URL validation fails (exit 2), report the error and task ID, leave
`task_page_url` unset, and continue bounded task monitoring anyway. Correct the portal
context and rerun this helper for the same task; never recreate the task or
substitute a production host for missing private context.

Use `PYTHON_RUNNER` selected by the Python helper runtime reference linked
directly from `SKILL.md`. Run from the loaded skill directory:

```bash
"${PYTHON_RUNNER[@]}" scripts/launch-task-page.py \
  --environment prod \
  --workspace-id <workspace-id> \
  --lakehouse-id <lakehouse-id> \
  --task-id <task-id> \
  --source-url <optional-fabric-page-or-lakehouse-url>
```

The JSON response contains `task_page_url`, a non-fatal `warning`, and one
structured `telemetry` object. The telemetry includes CLI origin, task-created
state, launch result, fallback use, workspace ID, task ID,
and environment. It never includes prompt or instruction content.
The object is local structured output, not an automatic telemetry upload.
`--no-open` reports `not_attempted`, without a failure warning or fallback.
