# Troubleshooting

| Situation | Handling |
| --- | --- |
| Task status is failed | Read `runDetails.errorMessage` and report it with task/run identifiers. |
| `POST /messages` returns 204 | This is expected for deployed routes; do not parse a body. |
| `POST /messages` returns 500 | OneLake may be inaccessible or the Lakehouse is unreachable. Refresh the MWC token, verify workspace/Lakehouse IDs, and retry. |
| `POST /run` returns 411 | Retry with `Content-Length: 0` or an explicit empty body. |
| `POST /run` returns 409 | Poll status and messages before deciding. If the task is `Running` or acquiring a new run, treat it as already in flight; otherwise report that the task is in a state that cannot be run. |
| `POST /run` returns 400 with instruction error | The task was created without `instruction`; re-`PUT` the task with the full instruction. |
| Running with no session ID | This can be valid during Spark session acquisition. Continue polling. |
| Agent looks stuck in a loop / repeats discovery | Expected: Osmos runs many experiments and revisits steps to converge on the best one, so it takes time and progress can look repetitive. Do not assume it is looping; do not cancel or re-run. Keep polling and relay progress. |
| Workspace has no capacity | Stop and ask the user to assign/provision Fabric capacity before creating or running a task. |
| `generatemwctoken` returns `HTTP 403` with an empty body | The current Azure CLI session may be in the wrong tenant. Ask for the workspace's resource tenant ID only now, then run `az login --tenant <resource-tenant-id> --allow-no-subscriptions` and retry token acquisition with the same tenant override. |
| `generatemwctoken` returns `HTTP 403` with `Tenant not authorized for cluster` | Run `scripts/resolve-auth-and-routing.py` or `scripts/resolve-auth-and-routing.ps1`. The helper reads the routed home cluster from Fabric response headers and retries token exchange there. Do not hand-edit hosts, workload types, token audiences, or capacity SKUs. |


## Retryable Spark statement timeout

This exact error message marks the documented retryable transient:

```text
Run failed while executing statements on the Spark session. Please retry.
```

Treat it as a Spark statement/token timeout limitation for long-running Project Osmos tasks, not a user-code failure. The orchestrator checkpoints `agent_state.json` after each completed search step and re-hydrates that partial state on retry, so re-running the same task resumes from the last persisted step.

Before retrying:

1. Fetch `GET /{taskId}/messages` and `GET /{taskId}`.
2. If the task is already `Running` or acquiring a session, do not issue another run.
3. If the run failed with the exact transient above, refresh the MWC token with the auth helper and call `POST /{taskId}/run` once on the same task ID.
4. Treat HTTP 409 as success only when the follow-up task read shows a run is already in flight.
5. If the same operation/error signature fails again, report the failure instead of creating a new task or retry loop.

## MWC token expiry mid-run

The MWC token typically expires after about 1.5 hours. When a task API call returns an auth-class response:

1. Re-run `scripts/resolve-auth-and-routing.py` or `scripts/resolve-auth-and-routing.ps1` for the same workspace and Lakehouse.
2. Use the refreshed token file and unchanged `TASKS_BASE`.
3. Retry the failed request once against the same task ID.
4. Never print or persist the bearer or MWC token in conversation output.
