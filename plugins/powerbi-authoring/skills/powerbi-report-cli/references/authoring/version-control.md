# Version Control for PBIR Editing

> Referenced from SKILL.md. Follow this workflow **before** modifying any report files.

## Pre-Flight: Check for Git Repo

Before making any changes to a PBIP folder, check if it has a git repo:

```bash
git -C "<pbip-folder>" rev-parse --is-inside-work-tree 2>&1
```

| Result | Meaning | Action |
|--------|---------|--------|
| `true` | Git repo exists | Proceed with branching workflow below |
| `fatal: not a git repository` | No repo | Ask user: "This report folder has no git repo. Want me to initialize one so I can safely track and revert changes?" |

If user declines initialization, warn that changes cannot be automatically reverted
and proceed with extra caution (validate before every write).

### Initialize a New Repo (if user approves)

```bash
cd "<pbip-folder>"
git init
git add -A
git commit -m "Initial commit: baseline report state"
```

This creates a clean baseline that all future edits branch from.

---

## Branching Workflow

**Always create a branch before editing report files.** This protects the
user's working state and enables clean revert.

### 1. Create a working branch

```bash
git -C "<pbip-folder>" checkout -b copilot/report-edits
```

Use descriptive branch names when the intent is specific:
- `copilot/add-sales-page`
- `copilot/fix-layout`
- `copilot/apply-dark-theme`

If a `copilot/*` branch already exists from a previous session, check with the
user before reusing or creating a new one.

### 2. Make changes

Edit report files (pages, visuals, filters, formatting) as requested.

### 3. Validate & verify

Run validation after every logical batch of changes:

```bash
powerbi-report-author validate "<path-to-.Report-dir>"
```

If the change affects rendered output, follow `references/authoring/powerbi-desktop.md` for Desktop
reload and screenshot verification. Do not proceed until structural validation
passes and any required visual verification is complete.

### 4. Ask user before committing

**Never auto-commit.** After validation and Desktop verification pass, ask the
user if they want to commit the changes. Show them what was changed and let
them decide.

If the user approves:

```bash
cd "<pbip-folder>"
git add -A
git commit -m "<descriptive message of what changed>"
```

Use clear commit messages that describe the user's intent:
- `"Add Executive Summary page with 4 KPI cards and trend chart"`
- `"Apply dark theme and fix font colors for contrast"`
- `"Add year slicer and region filter to Sales page"`

### 5. Continue or finish

- **More changes requested**: Continue editing on the same branch, validate and
  verify after each batch, ask user before each commit.
- **User satisfied**: Inform user the changes are on branch `copilot/report-edits`
  and they can merge to their main branch when ready.

---

## Reverting Changes

### Revert all uncommitted changes

If edits fail validation or user wants to undo current work-in-progress:

```bash
git -C "<pbip-folder>" checkout -- .
git -C "<pbip-folder>" clean -fd
```

This restores all files to the last committed state and removes any new
untracked files/directories.

### Revert the last commit

If the last committed batch of changes needs to be undone:

```bash
git -C "<pbip-folder>" reset --hard HEAD~1
```

### Revert to the original state (before any copilot edits)

To discard all changes made on the working branch and return to the starting point:

```bash
git -C "<pbip-folder>" checkout main
git -C "<pbip-folder>" branch -D copilot/report-edits
```

Replace `main` with whatever branch was active before the edits began. If unsure,
check with:

```bash
git -C "<pbip-folder>" log --oneline --all --graph | head -20
```

### Revert a specific file

If only one file needs to be restored:

```bash
git -C "<pbip-folder>" checkout HEAD -- "path/to/file.json"
```

---

## Decision Tree

```text
User requests a report change
    │
    ▼
Is the PBIP folder a git repo?
    │
    ├── NO → Ask user to initialize → git init + initial commit
    │
    ▼ YES
    │
Are there uncommitted changes?
    │
    ├── YES → Warn user: "There are uncommitted changes. Shall I commit
    │         them first as a checkpoint, or stash them?"
    │         • Commit: git add -A && git commit -m "checkpoint before copilot edits"
    │         • Stash:  git stash push -m "stashed before copilot edits"
    │
    ▼ NO (clean working tree)
    │
Create working branch → copilot/<intent>
    │
    ▼
Make changes → Validate → Commit
    │
    ├── Validation fails → Revert uncommitted (git checkout -- .)
    │                     → Fix and retry
    │
    ├── User requests revert → git reset --hard HEAD~N or checkout main
    │
    ▼ Success
    │
Inform user: changes committed on branch, ready to merge or use
```

---

## Important Notes

- **Never force-push or rewrite history** on branches the user created.
  Only manage `copilot/*` branches.
- **Check for uncommitted changes** before creating a branch. Dirty working
  trees can cause checkout failures.
- **Commit frequently** — after each validated change set, not at the end
  of a long editing session. This gives fine-grained revert points.
- **The `.pbip` file is outside the `.Report/` directory** — make sure the
  git repo covers the full PBIP folder (the directory containing the `.pbip` file),
  not just the `.Report/` subdirectory.
- **`localSettings.json`** should be in `.gitignore` — it contains user-local
  state that shouldn't be versioned.
