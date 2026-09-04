"""
Tangled repository fixture - Cycle Member B.
Calls Cycle Member C.
"""
from .cycle_c import process_cycle_c


def process_cycle_b(data):
    if not data:
        return {}
    transformed = {k: str(v) for k, v in data.items()}
    return process_cycle_c(transformed)
