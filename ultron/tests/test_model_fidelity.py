"""
Ultron Unit Tests — Golden Model Fidelity Test Suite
Campaign 35 / v2.4 — Golden Topology Fidelity Verification Across 7 Core Reference Topologies
"""

import sys
import os
import tempfile
import unittest

from ultron.core.system_model import SystemNodeType, SystemEdgeType
from ultron.core.language_adapter import PythonLanguageAdapter


class TestModelFidelity(unittest.TestCase):
    """Test suite verifying AST extraction accuracy against independently authored golden topologies."""

    def test_golden_topology_1_single_file(self):
        """Topology 1: Single file with module, class, methods, and facts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "calculator.py")
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(
                    "class Calculator:\n"
                    "    def add(self, a, b):\n"
                    "        return a + b\n\n"
                    "    def subtract(self, a, b):\n"
                    "        return a - b\n"
                )

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            mod_node = graph.nodes.get("module:calculator.py")
            self.assertIsNotNone(mod_node, "Module node missing")
            self.assertGreater(mod_node.facts.get("loc", 0), 0)

            class_node = graph.nodes.get("class:calculator.py:Calculator")
            self.assertIsNotNone(class_node, "Class node missing")

            add_node = graph.nodes.get("function:calculator.py:add")
            sub_node = graph.nodes.get("function:calculator.py:subtract")
            self.assertIsNotNone(add_node, "Method add missing")
            self.assertIsNotNone(sub_node, "Method subtract missing")

    def test_golden_topology_2_multi_module_imports(self):
        """Topology 2: Multi-module package with A -> B -> C import edges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "pkg"), exist_ok=True)
            
            with open(os.path.join(tmpdir, "pkg", "c.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("def fn_c(): return 42\n")
            with open(os.path.join(tmpdir, "pkg", "b.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import pkg.c\ndef fn_b(): return pkg.c.fn_c()\n")
            with open(os.path.join(tmpdir, "pkg", "a.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import pkg.b\ndef fn_a(): return pkg.b.fn_b()\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            self.assertIn("module:pkg/a.py", graph.nodes)
            self.assertIn("module:pkg/b.py", graph.nodes)
            self.assertIn("module:pkg/c.py", graph.nodes)

            # Check import edges
            import_edges = [e for e in graph.edges if e.type == SystemEdgeType.IMPORTS]
            self.assertTrue(any(e.source_id == "module:pkg/a.py" and e.target_id == "module:pkg/b.py" for e in import_edges))
            self.assertTrue(any(e.source_id == "module:pkg/b.py" and e.target_id == "module:pkg/c.py" for e in import_edges))

    def test_golden_topology_3_circular_dependencies(self):
        """Topology 3: Circular import chain A -> B -> C -> A."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "mod_a.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import mod_b\n")
            with open(os.path.join(tmpdir, "mod_b.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import mod_c\n")
            with open(os.path.join(tmpdir, "mod_c.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import mod_a\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            self.assertEqual(len(graph.nodes), 3)
            import_edges = [e for e in graph.edges if e.type == SystemEdgeType.IMPORTS]
            self.assertEqual(len(import_edges), 3)

    def test_golden_topology_4_class_inheritance(self):
        """Topology 4: Class inheritance Child -> Parent INHERITS edge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "models.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("class Base:\n    pass\n\nclass Child(Base):\n    pass\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            inherits_edges = [e for e in graph.edges if e.type == SystemEdgeType.INHERITS]
            self.assertEqual(len(inherits_edges), 1)
            self.assertEqual(inherits_edges[0].source_id, "class:models.py:Child")

    def test_golden_topology_5_containment_hierarchy(self):
        """Topology 5: Containment hierarchy Module -> Class -> Method CONTAINS edges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "app.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("class App:\n    def run(self):\n        pass\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            contains_edges = [e for e in graph.edges if e.type == SystemEdgeType.CONTAINS]
            self.assertGreaterEqual(len(contains_edges), 2)
            self.assertTrue(any(e.source_id == "module:app.py" and e.target_id == "class:app.py:App" for e in contains_edges))

    def test_golden_topology_6_test_associations(self):
        """Topology 6: Test association edge TestFoo -> Foo TESTS edge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "service.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("def do_work(): pass\n")
            with open(os.path.join(tmpdir, "test_service.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("import service\ndef test_do_work(): assert True\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            test_edges = [e for e in graph.edges if e.type == SystemEdgeType.TESTS]
            self.assertGreaterEqual(len(test_edges), 1)
            self.assertTrue(any(e.source_id == "module:test_service.py" and e.target_id == "module:service.py" for e in test_edges))

    def test_golden_topology_7_broken_syntax_handling(self):
        """Topology 7: Invalid Python source syntax error boundary metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "corrupted.py"), "w", encoding="utf-8", errors="replace") as f:
                f.write("def broken(:\n")

            adapter = PythonLanguageAdapter()
            graph = adapter.parse_repository(tmpdir)

            bad_node = graph.nodes.get("module:corrupted.py")
            self.assertIsNotNone(bad_node)
            self.assertIn("parse_error", bad_node.facts)


if __name__ == "__main__":
    unittest.main()
