# MVP Readiness Audit

Date: 2026-10-13

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
| Register/login | User can register, log in, receive a server-managed httpOnly token cookie, access protected pages, and log out. | READY in deployed browser after auth hydration fix. |
| Business setup | User can create and edit a business with name, industry, country/market, product/service, audience, brand voice, goals, preferred platforms, posting frequency, and competitors. | READY in deployed browser. |
| AI Studio | User can submit a seven-day content-plan request and see queue/running/completed/failed state. | READY in deployed browser after durable submitting-to-queued transition fix. |
| Seven-day plan | Generated plan must pass the production content-plan validator: days 1-7, valid platforms/content types/objectives, review required. | READY by backend validation. |
| Draft conversion | Selected days create drafts once; duplicate conversion is prevented by source generation/day uniqueness. | READY by backend constraint and service checks. |
| Draft editing/workflow | User can create, update, request review, approve, and schedule drafts; publishing remains unimplemented. | READY in deployed browser after focused draft editor verification. |
| Calendar | User can see draft title, platform, status, and schedule state. | READY: list view is the intended MVP calendar surface; true grid layout is post-MVP. |
| Reports | Async business reports queue, poll, complete, create history, notify once, and export JSON/CSV. | READY in deployed browser. |
| Notifications | Report/workflow notifications are stored and readable. | READY in deployed browser for report completion. |
| Competitors | User can create competitor records and compare stored values. | NOT_REQUIRED_FOR_MVP: route remains available but is removed from primary navigation for the MVP demo. |
| Trends | Existing trend records and pages exist. | NOT_REQUIRED_FOR_MVP: advanced trend engine is post-MVP. |
| Error UX | Provider, validation, auth, job failure, and report failure paths return safe messages. | READY for current MVP: representative browser errors are safe; exhaustive provider-failure drills remain P2. |
| Quotas | AI generation quotas exist by user/day and business/month; Generate Ideas has a business/day item cap. | READY by code; idempotent duplicate requests avoid extra queued jobs, and Generate Ideas now has app-level cost protection before unbounded provider usage. |
| Security config | Production settings force DEBUG=false, secure cookies, allowed hosts, CORS/CSRF, HTTPS headers. | READY by code; environment values must be verified during deployment recovery. |
| Observability | Health endpoints, structured logs, job status fields, and Redis/database readiness exist. | READY for demo: health/readiness/job states and Render logs cover MVP operations; v1 operations doc added; paid monitoring is post-MVP. |

## Feature Inventory

| Area | Status | Evidence |
| --- | --- | --- |
| Authentication | READY | JWT auth in Django, Next.js route handlers/cookie proxy, protected dashboard layout, logout route. |
| Business profiles | READY | `Business` model and serializer include core fields plus brand voice; onboarding now captures brand voice. |
| AI Studio | READY | Studio page uses Groq-backed generate and weekly content-plan APIs. |
| Content-plan generation | READY | `validate_content_plan`, provider structured JSON, quota checks, async queue/status endpoints, idempotency key support. |
| Drafts | READY | Draft CRUD/workflow APIs exist; focused editor supports title, caption, CTA, hashtags, platform, content type, and objective. |
| Calendar | READY | Schedule-oriented list exists with status/scheduled date; full calendar grid is not required for MVP. |
| Reports | READY | Durable report jobs, deterministic metrics, optional AI recommendations, report history, notification, JSON/CSV export. |
| Exports | READY | Report JSON and CSV export endpoints exist. |
| Notifications | READY | Notification model/views and report/workflow notifications exist. |
| Competitors | PARTIAL | Competitor CRUD and stored metrics exist; generated competitor posts/comparison are not real scraping. |
| Trend engine | NOT_REQUIRED_FOR_MVP | Trend model/page exist; advanced EMA/momentum/slope/forecast engine is not implemented and should not block MVP. |
| Settings/profile | READY | Profile displays and edits business context through the existing business API. |
| Onboarding | READY | Concise create-business flow covers minimum useful context, including preferred platforms and posting frequency. |
| Quotas | READY | Content-plan service enforces user and business quotas before provider execution. |
| Celery jobs | READY | Content plan and report Celery tasks support retrying, failed/completed states, and stale running handling. |
| Error UX | READY | API wraps provider/config/validation failures safely for current MVP actions; exhaustive negative testing remains P2. |

## Infrastructure Status

Track B replaces Railway for active staging:

- Frontend: existing Vercel staging project
- Backend: Render Free Web Service
- Database: Neon Free PostgreSQL
- Queue: Upstash Free Redis
- AI: existing Groq provider

Railway is archive/recovery-only. No Railway mutation is required for MVP readiness. The Track B staging stack is active for the MVP demo. Render Free may sleep after inactivity; true idle-sleep wake should continue to be monitored under real demo conditions.

## Launch Blockers

### P0

- None known for the verified core MVP journey.

### P1

- None known for the verified core MVP journey.

### P2

- Exhaustive provider-failure UX drills for Groq unavailable/rate limit, Celery unavailable, Redis unavailable, expired auth, and failed jobs.
- Observability is enough for MVP but lacks provider-level dashboards/alerts.
- Render Free true idle-sleep wake still needs continued monitoring under real demo conditions.

### P3

- True calendar grid layout.
- Non-core partial routes remain available by URL but are removed from primary navigation for the MVP demo.
- Field-by-field Unicode and boundary sweeps remain for profile and draft editor.
- Backup restore procedure is documented but restore testing remains P1 before v1.0.0 tagging.
- Advanced trend engine with EMA, slope, acceleration, lifecycle, strength, confidence, and forecasts.
- Real social OAuth, scheduled publishing, billing, knowledge base, and social inbox.

## AI Research Freeze

AI research is paused until the MVP user journey is operational. Current production AI remains Groq. Local research found that Qwen3-1.7B with constrained trusted evidence/relation selection is promising, but it is not deployed and should not block product readiness.
