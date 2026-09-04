"""
Mixed repository fixture - Schema definitions.
"""


def validate_schema(data):
    if not isinstance(data, dict):
        return False
    return "id" in data
