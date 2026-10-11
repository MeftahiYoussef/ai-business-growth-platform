# Deployed Product Audit

Date: 2026-10-11

Environment:
- Frontend: Vercel staging, `https://ai-business-growth-platform-staging.vercel.app`
- Backend: Render Free, `https://ai-business-growth-platform.onrender.com`
- Database: Neon PostgreSQL
- Queue: Upstash Redis
- AI provider: Groq

This audit used real browser sessions against the deployed frontend. HTTP 200 responses, unit tests, and page render alone were not counted as feature success.

## Summary

Initial result: not MVP ready. The deployed app had a core auth/onboarding interaction defect and an async content-plan refresh race.

Current result after fixes: core MVP journey passes in deployed browser testing.

Core journey verified:

REGISTER / LOGIN -> BUSINESS ONBOARDING -> DASHBOARD -> AI STUDIO -> ASYNC GROQ CONTENT PLAN -> REFRESH RECOVERY -> 7-DAY PLAN -> DRAFT CONVERSION -> DRAFT EDIT -> REPORT -> NOTIFICATION -> JSON/CSV EXPORT -> LOGOUT/LOGIN -> DATA PERSISTENCE

## Root Causes Found

| Root cause | Impact | Fix |
| --- | --- | --- |
| Auth forms were interactive before React hydration. A fast click could submit the server-rendered form as a browser GET and place credentials in the URL. | P0: registration/login could fail before any API request, and password could appear in the URL. | Login/register forms now render disabled until hydrated and use `method="post"` as a fallback guard. |
| AI Studio showed `Generating...` before the queue endpoint returned a durable generation ID. Refreshing in that pre-queue window lost the job from the UI while the backend could still complete it. | P1: refresh recovery was unreliable and could create orphaned completed generations. | AI Studio now shows `Submitting...` before the queue response, stores the generation ID after HTTP 202, and only then shows queued/running recoverable state. |
| Audit assertion treated input values as page text. | False negative for draft edit persistence. | Rechecked field values directly; draft save returned 200 and persisted after reload. |
| Logout exists on Profile, not in the global shell. | P2 UX gap: user can log out, but not from every page. | Documented as remaining UX issue. |

## Route Inventory

| Route | Visible in nav | Auth required | Status | User action tested | Remaining issue |
| --- | --- | --- | --- | --- | --- |
| `/` | No | Depends | PARTIAL | Not a core destination in walkthrough. | Redirect behavior not separately audited. |
| `/login` | Public link | No | WORKING | Login, validation, logout/relogin persistence. | None blocking. |
| `/register` | Public link | No | WORKING | Registration from clean browser. | Free-tier latency can be noticeable. |
| `/forgot-password` | Login link | No | NOT_REQUIRED_FOR_MVP | Page route exists. | Password reset flow not in MVP acceptance. |
| `/onboarding` | Redirect target | Yes | WORKING | Ten-step business creation, save, dashboard redirect. | Multi-step flow is basic but functional. |
| `/dashboard` | Yes | Yes | WORKING | Fresh account, populated account, quick links render. | Some dashboard cards are placeholder-style metrics. |
| `/profile` | Yes | Yes | WORKING | Business profile display, logout, profile data persisted. | Logout only available here. |
| `/studio` | Yes | Yes | WORKING | Groq async content plan, polling, refresh recovery, 7 items rendered. | Cold starts can add latency. |
| `/calendar` | Yes | Yes | WORKING | Draft list, draft links, persisted generated drafts. | MVP list view only. |
| `/calendar/[id]` | From calendar | Yes | WORKING | Draft editor load, save, reload persistence. | Save feedback is toast-only. |
| `/reports` | Yes | Yes | WORKING | Async report generation, history, notification, JSON and CSV exports. | Report generation latency depends on free-tier wake/queue. |
| `/notifications` | Yes | Yes | WORKING | Report-ready notification visible. | No global logout button here. |
| `/analytics` | Yes | Yes | PARTIAL | Empty/fresh state loads safely. | Real analytics integrations are not MVP-critical. |
| `/competitors` | Yes | Yes | PARTIAL | Empty state loads safely. | Advanced competitor workflow is post-MVP. |
| `/competitors/[id]` | No | Yes | NOT_REQUIRED_FOR_MVP | Not tested without competitor records. | Post-MVP unless competitor detail becomes core. |
| `/trends` | Yes | Yes | NOT_REQUIRED_FOR_MVP | Empty state loads safely. | Trend Engine intentionally out of scope. |
| `/generate` | Yes | Yes | PARTIAL | Page loads safely. | Secondary generator is not core MVP path. |
| `/generator` | No | Yes | NOT_REQUIRED_FOR_MVP | Route exists but not primary navigation. | Should be consolidated or hidden later. |
| `/strategy` | Yes | Yes | PARTIAL | Page loads safely. | Strategy generation not part of core acceptance. |
| `/integrations` | Yes | Yes | PARTIAL | Empty state loads safely. | Real social integrations are post-MVP. |
| `/team` | Yes | Yes | PARTIAL | Team page loads with account context. | Invite workflow not core-tested. |
| `/analysis` | Yes | Yes | PARTIAL | Page loads safely. | Analysis generation not core MVP path. |
| `/settings` | No | Yes | PARTIAL | Redirects to `/profile`. | Redirect is acceptable, but route should be documented or removed later. |

Totals:
- Total deployed routes inventoried: 23
- Working: 10
- Partial: 8
- Not required for MVP: 5
- Broken: 0 after fixes
- Working percentage across all inventoried routes: 43.5%
- MVP core-flow working percentage: 100%

## Browser Evidence

Verified from deployed frontend:
- Registration and onboarding created a business and redirected to `/dashboard`.
- AI Studio queued a content-plan job with HTTP 202.
- Durable queued state stored `activeContentPlanGenerationId`.
- Browser refresh recovered the active async job.
- Completed plan contained days 1-7.
- Draft conversion created 7 drafts.
- Draft editor saved with HTTP 200 and persisted after reload.
- Report generation completed from the UI.
- JSON export returned 200.
- CSV export returned 200.
- Notification page showed the report-ready notification.
- Logout from Profile and relogin preserved drafts and reports.

Failed network requests during the final core checks: none.

Browser console/runtime errors during final core checks: none observed.

## Remaining Issues

P0: none known.

P1: none known for the core MVP journey.

P2:
- Logout is only available from Profile, not globally.
- Several navigation pages are functional empty/placeholder states rather than complete product workflows.
- Render Free cold starts and Vercel/Render auth latency remain noticeable.

P3:
- `/settings` redirects to `/profile`; later cleanup should either document it in navigation or remove the route.
- `/generator` overlaps conceptually with `/generate`.
- Advanced competitors, Trend Engine, social integrations, and richer analytics remain post-MVP.

## Release Gate

MVP READY for free staging/demo: YES, after the fixes in this branch are merged and the current deployed frontend build remains active.

Do not tag a release from the earlier incorrect readiness conclusion without acknowledging this audit and fix set.
