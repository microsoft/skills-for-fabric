param(
    [Parameter(Mandatory = $false)]
    [string]$TestFolder,
    [Parameter(Mandatory = $false)]
    [switch]$SkipCleanup
)

$ErrorActionPreference = "Stop"


# Resolve paths
$evalSource = Join-Path $PSScriptRoot "full-eval-tests"
$repoRoot   = Split-Path -Parent $PSScriptRoot

function Invoke-CopilotMonitored {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prompt,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string]$LogPath,
        [Parameter(Mandatory = $true)]
        [string]$BailOutCode,
        [Parameter(Mandatory = $true)]
        [string]$Context,
        [int]$UnknownOptionThreshold = 3
    )

    if (Test-Path $LogPath) {
        Remove-Item -Path $LogPath -Force
    }

    $job = Start-Job -ScriptBlock {
        param($PromptArg, $WorkingDirectoryArg, $LogPathArg)

        Set-Location $WorkingDirectoryArg
        & copilot --yolo -p $PromptArg 2>&1 | Tee-Object -FilePath $LogPathArg -Append

        [PSCustomObject]@{
            __copilot_exit_code = if ($LASTEXITCODE -ne $null) { [int]$LASTEXITCODE } else { 0 }
        }
    } -ArgumentList $Prompt, $WorkingDirectory, $LogPath

    $unsupportedCount = 0
    while ((Get-Job -Id $job.Id).State -eq 'Running') {
        Start-Sleep -Milliseconds 1000

        if (Test-Path $LogPath) {

            # Detect agent-emitted bail-out codes (EVAL-BAIL-001, EVAL-BAIL-003).
            # The agent writes these when it cannot proceed on a test case. Kill the
            # job immediately so the runner can move to the next plan instead of
            # waiting for the full timeout.
            $agentBail = Select-String -Path $LogPath -Pattern "EVAL-BAIL-00[13]" 2>$null | Select-Object -First 1
            if ($agentBail) {
                $detectedCode = if ($agentBail.Line -match "(EVAL-BAIL-00[13])") { $matches[1] } else { "EVAL-BAIL-00x" }
                Stop-Job -Id $job.Id -ErrorAction SilentlyContinue
                Remove-Job -Id $job.Id -Force -ErrorAction SilentlyContinue
                return [PSCustomObject]@{
                    ExitCode              = 998
                    UnsupportedOptionHits = $unsupportedCount
                    BailedOut             = $true
                    BailOutCode           = $detectedCode
                    Context               = $Context
                }
            }
        }
    }

    $jobOutput = Receive-Job -Id $job.Id -Keep 2>$null
    $jobExitCode = 0
    if ($jobOutput) {
        $exitRecord = $jobOutput | Where-Object { $_ -is [PSCustomObject] -and $_.PSObject.Properties.Name -contains '__copilot_exit_code' } | Select-Object -Last 1
        if ($exitRecord) {
            $jobExitCode = [int]$exitRecord.__copilot_exit_code
        }
    }
    Remove-Job -Id $job.Id -Force -ErrorAction SilentlyContinue

    if (Test-Path $LogPath) {
        Get-Content -Path $LogPath
    }

    if (Test-Path $LogPath) {
        $unsupportedCount = (Select-String -Path $LogPath -SimpleMatch "unknown option '--no-warnings'" 2>$null).Count
    }

    return [PSCustomObject]@{
        ExitCode              = $jobExitCode
        UnsupportedOptionHits = $unsupportedCount
        BailedOut             = $false
        BailOutCode           = $null
        Context               = $Context
    }
}

# Create or resolve TestFolder
if (-not $TestFolder) {
    $guid = [System.Guid]::NewGuid().ToString()
    $TestFolder = Join-Path ([System.IO.Path]::GetTempPath()) $guid
}
if (-not (Test-Path $TestFolder)) {
    New-Item -ItemType Directory -Path $TestFolder -Force | Out-Null
}

Write-Host "========================================="
Write-Host "  Full Eval Runner"
Write-Host "========================================="
Write-Host "  Test folder: $TestFolder"
Write-Host "========================================="

# Clean and copy eval framework
Get-ChildItem -Path $TestFolder -Recurse -Force | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $evalSource "*") -Destination $TestFolder -Recurse -Force
Write-Host "Copied eval framework to: $TestFolder"

# Reinstall the local plugin
copilot plugin marketplace remove fabric-collection --force
copilot plugin marketplace add $repoRoot
copilot plugin install fabric-skills@fabric-collection

# ---------------------------------------------------------------------------
# Discover eval plan files
# ---------------------------------------------------------------------------
$plansDir = Join-Path $TestFolder "plan"
$evalPlans = @()
if (Test-Path $plansDir) {
    $evalPlans += Get-ChildItem -Path $plansDir -Filter "eval-*.md" -File -Recurse
}

if ($evalPlans.Count -eq 0) {
    Write-Error "No eval plan files found."
    return
}

Write-Host "`nFound $($evalPlans.Count) eval plan(s) to execute:`n"
$evalPlans | ForEach-Object { Write-Host "  - $($_.Name)" }

# ---------------------------------------------------------------------------
# Run workspace cleanup (Phase 0)
# ---------------------------------------------------------------------------
if ($SkipCleanup) {
    Write-Host "`n--- Phase 0: Workspace Cleanup (SKIPPED via -SkipCleanup) ---"
}
else {
Write-Host "`n--- Phase 0: Workspace Cleanup ---"
$cleanupPrompt = @"
Follow plan/00-overview.md and execute Phase 0.
"@
$cleanupLog = Join-Path $TestFolder "phase0-cleanup.log"
try {

    Write-Host "========================================="
    Write-Host "  INVOCATION:"
    Write-Host $cleanupPrompt
    Write-Host "========================================="        

    $cleanupRun = Invoke-CopilotMonitored `
        -Prompt $cleanupPrompt `
        -WorkingDirectory $TestFolder `
        -LogPath $cleanupLog `
        -BailOutCode "EVAL-SUITE-021" `
        -Context "Phase 0 cleanup"


    if ($cleanupRun.ExitCode -ne 0) {
        Write-Warning "Cleanup exited with code $($cleanupRun.ExitCode)."
    }
}
catch {
    Write-Warning "Cleanup error: $_"
}

} # end -not SkipCleanup

# ---------------------------------------------------------------------------
# Result folder
# ---------------------------------------------------------------------------
$resultDest = Join-Path $evalSource "result"
if (-not (Test-Path $resultDest)) {
    New-Item -ItemType Directory -Path $resultDest -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Run each eval plan as a SEPARATE copilot session
# ---------------------------------------------------------------------------
$summary = @()
$suiteBailOut = $false
$suiteBailOutCode = $null
$suiteBailOutReason = $null

foreach ($plan in $evalPlans) {
    $planName = $plan.BaseName            # e.g. "eval-medallion"
    $planRelPath = $plan.FullName.Replace($TestFolder, "").TrimStart("\", "/")

    Write-Host "`n=========================================`n"
    Write-Host "  Running: $planName"
    Write-Host "  Plan:    $planRelPath"
    Write-Host "`n=========================================`n"

    # Execute plan according to canonical rules in 00-overview.md
    $skillPrompt = @"
Follow plan/00-overview.md and execute eval plan '$planRelPath'.
Enforce Bailout Conditions exactly as defined in plan/00-overview.md.
"@

    $testStart = Get-Date
    $errorMsg  = $null
    $planRunLog = Join-Path $TestFolder "$planName-run.log"
    $cliUnsupportedOptionCount = 0

    try {

        Write-Host "========================================="
        Write-Host "  INVOCATION:"
        Write-Host $skillPrompt
        Write-Host "========================================="        

        # Note: --no-warnings noise from the CLI fires once per internal tool call during plan
        # execution and is not a meaningful failure signal. Bail-out monitoring is intentionally
        # disabled for plan runs (threshold = MaxValue). EVAL-SUITE-021 still protects Phase 0.
        $planRun = Invoke-CopilotMonitored `
            -Prompt $skillPrompt `
            -WorkingDirectory $TestFolder `
            -LogPath $planRunLog `
            -BailOutCode "EVAL-SUITE-020" `
            -Context $planName `
            -UnknownOptionThreshold ([int]::MaxValue)

        if ($planRun.ExitCode -ne 0) {
            if ($planRun.BailedOut) {
                Write-Warning "  $planName bailed out ($($planRun.BailOutCode)) — agent could not proceed. Continuing to next plan."
            } else {
                $errorMsg = "copilot exited with code $($planRun.ExitCode)"
            }
        }
    }
    catch {
        $errorMsg = $_.ToString()
    }

    $testDuration = ((Get-Date) - $testStart).TotalSeconds
    Write-Host "  Finished: $planName — Duration: $([math]::Round($testDuration, 1)) s"
    if ($errorMsg) {
        Write-Warning "  $planName error: $errorMsg"
    }

    if (Test-Path $planRunLog) {
        $cliUnsupportedOptionCount = (Select-String -Path $planRunLog -SimpleMatch "unknown option '--no-warnings'" 2>$null).Count
    }

    $summary += [PSCustomObject]@{
        Plan     = $planName
        Duration = [math]::Round($testDuration, 1)
        Error    = $errorMsg
    }

    # Copy any result .md files produced
    $mdFiles = Get-ChildItem -Path $TestFolder -Filter "*-results.md" -File 2>$null
    if ($mdFiles) {
        foreach ($f in $mdFiles) {
            Copy-Item -Path $f.FullName -Destination $resultDest -Force
        }
    }

    # Suite-level bailout: stop entire run if this plan contains SKIP/SKIPPED
    $planResult = Get-ChildItem -Path $TestFolder -Filter "$planName-results.md" -File -Recurse 2>$null |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($planResult) {
        $planText = Get-Content -Path $planResult.FullName -Raw
        if ($planText -match '(?im)^\|[^\r\n]*\|\s*SKIP(?:PED)?\s*\|') {
            $suiteBailOut = $true
            $suiteBailOutCode = "EVAL-SUITE-010"
            $suiteBailOutReason = "Detected SKIP/SKIPPED in $($planResult.Name)."

            Write-Error "${suiteBailOutCode}: $suiteBailOutReason Suite aborted to avoid invalid downstream dependency assumptions."
            break
        }
    }

    if ($suiteBailOut) {
        break
    }
}

# ---------------------------------------------------------------------------
# Print execution summary
# ---------------------------------------------------------------------------
Write-Host "`n========================================="
Write-Host "  Eval Execution Summary"
Write-Host "========================================="
$summary | Format-Table -AutoSize
Write-Host "Total plans executed: $($summary.Count)"
Write-Host "Results copied to: $resultDest"

if ($suiteBailOut) {
    Write-Error "${suiteBailOutCode}: $suiteBailOutReason"
    exit 10
}

# ---------------------------------------------------------------------------
# Generate merged eval-results.md summary
# ---------------------------------------------------------------------------
Write-Host "`n--- Generating merged summary ---"

# Build the list of individual result files that were produced
$resultFiles = Get-ChildItem -Path $resultDest -Filter "eval-*-results.md" -File `
    | Where-Object { $_.Name -ne "eval-results.md" }

if ($resultFiles.Count -gt 0) {
    $summaryPrompt = @"
Follow plan/00-overview.md and generate the merged summary in full-eval-tests/result/eval-results.md.
"@

    Push-Location $TestFolder
    try {
        & copilot --yolo -p $summaryPrompt
    }
    catch {
        Write-Warning "Summary generation error: $_"
    }
    finally {
        Pop-Location
    }

    # Copy the generated summary back (copilot writes into $TestFolder's copy)
    $summaryFile = Join-Path $TestFolder "full-eval-tests" "result" "eval-results.md"
    if (Test-Path $summaryFile) {
        Copy-Item -Path $summaryFile -Destination $resultDest -Force
        Write-Host "Merged summary: $resultDest\eval-results.md"
    }
    # Also check if copilot wrote it directly in the TestFolder root
    $summaryFileAlt = Get-ChildItem -Path $TestFolder -Filter "eval-results.md" -File 2>$null | Select-Object -First 1
    if ($summaryFileAlt -and $summaryFileAlt.FullName -ne $summaryFile) {
        Copy-Item -Path $summaryFileAlt.FullName -Destination $resultDest -Force
        Write-Host "Merged summary (alt): $resultDest\eval-results.md"
    }
}
else {
    Write-Warning "No individual result files found to summarize."
}

# ---------------------------------------------------------------------------
# Regression analysis
# ---------------------------------------------------------------------------
Write-Host "`n--- Regression Analysis ---"
$regressionsPrompt = @"
Follow plan/00-overview.md and generate full-eval-tests/result/regression_analysis.md.
"@
Push-Location $TestFolder
try {
    & copilot --yolo -p $regressionsPrompt
}
catch {
    Write-Warning "Regression analysis error: $_"
}
finally {
    Pop-Location
}

# Copy regression analysis back
$regressionFile = Get-ChildItem -Path $TestFolder -Filter "regression_analysis.md" -Recurse -File 2>$null | Select-Object -First 1
if ($regressionFile) {
    Copy-Item -Path $regressionFile.FullName -Destination $resultDest -Force
    Write-Host "Regression analysis: $resultDest\regression_analysis.md"
}
