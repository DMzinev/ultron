"""
Ultron Unit Tests — Round-Trip Serialization & Model Completeness Telemetry
Campaign 40 / v2.5 — Serialization Integrity & Completeness Telemetry Verification Suite
"""

import sys
import os
import unittest

from ultron.core.system_model import (
    SystemNode, SystemEdge, EvidenceObject, SystemGraph,
    SystemNodeType, SystemEdgeType, SystemModelManager
)


class TestModelSerialization(unittest.TestCase):
    """Test suite verifying Graph -> JSON -> Graph' round-trip identity and completeness telemetry."""

    def test_round_trip_serialization_integrity(self):
        """Test that converting graph to dict and back preserves hash identity and deep equality."""
        mgr_orig = SystemModelManager()
        
        node_mod = SystemNode(id="module:core/foo.py", type=SystemNodeType.MODULE, file_path="core/foo.py", facts={"loc": 45, "complexity": 3})
        node_cls = SystemNode(id="class:core/foo.py:Foo", type=SystemNodeType.CLASS, file_path="core/foo.py", facts={"name": "Foo"})
        edge = SystemEdge(source_id="module:core/foo.py", target_id="class:core/foo.py:Foo", type=SystemEdgeType.CONTAINS)
        evidence = EvidenceObject(id="ev-1", type="AST_FACT", subject_id="module:core/foo.py", measurement={"loc": 45}, source={"adapter": "python"})

        mgr_orig.add_node(node_mod)
        mgr_orig.add_node(node_cls)
        mgr_orig.add_edge(edge)
        mgr_orig.add_evidence(evidence)

        hash_orig = mgr_orig.compute_hash()

        # Serialize to dict and deserialize back
        dict_envelope = mgr_orig.graph.to_dict()
        restored_graph = SystemGraph.from_dict(dict_envelope)
        mgr_restored = SystemModelManager(restored_graph)

        hash_restored = mgr_restored.compute_hash()

        self.assertEqual(hash_orig, hash_restored, "Hash mismatch after round-trip serialization")
        self.assertIn("module:core/foo.py", restored_graph.nodes)
        self.assertIn("class:core/foo.py:Foo", restored_graph.nodes)
        self.assertEqual(len(restored_graph.edges), 1)
        self.assertIn("ev-1", restored_graph.evidence)

    def test_completeness_telemetry_zero_guard(self):
        """Test completeness telemetry computation with zero-division guard."""
        mgr = SystemModelManager()
        telemetry = mgr.compute_completeness_telemetry(files_discovered=0)

        self.assertEqual(telemetry["files_discovered"], 0)
        self.assertEqual(telemetry["files_parsed"], 0)
        self.assertEqual(telemetry["parse_coverage_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
