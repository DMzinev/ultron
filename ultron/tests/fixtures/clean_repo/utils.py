"""
Clean repository fixture - Utility functions.
"""


def format_response(status_code, payload):
    return {
        "status": status_code,
        "data": payload,
    }


def slugify(text):
    return text.strip().lower().replace(" ", "-")
