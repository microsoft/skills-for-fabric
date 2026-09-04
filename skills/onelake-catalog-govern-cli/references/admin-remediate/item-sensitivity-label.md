<!-- TOPIC REFERENCE for onelake-catalog-govern-cli (mode: admin-remediate). Loaded on demand from admin-remediate.md. -->

# Apply or Remove Item Sensitivity Labels

> Part of the `onelake-catalog-govern-cli` skill (admin-remediate mode). Return to the dispatcher admin-remediate.md. To stop the backlog regrowing, also set a domain default label.

Remediates pillar-2 "unlabeled items" findings by writing labels onto existing items.

> **This is a genuine admin-tier capability — not a data-owner one.** Per [Set or remove sensitivity labels using Power BI REST admin APIs](https://learn.microsoft.com/en-us/power-bi/enterprise/service-security-sensitivity-label-inheritance-set-remove-api): *"Users must be Fabric administrators to call these APIs"* and the **required scope is `Tenant.ReadWrite.All`**. There is **no** non-admin REST path to bulk-apply item labels, so do **not** route this to the data owner and do **not** answer "contact the owner." A Fabric admin performs it directly.

Two API families exist:

| API | Endpoint | Service principal |
|---|---|---|
| Fabric admin labels | `POST /v1/admin/items/bulkSetLabels` / `bulkRemoveLabels` | **No** |
| Power BI admin information protection | `POST /v1.0/myorg/admin/informationprotection/setLabels` / `removeLabels` | **No** |

```bash
# Fabric admin API (preferred — same audience as the rest of this skill)
az rest --method post --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/admin/items/bulkSetLabels" \
  --body '{"items":[{"id":"<itemId>","type":"SemanticModel"}],"labelId":"<labelGuid>"}'
```

```bash
# Power BI admin API (audience differs)
az rest --method post --resource https://analysis.windows.net/powerbi/api \
  --url "https://api.powerbi.com/v1.0/myorg/admin/informationprotection/setLabels" \
  --body '{"labelId":"<labelGuid>","artifacts":{"datasets":[{"id":"<id>"}]}}'
```

> ⚠️ **Neither labeling API supports service principals or managed identities** — these must run under a signed-in Fabric admin. Automating them in an unattended pipeline will fail.

- Power BI artifact keys are `dashboards`, `reports`, `datasets`, and `dataflows`.
- Power BI variant: max **2,000 items per request**, max **25 requests per hour** — batch accordingly and warn the user on large remediations.
- The label must exist in the calling admin's own **label policy**, or the call fails.
- Label IDs are GUIDs; friendly names come from Microsoft Purview, not these APIs.
- **Always dry-run first**: show the user the item list and the target label, and get confirmation. Relabeling is visible to end users and can restrict access.
