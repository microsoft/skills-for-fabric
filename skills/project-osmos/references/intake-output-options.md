# Intake output and reasoning options

Question definitions for saved artifacts and reasoning effort, plus fallback recommendations.

## Question 6: artifact format

- `let the agent decide`—choose a reproducible artifact when useful;
- `notebook always`—save a Fabric notebook;
- `don't save artifacts`—keep only task messages and skip Question 7.

## Question 7: artifact destination

- `workspace folder`—requires a concrete workspace path; publishing failure is terminal;
- `lakehouse Files`—save under a concrete `Files/` path;
- `both`—requires both concrete destinations;
- `let the agent decide`.

Never silently fall back from a failed workspace publish to Lakehouse Files.

## Question 8: reasoning effort

Options are `low`, `medium`, `high`, and `xhigh` (`max`, `extra high`, and `ultra` are aliases for `xhigh`).

Always recommend `medium`. Do not infer another level from task complexity; change it only when the user explicitly selects one.

## Dynamic recommendations

| Explicit outcome signal | Recommendation |
|---|---|
| rerun, idempotent, or counts unchanged | reconcile idempotently and collect key/scope |
| review, approve, or before publishing | staging table + manual promotion and one explicit gate |
| missing target that must be created safely | staged create-and-promote |

## Fallback matrix

Use only for settings not resolved by explicit requirements or known facts.

| Setting | Exploration | Transformative ingest | Additive | Mutative | Schema migration | Unclear |
|---|---|---|---|---|---|---|
| Permission | read-only | source read-only, targets write | targets write | targets write | targets write | ask per resource |
| Safety | skip | clone-and-promote | skip | clone-and-promote | staged create-and-promote | ask |
| Promotion | skip | re-run final code | skip | re-run final code | atomic rename | ask |
| Rerun | n/a | fail if populated | reconcile idempotently | fail if populated | fail if populated | ask |
| Schema | skip | locked | locked | locked | requested change only | ask |
| Format | don't save | notebook | notebook | notebook | notebook | let agent decide |
| Destination | skip | workspace folder | workspace folder | workspace folder | workspace folder | ask |
| Effort | medium | medium | medium | medium | medium | medium |

If safety is neither clone-and-promote nor staged create-and-promote, skip promotion. If artifacts are not saved, skip destination.
