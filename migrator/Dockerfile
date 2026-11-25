# Образ консольного застосунку міграцій (контекст збирання — корінь репозиторію)
FROM python:3.12-slim

WORKDIR /migrator
ENV PYTHONPATH=/migrator PYTHONUNBUFFERED=1

COPY migrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ORM-моделі беруться з коду сервера (Code-First)
COPY app ./app
COPY migrator/alembic.ini migrator/migrate.py ./
COPY migrator/migrations ./migrations

ENTRYPOINT ["python", "migrate.py"]
CMD ["upgrade", "head"]
