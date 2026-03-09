<#
.SYNOPSIS
    Installs Fabric Skills for AI coding tools.

.DESCRIPTION
    This script installs Fabric Skills to your local environment and configures
    cross-tool compatibility files for Claude, Cursor, VS Code, and other AI tools.

.PARAMETER SkillsPath
    Custom path for skills installation. Defaults to ~/.copilot/skills/fabric

.PARAMETER ProjectPath
    Path to project root for compatibility files. Defaults to current directory.

.PARAMETER SkipCompatibility
    Skip copying compatibility files to project root.

.EXAMPLE
    .\install.ps1

.EXAMPLE
    .\install.ps1 -ProjectPath "C:\MyProject" -SkipCompatibility
#>


param(
    [string]$SkillsPath = "",
    [string]$ProjectPath = ".",
    [switch]$SkipCompatibility
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Status($message) { Write-Host "[*] $message" -ForegroundColor Cyan }
function Write-Success($message) { Write-Host "[+] $message" -ForegroundColor Green }
function Write-Info($message) { Write-Host "    $message" -ForegroundColor Gray }

Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   Microsoft Skills for Fabric Installer   ║" -ForegroundColor Magenta  
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# Determine skills installation path
if ([string]::IsNullOrEmpty($SkillsPath)) {
    $SkillsPath = Join-Path $env:USERPROFILE ".copilot\skills\fabric"
}

# Install skills
Write-Status "Installing skills to $SkillsPath"
if (Test-Path $SkillsPath) {
    Write-Info "Removing existing installation..."
    Remove-Item -Recurse -Force $SkillsPath
}

New-Item -ItemType Directory -Force -Path $SkillsPath | Out-Null

# Copy skill folders
$skillsSource = Join-Path $ScriptDir "skills"
$skillFolders = Get-ChildItem -Path $skillsSource -Directory

foreach ($folder in $skillFolders) {
    $dest = Join-Path $SkillsPath $folder.Name
    Copy-Item -Path $folder.FullName -Destination $dest -Recurse
    Write-Info "Installed: $($folder.Name)"
}

Write-Success "Installed $($skillFolders.Count) skills"

# Install compatibility files
if (-not $SkipCompatibility) {
    Write-Host ""
    Write-Status "Setting up cross-tool compatibility..."
    
    $ProjectPath = Resolve-Path $ProjectPath
    $compatDir = Join-Path $ScriptDir "compatibility"
    
    # CLAUDE.md
    $claudeSrc = Join-Path $compatDir "CLAUDE.md"
    $claudeDst = Join-Path $ProjectPath "CLAUDE.md"
    if (-not (Test-Path $claudeDst)) {
        Copy-Item $claudeSrc $claudeDst
        Write-Info "Created: CLAUDE.md (Claude Code)"
    } else {
        Write-Info "Skipped: CLAUDE.md (already exists)"
    }
    
    # .cursorrules
    $cursorSrc = Join-Path $compatDir ".cursorrules"
    $cursorDst = Join-Path $ProjectPath ".cursorrules"
    if (-not (Test-Path $cursorDst)) {
        Copy-Item $cursorSrc $cursorDst
        Write-Info "Created: .cursorrules (Cursor)"
    } else {
        Write-Info "Skipped: .cursorrules (already exists)"
    }
    
    # AGENTS.md
    $agentsSrc = Join-Path $compatDir "AGENTS.md"
    $agentsDst = Join-Path $ProjectPath "AGENTS.md"
    if (-not (Test-Path $agentsDst)) {
        Copy-Item $agentsSrc $agentsDst
        Write-Info "Created: AGENTS.md (Codex/Jules)"
    } else {
        Write-Info "Skipped: AGENTS.md (already exists)"
    }
    
    # .windsurfrules
    $windSrc = Join-Path $compatDir ".windsurfrules"
    $windDst = Join-Path $ProjectPath ".windsurfrules"
    if (-not (Test-Path $windDst)) {
        Copy-Item $windSrc $windDst
        Write-Info "Created: .windsurfrules (Windsurf)"
    } else {
        Write-Info "Skipped: .windsurfrules (already exists)"
    }
    
    Write-Success "Compatibility files configured"
}

Write-Host ""
Write-Success "Installation complete!"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Start a new GitHub Copilot CLI session" -ForegroundColor Gray
Write-Host "  2. Try: 'Help me create a Lakehouse table'" -ForegroundColor Gray
Write-Host "  3. Run /skills list to see available skills" -ForegroundColor Gray
Write-Host ""
