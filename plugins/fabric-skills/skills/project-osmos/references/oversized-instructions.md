# Oversized instruction fallback

Use this fallback only when the complete handoff remains above 9,500 characters after generated operational text has been compacted. Preserve the full handoff exactly.

1. Generate the task UUID before task creation.
2. Write the complete UTF-8 handoff to a local file with `## User outcome` first and `## Execution plan` immediately below it.
3. Acquire a OneLake token for `https://storage.azure.com/` and store it in a temporary mode-600 file. Never put the token on the command line.

```bash
ONELAKE_TOKEN_FILE=$(mktemp "${TMPDIR:-/tmp}/osmos-onelake-token.XXXXXX")
chmod 600 "$ONELAKE_TOKEN_FILE"
trap 'rm -f "$ONELAKE_TOKEN_FILE"' EXIT

az account get-access-token \
  --resource https://storage.azure.com/ \
  --query accessToken \
  --output tsv > "$ONELAKE_TOKEN_FILE"
```

4. Upload the exact handoff to the selected task Lakehouse:

```bash
"${PYTHON_RUNNER[@]}" skills/project-osmos/scripts/upload-onelake-file.py \
  --source "$FULL_INSTRUCTION_FILE" \
  --workspace-id "$WORKSPACE_ID" \
  --lakehouse-id "$LAKEHOUSE_ID" \
  --destination "Files/ProjectOsmos/tasks/$TASK_ID/instruction.md" \
  --token-file "$ONELAKE_TOKEN_FILE"
```

5. If upload fails, stop before task creation. Do not truncate, paraphrase, ask the user to shorten the outcome, or choose another destination silently.
6. Use this bootstrap as both the task `instruction` and initial user message:

```text
The complete authoritative task specification is stored in the attached Lakehouse at `Files/ProjectOsmos/tasks/<task-id>/instruction.md`. Read the entire UTF-8 file before planning or execution and follow it exactly, including its user outcome and execution plan. Do not summarize or replace it with assumptions. If the file cannot be read, fail before mutation and report the path.
```

Run the instruction-length checker on the bootstrap before `PUT`. Record `handoff_mode: onelake_reference` and `instruction_path` in the local intake audit. For an inline handoff, record `handoff_mode: inline` and `instruction_path: null`.
