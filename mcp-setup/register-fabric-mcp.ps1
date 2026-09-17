<#
.SYNOPSIS
    Registers a Fabric MCP server with GitHub Copilot CLI and other AI tools.

.DESCRIPTION
    This script adds MCP server configuration to your local AI tool configs,
    enabling Fabric operations through natural language.

.PARAMETER ServerUrl
    The URL of the Fabric MCP server.

.PARAMETER ServerName
    Local name for the server (default: fabric).

.PARAMETER AuthType
    Authentication type: none, bearer, api-key (default: none).

.PARAMETER Token
    Authentication token (required if AuthType is bearer or api-key).

.PARAMETER Tool
    Which tool to configure: copilot, claude, vscode, all (default: all).

.PARAMETER Headers
    Hashtable of custom HTTP headers to include in the MCP server config (e.g., @{"X-VARIANTS"="Fabric.Routing.FabricIQ.V1"}).

.EXAMPLE
    .\register-fabric-mcp.ps1 -ServerUrl "https://fabric-mcp.example.com" -ServerName "fabric"

.EXAMPLE
    .\register-fabric-mcp.ps1 -ServerUrl "https://fabric-mcp.example.com" -AuthType bearer -Token $env:FABRIC_TOKEN

.EXAMPLE
    # Register FabricIQ with live token and required headers
    $token = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
    .\register-fabric-mcp.ps1 -ServerUrl "https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq" `
      -ServerName "FabricIQ" -AuthType bearer -Token $token `
      -Headers @{ "X-VARIANTS" = "Fabric.Routing.FabricIQ.V1" }
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerUrl,
    
    [string]$ServerName = "fabric",
    
    [ValidateSet("none", "bearer", "api-key")]
    [string]$AuthType = "none",
    
    [string]$Token = "",
    
    [hashtable]$Headers = @{},
    
    [ValidateSet("copilot", "claude", "vscode", "all")]
    [string]$Tool = "all"
)

$ErrorActionPreference = "Stop"

function Write-Status($message) {
    Write-Host "[*] $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "[+] $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "[!] $message" -ForegroundColor Yellow
}

function Add-McpServer($configPath, $toolName, $serverConfig) {
    Write-Status "Configuring $toolName..."
    
    $configDir = Split-Path $configPath -Parent
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    }
    
    if (Test-Path $configPath) {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json -AsHashtable
    } else {
        $config = @{}
    }
    
    if (-not $config.ContainsKey("mcpServers")) {
        $config["mcpServers"] = @{}
    }
    
    $config["mcpServers"][$ServerName] = $serverConfig
    
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    Write-Success "$toolName configured at $configPath"
}

# Build server configuration
$serverConfig = @{
    url = $ServerUrl
    transport = "http"
}

if ($Headers.Count -gt 0) {
    $serverConfig["headers"] = $Headers
}

# Copilot's mcp.json expands ${VAR} placeholders itself, so a token-less run can
# still write a usable entry there. Claude's bridge cannot -- see the Claude
# block below -- so remember whether a concrete token was actually supplied.
$hasConcreteToken = -not [string]::IsNullOrEmpty($Token)

if ($AuthType -ne "none") {
    if (-not $hasConcreteToken) {
        Write-Warning "AuthType is '$AuthType' but no token provided. Using environment variable reference."
        $Token = "`${FABRIC_MCP_TOKEN}"
    }
    $serverConfig["auth"] = @{
        type = $AuthType
        token = $Token
    }
}

# Configure tools
if ($Tool -eq "copilot" -or $Tool -eq "all") {
    $copilotConfig = Join-Path $env:USERPROFILE ".copilot\mcp.json"
    Add-McpServer $copilotConfig "GitHub Copilot CLI" $serverConfig
}

if ($Tool -eq "claude" -or $Tool -eq "all") {
    $claudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

    # Claude Desktop speaks stdio, so a remote HTTP server needs a bridge.
    # mcp-remote forwards arbitrary headers with a repeatable --header flag,
    # which is what carries X-VARIANTS and the bearer token. Pinned so the
    # generated config is reproducible and not silently upgraded by npx.
    $mcpRemoteVersion = "0.8.3"  # Update this when upgrading
    $claudeArgs = @("-y", "mcp-remote@$mcpRemoteVersion", $ServerUrl)
    $claudeEnv = @{}

    foreach ($key in $Headers.Keys) {
        # No space after the colon: Claude Desktop on Windows (and Cursor)
        # mangles arguments that contain spaces.
        $claudeArgs += @("--header", "${key}:$($Headers[$key])")
    }

    if ($AuthType -eq "bearer" -and $hasConcreteToken) {
        # The token contains a space after "Bearer", so it goes through env
        # rather than inline in the argument vector.
        $claudeArgs += @("--header", 'Authorization:${FABRIC_MCP_AUTH}')
        $claudeEnv["FABRIC_MCP_AUTH"] = "Bearer $Token"
    }
    elseif ($AuthType -eq "bearer") {
        # Claude's JSON "env" values are passed to the child process verbatim --
        # they are not shell-expanded -- so baking the ${FABRIC_MCP_TOKEN}
        # placeholder in here would send that literal string as the credential.
        # Copilot's mcp.json does expand it, which is why only this path opts out.
        Write-Warning "No -Token was supplied, so no Authorization header was written for Claude Desktop. Unlike Copilot's mcp.json, Claude does not expand `${FABRIC_MCP_TOKEN} placeholders. Re-run with -Token `$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)."
    }
    elseif ($AuthType -ne "none") {
        # Only bearer can be bridged automatically. "Authorization: api-key <key>"
        # is not a real auth scheme, and there is no universal API-key header name
        # to guess -- services use X-API-Key, api-key, Ocp-Apim-Subscription-Key
        # and others. Writing a wrong header silently is worse than writing none,
        # so point at -Headers, which the loop above forwards verbatim.
        Write-Warning "AuthType '$AuthType' cannot be bridged to Claude Desktop automatically; no Authorization header was written. Re-run with -Headers @{ '<YourKeyHeader>' = '<key>' } to send the key under the header your service expects."
    }

    $claudeServerConfig = @{
        command = "npx"
        args    = $claudeArgs
    }
    if ($claudeEnv.Count -gt 0) {
        $claudeServerConfig["env"] = $claudeEnv
    }

    Add-McpServer $claudeConfig "Claude Desktop" $claudeServerConfig
}

if ($Tool -eq "vscode" -or $Tool -eq "all") {
    if ($Headers.Count -gt 0 -or $AuthType -ne "none") {
        Write-Warning "This script writes a URL-only entry for VS Code; headers/auth will NOT be applied and FabricIQ will fail to authenticate. VS Code does support headers -- see mcp-setup/README.md for a working hand-written mcp.json."
    }
    $vscodeConfig = Join-Path $env:APPDATA "Code\User\settings.json"
    if (Test-Path $vscodeConfig) {
        Write-Status "Configuring VS Code..."
        $settings = Get-Content $vscodeConfig -Raw | ConvertFrom-Json -AsHashtable
        
        if (-not $settings.ContainsKey("github.copilot.chat.mcpServers")) {
            $settings["github.copilot.chat.mcpServers"] = @{}
        }
        $settings["github.copilot.chat.mcpServers"][$ServerName] = @{ url = $ServerUrl }
        
        $settings | ConvertTo-Json -Depth 10 | Set-Content $vscodeConfig -Encoding UTF8
        Write-Success "VS Code configured"
    } else {
        Write-Warning "VS Code settings not found at $vscodeConfig"
    }
}

Write-Host ""
Write-Success "Fabric MCP server '$ServerName' registered successfully!"
Write-Host ""
Write-Host "To verify, run in Copilot CLI:" -ForegroundColor White
Write-Host "  /mcp list" -ForegroundColor Gray

