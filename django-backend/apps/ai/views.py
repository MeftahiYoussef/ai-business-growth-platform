from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.content_plan_service import create_drafts_from_plan, generate_weekly_content_plan
from apps.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
)
from apps.content_planner.serializers import ContentDraftSerializer
from common.utilities.access import get_owned_business

from .models import AIContentGeneration, AIContentGenerationVersion
from .providers.factory import get_ai_provider
from .serializers import (
    AIContentGenerationSerializer,
    AIContentGenerationVersionSerializer,
    ContentPlanCreateDraftsRequestSerializer,
    ContentPlanGenerateRequestSerializer,
    ContentPlanGenerateResponseSerializer,
)


class AIStudioGenerateView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        provider = get_ai_provider()
        prompt = {
            **request.data,
            "businessName": business.name,
            "brandVoice": business.brand_voice,
            "productOrService": request.data.get("productOrService") or business.product_or_service,
        }
        generated = provider.generate_social_content(prompt)
        record = AIContentGeneration.objects.create(
            business=business,
            user=request.user,
            objective=request.data.get("objective") or "grow awareness",
            platform=request.data.get("platform") or "LinkedIn",
            audience=request.data.get("audience") or business.target_audience,
            tone=request.data.get("tone") or business.brand_voice,
            language=request.data.get("language") or "English",
            content_format=request.data.get("contentFormat") or "post",
            prompt=prompt,
            generated_content=generated,
            provider=provider.name,
            generation_parameters={"provider": provider.name},
            usage={"tokens": 0, "cost": 0},
        )
        AIContentGenerationVersion.objects.create(
            generation=record,
            business=business,
            version_number=1,
            action="initial",
            generated_content=generated,
        )
        return Response({"success": True, "data": AIContentGenerationSerializer(record).data}, status=status.HTTP_201_CREATED)


class AIStudioHistoryView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId") or request.query_params.get("business_id"))
        rows = AIContentGeneration.objects.filter(business=business).order_by("-created_at")[:50]
        return Response({"success": True, "data": AIContentGenerationSerializer(rows, many=True).data})


class AIStudioActionView(APIView):
    def post(self, request, generation_id):
        business = get_owned_business(request.user)
        record = AIContentGeneration.objects.filter(id=generation_id, business=business).first()
        if not record:
            return Response({"success": False, "message": "Generation not found"}, status=404)
        action = request.data.get("action") or "regenerate"
        provider = get_ai_provider()
        prompt = {**record.prompt, "editingAction": action, "additionalInstructions": request.data.get("instructions", "")}
        generated = provider.generate_social_content(prompt)
        version = record.versions.count() + 1
        record.generated_content = generated
        record.prompt = prompt
        record.save(update_fields=["generated_content", "prompt"])
        AIContentGenerationVersion.objects.create(
            generation=record, business=business, version_number=version, action=action, generated_content=generated,
        )
        return Response({"success": True, "data": AIContentGenerationSerializer(record).data})


class AIStudioVersionsView(APIView):
    def get(self, request, generation_id):
        business = get_owned_business(request.user)
        record = AIContentGeneration.objects.filter(id=generation_id, business=business).first()
        if not record:
            return Response({"success": False, "message": "Generation not found"}, status=404)
        return Response({"success": True, "data": AIContentGenerationVersionSerializer(record.versions.order_by("-version_number"), many=True).data})


def _ai_error_response(exc):
    if isinstance(exc, AIRateLimitError):
        return Response({"success": False, "message": str(exc)}, status=429)
    if isinstance(exc, AITimeoutError):
        return Response({"success": False, "message": str(exc)}, status=504)
    if isinstance(exc, AIConfigurationError):
        return Response({"success": False, "message": "AI provider is not configured"}, status=500)
    if isinstance(exc, AIValidationError):
        return Response({"success": False, "message": "AI provider returned invalid content"}, status=502)
    if isinstance(exc, AIProviderError):
        return Response({"success": False, "message": "AI provider request failed"}, status=502)
    raise exc


class ContentPlanGenerateView(APIView):
    @extend_schema(
        request=ContentPlanGenerateRequestSerializer,
        responses={201: ContentPlanGenerateResponseSerializer},
        operation_id="content_plan_generate",
    )
    def post(self, request):
        serializer = ContentPlanGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            record = generate_weekly_content_plan(
                user=request.user,
                business_id=data["business_id"],
                platforms=data["platforms"],
                start_date=data["start_date"],
                goal=data.get("goal", ""),
                additional_instructions=data.get("additional_instructions", ""),
            )
        except Throttled:
            raise
        except ValidationError:
            raise
        except (AIConfigurationError, AIProviderError, AIRateLimitError, AITimeoutError, AIValidationError) as exc:
            return _ai_error_response(exc)
        return Response({
            "success": True,
            "id": str(record.id),
            "status": record.status,
            "provider": record.provider,
            "model": record.model,
            "prompt_version": record.prompt_version,
            "plan": record.structured_output,
            "usage": {
                "input_tokens": record.usage.get("input_tokens", 0),
                "output_tokens": record.usage.get("output_tokens", 0),
            },
            "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
            "data": AIContentGenerationSerializer(record).data,
        }, status=status.HTTP_201_CREATED)


class ContentPlanCreateDraftsView(APIView):
    @extend_schema(
        request=ContentPlanCreateDraftsRequestSerializer,
        responses={201: ContentDraftSerializer(many=True)},
        operation_id="content_plan_create_drafts",
    )
    def post(self, request, generation_id):
        serializer = ContentPlanCreateDraftsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        drafts = create_drafts_from_plan(
            user=request.user,
            generation_id=generation_id,
            item_day_numbers=serializer.validated_data["item_day_numbers"],
            edited_items=serializer.validated_data.get("edited_items", {}),
        )
        return Response({"success": True, "data": ContentDraftSerializer(drafts, many=True).data}, status=status.HTTP_201_CREATED)
