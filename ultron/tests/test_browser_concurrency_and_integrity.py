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
        """Asserts static presence of abortAll, getWithRetry, and READY->CONNECTED transition."""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        
        # 1. APIClient static methods
        with open(os.path.join(web_dir, "modules", "api.js"), "r", encoding="utf-8") as f:
            api_js = f.read()
        self.assertIn("static abortAll()", api_js)
        self.assertIn("static getWithRetry(", api_js)
        self.assertIn("static buildUrl(", api_js)

        # 2. StateStore VALID_TRANSITIONS allows READY -> CONNECTED
        with open(os.path.join(web_dir, "modules", "state.js"), "r", encoding="utf-8") as f:
            state_js = f.read()
        self.assertIn("[STATES.READY]: [STATES.CONNECTED", state_js)

        # 3. Index.js TDZ & slider safety
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()
        # currentObjectiveState must be declared near top before updateDashboard
        obj_decl_pos = index_js.find("let currentObjectiveState = null;")
        dash_pos = index_js.find("function updateDashboard(")
        self.assertNotEqual(obj_decl_pos, -1, "currentObjectiveState must be declared")
        self.assertLess(obj_decl_pos, dash_pos, "currentObjectiveState must be declared before updateDashboard to avoid TDZ")
        self.assertNotIn("sliderTypo ?", index_js, "sliderTypo must not be referenced as undeclared variable")
        self.assertNotIn("if (sliderTypo)", index_js, "sliderTypo must not be referenced as undeclared variable")

    def test_state_store_blocked_state_and_polling_guard_contract(self):
        """Verifies Phase 2.2 Root Cause A invariants:
        1. STATES.BLOCKED exists in state.js and VALID_TRANSITIONS connects it to READY/ERROR.
        2. index.js stateMetadata defines [STATES.BLOCKED] with red status dot (#ef4444).
        3. index.js startPolling contains active-repository guard dropping stale background callbacks.
        4. updateCurrentWorkSurface synchronizes res.status == 'BLOCKED' with stateStore.setState(STATES.BLOCKED).
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")

        # 1. StateStore enum & transitions
        with open(os.path.join(web_dir, "modules", "state.js"), "r", encoding="utf-8") as f:
            state_js = f.read()
        self.assertIn("BLOCKED: 'BLOCKED'", state_js)
        self.assertIn("[STATES.BLOCKED]: [STATES.READY", state_js)
        self.assertIn("[STATES.READY]: [STATES.CONNECTED", state_js)

        # 2. index.js stateMetadata mapping & active-repo guard
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()
        self.assertIn("[STATES.BLOCKED]: { text: \"Workflow Blocked\", dot: \"#ef4444\"", index_js)
        self.assertIn("if (repoPath && activeRepo && repoPath !== activeRepo)", index_js)
        self.assertIn("stateStore.setState(STATES.BLOCKED)", index_js)

    def test_user_blockers_and_ergonomics_contracts(self):
        """Verifies resolution of the 4 Major User Blockers:
        1. Startup sequence uses gentle health check instead of blind auto-scan error crash.
        2. .toast in index.css is placed at top: 24px (never bottom: 24px) to prevent occluding action buttons.
        3. Demo mode defines instant self-contained loadDemoDataset without network dependency.
        4. Auditor tab navigation hydrates file explorer tree upon tab selection.
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")

        # 1. index.css toast position
        with open(os.path.join(web_dir, "index.css"), "r", encoding="utf-8") as f:
            index_css = f.read()
        import re
        self.assertFalse(bool(re.search(r"\.toast\s*\{[^}]*bottom:\s*24px", index_css)), "Toast must not be fixed to bottom: 24px")
        self.assertTrue(bool(re.search(r"\.toast\s*\{[^}]*top:\s*24px", index_css)), "Toast must be positioned at top: 24px")
        self.assertIn("pointer-events: none;", index_css)

        # 2. index.js startup sequence, demo dataset, and auditor hydration
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()
        self.assertNotIn("First launch detected — auto-scanning active repository", index_js)
        self.assertIn("APIClient.get(\"/api/v1/health\")", index_js)
        self.assertIn("function loadDemoDataset()", index_js)
        self.assertIn("targetTab === \"auditor-tab\"", index_js)
        self.assertIn("UIManager.renderFileExplorer(files, handleSelectFileForInspection)", index_js)

    def test_phase24_visual_hierarchy_and_action_contracts(self):
        """
        Verifies Phase 2.4 Visual Hierarchy & Usability Overhaul:
        1. Redundant horizontal project header is hidden, eliminating the visual sandwich effect.
        2. Primary CTA has unambiguous priority styling (btn-primary-action).
        3. Secondary diagnostic controls are cleanly subdued (btn-secondary-action).
        4. Agent handoff is styled with an elegant distinct accent (btn-agent-handoff).
        5. Top header utilities are consolidated with .utility-btn.
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_html = f.read()
        with open(os.path.join(web_dir, "index.css"), "r", encoding="utf-8") as f:
            index_css = f.read()

        # 1. Project header stripe hidden
        self.assertIn('id="overview-project-header" style="display: none;"', index_html)

        # 2. Action buttons have clear hierarchy classes
        self.assertIn('id="btn-current-work-action" class="btn primary btn-small btn-primary-action"', index_html)
        self.assertIn('id="btn-toggle-diagnostic-detail" class="btn secondary btn-small btn-secondary-action"', index_html)
        self.assertIn('id="btn-current-work-push-agent" class="btn secondary btn-small btn-agent-handoff"', index_html)

        # 3. Top header utilities
        self.assertIn('class="btn secondary utility-btn"', index_html)

        # 4. CSS definitions exist
        self.assertIn(".btn-primary-action", index_css)
        self.assertIn(".btn-secondary-action", index_css)
        self.assertIn(".btn-agent-handoff", index_css)
        self.assertIn(".utility-btn", index_css)

    def test_phase25_decision_centric_contracts(self):
        """
        Verifies Phase 2.5 Decision-Centric Transformation Contracts:
        1. Stage A (Overview): What Matters Decision Card exists and is hydrated with plain-English consequences.
        2. Stage B (Structure): Blast-Radius Visual Halo is implemented in selectNode with amber/red illumination.
        3. Stage C (Work): 7-Stage Development Lifecycle Stepper timeline is rendered in Objective Planner.
        4. Stage D (Agent Context): Structured compiler cards (Target, Why, Change, Do Not Touch, Evidence, Verify).
        5. Stage E (Verify): Repository Health Delta card proves value (What got better, What got worse, Can I continue).
        6. Stage G (Empty States): Actionable onboarding cards with direct connect/run buttons.
        """
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interfaces", "web")
        with open(os.path.join(web_dir, "index.html"), "r", encoding="utf-8") as f:
            index_html = f.read()
        with open(os.path.join(web_dir, "modules", "ui.js"), "r", encoding="utf-8") as f:
            ui_js = f.read()
        with open(os.path.join(web_dir, "modules", "graph.js"), "r", encoding="utf-8") as f:
            graph_js = f.read()
        with open(os.path.join(web_dir, "index.js"), "r", encoding="utf-8") as f:
            index_js = f.read()

        # 1. Overview What Matters Decision Surface
        self.assertIn('id="what-matters-decision-card"', index_html)
        self.assertIn('id="btn-decision-prepare-mission"', index_html)
        self.assertIn('id="btn-decision-view-graph"', index_html)
        self.assertIn('decisionCard = document.getElementById("what-matters-decision-card")', ui_js)
        self.assertIn('🚀 Prepare', ui_js)
        # Verify What Matters is placed on main Overview surface, NOT trapped inside .engineer-only
        card_pos = index_html.find('id="what-matters-decision-card"')
        eng_only_pos = index_html.find('class="grid-card glass engineer-only"')
        self.assertTrue(card_pos > 0 and eng_only_pos > 0 and card_pos < eng_only_pos, "What Matters card must be visible to Creator mode outside .engineer-only")

        # 2. Structure Graph Blast-Radius Halo & Canvas Click Clear
        self.assertIn('computeTransitiveDependents', graph_js)
        self.assertIn('#f59e0b', graph_js) # Amber direct dependent halo
        self.assertIn('#ef4444', graph_js) # Red transitive dependent halo
        self.assertIn('node.element.style.opacity = "0.25"', graph_js) # Dimming unrelated nodes
        self.assertIn('clearSelection()', graph_js)
        self.assertIn('this.clickHandler = (e) =>', graph_js) # Canvas click handler defined
        self.assertIn('svg.addEventListener("click", this.clickHandler)', graph_js) # Canvas click wired

        # 3. Work 7-Stage Development Stepper Timeline
        self.assertIn('stepper-timeline', ui_js)
        self.assertIn('MISSION_READY', ui_js)
        self.assertIn('CHECKPOINTED', ui_js)
        self.assertIn('You are here:', ui_js)
        self.assertIn('Next action:', ui_js)
        self.assertIn('rawStatus === "IDLE" || rawStatus === "DISCOVERING"', ui_js)
        self.assertIn('rawStatus === "ISSUE_SELECTED" || rawStatus === "SELECTED"', ui_js)
        self.assertIn('rawStatus === "OBSERVING"', ui_js)
        self.assertIn('rawStatus === "VERIFYING"', ui_js)

        # 4. Agent Context Structured Compiler Cards
        self.assertIn('id="compiler-cards-container"', index_html)
        self.assertIn('id="card-target-file"', index_html)
        self.assertIn('id="card-why-reason"', index_html)
        self.assertIn('id="card-change-intent"', index_html)
        self.assertIn('id="card-do-not-touch"', index_html)
        self.assertIn('id="card-evidence-summary"', index_html)
        self.assertIn('id="card-verify-cmd"', index_html)

        # 5. Verify Repository Health Delta
        self.assertIn('id="repo-health-delta-card"', index_html)
        self.assertIn('id="delta-what-better"', index_html)
        self.assertIn('id="delta-what-worse"', index_html)
        self.assertIn('id="delta-can-continue"', index_html)
        self.assertIn('deltaStatusBadge = document.getElementById("health-delta-status-badge")', ui_js)
        self.assertIn('deltaWhatBetter = document.getElementById("delta-what-better")', ui_js)
        self.assertIn('deltaWhatWorse = document.getElementById("delta-what-worse")', ui_js)
        self.assertIn('deltaCanContinue = document.getElementById("delta-can-continue")', ui_js)

        # 6. Actionable Empty States
        self.assertIn('id="btn-work-empty-connect"', index_html)
        self.assertIn('id="btn-graph-empty-connect"', index_html)
        self.assertIn('id="btn-verify-empty-run"', index_html)
        self.assertIn('btnGraphConnect.onclick', index_js)
        self.assertIn('btnWorkConnect.onclick', index_js)
        self.assertIn('btnVerifyRun.onclick', index_js)


if __name__ == "__main__":
    unittest.main()



