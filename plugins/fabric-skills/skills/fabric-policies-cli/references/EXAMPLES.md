# Authoring examples

All examples are offline designs from the bundled 2026-10-26 snapshot, not a closed
list of supported policies. Check current official sources on online requests.
GUIDs below are synthetic examples, not discovered tenant identifiers.
Substitute verified user inputs before any deployment.
The rule bodies follow the beta Create Policy Rule contract, including `effects`.
Use the API reference indexed in SKILL.md for separate create-set and activation requests.

## Contents

- [Finance Lakehouse only in Prod](#finance-lakehouse-only-in-prod-preserve-other-workspaces)
- [Dev and Prod with separate teams](#dev-and-prod-with-separate-teams)
- [Restrict CMK editing](#restrict-cmk-editing-preserve-all-other-editing)
- [Partner sharing](#partner-sharing-design-only)
- [Newly documented policies](#newly-documented-policies)
- [Missing inputs and unsupported requests](#missing-inputs-and-unsupported-requests)

## Finance Lakehouse only in Prod; preserve other workspaces

**Intent:** Only Finance members can create Lakehouse in Prod; everyone else
can continue creating all permitted types in other workspaces on this capacity.

**Mapping:** Capacity `ItemCreation`. Assume Prod is
`11111111-1111-4111-8111-111111111111` and Finance is
`22222222-2222-4222-8222-222222222222`. Still need the storage workspace and
capacity IDs and confirmation these are the intended objects.

Send each object separately to Create Policy Rule. Rule 1:

```json
{
  "displayName": "Finance Lakehouse in Prod",
  "policy": "ItemCreation",
  "conditions": [
    {
      "type": "Dynamic",
      "targetProperty": "workspace.id",
      "predicate": {"operator": "AnyOf", "values": ["11111111-1111-4111-8111-111111111111"]}
    },
    {
      "type": "Dynamic",
      "targetProperty": "principal.groups.id",
      "predicate": {"operator": "AnyOf", "values": ["22222222-2222-4222-8222-222222222222"]}
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

Rule 2 preserves outside-Prod behavior without overriding Rule 1:

```json
{
  "displayName": "Preserve creation outside Prod",
  "policy": "ItemCreation",
  "conditions": [
    {
      "type": "Dynamic",
      "targetProperty": "workspace.id",
      "predicate": {"operator": "NoneOf", "values": ["11111111-1111-4111-8111-111111111111"]}
    }
  ],
  "effects": [{"type": "Allow"}]
}
```

| Attempt after activation | Expected policy outcome |
|---|---|
| Finance, Lakehouse, Prod | Allow |
| Finance, Notebook, Prod | Block |
| Non-Finance, Lakehouse, Prod | Block |
| Either group, any supported item, other workspace on capacity | Allow, subject to workspace permissions |
| Workspace on another capacity | Not governed by this set |

Without Rule 2, other workspaces on this capacity would also be blocked.
An unrestricted Allow rule would undo the Prod restriction. Rule order cannot
fix such overlap.

## Dev and Prod with separate teams

For "DG-Team can create anything in Dev; Engineering-Lead can create only
Lakehouse/Warehouse in Prod", use two `ItemCreation` Allow rules on one capacity:
Dev workspace AND DG-Team (omit item type); Prod workspace AND Engineering-Lead
AND `item.type AnyOf [Lakehouse, Warehouse]`. Do not enumerate all item types to
represent unrestricted Dev access. Ask what should happen to other workspaces;
without a complementary rule they are blocked. Never add a blanket baseline rule.

## Restrict CMK editing, preserve all other editing

**Intent:** Only IT-Security workspace admins may edit CMK in Prod. Everyone
retains their existing editing rights elsewhere and for other supported settings.

Tenant `WorkspaceSettingsEditing`. Required rules are:

| Rule | AND conditions | Effect |
|---|---|---|
| IT-Security edits CMK in Prod | `workspace.id AnyOf [Prod]`; `principal.groups.id AnyOf [IT-Security]`; `workspaceSettingsEditing.settingType AnyOf [Encryption]` | Allow |
| CMK editing outside Prod | `workspace.id NoneOf [Prod]`; `workspaceSettingsEditing.settingType AnyOf [Encryption]` | Allow |
| Other supported setting edits everywhere | `workspaceSettingsEditing.settingType NoneOf [Encryption]` | Allow |

For example, the first rule's beta request is:

```json
{
  "displayName": "IT-Security edits CMK in Prod",
  "policy": "WorkspaceSettingsEditing",
  "conditions": [
    {
      "type": "Dynamic",
      "targetProperty": "workspace.id",
      "predicate": {"operator": "AnyOf", "values": ["11111111-1111-4111-8111-111111111111"]}
    },
    {
      "type": "Dynamic",
      "targetProperty": "principal.groups.id",
      "predicate": {"operator": "AnyOf", "values": ["33333333-3333-4333-8333-333333333333"]}
    },
    {
      "type": "Dynamic",
      "targetProperty": "workspaceSettingsEditing.settingType",
      "predicate": {"operator": "AnyOf", "values": ["Encryption"]}
    }
  ],
  "effects": [{"type": "Allow"}]
}
```

A nonmember workspace admin is blocked editing Encryption in Prod, but can still
edit OutboundNetworking. An IT-Security member without workspace-admin permission
does not gain it. Other workspaces retain CMK editing. The policy does NOT set CMK
values or override tenant-disabled functionality.

## Partner sharing: design only

**Intent:** Only Sales may share Confidential data with @acme.com and @techcorp.com.

Tenant external-sharing design: `principal.groups.id AnyOf [Sales-ID]`,
`item.sensitivityLabel.id AnyOf [Confidential-ID]`,
`externalDataShareRecipient.emailDomain AnyOf [@acme.com, @techcorp.com]`.
All conditions must hold. Ask whether this should apply tenant-wide or to selected
workspaces, and collect group, label, and optional workspace GUIDs.

In this snapshot the scenario article documents `ExternalDataSharing`, but the beta
REST rule enum omits it. Do not generate a supposedly executable creation or activation
sequence for this design. Explain the mismatch and require a verified updated
contract before automation; the Policies Center is the documented UI entry point.

## Newly documented policies

**Intent:** "Use the Fabric policy announced after this skill's snapshot."

Check the current overview and follow the policy's official scenario and endpoint
references. Establish its identifier, scope, conditions, effects, defaults and
permissions, then apply the same intent-to-rules and guarded lifecycle workflow.
Do not reject it just because it is absent from these examples, or substitute
ItemCreation for an unrelated action. If only an announcement or conceptual
scenario is available, deliver a labeled design and identify the missing executable
contract. Offline, disclose the freshness limit and request official references
instead of claiming current support or inventing a policy identifier.

## Missing inputs and unsupported requests

- "Lock down Finance": ask which action, scope, groups, workspaces, allowed cases
  and exceptions. Do not guess an item type or generate deployable JSON.
- "Force encryption on every new workspace": no verified default-setting policy;
  WorkspaceSettingsEditing controls who edits, not what value is set.
- "Use Deny, AllOf and workspace.name": reject the authored effect/operator/path;
  propose Allow with `AnyOf`/`NoneOf` and verified `workspace.id` as appropriate.
