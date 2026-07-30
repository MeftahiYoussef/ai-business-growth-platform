class AIError(Exception):
    status_code = 502


class AIConfigurationError(AIError):
    status_code = 500


class AIProviderError(AIError):
    status_code = 502


class AIValidationError(AIError):
    status_code = 502


class AIRateLimitError(AIError):
    status_code = 429


class AITimeoutError(AIError):
    status_code = 504


class AIIdempotencyConflictError(AIError):
    status_code = 409
