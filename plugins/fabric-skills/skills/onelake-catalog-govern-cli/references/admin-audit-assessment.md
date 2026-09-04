# Admin Audit Assessment and Reporting


## Contents

- [Full Governance Posture Assessment](#full-governance-posture-assessment)

Use this leaf reference for evaluative governance questions after applying the admin audit scope gate.

## Full Governance Posture Assessment

End-to-end workflow when the user asks a broad question ("how healthy is our governance?", "governance audit"). Work the pillars in order and report them in order.

### Which steps apply — retrieval vs. evaluative questions

This skill serves the admin's whole job, not one action. Match the workflow to the question rather than running all of it every time.

| Question type | Examples | Steps that apply |
|---|---|---|
| **Retrieval** — the user wants a fact or a list | "list all domains", "which workspaces are in Sales?", "who are the admins of this domain?", "how many items are in this workspace?" | **Step 0 only**, then load the matching reference and answer. Return the data plainly. |
| **Evaluative** — the user wants a judgement | "how healthy are our domains?", "find assignment gaps", "governance posture", "label coverage", "audit", "what should we fix?" | **Step 0, the relevant pillar step(s), then Steps 4–6.** |

- **Step 0 (the Scope Gate) is never optional** — a wrong denominator ruins a plain lookup just as thoroughly as an audit, and unfiltered lists surface deleted and personal workspaces the user cannot act on.
- **Steps 4–5 exist for evaluative questions.** Do not attach priority, effort and remediation sequencing to a lookup — it buries the answer the user actually asked for.
- **A narrow evaluative question is still evaluative.** "Review domains health" needs Steps 4–6 scoped to that pillar; it does not need the other two pillars.
- **When in doubt, ask** — or answer the retrieval question first, then offer the assessment.

### Step 0 — Establish scope and caveats
1. Confirm the caller is a Fabric admin (see Prerequisites).
2. Ask whether to scope to a specific **domain/subdomain** or assess the whole tenant.
3. Note upfront that admin-monitoring-derived figures may be **up to 24h stale**.
4. **Apply the Scope Gate** and keep the resulting ID set for every later pillar.

### Step 1 — Health (Manage your data estate)
- Compute: unassigned workspaces (%), empty domains (named), domain-capacity misalignment, tag duplication.
- **Check domain ownership** — domains with no `Admin` role assignment, and domains whose contributor scope is `EntireTenant`. See Find Ownerless Domains.
- **Check workspace ownership** — single-admin workspaces, workspaces with no *human* admin, and any tenant `>= N` admin policy. Ask for the threshold; do not assume one. See Find Workspace Admin Gaps.
- **Check for unused workspaces** — report **empty (0 items)** always; assess **inactivity** only if you can afford the ~28-day activity fetch, and say explicitly when you did not. See Find Unused Workspaces.
- **Check capacity health** — suspended/deleting capacities holding workspaces, ownerless and single-admin capacities, empty capacities, and the count of workspaces whose `capacityId` does not resolve. State that **overload/CU cannot be assessed via API**. See Capacity Health.
- **Check item health** — stale items by `lastUpdatedDate`, items with no creator, unresolvable creator principals. See Item Health.
- **Check data freshness** — semantic models whose latest refresh failed or is past its expected cadence. `lastUpdatedDate` records modification, **not** refresh state; use the Power BI refresh history API. Freshness is a data-estate/currency signal, audited here under Health (a deliberate divergence from the product's Discover/Trust/Reuse tab). See Data freshness (refresh state).
- **Check domain metadata** — missing descriptions and missing default sensitivity labels. See Check Domain Metadata Completeness. State that **domain images cannot be audited via API**.
- For **domain-health** assessments specifically, use the Domain-Health Reporting Template so each finding has semantic explanation, action, and priority.
- See also Assignment Gaps.

### Step 2 — Protect (Protect, secure & comply)
- **First**, restrict the item set to items whose `workspaceId` is in the Step 0 active set — `/v1/admin/items` and the scanner API both return items from deleted workspaces as `Active`.
- Assess **sensitivity label coverage**: percentage of unlabeled items, broken down by item type and by owning user/workspace/domain.
- Assess **DLP posture**: which workspaces/items were evaluated, the **last evaluation time** (stale scans hide violations), and any open policy violations.
- Flag domains with no default sensitivity label configured.
- See `govern-pillars.md` § Pillar 2 and Sensitivity Label and DLP Coverage.

### Step 3 — Trust / Curate (Discover, trust & reuse)
- Use the same active-workspace-filtered item set as Step 2.
- Assess **curation**: description coverage, endorsement split by Promoted / Certified / Master data, and **tag coverage** (items/workspaces with no tag) as a discoverability signal. Freshness is **not** assessed here — it is a Health signal, checked in Step 1.
- Check whether certification is even **enabled** — zero certified items often means the feature was never turned on, not that quality is poor.
- Tag **hygiene** (near-duplicate/sprawling tag definitions) is a Health finding (Step 1); tag **coverage** for discovery is the Trust finding here — report the two separately.
- See `govern-pillars.md` § Pillar 3 and Description, Endorsement and Tag Coverage.

### Step 4 — Prioritise and sequence

Two distinct jobs. Do both.

**4a. Surface compounding findings first** — these are higher priority than either signal alone:
- **Ownerless AND populated** — a domain holding workspaces with no assigned Admin: governed content with nobody governing it.
- **Certified but stale** — an authoritative item serving out-of-date data.
- **Broadly shared but unlabeled** — a trust gap and a protection gap together.
- **Unassigned to any domain AND unlabeled** — outside both governance and protection scope.

**4b. Order the remediation by dependency, not by magnitude.** The biggest number is often the *lowest*-value action, and acting on it first can actively make things worse. Apply these sequencing rules:

| Rule | Why |
|---|---|
| **Ownership before coverage** | Bulk-assigning workspaces into ownerless, `EntireTenant`-writable domains scales the ungoverned surface and is tedious to reverse. Assign domain Admins first. |
| **Access scope before bulk writes** | Closing `EntireTenant` contributor scope after a mass assignment leaves an uncontrolled window in between. |
| **Delete/keep decisions before enrichment** | Adding descriptions and labels to domains or workspaces that are about to be deleted is wasted effort. |
| **Domain default label before bulk assignment** | `defaultLabelId` only labels **new** and **touched-unlabeled** items — never dormant ones. Anything assigned before it is set contributes to a permanent unlabeled backlog. |
| **Cheap + reversible before expensive + sticky** | Prefer actions that a single admin can undo. |

State the ordering rationale explicitly in the report — "this is the biggest number but the last thing you should do, because…" is often the most valuable sentence in the whole audit.

### Step 5 — Report

#### Deliverable Contract (what an audit must produce)

> Applies to **evaluative** questions. A retrieval question is answered with the data itself — see Which steps apply.

Structure every finding as **finding → evidence → why it matters → recommended action → priority → effort**, grouped by pillar. All six are required — **do not stop at counts.** Concretely:

| Element | Requirement |
|---|---|
| **Evidence** | Count **and** percentage against the Scope Gate denominator, plus 10-15 named examples. Offer CSV export rather than dumping full lists. |
| **Why it matters** | The consequence in the user's terms, not a restatement of the metric. Pull from the "why it matters" columns in `govern-pillars.md`. Say plainly when the risk is *lower* than it looks (e.g. domain membership is not an access control). |
| **Recommended action** | A specific, named method — not an outcome. "Assign a security group as domain Admin", not "improve ownership". Name the caveats that make it fail (see the remediate skill). |
| **Priority** | From Step 4b, with the sequencing reason. |
| **Effort** | A rough order of magnitude ("~15 min", "bulk operation") so the user can pick off quick wins. |

For **every** health area — domains, workspaces, capacity, items — also include:

- **Clean/pass findings** when a checked area has no gap, so the reader knows it was assessed rather than omitted (e.g. "0 of 59 capacities suspended — no action needed").
- **Human keep / delete / review decisions** for cleanup candidates — empty domains, empty workspaces, empty capacities, stale items — not just a count. **Never auto-recommend deletion**; surface candidates for a person to decide.
- **Priority as blast radius × compounding signals**, and **effort that says whether a tenant admin can fix it or must escalate** (many item- and workspace-level findings are not admin-fixable — see Step 6).

Open with a two-or-three sentence **interpretation** — what the pattern across findings actually means (e.g. "the domain layer was set up but never operated") — before any table. Close with the blind spots from Known Blind Spots, so a clean bill of health is never implied for surfaces you cannot see.

### Step 6 — Hand off to remediation

This skill is **read-only**. Route the user to `admin-remediate` mode to act. Note upfront that **endorsement badges and DLP policies have no public write API** and must be handled in the portal.

Split the findings into two lists, and say which is which:

| | Examples | Handoff |
|---|---|---|
| **Tenant admin can fix** | Domain assignment gaps, domain admins, sensitivity labels, domain defaults, tenant tag definitions | Admin-remediate mode |
| **Object admins can fix** | Capacity assignment, descriptions, applied tags, refresh, item identity | Dataowner-remediate mode; requires the documented workspace/item/capacity roles |
| **Tenant admin *cannot* fix** | Delete/edit stale or unused **items**, item ownership, **workspace role gaps** (incl. single-admin workspaces), capacity admins, endorsement, DLP | Needs a **named contact** — see remediate § Route a Finding to Someone Who Can Fix It |

The second list is usually the larger one for item-level health. Presenting it as actionable-by-the-admin is the most common way this audit misleads.

---
