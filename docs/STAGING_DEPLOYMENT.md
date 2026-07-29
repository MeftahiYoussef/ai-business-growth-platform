# Staging Deployment

This document describes the staging baseline for the AI Business Growth & Trend Intelligence Platform. Do not place real credentials in this file.

## Backend Environment

Required Django settings:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=staging.example.com
CORS_ALLOWED_ORIGINS=https://staging.example.com
CSRF_TRUSTED_ORIGINS=https://staging.example.com
USE_SQLITE=false
DATABASE_NAME=business_intelligence_staging
DATABASE_USER=business_intelligence
DATABASE_PASSWORD=
DATABASE_HOST=
DATABASE_PORT=5432
DATABASE_CONN_MAX_AGE=60
DATABASE_SSLMODE=require
AI_PROVIDER=groq
GROQ_API_KEY=
GROQ_DEFAULT_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=60
GROQ_MAX_RETRIES=2
GROQ_MAX_OUTPUT_TOKENS=4000
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
USE_X_FORWARDED_PROTO=true
DJANGO_LOG_LEVEL=INFO
```

`GROQ_API_KEY`, `DATABASE_PASSWORD`, and `DJANGO_SECRET_KEY` must come from the staging secret manager. They must not be exposed to the frontend or committed.

## Frontend Environment

Required frontend variable:

```env
NEXT_PUBLIC_API_URL=https://staging-api.example.com
```

Do not define `NEXT_PUBLIC_GROQ_API_KEY` or any browser-visible provider key.

## Deployment Steps

1. Build and deploy the backend with `DJANGO_SETTINGS_MODULE=config.settings.production`.
2. Run `python manage.py check --deploy` with staging environment values.
3. Run `python manage.py migrate`.
4. Run `python manage.py collectstatic --noinput` if the hosting target serves Django static files.
5. Build and deploy the frontend with the staging API URL.
6. Confirm TLS termination and `X-Forwarded-Proto` handling when `USE_X_FORWARDED_PROTO=true`.

## Health Checks

- Liveness: `GET /api/health/live/`
- Readiness: `GET /api/health/ready/`

Readiness verifies database connectivity only. It must not call Groq or expose settings.

## Smoke-Test Checklist

- Register or log in with a staging test account.
- Create or open a staging business workspace.
- Confirm `/api/health/ready/` returns `{"status":"ok"}`.
- Generate a seven-day content plan with mocked or controlled Groq usage as appropriate for staging.
- Confirm exactly seven items, token metadata, provider metadata, and prompt version are stored.
- Convert two plan items into drafts.
- Confirm drafts remain unapproved, unscheduled, and unpublished.
- Submit the same conversion request again and confirm no duplicate drafts are created.

## Backup and Restore

- Enable managed PostgreSQL backups with point-in-time recovery where available.
- Retain backups long enough to cover release rollback windows and incident response policy.
- Test restoring staging data into an isolated database before production launch.
- Include migration state in release records so database restores and application rollbacks remain compatible.

## Logging and Monitoring

- Forward Django structured logs to the staging log platform.
- Alert on repeated 5xx responses, failed readiness checks, migration failures, and unexpected AI provider errors.
- Do not log request authorization headers, provider keys, database passwords, or token values.

## Rollback

1. Stop new deployments.
2. Revert the application artifact to the previous known-good version.
3. Review whether the database migration is backward-compatible.
4. If data rollback is required, restore PostgreSQL from the validated backup path into an isolated database first.
5. Repoint staging only after the restored database passes health checks and smoke tests.

## Remaining Deployment Limits

- No Celery/Redis worker tier is required for the current synchronous workflow.
- No social OAuth or publishing credentials are required for the current sandbox integration mode.
- No RAG, billing, or background publishing infrastructure is part of this staging foundation.
