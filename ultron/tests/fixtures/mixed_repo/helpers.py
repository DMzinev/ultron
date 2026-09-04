"""
Mixed repository fixture - Helpers.
"""


def clean_string(val):
    return val.strip() if val else ""


def sanitize_dict(d):
    return {k: v for k, v in d.items() if v is not None}
