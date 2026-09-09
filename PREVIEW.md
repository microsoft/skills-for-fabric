# Azure CLI MCP authentication preview

This is an opt-in test branch, not a release. The production branch and
marketplace are unchanged. The preview uses marketplace
`fabric-collection-az-preview` and version `0.3.15-az-preview.1`.

## Claude Code

Use a current Claude Code version (connection checks use 2.1.220) and Azure CLI
in the same environment. An existing `az login` is sufficient if it can obtain
a Fabric token; do not sign in again unnecessarily.

If the production `fabric-skills` plugin is enabled, temporarily disable it
for this test, without uninstalling it:

```powershell
claude plugin disable fabric-skills@fabric-collection
```

From the project where you normally launch Claude, clone and install the preview:

```powershell
git clone --branch preview/azure-cli-mcp-auth --single-branch --depth 1 https://github.com/microsoft/skills-for-fabric.git .\fabric-mcp-preview
$preview = (Resolve-Path .\fabric-mcp-preview).Path
claude plugin marketplace add $preview
claude plugin install fabric-skills@fabric-collection-az-preview
claude mcp list
```

No build step or private-repository access is needed. Start a new Claude
process in your normal project, not inside the skills checkout. Use `/plugin`
to confirm that only the preview variant of `fabric-skills` is enabled.

Expect the three `plugin:fabric-skills:` MCPs to connect. An older local,
user or project registration can override them. Review the scope shown by
`/mcp` and follow the [migration guidance](mcp-setup/README.md#claude-code)
before removing only an obsolete entry.

Repeat your original read-only Fabric task and reconnect once. Report the
client version, MCP status and whether the task actually used the MCP.
Do not share tokens. Connection checks alone do not prove every workload
permission or token-expiry recovery. Claude's chat sign-in remains separate.

## Codex

Use Codex 0.153.4 or newer and the [configuration example](mcp-setup/README.md#codex).
Merge only the relevant MCP entries into your existing configuration, preserving
model-provider settings and working connections. Reading `AGENTS.md` does not
register MCPs.

## Restore the production setup

```powershell
claude plugin uninstall fabric-skills@fabric-collection-az-preview
claude plugin marketplace remove fabric-collection-az-preview
# Only if you disabled it for this test:
claude plugin enable fabric-skills@fabric-collection
```

For Codex, restore only the MCP entries you changed. Do not delete an entire
client configuration or sign out of Azure.
