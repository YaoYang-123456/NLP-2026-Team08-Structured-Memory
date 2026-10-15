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
        throw 'Saved process identity differs; refusing to stop another process.'
    }
    return $candidate
}

if ($Action -eq 'Status') {
    Invoke-RestMethod "$address/api/version" | ConvertTo-Json
    Invoke-RestMethod "$address/api/ps" | ConvertTo-Json -Depth 6
    exit
}
if ($Action -eq 'Stop') {
    $owned = Get-OwnedProcess
    if ($owned) {
        if ($ExpectedProcessId -and $owned.Id -ne $ExpectedProcessId) {
            throw 'This session does not own the current project server.'
        }
        # The dedicated server and its own runner only; never stop all Ollama processes.
        & taskkill.exe /PID $owned.Id /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the project server process tree.' }
    }
    exit
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
