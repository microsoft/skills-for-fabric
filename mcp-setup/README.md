# MCP Server Registration for Fabric

This folder contains scripts to register external Fabric MCP (Model Context Protocol) servers with your local AI coding tools.

> **Note**: These scripts register MCP servers that are built and hosted elsewhere. They do not create or run the servers themselves.

## Prerequisites

1. **GitHub Copilot CLI** installed and authenticated
2. **Fabric MCP Server** URL (provided by your organization or a third-party)
3. **Authentication credentials** for the MCP server (if required)

## Quick Start

### FabricIQ (Power BI Data Analysis)

FabricIQ is a remote HTTP MCP server hosted by Microsoft Fabric for Power BI data analysis — artifact discovery, schema inspection, DAX generation, and query execution.

**Windows (PowerShell):**

```powershell
.\register-fabric-mcp.ps1 -ServerUrl "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365" `
  -ServerName "FabricIQ" -AuthType bearer `
  -Headers @{"X-VARIANTS"="Fabric.Routing.PowerBIDataExploration"} `
  -Token (az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)
```

**macOS/Linux (Bash):**

```bash
./register-fabric-mcp.sh \
  --server-url "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365" \
  --server-name "FabricIQ" --auth-type bearer \
  --headers '{"X-VARIANTS":"Fabric.Routing.PowerBIDataExploration"}' \
  --token "$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)"
```

> **Note:** The Bearer token expires after ~60-90 minutes. Re-run the command to refresh.

### Custom Fabric MCP Server

```powershell
.\register-fabric-mcp.ps1 -ServerUrl "https://your-fabric-mcp-server.com" -ServerName "fabric"
```

```bash
./register-fabric-mcp.sh --server-url "https://your-fabric-mcp-server.com" --server-name "fabric"
```

## Configuration Options

| Option | Description | Required |
|--------|-------------|----------|
| `ServerUrl` / `--server-url` | URL of the Fabric MCP server | Yes |
| `ServerName` / `--server-name` | Local name for the server (default: `fabric`) | No |
| `AuthType` / `--auth-type` | Authentication type: `none`, `bearer`, `api-key` | No |
| `Token` / `--token` | Authentication token (if required) | Depends |
| `Headers` / `--headers` | Custom HTTP headers. PowerShell: hashtable `@{"X-VARIANTS"="..."}`. Bash: JSON string `'{"X-VARIANTS":"..."}'` | No |

## FabricIQ Details

| Property | Value |
|----------|-------|
| **Server Name** | `FabricIQ` |
| **URL** | `https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365` |
| **Transport** | HTTP (remote) |
| **Auth** | Bearer token (Fabric/Power BI audience) |
| **Required Header** | `X-VARIANTS: Fabric.Routing.PowerBIDataExploration` |
| **Token Audience** | `https://analysis.windows.net/powerbi/api` |
| **Tools** | `DiscoverArtifacts`, `GetReportMetadata`, `GetSemanticModelSchema`, `ValueSearch`, `ExecuteQuery`, `ResolveReportIdFromUrl` |

### Token Acquisition

FabricIQ requires a Bearer token scoped to the Power BI API audience:

```powershell
# Interactive (local dev)
az login
$token = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv

# Service principal (CI)
az login --service-principal -u $env:AZURE_CLIENT_ID -t $env:AZURE_TENANT_ID --certificate $env:AZURE_CLIENT_CERTIFICATE_PATH
$token = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
```

## Manual Configuration

If you prefer to configure manually, edit your MCP configuration file:

### GitHub Copilot CLI

Location: `~/.copilot/mcp.json` (or `%USERPROFILE%\.copilot\mcp.json` on Windows)

```json
{
  "mcpServers": {
    "FabricIQ": {
      "url": "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365",
      "transport": "http",
      "headers": {
        "X-VARIANTS": "Fabric.Routing.PowerBIDataExploration"
      },
      "auth": {
        "type": "bearer",
        "token": "${FABRIC_MCP_TOKEN}"
      }
    }
  }
}
```

### Claude Desktop

Location: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "FabricIQ": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-proxy@0.1.0", "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365"]
    }
  }
}
```

**Note:** Version `0.1.0` is pinned for security and reproducibility. Update the version number when upgrading.

### VS Code (Copilot Extensions)

Add to your VS Code settings.json:

```json
{
  "github.copilot.chat.mcpServers": {
    "FabricIQ": {
      "url": "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365"
    }
  }
}
```

## Template File

Use `mcp-config-template.json` as a starting point for your configuration.

## Verifying Registration

After registration, verify the MCP server is available:

```bash
# In Copilot CLI
/mcp list

# Or test a Fabric operation
"List all workspaces using Fabric MCP"
```

## Troubleshooting

### Server Not Found
- Verify the server URL is correct and accessible
- Check firewall/proxy settings

### Authentication Failed
- Verify your token is valid and not expired
- Check the auth type matches what the server expects

### Connection Timeout
- The MCP server may be starting up (cold start)
- Try again after a few seconds

