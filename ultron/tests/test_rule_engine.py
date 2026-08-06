import os
import tempfile
import shutil
import unittest
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import (
    RepositoryMetadata, AnalysisRun, FileRecord, MetricRecord,
    DependencyRecord, RkmRule, RkmRuleInstance, RkmEvaluation, RkmViolation,
    RkmViolationEvidence, EvaluationStatus, RkmManifest
)
from ultron.core.rkm.engine import ConstraintEngine

class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.store = RepositoryStore(self.db_path)

        # Setup mock metadata and analysis run
        with self.store.transaction():
            meta = RepositoryMetadata(
                id=1,
                repository_uuid="repo-uuid-5678",
                name="test_repo",
                root_path="/mock/root",
                language="Python",
                size=2000,
                rkm_version="1.2.0",
                minimum_reader_version="1.2.0",
                maximum_writer_version="1.x",
                latest_analysis_run_id=None
            )
            self.metadata_id = self.store.save_metadata(meta)

            self.run = AnalysisRun(
                id=None,
                repository_id=self.metadata_id,
                timestamp="2026-07-15T12:00:00",
                duration=0.5,
                engine_version="1.2.0",
                rkm_version="1.2.0",
                content_hash="mock-hash-def",
                previous_run_id=None,
                semantic_hash="mock-semantic-hash",
                semantic_hash_strategy="AST"
            )
            self.run_id = self.store.save_analysis_run(self.run)
            self.store.update_latest_analysis_run(self.metadata_id, self.run_id)

            # Save two files
            self.file_1 = FileRecord(
                id=None,
                analysis_run_id=self.run_id,
                path="main.py",
                role="CLI",
                package="core",
                size=500,
                last_modified="2026-07-15T12:00:00",
                created_at=None,
                updated_at=None
            )
            self.file_1_id = self.store.save_file(self.file_1)

            self.file_2 = FileRecord(
                id=None,
                analysis_run_id=self.run_id,
                path="ultron/core/analyzer.py",
                role="Internal",
                package="core",
                size=600,
                last_modified="2026-07-15T12:00:00",
                created_at=None,
                updated_at=None
            )
            self.file_2_id = self.store.save_file(self.file_2)

            # Save metrics
            self.metric_comp = MetricRecord(None, self.file_1_id, "complexity", 20.0, None, None)
            self.metric_coup = MetricRecord(None, self.file_1_id, "coupling", 12.0, None, None)
            self.store.save_metrics([self.metric_comp, self.metric_coup])
            
            # Retrieve saved metrics to fetch database IDs
            saved_metrics = self.store.get_metrics(self.file_1_id)
            self.comp_metric_id = next(m.id for m in saved_metrics if m.name == "complexity")
            self.coup_metric_id = next(m.id for m in saved_metrics if m.name == "coupling")

            # Save dependencies
            dep = DependencyRecord(None, self.file_1_id, "ultron.core.analyzer")
            self.store.save_dependencies([dep])
            saved_deps = self.store.get_dependencies(self.file_1_id)
            self.dep_id = saved_deps[0].id

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir)

    def test_rules_and_instances_persistence(self):
        # 1. Save rules and instances
        rules = [
            RkmRule("complexity_limit", "default", "Complexity Limit", "Check complexity", "complexity_limit", "1.0.0"),
            RkmRule("layer_restriction", "default", "Layer Restriction", "Check layers", "layer_restriction", "1.0.0")
        ]
        self.store.save_rules(rules)

        instances = [
            RkmRuleInstance(None, "complexity_limit", 1, "warning", {"max": 15}, "1.0.0"),
            RkmRuleInstance(None, "layer_restriction", 1, "error", {"source_pattern": "main.py", "target_pattern": "ultron/core/*"}, "1.0.0")
        ]
        self.store.save_rule_instances(instances)

        # 2. Assert retrieved rules/instances match
        ret_rules = self.store.get_rules()
        self.assertEqual(len(ret_rules), 2)
        self.assertEqual(ret_rules[0].id, "complexity_limit")

        ret_insts = self.store.get_rule_instances()
        self.assertEqual(len(ret_insts), 2)
        self.assertEqual(ret_insts[0].predicate_config, {"max": 15})

    def test_stateless_constraint_plugins(self):
        engine = ConstraintEngine()
        
        # Define rule & instance config
        rule_comp = RkmRule("complexity_limit", "default", "Complexity Limit", "Check complexity", "complexity_limit", "1.0.0")
        config_comp = {"max": 15}

        # Evaluate Complexity constraint plugin
        plugin_comp = engine.plugins["complexity_limit"]
        violations = plugin_comp.evaluate(self.store, self.run_id, rule_comp, config_comp)
        
        self.assertEqual(len(violations), 1)
        vio, evidences = violations[0]
        self.assertEqual(vio.file_id, self.file_1_id)
        self.assertIn("complexity is 20", vio.details)
        self.assertEqual(len(evidences), 1)
        self.assertEqual(evidences[0].evidence_type, "metric")
        self.assertEqual(evidences[0].evidence_id, self.comp_metric_id)

    def test_layer_restriction_plugin(self):
        engine = ConstraintEngine()
        rule_layer = RkmRule("layer_restriction", "default", "Layer Restriction", "Check layers", "layer_restriction", "1.0.0")
        config_layer = {"source_pattern": "main.py", "target_pattern": "ultron/core/*"}

        plugin_layer = engine.plugins["layer_restriction"]
        violations = plugin_layer.evaluate(self.store, self.run_id, rule_layer, config_layer)
        
        self.assertEqual(len(violations), 1)
        vio, evidences = violations[0]
        self.assertEqual(vio.file_id, self.file_1_id)
        self.assertIn("Dependency boundary violation", vio.details)
        self.assertEqual(len(evidences), 1)
        self.assertEqual(evidences[0].evidence_type, "dependency")
        self.assertEqual(evidences[0].evidence_id, self.dep_id)

    def test_evaluations_and_violations_persistence(self):
        # 1. Save rule definition first (to satisfy FK constraints)
        rule = RkmRule("complexity_limit", "default", "Complexity Limit", "Check complexity", "complexity_limit", "1.0.0")
        self.store.save_rules([rule])

        # 2. Save rule instance
        inst = RkmRuleInstance(None, "complexity_limit", 1, "warning", {"max": 15}, "1.0.0")
        self.store.save_rule_instances([inst])

        # 3. Save evaluation
        ev = RkmEvaluation(
            id=None,
            analysis_run_id=self.run_id,
            rule_id="complexity_limit",
            status=EvaluationStatus.FAILED,
            started_at="2026-07-15T12:00:00",
            finished_at="2026-07-15T12:00:01",
            duration_ms=100,
            engine_version="1.2.0",
            rule_version="1.0.0"
        )
        ev_id = self.store.save_evaluations([ev])[0]

        # 4. Save violation and evidence
        vio = RkmViolation(
            id=None,
            evaluation_id=ev_id,
            file_id=self.file_1_id,
            symbol_id=None,
            details="Complexity too high"
        )
        evidence = RkmViolationEvidence(
            id=None,
            violation_id=None,
            evidence_type="metric",
            evidence_id=self.comp_metric_id
        )
        self.store.save_violations([(vio, [evidence])])

        # 5. Fetch violations and assert evidence link correctness
        violations_list = self.store.get_violations(self.run_id)
        self.assertEqual(len(violations_list), 1)
        
        vio_ret, rule_ret, evidences_ret = violations_list[0]
        self.assertEqual(vio_ret.details, "Complexity too high")
        self.assertEqual(rule_ret.id, "complexity_limit")
        self.assertEqual(len(evidences_ret), 1)
        self.assertEqual(evidences_ret[0].evidence_type, "metric")
        self.assertEqual(evidences_ret[0].evidence_id, self.comp_metric_id)

    def test_manifest_immutability(self):
        # Initial manifest insert
        manifest = RkmManifest(
            repository_uuid="repo-uuid-5678",
            schema_version="1.2.0",
            minimum_reader_version="1.2.0",
            maximum_writer_version="1.x",
            engine_version="1.2.0",
            rule_pack_version="1.0.0",
            snapshot_version="1.0.0"
        )
        self.store.save_manifest(manifest)

        # Re-saving manifest should raise RuntimeError (singleton enforcement)
        with self.assertRaises(RuntimeError):
            self.store.save_manifest(manifest)
            
        # Altering mutable fields via update_manifest should succeed
        self.store.update_manifest(
            engine_version="1.3.0",
            rule_pack_version="2.0.0",
            snapshot_version="1.1.0"
        )
        ret_manifest = self.store.get_manifest()
        self.assertEqual(ret_manifest.engine_version, "1.3.0")
        self.assertEqual(ret_manifest.rule_pack_version, "2.0.0")
        self.assertEqual(ret_manifest.repository_uuid, "repo-uuid-5678")

if __name__ == "__main__":
    unittest.main()
