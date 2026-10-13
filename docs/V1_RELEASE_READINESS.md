# v1.0.0 Release Readiness

Date: 2026-10-13

Final release status and deployed acceptance evidence are recorded in the [v1.0.0 release](https://github.com/MeftahiYoussef/ai-business-growth-platform/releases/tag/v1.0.0). Publish that release only after final main CI, deployment verification, and a clean-browser journey pass. The findings below retain the pre-release history, including failed gate attempts.

## Scope

Current v1 scope is the single-business MVP:

- dashboard
- profile and business context editing
- Generate Ideas
- AI Studio seven-day plans
- drafts
- calendar/list
- reports
- alerts
- JSON/CSV exports

Post-v1:

- multi-business switching
- advanced competitors
- advanced trend engine
- auto-publishing
- advanced analytics
- billing
- knowledge base/RAG

## Current Feature Gate

Baseline tag: `v0.9.0-mvp-hardened`

Current MVP feature groups: 13

Current classification before this release branch:

- Working: 13
- Partial: 0
- Broken: 0
- P0: 0
- P1: 0

Release branch findings and fixes:

- Removed fake Profile usage counts.
- Removed hidden Strategy fallback recommendations that looked like real intelligence.
- Relabeled Competitor sample post generation as post-MVP/sample data.
- Added a server-side daily Generate Ideas item cap with `CONTENT_IDEAS_MAX_BUSINESS_DAILY_ITEMS`.
- Added content-plan validation to reject unsupported quantitative performance claims such as `40% faster sales cycle`.

## Deployed Reverification

Fresh browser MVP journey was rerun against deployed staging on 2026-10-13 before release-branch changes:

- Registration/login: pass
- Business onboarding/profile persistence: pass
- Desktop navigation: pass
- Mobile navigation: pass
- Favicon: pass
- Generate Ideas: 3 batches, 10 ideas each, Groq-backed, no duplicates
- AI Studio: 7 items generated through async queue
- Report: completed
- Notifications: read state persisted
- JSON/CSV exports: pass
- Logout/relogin persistence: pass
- Browser console errors: none
- Unexpected failed requests: none

Known harness limitations from that smoke:

- Headless clipboard read is unreliable; previous targeted copy test passed.
- Some text checks in the harness underreported draft edit/human-review state despite successful persistence and generated content.

## Repeated AI Quality Sampling

Generate Ideas deployed probe:

- Attempted: 20 batches across 4 synthetic businesses
- Completed before provider failure: 16 batches
- Total ideas generated: 160
- Normal provider path: Groq for all completed batches
- Deterministic fallback use: 0
- Within-batch duplicate normalized titles: 0
- Near-duplicate pairs: 0
- Provider rate limits: 2 recovered 429s
- Final stop: safe 502 provider failure on batch 17
- Average completed-batch latency: about 27.7 seconds

AI Studio deployed probe:

- Completed: 10 plans
- Success rate: 100%
- Items per plan: 7/7
- Duplicate title rate: 0
- Near-duplicate pairs: 0
- Human review flag: 7/7 for every plan
- Provider: Groq
- Average latency: about 24.2 seconds

AI quality issue found:

- One plan title included an unsupported metric claim: `40% Faster Sales Cycle`.
- Release branch now rejects unsupported quantitative performance claims in generated plan text fields.

## Final Browser Gate Findings

- Root route loading boundary removed in PR #33 after deployed authenticated pages stayed on `Loading...`.
- Studio job `55c6e4d6-aad8-4d9e-9498-f46c3b6b8bcb` returned `failed`, `AIValidationError`, and `result_available=false`. A successful Celery task exit did not mean a successful AI generation.
- A fresh deployed Studio run rendered seven items, confirming that the failure was intermittent invalid provider output.
- Validation recovery regenerates once from the original business context. Both responses are checked against the same validation; rejected output is never saved as a usable plan. Successful usage includes tokens from both responses.
- Studio failures remain visible beside the generation button. Terminal jobs without a usable plan stop polling and allow retry.
- The next browser run hit a safe provider error on idea batch three after Groq 429 and repeated schema-rejection responses. It also exposed fabricated customer-growth copy in an accepted batch. Idea generation now rejects known quantitative performance claims and regenerates once using its existing validation retry; its prompt explicitly prohibits invented customers, testimonials, and case-study results.
- Release tagging remains blocked until the final deployed clean-browser journey passes.

## Provider And Quota Notes

Groq is the production AI provider. Qwen, LoRA, and RAG are not part of v1.0.0.

Content-plan generation already has user/day and business/month limits. Generate Ideas now has a business/day item cap to avoid unlimited provider spend and to fail before unbounded external-provider usage.

`CONTENT_IDEAS_MAX_BUSINESS_DAILY_ITEMS=200` semantics:

- The quota counts persisted generated `ContentIdea` rows, not request attempts.
- The reset boundary is the Django server timezone day boundary.
- A normal 10-idea request allows up to 20 successful batches per business per day.
- The quota is business-scoped.
- Requests that would exceed the cap are rejected before the provider call with HTTP 429.
- Failed provider calls do not consume quota because no ideas are persisted.
- Internal provider retry attempts do not consume quota unless the final batch is accepted and saved.
- Duplicate completed requests can still consume quota as separate successful batches; the daily cap bounds the total.

Provider burst reliability is a v1 operational limitation:

- Sustained repeated Generate Ideas calls can hit Groq 429/502 responses.
- The app returns safe errors.
- The product should not promise uninterrupted high-volume generation on free/demo staging.

## Health

Checked on 2026-10-13:

- `/api/health/live/`: 200, `{"status":"ok"}`
- `/api/health/ready/`: 200, database ok, Redis ok
- `/api/docs/`: 200

## Dependency Audit

Completed on 2026-10-13:

- Frontend production audit: `npm audit --omit=dev --audit-level=moderate` returns `found 0 vulnerabilities`.
- Frontend full audit: remaining high advisory is dev-only through `eslint-config-next`/`@next/eslint-plugin-next`/`fast-glob`/`micromatch`/`braces`; the available fix requires a forced breaking lint-package path and is not deployed runtime code.
- Backend audit: `pip-audit -r requirements.txt` returns `No known vulnerabilities found`.

Security updates applied:

- `next` -> `16.4.0`
- `djangorestframework` -> patched range `>=3.17.2,<3.19` (local audit resolved to `3.18.3`)
- `python-dotenv` -> patched range `>=1.2.2,<1.3` (local audit resolved to `1.2.4`)
- `pytest` -> patched range `>=9.0.3,<10` (local audit resolved to `9.1.1`)

No unresolved release-blocking dependency advisory remains.

## Backup And Restore Drill

Completed on 2026-10-13 using PostgreSQL 16.15 Docker tooling against the Neon staging database.

- Backup format: custom `pg_dump --format=custom --no-owner --no-acl`
- Backup timestamp UTC: `20261013T095808Z`
- Backup size: `412005` bytes
- Backup SHA-256: `3aea2440eb360e396353666dd08322625ca7e8fd6e32284e88d5e5ded3d47565`
- Restore target: temporary local PostgreSQL 16 container
- Restore result: PASS
- Temporary restore target: destroyed after verification

Safe source/restored count comparison:

| Table/group | Source | Restored |
| --- | ---: | ---: |
| `django_migrations` | 56 | 56 |
| users | 45 | 45 |
| businesses | 36 | 36 |
| content ideas | 464 | 464 |
| AI generations | 21 | 21 |
| background jobs | 8 | 8 |
| drafts | 56 | 56 |
| reports | 8 | 8 |
| notifications | 8 | 8 |

Expected table check: 9/9. Checked orphan counts for drafts, AI generations, reports, and notifications were all 0.

## Release Gate

v1.0.0 requires:

- P0 = 0
- P1 = 0
- 13/13 current MVP feature groups working or perfect
- no known data-loss issue
- no known authorization leak
- no known credential leak
- backup procedure documented and restore drill passed
- dependency advisory review completed with no unresolved release blockers
- deployment runbook documented
- rollback procedure documented
- clean-browser journey passed
- main CI passed
- deployed main commit verified

Final gate outcome: see the [v1.0.0 release evidence](https://github.com/MeftahiYoussef/ai-business-growth-platform/releases/tag/v1.0.0). A failed browser run or incomplete main CI blocks publication.
