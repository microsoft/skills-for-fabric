# Fabric Policies REST API

Bundled contracts verified 2026-10-26; recheck current official endpoint references
on each online use. This is a starting point, not a fixed policy/API allowlist.
Use COMMON-CLI.md and COMMON-CORE.md (indexed in SKILL.md) for authentication, transport,
pagination, retries and long-running operations. Every Fabric call, including
polling and retries, needs `x-ms-fabric-skill: fabric-policies-cli`.

## Contents

- [Contract and permission boundaries](#contract-and-permission-boundaries)
- [Read-only scenario discovery](#read-only-scenario-discovery)
- [Endpoints](#endpoints)
- [Separate request shapes](#separate-request-shapes)
- [Safe execution](#safe-execution)
- [Error handling](#error-handling)
- [Endpoint sources](#endpoint-sources)

## Contract and permission boundaries

- For a newly documented policy or operation, verify its exact identifier, scope,
  condition/effect schema, evaluation semantics, permissions and endpoint before
  adapting this lifecycle. Do not copy a sibling policy's contract or assume the
  bundled enum, effects, limits or beta status remain complete and current.
- PolicySet items are preview. Rule endpoints and Tenant active-set lookup below
  are beta: include `beta=true`. Beta is for evaluation/development and not
  recommended for production.
- Item creation: Contributor workspace role and delegated `Item.ReadWrite.All`.
  Rule creation/deletion requires item Write; rule update requires Read and Write.
  Rule listing requires Read and `Item.Read.All` or `Item.ReadWrite.All`.
  Listing policy-set items requires Viewer workspace role and delegated
  `Workspace.Read.All` or `Workspace.ReadWrite.All`.
- Capacity activation/deactivation: item Read, capacity administrator,
  `Item.Read.All` or `Item.ReadWrite.All`, plus `Capacity.ReadWrite.All`.
  Active-capacity lookup requires capacity administrator and `Capacity.Read.All`
  or `Capacity.ReadWrite.All`.
- Tenant activation/deactivation and active lookup: Fabric administrator and
  delegated `Tenant.ReadWrite.All`; documented limit 10 requests/minute.
- The cited operations support users, service principals and managed identities.
  Delegated scopes describe user-token authorization; do not imply a scope string
  alone grants a service principal the necessary role or tenant access.

## Read-only scenario discovery

Use current credentials and the shared CLI discovery/authentication guidance.
A request to build a policy authorizes read-only discovery, not mutations.
If sign-in or directory access is missing, explain the prerequisite; never request
secrets in chat or broaden privileges silently.

1. List all visible workspaces, follow pagination, then filter names with JMESPath.
   Read the target workspace to determine its capacity; list visible capacities
   and resolve the intended one. Reuse a suitable existing administrative storage
   workspace with sufficient permissions, proposing the choice for review.
2. Resolve scenario actor names to Entra security-group object IDs using the
   authenticated directory surface, for example `az ad group list --filter` with
   an exact display-name filter. Escape OData values and shell arguments correctly.
   Do not match on a convenient substring or assume display names are unique.
   Distinguish a business role ("Finance") from a Fabric workspace/admin role.
3. Read existing PolicySet items, rules and active scope state before proposing
   any creation/replacement. Reuse known IDs. For labels, use an authorized
   label-discovery surface only when its contract is verified.
4. Preflight the caller's operation-specific roles/scopes above and the governed
   actors' underlying rights. `GET /workspaces/{workspaceId}/roleAssignments`
   requires Member or higher plus `Workspace.Read.All`/`Workspace.ReadWrite.All`;
   follow pagination. Inability to list roles is not proof of missing create rights:
   disclose unverified access rather than elevate merely to enumerate it.
5. If a name has multiple matches, ask the user to choose; if no matching group
   exists, ask for the intended existing group instead of creating one.
   Ask for IDs manually only when authorized discovery cannot obtain them.
   Do not assign roles, create groups, or change membership as part of policy authoring.

All Fabric discovery requests require the skill telemetry header. Directory
requests use their own documented authorization, not a Fabric resource token.

## Endpoints

Base URL: `https://api.fabric.microsoft.com/v1`.
`{ws}` is the storage workspace; `{set}` and `{rule}` are returned object IDs.

| Operation | Method and path | Body / notes |
|---|---|---|
| Create set | `POST /workspaces/{ws}/policySets` | `displayName`, optional description, `creationPayload.scope.type` |
| List / get sets | `GET /workspaces/{ws}/policySets[/{set}]` | List pages before filtering |
| Update item metadata | `PATCH /workspaces/{ws}/policySets/{set}` | `displayName` / `description`, not scope or rules |
| Delete item | `DELETE /workspaces/{ws}/policySets/{set}` | Confirm inactive before deletion; don't deactivate implicitly |
| List rules | `GET /workspaces/{ws}/policySets/{set}/policyRules?beta=true` | Paginated `value` list |
| Add rule | `POST /workspaces/{ws}/policySets/{set}/policyRules?beta=true` | Create-rule shape below |
| Update rule | `PATCH /workspaces/{ws}/policySets/{set}/policyRules/{rule}?beta=true` | `displayName`, `description`, `conditions`; conditions array fully replaces existing one |
| Delete rule | `DELETE /workspaces/{ws}/policySets/{set}/policyRules/{rule}?beta=true` | May change live enforcement |
| Replace one policy's rules | `POST /workspaces/{ws}/policySets/{set}/policyRules/replaceByPolicy?beta=true` | `policy`, `policyRules`; replaces ALL rules of that policy |
| Read active capacity set | `GET /capacities/{capacityId}/policySets/active` | Returns set ID and storage workspace ID |
| Activate Capacity | `POST /workspaces/{ws}/policySets/{set}/activate` | `{"scopeType":"Capacity","capacityId":"<capacity-id>"}` |
| Deactivate Capacity | `POST /workspaces/{ws}/policySets/{set}/deactivate` | `{"scopeType":"Capacity"}` |
| Read active Tenant set | `GET /admin/policySets/active?beta=true` | Includes rules |
| Activate Tenant | `POST /admin/workspaces/{ws}/policySets/{set}/activate` | No body |
| Deactivate Tenant | `POST /admin/workspaces/{ws}/policySets/{set}/deactivate` | No body |

Activation accepts optional `?allowReplace=true`; default is false. Do not add
it automatically on `PolicySetActivationConflict`.
The conceptual lifecycle mentions a runtime evaluation API, but no request contract
is verified here: do not invent an `/evaluate` endpoint or simulation guarantee.

## Separate request shapes

Create an inactive Capacity set (for Tenant use `"type": "Tenant"`):

```json
{
  "displayName": "Finance item governance",
  "description": "Capacity-scoped item creation controls.",
  "creationPayload": {"scope": {"type": "Capacity"}}
}
```

Create one rule. This is a **template, not deployable** until placeholders are
resolved and confirmed:

```json
{
  "displayName": "Finance Lakehouse in Prod",
  "policy": "ItemCreation",
  "conditions": [
    {
      "type": "Dynamic",
      "targetProperty": "workspace.id",
      "predicate": {"operator": "AnyOf", "values": ["<prod-workspace-id>"]}
    },
    {
      "type": "Dynamic",
      "targetProperty": "principal.groups.id",
      "predicate": {"operator": "AnyOf", "values": ["<finance-group-id>"]}
    },
    {
      "type": "Dynamic",
      "targetProperty": "item.type",
      "predicate": {"operator": "AnyOf", "values": ["Lakehouse"]}
    }
  ],
  "effects": [{"type": "Allow"}]
}
```

Rules don't contain activation scope or capacity IDs. In this snapshot the request's
`policy` enum lists only `ItemCreation` and `WorkspaceSettingsEditing`; discover
additions from current endpoint documentation instead of rejecting them by this list.
The Create Policy Rule REST contract **requires `effects`**, unlike the item
creation and external-sharing conceptual articles which say effects are omitted.
Follow the beta endpoint's required fields, not illustrative overview `then` JSON.
Item-definition serialization is another contract; do not reuse create-rule bodies
as encoded definitions without checking the linked item-definition specification.

For `replaceByPolicy`, put the type in outer `policy` and the complete rules to
retain in `policyRules`; each entry has `displayName`, optional `description`,
`conditions` and `effects`, but no inner `policy`.

## Safe execution

1. Resolve storage workspace and existing set/rules, including all pages; verify
   immutable scope, target capacity membership, IDs, roles and feature availability.
2. Present the exact policy and execution plan for review before any mutation.
   One explicit approval can cover creating, configuring and activating the reviewed
   policy; it must name enforcement and any replacement, not merely approve JSON syntax.
   For approved creation, save JSON bodies separately. Create the set, capture its returned
   ID, add rules and read back. A 202 is pending: follow Location/operation-result
   processing in the shared LRO reference. Never assume success from an accepted call.
3. Compare the full effective policy with intent, including complementary rules.
   For active-set changes, obtain approval before mutation, not just before activation.
4. Re-read the scope's active set before enforcement. Compare it with the approved
   existing active ID, desired set, scope, impacted workspaces/settings and rollback.
   If activation was explicitly approved and preconditions are unchanged, proceed
   without another approval prompt. Otherwise stop and obtain fresh approval;
   never treat ordinary activation approval as approval to replace a different set.
5. Activate using the correct Capacity vs Admin/Tenant endpoint. Read the active
   set back and confirm the expected ID. Allow up to 15 minutes propagation; test
   positive and negative governed operations with authorized test users.
6. Rollback requires approval too: deactivate the new set or restore the recorded
   previous set through the appropriate endpoint. Removing the last rule can restore
   a permissive default, so deletion is not automatically a safe rollback.

Example commands below are templates to show, **not execute**, on planning requests.
Replace all angle-bracket inputs; use the correct existing JSON filenames:

```powershell
az rest --method post --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/<storage-workspace-id>/policySets" --headers "x-ms-fabric-skill=fabric-policies-cli" --body "@create-set.json"
az rest --method post --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/<storage-workspace-id>/policySets/<policy-set-id>/policyRules?beta=true" --headers "x-ms-fabric-skill=fabric-policies-cli" --body "@finance-rule.json"
az rest --method get --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces/<storage-workspace-id>/policySets/<policy-set-id>/policyRules?beta=true" --headers "x-ms-fabric-skill=fabric-policies-cli"
```

## Error handling

- `Unauthorized` / 401/403: check identity, audience, item permissions and scope
  admin role; do not request broader privileges without explaining the failing operation.
- `NotFound`: verify storage workspace, set/rule IDs and visibility.
- `UnsupportedPolicyForScope`, `InvalidActivationScope`: stop and correct the
  design; don't silently change scope.
- `PropertyCannotBeNullOrEmpty`, `PropertyMinCount`, `PropertyMaxCount`,
  `DuplicateConditionTargetProperty`, `InvalidConditionCombination`,
  `UnsupportedPropertyValue`: show the rejected property and fix against the contract.
- Activation conflict: report the existing active set, never force replacement.
- 429: honor `Retry-After`. For retryable failures follow shared guidance; after
  ambiguous POST outcomes, inspect existing state before retrying to avoid duplicates.

## Endpoint sources

- [Create Policy Set](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/items/create-policy-set)
- [List workspace role assignments](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/list-workspace-role-assignments)
- [List Policy Sets](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/items/list-policy-sets)
- [Update Policy Set](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/items/update-policy-set)
- [Delete Policy Set](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/items/delete-policy-set)
- [Create rule (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/policy-rules/create-policy-rule(beta))
- [List rules (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/policy-rules/list-policy-rules(beta))
- [Update rule (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/policy-rules/update-policy-rule(beta))
- [Delete rule (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/policy-rules/delete-policy-rule(beta))
- [Replace by policy (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/policy-rules/replace-policy-rules-by-policy(beta))
- [Capacity activate](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/activation/activate), [deactivate](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/activation/deactivate), [active](https://learn.microsoft.com/en-us/rest/api/fabric/policyset/activation/get-active-for-capacity)
- [Tenant activate](https://learn.microsoft.com/en-us/rest/api/fabric/admin/policy-sets/activate), [deactivate](https://learn.microsoft.com/en-us/rest/api/fabric/admin/policy-sets/deactivate), [active (beta)](https://learn.microsoft.com/en-us/rest/api/fabric/admin/policy-sets/get-active(beta))
