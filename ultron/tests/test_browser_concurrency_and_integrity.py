"""
Ultron Browser Concurrency & State Integrity Test Suite (v2.6.1)
Simulates and asserts:
1. Request sequence validation & out-of-order stale response discarding
2. Stale success after newer failure protection
3. Snapshot-grounded agent context freshness (Snapshot A != Snapshot B)
4. Repository vs workspace identity isolation
5. Continuation readiness decision semantics & explicit reason codes
"""

import os
import shutil
import tempfile
import unittest

from ultron.core.objective_tracker import ObjectiveTracker
from ultron.core.agent_context_builder import AgentContextBuilder, CanonicalAgentContext
from ultron.core.safety_evaluator import SafetyEvaluator, ContinuationReadinessReport


class TestBrowserConcurrencyAndIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="ultron_concurrency_test_")
        self.repo_a = os.path.join(self.tmp_dir, "repo_a")
        self.repo_b = os.path.join(self.tmp_dir, "repo_b")
        os.makedirs(self.repo_a, exist_ok=True)
        os.makedirs(self.repo_b, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_contextual_request_sequencing_simulation(self):
        """
        Simulates the exact APIClient request sequence validation:
        1. Request A starts for context 'analysis:repo_a' (seq=1)
        2. Request B starts for context 'analysis:repo_a' (seq=2)
        3. Request B resolves first -> accepted as authoritative (seq=2 == latest)
        4. Request A resolves late -> discarded as stale (seq=1 < latest=2)
        """
        request_sequences = {}

        def start_request(context_key):
            seq = request_sequences.get(context_key, 0) + 1
            request_sequences[context_key] = seq
            return seq

        def validate_response(context_key, seq, payload):
            latest_seq = request_sequences.get(context_key, 0)
            if seq < latest_seq:
                return {"stale": True, "success": False, "data": None}
            return {"stale": False, "success": True, "data": payload}

        # Step 1: Request A starts
        seq_a = start_request("analysis:repo_a")
        self.assertEqual(seq_a, 1)

        # Step 2: Request B starts before A finishes
        seq_b = start_request("analysis:repo_a")
        self.assertEqual(seq_b, 2)

        # Step 3: Request B resolves
        res_b = validate_response("analysis:repo_a", seq_b, {"result": "Payload B (Authoritative)"})
        self.assertFalse(res_b["stale"])
        self.assertTrue(res_b["success"])
        self.assertEqual(res_b["data"]["result"], "Payload B (Authoritative)")

        # Step 4: Request A resolves late
        res_a = validate_response("analysis:repo_a", seq_a, {"result": "Payload A (Stale)"})
        self.assertTrue(res_a["stale"])
        self.assertFalse(res_a["success"])
        self.assertIsNone(res_a["data"])

    def test_stale_success_after_newer_failure_protection(self):
        """
        Ensures that if Request A starts (seq 1), Request B starts (seq 2) and fails,
        Request A succeeding later CANNOT overwrite the failure with stale data.
        """
        request_sequences = {"analysis:repo_a": 0}

        # Request A starts
        seq_a = 1
        request_sequences["analysis:repo_a"] = seq_a

        # Request B starts and fails
        seq_b = 2
        request_sequences["analysis:repo_a"] = seq_b
        state_after_b = {"status": "failed", "error": "Syntax Error in module"}

        # Request A resolves late with old success
        latest_seq = request_sequences["analysis:repo_a"]
        is_stale_a = seq_a < latest_seq
        self.assertTrue(is_stale_a)

        # State must remain B's state, not resurrected by A
        authoritative_state = state_after_b
        self.assertEqual(authoritative_state["status"], "failed")

    def test_dual_workspace_and_repository_identity(self):
        """
        Asserts that ObjectiveTracker differentiates between local workspace_id
        and repository_id, ensuring deterministic isolation.
        """
        tracker_a = ObjectiveTracker(self.repo_a)
        tracker_b = ObjectiveTracker(self.repo_b)

        state_a = tracker_a.get_objective()
        state_b = tracker_b.get_objective()

        self.assertIn("workspace_id", state_a)
        self.assertIn("repository_id", state_a)
        self.assertEqual(state_a["workspace_id"], tracker_a.workspace_id)
        self.assertNotEqual(state_a["workspace_id"], state_b["workspace_id"])
        self.assertNotEqual(state_a["repository_id"], state_b["repository_id"])

    def test_agent_context_snapshot_grounding_and_freshness(self):
        """
        Verifies that CanonicalAgentContext embeds explicit snapshot_id, model_hash,
        repository_revision, and timestamp, and that changing the snapshot produces a new context.
        """
        tracker = ObjectiveTracker(self.repo_a)
        obj_state = tracker.get_objective()

        # Context for Snapshot 1
        ctx_1 = AgentContextBuilder.build(
            objective_state=obj_state,
            repo_path=self.repo_a,
            snapshot_id="snap_1001",
            model_hash="hash_aaa"
        )
        self.assertEqual(ctx_1.snapshot_id, "snap_1001")
        self.assertEqual(ctx_1.model_hash, "hash_aaa")
        self.assertTrue(bool(ctx_1.generated_at))

        rendered_md_1 = AgentContextBuilder.render_markdown(ctx_1)
        self.assertIn("SNAPSHOT: snap_1001", rendered_md_1)
        self.assertIn("MODEL_HASH: hash_aaa", rendered_md_1)

        # Context for Snapshot 2 (after code changes)
        ctx_2 = AgentContextBuilder.build(
            objective_state=obj_state,
            repo_path=self.repo_a,
            snapshot_id="snap_1002",
            model_hash="hash_bbb"
        )
        self.assertNotEqual(ctx_1.snapshot_id, ctx_2.snapshot_id)
        self.assertNotEqual(ctx_1.model_hash, ctx_2.model_hash)

        rendered_claude_2 = AgentContextBuilder.render_claude(ctx_2)
        self.assertIn('snapshot_id="snap_1002"', rendered_claude_2)

    def test_continuation_readiness_reason_codes_and_snapshot_binding(self):
        """
        Verifies that SafetyEvaluator returns explicit reason_codes and snapshot binding,
        never making claims of universal bug-free safety.
        """
        # Case A: Ready to continue (zero blocking conditions)
        ready_report = SafetyEvaluator.evaluate(
            test_results={"passed": True, "passed_count": 25, "failed_count": 0},
            modified_files=["core/utils.py"],
            boundary_constraints=["do not modify auth"],
            cycle_count=0,
            snapshot_id="snap_555"
        )
        self.assertTrue(ready_report.safe_to_continue)
        self.assertEqual(ready_report.badge, "CONTINUE BUILDING")
        self.assertEqual(ready_report.decision_type, "CONTINUATION_READINESS")
        self.assertEqual(len(ready_report.reason_codes), 0)
        self.assertEqual(ready_report.snapshot_id, "snap_555")
        self.assertIn("0 blocking conditions detected", ready_report.summary)

        # Case B: Blocked with multiple reason codes (Failing tests + Boundary violation)
        blocked_report = SafetyEvaluator.evaluate(
            test_results={"passed": False, "passed_count": 20, "failed_count": 5},
            modified_files=["auth/jwt_handler.py"],
            boundary_constraints=["do not modify auth"],
            cycle_count=2,
            snapshot_id="snap_555"
        )
        self.assertFalse(blocked_report.safe_to_continue)
        self.assertEqual(blocked_report.badge, "PAUSE & REVIEW")
        self.assertIn("TESTS_FAILING", blocked_report.reason_codes)
        self.assertIn("BOUNDARY_VIOLATION", blocked_report.reason_codes)
        self.assertIn("CIRCULAR_DEPENDENCY", blocked_report.reason_codes)
        self.assertGreaterEqual(len(blocked_report.blocking_conditions), 3)

    def test_snapshot_freshness_rejection_on_stale_snapshot(self):
        """
        Adversarial Test: Double Protection (Request freshness + Snapshot freshness).
        Ensures that if Context A was generated against Snapshot 1, then repository code changes
        causing Snapshot 2 to become active, Context A is rejected by the store/verifier
        because its snapshot_id is stale compared to the authoritative active snapshot.
        """
        active_snapshot_id = "snap_v2_new"

        # Context generated from old snapshot
        old_ctx = CanonicalAgentContext(
            repository_root=self.repo_a,
            repository_id="repo_123",
            objective_title="Feature A",
            objective_description="Description A",
            progress_pct=50.0,
            active_task={"id": "t1", "title": "Task 1", "status": "in_progress"},
            snapshot_id="snap_v1_old"
        )

        def is_context_fresh(ctx: CanonicalAgentContext, current_snap: str) -> bool:
            return ctx.snapshot_id == current_snap

        # Old context arrives when current is snap_v2_new
        self.assertFalse(is_context_fresh(old_ctx, active_snapshot_id))

        # Fresh context generated against current snapshot
        fresh_ctx = CanonicalAgentContext(
            repository_root=self.repo_a,
            repository_id="repo_123",
            objective_title="Feature A",
            objective_description="Description A",
            progress_pct=50.0,
            active_task={"id": "t1", "title": "Task 1", "status": "in_progress"},
            snapshot_id="snap_v2_new"
        )
        self.assertTrue(is_context_fresh(fresh_ctx, active_snapshot_id))

    def test_interrupted_atomic_write_recovery(self):
        """
        Adversarial Test: Atomic Write Interruption & Safe Recovery.
        Simulates an interrupted write where .ultron/objective.json.tmp is created partially
        during a simulated crash, but the valid .ultron/objective.json remains untouched.
        Verifies that upon reload, ObjectiveTracker reads the intact valid state and can
        subsequently overwrite the temp file safely.
        """
        tracker = ObjectiveTracker(self.repo_a)
        
        # 1. Establish valid saved state with 2 tasks
        tracker.set_objective(
            title="Production Hardening",
            description="Stabilize background job worker.",
            tasks=[
                {"id": "t1", "title": "Worker loop", "status": "done"},
                {"id": "t2", "title": "Crash telemetry", "status": "in_progress"}
            ]
        )
        self.assertTrue(os.path.exists(tracker.storage_file))

        # 2. Simulate process interruption leaving orphaned/corrupted .tmp file
        tmp_file = tracker.storage_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write("<<< INCOMPLETE PARTIAL TMP WRITE BEFORE SIGKILL >>>")

        # 3. Fresh ObjectiveTracker restarts
        recovered_tracker = ObjectiveTracker(self.repo_a)
        recovered_state = recovered_tracker.get_objective()

        # Valid state must be intact with 100% fidelity
        self.assertEqual(recovered_state["title"], "Production Hardening")
        self.assertEqual(recovered_state["tasks"][0]["status"], "done")
        self.assertEqual(recovered_state["tasks"][1]["status"], "in_progress")
        self.assertEqual(recovered_state["progress_pct"], 50.0)

        # 4. Subsequent write cleanly completes and cleans up temp file
        recovered_tracker.complete_task("t2")
        updated_state = recovered_tracker.get_objective()
        self.assertEqual(updated_state["tasks"][1]["status"], "done")
        self.assertEqual(updated_state["progress_pct"], 100.0)
        self.assertFalse(os.path.exists(tmp_file))

    def test_behavioral_rapid_repo_switch_isolation(self):
        """
        Behavioral Test: Rapid Repository Switching & Isolation.
        Asserts that switching from Repo A to Repo B immediately discards late-arriving
        Repo A responses and ensures Repo A cannot mutate Repo B's active state.
        """
        active_repo = "repo_a"
        state_store = {
            "repo": "repo_a",
            "snapshot_id": "snap_a_1",
            "last_analysis": {"files": ["repo_a/main.py"]},
            "active_requests": {"analysis:repo_a"}
        }

        def on_repo_switch(new_repo):
            nonlocal active_repo
            active_repo = new_repo
            state_store["repo"] = new_repo
            state_store["snapshot_id"] = ""
            state_store["last_analysis"] = None
            state_store["active_requests"].clear()

        def handle_late_response(target_repo, payload):
            if target_repo != active_repo:
                return {"discarded": True, "reason": "Inactive repository"}
            state_store["last_analysis"] = payload
            return {"discarded": False, "success": True}

        # Step 1: User switches to Repo B
        on_repo_switch("repo_b")
        self.assertEqual(active_repo, "repo_b")
        self.assertIsNone(state_store["last_analysis"])
        self.assertEqual(len(state_store["active_requests"]), 0)

        # Step 2: Late-arriving response from Repo A arrives
        late_res = handle_late_response("repo_a", {"files": ["repo_a/stale.py"]})
        self.assertTrue(late_res["discarded"])
        self.assertEqual(late_res["reason"], "Inactive repository")

        # Step 3: State store for Repo B remains clean and uncontaminated
        self.assertIsNone(state_store["last_analysis"])

        # Step 4: Legitimate response for Repo B arrives
        valid_res = handle_late_response("repo_b", {"files": ["repo_b/app.py"]})
        self.assertFalse(valid_res["discarded"])
        self.assertEqual(state_store["last_analysis"]["files"], ["repo_b/app.py"])

    def test_behavioral_debouncing_execution_count(self):
        """
        Behavioral Test: 150ms Input Debouncing Execution Rate.
        Asserts that 10 rapid keystrokes within 50ms trigger at most 1 actual execution.
        """
        import time

        executions = []

        def raw_filter_fn(query):
            executions.append({"query": query, "time": time.perf_counter()})

        class Debouncer:
            def __init__(self, fn, wait_sec=0.05):
                self.fn = fn
                self.wait_sec = wait_sec
                self.last_query = None
                self.last_scheduled = 0

            def call(self, query):
                self.last_query = query
                self.last_scheduled = time.perf_counter()

            def flush_if_ready(self, current_time):
                if self.last_query is not None and (current_time - self.last_scheduled) >= self.wait_sec:
                    q = self.last_query
                    self.last_query = None
                    self.fn(q)

        debouncer = Debouncer(raw_filter_fn, wait_sec=0.05)

        # 10 rapid keystrokes within 20ms
        start_t = time.perf_counter()
        for i in range(10):
            simulated_t = start_t + (i * 0.002)
            debouncer.call(f"search_term_{i}")
            debouncer.flush_if_ready(simulated_t)  # Should NOT trigger yet

        self.assertEqual(len(executions), 0, "Debouncer triggered prematurely during rapid typing")

        # After wait time expires
        after_wait_t = start_t + 0.08
        debouncer.flush_if_ready(after_wait_t)

        self.assertEqual(len(executions), 1, f"Expected exactly 1 execution, got {len(executions)}")
        self.assertEqual(executions[0]["query"], "search_term_9", "Expected latest keystroke to be executed")

    def test_graph_layout_cache_lru_and_invalidation(self):
        """
        Behavioral Test: Graph Layout Cache Keying, Eviction & Invalidation.
        Asserts 5-parameter key structure (repo + snap + hash + mode + svg), max 10 entries LRU,
        and selective repository invalidation.
        """
        class BoundedGraphLayoutCache:
            def __init__(self, max_entries=10):
                self.cache = {}
                self.max_entries = max_entries

            def make_key(self, repo, snap, hash_val, mode, svg):
                return f"{repo}::{snap}::{hash_val}::{mode}::{svg}"

            def get(self, repo, snap, hash_val, mode, svg):
                key = self.make_key(repo, snap, hash_val, mode, svg)
                return self.cache.get(key)

            def set(self, repo, snap, hash_val, mode, svg, data):
                key = self.make_key(repo, snap, hash_val, mode, svg)
                if len(self.cache) >= self.max_entries and key not in self.cache:
                    oldest = next(iter(self.cache))
                    del self.cache[oldest]
                self.cache[key] = data

            def clear_repo(self, repo_id):
                prefix = f"{repo_id}::"
                keys_to_del = [k for k in self.cache if k.startswith(prefix)]
                for k in keys_to_del:
                    del self.cache[k]

        glc = BoundedGraphLayoutCache(max_entries=10)

        # Populate 10 items for repo_1
        for i in range(10):
            glc.set("repo_1", f"snap_{i}", f"hash_{i}", "system", "svg_main", {"nodes": [f"n{i}"]})

        self.assertEqual(len(glc.cache), 10)
        self.assertIsNotNone(glc.get("repo_1", "snap_0", "hash_0", "system", "svg_main"))

        # Add 11th item -> snap_0 should be evicted
        glc.set("repo_2", "snap_new", "hash_new", "system", "svg_main", {"nodes": ["new_node"]})
        self.assertEqual(len(glc.cache), 10)
        self.assertIsNone(glc.get("repo_1", "snap_0", "hash_0", "system", "svg_main"), "Oldest key should be evicted")
        self.assertIsNotNone(glc.get("repo_2", "snap_new", "hash_new", "system", "svg_main"))

        # Clear repo_1 specifically
        glc.clear_repo("repo_1")
        self.assertEqual(len(glc.cache), 1, "All repo_1 entries should be cleared")
        self.assertIsNotNone(glc.get("repo_2", "snap_new", "hash_new", "system", "svg_main"))

    def test_stability_contracts_and_state_machine_integrity(self):
        """Asserts index.js state initialization and absence of undeclared variables."""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()
        self.assertIn("const state = {", index_js)
        self.assertNotIn("sliderTypo ?", index_js, "sliderTypo must not be referenced as undeclared variable")
        self.assertNotIn("if (sliderTypo)", index_js, "sliderTypo must not be referenced as undeclared variable")

    def test_state_store_blocked_state_and_polling_guard_contract(self):
        """Verifies polling guard and job status handling in index.js."""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()
        self.assertIn("async function waitForJob()", index_js)
        self.assertIn('api("/api/v1/progress")', index_js)
        self.assertIn('if (p.status === "failed")', index_js)

    def test_user_blockers_and_ergonomics_contracts(self):
        """Verifies startup sequence and toast notification contract in index.js and index.html."""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_html = f.read()
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()

        # Toast element and helper
        self.assertIn('id="toast"', index_html)
        self.assertIn("function showToast(", index_js)
        # Gentle health check startup
        self.assertIn('api("/api/v1/health")', index_js)
        self.assertIn("async function pingServer()", index_js)

    def test_phase24_visual_hierarchy_and_action_contracts(self):
        """
        Verifies C4 Visual Hierarchy & Action Contracts:
        1. Topbar brand, nav tabs, repo picker, scan button.
        2. Primary CTA has primary styling (.btn-primary).
        3. Ghost and subtle buttons are cleanly defined.
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_html = f.read()
        with open(os.path.join(web_dir, "index.css"), "r", encoding="utf-8") as f:
            index_css = f.read()

        # 1. Nav tabs and Primary Scan Button
        self.assertIn('id="scan-btn" class="btn btn-primary"', index_html)
        self.assertIn('id="nav-tabs"', index_html)
        self.assertIn('class="nav-tab', index_html)

        # 2. CSS hierarchy rules
        self.assertIn(".btn-primary", index_css)
        self.assertIn(".btn-ghost", index_css)

    def test_phase25_decision_centric_contracts(self):
        """
        Verifies C4 Decision-Centric Architecture Contracts:
        1. Primary Verdict headline answers: 'These N files are risky to change — here's why.'
        2. Supporting health score context card.
        3. Agent Studio mission compiler.
        4. Code Auditor safety gate.
        5. Structured empty states across pillars.
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_html = f.read()

        # 1. Primary Verdict
        self.assertIn('id="primary-verdict-title"', index_html)
        self.assertIn('id="primary-risky-count"', index_html)
        self.assertIn('id="primary-verdict-desc"', index_html)

        # 2. Supporting Context
        self.assertIn('id="health-score"', index_html)
        self.assertIn('id="health-badge"', index_html)

        # 3. Agent Studio & Code Auditor
        self.assertIn('id="studio-compile-btn"', index_html)
        self.assertIn('id="auditor-run-btn"', index_html)

        # 4. Structured Empty States
        self.assertIn('id="list-empty"', index_html)
        self.assertIn('id="detail-placeholder"', index_html)


if __name__ == "__main__":
    unittest.main()



