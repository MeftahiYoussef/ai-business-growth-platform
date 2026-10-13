# v1.0.0 Release Readiness

Date: 2026-10-13

Status: **not ready to tag yet**. The release branch is in hardening and documentation. A v1.0.0 tag requires this branch to merge, final main CI to pass, main to deploy, and a final clean-browser journey to pass.

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

## Provider And Quota Notes

Groq is the production AI provider. Qwen, LoRA, and RAG are not part of v1.0.0.

Content-plan generation already has user/day and business/month limits. Generate Ideas now has a business/day item cap to avoid unlimited provider spend and to fail before unbounded external-provider usage.

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

Attempted on 2026-10-13:

- `npm audit --audit-level=moderate`: blocked by DNS/network access to `registry.npmjs.org`.
- `pip list --outdated`: blocked by DNS/network access to PyPI and stopped after repeated retries.

Dependency advisory review is therefore **NOT_FULLY_TESTED** in this workspace and should be rerun in CI or another environment with registry access before tagging v1.0.0.

## Release Gate

v1.0.0 requires:

- P0 = 0
- P1 = 0
- 13/13 current MVP feature groups working or perfect
- no known data-loss issue
- no known authorization leak
- no known credential leak
- backup procedure documented
- dependency advisory review completed or explicitly accepted
- deployment runbook documented
- rollback procedure documented
- clean-browser journey passed
- main CI passed
- deployed main commit verified

Current status: **not ready to tag until this release branch is merged, deployed, and clean-browser verified.**
