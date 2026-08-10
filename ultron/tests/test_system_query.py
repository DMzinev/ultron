"""
Ultron Unit Tests — SystemQueryEngine Verification
Campaign 33 / v2.3 — Query Engine Primitives & Cycle Prevention Test Suite
"""

import sys
import os
import unittest

from ultron.core.system_model import (
    SystemNode, SystemEdge, SystemGraph,
    SystemNodeType, SystemEdgeType, SystemModelManager
)
from ultron.core.system_query import SystemQueryEngine


class TestSystemQueryEngine(unittest.TestCase):
    """Test suite verifying SystemQueryEngine primitives, cycle prevention, and agent context extraction."""

    def setUp(self):
        self.manager = SystemModelManager()
        
        # Build test graph topology:
        # mod_a -> mod_b -> mod_c -> mod_a (cycle)
        # mod_a -> test_a
        self.node_a = SystemNode(id="module:core/mod_a.py", type=SystemNodeType.MODULE, file_path="core/mod_a.py", facts={"loc": 100})
        self.node_b = SystemNode(id="module:core/mod_b.py", type=SystemNodeType.MODULE, file_path="core/mod_b.py", facts={"loc": 150})
        self.node_c = SystemNode(id="module:core/mod_c.py", type=SystemNodeType.MODULE, file_path="core/mod_c.py", facts={"loc": 80})
        self.test_a = SystemNode(id="module:tests/test_mod_a.py", type=SystemNodeType.TEST, file_path="tests/test_mod_a.py", facts={"loc": 50})

        self.manager.add_node(self.node_a)
        self.manager.add_node(self.node_b)
        self.manager.add_node(self.node_c)
        self.manager.add_node(self.test_a)

        # Edges
        self.manager.add_edge(SystemEdge(source_id="module:core/mod_a.py", target_id="module:core/mod_b.py", type=SystemEdgeType.IMPORTS))
        self.manager.add_edge(SystemEdge(source_id="module:core/mod_b.py", target_id="module:core/mod_c.py", type=SystemEdgeType.IMPORTS))
        self.manager.add_edge(SystemEdge(source_id="module:core/mod_c.py", target_id="module:core/mod_a.py", type=SystemEdgeType.IMPORTS))  # Cycle
        self.manager.add_edge(SystemEdge(source_id="module:tests/test_mod_a.py", target_id="module:core/mod_a.py", type=SystemEdgeType.TESTS))

        self.query_engine = SystemQueryEngine(self.manager.graph)

    def test_invariant_2_pure_query_engine(self):
        """INVARIANT 2: SystemQueryEngine contains zero scoring logic."""
        methods = [m for m in dir(self.query_engine) if not m.startswith("_")]
        self.assertNotIn("calculate_score", methods)
        self.assertNotIn("rate_risk", methods)
        self.assertNotIn("score_node", methods)

    def test_find_node_primitives(self):
        """Test Level 1 node lookup primitive with path normalization."""
        n1 = self.query_engine.find_node("core/mod_a.py")
        self.assertIsNotNone(n1)
        self.assertEqual(n1.id, "module:core/mod_a.py")

        # Test Windows path normalization
        n2 = self.query_engine.find_node("core\\mod_b.py")
        self.assertIsNotNone(n2)
        self.assertEqual(n2.id, "module:core/mod_b.py")

    def test_circular_dependency_traversal(self):
        """Test cycle prevention (visited set) during deep dependency search."""
        deps = self.query_engine.find_dependencies("core/mod_a.py", depth=5)
        # Should return mod_b and mod_c without infinite loop
        dep_ids = [d.id for d in deps]
        self.assertIn("module:core/mod_b.py", dep_ids)
        self.assertIn("module:core/mod_c.py", dep_ids)

    def test_find_dependents_and_callers(self):
        """Test Level 2 & 3 incoming dependent traversals."""
        dependents = self.query_engine.find_dependents("core/mod_a.py", depth=1)
        dep_ids = [d.id for d in dependents]
        self.assertIn("module:core/mod_c.py", dep_ids)
        self.assertIn("module:tests/test_mod_a.py", dep_ids)

    def test_find_tests_for(self):
        """Test Level 3 test lookup primitive."""
        tests = self.query_engine.find_tests_for("core/mod_a.py")
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].id, "module:tests/test_mod_a.py")

    def test_invariant_6_agent_context_extraction(self):
        """
        INVARIANT 6: Agent context is a projection of the canonical model, not a second representation.
        """
        ctx = self.query_engine.get_agent_context("core/mod_a.py", depth=2)
        self.assertTrue(ctx["found"])
        self.assertEqual(ctx["target"], "core/mod_a.py")
        self.assertGreaterEqual(ctx["summary"]["total_nodes"], 3)
        self.assertGreaterEqual(ctx["summary"]["tests_count"], 1)


if __name__ == "__main__":
    unittest.main()
