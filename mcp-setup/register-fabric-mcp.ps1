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
    Hashtable of custom HTTP headers to include in the MCP server config (e.g., @{"X-VARIANTS"="Fabric.Routing.PowerBIDataExploration"}).

.EXAMPLE
    .\register-fabric-mcp.ps1 -ServerUrl "https://fabric-mcp.example.com" -ServerName "fabric"

.EXAMPLE
    .\register-fabric-mcp.ps1 -ServerUrl "https://fabric-mcp.example.com" -AuthType bearer -Token $env:FABRIC_TOKEN

.EXAMPLE
    # Register FabricIQ with live token and required headers
    $token = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
    .\register-fabric-mcp.ps1 -ServerUrl "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365" `
      -ServerName "FabricIQ" -AuthType bearer -Token $token `
      -Headers @{ "X-VARIANTS" = "Fabric.Routing.PowerBIDataExploration" }
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

if ($AuthType -ne "none") {
    if ([string]::IsNullOrEmpty($Token)) {
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
    if ($Headers.Count -gt 0 -or $AuthType -ne "none") {
        Write-Warning "Claude Desktop uses mcp-proxy and does not support custom headers or auth config directly. Headers/auth will not be applied to this target."
    }
    $claudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
    # Claude uses a different format with command/args for remote servers
    # Version pinned for security and reproducibility
    $mcpProxyVersion = "0.1.0"  # Update this when upgrading
    $claudeServerConfig = @{
        command = "npx"
        args = @("-y", "@anthropic/mcp-proxy@$mcpProxyVersion", $ServerUrl)
    }
    Add-McpServer $claudeConfig "Claude Desktop" $claudeServerConfig
}

if ($Tool -eq "vscode" -or $Tool -eq "all") {
    if ($Headers.Count -gt 0 -or $AuthType -ne "none") {
        Write-Warning "VS Code MCP config supports URL only. Headers/auth will not be applied to this target."
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

