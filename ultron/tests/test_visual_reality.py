import unittest
from ultron.core.ui_reality_compiler import UIRealityCompiler

class TestVisualReality(unittest.TestCase):
    def test_browser_reality_snapshot_schema(self):
        snap = UIRealityCompiler.generate_browser_reality_snapshot()
        self.assertEqual(snap.get("version"), "1.5.0")
        self.assertGreater(snap.get("total_dom_elements", 0), 500)
        self.assertGreater(snap.get("interactive_controls", 0), 50)
        self.assertEqual(snap.get("action_priority_conflicts"), [])
        self.assertEqual(snap.get("runtime_health", {}).get("status"), "HEALTHY")

    def test_dominant_actions_by_stage(self):
        snap = UIRealityCompiler.generate_browser_reality_snapshot()
        dominant = snap.get("dominant_actions", {})
        self.assertEqual(dominant.get("VERIFY"), "btn-run-tests")
        self.assertEqual(dominant.get("AGENT_CONTEXT"), "btn-generate-prompt")
        self.assertEqual(dominant.get("STRUCTURE"), "btn-refresh-graph")

if __name__ == "__main__":
    unittest.main()
