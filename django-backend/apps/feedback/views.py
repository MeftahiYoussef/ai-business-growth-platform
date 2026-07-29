from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content_ideas.models import ContentIdea
from common.utilities.access import get_owned_business
from common.utilities.ids import id_filter

from .models import Feedback
from .serializers import FeedbackSerializer


class FeedbackView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        if "liked" not in request.data:
            raise ValidationError({"liked": ["liked must be true or false"]})
        idea = ContentIdea.objects.filter(id_filter(request.data.get("contentIdeaId")), business=business).first()
        if not idea:
            raise NotFound("Content idea not found")
        feedback = Feedback.objects.create(
            business=business,
            content_idea=idea,
            liked=bool(request.data.get("liked")),
            comment=request.data.get("comment") or "",
        )
        return Response({"success": True, "data": FeedbackSerializer(feedback).data}, status=status.HTTP_201_CREATED)
