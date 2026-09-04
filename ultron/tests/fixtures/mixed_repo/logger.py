"""
Mixed repository fixture - Logger wrapper.
"""


def log_event(level, msg):
    return f"[{level}] {msg}"
