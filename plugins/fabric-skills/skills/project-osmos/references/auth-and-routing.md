# Authentication and route construction

Build the direct SparkCore task route after resolving workspace and Lakehouse IDs from Fabric page context, Microsoft Fabric Skills discovery, or a validated Lakehouse browser URL.

Use `common/COMMON-CLI.md` authentication recipes for shared Azure CLI login and token prerequisites. This reference owns only the Project Osmos-specific Power BI audience, MWC exchange, and capacity-scoped SparkCore route.

## Optional resource tenant override

Use the current Azure CLI session by default. Do not ask for a tenant ID before attempting authentication. If the user already supplied the Microsoft Entra tenant ID that owns the workspace, pass it explicitly; guest users may need this resource-tenant override when their current session is in their home tenant. Ask for the resource tenant only when authentication or workspace lookup shows that the current session cannot access the target tenant.

## Public Fabric route

Use a Power BI bearer token, workspace capacity lookup, MWC token generation, and a capacity-scoped SparkCore route.

Public hosts:
| Purpose | Host |
| --- | --- |
| Workspace metadata and capacity lookup | `https://api.fabric.microsoft.com` |
| MWC token exchange | `https://api.fabric.microsoft.com/metadata/v201606/generatemwctoken` |

The tested helpers add `x-ms-fabric-skill: project-osmos` to every Fabric metadata and MWC token-exchange request, including a home-cluster retry.
They accept only `https://api.fabric.microsoft.com` as the caller-supplied public
Fabric API host and validate workspace and Lakehouse IDs as UUIDs before making
an authenticated request. Routed home-cluster and SparkCore hosts are accepted
only from Fabric service responses.

> **Use `TargetUriHost` for SparkCore:** The `generatemwctoken` response includes a `TargetUriHost` field that is the routed SparkCore host for that capacity. Use it directly as the workload host instead of guessing a generic hostname.

### Token and route steps

1. Use the current Azure CLI session. If no session is available, run `az login --allow-no-subscriptions`. For a supplied resource-tenant override, run `az login --tenant <resource-tenant-id> --allow-no-subscriptions`.
2. Get a Power BI bearer token with `az account get-access-token --resource https://analysis.windows.net/powerbi/api`. Add `--tenant <resource-tenant-id>` only when an override was supplied.
3. Call the workspace metadata endpoint and capture the API `capacityId` field. Use it as the route/token capacity ID, and persist it in `routing.json` as `capacity_id`.
4. Call the public Fabric `generatemwctoken` endpoint with:
   - `capacityObjectId`
   - `workloadType` set to `SparkCore`
   - `workspaceObjectId`
   - `artifactObjectIds` containing the lakehouse ID
5. If token generation succeeds, use the returned token in the task route.

Do not guess or substitute another token-exchange host. Use the tested helper scripts below to perform this same flow. They capture the routed home cluster from Fabric response headers and retry `generatemwctoken` there only for the specific `Tenant not authorized for cluster` response. `TargetUriHost` is still used only after token generation succeeds, as the SparkCore workload host for later task calls.

### Tested auth helper scripts

The helpers write `routing.json`, a private `mwc-token` file, `env.sh` for Bash, and `env.ps1` for PowerShell. Use the generated environment file for task lifecycle and follow-up calls.
The examples below run from the loaded skill directory so the same `scripts/...` paths work in both the source checkout and the packaged ADC bundle.

```bash
"${PYTHON_RUNNER[@]}" scripts/resolve-auth-and-routing.py \
  --workspace-id <workspace-id> \
  --lakehouse-id <lakehouse-id> \
  --output-dir .dataprojects/auth
source .dataprojects/auth/env.sh
```

For a guest or cross-tenant workspace, add `--resource-tenant-id <resource-tenant-id>`.

```powershell
pwsh -NoProfile -File scripts/resolve-auth-and-routing.ps1 `
  -WorkspaceId <workspace-id> `
  -LakehouseId <lakehouse-id> `
  -OutputDir .dataprojects/auth
. .dataprojects/auth/env.ps1
```

For a guest or cross-tenant workspace, add `-ResourceTenantId <resource-tenant-id>`. The Python helper still accepts `--tenant-id`, and the PowerShell wrapper still accepts `-TenantId`, as compatibility aliases.

Direct route shape:
```text
${TASKS_BASE}
```
Public Fabric routes normally use:
```text
Authorization: mwctoken <contents of TOKEN_FILE>
```


## Secret handling

- Prefer token environment variables over command-line token arguments.
- Do not print bearer tokens, MWC tokens, certificate payloads, or tenant secrets.
- Redact auth headers from any logs copied into issues or PRs.
