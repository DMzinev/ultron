"""
Tangled repository fixture - Helpers module.
Imports GodModule.
"""
from .god_module import GodManager


def helper_transform(val):
    mgr = GodManager()
    return mgr.step_01(val)
