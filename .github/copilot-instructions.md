# Copilot Instructions for skills-for-fabric Repository

This repository contains AI coding assistant skills for Microsoft Fabric.

## Repository Structure

- `.github/skills/` - Meta-skills for repository contributors
- `mcp-setup/` - Scripts to register external MCP servers
- `compatibility/` - Cross-tool configuration files

## When Adding or Modifying Skills

### SKILL.md Requirements

Every skill, other than check-updates, must have a `SKILL.md` with:

1. **YAML frontmatter** with `name` and `description`
2. Check for updates notice at the top of the file (multi-line blockquote):
   ```
   > **Update Check — ONCE PER SESSION (mandatory)**
   > The first time this skill is used in a session, run the **check-updates** skill before proceeding.
   > - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill (e.g., `/fabric-skills:check-updates`).
   > - **Claude Code / Cowork / Cursor / Windsurf / Codex**: read the local `package.json` version, then compare it against the remote version via `git fetch origin main --quiet && git show origin/main:package.json` (or the GitHub API). If the remote version is newer, show the changelog and update instructions.
   > - Skip if the check was already performed earlier in this session.
   ```
3. Check for instructions on how to find workspaces or items in Fabric:
   ```   
   > **CRITICAL NOTES**
   > 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
   > 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering
   ``` 
4. **Must/Prefer/Avoid** sections for clear guidance
5. **Examples** section with code or prompt/response pairs

### Naming Conventions

- End-to-end skills: `e2e-{task-name}` (e.g., `e2e-medallion-architecture`)
- Developer skills: `{endpoint_or_engine}-authoring-{access_method}` (e.g., `sqldw-authoring-cli`)
- Consumer skills: `{endpoint_or_engine}-consumption-{access_method}` (e.g., `sqldw-consumption-cli`)
- Operations skills: `{endpoint_or_engine}-operations-{access_method}` (e.g., `sqldw-operations-cli`)
- Agents: `{persona}` (e.g., `FabricDataEngineer`) for cross-endpoint orchestration

### Description Field

Write descriptions that enable accurate skill discovery:
- Start with an action verb
- Mention specific technologies (SDKs, languages, tools)
- Distinguish from similar skills

## Key References

- **Fabric REST APIs**: https://learn.microsoft.com/en-us/rest/api/fabric/articles/
- **Fabric Documentation**: https://learn.microsoft.com/en-us/fabric/

## Two User Personas

### Developers (`-authoring-` skills)
Target users who write code: SDKs, APIs, automation scripts, CI/CD, infrastructure-as-code.

### Consumers (`-consumption-` skills)
Target users who interact via CLI/AI: run queries, explore data, ad-hoc operations.

### Operations (`-operations-` skills)
Target users diagnosing performance and health: system view queries, multi-step investigation workflows, threshold-based recommendations.

## Cross-Tool Compatibility

When modifying skills, ensure compatibility files in `compatibility/` are updated:
- `CLAUDE.md` for Claude Code
- `.cursorrules` for Cursor
- `AGENTS.md` for Codex/Jules/OpenCode
- `.windsurfrules` for Windsurf
- `GEMINI.md` for Gemini CLI (imports `@./AGENTS.md`; no separate edits)
