from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services import generate_business_analysis
from apps.trends.models import Trend
from common.utilities.access import get_owned_business

from .models import BusinessAnalysis
from .serializers import BusinessAnalysisSerializer


class AnalysisView(APIView):
    def get(self, request):
        business = get_owned_business(request.user)
        analysis = BusinessAnalysis.objects.filter(business=business).order_by("-created_at").first()
        return Response({"success": True, "data": BusinessAnalysisSerializer(analysis).data if analysis else None})


class GenerateAnalysisView(APIView):
    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        trends = list(Trend.objects.filter(business=business).order_by("-created_at")[:5])
        analysis = BusinessAnalysis.objects.create(**generate_business_analysis(business, trends))
        return Response({"success": True, "data": BusinessAnalysisSerializer(analysis).data}, status=status.HTTP_201_CREATED)
