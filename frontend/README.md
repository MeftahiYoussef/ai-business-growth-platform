# AI Business Growth & Trend Intelligence Platform - Next.js Frontend

Next.js App Router frontend for the AI Business Growth & Trend Intelligence Platform.

## Requirements

- Node.js 20+
- Django backend running on `http://localhost:8000`

## Environment

Create `.env.local`:

```bash
cp .env.example .env.local
```

Default:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=false
NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=false
```

Set `NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=true` only when the Django backend has Redis and a Celery worker available. This switches the seven-day content-plan UI to queue the request, poll the backend status endpoint, and render the completed plan when the worker finishes. Redis, Celery, database, Django, and Groq secrets must never use `NEXT_PUBLIC_` variables.

Set `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=true` only after the Django backend has `ASYNC_REPORTS_ENABLED=true`, Redis, and a Celery worker available. This switches the reports page to queue business-performance reports, poll report-job status, recover an active job after refresh, and render computed metrics separately from AI recommendations. Leave it false in staging until the report feature is explicitly activated.

## Run

Django backend:

```bash
cd ../django-backend
.venv/bin/python manage.py runserver 8000
```

Next.js frontend:

```bash
cd frontend
npm install
npm run dev
```

## Build And Test

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## Authentication Architecture

The browser does not store the JWT in local storage. Login and registration call Next.js route handlers under `/api/auth/*`; those handlers call Django and store the returned JWT in an `httpOnly`, `SameSite=Lax` cookie.

Client-side data requests go through `/api/backend/*`, which attaches the cookie token to Django as `Authorization: Bearer <token>`.

The backend proxy forwards Django API paths with a trailing slash. This avoids POST redirect failures when hosted platforms normalize browser-facing route slashes before the Next.js route handler runs.

## Project Structure

- `app/(auth)` public login, register, forgot-password routes
- `app/(dashboard)` protected dashboard routes
- `app/api/auth` auth cookie route handlers
- `app/api/backend/[...path]` backend proxy
- `components` reusable UI/layout/forms/feedback components
- `features` typed API modules
- `lib` API, auth, constants, utility code
- `types` backend response models

## Application Routes

| Feature | Next.js route |
| --- | --- |
| Login | `/login` |
| Register | `/register` |
| Business onboarding | `/onboarding` |
| Dashboard | `/dashboard` |
| Competitors | `/competitors` |
| Competitor detail | `/competitors/[id]` |
| Trends | `/trends` |
| Content generator | `/generate` |
| Strategy | `/strategy` |
| Business analysis | `/analysis` |
| Reports | `/reports` |
| Profile and settings | `/profile` |

## Deployment

Set `NEXT_PUBLIC_API_URL` to the deployed Django backend origin. Use HTTPS in production so the auth cookie can use `Secure`.

The staging frontend has `NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=true` enabled only on the existing Vercel staging project. Browser smoke testing verified authentication, queue submission, status polling, refresh recovery, seven-item rendering, duplicate-submit protection, draft conversion, duplicate draft prevention, safe failure presentation, logout, and protected-route behavior.

Immediate staging rollback is frontend-only: set `NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN=false` in the existing Vercel staging project and redeploy. Keep the synchronous Django endpoint available and do not delete Redis, the worker, or generation history during rollback.

Async report rollback is also frontend-first while the feature remains behind flags: set `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=false` and keep the backend queue endpoints, worker, Redis, and historical reports intact.
