"""
Tangled repository fixture - Cycle Member C.
Calls GodModule (closing the cycle).
"""
from .god_module import GodManager


def process_cycle_c(data):
    mgr = GodManager()
    return mgr.handle_cycle({"action": "run", "payload": data})
