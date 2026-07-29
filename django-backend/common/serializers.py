from common.utilities.ids import external_id


class MongoCompatMixin:
    def get__id(self, obj):
        return external_id(obj)


def dt(value):
    return value.isoformat().replace("+00:00", "Z") if value else None
