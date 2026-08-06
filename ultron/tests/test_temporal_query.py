import os
import tempfile
import shutil
import unittest
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.query import QueryRepository
from ultron.core.rkm.schema import (
    RepositoryMetadata, AnalysisRun, FileRecord, MetricRecord, FactRecord, DependencyRecord
)

class TestTemporalQuery(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_temporal.db")

        # Create multi-run timeline history
        store = RepositoryStore(self.db_path)
        try:
            with store.transaction():
                meta = RepositoryMetadata(
                    id=1,
                    repository_uuid="repo-uuid-5678",
                    name="temporal_repo",
                    root_path="/mock/root",
                    language="Python",
                    size=2000,
                    rkm_version="1.2.0",
                    minimum_reader_version="1.2.0",
                    maximum_writer_version="1.x",
                    latest_analysis_run_id=None
                )
                meta_id = store.save_metadata(meta)

                # --- RUN 1 ---
                run_1 = AnalysisRun(
                    id=None,
                    repository_id=meta_id,
                    timestamp="2026-07-14T09:00:00",
                    duration=1.0,
                    engine_version="1.1.0",
                    rkm_version="1.2.0",
                    content_hash="hash-1",
                    previous_run_id=None
                )
                run_id_1 = store.save_analysis_run(run_1)
                store.update_latest_analysis_run(meta_id, run_id_1)

                file_1_r1 = FileRecord(
                    id=None,
                    analysis_run_id=run_id_1,
                    path="main.py",
                    role="entrypoint",
                    package="core",
                    size=100,
                    last_modified="2026-07-14T09:00:00",
                    created_at=None,
                    updated_at=None
                )
                file_1_id_r1 = store.save_file(file_1_r1)

                # Add metric & dependency for main.py in Run 1
                store.save_metrics([MetricRecord(None, file_1_id_r1, "complexity", 5.0, None, None)])
                store.save_dependencies([DependencyRecord(None, file_1_id_r1, "helper")])

                # --- RUN 2 ---
                run_2 = AnalysisRun(
                    id=None,
                    repository_id=meta_id,
                    timestamp="2026-07-14T10:00:00",
                    duration=1.1,
                    engine_version="1.1.0",
                    rkm_version="1.2.0",
                    content_hash="hash-2",
                    previous_run_id=run_id_1
                )
                run_id_2 = store.save_analysis_run(run_2)
                store.update_latest_analysis_run(meta_id, run_id_2)

                file_1_r2 = FileRecord(
                    id=None,
                    analysis_run_id=run_id_2,
                    path="main.py",
                    role="entrypoint",
                    package="core",
                    size=150,  # size changed!
                    last_modified="2026-07-14T10:00:00",
                    created_at=None,
                    updated_at=None
                )
                file_1_id_r2 = store.save_file(file_1_r2)

                # Metric changed from 5.0 -> 8.0!
                store.save_metrics([MetricRecord(None, file_1_id_r2, "complexity", 8.0, None, None)])
                store.save_dependencies([
                    DependencyRecord(None, file_1_id_r2, "helper"),
                    DependencyRecord(None, file_1_id_r2, "db")  # dependency added!
                ])

                # Added a new file in Run 2
                file_2_r2 = FileRecord(
                    id=None,
                    analysis_run_id=run_id_2,
                    path="db.py",
                    role="database",
                    package="core",
                    size=200,
                    last_modified="2026-07-14T10:00:00",
                    created_at=None,
                    updated_at=None
                )
                store.save_file(file_2_r2)
        finally:
            store.close()


        self.query = QueryRepository(self.db_path)

    def tearDown(self):
        self.query.close()
        shutil.rmtree(self.temp_dir)

    def test_get_analysis_history(self):
        """Query RKM analysis run history timeline."""
        history = self.query.get_analysis_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content_hash"], "hash-1")
        self.assertEqual(history[1]["content_hash"], "hash-2")
        self.assertEqual(history[1]["previous_run_id"], history[0]["id"])

    def test_compare_runs(self):
        """Compare two analysis runs and assert metric/dependency/file changes."""
        # Retrieve run IDs
        history = self.query.get_analysis_history()
        run_id_1 = history[0]["id"]
        run_id_2 = history[1]["id"]

        comparison = self.query.compare_runs(run_id_1, run_id_2)

        # Added files assertion
        self.assertEqual(comparison.added_files, ["db.py"])
        self.assertEqual(comparison.removed_files, [])
        self.assertEqual(comparison.modified_files, ["main.py"])

        # Delta metrics assertions
        self.assertIn("main.py", comparison.metric_delta)
        main_metrics = comparison.metric_delta["main.py"]
        self.assertIn("complexity", main_metrics)
        self.assertEqual(main_metrics["complexity"]["before"], 5.0)
        self.assertEqual(main_metrics["complexity"]["after"], 8.0)
        self.assertEqual(main_metrics["complexity"]["delta"], 3.0)

        # Delta dependencies assertions
        self.assertIn("main.py", comparison.dependency_delta)
        main_deps = comparison.dependency_delta["main.py"]
        self.assertEqual(main_deps["added"], ["db"])
        self.assertEqual(main_deps["removed"], [])

    def test_compare_invalid_runs_raises_exception(self):
        """compare_runs must raise ValueError when given non-existent run IDs."""
        with self.assertRaises(ValueError):
            self.query.compare_runs(9999, 8888)

    def test_get_file_history_timeline(self):
        """Track history progression of a specific file."""
        history = self.query.get_file_history("main.py")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["size"], 100)
        self.assertEqual(history[1]["size"], 150)
        self.assertEqual(history[0]["metrics"]["complexity"], 5.0)
        self.assertEqual(history[1]["metrics"]["complexity"], 8.0)

    def test_path_normalization_and_validation(self):
        """Query methods normalize path separators and validate input parameters."""
        # 1. Backslash normalization on Windows paths
        history = self.query.get_file_history("core\\..\\main.py")
        # Since we use simple path replacement: core/../main.py
        self.assertEqual(len(self.query.get_file_history("core\\..\\main.py")), 0) # Path normalized but doesn't exist
        
        # Test exact match normalization
        self.assertEqual(len(self.query.get_file_history("core\\main.py")), 0)
        
        # 2. Strict guards validation check raising TypeError or ValueError
        with self.assertRaises(TypeError):
            self.query.get_file_history(None)
        with self.assertRaises(TypeError):
            self.query.get_file_history(1234)
        with self.assertRaises(ValueError):
            self.query.get_file_history("")
        with self.assertRaises(ValueError):
            self.query.get_file_history("   ")
