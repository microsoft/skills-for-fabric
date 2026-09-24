# Operational intake flow

Runtime flow for classifying a `project-osmos` task, extracting explicit requirements, and presenting recommendations before any API call.

## Task types

Classify each task as one of:

| Type | Meaning |
|---|---|
| Exploration | Read-only profiling, counting, sampling, or summarization |
| Transformative ingest | Read and transform sources into one or more targets |
| Additive | Insert known rows into an existing target |
| Mutative | Update or delete existing rows |
| Schema migration | Change target structure |
| Unclear | The requested action cannot be classified safely |

Announce the inferred type in one line and allow the user to change it. Ambiguous verbs such as `update`, `delete`, `fix`, `clean up`, `migrate`, `sync`, `merge`, and `correct` force `Unclear` unless the outcome is specific.

## Derive requirements before applying defaults

Extract the complete user outcome before consulting fallback recommendations:

- named sources and targets;
- permission per resource;
- safety, promotion, rerun, and schema behavior per write target;
- stable keys or partition scope for idempotent reruns;
- output names, paths, formats, validations, and mutation caps;
- explicit review, approval, or manual-promotion gates;
- reasoning effort when the user specified one.

Resolve settings in this order:

1. Explicit user requirement—preserve it verbatim.
2. Concrete dependent fact—derive only when the dependency is known.
3. Task-type fallback—use only for unresolved settings.

Never let a task-type fallback override an explicit user requirement. Conflicting explicit requirements remain unresolved.

## Recommendation card

Render a vertical monospace card with all eight numbered settings. Each row contains the selected answer and a one-sentence `Why:` line:

1. Permission boundary
2. Safety pattern
3. Promote step
4. Re-run semantics
5. Schema evolution
6. Artifact format
7. Artifact destination
8. Reasoning effort

For Question 1, repeat that the boundary is model guidance rather than a hard Fabric permission. For Question 7, show only the destination category in the card; ask for a concrete workspace path after acceptance when needed.

Offer exactly:

- **Accept recommendations**
- **Change a setting**
- **Explain a setting**
- **Walk through every question**

Do not enumerate one visible menu item per question. Use a second prompt to select the setting after Change or Explain.

## Reply handling

| Reply | Behavior |
|---|---|
| Accept | Treat as final task authorization, resolve dependent values, reconcile conflicts, then compose the handoff |
| Change | Render the selected question and options, preserve the choice, then show the card again |
| Explain | Explain the selected setting and allow a new choice or cancel |
| Walk through | Ask each applicable question in order |
| Anything else | Repeat the card; never auto-start |

Pick letters start at `a` in displayed order. A change that alters applicability must preserve still-valid choices, remove invalid choices, recompute defaults, and show the card again.
