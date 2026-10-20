param(
    [switch]$Run,
    [switch]$Assemble,
    [int]$Limit = 0,
    [string]$Conversation = '',
    [switch]$RetryFailed,
    [string]$Data = 'data/locomo/development.conversations.json',
    [string]$SelectionConfig = 'configs/locomo-smoke.json',
    [string]$PlanRoot = 'output/structmem/development',
    [string]$HandoffRoot = 'output/structmem/handoff'
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $runtime = Get-Content -LiteralPath 'output/structmem/local-runtime.json' -Raw | ConvertFrom-Json
    & $runtime.python src/structmem_development.py plan --data $Data --selection-config $SelectionConfig --output $PlanRoot
    if ($LASTEXITCODE -ne 0) { throw 'Plan validation failed; no model requests started' }
    if ($Run) {
        $runArgs = @('src/structmem_development.py', 'run', '--plan', "$PlanRoot/plan.json",
            '--upstream', $runtime.upstream, '--embedding-model', $runtime.embedding_model, '--limit', $Limit)
        if ($Conversation) { $runArgs += @('--conversation', $Conversation) }
        if ($RetryFailed) { $runArgs += '--retry-failed' }
        & $runtime.python @runArgs
        if ($LASTEXITCODE -ne 0) { throw 'Session build stopped; inspect checkpoint summaries' }
    }
    if ($Assemble) {
        $assembleArgs = @('src/structmem_development.py', 'assemble', '--plan', "$PlanRoot/plan.json", '--output', $HandoffRoot)
        if ($Conversation) { $assembleArgs += @('--conversation', $Conversation) }
        & $runtime.python @assembleArgs
        if ($LASTEXITCODE -ne 0) { throw 'Handoff assembly failed or conversations incomplete' }
    }
} finally {
    Pop-Location
}
