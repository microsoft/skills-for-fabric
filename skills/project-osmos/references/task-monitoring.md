# Task monitoring

Use bounded task and message API reads to report Project Osmos progress, then return control to the user.

## Progress check

1. Fetch `GET /{taskId}/messages`.
2. Relay unseen assistant messages, deduplicated by message ID.
3. Fetch `GET /{taskId}`.
4. Report current status and `runDetails`.
5. Return control to the user.

Ground progress reports in task messages as well as status. Treat role values `Assistant`, `1`, and `"1"`
as assistant messages on inbound reads; canonical roles are
`User`, `Assistant`, and `System`. Deduplicate using original message IDs.
Use the saved route for read-only inspection, including legacy `/aichat`; trial
or unknown eligibility must not prevent these reads.

## Status normalization

Canonical status values are Created, Running, Cancelling, Cancelled, Completed, and Failed.
Numeric values `0`–`5` (including stringified numbers) map to those states in that order.
Python integrations can import the normalization helpers from `scripts/task_status.py`;
it is a library module, not a standalone command.

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

## Spark failure diagnosis

`Run failed while executing statements on the Spark session. Please retry.` is
lossy and can hide a nontransient eligibility rejection. Read messages/status
and follow `troubleshooting.md` from the skill reference index; do not automatically resume.

## Response fields

Report task ID, workspace ID/name, default Lakehouse ID/name, status, operation ID, session ID when present, start/completion timestamps, and error message. Never invent missing values.

Include the Fabric task link when the user needs to view progress. Continue
conversation and control operations through the CLI task APIs, not browser automation.
