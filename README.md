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

## CI

Файл `azure-pipelines.yml`: pipeline запускається після push у гілку `main` і виконує етапи
збирання проєкту, запуску unit-тестів, збирання Docker-образу, присвоєння тегів (`latest` і номер збірки)
та публікації образу в Docker Hub.
