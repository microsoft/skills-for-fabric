# Trust and Curation — Endorsement, Descriptions, Tags (Pillar 3)

> **Read this when:** Measuring whether items are discoverable, documented and trustworthy.

Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

## Description, Endorsement and Tag Coverage (Pillar 3)

1. **Description coverage** — from the fully paginated Fabric Admin item inventory, count items where `description` is null/empty. Report as an all-Fabric percentage, ranked by item type, workspace, and domain.
2. **Endorsement coverage** — within scanner-supported Power BI artifact types, count items with `endorsementDetails` present, split by `Promoted` / `Certified` / `Master data`. Missing field ⇒ unendorsed. State the scanned type denominator and report Fabric-native types absent from scanner output as unassessed.
   - Before reporting "zero certified items" as a failure, check whether certification is **enabled** in tenant settings — it is off by default and enablement can be delegated to domain admins.
   - Power BI **dashboards cannot be endorsed** — exclude them from the denominator.
3. **Tag coverage** — use the fully paginated Fabric Admin item and workspace inventories to count items and workspaces carrying no tag (`tags[]` empty/absent), ranked by item type, workspace, and domain. Tags make content **discoverable** by classification in the catalog, so *coverage* is a trust/curate signal and belongs here. Tag **hygiene** — near-duplicate `displayName`s, sprawl, ad-hoc definitions — is instead a data-estate/organization concern and is audited under **Health**; see `govern-pillars.md` § Pillar 1. Report the two separately so the reader knows which lever fixes which gap.
4. **Cross-pillar**: intersect the endorsed set with the **stale-refresh** set — note that freshness is audited under Health, so pull the stale set from health-item.md § Data freshness (refresh state) — and the broadly-shared set with the unlabeled set. Surface those items first.

> **Freshness is audited under Health, not here.** "Is this item refreshing on schedule?" is treated as a data-estate/currency signal in health-item.md § Data freshness (refresh state) — a deliberate divergence from the product's Govern tab, which lists data freshness under *Discover, trust & reuse*.

---
