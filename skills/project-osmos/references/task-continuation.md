# Task continuation

Continue a user-authored follow-up on the same task ID. Never rerun intake or create a replacement task.

`Ask Osmos to <instruction>` is a local-agent follow-up request. Forward the
requested instruction in full through the ordered flow below; do not interpret
"interrupt" as permission to cancel the active run. Explicit `Cancel` and `Resume`
requests use the controls and confirmation gates in `task-lifecycle.md`.

Only continue an approval request when the reconciled `Approval gates` field lists that gate. `fail if target already populated` is a terminal policy, not an approval gate.

## Command-line flow

On non-Windows systems, restrict the token file to its owner (for example,
`chmod 600 "$TOKEN_FILE"`); the continuation helper rejects any group/other
permissions on the opened file before reading it. Windows retains its existing
file-access behavior without a POSIX mode check.

```bash
"${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/post-user-message.py \
  --base-url "$TASKS_BASE" \
  --task-id "$TASK_ID" \
  --token-file "$TOKEN_FILE" \
  --message "$FOLLOW_UP" \
  --auth-scheme "mwctoken" \
  --output json
```

The command-line helper:

1. Verifies `--base-url` exactly matches `tasks_base` in the `routing.json`
   beside the token file before reading the token. Both canonical `/tasks` and
   legacy `/aichat` are accepted; both address the same task IDs.
   Validates saved resource/environment context before any task request.
   Rechecks the selected target's current workspace capacity assignment.
   Only production also probes SKU metadata and applies trial/unknown policy;
   other targets rely on service eligibility (see `capacity-preflight.md`).
2. Reads live task status.
3. Posts the complete user message first.
4. Reads live status again after the post.
5. Avoids `/run` when a run is active.
6. Calls `/run` exactly once when the task is not running.

If status lookup or message post fails, no run starts. If `/run` returns HTTP 409, the helper reads status once and accepts the conflict only when the same task is now Running. It never sends a second run request.

The JSON result reports before/after status, whether the message posted, whether run start was attempted, whether a run started or is active, and the run-start outcome. Surface any failure explicitly.

Unknown production SKU eligibility pauses execution unless the user explicitly
acknowledges it for this invocation; only then add `--allow-unknown-capacity`.
Confirmed public trial cannot be overridden. Read-only inspection does not invoke this helper and remains available
when execution is blocked.

The same CLI accepts saved routing from earlier installations.
Nonproduction Fabric targets remain supported; untrusted non-Fabric hosts do not.
It validates matching API/portal origins, trusted workload origins
and the exact resource-derived task base before token access. The bundled
resolver rechecks the selected target's capacity assignment before execution;
only production also applies the production SKU policy. Service endpoints
enforce authorization and eligibility on other targets. Do not infer permission
from a pasted URL or workload-host naming convention. This read-only preflight
does not rewrite saved routing, tokens or recovery files.

The built-in HTTP transport refuses redirects instead of forwarding
authorization or substituting a route. A redirect fails the operation; preserve
the original task context and inspect its state before retrying.

If the message transport fails without confirming submission, the outcome is
unknown: retain the emitted message ID and inspect messages before retrying.
If message posting succeeded but a later step failed, the error retains that ID
and reports the confirmed post; inspect status/messages before taking further
action and do not repost the same message with a fresh ID.
Refresh authentication for the same workspace,
Lakehouse, and environment; keep `.dataprojects` task/recovery files intact.

## Shared continuation function

`continue_task()` in `scripts/post-user-message.py` posts a follow-up message;
ordinary `Resume` uses the empty-body `/run` flow in `task-lifecycle.md` instead.
The function is environment-neutral. Its required `preflight` callback runs
before any task request or message ID is generated. The CLI checks workspace
assignment on every selected target and SKU policy only on production;
other callers supply their own execution policy.

Select the existing task and routing context from the conversation or saved
recovery state; ask the user to confirm if ambiguous. Refresh authentication in
that same context, without replacing the task or inventing missing metadata.
The shared function does not require a tenant field in saved routing.
Use `read_private_token_file()` for file-backed tokens; never log tokens.

Optional `request` replaces the HTTP helper for every task call, including
conflict lookups. It uses the helper's signature and returns `HttpResult`.
Custom transports own required headers and redirect policy; surface failures
without transport or route fallback. Normal CLI usage needs no custom transport.

Reuse `ContinuationResult` and `ContinuationError`, preserve emitted message IDs,
and follow the lifecycle confirmation and successful-start/resume notice requirements.
