"""
Ultron Unit Tests — SystemModel & LanguageAdapter Verification
Campaign 32 / v2.3 — Canonical System Model & 6 Architectural Invariants Test Suite
"""

import sys
import os
import tempfile
import unittest

from ultron.core.system_model import (
    SystemNode, SystemEdge, EvidenceObject, SystemGraph,
    SystemNodeType, SystemEdgeType, SystemModelManager, SystemModelSnapshot
)
from ultron.core.language_adapter import PythonLanguageAdapter


class TestSystemModel(unittest.TestCase):
    """Test suite verifying SystemModel data structures, serialization, and architectural invariants."""

    def test_node_edge_evidence_serialization(self):
        node = SystemNode(
            id="module:ultron/core/analyzer.py",
            type=SystemNodeType.MODULE,
            file_path="ultron/core/analyzer.py",
            line_start=1,
            line_end=200,
            facts={"loc": 150, "complexity": 12}
        )
        d = node.to_dict()
        self.assertEqual(d["id"], "module:ultron/core/analyzer.py")
        self.assertEqual(d["type"], "MODULE")
        self.assertEqual(d["file_path"], "ultron/core/analyzer.py")
        self.assertEqual(d["facts"]["complexity"], 12)

        rebuilt_node = SystemNode.from_dict(d)
        self.assertEqual(rebuilt_node.id, node.id)
        self.assertEqual(rebuilt_node.type, SystemNodeType.MODULE)

        edge = SystemEdge(
            source_id="module:ultron/interfaces/server.py",
            target_id="module:ultron/core/analyzer.py",
            type=SystemEdgeType.IMPORTS
        )
        ed = edge.to_dict()
        self.assertEqual(ed["source_id"], "module:ultron/interfaces/server.py")
        self.assertEqual(ed["type"], "IMPORTS")

        ev = EvidenceObject(
            id="ev-ast-01",
            type="AST_FACT",
            subject_id="module:ultron/core/analyzer.py",
            measurement={"loc": 150},
            source={"adapter": "python"}
        )
        evd = ev.to_dict()
        self.assertEqual(evd["id"], "ev-ast-01")
        self.assertEqual(evd["type"], "AST_FACT")

    def test_invariant_1_pure_data_manager(self):
        """INVARIANT 1: SystemModelManager contains zero risk/recommendation logic."""
        manager = SystemModelManager()
        methods = [m for m in dir(manager) if not m.startswith("_")]
        self.assertNotIn("calculate_risk", methods)
        self.assertNotIn("generate_recommendation", methods)
        self.assertNotIn("evaluate_score", methods)

    def test_invariant_4_deterministic_hashing(self):
        """INVARIANT 4: Canonical serialization produces byte-identical hashes for identical repo states."""
        mgr1 = SystemModelManager()
        mgr2 = SystemModelManager()

        node_a = SystemNode(id="module:a.py", type=SystemNodeType.MODULE, file_path="a.py", facts={"loc": 10})
        node_b = SystemNode(id="module:b.py", type=SystemNodeType.MODULE, file_path="b.py", facts={"loc": 20})
        edge_ab = SystemEdge(source_id="module:a.py", target_id="module:b.py", type=SystemEdgeType.IMPORTS)

        # Add nodes in normal order to mgr1
        mgr1.add_node(node_a)
        mgr1.add_node(node_b)
        mgr1.add_edge(edge_ab)

        # Add nodes in reverse order to mgr2
        mgr2.add_node(node_b)
        mgr2.add_node(node_a)
        mgr2.add_edge(edge_ab)

        hash1 = mgr1.compute_hash()
        hash2 = mgr2.compute_hash()

        self.assertEqual(hash1, hash2, "Deterministic model hashing failed across node orderings")
        self.assertEqual(len(hash1), 64, "SHA-256 digest length must be 64 hex chars")

    def test_python_language_adapter_parsing(self):
        """Test PythonLanguageAdapter AST parsing and error boundaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "sample.py")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("import os\n\nclass Sample:\n    def foo(self):\n        return True\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            self.assertGreaterEqual(len(graph.nodes), 1)
            mod_node = graph.nodes.get("module:sample.py")
            self.assertIsNotNone(mod_node)
            self.assertEqual(mod_node.file_path, "sample.py")
            self.assertGreater(mod_node.facts.get("loc", 0), 0)

            # Check class node
            class_node = graph.nodes.get("class:sample.py:Sample")
            self.assertIsNotNone(class_node)

            # Check function node
            func_node = graph.nodes.get("function:sample.py:foo")
            self.assertIsNotNone(func_node)

    def test_python_adapter_syntax_error_handling(self):
        """Test that invalid syntax is caught cleanly without crashing adapter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "broken.py")
            with open(bad_file, "w", encoding="utf-8") as f:
                f.write("def broken_syntax(:\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            mod_node = graph.nodes.get("module:broken.py")
            self.assertIsNotNone(mod_node)
            self.assertIn("parse_error", mod_node.facts)
            self.assertTrue(mod_node.facts["parse_error"].startswith("SyntaxError"))


if __name__ == "__main__":
    unittest.main()
