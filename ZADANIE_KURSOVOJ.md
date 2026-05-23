# Задание на курсовой проект (вариант 4)

**Студент:** Тарасов Вадим Романович  
**Группа:** 221131  
**Репозиторий:** https://github.com/vadeetar/Kursach

**Дисциплина:** Методы и технологии программирования  
**Категория:** Обеспечение информационной безопасности систем  
**Тема:** Платформа управления уязвимостями (Vulnerability Management)

## Технологии (по методичке)

- Python + FastAPI + PostgreSQL + NVD API

## Описание

Система для сбора и анализа данных об уязвимостях из открытых источников (CVE, NVD). Сопоставление с инвентаризацией ПО организации, приоритизация на основе CVSS и контекста (EPSS, критичность актива). Веб-интерфейс для отслеживания статуса исправления.

## Реализовано в репозитории

| Требование методички | Файл / модуль |
|---------------------|---------------|
| REST API + OpenAPI | `backend/app/api/routes.py` |
| NVD API | `backend/app/services/nvd_collector.py` |
| EPSS | `backend/app/services/epss_collector.py` |
| Сопоставление CVE ↔ ПО | `backend/app/services/matcher.py` |
| Приоритизация CVSS | `backend/app/services/prioritizer.py` |
| Веб-интерфейс | `backend/app/static/` |
| Docker | `docker-compose.yml`, `backend/Dockerfile` |
| Тесты pytest | `backend/tests/` |
| SAST / CI | `.github/workflows/ci.yml` |
| Пояснительная записка | `POYASNITELNA_ZAPISKA.md` |
| Диаграммы | `docs/ARCHITECTURE.md` |
