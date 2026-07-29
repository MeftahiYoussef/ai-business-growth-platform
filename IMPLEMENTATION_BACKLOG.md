# Implementation Backlog

| Priority | Task | Files | Dependencies | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| P0 | Add full brand profile fields to UI | onboarding/profile pages | Business model extension | All brand fields editable. |
| P0 | Production deployment rehearsal | Django/hosting config | PostgreSQL instance, deployment domain, secret manager | `check --deploy`, migrations, static files, health checks, and rollback plan validated in staging. |
| P1 | Real OAuth providers | `apps/integrations/providers` | Platform credentials | OAuth connect/revoke/refresh for Instagram/Facebook/LinkedIn. |
| P1 | Celery/Redis jobs | Django backend | Redis | Sync/publishing/report jobs run async with retry logs. |
| P1 | Scheduled publication | `apps/content_planner` | Provider APIs | Approved scheduled posts publish or fail with retry. |
| P1 | Campaign analytics | analytics/reports | Campaign metrics | Campaign report has actual-vs-target metrics. |
| P2 | Billing and subscriptions | new billing app | Stripe or provider | Server-side feature limits enforced. |
| P2 | Knowledge base | new knowledge app | pgvector/storage | Business-isolated document chunks searchable. |
| P3 | Social inbox | new inbox app | Provider API support | Comments/mentions sync and resolution workflow. |

## Completed Infrastructure

- Real Groq smoke test and seven-day content-plan workflow passed with `openai/gpt-oss-20b`.
- PostgreSQL development configuration, Compose service, CI service, health endpoints, connection persistence, SSL mode support, and database-level duplicate draft protection are implemented.
- Remaining deployment limitation: production has not been exercised against the final hosting platform, managed PostgreSQL backup policy, or secret manager.
