#!/bin/bash
#
# Register a Fabric MCP server with GitHub Copilot CLI and other AI tools.
#
# Usage:
#   ./register-fabric-mcp.sh --server-url "https://fabric-mcp.example.com" [options]
#
# Options:
#   --server-url URL      URL of the Fabric MCP server (required)
#   --server-name NAME    Local name for the server (default: fabric)
#   --auth-type TYPE      Authentication: none, bearer, api-key (default: none)
#   --token TOKEN         Authentication token (if required)
#   --headers JSON        Custom HTTP headers as JSON string (e.g., '{"X-VARIANTS": "..."}')
#   --tool TOOL           Tool to configure: copilot, claude, vscode, all (default: all)
#
# Example (FabricIQ):
#   ./register-fabric-mcp.sh \
#     --server-url "https://api.fabric.microsoft.com/v1/mcp/fabricaihub/integrations/m365" \
#     --server-name "FabricIQ" --auth-type bearer \
#     --token "$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)" \
#     --headers '{"X-VARIANTS": "Fabric.Routing.PowerBIDataExploration"}'
#

set -e

# Defaults
SERVER_NAME="fabric"
AUTH_TYPE="none"
TOKEN=""
HEADERS=""
TOOL="all"
SERVER_URL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server-url)
            SERVER_URL="$2"
            shift 2
            ;;
        --server-name)
            SERVER_NAME="$2"
            shift 2
            ;;
        --auth-type)
            AUTH_TYPE="$2"
            shift 2
            ;;
        --token)
            TOKEN="$2"
            shift 2
            ;;
        --headers)
            HEADERS="$2"
            shift 2
            ;;
        --tool)
            TOOL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$SERVER_URL" ]]; then
    echo "Error: --server-url is required"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

status() { echo -e "${CYAN}[*] $1${NC}"; }
success() { echo -e "${GREEN}[+] $1${NC}"; }
warning() { echo -e "${YELLOW}[!] $1${NC}"; }

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required. Install with: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

# Build auth config
AUTH_CONFIG=""
if [[ "$AUTH_TYPE" != "none" ]]; then
    if [[ -z "$TOKEN" ]]; then
        warning "AuthType is '$AUTH_TYPE' but no token provided. Using environment variable reference."
        TOKEN="\${FABRIC_MCP_TOKEN}"
    fi
    AUTH_CONFIG=", \"auth\": {\"type\": \"$AUTH_TYPE\", \"token\": \"$TOKEN\"}"
fi

# Build headers config
HEADERS_CONFIG=""
if [[ -n "$HEADERS" ]]; then
    if ! echo "$HEADERS" | jq empty 2>/dev/null; then
        echo -e "${RED}[✗] --headers value is not valid JSON: $HEADERS${NC}" >&2
        exit 1
    fi
    HEADERS_CONFIG=", \"headers\": $HEADERS"
fi

# Configure GitHub Copilot CLI
configure_copilot() {
    local config_path="$HOME/.copilot/mcp.json"
    status "Configuring GitHub Copilot CLI..."
    
    mkdir -p "$(dirname "$config_path")"
    
    if [[ -f "$config_path" ]]; then
        local existing=$(cat "$config_path")
    else
        local existing="{}"
    fi
    
    local server_config="{\"url\": \"$SERVER_URL\", \"transport\": \"http\"$HEADERS_CONFIG$AUTH_CONFIG}"
    
    echo "$existing" | jq ".mcpServers.$SERVER_NAME = $server_config" > "$config_path"
    success "GitHub Copilot CLI configured at $config_path"
}

# Configure Claude Desktop
configure_claude() {
    if [[ -n "$HEADERS" || "$AUTH_TYPE" != "none" ]]; then
        warning "Claude Desktop uses mcp-proxy and does not support custom headers or auth config directly. Headers/auth will not be applied to this target."
    fi
    local config_path
    if [[ "$OSTYPE" == "darwin"* ]]; then
        config_path="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    else
        config_path="$HOME/.config/claude/claude_desktop_config.json"
    fi
    
    status "Configuring Claude Desktop..."
    mkdir -p "$(dirname "$config_path")"
    
    if [[ -f "$config_path" ]]; then
        local existing=$(cat "$config_path")
    else
        local existing="{}"
    fi
    
    # Claude uses command/args format for remote servers
    # Version pinned for security and reproducibility
    local mcp_proxy_version="0.1.0"  # Update this when upgrading
    local server_config="{\"command\": \"npx\", \"args\": [\"-y\", \"@anthropic/mcp-proxy@$mcp_proxy_version\", \"$SERVER_URL\"]}"
    
    echo "$existing" | jq ".mcpServers.$SERVER_NAME = $server_config" > "$config_path"
    success "Claude Desktop configured at $config_path"
}

# Configure VS Code
configure_vscode() {
    if [[ -n "$HEADERS" || "$AUTH_TYPE" != "none" ]]; then
        warning "VS Code MCP config supports URL only. Headers/auth will not be applied to this target."
    fi
    local config_path="$HOME/.config/Code/User/settings.json"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        config_path="$HOME/Library/Application Support/Code/User/settings.json"
    fi
    
    if [[ -f "$config_path" ]]; then
        status "Configuring VS Code..."
        local server_config="{\"url\": \"$SERVER_URL\"}"
        local updated=$(cat "$config_path" | jq ".[\"github.copilot.chat.mcpServers\"].$SERVER_NAME = $server_config")
        echo "$updated" > "$config_path"
        success "VS Code configured"
    else
        warning "VS Code settings not found at $config_path"
    fi
}

# Run configuration
case $TOOL in
    copilot)
        configure_copilot
        ;;
    claude)
        configure_claude
        ;;
    vscode)
        configure_vscode
        ;;
    all)
        configure_copilot
        configure_claude
        configure_vscode
        ;;
esac

echo ""
success "Fabric MCP server '$SERVER_NAME' registered successfully!"
echo ""
echo "To verify, run in Copilot CLI:"
echo "  /mcp list"

