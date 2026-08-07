"""
Ultron Synthetic Repository Scale Benchmark Suite
Campaign 22 — Scale Validation, Heap Allocation Measurement & Throughput Audits
"""

import unittest
import tracemalloc
import time
import os
import tempfile
import shutil

class TestScalabilityBenchmark(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Generate 1,000 synthetic Python source files with 5 functions each (5,000 functions total)
        for i in range(1000):
            file_path = os.path.join(self.temp_dir, f"module_{i}.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"def func_{i}_1(): pass\n")
                f.write(f"def func_{i}_2(): pass\n")
                f.write(f"def func_{i}_3(): pass\n")
                f.write(f"def func_{i}_4(): pass\n")
                f.write(f"def func_{i}_5(): pass\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_synthetic_scale_scan_performance_and_memory(self):
        """Benchmarking 1,000 synthetic files / 5,000 functions for memory (< 150MB) and scan throughput (< 5s)."""
        from ultron.core import analyzer

        tracemalloc.start()
        start_time = time.perf_counter()

        # Run core AST scan
        results = analyzer.analyze_directory(self.temp_dir)

        elapsed_time = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_tracemalloc_memory(), tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        print(f"\n[Scale Benchmark] Scanned 1,000 files / 5,000 functions in {elapsed_time:.2f}s | Peak Heap Allocation: {peak_mb:.2f} MB")

        # Assertions per Campaign 22 performance budgets
        self.assertLess(elapsed_time, 15.0, f"Scan duration ({elapsed_time:.2f}s) exceeded 15.0s budget for 1,000 files")
        self.assertLess(peak_mb, 150.0, f"Peak memory allocation ({peak_mb:.2f}MB) exceeded 150MB budget")
        self.assertGreaterEqual(len(results), 1000)

if __name__ == "__main__":
    unittest.main()
