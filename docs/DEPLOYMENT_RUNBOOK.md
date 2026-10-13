# Deployment Runbook

Date: 2026-10-13

## Current Staging Topology

- Frontend: Vercel
- Backend: Render Free Web Service
- Database: Neon PostgreSQL
- Queue: Upstash Redis
- AI: Groq
- Worker: Celery concurrency 1 inside the Render web service for free staging/demo only

This is not a production SLA topology. Render Free can sleep after inactivity.

## Deploy Order

1. Merge only after CI is green.
2. Confirm backend environment variable names are configured in Render.
3. Deploy Render backend from the verified main commit.
4. Render build command installs Python dependencies and collects static files.
5. Render start command runs `bin/render_free_staging_start.sh`.
6. Startup runs Django migrations, starts Celery when `START_CELERY_IN_WEB=true`, then runs Gunicorn.
7. Verify backend health.
8. Confirm Vercel frontend points to the Render backend URL.
9. Deploy or refresh Vercel if frontend changes were merged.
10. Run clean-browser smoke.

## Backend Verification

Required:

```text
GET /api/health/live/  -> 200
GET /api/health/ready/ -> 200 with database=ok and redis=ok
GET /api/docs/         -> 200
```

Render logs should show:

- Gunicorn started and bound to `$PORT`
- Celery worker started
- worker concurrency = 1
- expected task modules registered
- Redis connection successful

Do not print or copy secret values into issue comments or release notes.

## Frontend Verification

Required:

- `/login` loads
- register/login works
- authenticated shell loads
- backend-bound requests use the Next.js proxy
- no Railway or localhost backend URLs appear in staging network requests

## Clean-Browser Smoke

Use a fresh browser session:

REGISTER/LOGIN -> PROFILE -> GENERATE IDEAS -> SAVE -> AI STUDIO -> 7-DAY PLAN -> DRAFTS -> EDIT -> CALENDAR -> REPORT -> NOTIFICATION -> JSON/CSV EXPORT -> LOGOUT -> LOGIN -> PERSISTENCE.

Do not replace this with curl-only checks.

## Rollback

If a bad deploy reaches staging:

1. Stop new user testing.
2. Identify the last verified commit. Current rollback baseline is `v0.9.0-mvp-hardened`.
3. Revert or redeploy the previous verified Vercel deployment.
4. Redeploy Render to the previous verified backend commit.
5. Do not roll back database schema unless a migration is confirmed incompatible.
6. If schema rollback is required, take a logical backup first and follow `DATABASE_BACKUP_RESTORE.md`.
7. Verify health endpoints and the clean-browser smoke.

Never delete Neon data or reset the database as a rollback shortcut.

## Release Tagging

Create `v1.0.0` only after:

- release PR merged
- final main CI green
- main deployed to Render/Vercel
- deployed commit verified
- clean-browser journey passed
- P0 = 0
- P1 = 0
