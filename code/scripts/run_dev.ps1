$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\uvicorn.exe")) {
    Write-Host "Virtual environment not found. Run: uv venv; uv sync" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting On-Call Assistant at http://127.0.0.1:8000" -ForegroundColor Green
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
