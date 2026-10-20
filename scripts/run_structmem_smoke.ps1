param(
    [string]$RunName = ("synthetic-" + (Get-Date -Format 'yyyyMMdd-HHmmss')),
    [string]$ReplayPath = ''
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    $runtime = Get-Content -LiteralPath 'output/structmem/local-runtime.json' -Raw | ConvertFrom-Json
    $inputPath = "output/structmem/$RunName-input.json"
    & $runtime.python src/structmem_build.py prepare --data tests/fixtures/structmem-synthetic.json --sample-id synthetic-smoke --session 1 --output $inputPath
    if ($LASTEXITCODE -ne 0) { throw 'Input preparation failed' }
    $buildArgs = @('src/structmem_build.py', 'build', '--input', $inputPath,
        '--config', 'configs/structmem-smoke.json', '--upstream', $runtime.upstream,
        '--embedding-model', $runtime.embedding_model, '--output', "output/structmem/$RunName", '--synthetic')
    if ($ReplayPath) { $buildArgs += @('--replay', $ReplayPath) }
    & $runtime.python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw 'Build failed; inspect the run summary.json' }
} finally {
    Pop-Location
}
