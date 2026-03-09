#!/bin/bash
#
# Microsoft Skills for Fabric Installer
#
# Usage:
#   ./install.sh [options]
#
# Options:
#   --skills-path PATH      Custom skills installation path (default: ~/.copilot/skills/fabric)
#   --project-path PATH     Project root for compatibility files (default: current directory)
#   --skip-compatibility    Skip copying compatibility files
#


set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_PATH=""
PROJECT_PATH="."
SKIP_COMPATIBILITY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skills-path)
            SKILLS_PATH="$2"
            shift 2
            ;;
        --project-path)
            PROJECT_PATH="$2"
            shift 2
            ;;
        --skip-compatibility)
            SKIP_COMPATIBILITY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
WHITE='\033[1;37m'
NC='\033[0m'

status() { echo -e "${CYAN}[*] $1${NC}"; }
success() { echo -e "${GREEN}[+] $1${NC}"; }
info() { echo -e "${GRAY}    $1${NC}"; }

echo ""
echo -e "${MAGENTA}╔═══════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║   Microsoft Skills for Fabric Installer   ║${NC}"
echo -e "${MAGENTA}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Determine skills installation path
if [[ -z "$SKILLS_PATH" ]]; then
    SKILLS_PATH="$HOME/.copilot/skills/fabric"
fi

# Install skills
status "Installing skills to $SKILLS_PATH"

if [[ -d "$SKILLS_PATH" ]]; then
    info "Removing existing installation..."
    rm -rf "$SKILLS_PATH"
fi

mkdir -p "$SKILLS_PATH"

# Copy skill folders
SKILLS_SOURCE="$SCRIPT_DIR/skills"
SKILL_COUNT=0

for folder in "$SKILLS_SOURCE"/*/; do
    folder_name=$(basename "$folder")
    cp -r "$folder" "$SKILLS_PATH/$folder_name"
    info "Installed: $folder_name"
    ((SKILL_COUNT++))
done

success "Installed $SKILL_COUNT skills"

# Install compatibility files
if [[ "$SKIP_COMPATIBILITY" == false ]]; then
    echo ""
    status "Setting up cross-tool compatibility..."
    
    PROJECT_PATH=$(cd "$PROJECT_PATH" && pwd)
    COMPAT_DIR="$SCRIPT_DIR/compatibility"
    
    # CLAUDE.md
    if [[ ! -f "$PROJECT_PATH/CLAUDE.md" ]]; then
        cp "$COMPAT_DIR/CLAUDE.md" "$PROJECT_PATH/CLAUDE.md"
        info "Created: CLAUDE.md (Claude Code)"
    else
        info "Skipped: CLAUDE.md (already exists)"
    fi
    
    # .cursorrules
    if [[ ! -f "$PROJECT_PATH/.cursorrules" ]]; then
        cp "$COMPAT_DIR/.cursorrules" "$PROJECT_PATH/.cursorrules"
        info "Created: .cursorrules (Cursor)"
    else
        info "Skipped: .cursorrules (already exists)"
    fi
    
    # AGENTS.md
    if [[ ! -f "$PROJECT_PATH/AGENTS.md" ]]; then
        cp "$COMPAT_DIR/AGENTS.md" "$PROJECT_PATH/AGENTS.md"
        info "Created: AGENTS.md (Codex/Jules)"
    else
        info "Skipped: AGENTS.md (already exists)"
    fi
    
    # .windsurfrules
    if [[ ! -f "$PROJECT_PATH/.windsurfrules" ]]; then
        cp "$COMPAT_DIR/.windsurfrules" "$PROJECT_PATH/.windsurfrules"
        info "Created: .windsurfrules (Windsurf)"
    else
        info "Skipped: .windsurfrules (already exists)"
    fi
    
    success "Compatibility files configured"
fi

echo ""
success "Installation complete!"
echo ""
echo -e "${WHITE}Next steps:${NC}"
echo -e "${GRAY}  1. Start a new GitHub Copilot CLI session${NC}"
echo -e "${GRAY}  2. Try: 'Help me create a Lakehouse table'${NC}"
echo -e "${GRAY}  3. Run /skills list to see available skills${NC}"
echo ""
