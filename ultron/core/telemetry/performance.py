"""
Ultron Empirical Performance Telemetry Module
Campaign 18 — Performance Instrumentation & Profiling
"""

import time
import os
import sys
from typing import Dict, Any, Optional

_TIMINGS: Dict[str, float] = {}

class PerformanceTimer:
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.start_time: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        _TIMINGS[self.stage_name] = round(elapsed * 1000, 2) # Latency in milliseconds


def get_performance_summary() -> Dict[str, Any]:
    """Returns a snapshot of recorded stage latencies in milliseconds."""
    total_ms = sum(_TIMINGS.values())
    return {
        "timings_ms": dict(_TIMINGS),
        "total_ms": round(total_ms, 2)
    }


def reset_performance_summary():
    """Resets the timing telemetry map."""
    _TIMINGS.clear()
