param(
    [switch]$SkipPreflight
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Starter = Join-Path $ScriptDir 'iniciar_alphascope_manha.ps1'
$Symbols = 'BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,LINKUSDT,BNBUSDT,ADAUSDT,DOGEUSDT,AVAXUSDT,TRXUSDT'

if (-not (Test-Path $Starter)) {
    throw "Script base não encontrado em $Starter"
}

$params = @{
    ProductionReal = $true
    StartDaemon = $true
    Symbols = $Symbols
}

if ($SkipPreflight) {
    $params.SkipPreflight = $true
}

& $Starter @params
if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao iniciar o AlphaScope real em 10 pares.'
}
