"""
Mixed repository fixture - Configuration.
"""
from .constants import APP_VERSION, DEFAULT_TIMEOUT


def get_config():
    return {
        "version": APP_VERSION,
        "timeout": DEFAULT_TIMEOUT,
    }
