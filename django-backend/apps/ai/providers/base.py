from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AIProviderResult:
    content: str
    parsed_data: dict[str, Any] | list[Any] | None
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    request_id: str | None = None
    finish_reason: str | None = None


class BaseAIProvider(ABC):
    name = "base"
    model = "base"

    @abstractmethod
    def generate_social_content(self, prompt: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def generate_structured_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        prompt_version: str,
    ) -> AIProviderResult:
        raise NotImplementedError
