# Response format

Scale detail to the task; don't force a deployment section on advice or inspection.

1. **Intent and policy:** requirement, chosen policy type, verified admin scope,
   storage workspace vs target workspaces, and support status. Include official
   source URLs and the actual check date; if offline/unavailable, identify the
   generated inventory's retrieval date and the 2026-10-26 contract-reference
   snapshot separately. Neither is an independent current check.
2. **Rules:** names, target properties, operators, values and verified effects.
   Explain AND within each rule and OR across rules where it affects the result.
3. **Effective behavior:** positive/negative cases, outside-target behavior,
   permissions still required, inactive vs activated behavior, and default when
   there are no rules. Call out broad overlapping rules.
4. **Identity and roles:** show discovered name-to-ID mappings, operator/admin roles
   and governed actors' underlying permissions, distinguishing verified from unknown.
   Ask only for unresolved intent, ambiguous objects, inaccessible identifiers
   or service-contract discrepancies; do not ask users to re-supply discovered IDs.
5. **Deliverable:** conceptual design, placeholder template, locally checked
   request files, or actual service results. Label the readiness accurately.
   API-ready output separates set creation, individual rules and activation.
6. **Approval and execution:** for build requests show one reviewable proposal
   covering exact API changes, enforcement, test cases and rollback; after explicit
   approval execute only that plan and report read-back results/propagation.
   Stop for changed preconditions, not a duplicate approval of an unchanged plan.
   Advice/file-only requests stay non-executing. Local JSON is not deployment.

For external sharing, name the documented scenario and conditions but explicitly
state that the bundled beta REST enum omits the policy type. Keep it design-only
unless a current executable contract is verified; do not preserve an obsolete
omission after official documentation resolves it.
