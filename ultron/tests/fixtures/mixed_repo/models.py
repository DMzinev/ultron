"""
Mixed repository fixture - Models.
"""


class ItemModel:
    def __init__(self, item_id, name, score=0):
        self.item_id = item_id
        self.name = name
        self.score = score


class BatchModel:
    def __init__(self, batch_id, items=None):
        self.batch_id = batch_id
        self.items = items or []
