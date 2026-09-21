# Project Overview

## Purpose

AI Business Growth & Trend Intelligence Platform is a SaaS workspace for social media planning, AI-assisted content creation, competitor intelligence, analytics, reporting, and team collaboration.

## Roles

- Owner
- Admin
- Manager
- Content creator
- Analyst
- Viewer

## Main Journeys

1. Register and create a business workspace.
2. Add brand, audience, products, competitors, and goals.
3. Connect a sandbox social account.
4. Analyze trends and competitor content.
5. Generate AI-assisted content.
6. Save drafts, request review, approve, and schedule.
7. View analytics, reports, notifications, and team activity.

## Architecture

- Frontend: Next.js App Router, TypeScript, server route handlers, httpOnly auth cookie.
- Backend: Django REST Framework, Simple JWT, Django ORM.
- Database target: PostgreSQL. Local verification can use SQLite with `USE_SQLITE=true`; PostgreSQL mode uses backend-only `DATABASE_*` variables and the `psycopg` driver.
- Async jobs: Celery with Redis broker/result backend for queued AI content-plan generation and the asynchronous business-report foundation. PostgreSQL remains the durable source of job state and results.
- AI: provider-neutral service layer with Groq as the only active concrete provider.
- Small LLM lab: source-only experimental foundation for `Qwen/Qwen3-1.7B` local evaluation, future LoRA, and future RAG. The corrected v2 evaluator now uses the production content-plan contract. It is not deployed and is not a Groq fallback.
- Social integrations: provider model with sandbox provider; real OAuth credentials are environment-driven future work.

## Main Features

- Business workspace onboarding.
- Team roles and invitations.
- Sandbox social account connection and sync.
- Analytics summary.
- AI content studio with generation history.
- Structured seven-day AI content plan generation with explicit draft conversion.
- Asynchronous seven-day plan queueing and status polling behind deployment flags.
- Content drafts, versioning, review workflow, and scheduling.
- Competitor comparison.
- Reports and in-app notifications.
- Asynchronous business performance report generation behind disabled activation flags.

## Operations

- Development SQLite: `USE_SQLITE=true .venv/bin/python manage.py migrate`.
- Development PostgreSQL: start the Compose `postgres` service, set `USE_SQLITE=false`, and run migrations/tests with `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_CONN_MAX_AGE`, and `DATABASE_SSLMODE`.
- Health checks: `GET /api/health/live/` confirms the process is running; `GET /api/health/ready/` verifies database connectivity and never calls Groq.
- Production settings live in `config.settings.production` and require explicit hosts, secret key, restricted CORS/CSRF origins, HTTPS cookie/security settings, static root, structured logging, and PostgreSQL SSL configuration.
- CI runs backend checks/tests/static analysis against PostgreSQL and frontend lint/type/test/build without a real Groq key.
- Local async development starts Compose `postgres` and `redis`, then runs a Celery worker with `celery -A config worker --loglevel=INFO --concurrency=1`. Tests use Celery eager mode unless a live Redis worker is being verified.
- Async reports are documented in `docs/ASYNC_REPORTS.md`. They reuse the existing Redis and worker architecture, keep computed metrics separate from optional AI recommendations, and remain disabled in staging until explicitly activated with backend and frontend flags.
- Small LLM experiments are documented in `docs/SMALL_LLM.md` and `docs/SMALL_LLM_BASELINE_V2.md`. The model lab includes a corrected 50-case synthetic golden dataset, deterministic metrics, a dataset builder, a LoRA config example, and a future RAG contract. The corrected Qwen pilot is not yet strong enough to justify LoRA, and the Groq comparison needs a clean retry after provider rate limiting clears. No fine-tuning, embeddings, pgvector migrations, or staging activation are included.
- Staging deployment is provider-native: Vercel and Railway should autodeploy from GitHub `main` after CI, while `.github/workflows/deploy-staging.yml` validates selected refs and verifies live staging health. The verification workflow is live; Railway and Vercel still require one-time account-owner GitHub connection steps before automatic provider deployments can be claimed.
- Active staging: Vercel for the Next.js frontend, Railway for the Django backend, Railway PostgreSQL, private Railway Redis, and one private Celery worker. Current URLs are `https://ai-business-growth-platform-staging.vercel.app` and `https://ai-business-growth-backend-staging-production.up.railway.app`. Backend async queueing and the Vercel async polling UI are enabled and browser-verified in staging; the synchronous endpoint remains available for rollback. The Render PostgreSQL resource remains preserved but unused because Render private-repository access remained blocked.
- Verified staging rollout IDs on 2026-08-01: Railway web `8221c1fa-e51d-4a27-92fe-2d827d692d5b`, Railway worker `0d025af3-34d5-4ce7-9a32-793dd5f8bc84`, and Vercel production `dpl_Cpe23nsoF5KSPqCmk14D3Fq7A6SL`.
