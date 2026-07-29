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
- Feedback.

`AIContentGenerationVersion` stores old versions so regeneration does not overwrite history.

## Content-Plan Flow

1. The authenticated user requests a seven-day plan for a business.
2. Django validates business membership and content-write permissions.
3. Simple database quotas are checked.
4. A minimal authorized AI context is built from business, trends, competitors, competitor posts, and calculated analytics.
5. Groq returns structured JSON.
6. Django validates the plan and saves generation history/usage.
7. The user explicitly selects items to create drafts.
8. Drafts remain in `draft` status and must pass the existing review/approval workflow.

## Testing

Automated tests mock the Groq SDK and do not make network requests. Real Groq testing requires manually placing a valid key in `django-backend/.env`.

CI uses a placeholder Groq key and mocked provider responses. The frontend must not define `NEXT_PUBLIC_GROQ_API_KEY`; all AI calls route through Django.

## Persistence and Safety

Weekly plan records store structured JSON in `AIContentGeneration.structured_output`, token usage in `usage`, provider metadata, prompt version, status, and draft links. Draft conversion is explicit and uses a database transaction. A database uniqueness constraint on `(source_ai_generation, source_plan_day)` prevents duplicate drafts for the same generated item even under concurrent conversion attempts.

The generation service enforces daily user quota and monthly business quota with database count queries before calling Groq. Failed provider calls are recorded safely and API responses remain sanitized.

## Current Limitations

- No fine-tuning.
- No knowledge-base retrieval or embeddings yet.
- No Celery/Redis background generation in this task.
- No autonomous publishing.
- No provider-cost pricing table beyond token usage storage.
- No background retry queue; generation and draft conversion remain synchronous.
