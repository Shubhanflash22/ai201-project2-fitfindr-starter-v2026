<#
One full trial of the capstone tests, no manual steps.

  .\run_trial.ps1 -Trial 2                  # sessions N, B, L (about 5 minutes)
  .\run_trial.ps1 -Trial 2 -Sessions T      # criterion 4 only (about 20 minutes)
  .\run_trial.ps1 -Trial 2 -Phase after     # same, writing to results\capstone\after

Sessions: N = criteria 1, 2a, 2b, 2e, 5, 2d on a normal server
          B = criterion 2c on a server with a fake API key
          L = criterion 3 on a server whose log path cannot be written
          T = criterion 4 (100 warm requests, 10 s apart) on a fresh server
#>
param(
    [Parameter(Mandatory = $true)][int]$Trial,
    [ValidateSet("before", "after")][string]$Phase = "before",
    [ValidateSet("N", "R", "B", "L", "T")][string[]]$Sessions = @("N", "R", "B", "L")
)

Set-Location $PSScriptRoot
[Environment]::CurrentDirectory = $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$outAbs = Join-Path $PSScriptRoot "results\capstone\$Phase"
New-Item -ItemType Directory -Force -Path $outAbs | Out-Null
$summaryFile = Join-Path $outAbs "driver_t$Trial.txt"
$health = "http://127.0.0.1:5000/health"
$script:summary = @()
$script:server = $null
$script:origKey = $env:GEMINI_API_KEY

function Test-Up {
    try { Invoke-WebRequest -Uri $health -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true }
    catch { return $false }
}

function Start-Server($name, $logPath, $stderrPath, $fakeKey) {
    $env:AI201_CACHE = "0"
    $env:AI201_LOG_PATH = $logPath
    if ($fakeKey) { $env:GEMINI_API_KEY = "not-a-real-key" }
    $stdoutPath = Join-Path $outAbs "server_${name}_t$Trial.out.txt"
    if (-not $stderrPath) { $stderrPath = Join-Path $outAbs "server_${name}_t$Trial.err.txt" }
    $script:server = Start-Process -FilePath $py -ArgumentList "serve.py" -WorkingDirectory $PSScriptRoot `
        -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Up) { return }
    }
    throw "server for session $name did not come up within 60 s; see $stderrPath"
}

function Stop-Server {
    if ($script:server) {
        cmd /c "taskkill /PID $($script:server.Id) /T /F >nul 2>&1"
        $script:server = $null
    }
    if ($script:origKey) { $env:GEMINI_API_KEY = $script:origKey }
    else { Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue }
    Remove-Item Env:AI201_LOG_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:AI201_CACHE -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 20; $i++) { if (-not (Test-Up)) { break }; Start-Sleep -Seconds 1 }
}

function Invoke-Driver([string[]]$DriverArgs) {
    $label = $DriverArgs -join " "
    $typ = ""
    $ti = [array]::IndexOf($DriverArgs, "--type")
    if ($ti -ge 0) { $typ = $DriverArgs[$ti + 1] }
    $resultFile = Join-Path $outAbs ("c" + $DriverArgs[0] + $typ + "_t" + $DriverArgs[1] + ".json")
    if (Test-Path $resultFile) {
        Write-Host "skipping, result already exists: $resultFile"
        $script:summary += "skipped, already exists: $(Split-Path $resultFile -Leaf)"
        return
    }
    Write-Host "> capstone_run.py $label"
    & $py capstone_run.py @DriverArgs 2>&1 | Tee-Object -Variable lines | ForEach-Object { Write-Host "$_" }
    $code = $LASTEXITCODE
    $text = @($lines | ForEach-Object { "$_" })
    Add-Content -Path $summaryFile -Value ("> " + $label)
    Add-Content -Path $summaryFile -Value $text
    if ($code -ne 0) { $script:summary += "FAILED (exit $code): capstone_run.py $label"; return }
    $script:summary += @($text | Where-Object { $_ -notmatch '^\s' -and $_ -notmatch '^saved' })
}

# ---- checks before anything starts ----
if (Test-Up) { throw "A server is already answering on port 5000. Stop it first." }
$mcp = Join-Path $PSScriptRoot "mcp_server.py"
$mcpOff = Join-Path $PSScriptRoot "mcp_server_off.py"
if (-not (Test-Path $mcp) -and (Test-Path $mcpOff)) { Rename-Item $mcpOff "mcp_server.py" }
if (-not (Test-Path $mcp)) { throw "mcp_server.py is missing." }

$expected = @()
foreach ($s in $Sessions) {
    switch ($s) {
        "N" { $expected += "log_N_t$Trial.jsonl", "c1_t$Trial.json", "c2a_t$Trial.json", "c2b_t$Trial.json", "c2e_t$Trial.json", "c5_t$Trial.json", "c2d_t$Trial.json" }
        "B" { $expected += "log_B_t$Trial.jsonl", "c2c_t$Trial.json" }
        "L" { $expected += "c3_t$Trial.json" }
        "T" { $expected += "log_T_t$Trial.jsonl", "c4_t$Trial.json" }
    }
}
$clash = @($expected | Where-Object { Test-Path (Join-Path $outAbs $_) })
if ($clash.Count -gt 0) { Write-Host "Already present, will be skipped: $($clash -join ', ')" }

# ---- sessions ----
try {
    foreach ($s in $Sessions) {
        Write-Host "=== trial $Trial session $s ==="
        if ($s -eq "N") {
            $log = Join-Path $outAbs "log_N_t$Trial.jsonl"
            Start-Server "N" $log $null $false
            try { Invoke-Driver @("1", "$Trial", "--log", $log, "--phase", $Phase) }
            finally { Stop-Server }
        }
        elseif ($s -eq "R") {
            $log = Join-Path $outAbs "log_R_t$Trial.jsonl"
            Start-Server "R" $log $null $false
            try {
                foreach ($ty in "a", "b", "e") {
                    Invoke-Driver @("2", "$Trial", "--log", $log, "--type", $ty, "--phase", $Phase)
                }
                Invoke-Driver @("5", "$Trial", "--log", $log, "--phase", $Phase)
                Rename-Item $mcp "mcp_server_off.py"
                try { Invoke-Driver @("2", "$Trial", "--log", $log, "--type", "d", "--phase", $Phase) }
                finally { Rename-Item $mcpOff "mcp_server.py" }
            } finally { Stop-Server }
        }
        elseif ($s -eq "B") {
            $log = Join-Path $outAbs "log_B_t$Trial.jsonl"
            Start-Server "B" $log $null $true
            try { Invoke-Driver @("2", "$Trial", "--log", $log, "--type", "c", "--phase", $Phase) }
            finally { Stop-Server }
        }
        elseif ($s -eq "L") {
            Start-Sleep -Seconds 30
            $stderr = Join-Path $outAbs "stderr_L_t$Trial.txt"
            Start-Server "L" $outAbs $stderr $false
            try { Invoke-Driver @("3", "$Trial", "--stderr", $stderr, "--phase", $Phase) }
            finally { Stop-Server }
        }
        elseif ($s -eq "T") {
            Start-Sleep -Seconds 30
            $log = Join-Path $outAbs "log_T_t$Trial.jsonl"
            Start-Server "T" $log $null $false
            try { Invoke-Driver @("4", "$Trial", "--log", $log, "--phase", $Phase) }
            finally { Stop-Server }
        }
    }
}
finally {
    Stop-Server
    if (-not (Test-Path $mcp) -and (Test-Path $mcpOff)) { Rename-Item $mcpOff "mcp_server.py" }
}

Write-Host ""
Write-Host "=== summary, trial $Trial ($Phase) ==="
$script:summary | ForEach-Object { Write-Host $_ }
Write-Host "mcp_server.py present: $(Test-Path $mcp)"