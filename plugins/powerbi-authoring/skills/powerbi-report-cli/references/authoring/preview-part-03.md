# Report Preview - Part 3

Continuation of `preview.md`. Open this file directly from the skill reference index.

## Screenshot artifact lifecycle

Apply this lifecycle to mandatory authoring validation screenshots on both
Desktop and service hosts:

1. Resolve the Windows local application-data folder with
   `[Environment]::GetFolderPath('LocalApplicationData')` and use
   `<LocalApplicationData>\Power BI Report Authoring\Screenshots` as the
   parent. Do not hard-code `C:\Users\<user>\AppData\Local`; the configured user
   profile may be on another local drive.
2. Before the first capture, ask the user for a preferred parent directory or
   permission to use the default. State that screenshots can contain visible
   report data and that the workflow-owned child will be deleted after the
   complete validation and review loop. Present the exact resolved absolute
   parent from step 1 as the recommended prefilled value. Never present
   `%LOCALAPPDATA%`, `$env:LOCALAPPDATA`, `<LocalApplicationData>`, the report
   directory, a project-relative `screenshots` directory, or any other
   unresolved or custom path as the prefilled value. Collect a custom parent
   only when the user explicitly chooses one.
3. Resolve the selected parent to an absolute path. If it is inside the PBIP
   project, a `.Report` or `.SemanticModel` directory, any Git worktree, or a
   known cloud-synchronized directory, warn that screenshots may expose report
   data and could be committed, uploaded, or synchronized. Ask for a local
   external directory instead. Use the warned location only after explicit
   confirmation.
4. Record the approved parent, but do not create the validation child yet.
   Complete CLI capability, host availability, status, open/attach, reload, and
   other readiness checks first. A failure before child creation leaves
   nothing workflow-owned to clean up.
5. Immediately before the first screenshot command, create
   `<parent>\validation-<report-name>-<UTC-timestamp>-<UUID>`. Sanitize
   `<report-name>` for the file system, generate a full untruncated UUID, and
   record the exact absolute child path as `<validation-screenshot-dir>`. Never
   capture directly into the shared parent directory.
6. Reuse the same child for every capture and retry in the complete edit ->
   validate -> preview -> screenshot -> review loop.
7. Once the child exists, treat cleanup as a `finally` action. After final
   review, and before every handled success, failure, blocked exit, or
   abandonment, verify that the deletion target is the exact recorded child
   and delete it recursively—even when capture failed and wrote no PNG. Never
   leave the child merely because the CLI is unsupported, the bridge or host is
   unavailable, reload or capture failed, or review could not continue. Never
   delete the selected parent, pre-existing files, sibling directories created
   by earlier or concurrent workflows, the PBIP project, or any broader path.
   Keep the shared `Screenshots` and `Power BI Report Authoring` parents even
   when empty.
8. Retry a failed deletion once. If it still fails, report the exact remaining
   path and require manual cleanup. Do not claim cleanup after an abrupt host or
   agent termination that prevented this step from running.

Treat a user-requested screenshot saved to an explicitly supplied final file or
directory as retained output, not as a mandatory validation artifact. Warn
about unsafe project, Git, or synchronized destinations, but do not
automatically delete explicitly retained output.
