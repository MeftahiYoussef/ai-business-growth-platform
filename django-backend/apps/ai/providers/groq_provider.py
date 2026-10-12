import json
import logging
import time
from typing import Any

from django.conf import settings
from groq import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    Groq,
    RateLimitError,
)

from apps.ai.exceptions import AIProviderError, AIRateLimitError, AITimeoutError, AIValidationError

from .base import AIProviderResult, BaseAIProvider

logger = logging.getLogger(__name__)


def _is_json_schema_validation_error(exc: APIStatusError) -> bool:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("code") == "json_validate_failed":
            return True
    return "json_validate_failed" in str(exc)


class GroqProvider(BaseAIProvider):
    name = "groq"

    def __init__(self) -> None:
        self.model = settings.GROQ_DEFAULT_MODEL
        self.client = Groq(
            api_key=settings.GROQ_API_KEY,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
            max_retries=settings.GROQ_MAX_RETRIES,
        )

    def generate_text(self, *, system: str, user: str) -> AIProviderResult:
        return self._chat_completion(
            system=system,
            user=user,
            response_format=None,
        )

    def generate_social_content(self, prompt: dict) -> dict:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "hook": {"type": "string"},
                "caption": {"type": "string"},
                "cta": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "alternatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"hook": {"type": "string"}, "angle": {"type": "string"}},
                        "required": ["hook", "angle"],
                    },
                },
                "imagePrompt": {"type": "string"},
            },
            "required": ["hook", "caption", "cta", "hashtags", "alternatives", "imagePrompt"],
        }
        result = self.generate_structured_json(
            system="You generate concise social media content. Return JSON only.",
            user=json.dumps(prompt, ensure_ascii=True),
            schema=schema,
            prompt_version="studio-v1",
        )
        if not isinstance(result.parsed_data, dict):
            raise AIValidationError("Groq returned invalid social content")
        return result.parsed_data

    def generate_structured_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        prompt_version: str,
    ) -> AIProviderResult:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": prompt_version.replace("-", "_"),
                "strict": True,
                "schema": schema,
            },
        }
        result = self._chat_completion(system=system, user=user, response_format=response_format)
        if not result.content.strip():
            raise AIValidationError("The AI provider returned an empty response")
        try:
            parsed = json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise AIValidationError("The AI provider returned invalid JSON") from exc
        return AIProviderResult(
            content=result.content,
            parsed_data=parsed,
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            request_id=result.request_id,
            finish_reason=result.finish_reason,
        )

    def _chat_completion(self, *, system: str, user: str, response_format: dict[str, Any] | None) -> AIProviderResult:
        started = time.monotonic()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6,
            "top_p": 0.95,
            "max_completion_tokens": settings.GROQ_MAX_OUTPUT_TOKENS,
            "stream": False,
        }
        if "gpt-oss" in self.model:
            kwargs["reasoning_effort"] = "medium"
        if response_format is not None:
            kwargs["response_format"] = response_format

        attempts = [kwargs]
        response = None
        for attempt_index, attempt_kwargs in enumerate(attempts):
            try:
                response = self.client.chat.completions.create(**attempt_kwargs)
                break
            except APITimeoutError as exc:
                logger.warning("Groq request timed out")
                raise AITimeoutError("The AI provider timed out") from exc
            except RateLimitError as exc:
                logger.warning("Groq rate limit reached")
                raise AIRateLimitError("The AI provider rate limit was reached") from exc
            except AuthenticationError as exc:
                logger.warning("Groq authentication failed")
                raise AIProviderError("The AI provider request failed") from exc
            except APIStatusError as exc:
                status_code = getattr(exc, "status_code", None)
                if (
                    response_format is not None
                    and attempt_index == 0
                    and status_code == 400
                    and _is_json_schema_validation_error(exc)
                ):
                    retry_kwargs = {**kwargs, "temperature": 0.2}
                    retry_kwargs["messages"] = [
                        {
                            "role": "system",
                            "content": (
                                f"{system} The JSON Schema is strict. Satisfy every required field, enum, const, "
                                "minItems and maxItems rule exactly."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"{user}\n\nRegenerate JSON for the same request. "
                                "Follow the supplied JSON Schema exactly, including array item counts, enum values, "
                                "required fields, const values, and additionalProperties=false."
                            ),
                        },
                    ]
                    if "reasoning_effort" in retry_kwargs:
                        retry_kwargs["reasoning_effort"] = "low"
                    attempts.append(retry_kwargs)
                    logger.warning("Groq structured response failed JSON schema validation; retrying once")
                    continue
                logger.warning("Groq provider error status=%s", status_code)
                raise AIProviderError("The AI provider request failed") from exc
            except (APIConnectionError, APIError) as exc:
                status_code = getattr(exc, "status_code", None)
                logger.warning("Groq provider error status=%s", status_code)
                raise AIProviderError("The AI provider request failed") from exc
            except Exception as exc:
                logger.exception("Unexpected Groq provider failure")
                raise AIProviderError("The AI provider request failed") from exc

        if response is None:
            raise AIProviderError("The AI provider request failed")

        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        content = getattr(message, "content", "") or ""
        if not content:
            raise AIValidationError("The AI provider returned an empty response")
        usage = getattr(response, "usage", None)
        model = getattr(response, "model", None) or self.model
        request_id = getattr(response, "id", None)
        finish_reason = getattr(choice, "finish_reason", None)
        logger.info("Groq structured request completed in %sms", round((time.monotonic() - started) * 1000))
        return AIProviderResult(
            content=content,
            parsed_data=None,
            provider=self.name,
            model=model,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            request_id=request_id,
            finish_reason=finish_reason,
        )
