"""
Unit tests for Ultron Provenance Lineage Engine (ultron/core/provenance.py)
"""

import unittest
from ultron.core.provenance import ProvenanceTracker, ProvenanceChain, EvidenceReference

class TestProvenanceEngine(unittest.TestCase):

    def test_evidence_reference_serialization(self):
        ref = EvidenceReference("ev_101", "AST_FACT", 0.95, {"line": 42})
        data = ref.to_dict()
        self.assertEqual(data["evidence_id"], "ev_101")
        self.assertEqual(data["source_type"], "AST_FACT")
        self.assertEqual(data["confidence"], 0.95)
        self.assertEqual(data["details"]["line"], 42)

    def test_provenance_tracker(self):
        tracker = ProvenanceTracker()
        chain = tracker.record_provenance("foo.py", "DERIVED_CODE", "ev_ast_01", "AST_FACT", 1.0, {"symbol": "bar"})
        
        self.assertIsNotNone(chain)
        self.assertEqual(chain.target_id, "foo.py")
        self.assertEqual(len(chain.references), 1)

        retrieved = tracker.get_provenance("foo.py")
        self.assertEqual(retrieved.target_id, "foo.py")
        self.assertEqual(retrieved.references[0].evidence_id, "ev_ast_01")

        full_dict = tracker.to_dict()
        self.assertIn("foo.py", full_dict)

if __name__ == "__main__":
    unittest.main()
