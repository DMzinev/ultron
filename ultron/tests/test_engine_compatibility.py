import os
import tempfile
import shutil
import unittest
from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.rkm.adapters import convert_to_rkm_records

class TestFrozenEngineCompatibility(unittest.TestCase):

    def test_adapter_accepts_existing_engine_output(self):
        """Adapter must successfully translate frozen engine outputs without modifying the engine."""
        temp_dir = tempfile.mkdtemp()
        try:
            src_dir = os.path.join(temp_dir, "mock_repo")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "app.py"), "w", encoding="utf-8") as f:
                f.write("import core\n")
            with open(os.path.join(src_dir, "core.py"), "w", encoding="utf-8") as f:
                f.write("pass\n")

            # Execute frozen engine directly (no changes to analyzer/scoring)
            codebase = analyzer.analyze_directory(src_dir)
            risks = scoring.evaluate_risks(codebase, ["app.py", "core.py"], repo_path=src_dir)
            
            # Map through RKM adapter
            records = convert_to_rkm_records(src_dir, codebase, risks)
            
            # Assert correct mapping to database entities
            self.assertIn("app.py", [f.path for f in records.files])
            self.assertIn("core.py", [f.path for f in records.files])
            self.assertTrue(len(records.metrics) > 0)
        finally:
            shutil.rmtree(temp_dir)
