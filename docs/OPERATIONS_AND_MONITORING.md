# Operations And Monitoring

Date: 2026-10-13

## Active Staging Architecture

Vercel frontend -> Render Free backend -> Django/Gunicorn -> Celery concurrency 1 -> Upstash Redis -> Neon PostgreSQL -> Groq.

Railway is archive/historical-data recovery only.

## What To Check First

1. Frontend: open `https://ai-business-growth-platform-staging.vercel.app/login`.
2. Backend liveness: `GET /api/health/live/`.
3. Backend readiness: `GET /api/health/ready/`.
4. API docs: `GET /api/docs/`.
5. Render logs for Django/Gunicorn and Celery startup.
6. Background job status in the Django database/API.
7. Vercel deployment status for frontend build/runtime errors.

## Expected Health Responses

`/api/health/live/`:

```json
{"status":"ok"}
```

`/api/health/ready/`:

```json
{"status":"ok","database":"ok","redis":"ok"}
```

Readiness must not expose credentials, hostnames with passwords, stack traces, Redis URLs, database URLs, or provider keys.

## Safe Log Sources

- Render service logs: Django request failures, Gunicorn startup, Celery worker startup, Celery task failures, Redis connection failures.
- Vercel logs: Next.js route handler failures and frontend server errors.
- Browser console/network: client-side errors and failed proxy requests.
- Django `AIContentGeneration` records: content-plan status, attempts, sanitized error code/message.
- Django report job fields: report queue/running/completed/failed status.

## Do Not Log

- passwords
- JWTs
- cookies
- DATABASE_URL
- Redis credentials
- Groq API key
- private user content unless required to debug a specific user-authorized support case

## Common Failure Patterns

| Symptom | Likely source | First check |
| --- | --- | --- |
| Login redirects back to login | frontend cookie/proxy/auth | Vercel logs, browser network, `/api/auth/me` |
| Ready endpoint 503 database | Neon/Django database config | Render env names, Neon dashboard |
| Ready endpoint 503 Redis | Upstash/Celery Redis config | Render env names, Upstash dashboard |
| AI job stuck queued | Celery not running or broker issue | Render logs for worker process |
| AI job failed safely | Groq/provider/validator | job error code, Render logs |
| Report export is HTML | frontend proxy or backend route | browser network content type |

## Minimal Monitoring Workflow

There is no paid external error-monitoring provider in v1 staging. Use a log-based workflow:

1. Confirm health endpoints.
2. Inspect Render logs for backend/Celery errors.
3. Inspect Vercel logs for frontend route-handler errors.
4. Reproduce with a synthetic test account.
5. Record failing route, request method, status code, sanitized response, and job ID if applicable.
6. Verify no secrets are present in browser-visible errors or logs.

## Correlation

The backend returns an `X-Request-ID` response header when supplied by the client. For support investigations, add a safe request ID in test tooling and correlate it with Render logs.
