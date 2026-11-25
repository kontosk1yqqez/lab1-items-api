# Items API

Простий REST API для керування списком товарів (CRUD): створення, перегляд, оновлення та видалення.
Дані повертаються у форматі JSON, сервіс має специфікацію OpenAPI та Swagger UI.
Лабораторна робота №1 з дисципліни «Методи та технології забезпечення CI/CD».

## Технології

- Мова: Python 3.12
- Фреймворк: FastAPI (сервер uvicorn)
- Тести: pytest
- CI: Azure DevOps Pipelines, Docker Hub

## Endpoints

| Метод | Endpoint | Опис | Коди відповіді |
|---|---|---|---|
| GET | /api/items | Отримати список об'єктів | 200 |
| GET | /api/items/{id} | Отримати об'єкт за ідентифікатором | 200, 404 |
| POST | /api/items | Створити новий об'єкт | 201, 422 |
| PUT | /api/items/{id} | Оновити наявний об'єкт | 200, 404, 422 |
| DELETE | /api/items/{id} | Видалити об'єкт | 204, 404 |

Swagger UI: http://localhost:8000/docs, специфікація OpenAPI: http://localhost:8000/openapi.json

## Збирання та запуск Docker image

```bash
docker build -t items-api .
docker run -d -p 8000:8000 --name items-api items-api
```

Готовий образ з Docker Hub:

```bash
docker run -d -p 8000:8000 kontorsk1yqqez/items-api:latest
```

## Запуск тестів

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## CI (GitHub Actions)

Файли в `.github/workflows/`:

- `ci.yml` — основний workflow. Запускається після push у `main`, `feature/**`, `bugfix/**`
  (зміни лише в `docs/` або `README.md` CI не запускають). Jobs:
  - `build-n-test` — встановлення залежностей, компіляція, unit-тести (pytest), звіт `test-results.xml` в артефактах;
  - `docker-pack-n-push` — виклик reusable workflow збирання Docker-образу.
- `docker-pack-n-push.yml` — reusable workflow (`workflow_call`) з параметрами `repository`, `tag`,
  `context`, `dockerfile`, `push`, `artifact-name`, `retention-days`.
  Для гілки `main` образ публікується в Docker Hub, для інших гілок — зберігається як `.tar` в артефактах запуску.

Необхідні GitHub Secrets (Settings → Secrets and variables → Actions):

| Secret | Значення |
|---|---|
| `DOCKERHUB_USERNAME` | логін Docker Hub |
| `DOCKERHUB_TOKEN` | Personal Access Token Docker Hub (Read & Write) |

Опційна змінна `DOCKERHUB_REPOSITORY` (Variables) перевизначає репозиторій образу (за замовчуванням `kontorsk1yqqez/items-api`).

Завантажити образ з артефакту гілки: `docker load -i items-api-image.tar`.

Попередній CI для Azure DevOps (лабораторна №1) — файл `azure-pipelines.yml`.
