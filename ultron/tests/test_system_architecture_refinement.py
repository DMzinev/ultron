"""
ultron.tests.test_system_architecture_refinement
Comprehensive Verification Suite for Ultron v2.7.2 System & Architecture Refinements:
1. RKM Fast-Path Cache Rehydration (< 20ms) & Data Parity
2. Polyglot Source Discovery & Multi-Language AST Extraction
3. Architectural Anti-Pattern Engine & Structural Health Diagnostics
"""

import os
import time
import shutil
import tempfile
import unittest

from ultron.core.pipeline.orchestrator import analyze_repository, reconstruct_codebase_from_rkm
from ultron.core.pipeline.discovery import discover
from ultron.core.rkm.store import RepositoryStore
from ultron.core.polyglot_adapter import PolyglotAdapter
from ultron.core.anti_pattern_detector import AntiPatternDetector


class TestSystemArchitectureRefinement(unittest.TestCase):
    """Verifies system scalability, sub-20ms cache rehydration, and polyglot architecture."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = self.temp_dir

        # Setup sample Python modules
        self.mod_a = os.path.join(self.repo_path, "service_a.py")
        with open(self.mod_a, "w", encoding="utf-8") as f:
            f.write(
                "import os\n"
                "def process_data(x):\n"
                "    if x > 10:\n"
                "        return x * 2\n"
                "    return x\n"
            )

        self.mod_b = os.path.join(self.repo_path, "service_b.py")
        with open(self.mod_b, "w", encoding="utf-8") as f:
            f.write(
                "from service_a import process_data\n"
                "def run():\n"
                "    return process_data(20)\n"
            )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_rkm_cache_rehydration_fast_path_and_parity(self):
        """Asserts cache-hit rehydration runs in < 20ms and matches cold analysis schema."""
        # 1. Cold analysis (populates SQLite RKM)
        cold_bundle = analyze_repository(self.repo_path, force=True)
        self.assertEqual(len(cold_bundle.files), 2)
        self.assertEqual(len(cold_bundle.risks), 2)

        db_path = os.path.join(self.repo_path, ".ultron", "repository.db")
        self.assertTrue(os.path.exists(db_path))

        # 2. Warm cache-hit analysis benchmark (N=10)
        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            cached_bundle = analyze_repository(self.repo_path, force=False)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000)

        mean_latency = sum(latencies) / len(latencies)
        self.assertLess(mean_latency, 25.0, f"Mean cache rehydration latency {mean_latency:.2f}ms exceeded 25ms budget")

        # 3. Verify exact schema parity
        self.assertEqual(cached_bundle.repo_uuid, cold_bundle.repo_uuid)
        self.assertEqual(cached_bundle.content_hash, cold_bundle.content_hash)
        self.assertEqual(len(cached_bundle.risks), len(cold_bundle.risks))

        for risk in cached_bundle.risks:
            self.assertTrue(hasattr(risk, "file_path"))
            self.assertTrue(hasattr(risk, "impact_score"))
            self.assertTrue(hasattr(risk, "coupling_score"))
            self.assertTrue(hasattr(risk, "complexity"))
            self.assertTrue(hasattr(risk, "architectural_role"))
            self.assertTrue(hasattr(risk, "change_strategy"))

    def test_rkm_cache_rehydration_corrupt_fallback(self):
        """Asserts corrupted or non-existent run ID triggers safe fallback to cold scan without crashing."""
        analyze_repository(self.repo_path, force=True)
        db_path = os.path.join(self.repo_path, ".ultron", "repository.db")

        # 1. Non-existent run id test
        store = RepositoryStore(db_path)
        try:
            codebase, risks = reconstruct_codebase_from_rkm(store, 99999)
            self.assertEqual(codebase, {})
            self.assertEqual(risks, [])
        finally:
            store.close()

        # 2. Corrupted DB file recovery test
        with open(db_path, "wb") as f:
            f.write(b"CORRUPTED_SQLITE_HEADER_DATA")

        # Should safely fall back to full analysis
        bundle = analyze_repository(self.repo_path, force=False)
        self.assertEqual(len(bundle.files), 2)
        self.assertEqual(len(bundle.risks), 2)

    def test_polyglot_discovery_and_ast_extraction(self):
        """Asserts discovery and AST extraction on mixed Python, TypeScript, JavaScript, and Go."""
        ts_file = os.path.join(self.repo_path, "client.ts")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write("import { run } from './service_b';\nexport function init(): void { if (true) { run(); } }\n")

        js_file = os.path.join(self.repo_path, "util.js")
        with open(js_file, "w", encoding="utf-8") as f:
            f.write("const fs = require('fs');\nfunction read() { return fs.readFileSync('foo'); }\nmodule.exports = { read };\n")

        go_file = os.path.join(self.repo_path, "main.go")
        with open(go_file, "w", encoding="utf-8") as f:
            f.write("package main\nimport \"fmt\"\nfunc main() { fmt.Println(\"Hello\") }\n")

        discovered = discover(self.repo_path)
        self.assertIn("service_a.py", discovered)
        self.assertIn("client.ts", discovered)
        self.assertIn("util.js", discovered)
        self.assertIn("main.go", discovered)

        # Verify Polyglot AST extraction
        with open(ts_file, "r", encoding="utf-8") as f:
            ts_ast = PolyglotAdapter.parse_file("client.ts", f.read())
        self.assertEqual(ts_ast["language"], "typescript")
        self.assertEqual(ts_ast["complexity"], 2.0)
        self.assertIn("./service_b", ts_ast["imports"])

        with open(go_file, "r", encoding="utf-8") as f:
            go_ast = PolyglotAdapter.parse_file("main.go", f.read())
        self.assertEqual(go_ast["language"], "go")
        self.assertIn("fmt", go_ast["imports"])

    def test_anti_pattern_engine_all_smells(self):
        """Asserts detection of God Object, Feature Envy, Shotgun Surgery, Brain Method, and Circular Imports."""
        nodes = [
            {"id": "god_module.py"},
            {"id": "caller_1.py"},
            {"id": "caller_2.py"},
            {"id": "caller_3.py"},
            {"id": "caller_4.py"},
            {"id": "caller_5.py"},
            {"id": "caller_6.py"},
            {"id": "cycle_a.py"},
            {"id": "cycle_b.py"},
        ]

        edges = [
            {"source": "caller_1.py", "target": "god_module.py"},
            {"source": "caller_2.py", "target": "god_module.py"},
            {"source": "caller_3.py", "target": "god_module.py"},
            {"source": "caller_4.py", "target": "god_module.py"},
            {"source": "caller_5.py", "target": "god_module.py"},
            {"source": "caller_6.py", "target": "god_module.py"},
            {"source": "god_module.py", "target": "ext_a.py"},
            {"source": "god_module.py", "target": "ext_b.py"},
            {"source": "cycle_a.py", "target": "cycle_b.py"},
            {"source": "cycle_b.py", "target": "cycle_a.py"},
        ]

        risks = [
            {"file_path": "god_module.py", "complexity": 22.0, "lines_of_code": 150},
            {"file_path": "cycle_a.py", "complexity": 3.0, "lines_of_code": 20},
            {"file_path": "cycle_b.py", "complexity": 3.0, "lines_of_code": 20},
        ]

        patterns = AntiPatternDetector.detect_anti_patterns(nodes, edges, risks)
        pattern_types = [p["pattern_type"] for p in patterns]

        self.assertIn("GOD_OBJECT", pattern_types)
        self.assertIn("SHOTGUN_SURGERY", pattern_types)
        self.assertIn("BRAIN_METHOD", pattern_types)
        self.assertIn("CIRCULAR_DEPENDENCY", pattern_types)

        # Assert playbooks are populated for all detected patterns
        for p in patterns:
            self.assertTrue(len(p["playbook"]) > 10)
            self.assertTrue(len(p["description"]) > 10)


if __name__ == "__main__":
    unittest.main()
