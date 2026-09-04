"""
Clean repository fixture - Routing layer.
"""
from .handlers import handle_home, handle_status


class Router:
    def __init__(self, config):
        self.config = config
        self.routes = {
            "home": handle_home,
            "status": handle_status,
        }

    def dispatch(self, path):
        handler = self.routes.get(path)
        if handler:
            return handler()
        return {"status": 404, "body": "Not Found"}


def create_router(config):
    return Router(config)
