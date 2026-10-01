# MVP Readiness Matrix

Verified date: 2026-10-01

| Area | Status | Blocker | Severity | Required for MVP | Owner/action | Verified date |
| --- | --- | --- | --- | --- | --- | --- |
| Authentication | READY | None known in code audit. | - | Yes | Run browser E2E after staging recovery. | 2026-10-01 |
| Business onboarding | READY | Preferred platforms/posting frequency not modeled. | P2 | Yes | Keep current concise onboarding; add richer profile fields later. | 2026-10-01 |
| AI content plan | READY | Needs staging E2E once infrastructure is healthy. | P1 | Yes | Verify one Groq seven-day generation through queue/polling. | 2026-10-01 |
| Async jobs | READY | Staging Redis/worker offline. | P0 | Yes | Recover existing Railway Redis/worker after Postgres is safe. | 2026-10-01 |
| Draft editing | PARTIAL | UI edit workflow is minimal. | P1 | Yes | Add clearer edit/save screen for generated drafts. | 2026-10-01 |
| Calendar | PARTIAL | List view only. | P3 | Yes | Use list for MVP; calendar grid later. | 2026-10-01 |
| Reports | READY | Needs staging E2E once infrastructure is healthy. | P1 | Yes | Verify async report queue/poll/history/export. | 2026-10-01 |
| Exports | READY | None known in code audit. | - | Yes | Verify JSON/CSV download in browser. | 2026-10-01 |
| Notifications | READY | Needs E2E confirmation for single report notification. | P1 | Yes | Verify notification after report completion. | 2026-10-01 |
| Competitor MVP | PARTIAL | Qualitative comparison text is not sourced from real analysis. | P2 | Yes | Keep competitor records; defer sophisticated comparison. | 2026-10-01 |
| Trend engine | NOT_REQUIRED_FOR_MVP | Advanced deterministic engine not implemented. | P3 | No | Defer advanced trend prediction. | 2026-10-01 |
| Error handling | PARTIAL | Browser failure-path sweep pending. | P2 | Yes | Test provider/job/auth/input failures after staging recovery. | 2026-10-01 |
| Responsive UX | PARTIAL | Not browser-verified in this pass. | P2 | Yes | Check desktop/tablet/mobile in final MVP E2E. | 2026-10-01 |
| Observability | PARTIAL | No paid monitoring integration; staging unhealthy. | P2 | Yes | Use health endpoints/job logs; add lightweight alerts later. | 2026-10-01 |
| Database backup | BLOCKED | Existing Railway Postgres offline; volume appears detached in read-only status. | P0 | Yes | Safe infra recovery first; do not replace volume. | 2026-10-01 |
| Deployment | BLOCKED | Railway backend/worker/db/Redis unhealthy. | P0 | Yes | Recover existing infrastructure in approved recovery task. | 2026-10-01 |
| Staging E2E | BLOCKED | Backend, worker, Postgres, and Redis are not healthy. | P0 | Yes | Run full MVP browser/API journey after recovery. | 2026-10-01 |

