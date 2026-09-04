[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$InputPath,

    [Parameter(Mandatory)]
    [string]$OutputPath,

    [switch]$AllowTrustedProjectBuild
)

$ErrorActionPreference = 'Stop'
$project = Join-Path $PSScriptRoot 'dedicated-pool-tool/DedicatedPoolTool.csproj'
$savedSdkPath = $env:MSBuildSDKsPath
try {
    Remove-Item Env:MSBuildSDKsPath -ErrorAction SilentlyContinue
    $resolvedInputPath = (Resolve-Path -LiteralPath $InputPath).Path
    $toolArguments = @($resolvedInputPath, $OutputPath)
    if ($AllowTrustedProjectBuild) {
        $toolArguments += '--allow-trusted-project-build'
    }
    dotnet run --project $project -- $toolArguments
}
finally {
    if ($null -ne $savedSdkPath) {
        $env:MSBuildSDKsPath = $savedSdkPath
    }
}
if ($LASTEXITCODE -ne 0) {
    throw "Dedicated Pool discovery failed with exit code $LASTEXITCODE."
}