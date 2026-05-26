# Руководство по получению скриншотов для курсовой работы

Используйте эти команды для получения всех 9 скриншотов, необходимых для защиты проекта.

---

## **Скриншот 1: Запущенные Docker контейнеры**

### Команда:
```bash
docker compose ps
```

### Что должно отобразиться:
```
NAME                      IMAGE                      COMMAND                  SERVICE      CREATED      STATUS                 PORTS
kursach-db-1              postgres:15-alpine         "postgres"               db           1 min ago    Up 30 seconds          5432/tcp
kursach-backend-1         kursach-backend:latest     "uvicorn app.main:app"   backend      1 min ago    Up 15 seconds          0.0.0.0:8000->8000/tcp
```

### Где взять:
Выполните в корне проекта после `docker compose up -d --build`

---

## **Скриншот 2: API документация Swagger**

### Команда:
Откройте в браузере после запуска контейнеров:
```
http://localhost:8000/api/v1/docs
```

### Где взять:
1. Запустите: `docker compose up -d --build`
2. Откройте браузер на `http://localhost:8000/api/v1/docs`
3. Скриншот должен показать список endpoints:
   - POST /api/v1/vulnerabilities
   - GET /api/v1/vulnerabilities
   - POST /api/v1/assets
   - GET /api/v1/findings
   - PATCH /api/v1/findings/{finding_id}
   - POST /api/v1/tasks/sync-nvd
   - И другие...

---

## **Скриншот 3: Структура БД (таблицы, связи)**

### Команда:
```bash
docker compose exec db psql -U vuln -d vuln_mgmt -c "\dt"
```

### Что должно отобразиться:
```
                 List of relations
 Schema |      Name       | Type  | Owner
--------+-----------------+-------+-------
 public | assets          | table | vuln
 public | findings        | table | vuln
 public | remediations    | table | vuln
 public | scan_metadata   | table | vuln
 public | vulnerabilities | table | vuln
```

### Для просмотра связей (Foreign Keys):
```bash
docker compose exec db psql -U vuln -d vuln_mgmt -c "\d findings"
```

Результат покажет все столбцы и связи, включая:
```
Foreign-key constraints:
    "findings_asset_id_fkey" FOREIGN KEY (asset_id) REFERENCES assets(id)
    "findings_vulnerability_id_fkey" FOREIGN KEY (vulnerability_id) REFERENCES vulnerabilities(id)
```

---

## **Скриншот 4: Запуск тестов (pytest output)**

### Команда:
```bash
cd backend
set PYTHONPATH=.
set DISABLE_SEED=1
pytest --tb=short
```

### Что должно отобразиться:
```
============================= test session starts ==============================
platform win32 -- Python 3.12.x, pytest-x.x.x, pluggy-1.x.x
rootdir: E:\курсач\backend, configfile: pytest.ini
collected 24 items

tests/test_api_vulnerabilities.py::test_create_vulnerability PASSED       [ 4%]
tests/test_api_vulnerabilities.py::test_list_vulnerabilities PASSED       [ 8%]
tests/test_api_assets.py::test_create_asset PASSED                        [12%]
...
======================== 24 passed in 3.45s ============================
```

---

## **Скриншот 5: Логи тестов с подробным выводом**

### Команда:
```bash
cd backend
set PYTHONPATH=.
set DISABLE_SEED=1
pytest -v -s --tb=short 2>&1 | tee pytest_output.txt
```

### Параметры:
- `-v` — verbose (подробный вывод каждого теста)
- `-s` — show print statements
- `--tb=short` — краткая информация об ошибках
- `2>&1 | tee pytest_output.txt` — вывод в файл и консоль

### Что должно отобразиться:
```
tests/test_api_vulnerabilities.py::test_create_vulnerability PASSED
tests/test_api_vulnerabilities.py::test_list_vulnerabilities PASSED
tests/test_api_vulnerabilities.py::test_get_vulnerability PASSED
tests/test_api_vulnerabilities.py::test_update_vulnerability PASSED
tests/test_api_assets.py::test_create_asset PASSED
tests/test_api_assets.py::test_list_assets PASSED
...
======================== 24 passed in 3.45s ============================
```

---

## **Скриншоты 6–8: Allure Reports**

### Установка Allure:
```bash
pip install allure-pytest
```

### Запуск тестов с Allure:
```bash
cd backend
set PYTHONPATH=.
set DISABLE_SEED=1
pytest --alluredir=allure-results -v
```

### Генерация Allure отчёта:
```bash
allure generate allure-results -o allure-report --clean
```

### Открыть отчёт:
```bash
allure open allure-report
```

---

## **Скриншот 6: Allure Report — Overview (главная страница)**

После открытия `allure open allure-report` откроется браузер с главной страницей:

- **Статус:** Успешно / Неудачно
- **Количество тестов:** 24
- **Продолжительность:** ~3.5 сек
- **График по результатам:** зелёный столбец (все passed)

Скриншот должен показать:
```
SUITES     24 passed      0 failed      0 skipped
TIMELINE   3.45 sec
SEVERITY   Trivial (все тесты)
```

---

## **Скриншот 7: Allure Report — Test Results (список всех тестов)**

Переходите на вкладку **Suites** в Allure Report и смотрите таблицу:

| Test | Duration | Status |
|------|----------|--------|
| test_create_vulnerability | 0.15s | PASSED |
| test_list_vulnerabilities | 0.12s | PASSED |
| test_get_vulnerability | 0.10s | PASSED |
| test_update_vulnerability | 0.18s | PASSED |
| test_create_asset | 0.20s | PASSED |
| ... | ... | PASSED |

---

## **Скриншот 8: Allure Report — Test Details (детали конкретного теста)**

Кликните на любой тест, например `test_create_vulnerability`:

Будут показаны:
- **Шаги теста** (Setup, Body, Teardown)
- **Время выполнения:** 0.15s
- **Статус:** PASSED
- **Параметры:**
  ```json
  {
    "cve_id": "CVE-2024-0001",
    "cvss_score": 8.5,
    "severity": "high"
  }
  ```

---

## **Скриншот 9: Результат падения теста (ошибка валидации)**

### Создайте тест, который должен упасть:

Добавьте в `backend/tests/test_api_vulnerabilities.py`:

```python
def test_invalid_cvss_score(client):
    """Test that invalid CVSS score is rejected"""
    response = client.post(
        "/api/v1/vulnerabilities",
        json={
            "cve_id": "CVE-2024-9999",
            "description": "Test vulnerability",
            "cvss_score": 12.0,  # Invalid! Max is 10.0
            "severity": "critical",
            "published_date": "2024-01-01T00:00:00",
            "last_modified_date": "2024-01-01T00:00:00"
        }
    )
    assert response.status_code == 422  # Validation error
```

### Запустите:
```bash
pytest -v -s tests/test_api_vulnerabilities.py::test_invalid_cvss_score
```

### Результат в консоли:
```
tests/test_api_vulnerabilities.py::test_invalid_cvss_score FAILED

_____ test_invalid_cvss_score _____

response = <Response [422]>

>       assert response.status_code == 422
E       AssertionError: assert 400 == 422
...
FAILED tests/test_api_vulnerabilities.py::test_invalid_cvss_score - AssertionError
```

### В Allure Report:
```
Test: test_invalid_cvss_score
Status: FAILED
Duration: 0.12s
Error:
  AssertionError: assert 400 == 422
  
Call Stack:
  File "test_api_vulnerabilities.py", line XX, in test_invalid_cvss_score
    assert response.status_code == 422
```

---

## **Быстрый старт всё в одном (для ускорения)**

```bash
# 1. Запустить Docker контейнеры
docker compose up -d --build

# 2. Подождать готовности (проверка health)
docker compose exec backend curl http://localhost:8000/api/v1/health

# 3. Скриншот 1 — контейнеры
docker compose ps > screenshot_1_docker_ps.txt

# 4. Скриншот 2 — открыть браузер на http://localhost:8000/api/v1/docs

# 5. Скриншот 3 — структура БД
docker compose exec db psql -U vuln -d vuln_mgmt -c "\dt" > screenshot_3_db_structure.txt

# 6. Локальные тесты (если Python установлен)
cd backend
set PYTHONPATH=.
set DISABLE_SEED=1
pytest --tb=short > screenshot_4_pytest_output.txt

# 7. Verbose вывод
pytest -v -s --tb=short > screenshot_5_pytest_verbose.txt

# 8-9. Allure отчёты
pip install allure-pytest
pytest --alluredir=allure-results -v
allure generate allure-results -o allure-report --clean
allure open allure-report
```

---

## **Обратите внимание**

- На Windows используйте `set` вместо `export`
- На Linux/Mac используйте `export`
- Docker Desktop должен быть запущен
- PostgreSQL должен быть доступен на `localhost:5432`
- Python 3.12+ должен быть установлен

---

Готово! Все 9 скриншотов получены.
