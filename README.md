# Items — каталог товарів

Розподілене вебрішення для керування списком товарів (CRUD): створення, перегляд, оновлення та видалення.
Лабораторні роботи №1–4 з дисципліни «Методи та технології забезпечення CI/CD».

## Компоненти

| Компонент | Каталог | Технології | Образ Docker Hub |
|---|---|---|---|
| Backend (REST API) | `app/` | Python 3.12, FastAPI, SQLAlchemy 2 (ORM, Code-First) | `kontorsk1yqqez/items-api` |
| Frontend (SPA) | `frontend/` | HTML + JavaScript, nginx 1.27 | `kontorsk1yqqez/items-frontend` |
| Міграції БД (консольний застосунок) | `migrator/` | Alembic | `kontorsk1yqqez/items-migrator` |
| База даних | — | PostgreSQL 16 | `postgres:16-alpine` |
| Helm Chart | `k8s/items-app/` | Helm 3 | артефакт CI `helm-chart` |

```
Browser ──> Ingress (nginx) ──/api──> Service api (NodePort) ──> Deployment api ──> Service db ──> StatefulSet PostgreSQL ──> PVC/PV
                      └──────/────> Service frontend ──> Deployment frontend (nginx + SPA)
Job migration (Alembic, initContainer чекає БД) ──> PostgreSQL
```

## Backend API

| Метод | Endpoint | Опис | Коди відповіді |
|---|---|---|---|
| GET | /api/items | Отримати список об'єктів | 200 |
| GET | /api/items/{id} | Отримати об'єкт за ідентифікатором | 200, 404 |
| POST | /api/items | Створити новий об'єкт | 201, 422 |
| PUT | /api/items/{id} | Оновити наявний об'єкт | 200, 404, 422 |
| DELETE | /api/items/{id} | Видалити об'єкт | 204, 404 |
| GET | /healthz | Перевірка стану (включно з підключенням до БД) | 200 |

Swagger UI: `/docs`, специфікація OpenAPI: `/openapi.json`.

## Конфігурація

| Змінна | Компонент | Опис |
|---|---|---|
| `DATABASE_URL` | api, migrator | ConnectionString SQLAlchemy, напр. `postgresql+psycopg://items:pass@host:5432/items`. У Kubernetes береться з Secret, що генерується чартом для кожного релізу/середовища |
| `API_BASE_URL` | frontend | адреса API для браузера (за замовчуванням відносний `/api` — запити йдуть на той самий host, де Ingress спрямовує `/api` до backend) |
| `API_UPSTREAM` | frontend | адреса backend для проксі `/api/` у nginx (корисно при port-forward) |

## Локальний запуск і тести

```bash
pip install -r requirements-dev.txt
python -m pytest            # тести використовують in-memory SQLite
```

Міграції (Code-First): моделі в `app/models.py`, міграції в `migrator/migrations/versions/`.

```bash
# нова міграція після зміни моделей
cd migrator && DATABASE_URL=... PYTHONPATH=.. alembic revision --autogenerate -m "опис"
# застосувати міграції
docker run --rm -e DATABASE_URL=... kontorsk1yqqez/items-migrator:latest upgrade head
```

## Збирання Docker-образів

```bash
docker build -t kontorsk1yqqez/items-api:latest .
docker build -t kontorsk1yqqez/items-frontend:latest frontend
docker build -t kontorsk1yqqez/items-migrator:latest -f migrator/Dockerfile .
```

## Helm Chart

Чарт розташований у `k8s/items-app` (створений командою `helm create items-app` у каталозі `k8s`).
Версія чарта та застосунку задаються в `k8s/items-app/Chart.yaml` (`version`, `appVersion`).
Параметри шаблонів — у `k8s/items-app/values.yaml`; налаштування середовища `lab` — у `k8s/values.lab.yaml`.

Чарт встановлює всі компоненти: StorageClass, PersistentVolume, PersistentVolumeClaim, StatefulSet і headless Service
PostgreSQL, Secret з обліковими даними та ConnectionString, Job міграцій, Deployment/Service/ConfigMap API,
Deployment/Service frontend, Ingress і тест `helm test`.

### Пакування чарта

```bash
helm lint k8s/items-app --strict
helm lint k8s/items-app -f k8s/values.lab.yaml --strict
helm package k8s/items-app --destination dist          # -> dist/items-app-0.1.0.tgz
```

### Встановлення

Потрібен кластер Kubernetes з NGINX Ingress Controller. Приклад для kind:

```bash
kind create cluster --config k8s/kind-webapp.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=180s

helm upgrade --install lab k8s/items-app \
  -n webapp-lab --create-namespace \
  -f k8s/values.lab.yaml \
  --wait --wait-for-jobs --timeout 5m

helm test lab -n webapp-lab --logs
```

Встановлення з архіву, отриманого з артефактів CI: `helm install lab items-app-0.1.0.tgz -n webapp-lab --create-namespace -f k8s/values.lab.yaml`.

Після встановлення застосунок доступний за адресою з `ingress.host`
(для `values.lab.yaml` — http://webapp.127.0.0.1.nip.io/, nip.io резолвиться в 127.0.0.1).
Для host `webapp.lab.test` з `values.yaml` додайте в hosts рядок `127.0.0.1 webapp.lab.test`.

Видалення: `helm uninstall lab -n webapp-lab` (PV з політикою Retain залишається, видаляється вручну).

## CI (GitHub Actions)

Файли в `.github/workflows/`:

- `ci.yml` — запускається після push у `main`, `feature/**`, `bugfix/**`
  (зміни лише в `docs/` або `README.md` CI не запускають). Jobs:
  - `build-n-test` — встановлення залежностей, компіляція, unit-тести (pytest), звіт `test-results.xml` в артефактах;
  - `docker-pack-n-push` — matrix із трьох образів (api, frontend, migrator), кожен збирається reusable workflow;
  - `helm-pack` — `helm lint`, `helm template`, `helm package`; архів чарта зберігається в артефакті `helm-chart`.
- `docker-pack-n-push.yml` — reusable workflow (`workflow_call`) з параметрами `repository`, `tag`,
  `context`, `dockerfile`, `push`, `artifact-name`, `retention-days`.
  Для гілки `main` образ публікується в Docker Hub, для інших гілок — зберігається як `.tar` в артефактах запуску.

Необхідні GitHub Secrets (Settings → Secrets and variables → Actions):

| Secret | Значення |
|---|---|
| `DOCKERHUB_USERNAME` | логін Docker Hub |
| `DOCKERHUB_TOKEN` | Personal Access Token Docker Hub (Read & Write) |

Опційна змінна `DOCKERHUB_NAMESPACE` (Variables) перевизначає простір імен образів (за замовчуванням `kontorsk1yqqez`).

Попередній CI для Azure DevOps (лабораторна №1) — файл `azure-pipelines.yml`.
