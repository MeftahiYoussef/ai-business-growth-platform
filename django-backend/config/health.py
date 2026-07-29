from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

HEALTH_RESPONSE = {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}


@extend_schema(responses={200: OpenApiResponse(response=HEALTH_RESPONSE, description="Application process is running")})
@api_view(["GET"])
@permission_classes([AllowAny])
def live(_request):
    return Response({"status": "ok"})


@extend_schema(
    responses={
        200: OpenApiResponse(response=HEALTH_RESPONSE, description="Database is reachable"),
        503: OpenApiResponse(response=HEALTH_RESPONSE, description="Database is not reachable"),
    }
)
@api_view(["GET"])
@permission_classes([AllowAny])
def ready(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return Response({"status": "error"}, status=503)
    return Response({"status": "ok"})
