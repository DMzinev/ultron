"""
test_adversarial_checkpoint_gating.py
=====================================
Comprehensive Adversarial Test Suite for Checkpoint & SafetyEvaluator Gating (Phase 1.4).
Attacks the Checkpoint & SafetyEvaluator gating system across 7 vectors:
  Vector 1: Disk file modified after readiness evaluated (filesystem reality divergence)
  Vector 2: Unrelated files modified
  Vector 3: Forbidden boundary files modified (normalization, case, traversal, prefix)
  Vector 4: Stale test results / failing tests / unexecuted tests
  Vector 5: Stale snapshot_id divergence
  Vector 6: Content hash / model hash mismatch
  Vector 7: Server restart / repository switch during unverified state
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from ultron.core.development_session import DevelopmentSessionManager, _SESSION_CACHE
from ultron.core.safety_evaluator import SafetyEvaluator
from ultron.core.system_model import SystemGraph, SystemNode, SystemEdge, SystemNodeType, SystemEdgeType


class TestAdversarialCheckpointGating(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_adv_chk_")
        self.sample_py = os.path.join(self.test_dir, "core_service.py")
        with open(self.sample_py, "w", encoding="utf-8") as f:
            f.write("def execute():\n    return 42\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        _SESSION_CACHE.clear()

    # -------------------------------------------------------------------------
    # Attack Vector 1: Disk file modified after readiness evaluated
    # -------------------------------------------------------------------------
    def test_vector1_disk_file_modified_after_readiness_blocks_checkpoint(self):
        """Verify that modifying, adding, or removing tracked files on disk after readiness causes STALE_READINESS."""
        mgr = DevelopmentSessionManager(self.test_dir)
        initial_hash = mgr.compute_current_filesystem_hash()
        snap_id = "snap_v1_001"

        mgr._session.latest_snapshot_id = snap_id
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "reason_codes": [],
            "snapshot_id": snap_id,
            "content_hash": initial_hash
        }

        # Baseline: Fresh state allows checkpoint
        valid_res = mgr.create_checkpoint(description="Clean baseline", force=False)
        self.assertTrue(valid_res["success"])
        self.assertEqual(valid_res["checkpoint"]["snapshot_id"], snap_id)

        # 1.1 Modify existing tracked file on disk
        with open(self.sample_py, "a", encoding="utf-8") as f:
            f.write("\ndef unanalyzed_mutation():\n    pass\n")

        res_mod = mgr.create_checkpoint(description="Attempt after modifying file", force=False)
        self.assertFalse(res_mod["success"])
        self.assertEqual(res_mod.get("error_code"), "STALE_READINESS")
        self.assertEqual(res_mod.get("decision"), "PAUSE & REVIEW")
        self.assertIn("modified on disk", res_mod.get("error", "").lower())

        # 1.2 Add a new source file on disk
        new_source = os.path.join(self.test_dir, "untracked_new.py")
        with open(new_source, "w", encoding="utf-8") as f:
            f.write("def rogue(): pass\n")

        res_add = mgr.create_checkpoint(description="Attempt after adding file", force=False)
        self.assertFalse(res_add["success"])
        self.assertEqual(res_add.get("error_code"), "STALE_READINESS")

        # 1.3 Delete a source file on disk
        os.remove(new_source)
        os.remove(self.sample_py)

        res_del = mgr.create_checkpoint(description="Attempt after deleting file", force=False)
        self.assertFalse(res_del["success"])
        self.assertEqual(res_del.get("error_code"), "STALE_READINESS")

    def test_vector1_ignored_non_source_files_do_not_falsely_block_fresh_state(self):
        """Verify that non-source files (e.g. .log, .tmp, .txt) do not alter content hash or block valid checkpoints."""
        mgr = DevelopmentSessionManager(self.test_dir)
        initial_hash = mgr.compute_current_filesystem_hash()
        snap_id = "snap_v1_002"

        mgr._session.latest_snapshot_id = snap_id
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "reason_codes": [],
            "snapshot_id": snap_id,
            "content_hash": initial_hash
        }

        # Create ignored log file
        log_file = os.path.join(self.test_dir, "runtime.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("INFO: Task completed successfully\n")

        # Hash remains unchanged and checkpoint succeeds
        self.assertEqual(mgr.compute_current_filesystem_hash(), initial_hash)
        res = mgr.create_checkpoint(description="Checkpoint with runtime log", force=False)
        self.assertTrue(res["success"])

    # -------------------------------------------------------------------------
    # Attack Vector 2: Unrelated files modified
    # -------------------------------------------------------------------------
    def test_vector2_unrelated_files_modified_blocks_readiness(self):
        """Verify that modifying files outside task boundary or declared constraints triggers BOUNDARY_VIOLATION."""
        constraints = [
            "Do not modify ultron/core/billing.py",
            "Forbidden: database/schema.sql",
            "never touch config/security_keys.json"
        ]

        # Case A: Touching forbidden billing.py
        report_a = SafetyEvaluator.evaluate(
            test_results={"passed": True, "failed_count": 0, "passed_count": 10},
            modified_files=["ultron/core/billing.py"],
            boundary_constraints=constraints
        )
        self.assertFalse(report_a.safe_to_continue)
        self.assertEqual(report_a.badge, "PAUSE & REVIEW")
        self.assertIn("BOUNDARY_VIOLATION", report_a.reason_codes)
        self.assertTrue(any("billing.py" in b for b in report_a.blocking_conditions))

        # Case B: Touching forbidden database schema
        report_b = SafetyEvaluator.evaluate(
            test_results={"passed": True, "failed_count": 0, "passed_count": 10},
            modified_files=["database/schema.sql"],
            boundary_constraints=constraints
        )
        self.assertFalse(report_b.safe_to_continue)
        self.assertIn("BOUNDARY_VIOLATION", report_b.reason_codes)

        # Case C: Touching only authorized files
        report_c = SafetyEvaluator.evaluate(
            test_results={"passed": True, "failed_count": 0, "passed_count": 10},
            modified_files=["ultron/core/feature_module.py"],
            boundary_constraints=constraints
        )
        self.assertTrue(report_c.safe_to_continue)
        self.assertEqual(report_c.badge, "CONTINUE BUILDING")
        self.assertEqual(len(report_c.blocking_conditions), 0)

    # -------------------------------------------------------------------------
    # Attack Vector 3: Forbidden boundary files modified (Normalization & Traversal)
    # -------------------------------------------------------------------------
    def test_vector3_path_obfuscation_and_case_normalization_blocked(self):
        """Verify that boundary violations cannot be bypassed with Windows backslashes, mixed case, or relative paths."""
        constraints = ["Do not touch ultron/core/sentinel.py", "Forbidden: security/keys.py"]

        obfuscated_variants = [
            "ultron\\core\\sentinel.py",
            "ULTRON/CORE/SENTINEL.PY",
            "./ultron/core/sentinel.py",
            "security\\keys.py",
            "SECURITY/KEYS.PY"
        ]

        for variant in obfuscated_variants:
            report = SafetyEvaluator.evaluate(
                test_results={"passed": True, "failed_count": 0, "passed_count": 5},
                modified_files=[variant],
                boundary_constraints=constraints
            )
            self.assertFalse(report.safe_to_continue, f"Failed to block obfuscated path: {variant}")
            self.assertIn("BOUNDARY_VIOLATION", report.reason_codes, f"Missing BOUNDARY_VIOLATION code for: {variant}")

        # Direct parameter forbidden_files_modified
        report_direct = SafetyEvaluator.evaluate(
            test_results={"passed": True, "failed_count": 0, "passed_count": 5},
            forbidden_files_modified=["ultron/core/sentinel.py"]
        )
        self.assertFalse(report_direct.safe_to_continue)
        self.assertIn("BOUNDARY_VIOLATION", report_direct.reason_codes)

    # -------------------------------------------------------------------------
    # Attack Vector 4: Stale test results / failing tests
    # -------------------------------------------------------------------------
    def test_vector4_stale_or_failing_tests_strictly_blocked(self):
        """Verify that missing test evidence or failing assertions strictly PAUSE and block checkpoint."""
        # 4.1 Unexecuted tests (None)
        rep_unexecuted = SafetyEvaluator.evaluate(test_results=None)
        self.assertFalse(rep_unexecuted.safe_to_continue)
        self.assertEqual(rep_unexecuted.badge, "PAUSE & REVIEW")
        self.assertIn("TESTS_UNEXECUTED", rep_unexecuted.reason_codes)

        # 4.2 Failing test suite
        rep_failing = SafetyEvaluator.evaluate(
            test_results={"passed": False, "failed_count": 2, "passed_count": 18}
        )
        self.assertFalse(rep_failing.safe_to_continue)
        self.assertIn("TESTS_FAILING", rep_failing.reason_codes)

        # 4.3 Direct test_failures_count
        rep_count = SafetyEvaluator.evaluate(test_failures_count=4)
        self.assertFalse(rep_count.safe_to_continue)
        self.assertIn("TESTS_FAILING", rep_count.reason_codes)

        # 4.4 Checkpoint creation gate blocks when safety assessment contains test failures
        mgr = DevelopmentSessionManager(self.test_dir)
        mgr._session.latest_snapshot_id = "snap_test_fail_01"
        mgr._session.safety_assessment = rep_failing.to_dict()
        mgr._session.safety_assessment["snapshot_id"] = "snap_test_fail_01"
        mgr._session.safety_assessment["content_hash"] = mgr.compute_current_filesystem_hash()

        res_chk = mgr.create_checkpoint(description="Attempt checkpoint with failing tests", force=False)
        self.assertFalse(res_chk["success"])
        self.assertEqual(res_chk.get("error_code"), "READINESS_BLOCKED")
        self.assertEqual(res_chk.get("decision"), "PAUSE & REVIEW")
        self.assertIn("TESTS_FAILING", res_chk.get("reason_codes", []))

    # -------------------------------------------------------------------------
    # Attack Vector 5: Stale snapshot_id
    # -------------------------------------------------------------------------
    def test_vector5_stale_snapshot_id_divergence_blocks_checkpoint(self):
        """Verify checkpoint rejects when safety assessment was evaluated on an older snapshot than session."""
        mgr = DevelopmentSessionManager(self.test_dir)
        fs_hash = mgr.compute_current_filesystem_hash()

        mgr._session.latest_snapshot_id = "snap_session_current_500"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "reason_codes": [],
            "snapshot_id": "snap_stale_ancestor_100",  # Divergence
            "content_hash": fs_hash
        }

        res = mgr.create_checkpoint(description="Attempt checkpoint on stale snapshot", force=False)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("error_code"), "STALE_READINESS")
        self.assertEqual(res.get("decision"), "PAUSE & REVIEW")
        self.assertIn("snap_stale_ancestor_100", res.get("error", ""))
        self.assertIn("snap_session_current_500", res.get("error", ""))

    # -------------------------------------------------------------------------
    # Attack Vector 6: Content hash / model hash mismatch
    # -------------------------------------------------------------------------
    def test_vector6_tampered_content_hash_mismatch_blocks_checkpoint(self):
        """Verify that tampered or mismatched content hash is rejected."""
        mgr = DevelopmentSessionManager(self.test_dir)
        
        mgr._session.latest_snapshot_id = "snap_hash_test_600"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "reason_codes": [],
            "snapshot_id": "snap_hash_test_600",
            "content_hash": "fabricated_sha256_hash_9999999999",
            "model_hash": "model_hash_600"
        }

        res = mgr.create_checkpoint(description="Attempt checkpoint with fabricated content hash", force=False)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("error_code"), "STALE_READINESS")
        self.assertIn("modified on disk", res.get("error", "").lower())

    # -------------------------------------------------------------------------
    # Attack Vector 7: Server restart / repository switch during unverified state
    # -------------------------------------------------------------------------
    def test_vector7_server_restart_and_repo_switch_isolation(self):
        """Verify persistence across server restarts and strict workspace isolation between repositories."""
        repo_a_dir = tempfile.mkdtemp(prefix="adv_repo_a_")
        repo_b_dir = tempfile.mkdtemp(prefix="adv_repo_b_")
        try:
            # 1. Repo A has unverified / paused state
            mgr_a = DevelopmentSessionManager(repo_a_dir)
            mgr_a._session.status = "paused"
            mgr_a._session.latest_snapshot_id = "snap_a_10"
            mgr_a._session.safety_assessment = {
                "safe_to_continue": False,
                "decision": "PAUSE & REVIEW",
                "blocking_conditions": ["Unresolved regression in Repo A"],
                "reason_codes": ["TESTS_FAILING"],
                "snapshot_id": "snap_a_10"
            }
            mgr_a._persist(mgr_a._session)

            # 2. Repo B has clean verified state
            mgr_b = DevelopmentSessionManager(repo_b_dir)
            fs_hash_b = mgr_b.compute_current_filesystem_hash()
            mgr_b._session.latest_snapshot_id = "snap_b_10"
            mgr_b._session.safety_assessment = {
                "safe_to_continue": True,
                "decision": "CONTINUE BUILDING",
                "blocking_conditions": [],
                "reason_codes": [],
                "snapshot_id": "snap_b_10",
                "content_hash": fs_hash_b
            }
            mgr_b._persist(mgr_b._session)

            # Verify Repo B can create checkpoint
            chk_b = mgr_b.create_checkpoint(description="Verified Repo B milestone", force=False)
            self.assertTrue(chk_b["success"])

            # Verify Repo A is blocked
            chk_a = mgr_a.create_checkpoint(description="Repo A attempt", force=False)
            self.assertFalse(chk_a["success"])
            self.assertEqual(chk_a.get("error_code"), "READINESS_BLOCKED")

            # 3. Simulate Server Restart: Wipe memory cache and re-initialize from disk
            _SESSION_CACHE.clear()

            restarted_mgr_a = DevelopmentSessionManager(repo_a_dir)
            self.assertEqual(restarted_mgr_a._session.status, "paused")
            self.assertFalse(restarted_mgr_a._session.safety_assessment.get("safe_to_continue"))

            # Checkpoint attempt after restart on unverified state must still be blocked
            chk_restarted_a = restarted_mgr_a.create_checkpoint(description="Attempt after restart", force=False)
            self.assertFalse(chk_restarted_a["success"])
            self.assertEqual(chk_restarted_a.get("error_code"), "READINESS_BLOCKED")

        finally:
            shutil.rmtree(repo_a_dir, ignore_errors=True)
            shutil.rmtree(repo_b_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # REST API Layer Gating Tests (/api/v1/checkpoint)
    # -------------------------------------------------------------------------
    def test_api_v1_create_checkpoint_accepts_valid_and_blocks_invalid(self):
        """Verify REST API POST /api/v1/checkpoint returns 200 on valid state and 400 with actionable error codes on invalid/stale state."""
        import io
        from ultron.interfaces.server import UltronAPIHandler

        mgr = DevelopmentSessionManager(self.test_dir)
        fs_hash = mgr.compute_current_filesystem_hash()
        snap_id = "snap_api_test_100"

        # Case 1: Clean, verified state -> HTTP 200
        mgr._session.latest_snapshot_id = snap_id
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "reason_codes": [],
            "snapshot_id": snap_id,
            "content_hash": fs_hash
        }
        mgr._persist(mgr._session)

        handler_200 = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_200.path = "/api/v1/checkpoint"
        handler_200.wfile = io.BytesIO()
        handler_200.headers = {}
        handler_200.get_post_data = lambda: {"repo": self.test_dir, "description": "API verified checkpoint"}
        
        status_codes_200 = []
        payloads_200 = []
        def fake_send_json_200(code, data):
            status_codes_200.append(code)
            payloads_200.append(data)
        handler_200.send_json_response = fake_send_json_200

        handler_200.handle_v1_create_checkpoint()

        self.assertEqual(status_codes_200, [200])
        self.assertTrue(payloads_200[0]["success"])
        self.assertTrue(payloads_200[0]["checkpoint_id"].startswith("chk_"))
        self.assertEqual(payloads_200[0]["checkpoint"]["snapshot_id"], snap_id)

        # Case 2: Modify file on disk -> HTTP 400 with STALE_READINESS
        with open(self.sample_py, "a", encoding="utf-8") as f:
            f.write("\ndef rogue_modification(): pass\n")

        handler_400 = UltronAPIHandler.__new__(UltronAPIHandler)
        handler_400.path = "/api/v1/checkpoint"
        handler_400.wfile = io.BytesIO()
        handler_400.headers = {}
        handler_400.get_post_data = lambda: {"repo": self.test_dir, "description": "API stale checkpoint attempt"}

        status_codes_400 = []
        payloads_400 = []
        def fake_send_json_400(code, data):
            status_codes_400.append(code)
            payloads_400.append(data)
        handler_400.send_json_response = fake_send_json_400

        handler_400.handle_v1_create_checkpoint()

        self.assertEqual(status_codes_400, [400])
        self.assertFalse(payloads_400[0]["success"])
        self.assertEqual(payloads_400[0]["error_code"], "STALE_READINESS")
        self.assertEqual(payloads_400[0]["decision"], "PAUSE & REVIEW")
        self.assertTrue(len(payloads_400[0]["blocking_conditions"]) > 0)


if __name__ == "__main__":
    unittest.main()
