from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import generate_strategy
from apps.trends.models import Trend
from common.utilities.access import get_owned_business

from .models import Strategy
from .serializers import StrategySerializer


class StrategyView(APIView):
    def get(self, request):
        business = get_owned_business(request.user)
        strategy = Strategy.objects.filter(business=business).order_by("-created_at").first()
        return Response({"success": True, "data": StrategySerializer(strategy).data if strategy else None})


class GenerateStrategyView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        trends = list(Trend.objects.filter(business=business).order_by("-created_at")[:5])
        strategy = Strategy.objects.create(**generate_strategy(business, trends))
        return Response({"success": True, "data": StrategySerializer(strategy).data}, status=status.HTTP_201_CREATED)
