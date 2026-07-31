# Implementation Backlog

| Priority | Task | Files | Dependencies | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| P0 | Add full brand profile fields to UI | onboarding/profile pages | Business model extension | All brand fields editable. |
| P0 | Monitor Railway staging usage | Railway dashboard | Active Railway staging services | Usage remains within the intended staging budget and no paid plan upgrade is selected without approval. |
| P0 | Complete provider-native Git autodeploy evidence | Railway/Vercel dashboards | Deferred provider Git connection verification | Prove Vercel and Railway deploy the exact `main` merge commit after CI without using provider deployment tokens. |
| P1 | Real OAuth providers | `apps/integrations/providers` | Platform credentials | OAuth connect/revoke/refresh for Instagram/Facebook/LinkedIn. |
| P1 | Async jobs beyond AI content plans | Django backend | Celery/Redis staging worker | Social sync, publishing, and reports run async with retry logs. |
| P1 | Scheduled publication | `apps/content_planner` | Provider APIs | Approved scheduled posts publish or fail with retry. |
| P1 | Campaign analytics | analytics/reports | Campaign metrics | Campaign report has actual-vs-target metrics. |
| P2 | Billing and subscriptions | new billing app | Stripe or provider | Server-side feature limits enforced. |
| P2 | Knowledge base | new knowledge app | pgvector/storage | Business-isolated document chunks searchable. |
| P3 | Social inbox | new inbox app | Provider API support | Comments/mentions sync and resolution workflow. |

## Completed Infrastructure

- Real Groq smoke test and seven-day content-plan workflow passed with `openai/gpt-oss-20b`.
- PostgreSQL development configuration, Compose service, CI service, health endpoints, connection persistence, SSL mode support, and database-level duplicate draft protection are implemented.
- Staging deployment is live with Vercel, Railway Django, and Railway PostgreSQL. Health checks, authentication, real Groq seven-day generation, draft conversion, duplicate prevention, backup, isolated restore, rollback to `v0.2.0-staging`, and latest-main restoration passed. Render PostgreSQL was created earlier and is preserved but unused.
- Celery/Redis staging services are active after explicit approval: private Railway Redis service `Redis`, private worker `ai-business-growth-celery-worker-staging`, backend Redis readiness, and browser-level async Groq smoke through Vercel queue/polling passed. The synchronous endpoint remains available for rollback.
