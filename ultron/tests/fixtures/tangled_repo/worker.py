"""
Tangled repository fixture - Worker module.
Imports GodModule.
"""
from .god_module import GodManager


class BackgroundWorker:
    def __init__(self):
        self.mgr = GodManager()

    def do_work(self, item):
        return self.mgr.dispatch_c([item])
