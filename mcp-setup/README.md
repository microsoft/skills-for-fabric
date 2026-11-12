# Fabric MCP setup for local Claude Code, Codex and VS Code

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
url = "https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq"
http_headers = { "X-VARIANTS" = "Fabric.Routing.FabricIQ.V1" }
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

All three helpers above request the same Fabric resource, so one `az login`
covers every server. FabricIQ also accepts a Power BI token
(`https://analysis.windows.net/powerbi/api`) — both audiences are valid against
its endpoint, so an existing Power BI-audience token keeps working and there is
no need to mint a second one.

When intentionally switching an existing HTTP entry to this helper, remove
its conflicting static bearer/Authorization settings. Stored OAuth credentials
can also take precedence; clear only that MCP's credentials with
`codex mcp logout <server-name>`, with user approval. Restart Codex and check
`/mcp`; `codex mcp list` alone shows configuration, not successful tool discovery.

## VS Code

VS Code has no header-helper equivalent, so the token is supplied through a
prompted input rather than minted per request. Create `.vscode/mcp.json` in the
workspace, or run **MCP: Open User Configuration** for a profile-wide entry:

```json
{
  "servers": {
    "FabricIQ": {
      "type": "http",
      "url": "https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq",
      "headers": {
        "X-VARIANTS": "Fabric.Routing.FabricIQ.V1",
        "Authorization": "Bearer ${input:fabric-token}"
      }
    }
  },
  "inputs": [
    {
      "id": "fabric-token",
      "type": "promptString",
      "description": "Fabric access token",
      "password": true
    }
  ]
}
```

Both the routing header and the token are required; a URL-only entry connects
and then fails on every call. Mint the token with the command below and paste it
at the prompt — VS Code stores it for subsequent sessions, so update the saved
input when it expires (Entra access tokens are short-lived).

```bash
az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken --output tsv
```

Do not commit a token: keep it in the prompted input, never inline in `headers`.

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

## Legacy registration scripts (Claude Desktop)

`register-fabric-mcp.ps1` requires PowerShell 7; `register-fabric-mcp.sh`
requires Bash and `jq`. Both default to `all` (Copilot CLI, Claude Desktop,
and existing VS Code settings). Use `-Tool` / `--tool` to select one target.

The scripts validate the server URL before creating directories or changing
configuration:

- Supply an absolute HTTP or HTTPS URL with a hostname. Embedded credentials,
  whitespace, control characters, and other URL schemes are rejected.
- HTTPS supports custom hosts, including private-network hosts. You are still
  responsible for trusting the endpoint; URL validation does not establish trust.
- HTTP loopback endpoints (`localhost`, IPv4 `127.0.0.0/8`, and IPv6 `::1`) need
  no override.
- Other HTTP endpoints require `-AllowInsecureHttp` /
  `--allow-insecure-http`. Use this only on a trusted network: traffic,
  including authentication headers, is unencrypted. Existing LAN HTTP commands
  must add this flag or switch to HTTPS.

```powershell
# Loopback HTTP does not require -AllowInsecureHttp.
.\mcp-setup\register-fabric-mcp.ps1 `
  -ServerUrl "http://localhost:3000/mcp" -ServerName "local-fabric" -Tool claude

# Explicitly accept unencrypted traffic on a trusted private network.
.\mcp-setup\register-fabric-mcp.ps1 `
  -ServerUrl "http://192.168.1.15:8080/mcp" -Tool claude -AllowInsecureHttp
```

```bash
# Loopback HTTP does not require --allow-insecure-http.
./mcp-setup/register-fabric-mcp.sh \
  --server-url "http://localhost:3000/mcp" --server-name local-fabric --tool claude

# Explicitly accept unencrypted traffic on a trusted private network.
./mcp-setup/register-fabric-mcp.sh \
  --server-url "http://192.168.1.15:8080/mcp" --tool claude --allow-insecure-http
```

### Desktop bridge dependency

Claude Desktop's stdio registration uses the third-party
[`mcp-remote`](https://github.com/punkpeye/mcp-remote) bridge, pinned to
[`0.8.3`](https://github.com/punkpeye/mcp-remote/releases/tag/v0.8.3)
([npm package](https://www.npmjs.com/package/mcp-remote/v/0.8.3)).
It is not an Anthropic package. Node.js and `npx` must be available to Desktop.
Registration only writes configuration; Desktop subsequently launches
`npx -y mcp-remote@0.8.3`. Allowed HTTP endpoints also get `--allow-http`.
Custom headers and concrete bearer tokens retain their existing handling.

An exact version pin prevents an automatic top-level upgrade, but does not
approve a publisher, pin all transitive dependencies, or verify an endpoint.
Before changing the pin, review the npm publisher/distribution, upstream release,
and applicable security advisories; do not substitute a similarly named package.

### Replace an existing legacy proxy entry

Updating these scripts does not repair previously saved configurations.
Before restarting Desktop, inspect its `claude_desktop_config.json` locally
and back it up securely; it can contain credentials. If the affected server's
`npx` arguments still reference `@anthropic/mcp-proxy@0.1.0`, rerun the updated
script with **the same server name**, a trusted URL, and `-Tool claude` /
`--tool claude`. This replaces that entry while preserving unrelated servers
and settings. Re-supply any required headers/authentication intentionally.
For a custom entry, review it first rather than removing or overwriting it
automatically. Restart Desktop after the replacement.

References: [Claude dynamic headers](https://code.claude.com/docs/en/mcp#use-dynamic-headers-for-custom-authentication)
and [Codex MCP configuration](https://developers.openai.com/codex/mcp).
