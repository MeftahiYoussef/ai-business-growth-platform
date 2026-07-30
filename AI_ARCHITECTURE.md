# AI Architecture

## Provider

Groq is currently the only enabled concrete AI provider.

The backend keeps the provider abstraction in `apps.ai.providers.base` so future providers can be added without changing the content-plan service. The only concrete provider is:

- `groq`: implemented in `apps.ai.providers.groq_provider` using the official Groq Python SDK.

Provider selection remains backend-only through `AI_PROVIDER`, but only `groq` is accepted. Unsupported values raise `AIConfigurationError`.

## Configuration

```env
AI_PROVIDER=groq
GROQ_API_KEY=
GROQ_DEFAULT_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=60
GROQ_MAX_RETRIES=2
GROQ_MAX_OUTPUT_TOKENS=4000

AI_MAX_USER_DAILY_REQUESTS=20
AI_MAX_BUSINESS_MONTHLY_REQUESTS=500
AI_MAX_REQUEST_INPUT_LENGTH=4000
AI_MAX_ADDITIONAL_INSTRUCTIONS_LENGTH=1200
AI_ASYNC_CONTENT_PLAN_ENABLED=false
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

`openai/gpt-oss-20b` is a Groq model identifier in this project. It does not enable any separate non-Groq provider.

The Groq key belongs only in `django-backend/.env`. It must never be committed or exposed to the frontend. The browser always calls Django, and Django calls Groq.

## Prompt Architecture

Weekly content plans use `apps.ai.prompts.content_plan.CONTENT_PLAN_PROMPT_VERSION`.

The prompt instructs the model to:

- Use only provided business, competitor, trend, and analytics context.
- Never fabricate analytics values.
- Mark unavailable information as unavailable.
- Respect brand restrictions.
- Return exactly seven distinct items.
- Require human review on every generated item.
- Return JSON only.

## Structured Output

`POST /api/ai/content-plans/generate/` uses non-streaming Groq Chat Completions with strict structured JSON output. Non-streaming is intentional because the app needs one complete JSON object before validation and persistence.

The asynchronous queue endpoint, `POST /api/ai/content-plans/queue/`, validates the same request and returns `202 Accepted` with a durable generation id. The Celery task receives only that generation UUID, then calls the same prompt/provider/validator flow in the worker.

Django validates the provider output again in Python. The schema requires:

- A summary, primary goal, and target audience.
- Exactly seven content items.
- Day numbers 1 through 7.
- Supported platforms/content types/objectives only.
- Non-empty captions with length limits.
- Hashtag limits.
- `requires_human_review: true`.

## Generation History

`AIContentGeneration` stores:

- Feature name.
- Prompt version.
- Sanitized input snapshot.
- Prompt metadata.
- Generated content.
- Structured output.
- Provider and model.
- Parameters.
- Token usage metadata.
- Status, error type, provider request id, latency, and draft links.
- Queue metadata: task id, queued/running/completed/failed timestamps, attempt count, sanitized last error, idempotency key, and request fingerprint.
- Feedback.

`AIContentGenerationVersion` stores old versions so regeneration does not overwrite history.

## Content-Plan Flow

1. The authenticated user requests a seven-day plan for a business.
2. Django validates business membership and content-write permissions.
3. Simple database quotas are checked.
4. A minimal authorized AI context is built from business, trends, competitors, competitor posts, and calculated analytics.
5. In synchronous mode, Django calls Groq in the request path. In asynchronous mode, Django stores a queued generation and enqueues Celery after transaction commit.
6. Groq returns structured JSON.
7. Django validates the plan and saves generation history/usage.
8. The user explicitly selects items to create drafts.
9. Drafts remain in `draft` status and must pass the existing review/approval workflow.

Async status values are `queued`, `running`, `retrying`, `completed`, `failed`, and `cancelled`. The status endpoint returns only authorized business data and sanitized failure messages.

## Testing

Automated tests mock the Groq SDK and do not make provider network requests. Real Groq testing requires manually placing a valid key in `django-backend/.env`.

CI uses a placeholder Groq key, mocked provider responses, and Celery eager mode for standard tests. A separate opt-in Redis integration test starts a real Celery worker against local Redis and still uses a mocked provider. The frontend must not define `NEXT_PUBLIC_GROQ_API_KEY`; all AI calls route through Django.

## Persistence and Safety

Weekly plan records store structured JSON in `AIContentGeneration.structured_output`, token usage in `usage`, provider metadata, prompt version, status, and draft links. Draft conversion is explicit and uses a database transaction. A database uniqueness constraint on `(source_ai_generation, source_plan_day)` prevents duplicate drafts for the same generated item even under concurrent conversion attempts.

The generation service enforces daily user quota and monthly business quota with database count queries before calling Groq. Failed provider calls are recorded safely and API responses remain sanitized.

The queue endpoint supports `Idempotency-Key`, scoped by authenticated user and business. A database uniqueness constraint prevents duplicate queued generations for the same scoped key; conflicting payload reuse returns `409`.

## Current Limitations

- No fine-tuning.
- No knowledge-base retrieval or embeddings yet.
- No autonomous publishing.
- No provider-cost pricing table beyond token usage storage.
- Live Railway Redis and Celery worker services are prepared but not deployed until no-cost/plan approval is explicit.
