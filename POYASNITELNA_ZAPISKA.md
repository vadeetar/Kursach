ПОЯСНИТЕЛЬНАЯ ЗАПИСКА  
к курсовому проекту  
«Платформа управления уязвимостями»  
по дисциплине «Методы и технологии программирования»

---

**Выполнил:** студент гр. 221131 — Тарасов Вадим Романович  
**Вариант:** 4 — Платформа управления уязвимостями (Vulnerability Management)  
**Репозиторий:** https://github.com/vadeetar/Kursach  
**Дата:** май 2026 г.

---

## СОДЕРЖАНИЕ

1. Введение  
2. Аналитическая часть  
3. Проектная часть  
4. Технологическая часть  
5. Реализация  
6. Тестирование  
7. Заключение  
8. Список литературы  
Приложения — см. `docs/PRILOZHENIYA.md`

---

## 1. ВВЕДЕНИЕ

### Актуальность

Прикладное ПО организаций строится на цепочках зависимостей (PyPI, npm, Maven и др.). Каждая библиотека может содержать известные уязвимости (CVE). По данным NIST, ежегодно публикуется более 20 000 новых CVE; значительная доля инцидентов связана с неустранёнными уязвимостями. Без автоматизированного сбора, приоритизации и учёта статуса исправления управление рисками становится неэффективным.

### Цель

Разработать программный продукт для автоматического сбора данных об уязвимостях из открытых источников, сопоставления с инвентаризацией ПО, контекстной приоритизации (CVSS, EPSS, критичность актива) и ведения статуса remediation через веб-интерфейс и REST API.

### Задачи

1. Проанализировать предметную область и аналоги.  
2. Спроектировать архитектуру и модель данных.  
3. Реализовать интеграцию с NVD API и EPSS API.  
4. Реализовать инвентаризацию активов и сопоставление с CVE.  
5. Разработать алгоритм приоритизации и SLA.  
6. Создать веб-интерфейс и документированный REST API (OpenAPI).  
7. Обеспечить качество: pytest, SAST, контейнеризация, CI/CD.  
8. Подготовить документацию и материалы к защите.

---

## 2. АНАЛИТИЧЕСКАЯ ЧАСТЬ

### 2.1 Предметная область

Цикл управления уязвимостями: обнаружение → оценка → планирование → исправление → верификация.

**Источники данных:**

| Источник | Назначение |
|----------|------------|
| [NVD](https://nvd.nist.gov) | CVE, CVSS 3.x, CPE, описания |
| [EPSS](https://www.first.org/epss) | Вероятность появления эксплойта |
| Инвентарь организации | Пакеты, версии, критичность |

### 2.2 Анализ аналогов

| Продукт | Ограничение | Наше решение |
|---------|-------------|--------------|
| Snyk, WhiteSource | Коммерция, облако | Локальное развёртывание, открытый код |
| Dependabot | Только GitHub | Независимый REST API |
| Ручной аудит | Медленно, ошибки | Автоматизация NVD + matcher |

### 2.3 Требования

**Функциональные (реализовано):**

- Синхронизация CVE из NVD API 2.0  
- Обновление EPSS для записей в БД  
- CRUD инвентаря ПО (ecosystem, package, version)  
- Автоматическое создание findings при добавлении актива и по задаче match  
- Фильтрация находок (статус, приоритет, просрочка SLA)  
- Отчёт executive-summary  
- Веб-дашборд  

**Нефункциональные:**

- Развёртывание через Docker Compose  
- Валидация данных (Pydantic V2)  
- Защита от SQL-инъекций (ORM)  
- CI: тесты, Bandit, Ruff  

**Запланировано в перспективе:** PDF-экспорт, Telegram-уведомления, JWT-аутентификация.

---

## 3. ПРОЕКТНАЯ ЧАСТЬ

### 3.1 Архитектура

```
┌──────────────────────────────────────────────┐
│  Presentation: веб-UI (HTML/JS) + OpenAPI    │
└──────────────────────────────────────────────┘
                      ↕
┌──────────────────────────────────────────────┐
│  Business: FastAPI routes + services         │
│  NVDCollector | EPSSCollector | Matcher    │
│  Prioritizer (CVSS × EPSS × criticality)     │
└──────────────────────────────────────────────┘
                      ↕
┌──────────────────────────────────────────────┐
│  Data: SQLAlchemy 2 + PostgreSQL             │
└──────────────────────────────────────────────┘
                      ↕
┌──────────────────────────────────────────────┐
│  External: NVD API, EPSS API                 │
└──────────────────────────────────────────────┘
```

Диаграммы Mermaid: `docs/ARCHITECTURE.md`.

### 3.2 Модель данных

- **Vulnerability** — CVE, CVSS, EPSS, CWE, affected_products (JSON).  
- **Asset** — ecosystem, package_name, version, business_criticality.  
- **Finding** — связь vulnerability ↔ asset, status, priority, risk_score, remediation_due_date.  
- **Remediation** — рекомендуемая версия патча.  
- **ScanMetadata** — журнал синхронизаций NVD/matcher.

### 3.3 REST API (основное)

| Метод | Endpoint | Назначение |
|-------|----------|------------|
| GET | `/api/v1/health` | Проверка сервиса |
| GET/POST | `/api/v1/vulnerabilities` | CVE |
| GET/POST/PUT/DELETE | `/api/v1/assets` | Инвентарь |
| GET/PATCH | `/api/v1/findings` | Находки |
| GET | `/api/v1/stats/risk` | Метрики |
| GET | `/api/v1/reports/executive-summary` | Отчёт |
| POST | `/api/v1/tasks/sync-nvd` | Синхронизация NVD |
| POST | `/api/v1/tasks/update-epss` | Обновление EPSS |
| POST | `/api/v1/tasks/match-assets` | Сопоставление |

Полная спецификация: `/api/v1/docs` (Swagger).

---

## 4. ТЕХНОЛОГИЧЕСКАЯ ЧАСТЬ

### 4.1 Стек (вариант 4 методички)

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.12 |
| Framework | FastAPI |
| Валидация | Pydantic V2 |
| ORM | SQLAlchemy 2 |
| СУБД | PostgreSQL 15 |
| HTTP-клиент | aiohttp (NVD, EPSS) |
| Контейнеры | Docker, Docker Compose |
| Тесты | pytest, httpx (TestClient) |
| Безопасность | Bandit, pip-audit |
| CI/CD | GitHub Actions |
| VCS | Git, Conventional Commits |

### 4.2 Обоснование выбора

**Python + FastAPI** — соответствие варианту 4, нативная async для запросов к NVD, автогенерация OpenAPI.  
**PostgreSQL** — JSON для CPE/продуктов, транзакции, индексы.  
**Веб-UI на статическом HTML/JS** — без отдельной сборки frontend, достаточно для демонстрации remediation; API пригоден для подключения React в будущем.

### 4.3 Интеграция NVD API 2.0

Endpoint: `https://services.nvd.nist.gov/rest/json/cves/2.0`  
Параметры: `pubStartDate`, `pubEndDate`, `startIndex`, `resultsPerPage`.  
Парсинг: `cve.id`, `descriptions`, `metrics.cvssMetricV31`, `weaknesses`, `configurations` (CPE).  
Лимиты: 5 запросов / 30 с (без ключа); с `NVD_API_KEY` — выше.

---

## 5. РЕАЛИЗАЦИЯ

### 5.1 Структура репозитория

```
backend/app/
  api/routes.py          — REST
  models.py, schemas.py  — данные
  services/
    nvd_collector.py     — NVD
    epss_collector.py    — EPSS
    matcher.py           — сопоставление
    prioritizer.py       — риск и SLA
  static/                — веб-интерфейс
  seed.py                — демо-данные
backend/tests/           — pytest
docker-compose.yml
.github/workflows/ci.yml
docs/
```

### 5.2 Приоритизация

```python
# Упрощённо: prioritizer.py
score = cvss_score
if epss_score: score += epss_score * 2
if business_criticality == "critical": score += 1
# → priority: critical | high | medium | low
risk_score = min(100, cvss * 10 * (1 + epss) * multiplier)
```

SLA (дней): critical — 7, high — 14, medium — 30, low — 90.

### 5.3 Веб-интерфейс

Вкладки: Дашборд, Находки, Инвентарь, CVE, Синхронизация.  
Обновление статуса finding через модальное окно (PATCH API).

### 5.4 Git и методичка

- Репозиторий: https://github.com/vadeetar/Kursach  
- Ветка `main`, коммиты в формате Conventional Commits  
- Рекомендуется ветка `develop` для доработок (Git Flow)  

### 5.5 AI-ассистированная разработка

Проектирование API, тестов и документации выполнено с использованием AI-ассистента Cursor (требование методички 2026).

---

## 6. ТЕСТИРОВАНИЕ

### 6.1 Стратегия

| Уровень | Содержание |
|---------|------------|
| Unit | models, prioritizer, парсер NVD |
| Integration | API + SQLite in-memory |
| CI | pytest, Bandit, Ruff на push |

### 6.2 Результаты

Команда: `cd backend && set DISABLE_SEED=1 && set TESTING=1 && pytest --cov=app`

- **Тестов:** 24 (все успешны)  
- **Покрытие:** ~71% (модули models/schemas >95%, API routes ~69%)  
- **SAST:** Bandit без критических замечаний в CI  

Примеры тестов: `tests/test_models.py`, `tests/test_api.py`, `tests/test_api_extended.py`, `tests/test_services.py`.

---

## 7. ЗАКЛЮЧЕНИЕ

Разработана **платформа управления уязвимостями**, соответствующая **варианту 4** методических указаний:

| Требование методички | Выполнено |
|---------------------|-----------|
| Python + FastAPI + PostgreSQL + NVD | Да |
| Сбор и анализ CVE | NVDCollector |
| Инвентаризация ПО | Asset CRUD |
| Приоритизация CVSS + контекст | prioritizer, risk_score |
| Веб-интерфейс remediation | static UI |
| Git | GitHub |
| Тестирование | pytest + CI |
| Docker | docker-compose.yml |
| Документация | README, OpenAPI, ARCHITECTURE, записка |
| SAST / зависимости | Bandit, pip-audit |

Продукт развёртывается одной командой `docker compose up`, пригоден для демонстрации на защите и дальнейшего развития (SBOM, Jira, Telegram, JWT).

---

## 8. СПИСОК ЛИТЕРАТУРЫ

1. NIST National Vulnerability Database. https://nvd.nist.gov  
2. FIRST EPSS. https://www.first.org/epss  
3. MITRE CVE. https://www.cve.org  
4. FastAPI Documentation. https://fastapi.tiangolo.com  
5. SQLAlchemy 2.0 Documentation. https://docs.sqlalchemy.org  
6. Pydantic V2 Documentation. https://docs.pydantic.dev  
7. Docker Documentation. https://docs.docker.com  
8. GitHub Actions Documentation. https://docs.github.com/actions  
9. McConnell S. Code Complete. Microsoft Press, 2023.  
10. Fowler M. Patterns of Enterprise Application Architecture. Addison-Wesley, 2022.  
11. Bandit — Python security linter. https://github.com/PyCQA/bandit  
12. Методические указания к курсовой работе МТП, 2026.

---

**Подготовил:** Тарасов Вадим Романович  
**Группа:** 221131  
**Подпись:** _______________  
**Дата:** «___» __________ 2026 г.

**Руководитель:** _______________  
**Подпись:** _______________
