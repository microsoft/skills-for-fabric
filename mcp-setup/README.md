# Fabric MCP setup for local Claude Code and Codex

> For this preview, use [PREVIEW.md](../PREVIEW.md) instead of the production
> plugin-install commands below.

The remote Fabric MCPs accept tokens from an existing Azure CLI sign-in.
Azure CLI must be installed in the same environment as the client. Check
the selected tenant without printing credentials:

```bash
az account show --query tenantId --output tsv
```

If needed, run `az login --tenant <tenant-id> --allow-no-subscriptions`.
Do not sign in again if the existing session works. Workspace permissions,
tenant policies and consent still apply. Claude/Codex chat authentication is
separate; this setup does not configure hosted Claude connectors.

## Claude Code

Install or update the plugin, then start a new Claude process:

```bash
claude plugin marketplace add microsoft/skills-for-fabric
claude plugin install fabric-skills@fabric-collection
# For an existing installation:
claude plugin update fabric-skills@fabric-collection
claude mcp list
```

The plugin supplies a native Azure CLI `headersHelper` for its three remote
MCPs. No extra helper runtime, copied token or new OAuth application is needed.
Read each server's status: installation success or exit code zero does not
mean all MCPs connected. Inside Claude, use `/mcp`.

An older local/user/project registration can override the plugin's entry.
If an obsolete local `FabricIQ` entry is failing, remove only that entry
with the user's approval, then recheck:

```bash
claude mcp remove --scope local FabricIQ
claude mcp list
```

Use the actual name and scope shown in `/mcp`; do not remove working custom
authentication or unrelated servers. The raw repository `.mcp.json` files
are Copilot-oriented; use the Claude plugin instead of copying those files.

## Codex

Use Codex **0.153.4 or newer**. Add or merge these entries into
`~/.codex/config.toml`, preserving unrelated settings. If a table already
exists, edit it rather than adding a duplicate. Codex does not read Claude's
plugin configuration, and `AGENTS.md` alone does not register MCPs.

```toml
[mcp_servers.FabricIQ]
url = "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365"
http_headers = { "X-VARIANTS" = "Fabric.Routing.PowerBIDataExploration" }
http_headers_helper = '''az account get-access-token --resource https://api.fabric.microsoft.com --query "{Authorization: join(' ', ['Bearer', accessToken])}" --output json --only-show-errors'''

[mcp_servers.powerbi-modeling-mcp]
url = "https://api.fabric.microsoft.com/v1/mcp/powerbi/authoring"
http_headers_helper = '''az account get-access-token --resource https://api.fabric.microsoft.com --query "{Authorization: join(' ', ['Bearer', accessToken])}" --output json --only-show-errors'''

[mcp_servers.fabric-sqlendpoint]
url = "https://api.fabric.microsoft.com/v1/mcp/dataPlane/sqlEndpoint"
http_headers_helper = '''az account get-access-token --resource https://api.fabric.microsoft.com --query "{Authorization: join(' ', ['Bearer', accessToken])}" --output json --only-show-errors'''
```

Keep an existing working stdio Power BI modeling server rather than replacing
it with the remote entry above. Trusted project or managed configuration can
take precedence over user settings.

When intentionally switching an existing HTTP entry to this helper, remove
its conflicting static bearer/Authorization settings. Stored OAuth credentials
can also take precedence; clear only that MCP's credentials with
`codex mcp logout <server-name>`, with user approval. Restart Codex and check
`/mcp`; `codex mcp list` alone shows configuration, not successful tool discovery.

## Authentication failures

- Verify Azure CLI is available and signed in where the client actually runs.
  A Windows sign-in is not automatically available inside WSL or a container.
- Check token acquisition safely with
  `az account get-access-token --resource https://api.fabric.microsoft.com --query expiresOn --output tsv`.
- Some client versions fall back to OAuth when the header command fails,
  producing the dynamic-registration error. Check Azure sign-in and older
  registrations before repeating OAuth login.
- Use current clients. Token-refresh behavior varies by version; reconnect or
  restart if necessary. A successful connection check does not validate expiry
  recovery or every Fabric workload operation.
- Never run the credential-producing header command in chat or paste its output
  into configuration. It is consumed privately by the MCP client.

The separate `powerbi-authoring` stdio plugin is unchanged. In the legacy
`register-fabric-mcp` scripts, the `claude` target means Claude Desktop,
not Claude Code; do not use it to repair these connections.

References: [Claude dynamic headers](https://code.claude.com/docs/en/mcp#use-dynamic-headers-for-custom-authentication)
and [Codex MCP configuration](https://developers.openai.com/codex/mcp).
