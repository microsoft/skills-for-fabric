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
#     --server-url "https://fabriciq.svc.cloud.microsoft/v1/mcp/fabriciq" \
#     --server-name "FabricIQ" --auth-type bearer \
#     --token "$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)" \
#     --headers '{"X-VARIANTS": "Fabric.Routing.FabricIQ.V1"}'
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
# Copilot's mcp.json expands ${VAR} placeholders itself, so a token-less run can
# still write a usable entry there. Claude's bridge cannot -- see configure_claude
# -- so remember whether a concrete token was actually supplied.
HAS_CONCRETE_TOKEN="false"
[[ -n "$TOKEN" ]] && HAS_CONCRETE_TOKEN="true"
AUTH_CONFIG=""
if [[ "$AUTH_TYPE" != "none" ]]; then
    if [[ "$HAS_CONCRETE_TOKEN" != "true" ]]; then
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
    
    # Claude Desktop speaks stdio, so a remote HTTP server needs a bridge.
    # mcp-remote forwards arbitrary headers with a repeatable --header flag,
    # which is what carries X-VARIANTS and the bearer token. Pinned so the
    # generated config is reproducible and not silently upgraded by npx.
    local mcp_remote_version="0.8.3"  # Update this when upgrading

    # No space after the colon in --header: Claude Desktop on Windows (and
    # Cursor) mangles arguments that contain spaces.
    # Spelled out rather than as a ${HEADERS:-{\}} default: that form is
    # correct but the brace escaping reads like a bug.
    local headers_json="{}"
    if [[ -n "$HEADERS" ]]; then
        headers_json="$HEADERS"
    fi

    local args_json
    args_json=$(jq -n \
        --arg url "$SERVER_URL" \
        --arg ver "$mcp_remote_version" \
        --argjson headers "$headers_json" \
        '["-y", ("mcp-remote@" + $ver), $url]
         + ($headers | to_entries | map("--header", (.key + ":" + .value)))')

    local env_json="{}"
    if [[ "$AUTH_TYPE" == "bearer" && "$HAS_CONCRETE_TOKEN" == "true" ]]; then
        # The token contains a space after "Bearer", so it goes through env
        # rather than inline in the argument vector.
        args_json=$(echo "$args_json" | jq '. + ["--header", "Authorization:${FABRIC_MCP_AUTH}"]')
        env_json=$(jq -n --arg v "Bearer $TOKEN" '{FABRIC_MCP_AUTH: $v}')
    elif [[ "$AUTH_TYPE" == "bearer" ]]; then
        # Claude's JSON "env" values are passed to the child process verbatim --
        # they are not shell-expanded -- so baking the ${FABRIC_MCP_TOKEN}
        # placeholder in here would send that literal string as the credential.
        # Copilot's mcp.json does expand it, which is why only this path opts out.
        warning "No --token was supplied, so no Authorization header was written for Claude Desktop. Unlike Copilot's mcp.json, Claude does not expand \${FABRIC_MCP_TOKEN} placeholders. Re-run with --token \"\$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)\"."
    elif [[ "$AUTH_TYPE" != "none" ]]; then
        # Only bearer can be bridged automatically. "Authorization: api-key <key>"
        # is not a real auth scheme, and there is no universal API-key header name
        # to guess -- services use X-API-Key, api-key, Ocp-Apim-Subscription-Key
        # and others. Writing a wrong header silently is worse than writing none,
        # so point at --headers, which the map above forwards verbatim.
        warning "--auth-type '$AUTH_TYPE' cannot be bridged to Claude Desktop automatically; no Authorization header was written. Re-run with --headers '{\"<YourKeyHeader>\": \"<key>\"}' to send the key under the header your service expects."
    fi

    local server_config
    server_config=$(jq -n \
        --argjson args "$args_json" \
        --argjson env "$env_json" \
        '{command: "npx", args: $args} + (if ($env | length) > 0 then {env: $env} else {} end)')
    
    echo "$existing" | jq ".mcpServers.$SERVER_NAME = $server_config" > "$config_path"
    success "Claude Desktop configured at $config_path"
}

# Configure VS Code
configure_vscode() {
    if [[ -n "$HEADERS" || "$AUTH_TYPE" != "none" ]]; then
        warning "This script writes a URL-only entry for VS Code; headers/auth will NOT be applied and FabricIQ will fail to authenticate. VS Code does support headers -- see mcp-setup/README.md for a working hand-written mcp.json."
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

