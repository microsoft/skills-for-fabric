# Intake reconciliation and handoff

Validate the selected plan, then create a compact, executable task instruction.

## Reconcile before dispatch

Compare the complete user outcome with every selected setting and dependent value.

| Requirement | Invalid combination |
|---|---|
| rerun, idempotent, counts unchanged | fail if populated or append duplicates |
| review, approve, before publishing | no approval gate |
| named output path or table | unresolved or agent-chosen name |
| read-only source | write permission or mutation |

Do not resolve a contradiction by precedence. Ask one targeted question that quotes both requirements and asks for the intended executable behavior. If still unresolved, stop locally and name the conflict.

## Size limits

The service accepts at most 10,000 characters. Target 9,500 or fewer and keep generated operational text to 2,500 characters or fewer.

1. Preserve the complete user outcome verbatim.
2. Include only selected execution-critical semantics; omit unselected options and rationales.
3. Run `"${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/check-instruction-length.py --path <instruction-file> --limit 9500`.
4. If the complete handoff remains too large, use the lossless process in `oversized-instructions.md`.

## Handoff shape

```text
## User outcome
<original instruction text, verbatim>

## Execution plan
Task: type=<type>; mode=autonomous; effort=<level>; gates=<none|explicit gate>
Resources:
- <resource>: permission=<read-only|write>; scope=<exact source scope>
Writes:
- <target>: safety=<choice and meaning>; promote=<choice and meaning>; rerun=<choice and exact populated-target behavior, key/scope=value>; schema=<choice and meaning>; approval=<none|gate>; cap=<value if applicable>
Artifact: format=<choice>; destination=<choice and concrete path/name>
Validation: <literal row-count, null, schema, and mutation checks>
Ambiguity: fail once naming the conflict and required input; never repeat a question.
```

Send this exact handoff in both `PUT /{taskId}` and the initial user message. Never send a bare option label without its executable meaning.

## Example

```text
## User outcome
Build idempotent bronze and gold Guidewire claim tables from Attempt#1-Guidewire Claims. Reruns must keep counts unchanged.

## Execution plan
Task: type=Transformative ingest; mode=autonomous; effort=medium; gates=none
Resources:
- Attempt#1-Guidewire Claims: permission=read-only; scope=all source rows
Writes:
- bronze_guidewire_claim: safety=staged create-and-promote (validate then atomically create); promote=atomic rename (retain prior target); rerun=reconcile idempotently (same input leaves counts unchanged, key=claim_id); schema=locked; approval=none
- gold_claim_starter: safety=staged create-and-promote (validate then atomically create); promote=atomic rename (retain prior target); rerun=reconcile idempotently (same input leaves counts unchanged, key=claim_id); schema=locked; approval=none
Artifact: format=notebook; destination=name=agent choice
Validation: report literal source, bronze, and gold counts and prove same-input rerun stability
Ambiguity: fail once naming the conflict and required input; never repeat a question.
```
