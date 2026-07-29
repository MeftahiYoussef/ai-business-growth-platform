# Staging Deployment Rehearsal

This runbook prepares a reproducible staging rehearsal for the AI Business Growth & Trend Intelligence Platform. Do not place real credentials in this file or in any committed platform environment file.

## Selected Architecture

- Frontend: Vercel-managed Next.js deployment from `frontend/`.
- Backend: Render-managed Python web service from `django-backend/`.
- Database: Render PostgreSQL attached to the backend service.
- Secrets: platform-managed environment variables in Render, Vercel, and the GitHub `staging` environment.

This is the smallest architecture that matches the repository: Next.js can run as a managed app, Django can run as a managed WSGI service, and PostgreSQL remains isolated from local SQLite. The existing legacy Node.js backend is not part of this deployment.

## Current Staging Rehearsal State

Last updated: 2026-07-29.

- GitHub PR #1 was merged into `main` at merge commit `f219394`.
- Render authentication succeeded for `Meftahi's workspace`.
- Vercel authentication succeeded for account `meftahyyyoussef-4358`.
- Render PostgreSQL was created:
  - name: `ai-business-growth-postgres-staging`
  - id: `dpg-d9kln4taeets739n9060-a`
  - database: `business_intelligence_staging`
  - user: `business_intelligence_staging`
  - region: Oregon
  - plan: free
  - status: available
- Render Django backend was not created because Render cannot yet fetch the private GitHub repository. The Render GitHub App must be authorized for `MeftahiYoussef/ai-business-growth-platform`.
- Intended backend URL after service creation: `https://ai-business-growth-backend-staging.onrender.com`.
- Vercel frontend was deployed:
  - project: `ai-business-growth-platform-staging`
  - production alias: `https://ai-business-growth-platform-staging.vercel.app`
  - deployment URL: `https://ai-business-growth-platform-staging-hm26tudfb.vercel.app`
  - deployment id: `dpl_2mAztDEbcTbfW4XwQ1mSicMAuHzw`
  - status: ready
- Vercel `NEXT_PUBLIC_API_URL` is configured for Production and Preview with the intended Render backend URL.
- Verified frontend HTTPS:
  - `GET /login` returned HTTP 200.
  - `GET /` returned HTTP 307 to `/login`.
- Live backend health checks, API docs, registration/login through Django, Groq generation, draft conversion, backup, restore, rollback, and manual GitHub deployment workflow remain blocked until the Render backend service can be created.

Exact account-owner action required:

1. Open `https://dashboard.render.com/account/repo-connections`.
2. Connect GitHub if it is not connected.
3. Install or configure the Render GitHub App with access to `MeftahiYoussef/ai-business-growth-platform`.
4. Re-run the Render service creation using `render.yaml` or the documented service settings.

## Backend Environment

Required Render environment variables:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<platform-managed-secret>
DJANGO_ALLOWED_HOSTS=<backend-hostname>
CORS_ALLOWED_ORIGINS=https://<frontend-hostname>
CSRF_TRUSTED_ORIGINS=https://<frontend-hostname>,https://<backend-hostname>

USE_SQLITE=false
DATABASE_NAME=<staging-db-name>
DATABASE_USER=<staging-db-user>
DATABASE_PASSWORD=<platform-managed-secret>
DATABASE_HOST=<staging-db-host>
DATABASE_PORT=5432
DATABASE_CONN_MAX_AGE=60
DATABASE_SSLMODE=require

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
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
USE_X_FORWARDED_PROTO=true
DJANGO_LOG_LEVEL=INFO
```

`DJANGO_SECRET_KEY`, `DATABASE_PASSWORD`, and `GROQ_API_KEY` must be generated or stored in Render secrets. Never expose them to the frontend.

Generate a Django secret locally only when you can store it directly into the platform secret field without printing or committing it:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Backend Build And Start

Render blueprint file: `render.yaml`.

Backend root directory:

```text
django-backend
```

Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Free Render web services do not support `preDeployCommand`, so migrations run at startup before Gunicorn. Start command:

```bash
sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"
```

Django's development server must not be used in staging.

## Static Files

Staging uses WhiteNoise with Django `collectstatic` and compressed manifest static files. This covers Django admin, DRF, and OpenAPI static assets without adding object storage. Future user-uploaded media should use managed object storage; it is outside this rehearsal.

## Frontend Environment

Required Vercel environment variable:

```env
NEXT_PUBLIC_API_URL=https://<backend-staging-host>
```

Do not define `NEXT_PUBLIC_GROQ_API_KEY`, database credentials, Django secrets, JWT signing secrets, or provider secrets. Frontend requests go through Next.js route handlers under `/api/backend/*`, which attach the HTTP-only cookie token to Django server-side.

Frontend build command:

```bash
npm run build
```

Frontend start command is platform-managed by Vercel.

## Cross-Origin Authentication

The browser stores the JWT access token in a secure HTTP-only Next.js cookie named `ai_growth_token` when `NODE_ENV=production`. API calls stay same-origin from browser to Next.js. Next.js route handlers call the remote Django API using `NEXT_PUBLIC_API_URL`.

Staging requirements:

- Frontend URL uses HTTPS.
- Backend URL uses HTTPS.
- `CORS_ALLOWED_ORIGINS` includes only the frontend origin.
- `CSRF_TRUSTED_ORIGINS` includes frontend and backend HTTPS origins.
- Cookies remain `Secure`, HTTP-only, `SameSite=Lax`, path `/`.
- JWT tokens are not exposed to browser JavaScript.
- Logout clears the same-origin auth cookie.

## Migration Rehearsal

Run against staging PostgreSQL only:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py showmigrations
```

Before migrations, confirm the engine safely:

```bash
python manage.py shell -c "from django.db import connection; print(connection.settings_dict['ENGINE']); print(connection.settings_dict['HOST']); print(connection.settings_dict['PORT']); print(connection.settings_dict['NAME'])"
```

Expected engine:

```text
django.db.backends.postgresql
```

Do not load local development data automatically. Create a staging superuser only through a secure platform shell command and do not store credentials in repository files.

## Health Checks

- Backend liveness: `GET https://<backend-host>/api/health/live/`
- Backend readiness: `GET https://<backend-host>/api/health/ready/`
- API docs: `GET https://<backend-host>/api/docs/`
- Frontend: `GET https://<frontend-host>/login`

Readiness verifies database connectivity only. It does not call Groq.

## Smoke-Test Checklist

Use controlled staging data only:

1. Register a new staging user.
2. Log in.
3. Verify `/api/auth/me`.
4. Create a business workspace.
5. Complete the business and brand profile fields currently supported by the UI/API.
6. Generate a Groq seven-day content plan.
7. Confirm exactly seven items.
8. Confirm provider, model, prompt version, token usage, request ID when available, and finish reason are stored.
9. Convert day 1 and day 2 into drafts.
10. Repeat conversion and confirm no duplicates.
11. Confirm drafts remain unapproved.
12. Confirm drafts remain unscheduled.
13. Confirm drafts remain unpublished.
14. Log out.
15. Confirm protected routes redirect or reject access.

## Safe Failure Tests

Run without changing the real Groq key:

- Invalid login returns a sanitized authentication error.
- Unauthenticated protected endpoint returns `401`.
- Cross-business generation or draft conversion is blocked.
- Invalid content-plan request returns validation errors.
- Temporary low quota setting in an isolated staging test blocks generation with `429`.
- Readiness failure is tested through isolated configuration or automated tests, not by damaging the active database.
- Missing required production environment variables are tested in a non-deployed shell with placeholder values.

## Logging

Staging logs include safe request-completion records:

- request method
- route
- status code
- duration in milliseconds
- request ID

AI generation records include provider, model, token counts, request ID when available, finish reason, and generation status in the database. Logs and API responses must not include Groq keys, database passwords, authorization headers, cookies, JWTs, OAuth tokens, or user passwords.

Future monitoring can connect Render/Vercel logs to an error-monitoring service. That integration is intentionally not part of this rehearsal.

## Backup And Restore

Before launch, confirm the selected Render PostgreSQL plan's backup policy. If the plan does not include managed backups, use a manual logical backup from a secure environment:

```bash
pg_dump --format=custom --file=/secure/path/staging-YYYYMMDD-HHMM.dump "$DATABASE_URL"
```

Restore only into a separate temporary staging database:

```bash
createdb business_intelligence_restore_test
pg_restore --dbname=business_intelligence_restore_test --clean --if-exists /secure/path/staging-YYYYMMDD-HHMM.dump
```

Verify migrations, one sample business, AI generation history, and draft links. Do not restore over the active staging database. Delete the temporary restore database only after verification and only when it is clearly isolated.

## Rollback

Safe application rollback:

1. Record the currently deployed commit SHA.
2. Identify the known-good tag `v0.1.0-foundation`.
3. Confirm new migrations are backward-compatible before deploying older code.
4. Roll back application code only through the platform release UI or deployment history.
5. Do not reverse database migrations automatically.
6. Verify liveness, readiness, login, and one protected API call.
7. Return staging to the latest commit after the rehearsal.

If the platform plan does not support one-click rollback, redeploy the selected tag manually and record the commands used.

## GitHub Deployment Workflow

Manual workflow: `.github/workflows/deploy-staging.yml`.

The workflow:

- runs only through `workflow_dispatch`;
- uses the GitHub environment named `staging`;
- validates backend and frontend before deployment;
- uses PostgreSQL service validation with placeholder Groq settings;
- references deploy hooks and staging URLs by secret name only;
- records the commit SHA;
- triggers Render and Vercel deploy hooks;
- fails when backend or frontend health checks fail.

Required GitHub environment secrets:

```text
RENDER_BACKEND_DEPLOY_HOOK_URL
VERCEL_FRONTEND_DEPLOY_HOOK_URL
STAGING_BACKEND_URL
STAGING_FRONTEND_URL
```

## Remaining External Limits

- No Render or Vercel service has been created by this repository change.
- Paid/free-tier availability must be confirmed in the provider dashboards before provisioning.
- Live staging health checks, Groq smoke tests, backup, restore, and rollback remain blocked until platform authentication and staging resources exist.
- Celery, Redis, social OAuth, billing, RAG, and social publishing are intentionally out of scope.
