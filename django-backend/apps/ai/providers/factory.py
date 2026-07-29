from django.conf import settings

from apps.ai.exceptions import AIConfigurationError

from .groq_provider import GroqProvider

GROQ_KEY_PLACEHOLDER = "PASTE_YOUR_NEW_GROQ_KEY_HERE"


def _valid_groq_key(value: str) -> bool:
    return bool(value and value.strip() and value.strip() != GROQ_KEY_PLACEHOLDER)


def get_ai_provider():
    provider = settings.AI_PROVIDER.lower().strip()
    if provider == "groq":
        if not _valid_groq_key(settings.GROQ_API_KEY):
            raise AIConfigurationError("Groq provider is enabled but GROQ_API_KEY is not configured")
        return GroqProvider()
    raise AIConfigurationError(f"Unsupported AI provider: {provider}. Only 'groq' is supported.")
