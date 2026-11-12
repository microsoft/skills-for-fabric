# Policy capabilities and evaluation

Bundled snapshot verified against Microsoft Learn on 2026-10-26, not an exhaustive
or permanently current allowlist. Capabilities here are preview; beta rule operations
are not recommended for production use.

## Contents

- [Live capability discovery](#live-capability-discovery)
- [Bundled policy matrix](#bundled-policy-matrix)
- [Conditions](#conditions)
- [Behavior to preserve](#behavior-to-preserve)
- [Scope, activation, and limits](#scope-activation-and-limits)
- [Current sources](#current-sources)

## Live capability discovery

1. Unless explicitly offline, read the current overview linked under Current sources.
   Enumerate its **Supported Fabric policies** and follow scenario links for the
   requested policy, or every policy for an inventory. Follow newly added links,
   not a guessed URL or this snapshot's fixed list.
2. Read the current REST lifecycle overview and relevant endpoint references,
   including `PolicyType`. Use exact endpoint URLs from the generated inventory
   or API reference; `(beta)` is part of the create-rule documentation path, not
   a `?view=` substitute. Do not retry guessed slugs when an indexed URL exists.
   Read relevant sections in bounded chunks and parallelize independent sources;
   an inventory does not need every item-creation/activation endpoint.
   For each relevant policy establish its exact identifier,
   availability, scope, governed action, conditions/operators/values, effects,
   defaults/evaluation semantics, limits and prerequisites. Before commands, also
   verify permissions, endpoints, required fields and API version/beta flags.
3. Use current verified documentation over this snapshot, including new policies,
   settings or changed contracts. An announcement/news item is a discovery lead,
   not sufficient proof of an executable API. An enum entry alone does not establish
   policy-specific condition support. Disclose conflicting sources; use the
   operation-specific schema for requests, but keep unresolved mappings design-only.
4. Cite the URLs actually read and the check date, distinguishing conceptual/UI
   availability from API-verified support. Do not claim a live check from a page's
   publication date, search snippet or memory. Call a capability new/changed only
   after comparing actual previous evidence; a newly read article is not necessarily
   a newly changed feature. Do not silently rewrite skill files.
5. If offline or lookup fails, state that current support is unverified and identify
   the snapshot date. Supplied excerpts may support a labeled provisional design,
   not independent verification. Ask for official sources for unfamiliar policies;
   never claim they are unsupported merely because they are absent here.

## Bundled policy matrix

| Policy | Scope | Governed operation | Default without rules |
|---|---|---|---|
| `ItemCreation` | Capacity | Creating Fabric items in workspaces assigned to the capacity | Allow according to workspace permissions |
| `WorkspaceSettingsEditing` | Tenant | Workspace admins editing supported settings, in portal or API | Allow according to existing permissions and tenant settings |
| External data sharing | Tenant | Creating/modifying external data shares | Scenario article says legacy tenant-setting configuration; overview summarizes Block all |

For sharing, disclose the default discrepancy rather than guaranteeing a
universal block-all default. Inspect the tenant's configuration before rollout.
In this snapshot the scenario article uses `ExternalDataSharing`; the overview's
illustrative JSON uses `ExternalDataShare`. Neither is in the bundled REST
`PolicyType` enum. Keep it design-only unless a current executable mapping is verified.

## Conditions

All paths below use Dynamic conditions with `AnyOf` or `NoneOf` and 1-50 string
values. Store IDs, not picker display names. Do not repeat a target property within
a rule. Separate rules express alternative combinations.

| Target property | Available for | Values |
|---|---|---|
| `workspace.id` | All three documented scenarios | Fabric workspace GUIDs; ItemCreation targets must be on selected capacity |
| `principal.groups.id` | All three | Transitive Microsoft Entra security-group object GUIDs |
| `item.type` | ItemCreation | Supported API identifiers, e.g. `Lakehouse`, `Warehouse`, `Notebook`, `DataPipeline`, `SemanticModel`, `Report` |
| `workspaceSettingsEditing.settingType` | WorkspaceSettingsEditing | `Encryption`, `OutboundNetworking` |
| `item.sensitivityLabel.id` | External-sharing design | Microsoft Purview label GUIDs |
| `item.workspace.id` | External-sharing design | Source workspace GUIDs, alternative to `workspace.id` |
| `externalDataShareRecipient.emailDomain` | External-sharing design | Normalized `@domain.tld`; comparisons are case-insensitive |

The shared definition of DynamicCondition permits dot-separated paths syntactically;
that does NOT make arbitrary paths valid. `workspace.name`, `principal.id`,
`itemType`, `recipientDomain` and `sensitivityLabel.id` are not substitutes.
Do not infer arbitrary ItemType enum members are enforced: verify unfamiliar types.

Unlabeled sharing uses the documented **No label** UI option. Its JSON sentinel
is not verified here; never invent `null`, an empty GUID, or a display-name sentinel.
The label picker requires the Purview Information Protection tenant setting and
shows the acting admin's available label policy.

## Behavior to preserve

- Conditions in a rule are AND. `AnyOf` values are OR; `NoneOf` is NOR.
  Omitted dimensions match all. Separate Allow rules are OR, not ordered overrides.
- If no rules exist for the evaluated policy, the system default applies.
  With rules, an unmatched governed operation is denied across the admin scope.
- These rules do not grant item creation or workspace-admin permissions.
  Tenant settings can still disable a capability.
- `WorkspaceSettingsEditing` controls who may edit, NOT the resulting setting value.
  Do not treat encryption-edit permission as enabling or enforcing CMK.
- A narrow Prod Allow rule alone blocks other workspaces on the same capacity
  (or tenant for settings). Complementary rules are necessary when other behavior
  should remain unchanged. A blanket Allow rule would defeat the restriction.

## Scope, activation, and limits

A PolicySet is a workspace item with immutable Tenant or Capacity scope. Its
storage workspace is not its enforcement boundary. Creation produces an inactive
item. Only one set can be active per scope; one set can be active on only one
scope at a time. Deactivate before moving it to another capacity.

The **Policies (preview)** tenant setting controls availability and can restrict
authoring to selected security groups. The storage workspace needs supported Fabric
capacity. Current overview excludes West Europe, North Europe, and West US.
Changes can take up to 15 minutes after activation; inspect status and test with
both group members and nonmembers. Evaluation decisions are recorded in audit logs.

Documentation has a limits conflict: the overview says 100 rules per Tenant policy
and 50 per Capacity policy; Create Policy Set and Replace By Policy REST references
say at most 50 rules of each type per set. Keep generated requests within 50 per
type and flag larger designs for service-contract verification, not automatic splitting.

## Current sources

- [Overview](https://learn.microsoft.com/en-us/fabric/governance/fabric-policies-overview)
- [Item creation](https://learn.microsoft.com/en-us/fabric/governance/fabric-policies-item-creation)
- [Workspace settings editing](https://learn.microsoft.com/en-us/fabric/governance/fabric-policies-edit-workspace-settings)
- [External data sharing](https://learn.microsoft.com/en-us/fabric/governance/fabric-policies-external-data-sharing)
- [REST lifecycle overview](https://learn.microsoft.com/en-us/fabric/governance/fabric-policies-rest-api)

This snapshot does not verify a roadmap for new-workspace defaults, device conditions,
arbitrary settings editing, or Set/Audit/Modify effects. Do not label them planned
or rule out future support without checking current official documentation.
