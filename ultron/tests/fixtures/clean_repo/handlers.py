"""
Clean repository fixture - Request handlers.
"""
from .service import ItemService
from .utils import format_response


def handle_home():
    service = ItemService()
    items = service.get_recent_items()
    return format_response(200, items)


def handle_status():
    return format_response(200, {"status": "healthy"})
