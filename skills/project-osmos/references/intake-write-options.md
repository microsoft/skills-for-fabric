# Intake write and safety options

Question definitions for resources and write targets. Ask Questions 1–5 once per applicable resource or target.

## Question 1: permission

For each named resource:

- `read-only`—inspect but do not mutate;
- `write`—create or change data or metadata.

If a resource must not be mutated, the user should also enforce that through Fabric or OneLake permissions.

## Question 2: safety pattern

For each write target:

- `let the agent decide`—choose from known target state and requested guarantees;
- `clone-and-promote`—iterate on a copy, then promote;
- `staged create-and-promote`—validate a candidate, then atomically create a missing target;
- `staging table + manual promotion`—stop before changing the real target and wait at an explicit gate;
- `iterate in place`—write directly to a disposable or explicitly approved target.

Only `staging table + manual promotion` creates an approval gate by itself.

## Question 3: promotion

Ask only for clone-and-promote or staged create-and-promote:

- `re-run final code against real target`—retain the candidate as evidence and perform a non-atomic final write;
- `data swap (INSERT OVERWRITE)`—atomically replace contents when supported;
- `atomic rename`—promote the candidate and retain the prior target as a backup;
- `let the agent decide`.

No promotion option requires approval unless an approval gate is listed separately.

## Question 4: rerun semantics

- `fail if target already populated`—terminal safety policy; confirmation does not override it;
- `reconcile idempotently`—same inputs leave contents and counts unchanged; requires a stable key or partition scope;
- `append (duplicates allowed)`—use only when duplicate rows are acceptable;
- `overwrite (truncate then write)`—use only for a fully owned target;
- `let the agent decide`.

Outcome language such as `rerun`, `idempotent`, `counts unchanged`, or `safe to re-run` requires `reconcile idempotently` and collection of the key or partition scope.

## Question 5: schema behavior

For each write target:

- `locked`—reject new, missing, or incompatible columns;
- `auto-evolve (mergeSchema)`—allow new columns;
- `type-widening only`—allow safe widening but no new columns;
- `let the agent decide`.

For schema-migration tasks, the requested schema change is the operation; this question controls unrelated drift.

## Pre-dispatch target-state check

Resolve whether each target exists, whether it contains rows, and whether the selected safety and rerun behavior can satisfy the outcome. If target state is unknown and changes the behavior, ask once before dispatch.
