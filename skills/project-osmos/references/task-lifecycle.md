# Task lifecycle

Use after resolving `TASKS_BASE` and a fresh MWC token. Outbound roles and statuses use strings; inbound reads accept string, numeric, and stringified-numeric values.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| PUT | `/{taskId}` | create or update task |
| GET | `/{taskId}` | read status and run details |
| DELETE | `/{taskId}` | permanently delete task |
| GET | `/` | list tasks for the Lakehouse |
| POST | `/{taskId}/messages` | add user message |
| GET | `/{taskId}/messages` | read conversation and progress |
| POST | `/{taskId}/run` | start or continue a run |
| POST | `/{taskId}/cancel` | cancel current run |

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
