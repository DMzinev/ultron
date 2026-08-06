import os
import tempfile
import shutil
import json
import unittest
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RepositoryMetadata, AnalysisRun, FileRecord
from ultron.core.rkm.snapshot import export_snapshot, import_snapshot

class TestSnapshot(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "original.db")
        self.snapshot_path = os.path.join(self.temp_dir, "snapshot.json")
        self.target_db_path = os.path.join(self.temp_dir, "imported.db")

        # Setup mock database with some data
        store = RepositoryStore(self.db_path)
        try:
            with store.transaction():
                meta = RepositoryMetadata(
                    id=1,
                    repository_uuid="repo-uuid-1234",
                    name="test_repo",
                    root_path="/mock/root",
                    language="Python",
                    size=1200,
                    rkm_version="1.3.0",
                    minimum_reader_version="1.3.0",
                    maximum_writer_version="1.x",
                    latest_analysis_run_id=None
                )
                meta_id = store.save_metadata(meta)
                
                run = AnalysisRun(
                    id=None,
                    repository_id=meta_id,
                    timestamp="2026-07-14T10:00:00",
                    duration=1.5,
                    engine_version="1.1.0",
                    rkm_version="1.3.0",
                    content_hash="mock-hash-abc",
                    previous_run_id=None
                )
                run_id = store.save_analysis_run(run)
                store.update_latest_analysis_run(meta_id, run_id)

                f = FileRecord(
                    id=None,
                    analysis_run_id=run_id,
                    path="main.py",
                    role="entrypoint",
                    package="core",
                    size=120,
                    last_modified="2026-07-14T10:00:00",
                    created_at=None,
                    updated_at=None
                )
                store.save_file(f)
        finally:
            store.close()


    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_snapshot_export_import_roundtrip(self):
        """Export a database to JSON, import it, and assert database identities."""
        # 1. Export snapshot
        export_snapshot(self.db_path, self.snapshot_path)
        self.assertTrue(os.path.exists(self.snapshot_path))

        with open(self.snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["snapshot_version"], "1.0.0")
        self.assertEqual(data["rkm_version"], "1.3.0")
        self.assertEqual(data["metadata"]["repository_uuid"], "repo-uuid-1234")
        self.assertEqual(len(data["analysis_runs"]), 1)
        self.assertEqual(data["analysis_runs"][0]["content_hash"], "mock-hash-abc")

        # 2. Import snapshot to fresh database
        import_snapshot(self.target_db_path, self.snapshot_path)
        self.assertTrue(os.path.exists(self.target_db_path))

        # 3. Assert imported database records
        imported_store = RepositoryStore(self.target_db_path)
        try:
            meta = imported_store.get_metadata()
            self.assertIsNotNone(meta)
            self.assertEqual(meta.repository_uuid, "repo-uuid-1234")
            self.assertEqual(meta.name, "test_repo")

            runs = imported_store.get_analysis_runs()
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0].content_hash, "mock-hash-abc")

            files = imported_store.get_files()
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].path, "main.py")
        finally:
            imported_store.close()

    def test_import_invalid_json_raises_value_error(self):
        """Importing invalid snapshot files must raise ValueError instead of raw system exceptions."""
        # 1. Empty/missing path
        with self.assertRaises(ValueError):
            import_snapshot(self.target_db_path, "nonexistent_file.json")

        # 2. Corrupted JSON file
        corrupt_file = os.path.join(self.temp_dir, "corrupt.json")
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{invalid json")

        with self.assertRaises(ValueError):
            import_snapshot(self.target_db_path, corrupt_file)

        # 3. Missing compatibility blocks
        invalid_structure = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_structure, "w", encoding="utf-8") as f:
            json.dump({"files": []}, f)

        with self.assertRaises(ValueError):
            import_snapshot(self.target_db_path, invalid_structure)
