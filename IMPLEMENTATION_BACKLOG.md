# Implementation Backlog

| Priority | Task | Files | Dependencies | Acceptance Criteria |
| --- | --- | --- | --- | --- |
| P0 | Add full brand profile fields to UI | onboarding/profile pages | Business model extension | All brand fields editable. |
| P0 | Monitor Railway staging usage | Railway dashboard | Active Railway staging services | Usage remains within the intended staging budget and no paid plan upgrade is selected without approval. |
| P0 | Complete provider-native Git autodeploy evidence | Railway/Vercel dashboards | Deferred provider Git connection verification | Prove Vercel and Railway deploy the exact `main` merge commit after CI without using provider deployment tokens. |
| P1 | Real OAuth providers | `apps/integrations/providers` | Platform credentials | OAuth connect/revoke/refresh for Instagram/Facebook/LinkedIn. |
| Done | Activate async reports in staging | Existing Railway web/worker/Redis and Vercel frontend | Source async report foundation, migrations, CI | Completed on 2026-08-01. `ASYNC_REPORTS_ENABLED` and `NEXT_PUBLIC_ASYNC_REPORTS_ENABLED` were enabled on the existing staging services, browser/API smoke tests passed, and the synchronous report fallback remains available. |
| P1 | Async jobs beyond reports | Django backend | Celery/Redis staging worker | Social sync and future publishing-related jobs run async with retry logs; publishing remains explicitly gated and unimplemented. |
| P1 | Revise small LLM curriculum v2 | `ml/datasets/`, `ml/training/reports/lora_v1_failure_analysis.md` | LoRA v1 failure analysis and llama.cpp constrained-decoding evidence | Add higher-diversity synthetic examples for required facts, safety refusals, multilingual instruction following, numeric preservation, and semantic fidelity before a second LoRA run. |
| Done | Test constrained local serving | `ml/eval/`, model-lab runtime | Qwen baseline and LoRA v1 reports | Completed on 2026-09-22. llama.cpp JSON Schema enforcement fixed Qwen content-plan schema and seven-day validity in the frozen benchmark; semantic and safety gaps remain. |
| P1 | Scheduled publication | `apps/content_planner` | Provider APIs | Approved scheduled posts publish or fail with retry. |
| P1 | Campaign analytics | analytics/reports | Campaign metrics | Campaign report has actual-vs-target metrics. |
| P2 | Billing and subscriptions | new billing app | Stripe or provider | Server-side feature limits enforced. |
| P2 | Knowledge base | new knowledge app | pgvector/storage | Business-isolated document chunks searchable. |
| P3 | Social inbox | new inbox app | Provider API support | Comments/mentions sync and resolution workflow. |

## Completed Infrastructure

- Real Groq smoke test and seven-day content-plan workflow passed with `openai/gpt-oss-20b`.
- PostgreSQL development configuration, Compose service, CI service, health endpoints, connection persistence, SSL mode support, and database-level duplicate draft protection are implemented.
- Staging deployment is live with Vercel, Railway Django, and Railway PostgreSQL. Health checks, authentication, real Groq seven-day generation, draft conversion, duplicate prevention, backup, isolated restore, rollback to `v0.2.0-staging`, and latest-main restoration passed. Render PostgreSQL was created earlier and is preserved but unused.
- Celery/Redis staging services are active after explicit approval: private Railway Redis service `Redis`, private worker `ai-business-growth-celery-worker-staging`, backend Redis readiness, and browser-level async Groq smoke through Vercel queue/polling passed. The synchronous endpoint remains available for rollback.
- Asynchronous business-performance report source foundation is implemented behind disabled feature flags. It reuses the existing Redis/worker, stores durable jobs in PostgreSQL, computes metrics from stored data only, supports optional AI recommendations with human-review requirements, and prepares future read-only social-sync job types without adding OAuth or publishing.
- Small LLM experimental source foundation is implemented for `Qwen/Qwen3-1.7B`: local OpenAI-compatible provider, 50-case synthetic evaluation dataset, deterministic evaluator, SFT dataset builder, LoRA config, model registry metadata, and future RAG contract. The content-plan evaluator reuses the production `content_plan_contract_v2`; Groq reference comparison completed; Qwen full 50-case baseline completed; LoRA v1 trained locally but did not improve structural behavior and is rejected. A llama.cpp constrained-decoding diagnostic fixed content-plan structure with base Qwen and identified remaining semantic/safety curriculum gaps. No RAG, embeddings, staging activation, or paid resources are included.
