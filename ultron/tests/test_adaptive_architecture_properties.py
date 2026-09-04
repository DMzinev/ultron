"""
ultron.tests.test_adaptive_architecture_properties
Adaptive Architecture Invariant Testing Matrix.

Tests fundamental mathematical and structural invariants across dynamically generated
AST trees, randomized import topologies, and dynamic chaos mutations.
"""

import os
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from ultron.core import analyzer
from ultron.core.analyzer import build_dependency_graph
from ultron.core.pipeline.orchestrator import compute_repository_content_hash
from ultron.core.rkm.risk_intelligence import compute_risk_profile


class TestAdaptiveArchitectureProperties(unittest.TestCase):
    """Generative property-based testing for Ultron architectural invariants."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_adaptive_")
        self.rng = random.Random(42)  # Seeded for 100% deterministic reproducibility

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _generate_synthetic_repo(self, num_files=10, max_depth=3, rng=None):
        """Generates a random multi-tier directory structure with Python source files and cross-imports."""
        r = rng or self.rng
        files_created = []
        module_names = [f"mod_{i}" for i in range(num_files)]

        for i, mod_name in enumerate(module_names):
            depth = r.randint(0, max_depth)
            sub_dirs = [f"pkg_{r.randint(0, 2)}" for _ in range(depth)]
            dir_path = os.path.join(self.test_dir, *sub_dirs)
            os.makedirs(dir_path, exist_ok=True)

            file_path = os.path.join(dir_path, f"{mod_name}.py")
            files_created.append(file_path)

            # Generate cross-module imports
            possible_targets = [m for m in module_names if m != mod_name]
            num_imports = r.randint(0, min(3, len(possible_targets)))
            chosen_imports = r.sample(possible_targets, num_imports) if possible_targets else []

            lines = []
            for target in chosen_imports:
                lines.append(f"import {target}")

            # Generate functions with varying branching depth
            num_funcs = r.randint(1, 4)
            for f_idx in range(num_funcs):
                func_name = f"fn_{mod_name}_{f_idx}"
                branch_depth = r.randint(1, 5)
                lines.append(f"def {func_name}(x):")
                lines.append("    res = x")
                for b in range(branch_depth):
                    lines.append(f"    if x > {b}:")
                    lines.append(f"        res += {b + 1}")
                lines.append("    return res\n")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        return files_created

    def test_property_determinism_and_idempotency(self):
        """Property 1: Analysis on identical codebase ASTs produces bit-for-bit identical fingerprints & nodes."""
        repo_files = self._generate_synthetic_repo(num_files=8, max_depth=2)

        # Run analysis pass 1
        codebase1 = analyzer.analyze_directory(self.test_dir)
        graph1 = build_dependency_graph(codebase1)
        hash1 = compute_repository_content_hash(self.test_dir, [os.path.relpath(p, self.test_dir) for p in repo_files])

        # Run analysis pass 2
        codebase2 = analyzer.analyze_directory(self.test_dir)
        graph2 = build_dependency_graph(codebase2)
        hash2 = compute_repository_content_hash(self.test_dir, [os.path.relpath(p, self.test_dir) for p in repo_files])

        # Assert bit-for-bit fingerprint determinism
        self.assertEqual(hash1, hash2, "Repository content fingerprint must be 100% deterministic")
        self.assertEqual(len(graph1.get("nodes", [])), len(graph2.get("nodes", [])), "Node count must be idempotent across passes")
        self.assertEqual(len(graph1.get("links", [])), len(graph2.get("links", [])), "Link count must be idempotent across passes")

        # Assert canonical node attributes
        nodes1 = sorted(graph1.get("nodes", []), key=lambda n: n.get("id", ""))
        nodes2 = sorted(graph2.get("nodes", []), key=lambda n: n.get("id", ""))
        for n1, n2 in zip(nodes1, nodes2):
            self.assertEqual(n1.get("id"), n2.get("id"))
            self.assertEqual(n1.get("label"), n2.get("label"))
            self.assertEqual(n1.get("type"), n2.get("type"))

    def test_property_risk_monotonicity(self):
        """Property 2: Risk Impact Score must be monotonically non-decreasing with complexity & coupling."""
        # Test 100 random parameter pairs
        for _ in range(100):
            c1 = self.rng.uniform(1.0, 50.0)
            k1 = self.rng.randint(0, 30)
            cov1 = self.rng.uniform(10.0, 100.0)

            c2 = c1 + self.rng.uniform(0.0, 20.0)  # c2 >= c1
            k2 = k1 + self.rng.randint(0, 10)       # k2 >= k1
            cov2 = cov1                             # constant coverage

            r1 = compute_risk_profile(entity_id="test_entity", complexity=c1, coupling_fanout=k1, coverage_percent=cov1)
            r2 = compute_risk_profile(entity_id="test_entity", complexity=c2, coupling_fanout=k2, coverage_percent=cov2)

            score1 = getattr(r1, "impact_score", 0.0)
            score2 = getattr(r2, "impact_score", 0.0)

            self.assertGreaterEqual(
                score2, score1 - 1e-9,
                f"Monotonicity violation: I(C={c2:.1f}, K={k2}) = {score2:.2f} < I(C={c1:.1f}, K={k1}) = {score1:.2f}"
            )

    def test_property_graph_closure_and_referential_integrity(self):
        """Property 3: All graph edges (u, v) in E must satisfy u in V and v in V (no dangling links/NaNs)."""
        _ = self._generate_synthetic_repo(num_files=12, max_depth=3)
        codebase = analyzer.analyze_directory(self.test_dir)
        graph_dict = build_dependency_graph(codebase)

        nodes = graph_dict.get("nodes", [])
        links = graph_dict.get("links", [])

        node_ids = {str(n.get("id", "")).replace("\\", "/") for n in nodes}

        self.assertGreater(len(nodes), 0, "Graph must contain at least one node")

        for link in links:
            src = str(link.get("source", "")).replace("\\", "/")
            tgt = str(link.get("target", "")).replace("\\", "/")

            self.assertTrue(src, "Edge source must not be empty")
            self.assertTrue(tgt, "Edge target must not be empty")
            self.assertIn(src, node_ids, f"Referential Integrity: Link source '{src}' missing from node set")
            self.assertIn(tgt, node_ids, f"Referential Integrity: Link target '{tgt}' missing from node set")

    def test_property_dynamic_ast_chaos_quarantine(self):
        """Property 4: Injected syntax errors and null bytes are quarantined without pipeline crash."""
        # 1. Valid file
        valid_path = os.path.join(self.test_dir, "clean_module.py")
        with open(valid_path, "w", encoding="utf-8") as f:
            f.write("def healthy_fn(): return 42\n")

        # 2. Syntax error file
        broken_syntax_path = os.path.join(self.test_dir, "broken_syntax.py")
        with open(broken_syntax_path, "w", encoding="utf-8") as f:
            f.write("def bad_syntax(:\n   unclosed bracket\n")

        # 3. Null bytes corrupted file
        corrupted_bytes_path = os.path.join(self.test_dir, "corrupted_nulls.py")
        with open(corrupted_bytes_path, "wb") as f:
            f.write(b"def corrupted(\x00\x00\xff): pass\n")

        # Assert analyze_file returns error dictionaries for corruptions
        broken_res = analyzer.analyze_file(broken_syntax_path)
        self.assertIn("error", broken_res, "analyze_file must return error dict on syntax failure")

        null_res = analyzer.analyze_file(corrupted_bytes_path)
        self.assertIn("error", null_res, "analyze_file must return error dict on byte corruption")

        # Run directory analyzer
        codebase = analyzer.analyze_directory(self.test_dir)

        # Assert clean module is parsed and corrupted files are quarantined without crashing
        clean_key = next((k for k in codebase.keys() if "clean_module.py" in k), None)
        self.assertIsNotNone(clean_key, "Clean module must be parsed and included in codebase")
        self.assertIn("definitions", codebase[clean_key])


if __name__ == "__main__":
    unittest.main()
