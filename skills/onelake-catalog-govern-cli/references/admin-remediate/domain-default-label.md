<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Set a Domain Default Sensitivity Label

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md. For clearing an existing unlabeled backlog, pair this with item-sensitivity-label.md.

The one delegated domain setting that is **fully API-backed** — readable on the `Domain` object as `defaultLabelId` and writable via the admin `PATCH` below, which (like all `/v1/admin/*` calls) requires a **Fabric tenant administrator**. Domain admins can set it for their own domains **only** when the preview tenant setting *"Domain admins can set default sensitivity labels for their domains"* is enabled (a delegated portal capability), not through this admin endpoint.

```bash
az rest --method patch --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/domains/{domainId}?preview=false" \
  --body '{"defaultLabelId":"<labelGuid>"}'
```

## What it actually does — do not overstate this

The label is applied to items in the domain's workspaces in **two** cases only:

1. When a new item in a domain having Sensitivity label is created and saved.
2. When an **existing unlabeled** item is updated and saved.

> ⚠️ **It never retroactively labels dormant items.** An unlabeled item that nobody touches stays unlabeled forever. So this does **not** clear an existing backlog — pair it with item-sensitivity-label.md for the backlog, and use the default label to stop the backlog regrowing.

For items that already carry a label, the domain default applies only in these cases:

| Existing label | Overridden by domain default? |
|---|---|
| Manually applied (any priority) | **No** |
| Automatically applied, lower priority | Yes |
| Automatically applied, higher priority | No |
| Default label from policy, lower priority | Yes |
| Default label from policy, higher priority | No |

## Requirements and limits

- Tenant setting **"Domain admins can set default sensitivity labels for their domains (preview)"** must be enabled first. If the `PATCH` appears to succeed but nothing takes effect, check this before debugging the call.
- **Remove** the default label by setting `defaultLabelId` to `00000000-0000-0000-0000-000000000000`.
- `preview=false` is a **mandatory** query parameter.
- **Not supported with deployment pipelines or Git integration** — flag this if the user relies on either.
- Tenant-*wide* default label policy is **not** settable here — that is Microsoft Purview / `Set-LabelPolicy` only.
