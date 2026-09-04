# Protect — Sensitivity Label and DLP Coverage (Pillar 2)

> **Read this when:** Measuring how much of the estate is labelled and protected.

Part of the `onelake-catalog-govern-cli` skill (admin-audit mode). Return to SKILL.md for scoping rules, blind spots and the full posture workflow.

---

## Sensitivity Label and DLP Coverage (Pillar 2)

1. Run the scanner flow above across all workspaces (batched by 100).
2. Flatten every item across all item-type collections in each workspace.
3. **Unlabeled %** = scanner-supported items where `sensitivityLabel` is absent ÷ all scanner-supported items. State the scanned artifact-type denominator, then break it down by item **type**, **workspace**, owning **domain** (join `workspaceId` → `domainId` from the admin workspaces list), and **creator**. Report Fabric-native item types absent from scanner output as **unassessed**, not unlabeled.
4. Flag domains with **no default sensitivity label** configured — see `govern-pillars.md` § Delegated protection settings.
5. **DLP violations and last-evaluation time are not exposed by these APIs** — direct the user to the OneLake catalog **Govern tab → View more → Protect, secure & comply** (the DLP selector shows evaluated workspaces/items, policy violations, and the last evaluation time), or to the **Microsoft Purview portal → Data loss prevention → Alerts** for aggregate DLP alerts. Say this explicitly rather than fabricating an endpoint.

---
