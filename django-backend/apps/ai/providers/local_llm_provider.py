import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.ai.exceptions import AIConfigurationError, AIProviderError, AITimeoutError, AIValidationError

from .base import AIProviderResult, BaseAIProvider

logger = logging.getLogger(__name__)


def _safe_json_loads(value: str) -> dict[str, Any] | list[Any]:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise AIValidationError("The local model returned invalid JSON") from exc


class LocalLLMProvider(BaseAIProvider):
    """
    Experimental OpenAI-compatible local provider.

    It is intentionally not registered in the production provider factory.
    Use it only for explicit model-lab evaluation.
    """

    name = "local"

    def __init__(self) -> None:
        if not settings.LOCAL_LLM_ENABLED:
            raise AIConfigurationError("Local LLM evaluation is disabled")
        self.base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.model = settings.LOCAL_LLM_MODEL
        self.timeout_seconds = settings.LOCAL_LLM_TIMEOUT_SECONDS
        self.max_output_tokens = settings.LOCAL_LLM_MAX_OUTPUT_TOKENS

    def generate_social_content(self, prompt: dict) -> dict:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "hook": {"type": "string"},
                "caption": {"type": "string"},
                "cta": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "alternatives": {"type": "array", "items": {"type": "object"}},
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
            raise AIValidationError("The local model returned invalid social content")
        return result.parsed_data

    def generate_structured_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        prompt_version: str,
    ) -> AIProviderResult:
        result = self._chat_completion(
            messages=[
                {"role": "system", "content": f"{system} Return valid JSON only."},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": prompt_version.replace("-", "_"),
                    "schema": schema,
                },
            },
            temperature=0.2,
        )
        if not result.content.strip():
            raise AIValidationError("The local model returned an empty response")
        parsed = _safe_json_loads(result.content)
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

    def generate_text(self, *, system: str, user: str, temperature: float = 0.2) -> AIProviderResult:
        return self._chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=None,
            temperature=temperature,
        )

    def _chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None,
        temperature: float,
    ) -> AIProviderResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        started = time.monotonic()
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except TimeoutError as exc:
            logger.warning("Local LLM request timed out")
            raise AITimeoutError("The local model timed out") from exc
        except HTTPError as exc:
            logger.warning("Local LLM server returned status=%s", exc.code)
            raise AIProviderError("The local model request failed") from exc
        except URLError as exc:
            logger.warning("Local LLM server is unavailable")
            raise AIProviderError("The local model is unavailable") from exc
        except OSError as exc:
            logger.warning("Local LLM connection failed")
            raise AIProviderError("The local model request failed") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AIValidationError("The local model server returned malformed JSON") from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices:
            raise AIValidationError("The local model server returned no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        if not isinstance(content, str) or not content.strip():
            raise AIValidationError("The local model returned an empty response")

        usage = data.get("usage") or {}
        logger.info("Local LLM request completed in %sms", round((time.monotonic() - started) * 1000))
        return AIProviderResult(
            content=content,
            parsed_data=None,
            provider=self.name,
            model=str(data.get("model") or self.model),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            request_id=data.get("id"),
            finish_reason=choice.get("finish_reason"),
        )
