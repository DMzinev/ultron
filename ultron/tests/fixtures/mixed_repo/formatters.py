"""
Mixed repository fixture - Formatters.
"""


def format_currency(amount):
    return f"${amount:.2f}"


def format_status(status):
    return status.upper()
