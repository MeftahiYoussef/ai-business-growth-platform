import hashlib
import json
import logging
import re
import time
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError

from apps.ai.context import build_ai_context
from apps.ai.exceptions import AIIdempotencyConflictError, AIValidationError
from apps.ai.models import AIContentGeneration, AIContentGenerationVersion
from apps.ai.prompts.content_plan import CONTENT_PLAN_PROMPT_VERSION, SUPPORTED_PLATFORMS, build_content_plan_prompt
from apps.ai.providers.factory import get_ai_provider
from apps.ai.validators import validate_content_plan
from apps.content_planner.models import ContentDraft, ContentVersion
from apps.teams.permissions import can_write_content
from common.utilities.access import accessible_businesses, get_owned_business

logger = logging.getLogger(__name__)

CONTENT_PLAN_FEATURE_NAME = "weekly_content_plan"
MAX_IDEMPOTENCY_KEY_LENGTH = 128
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def _usage(input_tokens: int | None = 0, output_tokens: int | None = 0) -> dict[str, int | None]:
    total_tokens = input_tokens + output_tokens if input_tokens is not None and output_tokens is not None else None
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _validate_request(*, platforms: list[str], additional_instructions: str) -> None:
    if not platforms:
        raise ValidationError({"platforms": ["Select at least one platform"]})
    unsupported = sorted(set(platforms) - set(SUPPORTED_PLATFORMS))
    if unsupported:
        raise ValidationError({"platforms": [f"Unsupported platforms: {', '.join(unsupported)}"]})
    if len(additional_instructions) > settings.AI_MAX_ADDITIONAL_INSTRUCTIONS_LENGTH:
        raise ValidationError({"additional_instructions": ["Additional instructions are too long"]})


def _check_usage_limits(*, user, business) -> None:
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    user_count = AIContentGeneration.objects.filter(user=user, created_at__gte=today_start).count()
    business_count = AIContentGeneration.objects.filter(business=business, created_at__gte=month_start).count()
    if user_count >= settings.AI_MAX_USER_DAILY_REQUESTS:
        raise Throttled(detail="Daily AI generation quota exceeded")
    if business_count >= settings.AI_MAX_BUSINESS_MONTHLY_REQUESTS:
        raise Throttled(detail="Monthly business AI generation quota exceeded")


def normalize_idempotency_key(raw_key: str | None) -> str:
    key = (raw_key or "").strip()
    if not key:
        return ""
    if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise ValidationError({"idempotency_key": ["Idempotency-Key is too long"]})
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise ValidationError({"idempotency_key": ["Idempotency-Key contains unsupported characters"]})
    return key


def _request_payload(*, platforms: list[str], start_date, goal: str, additional_instructions: str) -> dict[str, Any]:
    return {
        "platforms": platforms,
        "start_date": start_date.isoformat(),
        "goal": goal or "",
        "additional_instructions": additional_instructions or "",
    }


def _request_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _prepare_content_plan_generation(
    *,
    user,
    business_id: str,
    platforms: list[str],
    start_date,
    goal: str = "",
    additional_instructions: str = "",
) -> tuple[Any, list[str], dict[str, Any], str]:
    business = get_owned_business(user, business_id)
    if not can_write_content(user, business):
        raise PermissionDenied("Not allowed to generate content plans for this business")
    normalized_platforms = [platform.lower() for platform in platforms]
    _validate_request(platforms=normalized_platforms, additional_instructions=additional_instructions)
    if len(goal) + len(additional_instructions) > settings.AI_MAX_REQUEST_INPUT_LENGTH:
        raise ValidationError("AI request input is too long")
    payload = _request_payload(
        platforms=normalized_platforms,
        start_date=start_date,
        goal=goal,
        additional_instructions=additional_instructions,
    )
    return business, normalized_platforms, payload, _request_fingerprint(payload)


def _create_content_plan_record(
    *,
    business,
    user,
    normalized_platforms: list[str],
    start_date,
    goal: str,
    request_payload: dict[str, Any],
    request_fingerprint: str,
    status: str,
    idempotency_key: str = "",
) -> AIContentGeneration:
    provider = get_ai_provider()
    context = build_ai_context(business=business)
    prompt = build_content_plan_prompt(
        context=context,
        platforms=normalized_platforms,
        start_date=start_date.isoformat(),
        goal=goal,
        additional_instructions=request_payload["additional_instructions"],
    )
    return AIContentGeneration.objects.create(
        business=business,
        user=user,
        feature_name=CONTENT_PLAN_FEATURE_NAME,
        prompt_version=CONTENT_PLAN_PROMPT_VERSION,
        objective=goal or "weekly content plan",
        platform=",".join(normalized_platforms),
        audience=business.target_audience,
        tone=business.brand_voice,
        language=context["business"]["preferred_language"],
        content_format="seven_day_plan",
        prompt={"version": CONTENT_PLAN_PROMPT_VERSION},
        input_snapshot={**prompt["input_snapshot"], "request": request_payload},
        provider=provider.name,
        model=provider.model,
        generation_parameters={"platforms": normalized_platforms, "start_date": start_date.isoformat()},
        status=status,
        queued_at=timezone.now() if status == AIContentGeneration.Status.QUEUED else None,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )


def _execute_content_plan_generation(record: AIContentGeneration) -> AIContentGeneration:
    business = record.business
    payload = (record.input_snapshot or {}).get("request") or {}
    platforms = payload.get("platforms") or record.generation_parameters.get("platforms") or record.platform.split(",")
    start_date = payload.get("start_date") or record.generation_parameters.get("start_date")
    goal = payload.get("goal", record.objective)
    additional_instructions = payload.get("additional_instructions", "")
    context = build_ai_context(business=business)
    prompt = build_content_plan_prompt(
        context=context,
        platforms=platforms,
        start_date=start_date,
        goal=goal,
        additional_instructions=additional_instructions,
    )
    provider = get_ai_provider()
    started = time.monotonic()
    try:
        validation_attempts = 0
        input_tokens = output_tokens = 0
        for validation_attempt in range(2):
            validation_attempts += 1
            try:
                result = provider.generate_structured_json(
                    system=prompt["system"],
                    user=prompt["user"],
                    schema=prompt["schema"],
                    prompt_version=prompt["prompt_version"],
                )
                input_tokens += result.input_tokens
                output_tokens += result.output_tokens
                plan = validate_content_plan(result.parsed_data)
                break
            except (ValidationError, AIValidationError) as exc:
                if validation_attempt == 1:
                    raise AIValidationError("AI provider returned invalid content after regeneration") from exc
                # Regenerate from the original context; never persist or relax validation of rejected content.
                logger.warning("ai_generation_validation_retry generation_id=%s", record.id)
                prompt["system"] += (
                    " The previous response failed application validation. Regenerate the entire plan. "
                    "Follow every schema constraint, use unique day numbers 1 through 7, and require human review. "
                    "Avoid all quantitative performance claims, including percentages, multipliers, and promises "
                    "to double or triple engagement, followers, leads, revenue, or sales."
                )

        record.generated_content = plan
        record.structured_output = plan
        record.provider = result.provider
        record.model = result.model
        record.usage = _usage(input_tokens, output_tokens)
        record.provider_request_id = result.request_id or ""
        record.generation_parameters = {
            **record.generation_parameters,
            "finish_reason": result.finish_reason,
            "validation_attempts": validation_attempts,
        }
        record.latency_ms = round((time.monotonic() - started) * 1000)
        record.status = AIContentGeneration.Status.COMPLETED
        record.completed_at = timezone.now()
        record.failed_at = None
        record.error_type = ""
        record.last_error_code = ""
        record.last_error_message = ""
        record.save()
        AIContentGenerationVersion.objects.get_or_create(
            generation=record,
            version_number=1,
            defaults={
                "business": business,
                "action": "content_plan_generated",
                "generated_content": plan,
            },
        )
        logger.info(
            "ai_generation_completed generation_id=%s business_id=%s provider=%s model=%s input_tokens=%s output_tokens=%s status=%s request_id=%s finish_reason=%s",
            record.id,
            business.id,
            record.provider,
            record.model,
            record.usage["input_tokens"],
            record.usage["output_tokens"],
            record.status,
            record.provider_request_id,
            result.finish_reason or "",
        )
        return record
    except Exception as exc:
        record.status = AIContentGeneration.Status.FAILED
        record.error_type = exc.__class__.__name__
        record.last_error_code = exc.__class__.__name__
        record.last_error_message = "Content plan generation failed"
        record.failed_at = timezone.now()
        record.latency_ms = round((time.monotonic() - started) * 1000)
        record.save(update_fields=["status", "error_type", "last_error_code", "last_error_message", "failed_at", "latency_ms"])
        logger.warning(
            "ai_generation_failed generation_id=%s business_id=%s provider=%s model=%s status=%s error_type=%s",
            record.id,
            business.id,
            record.provider,
            record.model,
            record.status,
            record.error_type,
        )
        raise


def generate_weekly_content_plan(
    *,
    user,
    business_id: str,
    platforms: list[str],
    start_date,
    goal: str = "",
    additional_instructions: str = "",
) -> AIContentGeneration:
    business, normalized_platforms, request_payload, fingerprint = _prepare_content_plan_generation(
        user=user,
        business_id=business_id,
        platforms=platforms,
        start_date=start_date,
        goal=goal,
        additional_instructions=additional_instructions,
    )
    _check_usage_limits(user=user, business=business)
    record = _create_content_plan_record(
        business=business,
        user=user,
        normalized_platforms=normalized_platforms,
        start_date=start_date,
        goal=goal,
        request_payload=request_payload,
        request_fingerprint=fingerprint,
        status=AIContentGeneration.Status.PENDING,
    )
    return _execute_content_plan_generation(record)


def submit_weekly_content_plan_job(
    *,
    user,
    business_id: str,
    platforms: list[str],
    start_date,
    goal: str = "",
    additional_instructions: str = "",
    idempotency_key: str | None = None,
) -> AIContentGeneration:
    business, normalized_platforms, request_payload, fingerprint = _prepare_content_plan_generation(
        user=user,
        business_id=business_id,
        platforms=platforms,
        start_date=start_date,
        goal=goal,
        additional_instructions=additional_instructions,
    )
    key = normalize_idempotency_key(idempotency_key)
    with transaction.atomic():
        if key:
            existing = AIContentGeneration.objects.select_for_update().filter(
                business=business,
                user=user,
                feature_name=CONTENT_PLAN_FEATURE_NAME,
                idempotency_key=key,
            ).first()
            if existing:
                if existing.request_fingerprint != fingerprint:
                    raise AIIdempotencyConflictError("Idempotency-Key was already used for a different request")
                return existing
        _check_usage_limits(user=user, business=business)
        try:
            with transaction.atomic():
                record = _create_content_plan_record(
                    business=business,
                    user=user,
                    normalized_platforms=normalized_platforms,
                    start_date=start_date,
                    goal=goal,
                    request_payload=request_payload,
                    request_fingerprint=fingerprint,
                    status=AIContentGeneration.Status.QUEUED,
                    idempotency_key=key,
                )
        except IntegrityError:
            if not key:
                raise
            existing = AIContentGeneration.objects.select_for_update().get(
                business=business,
                user=user,
                feature_name=CONTENT_PLAN_FEATURE_NAME,
                idempotency_key=key,
            )
            if existing.request_fingerprint != fingerprint:
                raise AIIdempotencyConflictError("Idempotency-Key was already used for a different request")
            return existing

        def enqueue_task() -> None:
            from apps.ai.tasks import generate_content_plan_task

            async_result = generate_content_plan_task.apply_async(args=[str(record.id)])
            record.task_id = async_result.id
            AIContentGeneration.objects.filter(id=record.id).update(task_id=async_result.id)

        transaction.on_commit(enqueue_task)
        return record


def run_queued_content_plan_generation(*, generation_id: str, task_id: str = "") -> AIContentGeneration | None:
    with transaction.atomic():
        record = AIContentGeneration.objects.select_for_update().select_related("business").filter(id=generation_id).first()
        if not record:
            return None
        if record.status in {AIContentGeneration.Status.COMPLETED, AIContentGeneration.Status.CANCELLED}:
            return record
        if record.status == AIContentGeneration.Status.RUNNING:
            stale_after = timezone.now() - timedelta(seconds=settings.CELERY_TASK_TIME_LIMIT + 60)
            if record.started_at and record.started_at > stale_after:
                return record
        record.status = AIContentGeneration.Status.RUNNING
        record.started_at = record.started_at or timezone.now()
        record.failed_at = None
        record.attempt_count += 1
        if task_id and not record.task_id:
            record.task_id = task_id
        record.save(update_fields=["status", "started_at", "failed_at", "attempt_count", "task_id"])
    return _execute_content_plan_generation(record)


def mark_content_plan_generation_retrying(*, generation_id: str, exc: Exception) -> None:
    AIContentGeneration.objects.filter(id=generation_id).exclude(status=AIContentGeneration.Status.COMPLETED).update(
        status=AIContentGeneration.Status.RETRYING,
        error_type=exc.__class__.__name__,
        last_error_code=exc.__class__.__name__,
        last_error_message="Temporary AI generation failure; retrying",
        failed_at=None,
    )


def mark_content_plan_generation_failed(*, generation_id: str, exc: Exception, message: str = "Content plan generation failed") -> None:
    AIContentGeneration.objects.filter(id=generation_id).exclude(status=AIContentGeneration.Status.COMPLETED).update(
        status=AIContentGeneration.Status.FAILED,
        error_type=exc.__class__.__name__,
        last_error_code=exc.__class__.__name__,
        last_error_message=message,
        failed_at=timezone.now(),
    )


def create_drafts_from_plan(*, user, generation_id: str, item_day_numbers: list[int], edited_items: dict[str, dict[str, Any]] | None = None) -> list[ContentDraft]:
    requested_days = sorted(set(int(day) for day in item_day_numbers))
    if not requested_days:
        raise ValidationError({"item_day_numbers": ["Select at least one plan item"]})
    created: list[ContentDraft] = []
    edited_items = edited_items or {}
    with transaction.atomic():
        record = AIContentGeneration.objects.select_for_update().filter(
            id=generation_id,
            business__in=accessible_businesses(user),
            feature_name="weekly_content_plan",
        ).select_related("business").first()
        if not record:
            raise ValidationError("Content plan generation not found")
        business = record.business
        if record.status != AIContentGeneration.Status.COMPLETED:
            raise ValidationError("Only completed content plans can create drafts")
        if not can_write_content(user, business):
            raise PermissionDenied("Not allowed to create drafts for this business")
        plan = validate_content_plan(record.structured_output or record.generated_content)
        existing_links = {int(day): draft_id for day, draft_id in (record.draft_links or {}).items()}
        persisted_links = {
            int(day): str(draft_id)
            for day, draft_id in ContentDraft.objects.filter(
                source_ai_generation=record,
                source_plan_day__in=requested_days,
            ).values_list("source_plan_day", "id")
            if day is not None
        }
        existing_links.update(persisted_links)
        for item in plan["items"]:
            day = int(item["day_number"])
            if day not in requested_days or day in existing_links:
                continue
            edited = edited_items.get(str(day), {})
            title = edited.get("title") or item["title"]
            caption = edited.get("caption") or item["caption"]
            cta = edited.get("call_to_action") or item["call_to_action"]
            objective = edited.get("objective") or item["objective"]
            draft = ContentDraft.objects.create(
                business=business,
                title=title,
                caption=caption,
                platform=item["platform"],
                content_type=item["content_type"],
                objective=objective,
                hashtags=edited.get("hashtags") or item["hashtags"],
                cta=cta,
                created_by=user,
                status=ContentDraft.Status.DRAFT,
                approval_status="draft",
                source_ai_generation=record,
                source_plan_day=day,
            )
            ContentVersion.objects.create(
                draft=draft,
                business=business,
                version_number=1,
                title=draft.title,
                caption=draft.caption,
                changed_by=user,
                change_summary="Created from AI content plan",
            )
            existing_links[day] = str(draft.id)
            created.append(draft)
        record.draft_links = {str(day): draft_id for day, draft_id in existing_links.items()}
        record.save(update_fields=["draft_links"])
    return created
