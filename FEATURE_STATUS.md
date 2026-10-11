# Feature Status

| Feature | Status | Notes |
| --- | --- | --- |
| Authentication | Complete | Simple JWT backend, httpOnly cookie via Next.js route handlers. |
| Business workspace | Complete MVP | Core profile and focused edit flow cover business name, industry, market, product/service, target audience, brand voice, objectives, preferred platforms, posting frequency, and competitors. |
| Team permissions | Complete MVP | Business roles, invitations, role enforcement tests. |
| Social integrations | Sandbox | Sandbox provider stores accounts/posts/metrics; real OAuth deferred. |
| Social sync | Sandbox | Synchronous mock sync endpoint; Celery deferred. |
| Analytics dashboard | Complete MVP | Summary metrics and platform breakdown from stored snapshots. |
| AI content studio | Complete MVP | Groq-only provider, generation history and versioning. |
| Seven-day AI content plan | Complete MVP | Structured output, quota checks, history/usage storage, explicit draft creation, and async queue/status support. |
| Celery/Redis async AI jobs | Staging active | Django Celery app, Redis settings, queued generation status, idempotency, safe retries, polling API, frontend opt-in UX, and local Redis docs are implemented. Track B staging uses Upstash Redis with Celery concurrency 1 inside the Render Free web service. The deployed browser core flow is verified for content-plan and report workflows. |
| PostgreSQL readiness | Complete MVP | SQLite fallback preserved; PostgreSQL settings, driver, migrations, indexes, health endpoints, and CI service configured. |
| Health endpoints | Complete MVP | Liveness and database readiness endpoints exist under `/api/health/`. |
| Staging deployment rehearsal | Complete MVP demo | Railway is no longer the active staging host. The zero-cost staging stack is existing Vercel frontend, Render Free backend, Neon Free PostgreSQL, Upstash Free Redis, and Groq. Core MVP browser flow is verified; whole-app route completion remains 43.5%. |
| Content calendar | Complete MVP | List/calendar workflow, draft edit, review, approve, and schedule. |
| Competitor comparison | Post-MVP from primary nav | Backend comparison endpoint with evidence-style fields exists, but advanced competitor workflow is not part of the MVP demo and is removed from primary navigation. |
| Trend discovery | Post-MVP from primary nav | Existing trends/analyze flow is preserved, but Trend Engine work is out of scope for the MVP demo and is removed from primary navigation. |
| Reports | Complete MVP + async foundation | Executive report generated from analytics summary. Asynchronous business-performance reports now have durable PostgreSQL jobs, status polling, idempotency, deterministic metrics, optional mocked AI recommendations, JSON/CSV exports, frontend support, and verified staging activation behind `ASYNC_REPORTS_ENABLED` / `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED`. |
| Notifications | Complete MVP | In-app notifications for workflow/report events. |
| Evidence grounding contract | Complete foundation | Production-owned deterministic evidence/relation grounding contract exists under Django backend code. It is model-agnostic infrastructure only and does not change current APIs or Groq behavior. |
| Small LLM model lab | Paused research | AI research is paused while MVP readiness is prioritized. `Qwen/Qwen3-1.7B` with constrained trusted evidence/relation selection is promising locally but not deployed. LoRA v1/v2/v2.1 and Qwen3-4B are not promoted. Groq remains the live production provider. RAG has not started. |
| Billing | Backlog | Phase 2. |
| Knowledge base | Backlog | Phase 3. |
| Social inbox | Backlog | Phase 3. |

## Integrations

- AI provider: Groq only. The model defaults to `openai/gpt-oss-20b` through Groq.
- Experimental local model: `Qwen/Qwen3-1.7B` for local evaluation only. `Qwen/Qwen3-4B` was capacity-checked and rejected before pilot.
- Local model and RAG work are paused until the MVP journey is operational.
- Social provider: `sandbox`

No sandbox output is presented as a real provider integration.

## Deployment Notes

- Use PostgreSQL for shared development/staging/production. SQLite is only a local fallback.
- Production settings require real deployment environment values for secret key, allowed hosts, CORS/CSRF origins, database connection values, and HTTPS/security headers.
- Staging uses platform-managed secrets only. Do not commit Render, Neon, Upstash, Vercel, database, Django, JWT, or Groq secrets. Railway is archive/recovery-only and should not receive new deployment mutations.
- Render Free may sleep after inactivity. This is acceptable for staging/demo, but true idle-sleep wake should continue to be monitored under demo conditions.
- Database backups should cover PostgreSQL data, migration history, and any future media/static upload storage. Local SQLite files are not a production backup target.
