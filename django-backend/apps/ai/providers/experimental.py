from .local_llm_provider import LocalLLMProvider


def get_experimental_small_llm_provider() -> LocalLLMProvider:
    """
    Return the explicitly enabled local provider for model-lab evaluation.

    This is separate from get_ai_provider() so production cannot silently
    fall back from Groq to a local model.
    """
    return LocalLLMProvider()
