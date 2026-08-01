# Feature Status

| Feature | Status | Notes |
| --- | --- | --- |
| Authentication | Complete | Simple JWT backend, httpOnly cookie via Next.js route handlers. |
| Business workspace | Partial | Core profile exists; advanced brand fields need UI expansion. |
| Team permissions | Complete MVP | Business roles, invitations, role enforcement tests. |
| Social integrations | Sandbox | Sandbox provider stores accounts/posts/metrics; real OAuth deferred. |
| Social sync | Sandbox | Synchronous mock sync endpoint; Celery deferred. |
| Analytics dashboard | Complete MVP | Summary metrics and platform breakdown from stored snapshots. |
| AI content studio | Complete MVP | Groq-only provider, generation history and versioning. |
| Seven-day AI content plan | Complete MVP | Structured output, quota checks, history/usage storage, explicit draft creation, and async queue/status support. |
| Celery/Redis async AI jobs | Staging active | Django Celery app, Redis settings, queued generation status, idempotency, safe retries, polling API, frontend opt-in UX, and local Redis docs are implemented. Railway staging has a private Redis service and private Celery worker; the Vercel async UI is enabled, browser-verified, and now used for both content-plan and report workflows. |
| PostgreSQL readiness | Complete MVP | SQLite fallback preserved; PostgreSQL settings, driver, migrations, indexes, health endpoints, and CI service configured. |
| Health endpoints | Complete MVP | Liveness and database readiness endpoints exist under `/api/health/`. |
| Staging deployment rehearsal | Complete MVP | Vercel frontend, Railway Django backend, Railway PostgreSQL, private Redis, and private Celery worker are live. Health, auth, async real Groq generation, status polling, draft conversion, duplicate prevention, backup, isolated restore, rollback, and latest-main recovery were verified. GitHub Actions staging verification is live; provider-native Vercel/Railway autodeploy remains deferred. Render PostgreSQL is preserved but unused. |
| Content calendar | Complete MVP | List/calendar workflow, draft/review/approve/schedule. |
| Competitor comparison | Complete MVP | Backend comparison endpoint with evidence-style fields. |
| Trend discovery | Existing | Existing trends/analyze flow preserved. |
| Reports | Complete MVP + async foundation | Executive report generated from analytics summary. Asynchronous business-performance reports now have durable PostgreSQL jobs, status polling, idempotency, deterministic metrics, optional mocked AI recommendations, JSON/CSV exports, frontend support, and verified staging activation behind `ASYNC_REPORTS_ENABLED` / `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED`. |
| Notifications | Complete MVP | In-app notifications for workflow/report events. |
| Billing | Backlog | Phase 2. |
| Knowledge base | Backlog | Phase 3. |
| Social inbox | Backlog | Phase 3. |

## Integrations

- AI provider: Groq only. The model defaults to `openai/gpt-oss-20b` through Groq.
- Social provider: `sandbox`

No sandbox output is presented as a real provider integration.

## Deployment Notes

- Use PostgreSQL for shared development/staging/production. SQLite is only a local fallback.
- Production settings require real deployment environment values for secret key, allowed hosts, CORS/CSRF origins, database connection values, and HTTPS/security headers.
- Staging uses platform-managed secrets only. Do not commit Railway, Render, Vercel, database, Django, JWT, or Groq secrets.
- Railway staging is usage-metered; monitor usage and configure budget alerts or hard limits where the workspace plan supports them. Redis and one Celery worker were added only after explicit approval; async reports reuse those services and do not require another worker or Redis instance. Do not add more metered services without approval.
- Database backups should cover PostgreSQL data, migration history, and any future media/static upload storage. Local SQLite files are not a production backup target.
