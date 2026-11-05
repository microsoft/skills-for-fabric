# Capacity preflight

## Contents

- [Public execution policy](#public-execution-policy)
- [Unknown is not supported or trial](#unknown-is-not-supported-or-trial)
- [Existing tasks and direct execution](#existing-tasks-and-direct-execution)

| Request | Required checks |
| --- | --- |
| Production execution, including saved-task continuation | Current workspace capacity assignment, then paginated SKU metadata and the production trial/unknown policy. |
| Execution on another selected target, including saved-task continuation | Current workspace capacity assignment; service-enforced eligibility, without the production SKU block. |
| Read-only task status/messages | No execution-capacity check; inspection never grants execution permission. |

Before mutations, read `capacityId` from `GET <selected-api-origin>/v1/workspaces/<workspaceId>`.
For production only, look that ID up in paginated [List Capacities](https://learn.microsoft.com/en-us/rest/api/fabric/core/capacities/list-capacities).
Use the selected tenant/target; never infer trial status from names, IDs or size.
Both resolver entry points and the continuation helper enforce these checks.
Start with `GET <selected-api-origin>/v1/capacities`, without a query string.
Only follow a returned continuation URI or add a nonempty continuation token
from the previous response. Never invent an empty `?continuationToken=`.

## Public execution policy

- An authoritative `FTL64` SKU is trial and blocked for public execution. Select
  an eligible supported capacity or contact the workspace/capacity administrator.
  Do not relocate a workspace, purchase capacity, change assignments, or change
  service policy automatically. The unknown override cannot bypass this block.
- Recognized F/P nontrial SKUs clear this trial check, **not** all AI eligibility
  requirements. Service policy, permissions, and other eligibility checks still
  apply. Capacity metadata does not expose effective service policy.
- The REST contract exposes SKU as a string, not a trial enum. `FTL64` is the
  verified trial value; unfamiliar variants remain unknown until authoritatively
  classified. Do not use an arbitrary `FT*` or `FTL*` prefix rule.

## Unknown is not supported or trial

After verifying the current workspace assignment, if SKU eligibility cannot be
verified, explain the uncertainty and obtain user approval before proceeding.
Do not treat missing metadata as proof of
eligibility or bypass a confirmed trial-capacity block. List Capacities exposes
only capacities where the caller is administrator or contributor; an absent
entry is not proof of trial or supported capacity.

Capacity metadata requests refuse HTTP redirects rather than forwarding
authorization to another endpoint. A redirect leaves eligibility unknown; do
not follow it or silently substitute a route.

Only after approval for this execution pass
`--allow-unknown-capacity` (`-AllowUnknownCapacity` in PowerShell). This choice is
not persisted as future consent, does not grant access, and cannot override
invalid routing or a confirmed trial block. Without a capacity ID, constructing
a new capacity-scoped route still fails even with acknowledgment.
An unreadable, missing or malformed workspace assignment stops even standalone check-only execution; acknowledgment
applies only to unknown SKU eligibility after that assignment has been verified.

## Existing tasks and direct execution

Validate saved task routing before token access: an untrusted non-Fabric backend
host is rejected, not treated as an eligible nonproduction target. Supported,
consistent saved targets proceed to their selected-target assignment checks;
all authenticated HTTP requests refuse redirects rather than forwarding credentials.

Read-only status and messages remain available without a capacity check.
For read-only credential refresh use `--purpose inspect` with the usual auth
arguments and output directory in the same environment.
Never use inspection authentication as permission to execute.

Immediately before direct `PUT`, message `POST`, or `/run`, use:

```bash
"${PYTHON_RUNNER[@]}" scripts/resolve-auth-and-routing.py \
  --workspace-id "$WORKSPACE_ID" --lakehouse-id "$LAKEHOUSE_ID" \
  --expected-capacity-id "$CAPACITY_ID" --check-capacity-only
```

PowerShell:

```powershell
pwsh -NoProfile -File scripts/resolve-auth-and-routing.ps1 `
  -WorkspaceId $env:WORKSPACE_ID -LakehouseId $env:LAKEHOUSE_ID `
  -ExpectedCapacityId $env:CAPACITY_ID -CheckCapacityOnly
```

This performs only metadata GETs (plus local Azure CLI token acquisition), writes
no files, and does not exchange an MWC token or mutate a task. Use IDs from the
selected saved context, and pass the same resource-tenant override if one was
used for authentication. `--expected-capacity-id` stops a changed assignment.
If successful workspace metadata has an absent, null, or empty `capacityId`,
it also stops saved-task execution, even with unknown-eligibility acknowledgment.
This is a missing current assignment, not merely limited visibility of its SKU.
The continuation helper invokes this automatically for production context.
For a selected target outside production, use the same bundled resolver with
`--portal-url <selected-lakehouse-url>` or `--existing-routing <routing.json>`.
It rechecks the workspace assignment but does not apply the production SKU block
or query production metadata. The selected service enforces its eligibility policy;
do not add a blanket trial block or infer effective service policy from SKU.
Workspace-assignment network/access failures, including read timeouts, stop this
check even with acknowledgment. In production, a SKU lookup read timeout after
assignment verification leaves eligibility unknown and may be explicitly
acknowledged for this execution. No extra plugin or package is needed.

For any saved task, prefer adding `--existing-routing <routing.json>` to the
check-only command above. It retains the exact selected target and saved resource
tenant automatically. Without saved context, the command defaults to production.
`scripts/capacity_preflight.py` and `scripts/task_routes.py` are internal modules
for capacity checks and saved-context validation, not standalone commands.
Keep the task, message/dedup IDs,
`.dataprojects`, saved route, and recovery state unchanged when blocked.

Local mocked checks do not prove live supported-capacity execution. Validate
that separately with explicit authorization; never restart a preserved failed
task merely to test endpoint availability.
