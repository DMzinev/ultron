"""
Tangled repository fixture - Entry point.
Imports GodModule.
"""
from .god_module import GodPipeline


def main():
    pipeline = GodPipeline()
    return pipeline.run_all({"sys_task": 120, "user_name": "alice"})


if __name__ == "__main__":
    main()
