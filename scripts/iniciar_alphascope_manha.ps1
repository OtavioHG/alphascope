param(
    [switch]$ProductionReal,
    [switch]$StartDaemon,
    [switch]$SkipPreflight,
    [string]$Symbols = 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,LINKUSDT,BNBUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,TRXUSDT'
)

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $ProjectRoot 'venv\Scripts\python.exe'
$ActivateScript = Join-Path $ProjectRoot 'venv\Scripts\Activate.ps1'
$Symbols = ($Symbols -split ',' | ForEach-Object { $_.Trim().ToUpper() } | Where-Object { $_ }) -join ','
$Interval = '1h'
$Limit = 500
$LiveLimit = 10

if (-not (Test-Path $PythonExe)) {
    throw "Python do venv não encontrado em $PythonExe"
}

Set-Location $ProjectRoot

function Run-Step {
    param(
        [string]$Title,
        [string[]]$CommandArgs
    )

    Write-Host "" 
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    & $PythonExe @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha em: $Title"
    }
}

function Start-PowerShellWindow {
    param(
        [string]$Title,
        [string]$Command
    )

    $Wrapped = "`$Host.UI.RawUI.WindowTitle = '$Title'; cd '$ProjectRoot'; . '$ActivateScript'; $Command"
    Start-Process powershell -ArgumentList '-NoExit', '-Command', $Wrapped | Out-Null
}

if (-not $SkipPreflight) {
    Run-Step 'Doctor geral' @('-m', 'alphascope.cli', 'doctor', '--json')
    Run-Step 'Modo atual do trader' @('-m', 'alphascope.cli', 'show-trader-mode')
    Run-Step 'Credenciais Binance live' @('-m', 'alphascope.cli', 'verify-exchange-credentials', '--mode', 'live')
    Run-Step 'Sincronização de conta' @('-m', 'alphascope.cli', 'sync-account')
    Run-Step 'Ingestão de mercado' @('-m', 'alphascope.cli', 'ingest-market', '--symbols', $Symbols, '--interval', $Interval, '--limit', "$Limit")
    Run-Step 'Construção de features' @('-m', 'alphascope.cli', 'build-features', '--symbols', $Symbols, '--interval', $Interval)
    Run-Step 'Ranking de ativos' @('-m', 'alphascope.cli', 'rank-assets', '--symbols', $Symbols, '--interval', $Interval)
    Run-Step 'Explicação do ranking' @('-m', 'alphascope.cli', 'explain-ranking', '--symbols', $Symbols, '--interval', $Interval, '--limit', '20')
    Run-Step 'Validação do multiagente' @('-m', 'alphascope.cli', 'run-multi-agent', '--symbol', 'BTCUSDT', '--interval', $Interval)
    Run-Step 'Status do runtime multiagente' @('-m', 'alphascope.cli', 'multi-agent-runtime-status', '--json')
    Run-Step 'Teste do Telegram' @('-m', 'alphascope.cli', 'test-telegram-alert')
    Run-Step 'Status operacional agregado' @('-m', 'alphascope.cli', 'runtime-status')
    Run-Step 'Snapshot da conta' @('-m', 'alphascope.cli', 'show-data', '--type', 'account', '--limit', '20')
    Run-Step 'Posições abertas' @('-m', 'alphascope.cli', 'show-data', '--type', 'open-positions', '--limit', '20')
}

if ($StartDaemon) {
    Start-PowerShellWindow 'AlphaScope Daemon' "& '$PythonExe' -m alphascope.cli start-daemon --symbols $Symbols --cycle-seconds 300 --timeframe $Interval --limit $Limit"
}

Start-PowerShellWindow 'AlphaScope API' "& '$PythonExe' -m alphascope.cli run-platform-api --host 0.0.0.0 --port 8010"
Start-PowerShellWindow 'AlphaScope Dashboard' "& '$PythonExe' -m alphascope.cli run-dashboard --host 0.0.0.0 --port 8501"
Start-PowerShellWindow 'AlphaScope Telegram' "& '$PythonExe' -m alphascope.cli run-telegram-bot"

if ($ProductionReal) {
    Run-Step 'INÍCIO DA PRODUÇÃO REAL' @('-m', 'alphascope.cli', 'start-live-trading', '--interval', $Interval, '--limit', "$LiveLimit")
} else {
    Write-Host ''
    Write-Host 'Pré-operação concluída. API, dashboard e Telegram foram iniciados.' -ForegroundColor Green
    Write-Host "Para iniciar produção real agora, rode:" -ForegroundColor Yellow
    Write-Host ".\scripts\iniciar_alphascope_manha.ps1 -ProductionReal" -ForegroundColor Yellow
    Write-Host "Ou para iniciar já com daemon contínuo:" -ForegroundColor Yellow
    Write-Host ".\scripts\iniciar_alphascope_manha.ps1 -ProductionReal -StartDaemon" -ForegroundColor Yellow
}
