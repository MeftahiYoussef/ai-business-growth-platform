# MVP Readiness Audit

Date: 2026-10-01

Scope: product readiness for the AI Business Growth & Trend Intelligence Platform. AI research is paused for this phase. Production AI remains Groq. The deterministic evidence-grounding contract is available as backend infrastructure but is not wired into current Groq responses.

## MVP Journey

1. Register or log in.
2. Create or select a business.
3. Configure business context.
4. Open AI Studio.
5. Generate a weekly content plan.
6. Queue and complete the Celery job when async content plans are enabled.
7. Validate that Groq returns exactly seven reviewed items.
8. Review plan items.
9. Convert selected items into drafts.
10. Edit drafts and workflow state.
11. View drafts in the calendar-oriented list.
12. Generate an async business report.
13. Receive one completion notification.
14. Export the report as JSON or CSV.
15. Log out and log back in.
16. Confirm persisted business, generations, drafts, reports, and notifications.

## Acceptance Criteria

| Step | Acceptance criteria | Current result |
| --- | --- | --- |
| Register/login | User can register, log in, receive a server-managed httpOnly token cookie, access protected pages, and log out. | READY locally by code path; staging E2E blocked by Railway state. |
| Business setup | User can create a business with name, industry, country, product/service, audience, brand voice, goals, and competitors. | READY after adding brand-voice onboarding input; preferred platforms and posting frequency remain future profile fields. |
| AI Studio | User can submit a seven-day content-plan request and see queue/running/completed/failed state. | READY by backend/frontend code; needs staging E2E once infrastructure is healthy. |
| Seven-day plan | Generated plan must pass the production content-plan validator: days 1-7, valid platforms/content types/objectives, review required. | READY by backend validation. |
| Draft conversion | Selected days create drafts once; duplicate conversion is prevented by source generation/day uniqueness. | READY by backend constraint and service checks. |
| Draft editing/workflow | User can create, update, request review, approve, and schedule drafts; publishing remains unimplemented. | PARTIAL for MVP: API exists, UI provides create/workflow actions; richer edit UI is still needed. |
| Calendar | User can see draft title, platform, status, and schedule state. | PARTIAL: list view works; true calendar layout is post-MVP. |
| Reports | Async business reports queue, poll, complete, create history, notify once, and export JSON/CSV. | READY by backend/frontend code; staging E2E blocked. |
| Notifications | Report/workflow notifications are stored and readable. | READY by code; needs staging E2E. |
| Competitors | User can create competitor records and compare stored values. | PARTIAL: records exist; comparison still contains placeholder qualitative fields. |
| Trends | Existing trend records and pages exist. | NOT_REQUIRED_FOR_MVP: advanced trend engine is post-MVP. |
| Error UX | Provider, validation, auth, job failure, and report failure paths return safe messages. | PARTIAL: core safe messages exist; browser sweep still required. |
| Quotas | AI generation quotas exist by user/day and business/month. | READY by code; idempotent duplicate requests avoid extra queued jobs. |
| Security config | Production settings force DEBUG=false, secure cookies, allowed hosts, CORS/CSRF, HTTPS headers. | READY by code; environment values must be verified during deployment recovery. |
| Observability | Health endpoints, structured logs, job status fields, and Redis/database readiness exist. | PARTIAL: enough for MVP operations; no external monitoring provider configured. |

## Feature Inventory

| Area | Status | Evidence |
| --- | --- | --- |
| Authentication | READY | JWT auth in Django, Next.js route handlers/cookie proxy, protected dashboard layout, logout route. |
| Business profiles | READY | `Business` model and serializer include core fields plus brand voice; onboarding now captures brand voice. |
| AI Studio | READY | Studio page uses Groq-backed generate and weekly content-plan APIs. |
| Content-plan generation | READY | `validate_content_plan`, provider structured JSON, quota checks, async queue/status endpoints, idempotency key support. |
| Drafts | PARTIAL | Draft CRUD/workflow APIs exist; calendar UI can create and move workflow state; full edit surface is thin. |
| Calendar | PARTIAL | Schedule-oriented list exists with status/scheduled date; full calendar grid is not required for MVP. |
| Reports | READY | Durable report jobs, deterministic metrics, optional AI recommendations, report history, notification, JSON/CSV export. |
| Exports | READY | Report JSON and CSV export endpoints exist. |
| Notifications | READY | Notification model/views and report/workflow notifications exist. |
| Competitors | PARTIAL | Competitor CRUD and stored metrics exist; generated competitor posts/comparison are not real scraping. |
| Trend engine | NOT_REQUIRED_FOR_MVP | Trend model/page exist; advanced EMA/momentum/slope/forecast engine is not implemented and should not block MVP. |
| Settings/profile | PARTIAL | Profile displays business context and logout; editing existing business profile should be improved. |
| Onboarding | READY | Concise create-business flow covers minimum useful context except preferred platforms/posting frequency, which are post-MVP profile enhancements. |
| Quotas | READY | Content-plan service enforces user and business quotas before provider execution. |
| Celery jobs | READY | Content plan and report Celery tasks support retrying, failed/completed states, and stale running handling. |
| Error UX | PARTIAL | API wraps provider/config/validation failures safely; full browser failure-path sweep remains. |

## Infrastructure Status

Railway read-only inspection on 2026-10-01 showed:

- Project: `ai-growth-staging`
- Backend web: failed
- Celery worker: failed
- Postgres: offline
- Redis: offline
- Postgres volume: ready but detached, 107 MB / 500 MB

No Railway deploy, restart, redeploy, creation, deletion, credential rotation, or paid action was performed. Because the Postgres volume is detached in read-only status, staging recovery must be handled as a separate safe infrastructure recovery task before staging E2E can be trusted.

## Launch Blockers

### P0

- Staging infrastructure is unhealthy and cannot prove the MVP journey until existing Postgres, Redis, backend, and worker are safely recovered without replacing volumes.

### P1

- Browser E2E journey must be rerun after staging recovery: auth, onboarding, content plan, draft conversion/edit, calendar, report, notification, export, logout/login persistence.
- Draft editing UX is too thin for a polished MVP; the API exists, but users need a clearer edit-and-save path for title, caption, CTA, hashtags, platform, content type, and objective.
- Profile editing after onboarding should be added or clarified so business context can be corrected without recreating a business.

### P2

- Competitor comparison qualitative text is placeholder-like and should be labeled or replaced with deterministic stored metrics.
- Error UX needs a systematic browser sweep for Groq unavailable/rate limit, Celery unavailable, Redis unavailable, expired auth, and failed jobs.
- Preferred platforms and posting frequency are not first-class business profile fields.
- Observability is enough for MVP but lacks provider-level dashboards/alerts.

### P3

- True calendar grid layout.
- Advanced trend engine with EMA, slope, acceleration, lifecycle, strength, confidence, and forecasts.
- Real social OAuth, scheduled publishing, billing, knowledge base, and social inbox.

## AI Research Freeze

AI research is paused until the MVP user journey is operational. Current production AI remains Groq. Local research found that Qwen3-1.7B with constrained trusted evidence/relation selection is promising, but it is not deployed and should not block product readiness.

