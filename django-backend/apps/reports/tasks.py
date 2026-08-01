import logging

from celery import shared_task

from apps.ai.exceptions import AIProviderError, AIRateLimitError, AITimeoutError

from .services import mark_report_job_failed, mark_report_job_retrying, run_business_report_job

logger = logging.getLogger(__name__)

TRANSIENT_REPORT_EXCEPTIONS = (AITimeoutError, AIRateLimitError, AIProviderError)


@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    ignore_result=False,
)
def generate_business_report_task(self, job_id: str) -> str:
    task_id = getattr(self.request, "id", "") or ""
    try:
        job = run_business_report_job(job_id=job_id, task_id=task_id)
    except TRANSIENT_REPORT_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            mark_report_job_failed(job_id=job_id, exc=exc, message="Report recommendations are temporarily unavailable")
            logger.warning("report_generation_retry_exhausted job_id=%s error_type=%s", job_id, exc.__class__.__name__)
            return job_id
        mark_report_job_retrying(job_id=job_id, exc=exc)
        logger.warning("report_generation_retrying job_id=%s retry=%s error_type=%s", job_id, self.request.retries + 1, exc.__class__.__name__)
        raise self.retry(exc=exc)
    except Exception as exc:
        mark_report_job_failed(job_id=job_id, exc=exc)
        logger.warning("report_generation_failed_permanent job_id=%s error_type=%s", job_id, exc.__class__.__name__)
        return job_id
    return str(job.id) if job else job_id
