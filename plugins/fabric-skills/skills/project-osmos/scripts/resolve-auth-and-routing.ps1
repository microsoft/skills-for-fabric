# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
<#
.SYNOPSIS
PowerShell entry point for resolving Project Osmos auth, token, and task routing.

.DESCRIPTION
Runs the same tested Python resolver as resolve-auth-and-routing.py and writes
env.ps1, env.sh, routing.json, and a private MWC token file under OutputDir.
Use this entry point from Windows PowerShell or cross-platform pwsh.
#>
[CmdletBinding()]
param(
    [Alias("TenantId")]
    [string]$ResourceTenantId,

    [Parameter(Mandatory = $true)]
    [string]$WorkspaceId,

    [Parameter(Mandatory = $true)]
    [string]$LakehouseId,

    [string]$OutputDir,

    [string]$FabricApiHost,

    [string]$PortalUrl,

    [string]$ExistingRouting,

    [string]$WorkloadType = "SparkCore",

    [double]$Timeout = 60,

    [string]$TokenResource = "https://analysis.windows.net/powerbi/api",

    [string]$PythonCommand = "",

    [string]$ExpectedCapacityId,

    [ValidateSet("execute", "inspect")]
    [string]$Purpose = "execute",

    [switch]$AllowUnknownCapacity,

    [switch]$CheckCapacityOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $CheckCapacityOnly -and [string]::IsNullOrWhiteSpace($OutputDir)) {
    throw "OutputDir is required unless CheckCapacityOnly is specified."
}

function Resolve-PythonInvocation {
    param([string]$RequestedCommand)

    if (-not [string]::IsNullOrWhiteSpace($RequestedCommand)) {
        $requested = Get-Command $RequestedCommand -ErrorAction SilentlyContinue
        if ($null -eq $requested) {
            throw "Python command not found: $RequestedCommand"
        }
        $requestedInvocation = @{
            FileName = $requested.Source
            PrefixArgs = @()
        }
        $probe = Test-PythonInvocation -Invocation $requestedInvocation
        if (-not $probe.Compatible) {
            throw (
                "Project Osmos helpers require Python 3.11 or newer; " +
                "$($requestedInvocation.FileName) reported Python $($probe.Version). " +
                "Activate or expose a compatible existing interpreter. " +
                "No packages or environments were changed."
            )
        }
        return $requestedInvocation
    }

    $checked = @()
    foreach ($candidate in @(
        @{ Name = "python"; PrefixArgs = @() },
        @{ Name = "python3"; PrefixArgs = @() },
        @{ Name = "py"; PrefixArgs = @("-3") }
    )) {
        $command = Get-Command $candidate.Name -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            $invocation = @{
                FileName = $command.Source
                PrefixArgs = @($candidate.PrefixArgs)
            }
            $probe = Test-PythonInvocation -Invocation $invocation
            if ($probe.Compatible) {
                return $invocation
            }
            $checked += "$($command.Source) (Python $($probe.Version))"
        }
    }

    $checkedText = if ($checked.Count -gt 0) { $checked -join ", " } else { "none found" }
    throw (
        "Project Osmos helpers require an existing Python 3.11 or newer interpreter. " +
        "Checked: $checkedText. Activate or expose a compatible interpreter, or pass " +
        "-PythonCommand. No packages or environments were changed."
    )
}

function Test-PythonInvocation {
    param([hashtable]$Invocation)

    $probeArgs = @($Invocation.PrefixArgs) + @(
        "-c",
        "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    )
    $versionOutput = & $Invocation.FileName @probeArgs 2>$null
    $exitCode = $LASTEXITCODE
    return @{
        Compatible = $exitCode -eq 0
        Version = if ($versionOutput) { @($versionOutput)[-1] } else { "unknown" }
    }
}

$python = Resolve-PythonInvocation -RequestedCommand $PythonCommand
$scriptPath = Join-Path $PSScriptRoot "resolve-auth-and-routing.py"
$arguments = @()
$arguments += @($python.PrefixArgs)
$arguments += @(
    $scriptPath,
    "--workspace-id", $WorkspaceId,
    "--lakehouse-id", $LakehouseId,
    "--workload-type", $WorkloadType,
    "--timeout", ([string]$Timeout),
    "--token-resource", $TokenResource
)
if ($FabricApiHost) { $arguments += @("--fabric-api-host", $FabricApiHost) }
if ($PortalUrl) { $arguments += @("--portal-url", $PortalUrl) }
if ($ExistingRouting) { $arguments += @("--existing-routing", $ExistingRouting) }
if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
    $arguments += @("--output-dir", $OutputDir)
}
if (-not [string]::IsNullOrWhiteSpace($ResourceTenantId)) {
    $arguments += @("--resource-tenant-id", $ResourceTenantId)
}
$arguments += @("--purpose", $Purpose)
if ($ExpectedCapacityId) { $arguments += @("--expected-capacity-id", $ExpectedCapacityId) }
if ($AllowUnknownCapacity) { $arguments += "--allow-unknown-capacity" }
if ($CheckCapacityOnly) { $arguments += "--check-capacity-only" }

& $python.FileName @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($CheckCapacityOnly) { exit 0 }

$envScript = Join-Path $OutputDir "env.ps1"
Write-Host ""
Write-Host "PowerShell env file: $envScript"
Write-Host "Run: . '$envScript'"
