# Запуск платформы без Docker (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"

if (-not (Test-Path $Backend)) {
    Write-Error "Папка backend не найдена: $Backend"
}

Set-Location $Backend
$env:PYTHONPATH = "."
Remove-Item Env:TESTING -ErrorAction SilentlyContinue
Remove-Item Env:DISABLE_SEED -ErrorAction SilentlyContinue

Write-Host "Установка зависимостей..."
py -3 -m pip install -q -r requirements.txt

$dbFile = Join-Path $Backend "vuln_mgmt.db"
Write-Host ""
Write-Host "База данных: $dbFile"
Write-Host "Откройте:  http://127.0.0.1:8000"
Write-Host "Swagger:   http://127.0.0.1:8000/api/v1/docs"
Write-Host "Остановка: Ctrl+C"
Write-Host ""

py -3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
