# Implementation Backlog

| Priority | Task | Files | Dependencies | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| P0 | Add full brand profile fields to UI | onboarding/profile pages | Business model extension | All brand fields editable. |
| P0 | Monitor Railway staging usage | Railway dashboard | Active Railway staging services | Usage remains within the intended staging budget and no paid plan upgrade is selected without approval. |
| P0 | Configure GitHub staging deployment secrets | GitHub repository settings | Railway token, service IDs, Vercel deploy hook, staging URLs | Manual `deploy-staging.yml` can run from `main` without embedding secrets in YAML. |
| P0 | Create Railway-compatible rollback tag | Git tags and Railway deployment history | Merged Railway staging configuration | A tag after the Railway deployment files can be redeployed safely and verified without reversing migrations. |
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
- Staging deployment is live with Vercel, Railway Django, and Railway PostgreSQL. Health checks, authentication, real Groq seven-day generation, draft conversion, duplicate prevention, backup, and isolated restore passed. Render PostgreSQL was created earlier and is preserved but unused.
