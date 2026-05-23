# Архитектура — Платформа управления уязвимостями (вариант 4)

## Контекст (C4 — уровень системы)

```mermaid
flowchart TB
    User[Аналитик ИБ / DevSecOps]
    UI[Веб-интерфейс]
    API[FastAPI Backend]
    PG[(PostgreSQL)]
    NVD[NIST NVD API]
    EPSS[FIRST EPSS API]

    User --> UI
    UI --> API
    API --> PG
    API --> NVD
    API --> EPSS
```

## Компоненты

| Модуль | Назначение |
|--------|------------|
| `NVDCollector` | Сбор CVE из NVD API 2.0 |
| `EPSSCollector` | Обновление вероятности эксплуатации |
| `VulnerabilityMatcher` | Сопоставление CVE ↔ инвентарь ПО |
| `prioritizer` | CVSS × EPSS × критичность актива, SLA |
| REST API | CRUD, отчёты, фоновые задачи |
| Static UI | Дашборд, находки, синхронизация |

## ER-диаграмма

```mermaid
erDiagram
    VULNERABILITY ||--o{ FINDING : has
    ASSET ||--o{ FINDING : has
    VULNERABILITY {
        string cve_id PK
        float cvss_score
        float epss_score
        json affected_products
    }
    ASSET {
        string ecosystem
        string package_name
        string version
    }
    FINDING {
        string status
        string priority
        float risk_score
        datetime remediation_due_date
    }
```

## Поток данных

```mermaid
sequenceDiagram
    participant Op as Оператор
    participant API as FastAPI
    participant NVD as NVD API
    participant DB as PostgreSQL

    Op->>API: POST /tasks/sync-nvd
    API->>NVD: GET /cves/2.0
    NVD-->>API: CVE JSON
    API->>DB: UPSERT vulnerabilities
    Op->>API: POST /tasks/match-assets
    API->>DB: CREATE findings
    Op->>API: PATCH /findings/{id}
    API->>DB: UPDATE status
```

## Технологический стек (по методичке)

- **Python 3.12** + **FastAPI** + **Pydantic V2**
- **PostgreSQL** + **SQLAlchemy 2**
- **NVD API** — открытый источник CVE
- **Docker / Docker Compose**
- **pytest**, **Bandit**, **pip-audit**, **GitHub Actions**
