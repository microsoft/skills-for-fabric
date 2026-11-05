# Authentication and route construction

Use the bundled resolver for the selected Fabric target. No additional skill,
SynapseML, Spark runtime or token-library installation is required locally.
Shared Azure CLI sign-in prerequisites remain in `common/COMMON-CLI.md`.
The bundled CLI entry points are `scripts/resolve-auth-and-routing.py` and
`scripts/resolve-auth-and-routing.ps1`, relative to the loaded skill directory.
The PowerShell wrapper delegates to Python.
Use the validated portal host's single DNS label to derive
the API origin: `app` maps to `https://api.fabric.microsoft.com`; another
validated label maps to `https://<label>api.fabric.microsoft.com`. This is the
rule implemented by `task_routes.portal_target()`. Retain the supplied target
and any matching saved origin;
this mapping is not evidence that the endpoint is deployed or accessible.

## Token flow

The public [SynapseML MWC exchange example](https://github.com/microsoft/SynapseML/blob/e8b71d877fa9e5517d6e5a4e384a3994a179b315/core/src/test/scala/com/microsoft/azure/synapse/ml/fabric/FabricTokenProvider.scala#L42-L65)
demonstrates the token request. It is an implementation example, not a complete
versioned REST contract. The local helper implements the exchange without
depending on SynapseML:

1. Acquire a Power BI bearer for `https://analysis.windows.net/powerbi/api`
   using the current Azure CLI session. Use an explicit resource-tenant override
   only if supplied, or after access failure establishes that it is needed.
2. Read workspace and Lakehouse metadata on the selected target. Capture the
   workspace `capacityId`; apply the capacity policy from the skill index before execution.
3. POST to `<selected-api-origin>/metadata/v201606/generatemwctoken` with
   `capacityObjectId`, `workloadType: SparkCore`, `workspaceObjectId`, and
   `artifactObjectIds: [<lakehouse-id>]`.
4. Use the returned `Token` and `TargetUriHost` for task calls. Never construct
   the workload host from an environment name or capacity ID.

Every Fabric metadata/token request carries `x-ms-fabric-skill: project-osmos`,
including the home-cluster retry. Only `Tenant not authorized for cluster`
permits retrying the exchange on the trusted home-cluster origin returned by
selected-target metadata. Other errors stop; redirects are not followed.

The service enforces token validity and artifact permissions. Local validation
restricts credential destinations to matching Fabric API origins and documented
[Fabric backend domains](https://learn.microsoft.com/en-us/fabric/security/fabric-allow-list-urls#notebook).
It does not infer authorization or environment membership from workload-host names.

## Resolve and save context

Run from the loaded skill directory, using the existing Python 3.11+ interpreter
selected by the runtime reference in the skill index:

```bash
"${PYTHON_RUNNER[@]}" scripts/resolve-auth-and-routing.py \
  --workspace-id <workspace-id> --lakehouse-id <lakehouse-id> \
  --portal-url "<selected-lakehouse-url>" --output-dir .dataprojects/auth
source .dataprojects/auth/env.sh
```

```powershell
pwsh -NoProfile -File scripts/resolve-auth-and-routing.ps1 `
  -WorkspaceId <workspace-id> -LakehouseId <lakehouse-id> `
  -PortalUrl "<selected-lakehouse-url>" -OutputDir .dataprojects/auth
. .dataprojects/auth/env.ps1
```

Omit the portal URL only for independently selected production context or when
refreshing saved routing. `--fabric-api-host` cannot override the selected target.
The helper writes `routing.json`, a private `mwc-token`, `env.sh` and `env.ps1`.
For a supplied resource tenant, add `--resource-tenant-id` or `-ResourceTenantId`;
`--tenant-id` and `-TenantId` remain compatibility aliases.

New task base:

```text
<TargetUriHost>/webapi/capacities/<capacityId>/workloads/SparkCore/SparkCoreService/direct/v1/workspaces/<workspaceId>/artifacts/<lakehouseId>/tasks
```

Task calls use `Authorization: mwctoken <token>`. Keep tokens out of
command-line arguments, chat, logs and displayed output.

## Same-task credential refresh

Reuse the usual output directory: existing `routing.json` automatically selects
the original target and resource tenant. Alternatively pass
`--existing-routing <original-routing.json>` (`-ExistingRouting`) when writing
fresh credentials into a different private directory.

Both paths verify workspace, Lakehouse, capacity, API origin and workload origin
before writing. Preserve the exact saved `/tasks` or `/aichat` base, task IDs,
message/dedup IDs and recovery files. Never overwrite another task's context.
Saved routing from earlier installations remains usable.

For read-only refresh add `--purpose inspect` (`-Purpose inspect`); execution
checks still apply before a later mutation. Authentication is not task authorization.
Stop on assignment/route changes instead of relocating or recreating the task.
Network failures require retry after resolving the cause, not an eligibility override.
