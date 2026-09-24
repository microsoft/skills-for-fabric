# Python helper runtime

Read this reference before invoking any script under `skills/project-osmos/scripts/`.

The helpers use only the Python standard library and require Python 3.11 or newer. They do not require a dependency sync or a dedicated Project Osmos environment.

## Select one existing interpreter

Resolve the runner once and reuse it for every helper in the task:

1. If a virtual or Conda environment is active, use its `python` when it is Python 3.11+.
2. Otherwise, if the current project already has a `uv` environment, use `uv run --no-sync python`. Use `--active` only when the active environment must win.
3. Otherwise scan existing `python` and `python3` commands in `PATH`, deduplicate aliases to the same interpreter, and use the first Python 3.11+ candidate.

Do not invoke `uv run` unless the environment already exists. Do not create `.venv`, alter dependency manifests or lockfiles, install packages, or switch interpreters during the task.

For the Bash examples, retain the selected command as the `PYTHON_RUNNER`
array. For a resolved executable path, use `PYTHON_RUNNER=("$selected_python")`;
if the selected runner is the existing uv environment, use
`PYTHON_RUNNER=(uv run --no-sync python)` (including `--active` when selected).
Invoke it as `"${PYTHON_RUNNER[@]}"` so paths with spaces and multi-argument
runners remain intact. Keep this same array for authentication, task-link
launching, and continuation; do not perform a fresh `python3` lookup. In other
shells, preserve the same selected executable and argument list using that
shell's native syntax.

Each helper enforces the same minimum before doing work. If an interpreter is too old, report the path and version from the helper error once. Treat a failed sibling-module import as an invocation-path or interpreter problem, not a reason to install a package.

This contract applies only to the local helpers. Do not add Python environment instructions to the remote Project Osmos task.
