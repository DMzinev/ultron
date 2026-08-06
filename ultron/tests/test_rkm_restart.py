import os
import tempfile
import shutil
import unittest
from ultron.core.pipeline.orchestrator import analyze_repository
from ultron.core.rkm.store import RepositoryStore

class TestRKMRestart(unittest.TestCase):

    def test_repository_survives_restart(self):
        """Ultron's database must survive execution restarts and retrieve identical records."""
        temp_dir = tempfile.mkdtemp()
        try:
            src_dir = os.path.join(temp_dir, "mock_repo")
            os.makedirs(src_dir)
            with open(os.path.join(src_dir, "app.py"), "w", encoding="utf-8") as f:
                f.write("import core\n")
            with open(os.path.join(src_dir, "core.py"), "w", encoding="utf-8") as f:
                f.write("pass\n")

            # 1. Run pipeline
            repo_uuid_1 = analyze_repository(src_dir)
            db_path = os.path.join(src_dir, ".ultron", "repository.db")

            # 2. Re-open DB from fresh Store instance (simulating restart)
            store = RepositoryStore(db_path)
            try:
                files = store.get_files()

                # 3. Assert facts are loaded correctly
                self.assertEqual(len(files), 2)
                self.assertTrue(any(f.path == "app.py" for f in files))
                self.assertTrue(any(f.path == "core.py" for f in files))
            finally:
                store.close()
        finally:
            shutil.rmtree(temp_dir)
