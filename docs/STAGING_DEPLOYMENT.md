# Staging Deployment Rehearsal

Last updated: 2026-07-29.

This runbook records the live staging deployment for the AI Business Growth & Trend Intelligence Platform. Do not place real credentials in this file or in any committed platform environment file.

## Active Architecture

- Frontend: Vercel-managed Next.js deployment from `frontend/`.
- Backend: Railway-managed Django service uploaded from local source in `django-backend/`.
- Database: Railway PostgreSQL attached to the Django service.
- AI: Groq only, model `openai/gpt-oss-20b`.
- Secrets: platform-managed environment variables in Railway, Vercel, and GitHub.

Render is no longer the active staging backend path because Render could not fetch the private GitHub repository from the active workspace after repeated GitHub App authorization attempts. The existing Render PostgreSQL resource `ai-business-growth-postgres-staging` remains preserved and unused; no staging application data is written to it.

The legacy Node.js backend is not part of this deployment.

## Live Resources

- Railway project: `ai-growth-staging`
- Railway backend service: `ai-business-growth-backend-staging`
- Railway PostgreSQL service: `Postgres`
- Railway backend URL: `https://ai-business-growth-backend-staging-production.up.railway.app`
- Vercel project: `ai-business-growth-platform-staging`
- Vercel frontend URL: `https://ai-business-growth-platform-staging.vercel.app`
- Preserved inactive Render database: `ai-business-growth-postgres-staging`

Railway resources are usage-metered. No paid plan upgrade or payment-card action was selected during this rehearsal.

## Backend Environment

Required Railway variables:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=false
DJANGO_SECRET_KEY=<platform-managed-secret>
DJANGO_ALLOWED_HOSTS=ai-business-growth-backend-staging-production.up.railway.app,healthcheck.railway.app
CORS_ALLOWED_ORIGINS=https://ai-business-growth-platform-staging.vercel.app
CSRF_TRUSTED_ORIGINS=https://ai-business-growth-platform-staging.vercel.app,https://ai-business-growth-backend-staging-production.up.railway.app

USE_SQLITE=false
DATABASE_NAME=${{Postgres.PGDATABASE}}
DATABASE_USER=${{Postgres.PGUSER}}
DATABASE_PASSWORD=<platform-managed-secret-or-service-reference>
DATABASE_HOST=${{Postgres.PGHOST}}
DATABASE_PORT=${{Postgres.PGPORT}}
DATABASE_CONN_MAX_AGE=60
DATABASE_SSLMODE=prefer

AI_PROVIDER=groq
GROQ_API_KEY=<platform-managed-secret>
GROQ_DEFAULT_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=60
GROQ_MAX_RETRIES=2
GROQ_MAX_OUTPUT_TOKENS=4000

AI_MAX_USER_DAILY_REQUESTS=20
AI_MAX_BUSINESS_MONTHLY_REQUESTS=500
AI_MAX_REQUEST_INPUT_LENGTH=4000
AI_MAX_ADDITIONAL_INSTRUCTIONS_LENGTH=1200

SECURE_SSL_REDIRECT=true
USE_X_FORWARDED_PROTO=true
WEB_CONCURRENCY=1
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
DJANGO_LOG_LEVEL=INFO
```

`DJANGO_SECRET_KEY`, `DATABASE_PASSWORD`, and `GROQ_API_KEY` must never be printed, committed, or exposed to the frontend.

## Backend Build And Start

Railway configuration:

- Config file: `django-backend/railway.toml`
- Source exclusions: `django-backend/.railwayignore`
- Dockerfile: `django-backend/Dockerfile`
- Health check: `/api/health/ready/`

Start command:

```bash
sh -c "python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-1} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"
```

Django's development server must not be used in staging.

## Static Files

Staging uses WhiteNoise with Django `collectstatic` and compressed manifest static files. The live Railway deployment copied static files successfully and served API docs over HTTPS.

## Frontend Environment

Required Vercel variable for Production and Preview:

```env
NEXT_PUBLIC_API_URL=https://ai-business-growth-backend-staging-production.up.railway.app
```

Do not define `NEXT_PUBLIC_GROQ_API_KEY`, database credentials, Django secrets, JWT signing secrets, or provider secrets. Frontend requests go through same-origin Next.js route handlers under `/api/backend/*`, which attach the HTTP-only cookie token to Django server-side.

## Cross-Origin Authentication

Verified staging behavior:

- `GET /` redirects unauthenticated users to `/login`.
- Registration and login work through the deployed frontend.
- The access token is stored in an HTTP-only, `Secure`, `SameSite=Lax` cookie.
- Refreshing the browser preserves the session.
- Protected routes load while authenticated and redirect or reject access after logout.
- CORS is restricted to the Vercel staging origin.
- CSRF trusted origins include the Vercel and Railway HTTPS origins.
- JWT values are not returned in response bodies or browser JavaScript.

## Health Checks

Verified live results:

- `GET /api/health/live/`: HTTP 200, minimal JSON.
- `GET /api/health/ready/`: HTTP 200, PostgreSQL readiness only.
- `HEAD /api/docs/`: HTTP 200.

Readiness does not call Groq.

## Smoke-Test Result

Controlled staging data was used only.

- Registration: passed.
- Login/current-user: passed.
- Business creation: passed.
- Real Groq seven-day content plan: passed.
- Generation status: `completed`.
- Provider/model: `groq` / `openai/gpt-oss-20b`.
- Token usage: nonzero input and output tokens persisted.
- Request metadata: request ID stored when available, finish reason `stop`.
- Structured output: exactly seven items with days `1` through `7`.
- Human review: every item had `requires_human_review=true`.
- Draft conversion: days 1 and 2 created exactly two drafts.
- Duplicate conversion: second conversion created zero additional drafts.
- Draft workflow states: drafts remained unapproved, unscheduled, and unpublished.
- Logout/protected route: passed.

Safe failure checks passed for invalid login, unauthenticated access, invalid content-plan request, and cross-business access. Provider timeout and quota handling remain covered by automated tests rather than damaging live staging secrets.

## Logging

Railway build and runtime logs were scanned for forbidden markers without printing secret values. No `gsk_`, Groq key variable, Django secret variable, database password marker, credential-bearing database URL marker, authorization header marker, bearer token marker, cookie marker, or app auth cookie marker was found in the retained runtime logs.

During backup setup, a database tunnel log exposed an active staging database password field to local tool output. The staging database password was immediately rotated, the backend variable was updated through Railway without printing the new value, the backend was redeployed, health checks passed again, and the temporary SSH key and local tunnel logs were removed.

## Backup And Restore

A logical Railway PostgreSQL backup was created outside the repository:

- Backup path: `/private/tmp/ai-business-growth-backups/staging-20260729-030000.dump`
- Size: 173 KB
- Format: custom `pg_dump`

Restore rehearsal used a separate temporary Railway PostgreSQL service, not the active staging database. Verification confirmed:

- Django migration history exists.
- Staging business data exists.
- Groq generation history exists.
- Structured seven-item output exists.
- Draft links exist.
- The duplicate-draft database protection exists as the partial unique index `unique_ai_generation_plan_day_draft`.

The temporary restore database service was deleted after verification.

## Rollback

The current Railway deployment is healthy after the Railway-specific deployment configuration and database credential rotation. A rollback to `v0.1.0-foundation` was not executed because that tag predates the Railway deployment files and would not reproduce the active local-source staging deployment safely. Do not reverse database migrations automatically during rollback.

Safe rollback options for the next rehearsal:

1. Use Railway deployment history to redeploy the latest known-good Railway deployment.
2. Create a Railway-compatible release tag after this branch is merged.
3. Verify liveness, readiness, login, and existing records after rollback.
4. Redeploy the latest `main` source after the rehearsal.

## GitHub Deployment Workflow

Manual workflow: `.github/workflows/deploy-staging.yml`.

The workflow:

- runs only through `workflow_dispatch`;
- uses the GitHub environment named `staging`;
- validates backend and frontend before deployment;
- uses PostgreSQL service validation with placeholder Groq settings;
- deploys the Django backend to Railway through `railway up`;
- references Railway, Vercel, and URL values by secret or variable name only;
- fails when backend or frontend health checks fail.

Required GitHub secrets:

```text
RAILWAY_TOKEN
RAILWAY_PROJECT_ID
RAILWAY_BACKEND_SERVICE_ID
VERCEL_FRONTEND_DEPLOY_HOOK_URL
STAGING_BACKEND_URL
STAGING_FRONTEND_URL
```

Optional GitHub variable:

```text
RAILWAY_ENVIRONMENT=production
```

The GitHub `staging` environment exists, but no deployment secrets are configured. The current GitHub plan rejected environment wait-timer protection rules, so manual approval/protection should be added later if the plan supports it. The manual workflow should not be run until the required secret values are configured.

## Remaining Limits

- Railway is active staging; Render PostgreSQL is preserved but unused.
- Railway resources are usage-metered; monitor usage and stop before any unwanted paid-plan requirement.
- No production deployment exists.
- No object storage, Celery, Redis, social OAuth, billing, RAG, or social publishing is configured.
