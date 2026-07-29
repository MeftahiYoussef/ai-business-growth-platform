from rest_framework import serializers

from common.serializers import MongoCompatMixin, dt
from common.utilities.ids import external_id

from .models import Feedback


class FeedbackSerializer(MongoCompatMixin, serializers.ModelSerializer):
    _id = serializers.SerializerMethodField()
    businessId = serializers.SerializerMethodField()
    contentIdeaId = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = ["_id", "businessId", "contentIdeaId", "liked", "comment", "createdAt"]

    def get_businessId(self, obj):
        return external_id(obj.business)

    def get_contentIdeaId(self, obj):
        return external_id(obj.content_idea)

    def get_createdAt(self, obj):
        return dt(obj.created_at)
