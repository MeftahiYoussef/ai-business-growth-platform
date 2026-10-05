# Fresh Free Staging

Date: 2026-10-01

This is the permanent Track B staging plan. Railway is no longer an active staging host. The old Railway project and volumes remain archive/recovery-only, and historical data is not imported into the fresh staging environment.

## Target Architecture

| Layer | Provider | Tier | Notes |
| --- | --- | --- | --- |
| Frontend | Existing Vercel staging project | Free/Hobby-compatible | Keep the existing project and update only the API URL. |
| Backend | Render Web Service | Free | One web service runs Django/Gunicorn and Celery for staging only. |
| Database | Neon PostgreSQL | Free | Fresh staging database. No Railway import. SSL required. |
| Queue | Upstash Redis | Free | Server-side Redis URL only. No browser exposure. |
| AI | Groq | Existing | Existing provider behavior remains unchanged. |

## Railway Boundary

Railway is archive/recovery-only:

- Do not deploy, redeploy, restart, or mutate Railway services.
- Do not delete `postgres-volume`.
- Do not touch `postgres-volume-B_c5`.
- Do not import old Railway data into this fresh staging track.

## Backend Configuration

The Django backend now supports `DATABASE_URL` for managed PostgreSQL services such as Neon. Deployed staging must set:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `USE_SQLITE=false`
- `DATABASE_URL` from Neon, with SSL enabled by the provider URL or `DATABASE_SSLMODE=require`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `GROQ_API_KEY`
- `AI_PROVIDER=groq`
- `AI_ASYNC_CONTENT_PLAN_ENABLED=true`
- `ASYNC_REPORTS_ENABLED=true`
- `REPORT_AI_RECOMMENDATIONS_ENABLED=true`
- `START_CELERY_IN_WEB=true`
- `CELERY_WORKER_CONCURRENCY=1`

Do not commit any real secret or connection string.

## Render Free Web Service

Render should deploy the backend using `render.yaml`.

The staging start script is:

```sh
sh bin/render_free_staging_start.sh
```

It runs:

1. `collectstatic`
2. `migrate`
3. Celery worker with concurrency `1`
4. Gunicorn bound to Render's `PORT`

This topology is staging-only. It avoids a paid Render background worker but has free-tier limitations.

## Free-Tier Limitations

Render Free services may sleep after inactivity. Cold starts are expected and acceptable for staging/demo use. After a cold start, both Gunicorn and the child Celery worker must start before async content-plan/report flows are considered healthy.

This is not the final production SLA topology.

## Vercel Configuration

Keep the existing Vercel staging project. After the Render backend is healthy:

- Set `NEXT_PUBLIC_API_URL` to the Render backend base URL.
- Set `NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=true`.
- Set `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=true`.

No backend, Redis, database, or Groq secrets belong in Vercel public variables.

## Fresh Database Flow

This Track B staging database is intentionally fresh:

1. Create one Neon Free PostgreSQL project.
2. Configure `DATABASE_URL` in Render only.
3. Run Django migrations.
4. Create minimal staging data via normal app flows.
5. Verify `django_migrations` and expected tables.

Do not wait for Railway data recovery and do not import Railway records.

## MVP Acceptance

Fresh staging is MVP-ready only when this path works end to end:

`auth -> business profile -> async Groq content plan -> Celery -> seven validated items -> draft conversion -> draft edit -> calendar/list -> async report -> notification -> JSON/CSV export -> logout/login persistence`
