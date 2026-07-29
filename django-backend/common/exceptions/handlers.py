from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _normalize_details(detail):
    if isinstance(detail, list):
        return [{"message": str(item)} for item in detail]
    if isinstance(detail, dict):
        return detail
    if detail:
        return detail
    return None


def compat_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        if isinstance(exc, Http404):
            return Response({"success": False, "message": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, PermissionDenied):
            return Response({"success": False, "message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"success": False, "message": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    message = "API request failed"
    if isinstance(exc, exceptions.ValidationError):
        message = "Validation failed"
    elif isinstance(exc, exceptions.AuthenticationFailed):
        message = "Invalid or expired token"
    elif isinstance(exc, exceptions.NotAuthenticated):
        message = "Authentication token is required"
    elif isinstance(exc, exceptions.NotFound):
        message = "Not found"
    elif isinstance(exc, exceptions.PermissionDenied):
        message = "Permission denied"
    elif isinstance(response.data, dict):
        message = str(response.data.get("detail") or response.data.get("message") or message)

    return Response(
        {"success": False, "message": message, "details": _normalize_details(response.data)},
        status=response.status_code,
    )
