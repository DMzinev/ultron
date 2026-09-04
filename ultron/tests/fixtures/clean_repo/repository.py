"""
Clean repository fixture - Data access repository.
"""


class ItemRepository:
    def __init__(self):
        self._storage = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
        ]

    def list_all(self):
        return list(self._storage)

    def add(self, record):
        record["id"] = len(self._storage) + 1
        self._storage.append(record)
        return record
