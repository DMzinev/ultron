"""
Clean repository fixture - Business service.
"""
from .repository import ItemRepository
from .models import Item


class ItemService:
    def __init__(self):
        self.repo = ItemRepository()

    def get_recent_items(self):
        records = self.repo.list_all()
        return [Item(r["id"], r["name"]) for r in records]

    def create_item(self, name):
        return self.repo.add({"name": name})
