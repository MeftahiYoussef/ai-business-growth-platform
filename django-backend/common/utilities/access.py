from rest_framework.exceptions import NotFound

from apps.businesses.models import Business
from apps.competitors.models import Competitor
from apps.teams.models import BusinessMember
from common.utilities.ids import id_filter


def accessible_businesses(user):
    member_business_ids = BusinessMember.objects.filter(user=user).values_list("business_id", flat=True)
    return (Business.objects.filter(owner=user) | Business.objects.filter(id__in=member_business_ids)).distinct()


def get_owned_business(user, business_id=None):
    qs = accessible_businesses(user)
    if business_id:
        qs = qs.filter(id_filter(business_id))
    business = qs.first()
    if not business:
        raise NotFound("Business not found for this user")
    return business


def get_owned_competitor(user, competitor_id):
    business = get_owned_business(user)
    competitor = Competitor.objects.filter(id_filter(competitor_id), business=business).first()
    if not competitor:
        raise NotFound("Competitor not found")
    return business, competitor
