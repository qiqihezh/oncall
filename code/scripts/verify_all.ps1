$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run: uv venv; uv sync" -ForegroundColor Yellow
    exit 1
}

$Port = 8123
$BaseUrl = "http://127.0.0.1:$Port"
$Uvicorn = ".\.venv\Scripts\uvicorn.exe"

Write-Host "Running pytest..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pytest tests

Write-Host "Starting temporary server on $BaseUrl ..." -ForegroundColor Cyan
$Process = Start-Process -FilePath $Uvicorn -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "$Port" -WorkingDirectory $Root -WindowStyle Hidden -PassThru

try {
    $Ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        try {
            Invoke-RestMethod "$BaseUrl/health" | Out-Null
            $Ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $Ready) {
        throw "Server did not become ready on $BaseUrl"
    }

    Write-Host "Running API verification..." -ForegroundColor Cyan
    .\.venv\Scripts\python.exe scripts\verify.py --base-url $BaseUrl
} finally {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}

Write-Host "All checks completed." -ForegroundColor Green
