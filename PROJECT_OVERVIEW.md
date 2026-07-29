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
- AI: provider-neutral service layer with Groq as the only active concrete provider.
- Social integrations: provider model with sandbox provider; real OAuth credentials are environment-driven future work.

## Main Features

- Business workspace onboarding.
- Team roles and invitations.
- Sandbox social account connection and sync.
- Analytics summary.
- AI content studio with generation history.
- Structured seven-day AI content plan generation with explicit draft conversion.
- Content drafts, versioning, review workflow, and scheduling.
- Competitor comparison.
- Reports and in-app notifications.

## Operations

- Development SQLite: `USE_SQLITE=true .venv/bin/python manage.py migrate`.
- Development PostgreSQL: start the Compose `postgres` service, set `USE_SQLITE=false`, and run migrations/tests with `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_CONN_MAX_AGE`, and `DATABASE_SSLMODE`.
- Health checks: `GET /api/health/live/` confirms the process is running; `GET /api/health/ready/` verifies database connectivity and never calls Groq.
- Production settings live in `config.settings.production` and require explicit hosts, secret key, restricted CORS/CSRF origins, HTTPS cookie/security settings, static root, structured logging, and PostgreSQL SSL configuration.
- CI runs backend checks/tests/static analysis against PostgreSQL and frontend lint/type/test/build without a real Groq key.
- Active staging: Vercel for the Next.js frontend, Railway for the Django backend, and Railway PostgreSQL. Current URLs are `https://ai-business-growth-platform-staging.vercel.app` and `https://ai-business-growth-backend-staging-production.up.railway.app`. Verified staging tag: `v0.2.0-staging`. The Render PostgreSQL resource remains preserved but unused because Render private-repository access remained blocked.
