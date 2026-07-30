import logging

from celery import shared_task

from apps.ai.content_plan_service import (
    mark_content_plan_generation_failed,
    mark_content_plan_generation_retrying,
    run_queued_content_plan_generation,
)
from apps.ai.exceptions import AIProviderError, AIRateLimitError, AITimeoutError

logger = logging.getLogger(__name__)

TRANSIENT_AI_EXCEPTIONS = (AITimeoutError, AIRateLimitError, AIProviderError)


@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    ignore_result=False,
)
def generate_content_plan_task(self, generation_id: str) -> str:
    task_id = getattr(self.request, "id", "") or ""
    try:
        record = run_queued_content_plan_generation(generation_id=generation_id, task_id=task_id)
    except TRANSIENT_AI_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            mark_content_plan_generation_failed(generation_id=generation_id, exc=exc, message="AI provider is temporarily unavailable")
            logger.warning("ai_generation_retry_exhausted generation_id=%s error_type=%s", generation_id, exc.__class__.__name__)
            return generation_id
        mark_content_plan_generation_retrying(generation_id=generation_id, exc=exc)
        logger.warning(
            "ai_generation_retrying generation_id=%s retry=%s error_type=%s",
            generation_id,
            self.request.retries + 1,
            exc.__class__.__name__,
        )
        raise self.retry(exc=exc)
    except Exception as exc:
        mark_content_plan_generation_failed(generation_id=generation_id, exc=exc)
        logger.warning("ai_generation_failed_permanent generation_id=%s error_type=%s", generation_id, exc.__class__.__name__)
        return generation_id
    return str(record.id) if record else generation_id
