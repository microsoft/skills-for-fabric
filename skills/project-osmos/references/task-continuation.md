# Task continuation

Continue a user-authored follow-up on the same task ID. Never rerun intake or create a replacement task.

Only continue an approval request when the reconciled `Approval gates` field lists that gate. `fail if target already populated` is a terminal policy, not an approval gate.

## Ordered helper flow

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

The helper:

1. Verifies `--base-url` exactly matches `tasks_base` in the `routing.json`
   beside the token file before reading the token.
2. Reads live task status.
3. Posts the complete user message first.
4. Reads live status again after the post.
5. Avoids `/run` when a run is active.
6. Calls `/run` exactly once when the task is not running.

If status lookup or message post fails, no run starts. If `/run` returns HTTP 409, the helper reads status once and accepts the conflict only when the same task is now Running. It never sends a second run request.

The JSON result reports before/after status, whether the message posted, whether run start was attempted, whether a run started or is active, and the run-start outcome. Surface any failure explicitly.
