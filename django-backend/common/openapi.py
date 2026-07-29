from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_serializer_context
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView


class GenericJSONResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(required=False)
    message = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)


class ProjectAutoSchema(AutoSchema):
    def _get_serializer(self):
        view = self.view
        context = build_serializer_context(view)
        try:
            if isinstance(view, GenericAPIView):
                if view.__class__.get_serializer == GenericAPIView.get_serializer:
                    return view.get_serializer_class()(context=context)
                return view.get_serializer(context=context)
            if isinstance(view, APIView):
                if callable(getattr(view, "get_serializer", None)):
                    return view.get_serializer(context=context)
                if callable(getattr(view, "get_serializer_class", None)):
                    return view.get_serializer_class()(context=context)
                if hasattr(view, "serializer_class"):
                    serializer_class = view.serializer_class
                    return serializer_class(context=context) if isinstance(serializer_class, type) else serializer_class
                return GenericJSONResponseSerializer(context=context)
            return GenericJSONResponseSerializer(context=context)
        except Exception:
            return GenericJSONResponseSerializer(context=context)
