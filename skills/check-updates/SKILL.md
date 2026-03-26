---
name: check-updates
description: >
  Check for skills-for-fabric marketplace updates at session start. Compares local version 
  against GitHub releases and shows changelog if updates are available. Use when the 
  user wants to: (1) check for skill updates, (2) see what's new in skills-for-fabric, 
  (3) verify current version. Triggers: "check for updates", "am I up to date", 
  "what version", "update skills", "show changelog".
---

# Check for Updates

This skill checks for updates to the skills-for-fabric marketplace at the start of each session.

## When to Run

Run this check **once per week** when any skills-for-fabric skill is first invoked. Skip if already checked within the last 7 days.

## Session State

The update check marker is stored in a **persistent, user-level directory** shared across all sessions and all plugins in the Fabric Skills marketplace:

```text
~/.config/fabric-collection/last-update-check.json
```
  
This file contains a JSON object mapping plugin names to the **UTC date** (YYYY-MM-DD) of their last update check:

```json
{
  "skills-for-fabric": "2026-02-17",
  "another-plugin": "2026-02-16"
}
```

Before checking, read `~/.config/fabric-collection/last-update-check.json`:
- If the file exists and the entry for the current plugin is within the last **7 days** (compared to the current **UTC date**), skip the check.
- If the file is missing, the plugin entry is absent, or the date is more than 7 days old (compared to the current **UTC date**), run the update check.

> **IMPORTANT — use UTC consistently**: Always use the current UTC date when saving and comparing the last-update-check timestamp. Do not use the local system timezone, as it varies across environments and can cause the check to run too often or be skipped. In shell, use `date -u +%Y-%m-%d` (Linux/macOS) or `(Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")` (PowerShell).

> **Note**: Create the `~/.config/fabric-collection/` directory if it does not exist. On Windows, use `$env:USERPROFILE\.config\fabric-collection\`.

## Update Check Procedure

### Step 1: Get Local Version

Read the `version` field from the local `package.json` file in the skills-for-fabric installation directory.

### Step 2: Determine Repository Owner and Name

Read the `repository` field from the local `plugin.json` (or `package.json`) to extract the GitHub owner and repo name. Parse the URL to get `owner` and `repo`:

```text
plugin.json → "repository": "https://github.com/<owner>/<repo>"
package.json → "repository.url": "https://github.com/<owner>/<repo>.git"
```

> **CRITICAL**: Use the owner string **exactly as it appears** in the URL. Do NOT alter, normalize, or "correct" the owner name (e.g., do NOT replace underscores with hyphens). The owner `bocrivat_microsoft` uses an **underscore** — this is intentional and correct.

### Step 3: Fetch Latest Release

Use the available tools in your environment to get the latest version. **Try methods in strict order — only fall back to the next method if the previous one fails or is unavailable.**

> **IMPORTANT**: Methods A and B work with both public and private repositories. Method C only works with public repos. Always attempt A or B first.

**Method A — Git CLI (preferred)**

If the skills-for-fabric directory is a Git clone, fetch the remote `package.json` without pulling:

```bash
git fetch origin main --quiet
git show origin/main:package.json
```

Extract the `version` field from the JSON output. This method is the most reliable because it uses the already-configured remote URL and authentication, and avoids any owner/repo name parsing.

**Method B — GitHub MCP tools (preferred for agentic environments)**

If you have access to GitHub MCP server tools (e.g., `get_file_contents`), use them to read the remote `package.json`. Use the owner and repo extracted in Step 2 **exactly as parsed** (do not modify the strings):

```text
get_file_contents(owner: "<owner>", repo: "<repo>", path: "package.json")
```

For this repository, the correct call is:
```text
get_file_contents(owner: "bocrivat_microsoft", repo: "skills-for-fabric", path: "package.json")
```

Extract the `version` field from the response. This method works with private repositories because MCP tools use authenticated GitHub access.

**Method C — GitHub REST API (fallback only, public repos)**

> ⚠️ **Only use this method if Methods A and B both fail or are unavailable.** This method does not work with private repositories.

If the repository is public, make a GET request using the owner/repo from Step 2:

```text
GET https://api.github.com/repos/<owner>/<repo>/releases/latest
```

Extract the `tag_name` field (e.g., `v0.2.0`) and remove the `v` prefix.

> **Note**: This method returns 404 for private repositories. If you receive a 404 error, do NOT assume the repository doesn't exist — retry with Method A or B.

### Step 4: Compare Versions

Compare the local version with the remote version using semantic versioning:
- If remote > local: Update available
- If remote <= local: Up to date

### Step 5: Display Results

#### If Up to Date

Show a brief confirmation and proceed:
```text
✅ skills-for-fabric v0.1.0 is up to date.
```

#### If Update Available

Show detailed information:

```text
╔══════════════════════════════════════════════════════════════════╗
║  🔄 skills-for-fabric Update Available                                ║
║                                                                  ║
║  Current: v0.1.0  →  Latest: v0.2.0                             ║
╚══════════════════════════════════════════════════════════════════╝

## What's New in v0.2.0

[Display relevant CHANGELOG.md entries here]

## Update Commands

Choose the update method based on how you installed skills-for-fabric:

### GitHub Copilot CLI
/plugin update skills-for-fabric@fabric-collection

### Manual (Git clone)
cd /path/to/skills-for-fabric
git pull
./install.ps1   # Windows
./install.sh    # macOS/Linux

─────────────────────────────────────────────────────────────────
Would you like to update now? (The current skill will still work)
```

### Step 6: Set Update Marker

After completing the check (regardless of result), update `~/.config/fabric-collection/last-update-check.json` with today's **UTC date** (YYYY-MM-DD) for the current plugin. Create the directory and file if they don't exist. Preserve entries for other plugins already in the file.

## Must

- Check for updates only once per week (based on UTC calendar date, not session lifetime or local timezone)
- Always proceed with the requested skill after the check (non-blocking)
- Handle network errors gracefully (show warning, continue with skill)
- Display the CHANGELOG.md content for versions between current and latest

## Prefer

- Use Git CLI (Method A) or GitHub MCP tools (Method B) for version checking — these work with private repos
- Fall back to the public GitHub REST API (Method C) **only** if Methods A and B both fail
- Show a concise summary rather than overwhelming detail
- Cache the check result in `~/.config/fabric-collection/last-update-check.json`
- Provide copy-pasteable update commands

## Avoid

- Blocking the user from using skills if update check fails
- Checking on every skill invocation (once per week is sufficient)
- Attempting Method C (public API) before trying Methods A or B
- Relying solely on unauthenticated public API calls (will fail for private repos)
- Auto-updating without user consent

## Error Handling

If the update check fails (network error, API rate limit, etc.):

```text
⚠️ Could not check for skills-for-fabric updates (network error).
   Continuing with current version (v0.1.0).
   Run '/skill check-updates' manually to retry.
```

## Manual Invocation

Users can manually check for updates at any time:
- GitHub Copilot CLI: `/skill check-updates`
- Other tools: Invoke the check-updates skill directly

## Reference

- **GitHub Repository**: https://github.com/microsoft/skills-for-fabric
- **Releases**: https://github.com/microsoft/skills-for-fabric/releases
- **CHANGELOG**: See `CHANGELOG.md` in repository root
