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
- Gunicorn for production WSGI serving
- WhiteNoise for staging static assets
- Celery with Redis for asynchronous AI jobs

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

## Experimental Local Small LLM

The repository includes an experimental OpenAI-compatible local provider for
model-lab evaluation only. Groq remains the production default and the provider
factory does not silently fall back to a local model.

Server-side settings:

```env
SMALL_LLM_EXPERIMENT_ENABLED=false
LOCAL_LLM_ENABLED=false
LOCAL_LLM_BASE_URL=http://127.0.0.1:8080/v1
LOCAL_LLM_MODEL=Qwen/Qwen3-1.7B
LOCAL_LLM_TIMEOUT_SECONDS=120
LOCAL_LLM_MAX_OUTPUT_TOKENS=2048
```

Local evaluation command:

```bash
LOCAL_LLM_ENABLED=true .venv/bin/python manage.py evaluate_small_llm --provider local --model Qwen/Qwen3-1.7B --limit 10
```

Do not expose local model settings through frontend variables. Do not commit
model weights, caches, adapters, or evaluation outputs.

## Asynchronous AI Generation

The weekly content-plan API now supports an asynchronous queue path while the existing synchronous endpoint remains available:

- Synchronous: `POST /api/ai/content-plans/generate/`
- Asynchronous queue: `POST /api/ai/content-plans/queue/`
- Status polling: `GET /api/ai/content-plans/<generation_id>/status/`

The queue endpoint validates the authenticated user, business access, input, and quotas before creating an `AIContentGeneration` with `status=queued`. It enqueues Celery only after the database transaction commits and passes only the generation UUID to the worker. The database record remains the durable source of product status: `queued`, `running`, `retrying`, `completed`, `failed`, and `cancelled`.

Use `Idempotency-Key` on queue requests to prevent duplicate submissions. Keys are scoped to the authenticated user and business. Reusing the same key with the same request returns the existing generation; reusing it with a different request returns `409`.

Local Redis and worker:

```bash
docker compose up -d postgres redis
CELERY_TASK_ALWAYS_EAGER=false AI_ASYNC_CONTENT_PLAN_ENABLED=true celery -A config worker --loglevel=INFO --concurrency=1
```

Useful local settings:

```env
AI_ASYNC_CONTENT_PLAN_ENABLED=true
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_ALWAYS_EAGER=false
CELERY_TASK_EAGER_PROPAGATES=true
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_ACKS_LATE=true
```

Tests can run without an external Redis service by setting `CELERY_TASK_ALWAYS_EAGER=true`.

Opt-in Redis broker integration test:

```bash
RUN_REDIS_INTEGRATION=true USE_SQLITE=false CELERY_TASK_ALWAYS_EAGER=false .venv/bin/pytest tests/test_celery_integration.py
```

Railway staging worker:

- Service: `ai-business-growth-celery-worker-staging`
- Config file: `railway.worker.toml`
- Command: `celery -A config worker --loglevel=INFO --concurrency=1 --uid=nobody`
- Redis: private Railway service `Redis`
- Public domain: none

The live Railway backend has Redis-aware readiness enabled. The Vercel staging frontend now has `NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=true` enabled for the public async polling flow. The synchronous endpoint remains available as the immediate frontend rollback path.

## Asynchronous Business Reports

Business-performance reports now use the reusable `common.BackgroundJob` model rather than overloading `AIContentGeneration`.

Endpoints:

- `POST /api/reports/queue/`
- `GET /api/reports/jobs/<job_id>/status/`
- `GET /api/reports/<report_id>/`
- `GET /api/reports/`
- `GET /api/reports/<report_id>/export.csv/`
- `GET /api/reports/<report_id>/export.json/`

The queue endpoint validates authentication, business ownership, report type, date range, and idempotency before committing a job. Celery is enqueued through `transaction.on_commit()` with only the background-job UUID. PostgreSQL stores job status, coarse progress, attempts, sanitized failures, report output, and exportable structured content.

Supported report type:

```text
business_performance
```

The report computes stored metrics only: draft/status counts, published-post records where present, platform/type/objective breakdowns, AI generation counts, token totals, recent trends, competitor observations, and data limitations. It does not invent reach, impressions, clicks, engagement rate, revenue, conversions, or follower growth.

Optional AI recommendations are disabled unless `REPORT_AI_RECOMMENDATIONS_ENABLED=true`. When enabled, the provider receives aggregate metrics and minimal business context only. Recommendations must include `requires_human_review=true`.

Activation flags:

```env
ASYNC_REPORTS_ENABLED=false
REPORT_AI_RECOMMENDATIONS_ENABLED=false
REPORT_MAX_PERIOD_DAYS=366
```

The frontend report UI is controlled separately by `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=false`. Staging report activation is not enabled by default. See `../docs/ASYNC_REPORTS.md` for lifecycle, retry, export, and future social-sync notes.

## Verified Async Report Rollout

On 2026-08-01 the existing Railway web and worker services were redeployed with async report processing enabled, while keeping the same PostgreSQL and Redis resources and the synchronous report fallback in place.

- Web deployment: `8221c1fa-e51d-4a27-92fe-2d827d692d5b`
- Worker deployment: `0d025af3-34d5-4ce7-9a32-793dd5f8bc84`
- Health remained `{"status":"ok","database":"ok","redis":"ok"}`
- The report queue returned `202 Accepted`
- The browser smoke test verified authentication, report queueing, report completion, report history, notifications, logout, and protected-route behavior.

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

Production/staging start command:

```bash
sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"
```

Release commands:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Static files are served through WhiteNoise in production settings with compressed manifest storage. The active staging deployment uses Railway for Django and PostgreSQL, paired with Vercel for the Next.js frontend. The preserved Render configuration is inactive because Render private-repository fetches remained blocked.

Railway staging files:

- `.railwayignore` excludes local secrets, SQLite databases, virtual environments, caches, tests, and generated static output from local-source upload.
- `railway.toml` defines the health-check path and Gunicorn start command.
- `railway.worker.toml` defines the private Celery worker build and start command.
- `Dockerfile` runs `collectstatic`, applies migrations, and starts Gunicorn against the platform `$PORT`.

Active staging backend:

```text
https://ai-business-growth-backend-staging-production.up.railway.app
```

Active staging frontend:

```text
https://ai-business-growth-platform-staging.vercel.app
```

Verified staging tag:

```text
v0.2.0-staging
```

Staging deployment is provider-native. Railway and Vercel should autodeploy from GitHub `main` after CI, while the GitHub staging workflow validates backend/frontend code and verifies live staging health. Public staging URLs and platform IDs are stored as GitHub variables. PR #8 merged the provider-native verification workflow, final main CI passed, and the main staging verification run `30491459546` passed. Railway and Vercel still require one-time account-owner GitHub connection steps before automatic provider deployments can be claimed.

Live async staging UI verification:

- Vercel deployment `dpl_4pjgXq6F398AsLjgPw2q5GQDZiQa` enabled the async frontend flag.
- Browser smoke test queued one seven-day content-plan job through the live Next.js proxy, Railway web service, private Redis service, and Celery worker.
- Observed states were `submitting`, `queued`, `running`, and `completed`.
- The completed result contained exactly seven items for days 1 through 7 with provider `groq`, model `openai/gpt-oss-20b`, and nonzero token counts.
- Draft conversion and duplicate-draft prevention passed; drafts remained unapproved, unscheduled, and unpublished.
- Safe failure presentation and logout/protected-route behavior passed.

See `../docs/STAGING_DEPLOYMENT.md` for environment variables, smoke-test results, backup/restore notes, rollback limits, and Railway usage controls.

## API Docs

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

## Health Endpoints

- `GET /api/health/live/` returns minimal liveness JSON.
- `GET /api/health/ready/` verifies database connectivity. When `AI_ASYNC_CONTENT_PLAN_ENABLED=true` or `ASYNC_REPORTS_ENABLED=true` and Celery eager mode is off, readiness also verifies Redis connectivity. It does not call Groq, prove worker liveness, or expose settings.

## CI

GitHub Actions runs backend checks, migrations, Django tests, pytest, Redis/Celery integration tests, Ruff, mypy, frontend lint/typecheck/tests/build, and safe secret scans. CI uses PostgreSQL and Redis services plus placeholder Groq secrets with mocked Groq calls.

## Backup Considerations

For production, back up PostgreSQL with point-in-time recovery where possible and retain migration history with releases. Test restore procedures before launch. SQLite files are local development artifacts and are ignored by source control.

## MongoDB Migration

```bash
.venv/bin/python manage.py migrate_from_mongodb --dry-run
.venv/bin/python manage.py migrate_from_mongodb
```

Original MongoDB ObjectIds are stored in `legacy_mongo_id`. API responses expose `_id` for frontend compatibility.
