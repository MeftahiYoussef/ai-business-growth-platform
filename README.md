# AI Business Growth & Trend Intelligence Platform

Production-oriented Next.js frontend with a Django REST Framework backend. The original Express/MongoDB backend is retained in `backend/` as rollback reference until the Django/PostgreSQL cutover is reviewed.

## Structure

```text
.
├── frontend/          # Next.js App Router frontend
├── django-backend/    # Django, DRF, Simple JWT, PostgreSQL API
├── backend/           # Legacy Express/MongoDB API kept for rollback
├── docs/archive/      # Historical migration notes
├── docker-compose.yml
└── package.json
```

## Requirements

- Node.js 20+
- npm
- Python 3.11+
- PostgreSQL 16+ or Docker Compose
- MongoDB only when running `migrate_from_mongodb`

## Django Setup

```bash
cd django-backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed
.venv/bin/python manage.py runserver 8000
```

For local PostgreSQL with Docker:

```bash
docker compose up -d postgres
```

API docs:

- `http://localhost:8000/api/docs/`
- `http://localhost:8000/api/redoc/`
- `http://localhost:8000/api/schema/`

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The frontend uses Next.js route handlers to store the backend JWT in an `httpOnly`, `SameSite=Lax` cookie. Browser requests go through `/api/backend/*`; the route handler attaches `Authorization: Bearer <token>` to Django.

## Tests And Checks

Django:

```bash
cd django-backend
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy .
.venv/bin/python manage.py check --deploy
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## MongoDB To PostgreSQL Migration

Dry run:

```bash
cd django-backend
.venv/bin/python manage.py migrate_from_mongodb --dry-run
```

Apply:

```bash
.venv/bin/python manage.py migrate_from_mongodb
```

Original MongoDB ObjectIds are stored in `legacy_mongo_id`; API responses continue to expose `_id` for frontend compatibility.

## Docker

```bash
docker compose up --build
```

This starts PostgreSQL, Django on `8000`, and Next.js on `3000`. MongoDB is available for migration with:

```bash
docker compose --profile migration up -d mongodb
```

## Security Notes

- Django uses Simple JWT access/refresh tokens and refresh-token blacklisting.
- Production settings require `DJANGO_SECRET_KEY`, restricted hosts, HTTPS, secure cookies, and restricted CORS/CSRF origins.
- No backend secrets are used by the frontend.
- The legacy Node backend should remain available until Django is verified against PostgreSQL and reviewed.

## v1.0.0 Release Scope

The current release target is a single-business MVP for staging/demo use:

- dashboard
- business profile
- Generate Ideas
- AI Studio seven-day content plans
- drafts
- calendar/list
- reports
- alerts
- JSON/CSV exports

The active staging stack is Vercel -> Render Free -> Django/Gunicorn -> Celery concurrency 1 -> Upstash Redis -> Neon PostgreSQL -> Groq. Render Free cold starts are an accepted demo limitation, not a production SLA.

See:

- `docs/V1_RELEASE_READINESS.md`
- `docs/DEPLOYMENT_RUNBOOK.md`
- `docs/OPERATIONS_AND_MONITORING.md`
- `docs/DATABASE_BACKUP_RESTORE.md`

Post-v1 work includes multi-business switching, advanced competitors, advanced Trend Engine, automatic publishing, billing, knowledge base/RAG, and production-grade hosting.
