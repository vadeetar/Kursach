# Приложения к пояснительной записке

**Автор:** Тарасов Вадим Романович, гр. 221131, вариант 4

Сохраните скриншоты в папку `docs/screenshots/` (создайте при оформлении Word/PDF) и вставьте в записку.

| № | Файл | Содержание |
|---|------|------------|
| А | `01_dashboard.png` | Главная страница — дашборд с метриками |
| Б | `02_findings.png` | Список находок с приоритетами |
| В | `03_finding_edit.png` | Диалог изменения статуса исправления |
| Г | `04_assets.png` | Инвентаризация ПО |
| Д | `05_vulnerabilities.png` | Список CVE |
| Е | `06_sync.png` | Вкладка синхронизации NVD/EPSS |
| Ж | `07_swagger.png` | Swagger UI `/api/v1/docs` |
| З | `08_docker.png` | `docker compose ps` или логи контейнеров |
| И | `09_github.png` | Репозиторий GitHub |
| К | `10_ci.png` | Успешный workflow GitHub Actions |

## Как сделать скриншоты

1. Запустить `docker compose up -d --build`  
2. Открыть http://localhost:8000 и пройти по вкладкам  
3. Win+Shift+S (Windows) → сохранить в `docs/screenshots/`  
4. Для CI: вкладка Actions на GitHub после push  

## Листинги кода (приложение Л)

Рекомендуемые фрагменты из репозитория:

- `backend/app/services/nvd_collector.py` — парсинг NVD 2.0  
- `backend/app/services/matcher.py` — сопоставление  
- `backend/app/services/prioritizer.py` — расчёт риска  
- `backend/app/api/routes.py` — REST endpoints  
