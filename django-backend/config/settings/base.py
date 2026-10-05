import os
import ssl
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: str = "false") -> bool:
    return env(name, default).lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: str) -> int:
    return int(env(name, default))


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = env(name)
        if value:
            return value
    return default


def required_database_env(*names: str) -> str:
    value = first_env(*names)
    if value:
        return value
    joined = " or ".join(names)
    raise RuntimeError(f"PostgreSQL is selected but {joined} is not configured")


def required_env(name: str) -> str:
    value = env(name)
    if not value:
        raise RuntimeError(f"{name} must be configured")
    return value


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "dev-only-change-me-64-char-minimum-local-secret-not-for-production-2026",
)
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.accounts",
    "apps.businesses",
    "apps.competitors",
    "apps.competitor_posts",
    "apps.trends",
    "apps.content_ideas",
    "apps.strategies",
    "apps.analyses",
    "apps.feedback",
    "apps.ai",
    "apps.teams",
    "apps.integrations",
    "apps.content_planner",
    "apps.analytics",
    "apps.reports",
    "apps.notifications",
    "common",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.RequestLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]},
    }
]

USE_SQLITE = env_bool("USE_SQLITE")


def database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must use postgres:// or postgresql://")
    query = parse_qs(parsed.query)
    options = {}
    sslmode = query.get("sslmode", [first_env("DATABASE_SSLMODE", "POSTGRES_SSLMODE", default="require")])[0]
    if sslmode:
        options["sslmode"] = sslmode
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": env_int("DATABASE_CONN_MAX_AGE", first_env("POSTGRES_CONN_MAX_AGE", default="60")),
        "OPTIONS": options,
    }


def build_database_config() -> dict[str, dict[str, object]]:
    if USE_SQLITE:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(BASE_DIR / "db.sqlite3"),
            }
        }
    database_url = first_env("DATABASE_URL", "POSTGRES_URL")
    if database_url:
        return {"default": database_from_url(database_url)}

    options = {}
    sslmode = first_env("DATABASE_SSLMODE", "POSTGRES_SSLMODE", default="prefer")
    if sslmode:
        options["sslmode"] = sslmode

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": required_database_env("DATABASE_NAME", "POSTGRES_DB"),
            "USER": required_database_env("DATABASE_USER", "POSTGRES_USER"),
            "PASSWORD": first_env("DATABASE_PASSWORD", "POSTGRES_PASSWORD"),
            "HOST": required_database_env("DATABASE_HOST", "POSTGRES_HOST"),
            "PORT": required_database_env("DATABASE_PORT", "POSTGRES_PORT"),
            "CONN_MAX_AGE": env_int("DATABASE_CONN_MAX_AGE", first_env("POSTGRES_CONN_MAX_AGE", default="60")),
            "OPTIONS": options,
        }
    }


DATABASES = build_database_config()

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "common.authentication.hashers.NodeBcryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.compat.PageNumberLimitPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "common.exceptions.handlers.compat_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "common.openapi.ProjectAutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("ACCESS_TOKEN_LIFETIME_MINUTES", "10080"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("REFRESH_TOKEN_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ["accept", "authorization", "content-type", "origin", "user-agent", "x-csrftoken", "x-requested-with"]

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SPECTACULAR_SETTINGS = {
    "TITLE": "AI Business Growth & Trend Intelligence API",
    "DESCRIPTION": "Django REST API compatible with the original Express backend.",
    "VERSION": "1.0.0",
}

MONGODB_URI = env("MONGODB_URI", "mongodb://127.0.0.1:27017/trend_intelligence")

AI_PROVIDER = env("AI_PROVIDER", "groq").lower()
GROQ_API_KEY = env("GROQ_API_KEY", "")
GROQ_DEFAULT_MODEL = env("GROQ_DEFAULT_MODEL", "openai/gpt-oss-20b")
GROQ_TIMEOUT_SECONDS = env_int("GROQ_TIMEOUT_SECONDS", "60")
GROQ_MAX_RETRIES = env_int("GROQ_MAX_RETRIES", "2")
GROQ_MAX_OUTPUT_TOKENS = env_int("GROQ_MAX_OUTPUT_TOKENS", "4000")
AI_MAX_USER_DAILY_REQUESTS = env_int("AI_MAX_USER_DAILY_REQUESTS", "20")
AI_MAX_BUSINESS_MONTHLY_REQUESTS = env_int("AI_MAX_BUSINESS_MONTHLY_REQUESTS", "500")
AI_MAX_REQUEST_INPUT_LENGTH = env_int("AI_MAX_REQUEST_INPUT_LENGTH", "4000")
AI_MAX_ADDITIONAL_INSTRUCTIONS_LENGTH = env_int("AI_MAX_ADDITIONAL_INSTRUCTIONS_LENGTH", "1200")
AI_ASYNC_CONTENT_PLAN_ENABLED = env_bool("AI_ASYNC_CONTENT_PLAN_ENABLED")
ASYNC_REPORTS_ENABLED = env_bool("ASYNC_REPORTS_ENABLED")
REPORT_AI_RECOMMENDATIONS_ENABLED = env_bool("REPORT_AI_RECOMMENDATIONS_ENABLED")
REPORT_MAX_PERIOD_DAYS = env_int("REPORT_MAX_PERIOD_DAYS", "366")

SMALL_LLM_EXPERIMENT_ENABLED = env_bool("SMALL_LLM_EXPERIMENT_ENABLED")
LOCAL_LLM_ENABLED = env_bool("LOCAL_LLM_ENABLED")
LOCAL_LLM_BASE_URL = env("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_LLM_MODEL = env("LOCAL_LLM_MODEL", "Qwen/Qwen3-1.7B")
LOCAL_LLM_TIMEOUT_SECONDS = env_int("LOCAL_LLM_TIMEOUT_SECONDS", "120")
LOCAL_LLM_MAX_OUTPUT_TOKENS = env_int("LOCAL_LLM_MAX_OUTPUT_TOKENS", "2048")
LOCAL_LLM_DISABLE_THINKING = env_bool("LOCAL_LLM_DISABLE_THINKING", "true")

REDIS_URL = env("REDIS_URL", "")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", REDIS_URL or "redis://localhost:6379/1")
if CELERY_BROKER_URL.startswith("rediss://"):
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
if CELERY_RESULT_BACKEND.startswith("rediss://"):
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = env_bool("CELERY_TASK_EAGER_PROPAGATES", "true")
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", "180")
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", "150")
CELERY_WORKER_PREFETCH_MULTIPLIER = env_int("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")
CELERY_TASK_ACKS_LATE = env_bool("CELERY_TASK_ACKS_LATE", "true")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = env_bool("CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP", "true")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_ENABLE_UTC = True
CELERY_RESULT_EXPIRES = env_int("CELERY_RESULT_EXPIRES_SECONDS", "86400")
