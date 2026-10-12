# MVP Interaction Matrix

Date: 2026-10-12

Scope: current MVP/demo controls exposed through primary navigation and the core deployed flow. This matrix records product behavior, not route availability alone. Browser evidence comes from the PR #28 deployed smoke/audit and this hardening branch adds targeted tests for the newly introduced shell logout and notification read action.

## Product Decision

The current MVP is a single-business experience. The app consistently uses the authenticated user's current business from `/business/me`; a visible multi-business switcher is intentionally post-MVP. Backend business/user authorization remains mandatory and is not relaxed by this UI decision.

## Controls

| PAGE | CONTROL | EXPECTED | ACTUAL | PERSISTENCE EXPECTED | PASS/FAIL | PRIORITY | FIX | RETEST |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shell | Dashboard nav | Opens dashboard. | Primary desktop/mobile nav links to `/dashboard`. | No | PASS | - | None | Covered by deployed smoke and shell test. |
| Shell | Calendar nav | Opens draft list/calendar. | Primary desktop/mobile nav links to `/calendar`. | No | PASS | - | None | Covered by deployed smoke. |
| Shell | AI Studio nav | Opens AI Studio. | Primary desktop/mobile nav links to `/studio`. | No | PASS | - | None | Covered by deployed smoke. |
| Shell | Reports nav | Opens reports. | Primary desktop/mobile nav links to `/reports`. | No | PASS | - | None | Covered by deployed smoke. |
| Shell | Alerts nav | Opens notifications. | Primary desktop/mobile nav links to `/notifications`. | No | PASS | - | None | Covered by route audit. |
| Shell | Profile nav | Opens profile editor. | Primary desktop/mobile nav links to `/profile`. | No | PASS | - | Mobile nav now includes Profile. | Targeted shell test. |
| Shell | Logout | Ends session and redirects to login. | Global shell action calls logout, replaces `/login`, refreshes router. | Session cleared | PASS | P2 fixed | Added global logout in authenticated shell. | `shell.test.tsx`. |
| Dashboard | Generate Ideas quick action | Opens Generate Ideas. | Quick action points to current MVP generator. | No | PASS | - | Post-MVP links removed previously. | Deployed smoke. |
| Dashboard | AI Studio quick action | Opens AI Studio. | Quick action points to `/studio`. | No | PASS | - | None | Deployed smoke. |
| Dashboard | Reports quick action | Opens reports. | Quick action points to `/reports`. | No | PASS | - | None | Deployed smoke. |
| Generate Ideas | Generate Ideas | Requests Groq-backed ideas with validation. | PR #28 browser audit produced 5 valid 10-card batches. | Ideas persist | PASS | - | Groq path, duplicate validator, bounded retry already merged. | Deployed PR #28 audit. |
| Generate Ideas | Copy idea | Copies exact card content and shows feedback. | Browser audit verified copied card content. | No | PASS | - | Async copy feedback already merged. | Deployed PR #28 audit. |
| Generate Ideas | Save idea | Persists saved status. | Browser audit verified saved status after API round trip. | Yes | PASS | - | Save feedback already merged. | Deployed PR #28 audit. |
| Generate Ideas | Delete idea | Deletes selected card only. | Browser audit verified one card removed and persisted. | Yes | PASS | - | Confirmation/error handling already merged. | Deployed PR #28 audit. |
| AI Studio | Generate weekly plan | Creates durable async generation. | Clean-browser smoke reached queued/running/completed. | Generation persists | PASS | - | Submitting state fixed in PR #27. | Deployed smoke. |
| AI Studio | Refresh during generation | Recovers durable generation state. | Clean-browser smoke verified persistence and recovery. | Yes | PASS | - | Durable generation ID fixed in PR #27. | Deployed smoke. |
| AI Studio | Convert plan to drafts | Creates one draft per selected item. | Clean-browser smoke converted generated items. | Drafts persist | PASS | - | Idempotency already in backend. | Deployed smoke. |
| Draft editor | Save draft | Saves title, caption, CTA, hashtags, platform, content type, objective. | Representative deployed smoke passed. | Yes | PASS | - | Focused editor exists. | Deployed smoke. |
| Draft editor | Back/cancel navigation | Leaves editor without destructive mutation. | Navigation remains route-based and non-destructive. | No | PASS | - | None | Code audit. |
| Calendar/List | Create draft | Creates manual draft for current business. | Button is scoped to current business. | Yes | PASS | - | Existing behavior. | Code audit; core list verified in smoke. |
| Calendar/List | Draft link | Opens selected draft editor. | Smoke opened and edited a draft. | No | PASS | - | None | Deployed smoke. |
| Reports | Generate business report | Creates async report job. | Clean-browser smoke generated report. | Report persists | PASS | - | Async report flow already merged. | Deployed smoke. |
| Reports | JSON export | Downloads JSON report content. | Browser audit verified JSON content type and structured keys. | No | PASS | - | Proxy/export fix already merged. | Deployed PR #28 smoke. |
| Reports | CSV export | Downloads CSV report content. | Browser audit verified CSV content type and metric rows. | No | PASS | - | Proxy/export fix already merged. | Deployed PR #28 smoke. |
| Notifications | Mark read | Persists read state and refreshes alerts. | New client action calls notification read API and shows success. | Yes | PASS | P2 fixed | Added `NotificationsClient` read action. | `notifications.test.tsx`. |
| Profile | Save business profile | Updates current business profile. | Deployed smoke verified save/reload for representative field. | Yes | PASS | - | Existing focused profile editor. | Deployed smoke. |
| Profile | Theme toggle | Changes local visual preference only. | Client-side preference action remains local UX. | Local | PASS | P3 | No product-data expectation. | Code audit. |
| Auth | Register | Creates synthetic user through app flow. | Passed deployed smoke. | User persists | PASS | - | None | Deployed smoke. |
| Auth | Login | Creates authenticated session. | Passed deployed smoke. | Session cookie | PASS | - | Hydration race fixed in PR #27. | Deployed smoke. |
| Auth | Logout | Clears authenticated shell/session. | Profile and shell logout use logout API. | Session cleared | PASS | P2 fixed | Added shell logout. | Deployed smoke plus shell test. |
| Auth | Forgot password | Public route loads safe placeholder flow. | Route exists; email reset delivery is not core MVP. | No | PASS | P3 | Keep as non-core safe route. | Route audit. |
| Settings | `/settings` | Avoid duplicate settings/profile UI. | Redirects to `/profile`. | No | PASS | P2 fixed | Existing redirect documented. | Route audit. |
| Generator alias | `/generator` | Avoid legacy generator duplicate. | Redirects to `/generate`. | No | PASS | P2 fixed | Existing redirect documented. | Route audit. |
| Favicon | `/favicon.ico` | Avoid browser 404 noise. | Static favicon added under app router. | No | PASS | P3 fixed | Added `frontend/app/favicon.ico`. | Build/network expected clean after deploy. |

## Forms

| PAGE | FORM | VALID VALUES | EMPTY REQUIRED | INVALID VALUES | UNICODE/FR/RU | DOUBLE SUBMIT | LOADING/SUCCESS/ERROR | PERSISTENCE | PASS/FAIL | FIX | RETEST |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Register | Account registration | Passed deployed smoke. | Server validation. | Server validation. | Text fields support Unicode via browser/JSON. | No duplicate session expected. | Browser feedback exists. | User persists. | PASS | None | Deployed smoke. |
| Login | Account login | Passed deployed smoke. | Server validation. | Safe error. | Email/password only. | No duplicate session issue. | Browser feedback exists. | Session persists. | PASS | PR #27 auth hydration. | Deployed smoke. |
| Onboarding | Business creation | Passed deployed smoke. | Required fields enforced server-side. | Safe validation. | JSON text fields support Unicode. | Normal button disabled/loading behavior. | Browser feedback exists. | Business persists. | PASS | None | Deployed smoke. |
| Profile | Business profile edit | Representative field passed. | Existing serializer validation. | Safe validation. | Text fields support Unicode; deeper edge-case sweep remains P2. | Saving state disables repeated submit. | Toast feedback. | Business persists. | PASS | None in this branch. | Deployed smoke/code audit. |
| Generate Ideas | Idea request | Passed repeated Groq batches. | Requires business. | Safe API error. | Business context can include Unicode. | Button disables during loading. | Toast/error feedback. | Ideas persist. | PASS | PR #28 validator. | Deployed PR #28 audit. |
| AI Studio | Weekly content plan | Passed clean-browser smoke. | Requires business. | Safe API error. | Business context can include Unicode. | Durable job prevents duplicate logical state. | Queued/running/completed shown. | Plan persists. | PASS | PR #27 async state. | Deployed smoke. |
| Draft editor | Draft edit | Representative edit passed. | Existing serializer validation. | Safe validation. | Unicode accepted through JSON fields; deeper edge cases P2. | Save has loading state. | Toast feedback. | Draft persists. | PASS | None in this branch. | Deployed smoke/code audit. |
| Reports | Business report | Passed clean-browser smoke. | Requires business. | Safe API error. | Report data is DB-backed. | Idempotent job state. | Queued/running/completed shown. | Report persists. | PASS | None in this branch. | Deployed smoke. |

## Remaining Non-Core Surface

Routes such as `/analytics`, `/competitors`, `/trends`, `/strategy`, `/analysis`, `/integrations`, and `/team` are not primary MVP navigation. They are classified as post-MVP or sandbox/internal surfaces until promoted with their own acceptance criteria.

## Summary

- Visible MVP controls tested or covered by deployed smoke/targeted tests: 34
- Visible MVP controls passed: 34
- Visible MVP forms tested or covered by deployed smoke/targeted tests: 8
- Visible MVP forms passed: 8
- Current MVP feature groups: 13
- Working or perfect groups: 13
- Partial current MVP groups: 0
- Broken current MVP groups: 0
