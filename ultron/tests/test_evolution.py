import os
import unittest
import sqlite3
import json
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import (
    RepositoryMetadata, AnalysisRun, FileRecord, MetricRecord, DependencyRecord,
    RkmRule, RkmRuleInstance, RkmViolation, RkmEvaluation, EvaluationStatus, RkmEntityHistory
)
from ultron.core.rkm.evolution.engine import EvolutionEngine
from ultron.interfaces.api import HistoryAPI, MetricsAPI, ViolationsAPI

class TestEvolution(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite DB
        self.db_path = ":memory:"
        self.store = RepositoryStore(self.db_path)
        
        # Seed initial metadata
        self.meta_id = self.store.save_metadata(RepositoryMetadata(
            id=None,
            repository_uuid="repo-test-uuid",
            name="test-repo",
            root_path="/dummy/root",
            language="Python",
            size=1000,
            rkm_version="1.3.0",
            minimum_reader_version="1.3.0",
            maximum_writer_version="1.x",
            latest_analysis_run_id=None
        ))

    def tearDown(self):
        self.store.close()

    def test_dynamic_run_comparison_deltas(self):
        # Create Run 1
        run1_id = self.store.save_analysis_run(AnalysisRun(
            id=None, repository_id=self.meta_id, timestamp="2026-07-20T10:00:00Z",
            duration=1.2, engine_version="1.3.0", rkm_version="1.3.0",
            content_hash="h1", previous_run_id=None, rule_pack_version="1.0.0",
            semantic_hash="sh1", archived=0, semantic_hash_strategy="ast"
        ))
        
        f1_id = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run1_id, path="math_ops.py",
            role="module", package="core", size=200, last_modified="now",
            created_at=None, updated_at=None
        ))
        self.store.save_metrics([MetricRecord(id=None, file_id=f1_id, name="complexity", value=5.0, created_at=None, updated_at=None)])

        # Create Run 2
        run2_id = self.store.save_analysis_run(AnalysisRun(
            id=None, repository_id=self.meta_id, timestamp="2026-07-20T10:05:00Z",
            duration=1.3, engine_version="1.3.0", rkm_version="1.3.0",
            content_hash="h2", previous_run_id=run1_id, rule_pack_version="1.0.0",
            semantic_hash="sh2", archived=0, semantic_hash_strategy="ast"
        ))
        
        # math_ops.py updated complexity, new file added utils.py
        f1_v2 = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run2_id, path="math_ops.py",
            role="module", package="core", size=220, last_modified="now",
            created_at=None, updated_at=None
        ))
        f2_v2 = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run2_id, path="utils.py",
            role="module", package="core", size=100, last_modified="now",
            created_at=None, updated_at=None
        ))
        
        self.store.save_metrics([
            MetricRecord(id=None, file_id=f1_v2, name="complexity", value=8.0, created_at=None, updated_at=None),
            MetricRecord(id=None, file_id=f2_v2, name="complexity", value=2.0, created_at=None, updated_at=None)
        ])

        # Dynamic comparison
        deltas = EvolutionEngine.compare_runs(self.store, run1_id, run2_id)
        
        # Verify additions and modifications
        added_paths = [d.entity_identifier for d in deltas if d.delta_type == "file_added"]
        self.assertIn("utils.py", added_paths)
        
        increased_metrics = [d.entity_identifier for d in deltas if d.delta_type == "metric_increased"]
        self.assertIn("math_ops.py:complexity", increased_metrics)

    def test_dynamic_trend_computations(self):
        # Create a series of 3 runs to establish trend
        prev_id = None
        for i, complexity_val in enumerate([4.0, 6.0, 9.0]):
            run_id = self.store.save_analysis_run(AnalysisRun(
                id=None, repository_id=self.meta_id, timestamp=f"2026-07-20T10:0{i}:00Z",
                duration=1.0, engine_version="1.3.0", rkm_version="1.3.0",
                content_hash=f"h{i}", previous_run_id=prev_id, rule_pack_version="1.0.0",
                semantic_hash=f"sh{i}", archived=0, semantic_hash_strategy="ast"
            ))
            f_id = self.store.save_file(FileRecord(
                id=None, analysis_run_id=run_id, path="math_ops.py",
                role="module", package="core", size=200, last_modified="now",
                created_at=None, updated_at=None
            ))
            self.store.save_metrics([MetricRecord(id=None, file_id=f_id, name="complexity", value=complexity_val, created_at=None, updated_at=None)])
            prev_id = run_id

        trends = EvolutionEngine.compute_trends(self.store, prev_id)
        # Find complexity trend for math_ops.py
        comp_trend = next((t for t in trends if t.entity_identifier == "math_ops.py" and t.metric_name == "complexity"), None)
        self.assertIsNotNone(comp_trend)
        self.assertEqual(comp_trend.direction, "increasing")
        self.assertGreater(comp_trend.velocity, 0.0)

    def test_dynamic_hotspot_scoring(self):
        # Create analysis run
        run_id = self.store.save_analysis_run(AnalysisRun(
            id=None, repository_id=self.meta_id, timestamp="2026-07-20T11:00:00Z",
            duration=1.0, engine_version="1.3.0", rkm_version="1.3.0",
            content_hash="h1", previous_run_id=None, rule_pack_version="1.0.0",
            semantic_hash="sh1", archived=0, semantic_hash_strategy="ast"
        ))
        
        f_id = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run_id, path="math_ops.py",
            role="module", package="core", size=300, last_modified="now",
            created_at=None, updated_at=None
        ))
        self.store.save_metrics([
            MetricRecord(id=None, file_id=f_id, name="complexity", value=10.0, created_at=None, updated_at=None),
            MetricRecord(id=None, file_id=f_id, name="coupling", value=2.0, created_at=None, updated_at=None)
        ])
        
        # Seed 3 modifications in history
        self.store.save_entity_history([
            RkmEntityHistory(None, "file", "math_ops.py", run_id, "modified"),
            RkmEntityHistory(None, "file", "math_ops.py", run_id, "modified"),
            RkmEntityHistory(None, "file", "math_ops.py", run_id, "modified")
        ])
        
        hotspots = EvolutionEngine.detect_hotspots(self.store, run_id)
        math_hotspot = next((h for h in hotspots if h.file_path == "math_ops.py"), None)
        self.assertIsNotNone(math_hotspot)
        self.assertEqual(math_hotspot.change_count, 1) # Deduplicated unique count per run
        self.assertGreaterEqual(math_hotspot.hotspot_score, 2.0)

    def test_impact_paths(self):
        run_id = self.store.save_analysis_run(AnalysisRun(
            id=None, repository_id=self.meta_id, timestamp="2026-07-20T12:00:00Z",
            duration=1.0, engine_version="1.3.0", rkm_version="1.3.0",
            content_hash="h1", previous_run_id=None, rule_pack_version="1.0.0",
            semantic_hash="sh1", archived=0, semantic_hash_strategy="ast"
        ))
        
        f1_id = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run_id, path="a.py",
            role="module", package="core", size=100, last_modified="now",
            created_at=None, updated_at=None
        ))
        f2_id = self.store.save_file(FileRecord(
            id=None, analysis_run_id=run_id, path="b.py",
            role="module", package="core", size=100, last_modified="now",
            created_at=None, updated_at=None
        ))
        
        # a.py depends on b.py
        self.store.save_dependencies([DependencyRecord(
            id=None, file_id=f1_id, target_path="b"
        )])
        
        impact = EvolutionEngine.perform_impact_analysis(self.store, run_id, ["b.py"])
        self.assertIn("a.py", impact["impacted_files"])
        self.assertIn("b.py", impact["impacted_files"])
