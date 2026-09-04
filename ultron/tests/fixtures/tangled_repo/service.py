"""
Tangled repository fixture - Service module.
Imports GodModule.
"""
from .god_module import GodManager


class TangledService:
    def __init__(self):
        self.mgr = GodManager()

    def serve(self, request):
        return self.mgr.dispatch_a(request.get("x", 0), request.get("y", 0), request.get("z", 0))
