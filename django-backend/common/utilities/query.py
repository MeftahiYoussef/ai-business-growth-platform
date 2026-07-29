from django.db.models import Q


def apply_search_sort(queryset, request, search_fields, sort_map=None):
    search = (request.query_params.get("search") or "").strip()
    if search:
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(query)

    sort_by = request.query_params.get("sortBy") or "createdAt"
    sort_order = request.query_params.get("sortOrder")
    sort_map = sort_map or {}
    field = sort_map.get(sort_by, sort_map.get("createdAt", "created_at"))
    prefix = "" if sort_order == "asc" else "-"
    return queryset.order_by(f"{prefix}{field}")
