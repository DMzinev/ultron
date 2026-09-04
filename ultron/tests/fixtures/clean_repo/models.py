"""
Clean repository fixture - Domain models.
"""


class Item:
    def __init__(self, item_id, name):
        self.id = item_id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}
