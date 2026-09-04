"""
Tangled repository fixture - Client module.
Imports GodModule.
"""
from .god_module import GodState


class TangledClient:
    def __init__(self):
        self.state = GodState()

    def fetch(self, key):
        return self.state.get_val(key)
