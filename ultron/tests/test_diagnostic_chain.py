import os
import tempfile
import shutil
import unittest
from ultron.core.pipeline.orchestrator import analyze_repository
from ultron.core.rkm.store import RepositoryStore

class TestDiagnosticChain(unittest.TestCase):

    def test_diagnostic_chain_integrity(self):
        """Ultron must preserve the reasoning structure: File -> Fact -> Interpretation -> Recommendation."""
        temp_dir = tempfile.mkdtemp()
        try:
            src_dir = os.path.join(temp_dir, "mock_repo")
            os.makedirs(src_dir)
            
            # Write a high-complexity, high-coupling hub file to trigger MEDIUM/HIGH risk evaluation
            with open(os.path.join(src_dir, "hub.py"), "w", encoding="utf-8") as f:
                f.write("def run_hub():\n")
                f.write("    if True: pass\n")
                f.write("    if True: pass\n")
                f.write("    if True: pass\n")
                f.write("    if True: pass\n")
                
            # Create downstream files calling the hub function to create coupling
            for i in range(3):
                with open(os.path.join(src_dir, f"dep_{i}.py"), "w", encoding="utf-8") as f:
                    f.write("import hub\n")
                    f.write("hub.run_hub()\n")

            repo_uuid = analyze_repository(src_dir)
            db_path = os.path.join(src_dir, ".ultron", "repository.db")
            
            store = RepositoryStore(db_path)
            try:
                files = store.get_files()
                hub_file = next((f for f in files if f.path == "hub.py"), None)
                self.assertIsNotNone(hub_file, "hub.py record must exist in DB")
                
                facts = store.get_facts(hub_file.id)
                self.assertTrue(len(facts) > 0, "Facts table must be populated")
                
                coupling_fact = next((f for f in facts if f.category == "coupling"), None)
                self.assertIsNotNone(coupling_fact, "coupling fact must be recorded")
                
                interpretations = store.get_interpretations(coupling_fact.id)
                self.assertTrue(len(interpretations) > 0, "Interpretations must exist for coupling fact")
                
                recs = store.get_recommendations(interpretations[0].id)
                self.assertTrue(len(recs) > 0, "Recommendations must exist for interpretations")
            finally:
                store.close()
        finally:
            shutil.rmtree(temp_dir)
