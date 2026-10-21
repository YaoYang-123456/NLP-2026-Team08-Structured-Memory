param(
    [ValidateSet('StartDownload', 'StartRuntime', 'Stop', 'Status')]
    [string]$Action = 'Status',
    [int]$ExpectedProcessId = 0
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$stateDir = Join-Path $root 'output/ollama-service'
$stateFile = Join-Path $stateDir 'service.json'
$address = 'http://127.0.0.1:11436'
$ollamaPath = (Get-Command ollama -ErrorAction Stop).Source

function Get-OwnedProcess {
    if (-not (Test-Path -LiteralPath $stateFile)) { return $null }
    $saved = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json
    $candidate = Get-Process -Id $saved.pid -ErrorAction SilentlyContinue
    if (-not $candidate) { return $null }
    if ($candidate.Path -ne $saved.executable -or
        $candidate.StartTime.ToUniversalTime().Ticks -ne ([datetime]$saved.process_started_utc).ToUniversalTime().Ticks) {
        # Windows reused the PID: the recorded server is gone; never act on its replacement.
        return $null
    }
    return $candidate
}

if ($Action -eq 'Status') {
    Invoke-RestMethod "$address/api/version" | ConvertTo-Json
    Invoke-RestMethod "$address/api/ps" | ConvertTo-Json -Depth 6
    exit
}
if ($Action -eq 'Stop') {
    $saved = if (Test-Path -LiteralPath $stateFile) { Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json } else { $null }
    $owned = Get-OwnedProcess
    if ($owned) {
        if ($ExpectedProcessId -and $owned.Id -ne $ExpectedProcessId) {
            throw 'This session does not own the current project server.'
        }
        # Remember descendants before taskkill: an already-exiting child can make it return nonzero.
        $processes = @(Get-CimInstance Win32_Process)
        $ids = @([int]$owned.Id)
        for ($i = 0; $i -lt $ids.Count; $i++) {
            $ids += @($processes | Where-Object { $_.ParentProcessId -eq $ids[$i] } | ForEach-Object { [int]$_.ProcessId })
        }
        $targets = @($processes | Where-Object { $_.ProcessId -in $ids } | ForEach-Object {
            $targetProcess = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            if ($targetProcess) {
                [ordered]@{pid=$targetProcess.Id; started_ticks=$targetProcess.StartTime.ToUniversalTime().Ticks}
            }
        })
        $saved | Add-Member -NotePropertyName stop_targets -NotePropertyValue $targets -Force
        [IO.File]::WriteAllText($stateFile, ($saved | ConvertTo-Json -Depth 6) + "`n", [Text.UTF8Encoding]::new($false))
        & taskkill.exe /PID $owned.Id /T /F | Out-Null
    }
    # Check actual postconditions even when taskkill returned zero or the server was already gone.
    for ($check = 0; $check -lt 5; $check++) {
        $remaining = @($saved.stop_targets | ForEach-Object {
            $candidate = Get-Process -Id $_.pid -ErrorAction SilentlyContinue
            if ($candidate -and $candidate.StartTime.ToUniversalTime().Ticks -eq $_.started_ticks) { $candidate.Id }
        })
        $server = Get-OwnedProcess
        $listening = @(Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue)
        if (-not $server -and -not $remaining.Count -and -not $listening.Count) {
            Write-Output 'Verified stopped: owned processes exited and project port released.'
            exit 0
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Cleanup incomplete: server=$([bool]$server), remaining=$($remaining -join ','), listeners=$($listening.Count)"
}
if (Get-OwnedProcess) { throw 'Project server already exists; inspect/stop it explicitly before changing mode.' }
if (Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 11436 is occupied; refusing to reuse an unowned service.'
}
$modelStore = [Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
if (-not $modelStore) { $modelStore = 'D:\LocalAI\ollama-models-nlp' }
New-Item -ItemType Directory -Force -Path $stateDir, $modelStore | Out-Null
$settings = @{
    OLLAMA_HOST = '127.0.0.1:11436'
    OLLAMA_MODELS = $modelStore
    OLLAMA_CONTEXT_LENGTH = '8192'
    OLLAMA_NUM_PARALLEL = '1'
    OLLAMA_MAX_LOADED_MODELS = '1'
    OLLAMA_KEEP_ALIVE = '5m'
    OLLAMA_NO_CLOUD = '1'
    OLLAMA_NOPRUNE = '1'
}
if ($Action -eq 'StartDownload') { $settings.CUDA_VISIBLE_DEVICES = '-1'; $settings.GGML_VK_VISIBLE_DEVICES = '-1' }
$previous = @{}
try {
    foreach ($name in $settings.Keys) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $settings[$name], 'Process')
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $proc = Start-Process -FilePath $ollamaPath -ArgumentList 'serve' -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $stateDir "$stamp.stdout.log") `
        -RedirectStandardError (Join-Path $stateDir "$stamp.stderr.log")
    $stateJson = [ordered]@{pid=$proc.Id; executable=$ollamaPath; mode=$Action;
        process_started_utc=$proc.StartTime.ToUniversalTime().ToString('o'); settings=$settings;
        address=$address} | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($stateFile, $stateJson + "`n", [Text.UTF8Encoding]::new($false))
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
for ($i = 0; $i -lt 30; $i++) {
    try {
        $version = Invoke-RestMethod "$address/api/version" -TimeoutSec 1
        [ordered]@{status='ready'; version=$version.version; mode=$Action; models=$modelStore;
            context_length=8192; address=$address} | ConvertTo-Json
        exit
    } catch { Start-Sleep -Milliseconds 500 }
}
& taskkill.exe /PID $proc.Id /T /F | Out-Null
throw 'Ollama did not become ready; inspect output/ollama-service logs.'
