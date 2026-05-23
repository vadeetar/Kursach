# Платформа управления уязвимостями

**Автор:** Тарасов Вадим Романович  
**Группа:** 221131  
**Вариант:** 4 — Платформа управления уязвимостями (Vulnerability Management)

Курсовой проект по дисциплине «Методы и технологии программирования».

Система сбора данных об уязвимостях (CVE, NVD), сопоставления с инвентаризацией ПО организации, приоритизации по CVSS/EPSS и веб-интерфейса для отслеживания статуса исправления.

## Стек

| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Pydantic V2 |
| БД | PostgreSQL 15 (SQLite — локально без Docker) |
| Источники | [NVD API 2.0](https://nvd.nist.gov/developers/vulnerabilities), [EPSS API](https://www.first.org/epss/api) |
| Контейнеры | Docker, Docker Compose |
| Качество | pytest, Bandit (SAST), pip-audit (SCA), GitHub Actions |

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up -d --build
```

Откройте в браузере:

- **Веб-интерфейс:** http://localhost:8000
- **Swagger API:** http://localhost:8000/api/v1/docs
- **Health:** http://localhost:8000/api/v1/health

## Локальная разработка (без Docker)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=sqlite:///./vuln_mgmt.db
uvicorn app.main:app --reload --app-dir .
```

Из каталога `backend` (где лежит пакет `app`):

```bash
cd backend
set PYTHONPATH=.
uvicorn app.main:app --reload
```

## Основные возможности

1. **Сбор CVE** — `POST /api/v1/tasks/sync-nvd` (NVD API)
2. **EPSS** — `POST /api/v1/tasks/update-epss`
3. **Инвентарь ПО** — `POST /api/v1/assets`
4. **Сопоставление** — `POST /api/v1/tasks/match-assets`
5. **Управление исправлением** — `PATCH /api/v1/findings/{id}`
6. **Отчёты** — `GET /api/v1/reports/executive-summary`

При первом запуске загружаются **демо-данные** (3 CVE, 3 пакета, находки).

## Тесты и безопасность

```bash
cd backend
pip install -r requirements.txt
set DISABLE_SEED=1
pytest --cov=app --cov-report=term-missing -v
bandit -r app -ll
pip-audit -r requirements.txt
ruff check app tests
```

## Структура проекта

```
├── backend/
│   ├── app/           # приложение FastAPI
│   ├── tests/         # pytest
│   ├── Dockerfile
│   └── requirements.txt
├── docs/ARCHITECTURE.md
├── docker-compose.yml
├── POYASNITELNA_ZAPISKA.md
└── .github/workflows/ci.yml
```

## Git Flow (рекомендация по методичке)

- `main` — стабильная версия
- `develop` — интеграция
- `feature/*` — новые функции
- Коммиты: `feat:`, `fix:`, `docs:`, `test:` (Conventional Commits)

## Документация

- [Пояснительная записка](POYASNITELNA_ZAPISKA.md)
- [Архитектура и диаграммы](docs/ARCHITECTURE.md)

## Переменные окружения

См. [.env.example](.env.example). Опционально: `NVD_API_KEY` для увеличенных лимитов NVD API.

## AI-ассистированная разработка

Проект создан с использованием AI-ассистента (Cursor) для ускорения проектирования API, тестов и документации в соответствии с требованиями методических указаний 2026 г.
