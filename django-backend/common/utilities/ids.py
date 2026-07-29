from uuid import UUID

from django.db.models import Q


def external_id(instance) -> str:
    return str(instance.legacy_mongo_id or instance.id)


def id_filter(value: str) -> Q:
    try:
        uuid_value = UUID(str(value))
    except (TypeError, ValueError):
        return Q(legacy_mongo_id=str(value))
    return Q(id=uuid_value) | Q(legacy_mongo_id=str(value))
