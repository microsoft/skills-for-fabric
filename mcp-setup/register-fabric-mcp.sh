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
#   --allow-insecure-http Allow non-loopback HTTP on a trusted network (loopback needs no flag)
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
ALLOW_INSECURE_HTTP="false"

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
        --allow-insecure-http)
            ALLOW_INSECURE_HTTP="true"
            shift
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

if [[ "$SERVER_URL" == *\\* ]] || ! parsed_url=$(jq -ern --arg url "$SERVER_URL" '
    def ipv4:
        split(".")
        | select(length == 4 and all(.[]; test("^(0|[1-9][0-9]{0,2})$")))
        | map(tonumber) | select(all(.[]; . <= 255));
    def hex_word:
        . as $value | [4096, 256, 16, 1]
        | map((($value / . | floor) % 16) as $digit | "0123456789abcdef"[$digit:($digit + 1)])
        | join("");
    def words: if . == "" then [] else split(":") end;
    def ipv6:
        if contains(".") then
            capture("^(?<prefix>.*:)(?<tail>[0-9.]+)$") as $mixed
            | ($mixed.tail | ipv4) as $ip
            | $mixed.prefix + (($ip[0] * 256 + $ip[1]) | hex_word)
                + ":" + (($ip[2] * 256 + $ip[3]) | hex_word)
        else . end
        | split("::") as $groups
        | ($groups[0] | words) as $left
        | if ($groups | length) == 1 then $left
          elif ($groups | length) == 2 then
            ($groups[1] | words) as $right
            | (($left + $right) | length) as $count
            | select($count < 8)
            | $left + [range($count; 8) | "0"] + $right
          else empty end
        | select(length == 8 and all(.[]; test("^[0-9a-fA-F]{1,4}$")));
    select($url | test("[\\s\\x00-\\x1f\\x7f<>\"\\\\]|%(?![0-9a-fA-F]{2})") | not)
    | ($url | capture("^(?<scheme>https?)://(?<host>\\[[0-9a-fA-F:.]+\\]|[^/:?#@]+)(?::(?<port>[0-9]+))?(?:[/?#].*)?$"; "i"))
    | select(.port == null or (.port | tonumber) <= 65535)
    | if (.host | startswith("[")) then
        (.host[1:-1] | ipv6) as $words
        | . + {loopback: (
            (($words[:7] | all(.[]; test("^0+$"))) and ($words[7] | test("^0{0,3}1$")))
            # IPv4-mapped 127/8 is loopback too, matching IPAddress.IsLoopback.
            or (($words[:5] | all(.[]; test("^0+$")))
                and ($words[5] | test("^ffff$"; "i"))
                and ($words[6] | test("^7f[0-9a-f]{2}$"; "i")))
        )}
      elif (.host | test("^[0-9.]+$")) then
        (.host | ipv4) as $ip | . + {loopback: ($ip[0] == 127)}
      else
        select(.host | test("^[\\p{L}\\p{N}_-]+(\\.[\\p{L}\\p{N}_-]+)*\\.?$"))
        | . + {loopback: ((.host | ascii_downcase) == "localhost")}
      end
    | [(.scheme | ascii_downcase), .loopback] | @tsv
' 2>/dev/null); then
    echo "Error: --server-url must be an absolute HTTP or HTTPS URL with a hostname and no credentials, whitespace, or control characters." >&2
    exit 1
fi
parsed_url=${parsed_url%$'\r'}
IFS=$'\t' read -r URL_SCHEME URL_IS_LOOPBACK <<< "$parsed_url"
if [[ "$URL_SCHEME" == "http" && "$URL_IS_LOOPBACK" != "true" ]]; then
    if [[ "$ALLOW_INSECURE_HTTP" != "true" ]]; then
        echo "Error: non-loopback HTTP requires --allow-insecure-http. Prefer HTTPS; opt in only on a trusted network." >&2
        exit 1
    fi
    warning "HTTP is unencrypted; server traffic and credentials can be intercepted."
fi

# Build auth config
# Copilot's mcp.json expands ${VAR} placeholders itself, so a token-less run can
# still write a usable entry there. Claude's bridge cannot -- see configure_claude
# -- so remember whether a concrete token was actually supplied.
HAS_CONCRETE_TOKEN="false"
[[ -n "$TOKEN" ]] && HAS_CONCRETE_TOKEN="true"
AUTH_CONFIG="null"
if [[ "$AUTH_TYPE" != "none" ]]; then
    if [[ "$HAS_CONCRETE_TOKEN" != "true" ]]; then
        warning "AuthType is '$AUTH_TYPE' but no token provided. Using environment variable reference."
        TOKEN="\${FABRIC_MCP_TOKEN}"
    fi
    AUTH_CONFIG=$(jq -n --arg type "$AUTH_TYPE" --arg token "$TOKEN" \
        '{type: $type, token: $token}')
fi

# Build headers config
HEADERS_CONFIG="null"
if [[ -n "$HEADERS" ]]; then
    if ! printf '%s\n' "$HEADERS" | jq -e 'type == "object" and all(.[]; type == "string")' > /dev/null 2>&1; then
        echo "Error: --headers must be a JSON object with string values." >&2
        exit 1
    fi
    HEADERS_CONFIG="$HEADERS"
fi

# Configure GitHub Copilot CLI
configure_copilot() {
    local config_path="$HOME/.copilot/mcp.json"
    status "Configuring GitHub Copilot CLI..."
    
    if [[ -f "$config_path" ]]; then
        local existing=$(cat "$config_path")
    else
        local existing="{}"
    fi
    
    local server_config
    server_config=$(jq -n --arg url "$SERVER_URL" \
        --argjson headers "$HEADERS_CONFIG" --argjson auth "$AUTH_CONFIG" \
        '{url: $url, transport: "http"}
         + (if $headers != null then {headers: $headers} else {} end)
         + (if $auth != null then {auth: $auth} else {} end)')
    local updated
    updated=$(printf '%s\n' "$existing" | jq -e --arg name "$SERVER_NAME" \
        --argjson server "$server_config" '.mcpServers[$name] = $server')
    mkdir -p "$(dirname "$config_path")"
    printf '%s\n' "$updated" > "$config_path"
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
        --arg scheme "$URL_SCHEME" \
        --argjson headers "$headers_json" \
        '["-y", ("mcp-remote@" + $ver), $url]
         + (if $scheme == "http" then ["--allow-http"] else [] end)
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
    
    local updated
    updated=$(printf '%s\n' "$existing" | jq -e --arg name "$SERVER_NAME" \
        --argjson server "$server_config" '.mcpServers[$name] = $server')
    mkdir -p "$(dirname "$config_path")"
    printf '%s\n' "$updated" > "$config_path"
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
        local updated
        updated=$(jq -e --arg name "$SERVER_NAME" --arg url "$SERVER_URL" \
            '.["github.copilot.chat.mcpServers"][$name] = {url: $url}' "$config_path")
        printf '%s\n' "$updated" > "$config_path"
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
