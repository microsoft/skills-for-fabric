# Task lifecycle

For live operations, use after resolving `TASKS_BASE` and a fresh MWC token. Offline plans use supplied routing and hypothetical responses without acquiring a token or inspecting authentication/helper implementations. Outbound roles and statuses use strings; inbound reads accept string, numeric, and stringified-numeric values.

`TASKS_BASE` ends in `/tasks` for new routes. `/aichat` addresses the same tasks;
either alias may reference the original task without migration. Preserve task/message
IDs, recovery state, and the selected tenant, capacity, workspace, Lakehouse, and environment.
After auth refresh, use `TASKS_BASE` from the current `routing.json`; never
reconstruct it in another environment.
Apply the active environment's execution policy immediately before any create,
update, user-message submission, or run. The bundled resolver checks the selected
target's assignment; production also requires the SKU policy in `capacity-preflight.md`
from the skill index. Service endpoints enforce eligibility on other targets.
Inspection/listing, cancellation, and deletion do not require
execution eligibility; their confirmation gates still apply.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| PUT | `/{taskId}` | create or update task |
| GET | `/{taskId}` | read status and run details |
| DELETE | `/{taskId}` | permanently delete task |
| GET | *(collection base, no suffix)* | list tasks for the Lakehouse |
| POST | `/{taskId}/messages` | add user message |
| GET | `/{taskId}/messages` | read conversation and progress |
| POST | `/{taskId}/run` | start or continue a run |
| POST | `/{taskId}/cancel` | cancel current run |

## Local-agent task controls

Immediately after a successful start or resume response from `POST /{taskId}/run`,
show the complete run card and control notice from step 8 of `SKILL.md` together
in chat, before performing further task operations or acting on user follow-ups.
If a follow-up arrives first, show the handoff, then act on the request.
Use an interim/commentary response rather than waiting for a final answer.
Browser-launch failure does not suppress the notice;
task creation alone or a blocked/failed start does not justify it.

Interpret controls in the existing Osmos task context, never as local background-agent
commands. Select the existing task and routing context from the conversation or
saved recovery state; ask the user to confirm when missing or ambiguous.

- `Ask Osmos to <instruction>` sends the complete requested instruction to the same task using `task-continuation.md`; do not cancel its active run or create a replacement.
- `Cancel` is the pause control: it stops the current run while retaining the task and history, subject to the confirmation below. It does not undo completed work.
- `Resume` uses the same task ID, instruction, environment, and recovery state; do not post a message. Read live status first: if Running, report the active run without another `/run`; if Cancelling, wait for cancellation to finish before resuming. Completed is not a no-op when the user explicitly requests Resume. For Completed or another resumable non-active status, refresh authentication in the same context, apply that environment's execution policy (including production capacity preflight), then submit one empty-body `POST /{taskId}/run`. An offline dry-run plans the same requests without executing them or changing saved state. Surface failures rather than automatically retrying.
- Delete requests follow the irreversible-deletion gate below.
- Feedback is a user-initiated email link. Do not send email automatically or attach task data, credentials, or operational identifiers.

## Cancel and delete gates

Delete is unrecoverable. Warn the user and require exact task ID re-entry before `DELETE`. A mismatch means no call.

Cancel stops only the current run. Explain that task history remains and ask for yes/no confirmation. Call `/cancel` only after explicit yes; do not require ID re-entry.

## Create task

Generate one task UUID. The service rejects `instruction` over 10,000 characters. Measure the complete handoff and use `oversized-instructions.md` before `PUT` when needed. The create `instruction` and initial user message must be identical.

```bash
TASK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
curl -s -X PUT "$TASKS_BASE/$TASK_ID" \
  -H "Authorization: mwctoken $MWC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"displayName":"Task description","instruction":"Full composed handoff"}'
```

If `/run` later returns an instruction error, the create request omitted or corrupted the handoff.

## Initial user message

Use a unique message UUID, UTC timestamp, string role `User`, and the exact composed handoff. Flat metadata is supported:

```json
{
  "messages": [{
    "id": "message-uuid",
    "role": "User",
    "content": "Full composed handoff",
    "timestamp": "ISO-8601",
    "metadata": {
      "author_name": "user@contoso.com",
      "author_source": "copilot-cli"
    }
  }]
}
```

Nested metadata objects are rejected by deployed SparkCore-direct routes. Success may be `204 No Content`.

## Start run

```bash
curl -s -X POST "$TASKS_BASE/$TASK_ID/run" \
  -H "Authorization: mwctoken $MWC_TOKEN" \
  -H 'Content-Length: 0'
```

An explicit empty body avoids `411 Length Required`.
