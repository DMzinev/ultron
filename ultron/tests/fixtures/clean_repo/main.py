"""
Clean repository fixture - Entry point.
Low complexity, shallow imports, no cycles.
"""
from .config import load_config
from .router import create_router


def main():
    config = load_config()
    router = create_router(config)
    return router.dispatch("home")


if __name__ == "__main__":
    main()
