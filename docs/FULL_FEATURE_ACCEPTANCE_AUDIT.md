# Full Feature Acceptance Audit

Date: 2026-10-11

Scope: deployed MVP/demo feature correctness. This audit does not treat route availability, HTTP 200 responses, successful builds, or button clicks as sufficient proof. A feature is counted as correct only when the visible action produces meaningful, defensible output and persists where expected.

## Local / Staging Parity

| Feature | Local data source | Staging data source | Same? | Problem |
| --- | --- | --- | --- | --- |
| Auth | Next.js proxy -> Django auth | Same | Yes | No known parity issue. |
| Business profile | Next.js proxy -> Django `Business` API | Same | Yes | No known parity issue. |
| Dashboard | Django business/competitor/trend/content-idea APIs | Same | Mostly | Before this branch, dashboard displayed hardcoded `Business score 86` and `Trend score 92`; fixed to deterministic profile completeness and stored trend count. |
| Content Generator / Generate Ideas | Django `/content-ideas/generate` -> deterministic service | Same | Yes | P1: deterministic service produced repeated visible idea hooks/titles and arbitrary-looking scores; fixed in this branch. |
| AI Studio 7-day plan | Django AI content-plan queue -> Celery -> Groq | Same provider if env flags match | Yes for staging | Semantic QA still needs broader repeated-run review, but core deployed flow passed. |
| Drafts/calendar | Django planner draft APIs | Same | Yes | Core conversion/edit persistence passed. |
| Reports/exports | Django report queue -> Celery -> deterministic metrics + optional AI recommendations | Same | Yes | Metrics are deterministic; exports passed smoke. |
| Alerts | Django notifications API | Same | Yes | Report notification passed smoke; read/unread actions not yet complete. |
| Hidden/post-MVP routes | Django sandbox/mock-capable routes | Same | Yes | Removed from primary navigation for MVP demo; direct URLs remain post-MVP/partial. |

## Generate Ideas Root Cause

The visible duplicate idea defect came from `django-backend/apps/ai/services.py::generate_content_ideas`.

Before this branch:

- The service was deterministic mock logic, not Groq.
- Every card used the same visible hook: `The {target_audience} trend your competitors are testing now`.
- CTA alternated, and scores changed, making cards appear different while the core idea was duplicated.
- Hashtags were hardcoded: `#aibusiness`, `#contentops`, `#trendstrategy`.
- Scores were formula placeholders without clear UI labeling.
- The endpoint persisted whatever the generator returned; no duplicate detector existed.

After this branch:

- Idea batches are generated from business context, goals, platform preferences, and stored trend topics when present.
- Titles are normalized and must be unique.
- Near-duplicate title/hook/caption combinations are rejected.
- CTA-only differences do not make duplicate ideas valid.
- The endpoint makes one deterministic alternate attempt if validation fails.
- If validation still fails, the API returns a safe 502 generation error and does not persist/display bad cards.
- Scores are deterministic rule-based estimates and the UI labels them as `Estimated engagement` and `Context fit`.

## Generate Ideas Diversity Results

| Measurement | Before fix | After fix |
| --- | --- | --- |
| Default batch size | 10 | 10 |
| Within-run visible duplicate hook/title rate | 90% when using the visible card heading from the old service | 0% in backend contract test |
| Within-run exact normalized title duplicates | Not rejected | 0 |
| CTA-only duplicate accepted | Yes | No |
| 5-run exact title duplicates | Repeated deterministic batches possible | 0 duplicates across 50 endpoint-generated titles |
| Personalization | Generic SaaS/competitor wording | B2B AI software and local bakery outputs diverge by industry/product/audience |

## Score Provenance

| Score | Previous provenance | Current provenance | UI treatment |
| --- | --- | --- | --- |
| Engagement | Formula placeholder: `78 + (index % 5) * 4` | Deterministic estimate from profile richness, goals, platform presence, trend presence, and format position | Labeled `Estimated engagement` |
| Trend match | Stored trend score if available, otherwise hardcoded `82` | Stored trend score if available, otherwise deterministic context-fit estimate from profile richness | Labeled `Context fit` |

No score should be interpreted as live analytics. Real analytics remain on analytics/reporting paths backed by stored social account snapshots or deterministic report metrics.

## Feature Quality Matrix

| Feature | Route | Action | Data source | Expected | Actual | Semantic quality | Persistence | Local | Staging | Status | Root cause | Fix | Retest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Auth registration/login | `/register`, `/login` | Register, login, logout, relogin | Django auth | Secure cookie session, no credential URL leakage | Passed prior clean-browser smoke | Working | Session persists | Same | Same | WORKING | Hydration race fixed in PR #27 | No new fix | Browser smoke passed after PR #27 |
| Dashboard metrics | `/dashboard` | View metric cards and quick actions | Django APIs | Real or defensibly derived values only | Previously had hardcoded scores | Partial before fix | N/A | Same | Same | WORKING after fix | Hardcoded card values | Replaced with profile completeness, stored trend count, stored competitor/idea counts | Frontend lint/typecheck pending full run |
| Generate Ideas | `/generate` | Generate idea batch | Django deterministic service | Unique, personalized, meaningful cards | Previously duplicate visible ideas | Fail before fix | Ideas persisted | Same | Same | WORKING after fix | Mock generator lacked diversity validation | Business-aware generator, duplicate validator, bounded retry, score relabeling | 10 backend tests pass |
| Copy idea | `/generate` | Copy card content | Browser clipboard | Exact card content copied with feedback | Previously no success/error feedback | Partial before fix | N/A | Same | Same | WORKING after fix | Fire-and-forget clipboard call | Added async copy with toast | Needs browser retest |
| Save idea | `/generate` | Bookmark/save idea | Django status update | Persist saved status and show feedback | Saved but button did not disable when saved | Partial before fix | Server persisted | Same | Same | WORKING after fix | UX state not explicit | Added error handling and disabled saved button | Needs browser retest |
| Delete idea | `/generate` | Delete card | Django delete endpoint | Confirm, delete one card, persist after refresh | Deleted without confirmation/error handling | Partial before fix | Server persisted | Same | Same | WORKING after fix | Missing guard/feedback | Added confirmation and error handling | Needs browser retest |
| AI Studio content plan | `/studio` | Generate seven-day plan | Groq via Django/Celery | 7 reviewed items, durable async state | Passed clean-browser smoke | Working | Generation persisted | Same if flags match | Same | WORKING | Prior submitting-state race fixed | No new fix | Passed clean-browser smoke |
| Draft conversion | `/studio` -> `/calendar` | Convert plan items to drafts | Django planner APIs | Fields map correctly and no duplicates | Passed happy-path smoke | Working | Server persisted | Same | Same | WORKING | No current P1 found | No new fix | Needs deeper field-by-field audit |
| Draft editor | `/calendar/[id]` | Edit title/caption/CTA/hashtags/platform/type/objective | Django planner APIs | Each field saves/reloads | Passed representative smoke | Working | Server persisted | Same | Same | WORKING | No current P1 found | No new fix | Needs Unicode/invalid-value audit |
| Calendar list | `/calendar` | View drafts and edit links | Django planner APIs | No phantom/missing/duplicate drafts | Passed smoke for generated drafts | Working | Server persisted | Same | Same | WORKING | No current P1 found | No new fix | Needs large-list audit |
| Reports | `/reports` | Generate report | Django reports/Celery | Deterministic metrics, optional AI separated | Passed smoke | Working | Server persisted | Same | Same | WORKING | No current P1 found | No new fix | Needs 0-data/small-data manual verification |
| JSON/CSV exports | `/reports` | Download exports | Django export endpoints | Correct status/content, no HTML error | Passed smoke with HTTP 200 | Working | N/A | Same | Same | WORKING | No current P1 found | No new fix | Needs file content diff to DB |
| Alerts | `/notifications` | View report notification | Django notifications API | New notification visible | Passed smoke | Working for view | Server persisted | Same | Same | WORKING | No current P1 found | No new fix | Read/unread not fully audited |
| Profile | `/profile` | Edit business profile and logout | Django business/auth APIs | Fields persist and are consumed by generation | Passed profile edit smoke; Generate Ideas now consumes context | Working | Server persisted | Same | Same | WORKING | No current P1 found | Generator previously underused fields | Generator now uses profile context | Needs all-field invalid/Unicode audit |
| Hidden partial routes | `/analytics`, `/competitors`, `/trends`, `/strategy`, `/integrations`, `/team`, `/analysis`, `/generate` direct | Direct URL access | Mixed/sandbox APIs | Not misleading in primary nav | Removed from primary nav, but direct URLs remain | Partial/post-MVP | Mixed | Same | Same | PARTIAL / NOT_REQUIRED | Feature scope not complete | Primary nav hides them | Keep labeled or disabled before promotion |

## Button / Form Inventory Summary

| Area | Visible controls audited | Result |
| --- | --- | --- |
| Auth forms | Register, login, show/hide password, logout | Working after PR #27 smoke. |
| Dashboard | Quick actions | Fixed to core MVP routes only. |
| Generate Ideas | Generate, copy, save, delete | P1 generator fixed; copy/save/delete UX fixed; browser retest still required. |
| AI Studio | Generate plan, platform toggles, selected days, create drafts | Core path passed smoke; broader combinations still P2 audit work. |
| Draft editor | Save draft fields | Representative edit passed smoke; deeper validation remains. |
| Reports | Generate report, JSON, CSV | Smoke passed. |
| Notifications | View notification | Smoke passed; read actions not currently exposed in UI. |
| Profile | Save profile, theme toggle, logout | Save/logout passed; theme is client-only UX. |

## Remaining Priorities

P0: none found in this pass.

P1 fixed in this branch:

- Generate Ideas duplicate visible output.
- Generate Ideas arbitrary-looking score presentation.
- Generate Ideas copy/save/delete feedback gaps.
- Dashboard hardcoded metrics.
- Dashboard quick actions to hidden/post-MVP routes.

P1 remaining: none known after this branch, pending deployed browser retest.

P2/P3 remaining:

- Full browser validation of Generate Ideas copy/save/delete after deploy.
- Field-by-field draft editor validation for invalid values, max lengths, special characters, French, and Russian.
- Report export file-content comparison to database values.
- Notification read/unread behavior if exposed later.
- Render Free true idle wake monitoring.
- Direct hidden routes should be labeled Coming Soon or kept out of primary navigation until complete.

## Current Ratings

This is a feature-level estimate after code audit plus targeted tests, not a full product re-certification:

- Total visible/current MVP feature groups: 13
- PERFECT: 0
- WORKING: 10
- PARTIAL: 3
- BROKEN: 0 after this branch
- PLACEHOLDER: 0 in primary navigation
- Feature functionality: 76.9% working-or-better
- Core MVP: 100% from prior clean-browser smoke, pending retest with this branch
- Semantic quality pass: improved for Generate Ideas; full semantic QA still requires broader repeated browser audit
- Visible button pass: partial until Generate Ideas copy/save/delete browser retest
- Form pass: partial until field-by-field invalid/Unicode audit
- Local/staging parity: code paths match for current frontend/backend architecture; staging will need redeploy to pick up this branch
