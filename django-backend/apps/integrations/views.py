from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utilities.access import get_owned_business

from .models import (
    SocialAccount,
    SocialAccountMetricSnapshot,
    SocialConnection,
    SocialPost,
    SocialPostMetricSnapshot,
    SynchronizationJob,
)
from .serializers import SocialAccountSerializer, SocialConnectionSerializer, SocialPostSerializer


class SocialConnectionView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        connections = SocialConnection.objects.filter(business=business).order_by("-created_at")
        return Response({"success": True, "data": SocialConnectionSerializer(connections, many=True).data})

    def post(self, request):
        business = get_owned_business(request.user, request.data.get("businessId"))
        provider = request.data.get("provider") or SocialConnection.Provider.SANDBOX
        connection = SocialConnection.objects.create(
            business=business,
            provider=provider,
            display_name=request.data.get("displayName") or f"{provider.title()} sandbox connection",
            required_permissions=["profile", "posts", "analytics"],
            connected_by=request.user,
        )
        account = SocialAccount.objects.create(
            connection=connection,
            business=business,
            platform=provider,
            provider_account_id=f"sandbox-{connection.id}",
            username=f"{business.name.lower().replace(' ', '-')}-{provider}",
            followers=1250,
            metadata={"sandbox": True},
        )
        self._seed_posts(account)
        return Response({"success": True, "data": SocialConnectionSerializer(connection).data}, status=status.HTTP_201_CREATED)

    def _seed_posts(self, account):
        for index in range(3):
            post = SocialPost.objects.create(
                business=account.business,
                account=account,
                provider_post_id=f"sandbox-post-{index}",
                caption=f"Sandbox {account.platform} content signal #{index + 1}",
                content_type="Carousel" if index % 2 == 0 else "Short video",
            )
            SocialPostMetricSnapshot.objects.create(
                post=post, business=account.business, snapshot_date=timezone.now().date(),
                reach=1200 + index * 200, impressions=2400 + index * 320, likes=80 + index * 12,
                comments=10 + index, shares=8 + index, saves=5 + index, clicks=20 + index, video_views=400 + index * 90,
            )
        SocialAccountMetricSnapshot.objects.create(
            account=account, business=account.business, snapshot_date=timezone.now().date(),
            followers=account.followers, reach=3600, impressions=7300, engagement=320,
        )


class SocialSyncView(APIView):
    def post(self, request, connection_id):
        business = get_owned_business(request.user)
        connection = SocialConnection.objects.filter(id=connection_id, business=business).first()
        if not connection:
            return Response({"success": False, "message": "Connection not found"}, status=404)
        job = SynchronizationJob.objects.create(business=business, connection=connection, status=SynchronizationJob.Status.COMPLETED, started_at=timezone.now(), completed_at=timezone.now())
        connection.last_successful_sync_at = timezone.now()
        connection.status = SocialConnection.Status.CONNECTED
        connection.save(update_fields=["last_successful_sync_at", "status"])
        return Response({"success": True, "data": {"jobId": str(job.id), "status": job.status}})


class SocialAccountsView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        accounts = SocialAccount.objects.filter(business=business).order_by("platform")
        return Response({"success": True, "data": SocialAccountSerializer(accounts, many=True).data})


class SocialPostsView(APIView):
    def get(self, request):
        business = get_owned_business(request.user, request.query_params.get("businessId"))
        posts = SocialPost.objects.filter(business=business).order_by("-published_at")[:50]
        return Response({"success": True, "data": SocialPostSerializer(posts, many=True).data})
