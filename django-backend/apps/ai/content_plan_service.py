import time
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError

from apps.ai.context import build_ai_context
from apps.ai.exceptions import AIValidationError
from apps.ai.models import AIContentGeneration, AIContentGenerationVersion
from apps.ai.prompts.content_plan import CONTENT_PLAN_PROMPT_VERSION, SUPPORTED_PLATFORMS, build_content_plan_prompt
from apps.ai.providers.factory import get_ai_provider
from apps.ai.validators import validate_content_plan
from apps.content_planner.models import ContentDraft, ContentVersion
from apps.teams.permissions import can_write_content
from common.utilities.access import accessible_businesses, get_owned_business


def _usage(input_tokens: int = 0, output_tokens: int = 0) -> dict[str, int]:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
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


def generate_weekly_content_plan(
    *,
    user,
    business_id: str,
    platforms: list[str],
    start_date,
    goal: str = "",
    additional_instructions: str = "",
) -> AIContentGeneration:
    business = get_owned_business(user, business_id)
    if not can_write_content(user, business):
        raise PermissionDenied("Not allowed to generate content plans for this business")
    normalized_platforms = [platform.lower() for platform in platforms]
    _validate_request(platforms=normalized_platforms, additional_instructions=additional_instructions)
    if len(goal) + len(additional_instructions) > settings.AI_MAX_REQUEST_INPUT_LENGTH:
        raise ValidationError("AI request input is too long")
    _check_usage_limits(user=user, business=business)

    context = build_ai_context(business=business)
    prompt = build_content_plan_prompt(
        context=context,
        platforms=normalized_platforms,
        start_date=start_date.isoformat(),
        goal=goal,
        additional_instructions=additional_instructions,
    )
    provider = get_ai_provider()
    record = AIContentGeneration.objects.create(
        business=business,
        user=user,
        feature_name="weekly_content_plan",
        prompt_version=CONTENT_PLAN_PROMPT_VERSION,
        objective=goal or "weekly content plan",
        platform=",".join(normalized_platforms),
        audience=business.target_audience,
        tone=business.brand_voice,
        language=context["business"]["preferred_language"],
        content_format="seven_day_plan",
        prompt={"version": CONTENT_PLAN_PROMPT_VERSION},
        input_snapshot=prompt["input_snapshot"],
        provider=provider.name,
        model=provider.model,
        generation_parameters={"platforms": normalized_platforms, "start_date": start_date.isoformat()},
        status=AIContentGeneration.Status.PENDING,
    )
    started = time.monotonic()
    try:
        result = provider.generate_structured_json(
            system=prompt["system"],
            user=prompt["user"],
            schema=prompt["schema"],
            prompt_version=prompt["prompt_version"],
        )
        if not isinstance(result.parsed_data, dict):
            raise AIValidationError("AI provider did not return an object")
        try:
            plan = validate_content_plan(result.parsed_data)
        except ValidationError as exc:
            raise AIValidationError("AI provider returned schema-invalid content") from exc
        record.generated_content = plan
        record.structured_output = plan
        record.provider = result.provider
        record.model = result.model
        record.usage = _usage(result.input_tokens, result.output_tokens)
        record.provider_request_id = result.request_id or ""
        record.generation_parameters = {
            **record.generation_parameters,
            "finish_reason": result.finish_reason,
        }
        record.latency_ms = round((time.monotonic() - started) * 1000)
        record.status = AIContentGeneration.Status.COMPLETED
        record.save()
        AIContentGenerationVersion.objects.create(
            generation=record,
            business=business,
            version_number=1,
            action="content_plan_generated",
            generated_content=plan,
        )
        return record
    except Exception as exc:
        record.status = AIContentGeneration.Status.FAILED
        record.error_type = exc.__class__.__name__
        record.latency_ms = round((time.monotonic() - started) * 1000)
        record.save(update_fields=["status", "error_type", "latency_ms"])
        raise


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
            draft = ContentDraft.objects.create(
                business=business,
                title=title,
                caption=caption,
                platform=item["platform"],
                content_type=item["content_type"],
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
