"""
Clean repository fixture - Configuration loader.
"""
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 30


def load_config():
    return {
        "port": DEFAULT_PORT,
        "timeout": DEFAULT_TIMEOUT,
        "debug": False,
    }
