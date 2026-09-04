<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Trust / Curate Writes

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md.

The trust/curate pillar has **only one** tenant-admin write: enabling certification. The other curation actions need just workspace/item-level rights, so they live in the **dataowner-remediate** cell; endorsement has no write API at all.

## What lives where

| Action | Tier | Where |
|---|---|---|
| **Enable certification / designate certifiers** | Fabric tenant admin (tenant setting) | **Here** (below) |
| Fix item descriptions | Item Write / workspace Contributor | dataowner-remediate.md § Fix Curation Gaps (Descriptions) |
| Trigger a **Power BI** semantic model refresh | `Dataset.ReadWrite.All` / workspace member | dataowner-remediate.md § Trigger a Semantic Model Refresh |
| Trigger a **Fabric-native** semantic model refresh | **No admin or public REST API** | **Escalate** — the **item owner** or a **workspace admin** must run it (portal *Refresh now*, a scheduled refresh, or a Data Factory semantic-model-refresh activity). See no-write-api-escalation.md |
| **Apply an endorsement badge** (Promoted / Certified) | — | **No public write API** — see no-write-api-escalation.md |

> When you find a stale description or unrefreshed model as an admin, you generally **cannot** fix it yourself (those need workspace-level rights, not tenant admin). For a **Fabric-native** semantic model there is no admin or public API to trigger a refresh **at all** — do not attempt one; instead name the **item owner** or a **workspace admin** who can, and pair the finding with a contact list. Hand the data-owner instruction to the workspace admin / owner — see no-write-api-escalation.md.

---

## Enable Certification and Designate Certifiers

If the audit skill reported "zero certified items", the cause is usually that certification was never enabled.

```bash
# 1. Inspect current state
az rest --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/tenantsettings" \
  --query "tenantSettings[?settingName=='CertifyDatasets']"

# 2. Enable and scope who may certify
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/tenantsettings/CertifyDatasets/update" \
  --body '{"enabled":true,"enabledSecurityGroups":[{"graphId":"<groupObjectId>","name":"Data Stewards"}]}'
```

- Requires Fabric admin (`Tenant.ReadWrite.All`); rate limit 25 req/min.
- **This endpoint is PREVIEW and Microsoft does not recommend it for production.** Always offer the Admin Portal path as the safer alternative and get explicit confirmation before calling it.
- Certification enablement can be **delegated to domain admins** via the delegation flags in the same payload — the right pattern for federated governance.
- Tenant settings are tenant-wide blast radius. Read the current value first, show the user the exact before/after, and never toggle a setting you were not asked about.
- Enabling certification lets stewards *apply* the badge in the portal; there is still **no REST API to set an endorsement badge** on an item.
