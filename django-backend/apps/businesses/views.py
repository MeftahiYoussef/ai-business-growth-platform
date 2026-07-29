from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.teams.models import ActivityLog, BusinessMember
from common.utilities.access import accessible_businesses, get_owned_business
from common.utilities.ids import id_filter

from .serializers import BusinessSerializer


class BusinessCollectionView(APIView):
    def post(self, request):
        serializer = BusinessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save(owner=request.user)
        BusinessMember.objects.get_or_create(
            business=business,
            user=request.user,
            defaults={"role": BusinessMember.Role.OWNER},
        )
        ActivityLog.objects.create(
            business=business,
            user=request.user,
            action="business.created",
            entity_type="Business",
            entity_id=str(business.id),
        )
        return Response({"success": True, "data": BusinessSerializer(business).data}, status=status.HTTP_201_CREATED)


class MyBusinessView(APIView):
    def get(self, request):
        business = accessible_businesses(request.user).first()
        return Response({"success": True, "data": BusinessSerializer(business).data if business else None})


class BusinessDetailView(APIView):
    def put(self, request, business_id):
        business = accessible_businesses(request.user).filter(id_filter(business_id)).first()
        if not business:
            business = get_owned_business(request.user, business_id)
        serializer = BusinessSerializer(business, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": BusinessSerializer(business).data})
