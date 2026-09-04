"""
Mixed repository fixture - App entry.
"""
from .config import get_config
from .risky_dispatcher import RiskyDispatcher


def run_app():
    cfg = get_config()
    dispatcher = RiskyDispatcher()
    return dispatcher.route_request("PROCESS", {"batches": []}, {"role": "admin"})
