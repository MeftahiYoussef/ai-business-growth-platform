# Django Backend

Django REST Framework backend for the AI Business Growth & Trend Intelligence Platform.

## Stack

- Django 5
- Django REST Framework
- Simple JWT
- PostgreSQL
- Django ORM
- django-cors-headers
- drf-spectacular OpenAPI docs

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
USE_SQLITE=true .venv/bin/python manage.py migrate
.venv/bin/python manage.py seed
USE_SQLITE=true .venv/bin/python manage.py runserver 8000
```

## Environment

See `.env.example` for all variables. SQLite is available for local fallback:

```bash
USE_SQLITE=true
```

PostgreSQL mode uses backend-only database variables:

```env
USE_SQLITE=false
DATABASE_NAME=business_intelligence
DATABASE_USER=business_intelligence
DATABASE_PASSWORD=
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
DATABASE_CONN_MAX_AGE=60
DATABASE_SSLMODE=prefer
```

`DATABASE_SSLMODE` is passed to psycopg and should be set according to the hosting provider, commonly `require` or `verify-full` in production. Do not expose database credentials to the frontend.

## Local PostgreSQL

Start only the development database:

```bash
docker compose up -d postgres
```

If host port `5432` is already in use, publish the container on another local port and set `DATABASE_PORT` to match:

```bash
POSTGRES_PUBLISHED_PORT=5434 docker compose up -d postgres
USE_SQLITE=false DATABASE_PORT=5434 .venv/bin/python manage.py migrate
```

Run migrations and tests without falling back to SQLite:

```bash
USE_SQLITE=false .venv/bin/python manage.py migrate
USE_SQLITE=false .venv/bin/python manage.py check
USE_SQLITE=false .venv/bin/python manage.py makemigrations --check --dry-run
USE_SQLITE=false .venv/bin/python manage.py test
USE_SQLITE=false .venv/bin/pytest
```

Print the active database engine before a verification run:

```bash
USE_SQLITE=false .venv/bin/python manage.py shell -c "from django.db import connection; print(connection.settings_dict['ENGINE'])"
```

## AI Provider

Groq is the only active AI provider. Place the key only in `django-backend/.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_secret_key
GROQ_DEFAULT_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=60
GROQ_MAX_RETRIES=2
GROQ_MAX_OUTPUT_TOKENS=4000
```

The model name `openai/gpt-oss-20b` is accessed through Groq.
Groq content-plan generation uses non-streaming Chat Completions with structured JSON schema output. Django validates the returned JSON again before saving history or creating drafts. Do not add Groq keys to frontend environment variables or expose them with a public client-side prefix.

Safe configuration check without printing the key:

```bash
AI_PROVIDER=groq USE_SQLITE=true .venv/bin/python manage.py shell -c "from django.conf import settings; print(settings.AI_PROVIDER); print(settings.GROQ_DEFAULT_MODEL); print(bool(settings.GROQ_API_KEY))"
```

Expected output when configured:

```text
groq
openai/gpt-oss-20b
True
```

If Groq returns rate-limit errors, the API responds with `429`. Free-tier limits may change; reduce request frequency or update the GroqCloud plan.

## Commands

```bash
USE_SQLITE=true .venv/bin/python manage.py check
USE_SQLITE=true .venv/bin/python manage.py makemigrations --check --dry-run
USE_SQLITE=true .venv/bin/python manage.py migrate
USE_SQLITE=true .venv/bin/python manage.py test
USE_SQLITE=true .venv/bin/pytest
USE_SQLITE=true .venv/bin/ruff check .
USE_SQLITE=true .venv/bin/mypy .
```

## Production Settings

Use `DJANGO_SETTINGS_MODULE=config.settings.production` with explicit environment values:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `USE_SQLITE=false`
- `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`
- `DATABASE_CONN_MAX_AGE`
- `DATABASE_SSLMODE`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `USE_X_FORWARDED_PROTO` when a trusted proxy terminates TLS
- safe Groq values: `AI_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_DEFAULT_MODEL`

Deployment check:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production USE_SQLITE=false .venv/bin/python manage.py check --deploy
```

## API Docs

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

## Health Endpoints

- `GET /api/health/live/` returns minimal liveness JSON.
- `GET /api/health/ready/` verifies database connectivity only. It does not call Groq or expose settings.

## CI

GitHub Actions runs backend checks, migrations, Django tests, pytest, Ruff, mypy, frontend lint/typecheck/tests/build, and safe secret scans. CI uses PostgreSQL as a service and placeholder Groq secrets with mocked Groq calls.

## Backup Considerations

For production, back up PostgreSQL with point-in-time recovery where possible and retain migration history with releases. Test restore procedures before launch. SQLite files are local development artifacts and are ignored by source control.

## MongoDB Migration

```bash
.venv/bin/python manage.py migrate_from_mongodb --dry-run
.venv/bin/python manage.py migrate_from_mongodb
```

Original MongoDB ObjectIds are stored in `legacy_mongo_id`. API responses expose `_id` for frontend compatibility.
