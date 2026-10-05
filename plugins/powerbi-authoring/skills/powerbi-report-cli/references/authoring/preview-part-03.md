# Report Preview - Part 3

Continuation of `preview.md`. Open this file directly from the skill reference index.

## Screenshot artifact lifecycle

Apply this lifecycle to mandatory authoring validation screenshots and
explicitly retained screenshot output on both Desktop and service hosts:

1. Classify any screenshot location in the initial request by intent:
   - A location supplied specifically for **temporary validation** is the
     temporary parent.
   - A location supplied with save/export/keep/retain intent is a **retained
     output destination**, not the validation parent. Never delete it or files
     written there. For a task that also requires mandatory authoring
     validation, keep retained output separate from the temporary validation
     child.
2. For mandatory validation, resolve the Windows local application-data folder
   with `[Environment]::GetFolderPath('LocalApplicationData')` and use
   `<LocalApplicationData>\Power BI Report Authoring\Screenshots` as the
   default temporary parent. Do not hard-code
   `C:\Users\<user>\AppData\Local`; the configured user profile may be on
   another local drive. Use a user-supplied temporary-validation parent instead
   when one was explicitly identified in step 1. Do not ask the user for a
   location or permission to use the default parent.
3. If a user-supplied temporary parent or retained destination is inside the
   PBIP project, a `.Report` or `.SemanticModel` directory, a Git worktree, or a
   known cloud-synchronized directory:
   1. Explain that screenshots may expose report data and could be committed,
      uploaded, or synchronized.
   2. Recommend a local external directory.
   3. Continue with the supplied location only after explicit confirmation.
4. For mandatory validation only, record the resolved absolute temporary
   parent, but do not create the parent or validation child yet. Complete CLI
   capability, host availability, status, open/attach, reload, and other
   readiness checks first. A failure before child creation leaves nothing
   workflow-owned to clean up.
5. Immediately before the first mandatory-validation screenshot command,
   create the temporary parent when it does not exist, then create
   `<parent>\validation-<report-name>-<UTC-timestamp>-<UUID>`. Sanitize
   `<report-name>` for the file system, generate a full untruncated UUID, and
   record the exact absolute child path as `<validation-screenshot-dir>`. Never
   capture directly into the shared parent directory.
6. Reuse the same child for every capture and retry in the complete edit ->
   validate -> preview -> screenshot -> review loop.
7. Review screenshot files directly from the recorded child.
8. Once the child exists, treat cleanup as a `finally` action. After final
   review, and before every handled success, failure, blocked exit, or
   abandonment, verify that the deletion target is the exact recorded child
   and delete it recursively—even when capture failed and wrote no PNG. Never
   leave the child merely because the CLI is unsupported, the bridge or host is
   unavailable, reload or capture failed, or review could not continue. Never
   delete the selected parent, pre-existing files, sibling directories created
   by earlier or concurrent workflows, the PBIP project, or any broader path.
   Keep the selected parent even when empty.
9. Retry a failed deletion once. If it still fails, report the exact remaining
   path and require manual cleanup. Do not claim cleanup after an abrupt host or
   agent termination that prevented this step from running.

Never automatically delete a screenshot the user requested with
save/export/keep/retain intent at a final file or directory path. Keep retained
output separate from the workflow-owned mandatory-validation child. For a
standalone retained-screenshot request, complete the same readiness checks,
create the retained destination only immediately before capture, write there
directly, review the requested output, and skip temporary-child cleanup because
the output belongs to the user.
