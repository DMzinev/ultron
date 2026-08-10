"""
Ultron Unit Tests — SystemModelDiff Verification
Campaign 37 / v2.4 — Structural Model Diffing & Change Score Verification Suite
"""

import sys
import os
import unittest

from ultron.core.system_model import (
    SystemNode, SystemEdge, SystemGraph,
    SystemNodeType, SystemEdgeType, SystemModelManager
)
from ultron.core.model_diff import SystemModelDiff


class TestModelDiff(unittest.TestCase):
    """Test suite verifying SystemModelDiff structural comparison and formula precision."""

    def test_empty_graph_diff(self):
        """Test boundary condition comparing two empty graphs."""
        g1 = SystemGraph()
        g2 = SystemGraph()
        res = SystemModelDiff.diff(g1, g2)

        self.assertEqual(res.added_nodes, [])
        self.assertEqual(res.removed_nodes, [])
        self.assertEqual(res.modified_nodes, [])
        self.assertEqual(res.added_edges, [])
        self.assertEqual(res.removed_edges, [])
        self.assertEqual(res.structural_change_score, 0.0)

    def test_node_addition_and_removal(self):
        """Test tracking added and removed nodes."""
        mgr1 = SystemModelManager()
        mgr2 = SystemModelManager()

        node_a = SystemNode(id="module:a.py", type=SystemNodeType.MODULE, file_path="a.py", facts={"loc": 50})
        node_b = SystemNode(id="module:b.py", type=SystemNodeType.MODULE, file_path="b.py", facts={"loc": 30})

        mgr1.add_node(node_a)
        mgr2.add_node(node_b)

        res = SystemModelDiff.diff(mgr1.graph, mgr2.graph)

        self.assertEqual(res.added_nodes, ["module:b.py"])
        self.assertEqual(res.removed_nodes, ["module:a.py"])
        # Score = 2.0 * (1 added + 1 removed) = 4.0
        self.assertEqual(res.structural_change_score, 4.0)

    def test_modified_node_and_edge_diff(self):
        """Test tracking modified LOC facts and added/removed edges."""
        mgr1 = SystemModelManager()
        mgr2 = SystemModelManager()

        node1_a = SystemNode(id="module:main.py", type=SystemNodeType.MODULE, file_path="main.py", facts={"loc": 100})
        node2_a = SystemNode(id="module:main.py", type=SystemNodeType.MODULE, file_path="main.py", facts={"loc": 150})
        node_dep = SystemNode(id="module:dep.py", type=SystemNodeType.MODULE, file_path="dep.py", facts={"loc": 20})

        mgr1.add_node(node1_a)

        mgr2.add_node(node2_a)
        mgr2.add_node(node_dep)
        mgr2.add_edge(SystemEdge(source_id="module:main.py", target_id="module:dep.py", type=SystemEdgeType.IMPORTS))

        res = SystemModelDiff.diff(mgr1.graph, mgr2.graph)

        self.assertEqual(res.added_nodes, ["module:dep.py"])
        self.assertEqual(len(res.modified_nodes), 1)
        self.assertEqual(res.modified_nodes[0]["loc_delta"], 50)
        self.assertEqual(len(res.added_edges), 1)

        # Expected score: 2.0 * (1 added node) + 1.0 * (1 added edge) + 0.1 * (50 delta LOC) = 2.0 + 1.0 + 5.0 = 8.0
        self.assertEqual(res.structural_change_score, 8.0)


if __name__ == "__main__":
    unittest.main()
