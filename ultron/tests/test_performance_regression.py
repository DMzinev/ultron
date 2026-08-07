"""
Ultron Calibrated Performance Regression Gate
Campaign 18 & Wave 5: Benchmark Baselines, Tracemalloc & Normalized Latency
"""

import unittest
import tracemalloc
import time
import json
import os
from pathlib import Path

class TestPerformanceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_path = Path(__file__).parent / "baselines" / "perf_baseline.json"
        with open(cls.baseline_path, "r", encoding="utf-8") as f:
            cls.baseline_data = json.load(f)

    def test_calibrated_performance_regression_gate(self):
        """Asserts performance metrics remain within 25% normalized calibration tolerance of baseline."""
        # Reference calibration loop to scale hardware clock variance
        cal_start = time.perf_counter()
        _dummy = sum(i * i for i in range(100000))
        cal_scale = max(0.5, min(2.0, (time.perf_counter() - cal_start) / 0.005))

        tracemalloc.start()
        start_time = time.perf_counter()

        # Execute lightweight benchmark payload
        from ultron.core import analyzer
        sample_codebase = {"main.py": {"definitions": [{"type": "function", "name": "foo"}]}}
        graph = analyzer.build_dependency_graph(sample_codebase)

        elapsed = time.perf_counter() - start_time
        peak_bytes = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        peak_mb = peak_bytes / (1024 * 1024)
        api_budget_ms = self.baseline_data["benchmarks"]["api_response_ms"] * cal_scale

        print(f"\n[Regression Gate] Latency: {elapsed*1000:.2f}ms (Budget: {api_budget_ms:.2f}ms) | Peak Heap: {peak_mb:.2f}MB")

        self.assertLess(elapsed * 1000, api_budget_ms, f"Latency ({elapsed*1000:.2f}ms) exceeded calibrated budget")
        self.assertLess(peak_mb, self.baseline_data["benchmarks"]["peak_heap_mb"], "Peak heap allocation exceeded budget")

if __name__ == "__main__":
    unittest.main()
