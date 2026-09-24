# Task monitoring

Use bounded task and message API reads to report Project Osmos progress. Do not create a local dashboard or background poller.

## Progress check

1. Fetch `GET /{taskId}/messages`.
2. Relay unseen assistant messages, deduplicated by message ID.
3. Fetch `GET /{taskId}`.
4. Report current status and `runDetails`.
5. Return control to the user.

Task status alone is not progress. Accept assistant role values `Assistant`, `1`, and `"1"` on inbound reads.

## Status normalization

Canonical status values are Created, Running, Cancelling, Cancelled, Completed, and Failed. Deployed routes may return `0`–`5` as numbers or strings. Use `scripts/task_status.py`.

Treat `runDetails.completedAt` or `runDetails.errorMessage` as terminal evidence even when the nominal status is Running.

Running with a null session ID can be valid during Spark acquisition. Do not declare failure only because `sessionId` is temporarily absent.

## Repetition versus elicitation loops

Repeated experiments, discovery, and validation can be normal. Repeated equivalent clarification questions are not progress.

If the same question intent appears three times without intervening non-elicitation assistant progress:

- stop forwarding repeated answers;
- identify the repeated question;
- name the conflicting or missing handoff fields;
- report a handoff-contract failure;
- do not restart, auto-answer, or create another task.

## Retryable Spark transient

For `Run failed while executing statements on the Spark session. Please retry.`, read messages and status first. If no run is active, refresh authentication and call `/run` once on the same task ID. A repeated identical failure is terminal; do not loop.

## Response fields

Report task ID, workspace ID/name, default Lakehouse ID/name, status, operation ID, session ID when present, start/completion timestamps, and error message. Never invent missing values.

Include the Fabric task link when the user needs to view progress. Continue
conversation and control operations through the CLI task APIs, not browser automation.
