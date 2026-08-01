# Asynchronous Business Reports

Last updated: 2026-07-31.

This document describes the source-code foundation for asynchronous analytics and business report generation. It reuses the existing Django, PostgreSQL, Redis, and Celery architecture. Do not add secrets to this file.

## Scope

The initial report type is `business_performance`. It uses only data already stored by the application:

- content draft totals and workflow statuses;
- stored published-post records where available;
- platform, content-type, and objective breakdowns;
- AI generation counts, completion/failure counts, and token totals;
- recent stored trend findings;
- stored competitor observations;
- explicit data limitations.

The report does not fabricate impressions, reach, clicks, engagement rate, revenue, conversions, or follower growth. Those metrics stay unavailable until real provider analytics are imported.

## Architecture

`common.BackgroundJob` is the reusable durable job model. PostgreSQL is the source of truth for job state, input, result references, progress, retries, and sanitized failures. Redis is only the Celery broker/result transport.

Business reports are stored in `reports.Report` and linked one-to-one with their creating background job. Historical completed reports are preserved; a new non-idempotent request creates a new report version.

Lifecycle:

```text
client submits report request
-> Django validates auth, business ownership, type, dates, and input size
-> BackgroundJob is created as queued
-> transaction.on_commit() enqueues Celery with the job UUID only
-> worker locks the job and marks running
-> worker aggregates deterministic PostgreSQL metrics
-> optional AI recommendations are generated from aggregate metrics only
-> report JSON is stored and the job becomes completed or failed
-> frontend polls the job status endpoint and loads the report
```

Celery task arguments contain only safe identifiers. Credentials, request objects, ORM objects, cookies, JWTs, and provider keys must never be task arguments.

## Flags

Backend defaults are disabled:

```env
ASYNC_REPORTS_ENABLED=false
REPORT_AI_RECOMMENDATIONS_ENABLED=false
REPORT_MAX_PERIOD_DAYS=366
```

Frontend defaults are disabled:

```env
NEXT_PUBLIC_ASYNC_REPORTS_ENABLED=false
```

Do not enable staging report UI flags until source tests, CI, migrations, and an explicit staging activation plan are complete.

## API

```text
POST /api/reports/queue/
GET /api/reports/jobs/{job_id}/status/
GET /api/reports/{report_id}/
GET /api/reports/
GET /api/reports/{report_id}/export.csv/
GET /api/reports/{report_id}/export.json/
```

`POST /api/reports/queue/` returns `202 Accepted` with a job ID and status URL. Queue requests support `Idempotency-Key`.

Cross-business report and job access returns a safe `404`. Responses do not expose Celery internals, broker URLs, provider response bodies, stack traces, or credentials.

## Idempotency

Explicit idempotency keys are scoped by user, business, and job type.

- Same key and same request returns the existing job.
- Same key and different request returns `409`.
- Database constraints protect concurrent submissions.
- No-key submissions use a short active-job fingerprint guard to reduce accidental rapid duplicates while still allowing intentional later report generation.

Retries and duplicate task delivery are idempotent: a completed job is a no-op, and a job can create at most one linked report.

## Progress

Progress is coarse-grained and persisted:

```text
queued: 0
collecting_data: 20
aggregating_metrics: 45
generating_recommendations: 70
saving_report: 90
completed: 100
failed: 100
```

The application does not invent precise progress from elapsed time.

## AI Recommendations

Numeric metrics are computed by Django from PostgreSQL. AI may only provide narrative highlights, risks, and recommendations when `REPORT_AI_RECOMMENDATIONS_ENABLED=true` and the request asks for recommendations.

The provider receives aggregate counts and minimal business profile context only. Recommendations must include `requires_human_review=true`. AI recommendation failures are sanitized and retried only when transient.

## Retry Policy

The report task retries transient provider/network errors with bounded retry count, backoff, and jitter. It does not retry invalid dates, unsupported report types, authentication, authorization, missing business records, quota exhaustion, or permanent configuration failures.

Failed jobs store a safe error code and user-facing message. Raw stack traces and sensitive provider response bodies are not stored.

## Exports

Initial exports are JSON and CSV. They require authorized report access, use safe generated filenames, and do not create public temporary URLs. PDF generation is intentionally out of scope.

## Local Commands

```bash
docker compose up -d postgres redis
```

Worker:

```bash
cd django-backend
CELERY_TASK_ALWAYS_EAGER=false celery -A config worker --loglevel=INFO --concurrency=1
```

Focused Redis integration:

```bash
RUN_REDIS_INTEGRATION=true USE_SQLITE=false CELERY_TASK_ALWAYS_EAGER=false .venv/bin/pytest tests/test_celery_integration.py
```

## Staging Preparation

No new Railway service is required. Future staging activation should reuse:

- existing Django web service;
- existing private Celery worker;
- existing private Redis service;
- existing PostgreSQL service.

Worker concurrency remains `1`. Redis and the worker must not have public domains.

## Future Social Sync Foundation

Future background job types are reserved for `social_account_sync`, `analytics_import`, `competitor_refresh`, `weekly_report`, and `trend_refresh`. Live social synchronization is not implemented in this phase.

Before real provider sync is added, it must include encrypted OAuth tokens, token refresh, read-only scopes by default, provider-specific rate limits, cursor pagination, idempotent upserts, webhook reconciliation, revoked-access handling, and no publishing permission unless explicitly approved.
