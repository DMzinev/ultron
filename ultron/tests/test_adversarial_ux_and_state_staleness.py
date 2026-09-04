"""
test_adversarial_ux_and_state_staleness.py
=========================================
Adversarial test suite targeting the 5 proof tightening vectors:
1. Filesystem & Snapshot State Staleness Gate (KANBAN-A01)
2. 3-Tier Structural Mission Quality Validator (KANBAN-A02)
3. Graph Edge Semantics & Transitive Blast Radius (KANBAN-A03)
4. Cross-Stage Stage-Level Snapshot Synchronization (KANBAN-A04)
5. Cross-Layer Contradiction Downgrade / Rejection
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

from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.development_session import DevelopmentSessionManager
from ultron.core.safety_evaluator import SafetyEvaluator
from ultron.core.system_model import SystemGraph, SystemNode, SystemEdge, SystemNodeType, SystemEdgeType


class TestAdversarialUXAndStateStaleness(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_adv_test_")
        # Create a sample python file in test repo
        self.sample_py = os.path.join(self.test_dir, "sample.py")
        with open(self.sample_py, "w", encoding="utf-8") as f:
            f.write("def calculate_total(a, b):\n    return a + b\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. State-Staleness Gate Tests (KANBAN-A01)
    # -------------------------------------------------------------
    def test_checkpoint_rejects_snapshot_id_divergence(self):
        """Verify checkpoint rejects when safety assessment was computed on an older snapshot."""
        mgr = DevelopmentSessionManager(self.test_dir)
        mgr._session.latest_snapshot_id = "snap_latest_100"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "snapshot_id": "snap_stale_001"  # Divergence
        }
        res = mgr.create_checkpoint(description="Stale snapshot checkpoint attempt", force=False)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("error_code"), "STALE_READINESS")
        self.assertIn("snap_stale_001", res["error"])

    def test_checkpoint_rejects_unrecalculated_filesystem_modifications(self):
        """Verify checkpoint rejects when files on disk were edited after safety evaluation."""
        mgr = DevelopmentSessionManager(self.test_dir)
        fs_hash_before = mgr.compute_current_filesystem_hash()

        mgr._session.latest_snapshot_id = "snap_current_200"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "snapshot_id": "snap_current_200",
            "content_hash": fs_hash_before
        }

        # Modify file on disk WITHOUT re-evaluating safety
        with open(self.sample_py, "a", encoding="utf-8") as f:
            f.write("\ndef unverified_function():\n    pass\n")

        res = mgr.create_checkpoint(description="Checkpoint after un-analyzed edit", force=False)
        self.assertFalse(res["success"])
        self.assertEqual(res.get("error_code"), "STALE_READINESS")
        self.assertIn("modified on disk", res["error"])

    def test_checkpoint_accepts_when_readiness_and_filesystem_are_fresh(self):
        """Verify checkpoint succeeds when snapshot and filesystem hashes match current reality."""
        mgr = DevelopmentSessionManager(self.test_dir)
        fs_hash_current = mgr.compute_current_filesystem_hash()

        mgr._session.latest_snapshot_id = "snap_fresh_300"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "snapshot_id": "snap_fresh_300",
            "content_hash": fs_hash_current
        }

        res = mgr.create_checkpoint(description="Fresh verified checkpoint", force=False)
        self.assertTrue(res["success"])
        self.assertTrue(res["checkpoint_id"].startswith("chk_"))
        self.assertEqual(res["checkpoint"]["snapshot_id"], "snap_fresh_300")

    # -------------------------------------------------------------
    # 2. 3-Tier Structural Mission Quality Tests (KANBAN-A02)
    # -------------------------------------------------------------
    def test_mission_validation_incomplete(self):
        """Verify INCOMPLETE classification when target or intent is missing."""
        res_no_target = AgentContextBuilder.validate_mission(target_file="", intent="Implement authentication")
        self.assertEqual(res_no_target["status"], "INCOMPLETE")
        self.assertFalse(res_no_target["is_valid"])
        self.assertIn("target_file", res_no_target["missing"])

        res_no_intent = AgentContextBuilder.validate_mission(target_file="auth.py", intent="")
        self.assertEqual(res_no_intent["status"], "INCOMPLETE")
        self.assertFalse(res_no_intent["is_valid"])
        self.assertIn("intent", res_no_intent["missing"])

    def test_mission_validation_weak(self):
        """Verify WEAK classification on vague intents or placeholder acceptance criteria."""
        # Generic vague intent
        res_vague = AgentContextBuilder.validate_mission(
            target_file="server.py",
            intent="fix stuff"
        )
        self.assertEqual(res_vague["status"], "WEAK")
        self.assertTrue(res_vague["is_valid"])
        self.assertFalse(res_vague["is_actionable"])
        self.assertIn("Intent is generic", res_vague["warnings"][0])

        # Trivial acceptance criteria
        res_trivial_crit = AgentContextBuilder.validate_mission(
            target_file="server.py",
            intent="Refactor request router for modularity",
            acceptance_criteria=["works", "ok"]
        )
        self.assertEqual(res_trivial_crit["status"], "WEAK")
        self.assertFalse(res_trivial_crit["is_actionable"])

    def test_mission_validation_ready(self):
        """Verify READY classification on concrete, actionable missions."""
        res_ready = AgentContextBuilder.validate_mission(
            target_file="server.py",
            intent="Implement token refresh endpoint to prevent expired session disconnects",
            acceptance_criteria=["POST /api/v1/auth/refresh returns 200 with new JWT", "Unit tests in test_auth.py pass with 100% assertions"]
        )
        self.assertEqual(res_ready["status"], "READY")
        self.assertTrue(res_ready["is_valid"])
        self.assertTrue(res_ready["is_actionable"])
        self.assertEqual(len(res_ready["warnings"]), 0)

    # -------------------------------------------------------------
    # 3. Graph Edge Semantics & Transitive Blast Radius (KANBAN-A03)
    # -------------------------------------------------------------
    def test_graph_metric_mathematical_consistency_on_dag_fixture(self):
        """
        Verify canonical edge semantics on DAG fixture:
        A -> B (A imports/depends on B)
        A -> C (A imports/depends on C)
        B -> D (B imports/depends on D)
        C -> E (C imports/depends on E)
        """
        graph = SystemGraph()
        for node_id in ["A", "B", "C", "D", "E"]:
            graph.add_node(SystemNode(id=node_id, type=SystemNodeType.MODULE, file_path=f"{node_id}.py"))

        # Add directed dependency edges (source imports target)
        graph.add_edge(SystemEdge(source_id="A", target_id="B", type=SystemEdgeType.IMPORTS))
        graph.add_edge(SystemEdge(source_id="A", target_id="C", type=SystemEdgeType.IMPORTS))
        graph.add_edge(SystemEdge(source_id="B", target_id="D", type=SystemEdgeType.IMPORTS))
        graph.add_edge(SystemEdge(source_id="C", target_id="E", type=SystemEdgeType.IMPORTS))

        # Invariant 1: Direct Dependencies (outgoing edges from u)
        self.assertEqual(sorted(graph.get_dependencies("A")), ["B", "C"])
        self.assertEqual(graph.get_dependencies("B"), ["D"])
        self.assertEqual(graph.get_dependencies("D"), [])

        # Invariant 2: Direct Dependents (incoming edges to u: who imports u)
        self.assertEqual(graph.get_dependents("A"), [])
        self.assertEqual(graph.get_dependents("B"), ["A"])
        self.assertEqual(graph.get_dependents("D"), ["B"])
        self.assertEqual(graph.get_dependents("E"), ["C"])

        # Invariant 3: Transitive Downstream Blast Radius (who breaks if u changes)
        # If D changes: B breaks directly, A breaks transitively => {B, A}
        # If E changes: C breaks directly, A breaks transitively => {C, A}
        # If A changes: nothing downstream breaks => {}
        def get_transitive_dependents(g: SystemGraph, start_node: str):
            visited = set()
            queue = [start_node]
            while queue:
                curr = queue.pop(0)
                for caller in g.get_dependents(curr):
                    if caller not in visited:
                        visited.add(caller)
                        queue.append(caller)
            return sorted(list(visited))

        self.assertEqual(get_transitive_dependents(graph, "D"), ["A", "B"])
        self.assertEqual(get_transitive_dependents(graph, "E"), ["A", "C"])
        self.assertEqual(get_transitive_dependents(graph, "B"), ["A"])
        self.assertEqual(get_transitive_dependents(graph, "A"), [])

    # -------------------------------------------------------------
    # 4. Cross-Layer Contradiction Rejection Tests
    # -------------------------------------------------------------
    def test_cross_layer_contradiction_rejection(self):
        """Verify contradictory states are safely rejected or downgraded."""
        # 1. Contradiction: test_failures > 0 cannot yield CONTINUE BUILDING
        report = SafetyEvaluator.evaluate(
            test_failures_count=2,
            forbidden_files_modified=[],
            cycle_count_delta=0,
            complexity_spike_delta=0.0
        )
        self.assertFalse(report.safe_to_continue)
        self.assertEqual(report.decision, "PAUSE & REVIEW")

        # 2. Contradiction: mission with empty acceptance criteria cannot be READY
        val = AgentContextBuilder.validate_mission(
            target_file="mod.py",
            intent="Complete refactoring without breakage",
            acceptance_criteria=[]
        )
        self.assertNotEqual(val["status"], "READY")
        self.assertEqual(val["status"], "WEAK")

    # -------------------------------------------------------------
    # 5. Phase 0.9.2 Hardening: TOCTOU, Cycles, and Anti-Jargon
    # -------------------------------------------------------------
    def test_checkpoint_toctou_content_hashes_and_divergence(self):
        """Verify TOCTOU fields and source vs ignored file modifications."""
        mgr = DevelopmentSessionManager(self.test_dir)
        fs_hash_initial = mgr.compute_current_filesystem_hash()

        mgr._session.latest_snapshot_id = "snap_toctou_101"
        mgr._session.safety_assessment = {
            "safe_to_continue": True,
            "decision": "CONTINUE BUILDING",
            "blocking_conditions": [],
            "snapshot_id": "snap_toctou_101",
            "content_hash": fs_hash_initial
        }

        # Successful checkpoint captures both hashes and immutability flag
        res_ok = mgr.create_checkpoint(description="Verified baseline", force=False)
        self.assertTrue(res_ok["success"])
        chk = res_ok["checkpoint"]
        self.assertEqual(chk["validated_content_hash"], fs_hash_initial)
        self.assertEqual(chk["checkpoint_content_hash"], fs_hash_initial)
        self.assertTrue(chk["is_content_immutable"])

        # Modifying non-tracked/ignored file (.log or .txt) does not break source content hash
        ignored_file = os.path.join(self.test_dir, "scratch.txt")
        with open(ignored_file, "w", encoding="utf-8") as f:
            f.write("temporary notes")

        fs_hash_after_txt = mgr.compute_current_filesystem_hash()
        self.assertEqual(fs_hash_initial, fs_hash_after_txt)

        # Modifying tracked source file (.py) changes hash and blocks checkpoint
        with open(self.sample_py, "a", encoding="utf-8") as f:
            f.write("\ndef extra_code(): pass\n")

        res_blocked = mgr.create_checkpoint(description="Attempt after tracked file edit", force=False)
        self.assertFalse(res_blocked["success"])
        self.assertEqual(res_blocked["error_code"], "STALE_READINESS")

    def test_graph_cyclic_topology_invariants_and_deduplication(self):
        """
        Verify circular dependency graph topology (A -> B -> C -> A):
        1. Direct dependencies: A -> B, B -> C, C -> A
        2. Direct dependents: A <- C, B <- A, C <- B
        3. Transitive traversal terminates cleanly without infinite loops.
        4. Transitive blast radius contains unique nodes and excludes origin from its own blast radius.
        """
        graph = SystemGraph()
        for nid in ["A", "B", "C"]:
            graph.add_node(SystemNode(id=nid, type=SystemNodeType.MODULE, file_path=f"{nid}.py"))

        # Form a circular dependency cycle: A -> B -> C -> A
        graph.add_edge(SystemEdge(source_id="A", target_id="B", type=SystemEdgeType.IMPORTS))
        graph.add_edge(SystemEdge(source_id="B", target_id="C", type=SystemEdgeType.IMPORTS))
        graph.add_edge(SystemEdge(source_id="C", target_id="A", type=SystemEdgeType.IMPORTS))

        # Direct dependencies (outgoing)
        self.assertEqual(graph.get_dependencies("A"), ["B"])
        self.assertEqual(graph.get_dependencies("B"), ["C"])
        self.assertEqual(graph.get_dependencies("C"), ["A"])

        # Direct dependents (incoming)
        self.assertEqual(graph.get_dependents("A"), ["C"])
        self.assertEqual(graph.get_dependents("B"), ["A"])
        self.assertEqual(graph.get_dependents("C"), ["B"])

        # Transitive dependents traversal (who breaks if A changes)
        # If A changes: B imports A? No, C imports A, so C breaks directly.
        # Then B imports C, so B breaks transitively.
        # Traversal must visit C then B and terminate without re-adding A.
        def get_cyclic_transitive_dependents(g: SystemGraph, origin: str):
            visited = set()
            queue = [origin]
            while queue:
                curr = queue.pop(0)
                for caller in g.get_dependents(curr):
                    if caller != origin and caller not in visited:
                        visited.add(caller)
                        queue.append(caller)
            return sorted(list(visited))

        blast_radius_a = get_cyclic_transitive_dependents(graph, "A")
        self.assertEqual(blast_radius_a, ["B", "C"])
        self.assertNotIn("A", blast_radius_a)
        self.assertEqual(len(blast_radius_a), 2)

    def test_mission_validation_anti_jargon_false_positive_defense(self):
        """
        Verify false positive defense: technical-sounding jargon with placeholder
        acceptance criteria must be downgraded to WEAK, while concrete missions pass as READY.
        """
        # Case 1: Jargon soup with hollow acceptance -> WEAK
        res_jargon = AgentContextBuilder.validate_mission(
            target_file="server.py",
            intent="Improve the distributed repository orchestration lifecycle architecture",
            acceptance_criteria=["System works correctly"]
        )
        self.assertEqual(res_jargon["status"], "WEAK")
        self.assertFalse(res_jargon["is_actionable"])
        self.assertIn("placeholder/trivial", res_jargon["warnings"][0])

        # Case 2: Concrete, bounded, actionable mission with verifiable criteria -> READY
        res_actionable = AgentContextBuilder.validate_mission(
            target_file="server.py",
            intent="Expose per-source evidence availability in the unified analysis payload without changing frozen core analysis.",
            acceptance_criteria=["Add ast/git/ai_proxy statuses and verify JSON response plus 358-test regression."]
        )
        self.assertEqual(res_actionable["status"], "READY")
        self.assertTrue(res_actionable["is_valid"])
        self.assertTrue(res_actionable["is_actionable"])
        self.assertEqual(len(res_actionable["warnings"]), 0)

if __name__ == "__main__":
    unittest.main()
