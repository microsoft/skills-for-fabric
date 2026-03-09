param(
    [Parameter(Mandatory = $false)]
    [string]$directoryPath,
    [Parameter(Mandatory = $false)]
    [string]$testName
)

$ErrorActionPreference = "Stop"

# Resolve the repository root (script lives under tests/)
$repoRoot = Split-Path -Parent $PSScriptRoot

# Step 1-2: If directoryPath not provided, create a GUID-named temp directory
if (-not $directoryPath) {
    $guid = [System.Guid]::NewGuid().ToString()
    $directoryPath = Join-Path ([System.IO.Path]::GetTempPath()) $guid
    New-Item -ItemType Directory -Path $directoryPath -Force | Out-Null
    Write-Host "Created temp directory: $directoryPath"
}
else {
    if (-not (Test-Path $directoryPath)) {
        New-Item -ItemType Directory -Path $directoryPath -Force | Out-Null
    }
}
# Step 3 : Reinstall the local plugin
copilot plugin marketplace remove fabric-collection --force
copilot plugin marketplace add $repoRoot
copilot plugin install fabric-skills@fabric-collection

# Step 4: Switch current directory to directoryPath
Push-Location $directoryPath
try {
    # Step 5: Read tests.json and run each test
    $testsJsonPath = Join-Path $repoRoot "tests" "tests.json"
    if (-not (Test-Path $testsJsonPath)) {
        Write-Error "tests.json not found at: $testsJsonPath"
        return
    }

    $tests = Get-Content $testsJsonPath -Raw | ConvertFrom-Json
    if ($testName) {
        $tests = @($tests | Where-Object { $_.name -eq $testName })
        if ($tests.Count -eq 0) {
            Write-Error "Test '$testName' not found in tests.json"
            return
        }
        Write-Host "Running single test: $testName" -ForegroundColor Cyan
    }
    $dtFormat = "yyyy-MM-dd HH:mm:ss.fff"
    $allTestsStart = Get-Date
    $throttleLimit = 50

    # Thread-safe collections for results and output
    $resultsBag = [System.Collections.Concurrent.ConcurrentBag[hashtable]]::new()
    $outputLock = [object]::new()

    # Launch all tests in parallel using thread jobs with throttling
    $jobs = @()
    foreach ($test in $tests) {
        $currentTestName = $test.name
        $safeName = $currentTestName -replace '[^a-zA-Z0-9_-]', '_'
        $outputFile = Join-Path $directoryPath "${safeName}_output.txt"
        $prompt = $test.prompt
        $expectedSkills = $test.expectedSkills
        $expectedResults = $test.expectedResults

        # Wait if we've hit the throttle limit
        while (@($jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $throttleLimit) {
            Start-Sleep -Milliseconds 200
        }

        $job = Start-ThreadJob -ScriptBlock {
            param($testName, $prompt, $outputFile, $expectedSkills, $expectedResults, $dtFormat, $dirPath)

            $testStart = Get-Date
            $lines = @()
            $errorMsg = $null

            # Run copilot as a separate process, capturing all output
            try {
                & copilot --yolo -p "$prompt" 2>&1 | Out-File -FilePath $outputFile -Encoding UTF8
            }
            catch {
                $errorMsg = $_.ToString()
            }

            $testEnd = Get-Date
            $testDuration = ($testEnd - $testStart).TotalSeconds

            # Read the output
            $output = ""
            if (Test-Path $outputFile) {
                $output = Get-Content $outputFile -Raw -ErrorAction SilentlyContinue
                if (-not $output) { $output = "" }
            }

            # Build the display lines as structured objects (text + color)
            $lines += @{ Text = ""; Color = "White" }
            $lines += @{ Text = "=== Running test: $testName ==="; Color = "Cyan" }
            $startText = "  Starting test: $($testStart.ToString($dtFormat)) ... finished: $($testEnd.ToString($dtFormat)) duration: $([math]::Round($testDuration, 1)) s"
            $lines += @{ Text = $startText; Color = "White" }

            if ($errorMsg) {
                $lines += @{ Text = "  WARNING: copilot process returned an error: $errorMsg"; Color = "Yellow" }
            }

            # Check expected skills
            $allSkillsFound = $true
            foreach ($skill in $expectedSkills) {
                if ($output -notmatch [regex]::Escape($skill)) {
                    $allSkillsFound = $false
                    $lines += @{ Text = "  MISSING skill: $skill"; Color = "Yellow" }
                }
                else {
                    $lines += @{ Text = "  Found skill: $skill"; Color = "Green" }
                }
            }

            # Check expected results
            $allResultsFound = $true
            foreach ($expected in $expectedResults) {
                if ($output -notmatch [regex]::Escape($expected)) {
                    $allResultsFound = $false
                    $lines += @{ Text = "  MISSING result: $expected"; Color = "Yellow" }
                }
                else {
                    $lines += @{ Text = "  Found result: $expected"; Color = "Green" }
                }
            }

            $passed = if ($allSkillsFound -and $allResultsFound) { "Y" } else { "N" }
            $resultColor = if ($passed -eq "Y") { "Green" } else { "Red" }
            $lines += @{ Text = "  Test result: $passed"; Color = $resultColor }

            return @{
                TestName = $testName
                Passed   = $passed
                Lines    = $lines
            }
        } -ArgumentList $currentTestName, $prompt, $outputFile, $expectedSkills, $expectedResults, $dtFormat, $directoryPath

        $jobs += $job
    }

    # Collect results as jobs complete, printing and recording one at a time
    $results = @()
    $completedJobIds = @{}

    while ($completedJobIds.Count -lt $jobs.Count) {
        foreach ($job in $jobs) {
            if ($completedJobIds.ContainsKey($job.Id)) { continue }
            if ($job.State -eq 'Completed' -or $job.State -eq 'Failed') {
                # Critical section: lock so only one test prints/records at a time
                [System.Threading.Monitor]::Enter($outputLock)
                try {
                    $completedJobIds[$job.Id] = $true

                    if ($job.State -eq 'Completed') {
                        $jobResult = Receive-Job -Job $job

                        # Print all buffered lines for this test atomically
                        foreach ($line in $jobResult.Lines) {
                            Write-Host $line.Text -ForegroundColor $line.Color
                        }

                        $results += @{
                            name   = $jobResult.TestName
                            passed = $jobResult.Passed
                        }
                    }
                    else {
                        $errInfo = Receive-Job -Job $job -ErrorAction SilentlyContinue
                        Write-Host ""
                        Write-Host "=== Test job FAILED ===" -ForegroundColor Red
                        Write-Host "  Error: $errInfo" -ForegroundColor Red
                    }
                }
                finally {
                    [System.Threading.Monitor]::Exit($outputLock)
                }

                Remove-Job -Job $job -Force
            }
        }
        Start-Sleep -Milliseconds 200
    }

    # Save results to testsResults.json
    $resultsPath = Join-Path $directoryPath "testsResults.json"
    $results | ConvertTo-Json -Depth 10 | Set-Content $resultsPath -Encoding UTF8

    $allTestsEnd = Get-Date
    $allTestsDuration = ($allTestsEnd - $allTestsStart).TotalSeconds

    Write-Host ""
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host "Tests started: $($allTestsStart.ToString($dtFormat)) tests finished: $($allTestsEnd.ToString($dtFormat)) duration: $([math]::Round($allTestsDuration, 1)) s"
    $passedCount = @($results | Where-Object { $_.passed -eq "Y" }).Count
    $totalCount = $results.Count
    Write-Host "Tests passed: $passedCount / $totalCount" -ForegroundColor $(if ($passedCount -eq $totalCount) { "Green" } else { "Yellow" })
    Write-Host "Results saved to: $resultsPath" -ForegroundColor Green
    Write-Host "Test directory: $directoryPath"
}
finally {
    Pop-Location
}
