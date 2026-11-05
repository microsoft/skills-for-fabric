# Troubleshooting

| Situation | Handling |
| --- | --- |
| Task status is failed | Read `runDetails.errorMessage` and report it with task/run identifiers. |
| `POST /messages` returns 204 | This is expected for deployed routes; do not parse a body. |
| `POST /messages` returns 500 | OneLake may be inaccessible or the Lakehouse is unreachable. Refresh the MWC token, verify workspace/Lakehouse IDs, and retry. |
| `POST /run` returns 411 | Retry with `Content-Length: 0` or an explicit empty body. |
| `POST /run` returns 409 | Read status and messages once before deciding. If the task is `Running` or acquiring a new run, treat it as already in flight; otherwise report that the task is in a state that cannot be run. |
| `POST /run` returns 400 with instruction error | The task was created without `instruction`; re-`PUT` the task with the full instruction. |
| Running with no session ID | This can be valid during Spark session acquisition, not proof of failure. Report the observed state and return control to the user; do not wait for a session ID before showing the run card and controls. |
| Agent looks stuck in a loop / repeats discovery | Expected: Osmos runs many experiments and revisits steps to converge on the best one, so it takes time and progress can look repetitive. Do not assume it is looping; do not cancel or re-run. Use a bounded status/message check to relay service evidence, then return control to the user. |
| Workspace has no current capacity assignment | Stop execution and verify the workspace assignment. Unknown-eligibility acknowledgment cannot override a missing assignment. Preserve saved task/route state; do not provision or relocate anything automatically. |
| Capacity SKU is unavailable or metadata cannot be read | In production, explain unknown eligibility and the verification/acknowledgment flow in `capacity-preflight.md` from the skill index. On another target, a metadata access/network failure stops until resolved; do not apply production policy or infer trial/supported status. Never automatically provision or relocate anything. |
| Confirmed public trial (`FTL64`) | Stop before task mutations. Select eligible supported capacity or contact the workspace/capacity administrator. Preserve the failed task and read-only inspection. |
| Canonical `/tasks` returns 404 | Verify the selected context and report the error. Do not silently switch environments or recreate a task. |
| `generatemwctoken` returns `HTTP 403` with an empty body | The current Azure CLI session may be in the wrong tenant. Ask for the workspace's resource tenant ID only now, then run `az login --tenant <resource-tenant-id> --allow-no-subscriptions` and retry token acquisition with the same tenant override. |
| `generatemwctoken` returns `HTTP 403` with `Tenant not authorized for cluster` | Run `scripts/resolve-auth-and-routing.py` or `scripts/resolve-auth-and-routing.ps1`. The helper reads the routed home cluster from Fabric response headers and retries token exchange there. Do not hand-edit hosts, workload types, token audiences, or capacity SKUs. |


## Generic Spark statement failure

This error is not proof of a transient or a timeout:

```text
Run failed while executing statements on the Spark session. Please retry.
```

It can hide downstream authorization or capacity eligibility failures. Preserve
the error and recovery state; do not guess the cause or automatically retry.

Before retrying:

1. Fetch `GET /{taskId}/messages` and `GET /{taskId}`.
2. If the task is already `Running` or acquiring a session, do not issue another run.
3. Check the selected target's eligibility policy and available failure evidence. A confirmed production trial block or a service authorization rejection is not retryable until resolved; a trial SKU on another target is not itself a block. If the underlying cause remains unknown, report it and ask before any resumed execution.
4. Only for an authorized retry after the cause is addressed, refresh the MWC token for the same workspace, Lakehouse, and environment, repeat execution preflight, then call `POST /{taskId}/run` once on the same task ID.
5. Treat HTTP 409 as success only when the follow-up task read shows a run is already in flight.
6. If the same operation/error signature fails again, report the failure instead of creating a new task or retry loop.

## MWC token expiry mid-run

The MWC token typically expires after about 1.5 hours. When a task API call returns an auth-class response:

1. Re-run `scripts/resolve-auth-and-routing.py` or `scripts/resolve-auth-and-routing.ps1` for the same selected target, workspace, Lakehouse and resource tenant using the usual output directory or `--existing-routing` / `-ExistingRouting`. For read-only status/messages use `--purpose inspect` / `-Purpose inspect`.
2. Use the refreshed token file and `TASKS_BASE`, retaining the exact saved `/tasks` or `/aichat` alias; both address the same tasks.
3. Retry the failed request once against the same task ID.
4. Never print or persist the bearer or MWC token in conversation output.
