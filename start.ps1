# Запуск платформы без Docker (Windows)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"

if (-not (Test-Path $Backend)) {
    Write-Error "Папка backend не найдена: $Backend"
}

Set-Location $Backend
$env:PYTHONPATH = "."

Write-Host "Установка зависимостей (если нужно)..."
py -3 -m pip install -q -r requirements.txt

$dbFile = Join-Path $Backend "vuln_mgmt.db"
Write-Host "База данных: $dbFile"
Write-Host "Откройте в браузере: http://127.0.0.1:8000"
Write-Host "Остановка: Ctrl+C"
Write-Host ""

py -3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
