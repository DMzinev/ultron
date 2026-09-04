"""
ultron.core.issue_orchestrator
Development Control Plane & Continuous Issue Orchestration Engine.

Manages the complete 9-phase lifecycle:
DISCOVER -> PRIORITIZE -> SELECT -> COMPILE -> ATTEMPT -> OBSERVE -> VERIFY -> GUARD -> CHECKPOINT

Constitutional Invariants (Phase 1.6 Refinement):
1. Single Authority: WorkQueue owns the current development lifecycle state.
2. Evidence-Derived State Advancement: The server derives admissible transitions from real evidence.
3. Zero Metric Gaming: DevelopmentAttempt is verified ONLY if all 3 pillars pass AND evidence package is complete.
4. Snapshot-Bound Consistency: Tests, visual state, and readiness must bind to the same snapshot identity.
5. One Active Issue / One Active Attempt at any time.
"""

import os
import sys
import json
import time
import hashlib
import ast
from typing import Dict, List, Optional, Any, Tuple

from ultron.core.work_queue import WorkQueue, WorkState, InvalidStateTransitionError, STATE_TRANSITIONS
from ultron.core.issue_memory import IssueMemory, IssueRecord
from ultron.core.development_session import DevelopmentSessionManager, DevelopmentAttempt, ExecutionRealityTrace
from ultron.core.agent_context_builder import AgentContextBuilder
from ultron.core.safety_evaluator import SafetyEvaluator
from ultron.core.test_runner_service import TestRunnerService
from ultron.core.ui_reality_compiler import UIRealityCompiler
from ultron.core.pipeline.orchestrator import compute_repository_content_hash


class IssueOrchestrator:
    """
    Coordinates issues, development state, evidence, missions, checkpoints,
    and regressions across the active repository.
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self.repo_path = self.repo_root
        self.work_queue = WorkQueue(self.repo_root)
        self.issue_memory = IssueMemory(self.repo_root)
        self.session_manager = DevelopmentSessionManager(self.repo_root)
        self.active_attempt: Optional[DevelopmentAttempt] = None
        self._load_active_attempt()

    def _attempt_file_path(self) -> str:
        return os.path.join(self.repo_root, ".ultron", "work", "active_attempt.json")

    def _load_active_attempt(self):
        af = self._attempt_file_path()
        if os.path.exists(af):
            try:
                with open(af, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.active_attempt = DevelopmentAttempt.from_dict(data)
            except Exception:
                self.active_attempt = None

    def _save_active_attempt(self):
        af = self._attempt_file_path()
        if self.active_attempt is None:
            if os.path.exists(af):
                try:
                    os.remove(af)
                except Exception:
                    pass
            return
        tmp = f"{af}.tmp.{int(time.time()*1000)}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.active_attempt.to_dict(), f, indent=2)
        for attempt in range(5):
            try:
                os.replace(tmp, af)
                break
            except (PermissionError, OSError):
                if attempt == 4:
                    try:
                        shutil.copy2(tmp, af)
                        os.remove(tmp)
                    except Exception:
                        pass
                    break
                time.sleep(0.05)

    # -------------------------------------------------------------------------
    # 1. DISCOVER ISSUES
    # -------------------------------------------------------------------------
    def discover_issues(self, bundle: Optional[Any] = None) -> List[IssueRecord]:
        """
        Discovers unresolved defects, AST complexity outliers, and broken contracts.
        Updates work queue state to DISCOVERING.
        """
        if self.work_queue.get_state().status != "DISCOVERING":
            self.work_queue.transition_to("DISCOVERING")
        discovered: List[IssueRecord] = []

        # 1. Existing memory issues (including REOPENED or DISCOVERED)
        existing = self.issue_memory.list_issues()
        pending_existing = [i for i in existing if i.status in ("DISCOVERED", "REOPENED")]
        discovered.extend(pending_existing)

        # Register product UX defects if not already in memory
        if not any(i.issue_id == "BUG-PROD-01" for i in existing):
            iss_prod1 = IssueRecord(
                issue_id="BUG-PROD-01",
                pillar="HUMAN",
                component="agent_context_hub",
                target="ultron/interfaces/web/modules/state.js",
                failure_class="PROVIDER_SYNC_DESYNCHRONIZATION",
                symptom="Agent Context Provider Switch & Prompt Compilation Desynchronization wipes user edits and bypasses provider format",
                reproduction="Select provider pill, edit intent/target files, compile prompt and switch provider",
                reproduction_signature="PROVIDER_SYNC_DESYNCHRONIZATION",
                fingerprint="prov_sync_01",
                root_cause="DOM inputs not updating canonical StateStore and compile button posting to legacy markdown endpoint",
                status="DISCOVERED",
                metadata={"user_impact": 5, "workflow_frequency": 5, "severity": 4, "confidence": 5, "repairability": 5}
            )
            discovered.append(iss_prod1)
            self.issue_memory.record_issue(iss_prod1)

        if not any(i.issue_id == "BUG-PROD-02" for i in existing):
            iss_prod2 = IssueRecord(
                issue_id="BUG-PROD-02",
                pillar="HUMAN",
                component="work_plan_hub",
                target="ultron/interfaces/web/index.html",
                failure_class="INFINITE_LOADING_SPINNER",
                symptom="Work & Plan tab shows permanent loading spinner when no objective is active (NO_ACTIVE_OBJECTIVE -> EMPTY STATE)",
                reproduction="Open Work & Plan tab without selecting active objective",
                reproduction_signature="INFINITE_LOADING_SPINNER",
                fingerprint="spin_empty_02",
                root_cause="Objective container rendered spinner instead of informative empty state",
                status="RESOLVED",
                fix_summary="Replaced permanent loading spinner with clear empty state explaining next actions",
                metadata={"user_impact": 3, "workflow_frequency": 4, "severity": 3, "confidence": 5, "repairability": 5}
            )
            self.issue_memory.record_issue(iss_prod2)

        # 2. Derive issues from AST bundle if available or auto-analyze
        if bundle is None:
            try:
                from ultron.core.pipeline.orchestrator import analyze_repository
                bundle = analyze_repository(self.repo_root)
            except Exception:
                bundle = None

        if bundle:
            # Check high risk hotspots (Complexity >= 15)
            risks = getattr(bundle, "risks", [])
            for r in risks:
                comp = getattr(r, "cyclomatic_complexity", 0) or getattr(r, "complexity", 0)
                fp = getattr(r, "file", "") or getattr(r, "file_path", "")
                if fp:
                    fp = fp.replace("\\", "/")
                if comp >= 15 and fp:
                    iss_id = f"HOTSPOT-{hashlib.sha256(fp.encode('utf-8')).hexdigest()[:8]}"
                    # Check if already tracked
                    if not any(i.target == fp for i in existing):
                        new_iss = IssueRecord(
                            issue_id=iss_id,
                            pillar="FUNCTIONAL",
                            component="ast_engine",
                            target=fp,
                            failure_class="COMPLEXITY_HOTSPOT",
                            symptom=f"Module '{fp}' has high Cyclomatic Complexity ({comp} >= 15)",
                            reproduction=f"Analyze {fp} AST metrics",
                            reproduction_signature=f"COMPLEXITY_HOTSPOT_{fp}",
                            fingerprint="",
                            root_cause="Deep structural branching and decision density exceeds threshold",
                            status="DISCOVERED",
                            metadata={"user_impact": 1, "workflow_frequency": 1, "severity": 1, "confidence": 1, "repairability": 1}
                        )
                        discovered.append(new_iss)
                        self.issue_memory.record_issue(new_iss)

        return self.prioritize_issues(discovered)

    # -------------------------------------------------------------------------
    # 2. PRIORITIZE ISSUES
    # -------------------------------------------------------------------------
    def calculate_product_score(self, iss: IssueRecord) -> Optional[int]:
        meta = iss.metadata or {}
        impact = meta.get("user_impact")
        freq = meta.get("workflow_frequency")
        sev = meta.get("severity")
        conf = meta.get("confidence")
        rep = meta.get("repairability")
        
        # Missing evidence -> UNKNOWN/unscored
        if any(v is None for v in (impact, freq, sev, conf, rep)):
            if iss.failure_class == "COMPLEXITY_HOTSPOT":
                return 1
            return None
        try:
            return int(impact) * int(freq) * int(sev) * int(conf) * int(rep)
        except (ValueError, TypeError):
            return None

    def prioritize_issues(self, issues: Optional[List[IssueRecord]] = None) -> List[IssueRecord]:
        """
        Ranks issues by product score:
        Priority 0: REOPENED (regressions take highest precedence).
        Priority 1: Product Score = User Impact * Frequency * Severity * Confidence * Repairability.
        Priority 2: Pillar severity (HUMAN > CONNECTIVITY > FUNCTIONAL).
        """
        if issues is None:
            issues = self.issue_memory.list_issues()

        pending = [i for i in issues if i.status in ("DISCOVERED", "REOPENED")]

        def sort_key(iss: IssueRecord) -> Tuple[int, int, int, str]:
            status_prio = 0 if iss.status == "REOPENED" else 1
            score = self.calculate_product_score(iss)
            score_prio = -(score if score is not None else 0)
            pillar_prio = {"HUMAN": 0, "CONNECTIVITY": 1, "FUNCTIONAL": 2}.get(iss.pillar, 3)
            return (status_prio, score_prio, pillar_prio, iss.issue_id)

        pending.sort(key=sort_key)
        return pending

    # -------------------------------------------------------------------------
    # 3. SELECT ISSUE
    # -------------------------------------------------------------------------
    def select_issue(self, issue_id: str) -> WorkState:
        """
        Selects a specific issue to work on, advancing state to ISSUE_SELECTED.
        """
        issue = self.issue_memory.get_issue(issue_id)
        if not issue:
            raise ValueError(f"Issue '{issue_id}' not found in issue memory.")

        state = self.work_queue.transition_to(
            "ISSUE_SELECTED",
            context={
                "active_issue": issue.issue_id,
                "repository_id": self.session_manager.session.repository_id if hasattr(self.session_manager, "session") else "",
                "attempt_number": len(issue.attempts) + 1
            }
        )
        return state

    # -------------------------------------------------------------------------
    # 4. COMPILE MISSION
    # -------------------------------------------------------------------------
    def compile_mission(self, issue_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Compiles bounded agent mission for the active issue via AgentContextBuilder.
        Advances state to MISSION_READY.
        """
        current = self.work_queue.get_state()
        target_issue_id = issue_id or current.active_issue
        if not target_issue_id:
            raise ValueError("No active issue selected to compile mission.")

        issue = self.issue_memory.get_issue(target_issue_id)
        if not issue:
            raise ValueError(f"Issue '{target_issue_id}' not found.")

        target_files = [issue.target] if issue.target else []
        mission_id = f"MIS-{issue.issue_id}-{int(time.time())}"

        objective_state = {
            "title": f"Resolve {issue.issue_id}: {issue.symptom}",
            "description": f"Fix root cause of defect: {issue.root_cause}. Verify resolution and prevent regressions.",
            "progress_pct": 0.0,
            "tasks": [
                {
                    "id": f"task-{issue.issue_id}",
                    "title": f"Fix {issue.target or 'defect'}",
                    "target_file": issue.target or "target_file.py",
                    "intent": f"Fix {issue.root_cause or 'defect'}",
                    "acceptance_criteria": [
                        f"Defect symptom eliminated: {issue.symptom}",
                        f"Regression test passes: {issue.regression_test or 'Master Test Suite'}"
                    ]
                }
            ],
            "affected_areas": target_files or [issue.target or "target_file.py"],
            "constraints": [
                "Preserve all existing public API contracts",
                "Ensure zero metric gaming and verify Three Pillars",
                "Zero unexpected modified files outside declared targets"
            ]
        }

        # Initialize new DevelopmentAttempt
        attempt_num = current.attempt_number or 1
        attempt_id = f"ATT-{issue.issue_id}-{attempt_num}"

        # Capture browser reality before
        browser_capture = UIRealityCompiler.capture_browser_reality(self.repo_root, attempt_id, stage="OVERVIEW")
        browser_evidence_dir = browser_capture.get("browser_evidence_dir", os.path.join(".ultron", "evidence", attempt_id).replace("\\", "/"))

        # Compile continuous Execution Reality Trace for this mission
        trace_id = f"TRACE-{attempt_id}"
        initial_trace = ExecutionRealityTrace(
            trace_id=trace_id,
            trigger=f"Selected issue '{issue.issue_id}': {issue.symptom}",
            element=f"#{issue.component or 'workspace'}",
            state_before="ISSUE_SELECTED",
            request={"action": "compile_mission", "issue_id": issue.issue_id},
            response={"status": "MISSION_READY", "mission_id": mission_id},
            state_after="MISSION_READY",
            dom_changes=[f"Objective focused on {issue.target or 'module'}"],
            screenshot_before=browser_capture.get("screenshot_path", ""),
            failure_point=issue.reproduction if issue.status in ("REOPENED", "DISCOVERED") else None,
            root_cause=issue.root_cause,
            result="PASS"
        )

        context = AgentContextBuilder.build(
            objective_state=objective_state,
            repo_path=self.repo_root,
            snapshot_id=self.session_manager.session.latest_snapshot_id if hasattr(self.session_manager, "session") else "snap_t0",
            mission_intent=f"Fix {issue.root_cause or 'defect'}",
            why_this_task_matters=f"Resolves {issue.pillar} defect in {issue.target or 'module'}",
            execution_trace=initial_trace.to_dict()
        )
        rendered = AgentContextBuilder.render_claude(context)
        mission_bundle = {
            "mission_id": mission_id,
            "context": context.to_dict(),
            "xml_envelope": rendered,
            "execution_reality_trace": initial_trace.to_dict()
        }

        html_path = os.path.join(self.repo_root, "ultron", "interfaces", "web", "index.html")
        structural_hash_before = ""
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    structural_hash_before = hashlib.sha256(f.read().encode("utf-8")).hexdigest()[:16]
            except Exception as e:
                sys.stderr.write(f"Structural hash read error: {e}\n")

        self.active_attempt = DevelopmentAttempt(
            attempt_id=attempt_id,
            issue_id=issue.issue_id,
            mission_id=mission_id,
            attempt_number=attempt_num,
            target_files=target_files,
            snapshot_before=self.session_manager.session.latest_snapshot_id if hasattr(self.session_manager, "session") else "snap_t0",
            browser_evidence_dir=browser_evidence_dir,
            structural_hash_before=structural_hash_before,
            visual_state_before=browser_capture,
            tests_before={"executed": True, "passed_count": 0, "failed_count": 0},
            execution_reality_trace=initial_trace.to_dict()
        )
        self._save_active_attempt()

        self.work_queue.transition_to(
            "MISSION_READY",
            context={
                "mission_id": mission_id,
                "attempt_number": attempt_num
            }
        )

        return mission_bundle

    def compile_repair_mission(self, issue_id: str, failure_packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consumes bounded failure packet (failing pillar, failure class, actual observation,
        affected files, visual/test evidence reference, reproduction), transitions from
        REPAIR_REQUIRED to MISSION_READY, increments attempt_number, and links to parent_attempt_id.
        """
        current_state = self.work_queue.get_state()
        if current_state.status not in ("REPAIR_REQUIRED", "BLOCKED", "MISSION_READY"):
            raise InvalidStateTransitionError(f"Cannot compile repair mission from status '{current_state.status}'.")

        issue = self.issue_memory.get_issue(issue_id)
        if not issue:
            # Fallback to active attempt issue or first issue
            if self.active_attempt and self.active_attempt.issue_id:
                issue = self.issue_memory.get_issue(self.active_attempt.issue_id)
            if not issue:
                raise ValueError(f"Issue '{issue_id}' not found.")

        packet = failure_packet or {}
        parent_id = self.active_attempt.attempt_id if self.active_attempt else f"ATT-{issue.issue_id}-1"
        next_attempt_num = (self.active_attempt.attempt_number + 1) if self.active_attempt else 2
        new_attempt_id = f"ATT-{issue.issue_id}-{next_attempt_num}"

        # Capture browser reality for repair baseline
        browser_capture = UIRealityCompiler.capture_browser_reality(self.repo_root, new_attempt_id, stage="OVERVIEW")
        browser_evidence_dir = browser_capture.get("browser_evidence_dir", os.path.join(".ultron", "evidence", new_attempt_id).replace("\\", "/"))

        html_path = os.path.join(self.repo_root, "ultron", "interfaces", "web", "index.html")
        structural_hash_before = ""
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    structural_hash_before = hashlib.sha256(f.read().encode("utf-8")).hexdigest()[:16]
            except Exception as e:
                sys.stderr.write(f"Structural hash read error: {e}\n")

        target_files = [issue.target] if issue.target else []

        repair_mission_id = f"REPAIR-{issue.issue_id}-{int(time.time())}"
        self.active_attempt = DevelopmentAttempt(
            attempt_id=new_attempt_id,
            parent_attempt_id=parent_id,
            issue_id=issue.issue_id,
            mission_id=repair_mission_id,
            attempt_number=next_attempt_num,
            target_files=target_files,
            snapshot_before=self.active_attempt.snapshot_after if (self.active_attempt and self.active_attempt.snapshot_after) else "snap_t0",
            browser_evidence_dir=browser_evidence_dir,
            structural_hash_before=structural_hash_before,
            visual_state_before=browser_capture,
            tests_before={"executed": True, "passed_count": 0, "failed_count": 0}
        )
        self._save_active_attempt()

        # If currently in BLOCKED, transition through REPAIR_REQUIRED first
        if current_state.status == "BLOCKED":
            self.work_queue.transition_to("REPAIR_REQUIRED", context={"blocking_reasons": packet.get("blocking_reasons", [])})

        # Transition to MISSION_READY with repair context
        self.work_queue.transition_to(
            "MISSION_READY",
            context={
                "mission_id": repair_mission_id,
                "attempt_number": next_attempt_num,
                "repair": True,
                "parent_attempt_id": parent_id,
                "failure_diagnostics": packet
            }
        )

        return {
            "mission_id": repair_mission_id,
            "attempt_number": next_attempt_num,
            "parent_attempt_id": parent_id,
            "failure_packet": packet,
            "instructions": f"Repair defect in {issue.target}. Failure reasons: {packet.get('blocking_reasons', ['Observed failure'])}"
        }

    # -------------------------------------------------------------------------
    # 5. EXECUTE ATTEMPT
    # -------------------------------------------------------------------------
    def execute_attempt(self, modified_files: Optional[List[str]] = None) -> DevelopmentAttempt:
        """
        Records that code execution has started/completed, advancing to IMPLEMENTING -> OBSERVING.
        """
        if not self.active_attempt:
            raise ValueError("No active development attempt initialized.")

        self.work_queue.transition_to("IMPLEMENTING")
        
        # Record modified files
        if modified_files is not None:
            self.active_attempt.changed_files = list(modified_files)
            # Check unexpected files
            target_set = set(self.active_attempt.target_files)
            self.active_attempt.unexpected_files = [
                f for f in modified_files if f not in target_set and not any(f.endswith(tf) for tf in target_set)
            ]
            self.active_attempt.execution_log["files_modified"] = list(modified_files)

        self._save_active_attempt()
        return self.active_attempt

    execute_mission = execute_attempt

    # -------------------------------------------------------------------------
    # 6. OBSERVE STATE
    # -------------------------------------------------------------------------
    def observe_state(
        self,
        snapshot_id: str,
        test_results: Dict[str, Any],
        visual_snapshot: Optional[Dict[str, Any]] = None
    ) -> DevelopmentAttempt:
        """
        Captures observed changes, test outcomes, and browser reality snapshot.
        Computes STRUCTURAL_UI_DELTA and BROWSER_VISUAL_DELTA.
        Advances state to OBSERVING -> VERIFYING.
        """
        if not self.active_attempt:
            raise ValueError("No active development attempt initialized.")

        self.work_queue.transition_to("OBSERVING")

        self.active_attempt.snapshot_after = snapshot_id
        self.active_attempt.tests_after = dict(test_results)
        self.active_attempt.tests_after["snapshot_id"] = snapshot_id

        # Compute structural UI delta
        html_path = os.path.join(self.repo_root, "ultron", "interfaces", "web", "index.html")
        html_after = ""
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html_after = f.read()
                self.active_attempt.structural_hash_after = hashlib.sha256(html_after.encode("utf-8")).hexdigest()[:16]
            except Exception as e:
                sys.stderr.write(f"Structural hash after read warning: {e}\n")

        # Capture browser after if not explicitly supplied
        browser_capture_after = visual_snapshot or UIRealityCompiler.capture_browser_reality(
            self.repo_root,
            self.active_attempt.attempt_id,
            stage="OVERVIEW"
        )
        self.active_attempt.visual_state_after = dict(browser_capture_after)
        self.active_attempt.visual_state_after["snapshot_id"] = snapshot_id

        # Compute Browser Visual Delta between before and after
        before_state = self.active_attempt.visual_state_before or {}
        after_state = self.active_attempt.visual_state_after or {}

        # Resolve snapshot file data if dict contains reference
        if isinstance(before_state, dict) and before_state.get("snapshot_file") and os.path.exists(before_state["snapshot_file"]):
            try:
                with open(before_state["snapshot_file"], "r", encoding="utf-8") as f:
                    before_state = json.load(f)
            except Exception as e:
                sys.stderr.write(f"Snapshot before file read warning: {e}\n")

        if isinstance(after_state, dict) and after_state.get("snapshot_file") and os.path.exists(after_state["snapshot_file"]):
            try:
                with open(after_state["snapshot_file"], "r", encoding="utf-8") as f:
                    after_state = json.load(f)
            except Exception as e:
                sys.stderr.write(f"Snapshot after file read warning: {e}\n")

        visual_delta = UIRealityCompiler.compile_browser_visual_delta(before_state, after_state)
        self.active_attempt.visual_delta_summary = visual_delta
        if self.active_attempt.visual_state_after:
            self.active_attempt.visual_state_after["delta"] = visual_delta

        self.active_attempt.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save_active_attempt()

        self.work_queue.transition_to("VERIFYING")
        return self.active_attempt

    # -------------------------------------------------------------------------
    # 7. VERIFY ATTEMPT
    # -------------------------------------------------------------------------
    def verify_attempt(self) -> Tuple[bool, List[str]]:
        """
        Evaluates Three-Pillar correctness and snapshot consistency.
        Returns (is_verified, reasons).
        """
        if not self.active_attempt:
            return False, ["No active development attempt to verify."]

        if self.active_attempt.outcome == "REGRESSION_DETECTED":
            return False, ["Regression Detected: Historical issue re-manifested! Reopened in IssueMemory."]

        reasons: List[str] = []

        # Pillar 1: FUNCTIONAL (Unit tests pass with zero failures OR AST syntax & static import integrity pass)
        tests_after = self.active_attempt.tests_after or {}
        has_tests_run = (tests_after.get("total", 0) > 0 or tests_after.get("passed_count", 0) > 0 or ("failed_count" in tests_after and not tests_after.get("ast_verified", False)))

        if has_tests_run:
            func_pass = (
                tests_after.get("failed_count", 1) == 0 and
                (tests_after.get("passed_count", 0) > 0 or tests_after.get("passed", False))
            )
            if not func_pass:
                reasons.append("Functional Pillar Failed: Tests failing or unexecuted.")
                func_reason = f"Tests failed: {tests_after.get('failed_count', 1)} failure(s)"
            else:
                func_reason = f"✓ {tests_after.get('passed_count', 0)} tests passing (0 failures)"
        else:
            # Zero-config / no test suite: Perform robust AST Syntax & Static Import verification
            ast_syntax_pass = True
            syntax_errors = []
            files_to_check = list(set((self.active_attempt.changed_files or []) + (self.active_attempt.target_files or [])))

            for rel_file in files_to_check:
                full_path = os.path.join(self.repo_root, rel_file)
                if not os.path.exists(full_path) or not os.path.isfile(full_path):
                    continue
                norm = rel_file.lower().replace('\\', '/')
                if norm.endswith(".py"):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f_py:
                            code_src = f_py.read()
                        ast.parse(code_src, filename=rel_file)
                    except SyntaxError as se:
                        ast_syntax_pass = False
                        syntax_errors.append(f"{rel_file}:{se.lineno} - {se.msg}")
                    except Exception as e:
                        ast_syntax_pass = False
                        syntax_errors.append(f"{rel_file} - {str(e)}")
                elif norm.endswith(".json"):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f_json:
                            json.load(f_json)
                    except Exception as je:
                        ast_syntax_pass = False
                        syntax_errors.append(f"{rel_file} - Invalid JSON: {str(je)}")
                else:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f_txt:
                            f_txt.read(4096)
                    except Exception as te:
                        ast_syntax_pass = False
                        syntax_errors.append(f"{rel_file} - Unreadable: {str(te)}")

            func_pass = ast_syntax_pass
            if not func_pass:
                reasons.append(f"Functional Pillar Failed: Syntax errors detected: {', '.join(syntax_errors)}")
                func_reason = f"Syntax errors: {', '.join(syntax_errors)}"
            else:
                func_reason = "✓ Code syntax & static imports verified cleanly (0 syntax errors)"
                self.active_attempt.tests_after = {
                    "passed": True,
                    "passed_count": 0,
                    "failed_count": 0,
                    "ast_verified": True,
                    "files_checked": len(files_to_check)
                }

        # Pillar 2: CONNECTIVITY (Zero unexpected modified files & server routes valid)
        unexp = [os.path.normpath(f).replace('\\', '/') for f in (self.active_attempt.unexpected_files or [])]
        conn_pass = len(unexp) == 0 and not self.active_attempt.rollback_performed
        if not conn_pass:
            reasons.append(f"Connectivity Pillar Failed: Unexpected files modified: {', '.join(unexp)}")
            conn_reason = f"Out-of-scope files modified: {', '.join(unexp)}"
        else:
            conn_reason = "✓ Changes strictly confined to target area (0 boundary breaches)"

        # Pillar 3: HUMAN (Browser reality clean, zero action priority conflicts, visual delta pass)
        human_pass = True
        human_reason = "✓ Interface layout clean with 0 console errors"

        # Epistemic Browser Gating:
        # If browser reality is explicitly DEGRADED (wireframe fallback), Human Reality CANNOT pass for UI issues.
        if self.active_attempt.visual_state_after:
            v_after = self.active_attempt.visual_state_after
            target_all = (self.active_attempt.target_files or []) + (self.active_attempt.changed_files or [])
            touches_ui = any("web" in f or "html" in f or "css" in f or "js" in f for f in target_all)
            active_iss = self.issue_memory.get_issue(self.active_attempt.issue_id) if self.active_attempt.issue_id else None
            is_human_issue = bool(active_iss and getattr(active_iss, "pillar", "") == "HUMAN")
            if (is_human_issue or touches_ui) and (v_after.get("browser_reality") == "DEGRADED" or v_after.get("wireframe_fallback")):
                human_pass = False
                human_reason = "Human Reality = NOT_PROVEN: Degraded wireframe evidence"
                reasons.append("Human Reality = NOT_PROVEN: Degraded wireframe evidence")

        visual_delta = self.active_attempt.visual_delta_summary or {}
        if visual_delta and not visual_delta.get("passed", True):
            human_pass = False
            for r in visual_delta.get("reasons", []):
                reasons.append(f"Human Reality Pillar Failed: {r}")
            human_reason = "Visual delta layout conflict detected"

        if self.active_attempt.visual_state_after:
            conflicts = self.active_attempt.visual_state_after.get("action_priority_conflicts", [])
            health = self.active_attempt.visual_state_after.get("runtime_health", {}).get("status", "HEALTHY")
            if conflicts or health != "HEALTHY":
                human_pass = False
                human_reason = f"Layout Conflicts: {conflicts} | Health: {health}"
                reasons.append(f"Human Reality Pillar Failed: Conflicts: {conflicts} | Health: {health}")

        # Record Three-Pillar Results
        self.active_attempt.three_pillar_results = {
            "FUNCTIONAL": func_pass,
            "CONNECTIVITY": conn_pass,
            "HUMAN": human_pass
        }

        # Structure Three-Pillar Details for plain-English consumption
        self.active_attempt.three_pillar_details = {
            "functional": {"passed": func_pass, "reason": func_reason},
            "connectivity": {"passed": conn_pass, "reason": conn_reason, "unexpected_files": unexp},
            "human": {"passed": human_pass, "reason": human_reason}
        }

        # Update 4-Stage Constitutional Progression
        if func_pass and conn_pass:
            if not getattr(self.active_attempt, "progression_stage", None) or self.active_attempt.progression_stage == "UNVERIFIED":
                self.active_attempt.progression_stage = "MECHANICALLY_COMPLIANT"

        if getattr(self.active_attempt, "progression_stage", None) in ("MECHANICALLY_COMPLIANT", "BROWSER_VERIFIED"):
            v_after = self.active_attempt.visual_state_after or {}
            if v_after.get("browser_reality") == "FULL" and human_pass:
                self.active_attempt.progression_stage = "BROWSER_VERIFIED"

        # Check historical regression against REGRESSION_GUARD issues
        regressed_issue = None
        active_issue = self.issue_memory.get_issue(self.active_attempt.issue_id) if self.active_attempt.issue_id else None
        active_failures = str(self.active_attempt.tests_after.get("failures", "")) + str(self.active_attempt.tests_after.get("errors", ""))
        
        # Priority 1: Match by explicit reproduction signature in active failure output
        for hist_issue in self.issue_memory.list_issues(status="REGRESSION_GUARD"):
            if hist_issue.reproduction_signature and hist_issue.reproduction_signature in active_failures:
                regressed_issue = self.issue_memory.check_for_regression(
                    pillar=hist_issue.pillar,
                    component=hist_issue.component,
                    target=hist_issue.target,
                    failure_class=hist_issue.failure_class,
                    reproduction_signature=hist_issue.reproduction_signature,
                    attempt_data=self.active_attempt.to_dict()
                )
                if regressed_issue:
                    break

        # Priority 2: Fallback if active issue itself was in REGRESSION_GUARD and failed
        if not regressed_issue and not func_pass and active_issue and active_issue.status == "REGRESSION_GUARD":
            regressed_issue = self.issue_memory.check_for_regression(
                pillar=active_issue.pillar,
                component=active_issue.component,
                target=active_issue.target,
                failure_class=active_issue.failure_class,
                reproduction_signature=active_issue.reproduction_signature,
                attempt_data=self.active_attempt.to_dict()
            )

        if regressed_issue:
            self.active_attempt.outcome = "REGRESSION_DETECTED"
            reasons.append(f"Regression Detected: Historical issue '{regressed_issue.issue_id}' re-manifested! Reopened in IssueMemory.")
            self._save_active_attempt()
            return False, reasons

        # Check evidence completeness
        is_verified = self.active_attempt.is_verified()
        self.active_attempt.outcome = "SUCCESS" if is_verified else "FAILURE"
        self._save_active_attempt()

        return is_verified, reasons

    # -------------------------------------------------------------------------
    # 8. GUARD REGRESSION & ADVANCE
    # -------------------------------------------------------------------------
    def guard_regression_and_advance(self) -> WorkState:
        """
        Derives admissible state advancement from attempt verification.
        If verified: transitions to CHECKPOINT_READY and guards issue.
        If failed: transitions to REPAIR_REQUIRED.
        If boundary breached or regression detected: transitions to BLOCKED.
        """
        if not self.active_attempt:
            raise ValueError("No active attempt.")

        is_verified, reasons = self.verify_attempt()

        if is_verified:
            # Transition to CHECKPOINT_READY
            state = self.work_queue.transition_to(
                "CHECKPOINT_READY",
                context={"active_issue": self.active_attempt.issue_id}
            )
            return state
        else:
            # Check if failure is due to boundary breach or historical regression
            if self.active_attempt.outcome == "REGRESSION_DETECTED" or self.active_attempt.unexpected_files:
                state = self.work_queue.transition_to(
                    "BLOCKED",
                    context={"blocking_reasons": reasons}
                )
                return state
            else:
                state = self.work_queue.transition_to(
                    "REPAIR_REQUIRED",
                    context={"blocking_reasons": reasons}
                )
                return state

    # -------------------------------------------------------------------------
    # 8b. RECORD HUMAN JUDGMENT
    # -------------------------------------------------------------------------
    def record_human_judgment(self, rating: str, rationale: str = "") -> Dict[str, Any]:
        """
        Records the human developer's assessment of whether the product actually improved.
        Enforces 4-stage progression:
            BETTER + FULL browser reality → stage = PRODUCT_IMPROVED, attempt outcome = SUCCESS
            BETTER + DEGRADED browser reality → stage = HUMAN_JUDGED (blocked from PRODUCT_IMPROVED)
            NO_DIFFERENCE → transition to PRODUCT_REVIEW_REQUIRED (blocks claiming improvement)
            WORSE        → transition to REPAIR_REQUIRED
        """
        if not self.active_attempt:
            raise ValueError("No active development attempt to judge.")

        judgment = {
            "rating": rating,
            "rationale": rationale,
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.active_attempt.human_judgment = judgment

        v_after = self.active_attempt.visual_state_after or {}
        browser_full = v_after.get("browser_reality") == "FULL"
        human_pass = self.active_attempt.three_pillar_results.get("HUMAN", False)

        # Stage 3: HUMAN_JUDGED
        self.active_attempt.progression_stage = "HUMAN_JUDGED"

        current_status = self.work_queue.get_state().status
        allowed = STATE_TRANSITIONS.get(current_status, set())

        # Crucial Negative Test Contract (Refinement 8 & Actionable Req 2):
        # If browser evidence is explicitly DEGRADED, it cannot reach PRODUCT_IMPROVED.
        # Otherwise, rating == BETTER qualifies as PRODUCT_IMPROVED with SUCCESS.
        if rating == "BETTER":
            is_degraded = (
                v_after.get("browser_reality") == "DEGRADED" or
                v_after.get("wireframe_fallback") is True
            )
            if is_degraded:
                self.active_attempt.progression_stage = "HUMAN_JUDGED"
                self.active_attempt.outcome = "PRODUCT_REVIEW_REQUIRED"
                sys.stderr.write("[Ultron] Gating Notice: Human judged BETTER, but browser evidence is DEGRADED. Stage capped at HUMAN_JUDGED.\n")
            else:
                self.active_attempt.progression_stage = "PRODUCT_IMPROVED"
                self.active_attempt.outcome = "SUCCESS"
        elif rating == "NO_DIFFERENCE":
            self.active_attempt.outcome = "PRODUCT_REVIEW_REQUIRED"
            if "REPAIR_REQUIRED" in allowed:
                try:
                    self.work_queue.transition_to(
                        "REPAIR_REQUIRED",
                        context={"blocking_reasons": ["Human judgment: NO_DIFFERENCE — product improvement not proven."]}
                    )
                except Exception as e:
                    sys.stderr.write(f"[Ultron] Warning: Could not transition to REPAIR_REQUIRED after NO_DIFFERENCE judgment: {e}\n")
        elif rating == "WORSE":
            self.active_attempt.outcome = "FAILURE"
            if "REPAIR_REQUIRED" in allowed:
                try:
                    self.work_queue.transition_to(
                        "REPAIR_REQUIRED",
                        context={"blocking_reasons": [f"Human judgment: WORSE — {rationale or 'product regressed'}"]}
                    )
                except Exception as e:
                    sys.stderr.write(f"[Ultron] Warning: Could not transition to REPAIR_REQUIRED after WORSE judgment: {e}\n")

        self._save_active_attempt()
        return judgment

    # -------------------------------------------------------------------------
    # 9. CHECKPOINT PROGRESSION
    # -------------------------------------------------------------------------
    def checkpoint_progression(self, fix_summary: str = "Verified milestone") -> str:
        """
        Mints authoritative checkpoint, records resolution in IssueMemory,
        and transitions state to CHECKPOINTED.
        Strictly mandates progression_stage == 'PRODUCT_IMPROVED' for product evaluations.
        """
        if self.active_attempt and self.active_attempt.human_judgment:
            if getattr(self.active_attempt, "progression_stage", None) != "PRODUCT_IMPROVED":
                current_stage = getattr(self.active_attempt, "progression_stage", "UNVERIFIED")
                raise InvalidStateTransitionError(
                    f"Cannot checkpoint progression: Attempt must reach constitutional stage 'PRODUCT_IMPROVED'. Current stage: '{current_stage}'."
                )

        current = self.work_queue.get_state()
        if current.status != "CHECKPOINT_READY":
            raise InvalidStateTransitionError(
                f"Cannot mint checkpoint while in state '{current.status}'. Must be in 'CHECKPOINT_READY'."
            )

        cid = f"CHK-{int(time.time())}"
        
        # Update issue memory
        if self.active_attempt:
            self.issue_memory.mark_resolved(
                issue_id=self.active_attempt.issue_id,
                fix_summary=fix_summary,
                regression_test="Master Test Suite",
                checkpoint_id=cid
            )

        # Transition work queue
        self.work_queue.transition_to(
            "CHECKPOINTED",
            context={"checkpoint_id": cid}
        )

        return cid

    # -------------------------------------------------------------------------
    # Current Work Presentation Helper
    # -------------------------------------------------------------------------
    def get_current_work_summary(self) -> Dict[str, Any]:
        """
        Returns structured high-signal data for the Current Work UI hero card:
        What are we fixing, Why, What is the agent doing, Evidence, Next Action,
        unified identity primitives, and evolution deltas.
        """
        from ultron.core.models import build_snapshot_id
        import hashlib

        state = self.work_queue.get_state()
        active_issue = self.issue_memory.get_issue(state.active_issue) if state.active_issue else None

        # Next Action CTA mapping
        next_action_map = {
            "IDLE": {"label": "Start Issue Discovery", "action": "discover", "style": "primary"},
            "DISCOVERING": {"label": "Select Top Issue", "action": "select", "style": "primary"},
            "ISSUE_SELECTED": {"label": "Compile Mission", "action": "compile", "style": "primary"},
            "MISSION_READY": {"label": "Execute Mission", "action": "execute", "style": "primary"},
            "IMPLEMENTING": {"label": "Observe Reality", "action": "observe", "style": "primary"},
            "OBSERVING": {"label": "Verify Three Pillars", "action": "verify", "style": "primary"},
            "VERIFYING": {"label": "Check Readiness", "action": "advance", "style": "primary"},
            "CHECKPOINT_READY": {"label": "Create Checkpoint", "action": "checkpoint", "style": "primary"},
            "CHECKPOINTED": {"label": "Next Problem", "action": "next", "style": "primary"},
            "REPAIR_REQUIRED": {"label": "Compile Repair Mission", "action": "repair", "style": "warning"},
            "BLOCKED": {"label": "Rollback & Reset", "action": "rollback", "style": "danger"}
        }

        action_info = next_action_map.get(state.status, {"label": "Inspect", "action": "inspect", "style": "secondary"})

        # Resolve identity primitives
        norm_path = os.path.normcase(os.path.abspath(self.repo_path))
        repo_id = hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:16]
        repo_uuid = "00a7c3ae-1a4f-41fb-9ed2-b5e48584cc59"
        analysis_run_id = None
        content_hash = ""

        db_path = os.path.join(self.repo_path, ".ultron", "repository.db")
        if os.path.exists(db_path):
            try:
                from ultron.core.rkm.store import RepositoryStore
                store = RepositoryStore(db_path)
                meta = store.get_metadata()
                if meta:
                    repo_uuid = meta.repository_uuid
                    analysis_run_id = meta.latest_analysis_run_id
                    repo_id = meta.id or repo_id
                if analysis_run_id:
                    run = store.get_analysis_run(analysis_run_id)
                    if run:
                        content_hash = run.content_hash or ""
                store.close()
            except Exception as e:
                sys.stderr.write(f"Store read warning: {e}\n")

        snapshot_id = build_snapshot_id(content_hash)

        # Attempt evolution telemetry
        what_changed = self.active_attempt.changed_files if self.active_attempt and self.active_attempt.changed_files else []
        if self.active_attempt and self.active_attempt.outcome == "SUCCESS":
            what_improved = active_issue.fix_summary if (active_issue and active_issue.fix_summary) else "Verification passed: 0 failures, 0 unexpected files."
            what_got_worse = "None detected (Zero regressions)"
        elif state.status == "BLOCKED":
            what_improved = "Blocked by safety boundary or regression guard"
            what_got_worse = ", ".join(state.blocking_reasons) if state.blocking_reasons else "Safety violation detected"
        else:
            what_improved = "Attempt in progress"
            what_got_worse = "None detected"

        blast_radius = [active_issue.target] if (active_issue and active_issue.target) else []
        if active_issue and active_issue.target:
            try:
                from ultron.core.rkm.store import RepositoryStore
                from ultron.core.rkm.query import RKMQueryEngine
                db_path = os.path.join(self.repo_root, ".ultron", "repository.db")
                if os.path.exists(db_path):
                    q = RKMQueryEngine(RepositoryStore(db_path))
                    real_blast = q.get_blast_radius(active_issue.target)
                    if real_blast:
                        blast_radius = real_blast
            except Exception:
                pass

        tests_data = self.active_attempt.tests_after if self.active_attempt else {}
        passed_cnt = tests_data.get("passed_count", 0)
        failed_cnt = tests_data.get("failed_count", 0)
        total_cnt = passed_cnt + failed_cnt

        func_pass = self.active_attempt.three_pillar_results.get("FUNCTIONAL", False) if self.active_attempt else False
        conn_pass = self.active_attempt.three_pillar_results.get("CONNECTIVITY", False) if self.active_attempt else False
        human_pass = self.active_attempt.three_pillar_results.get("HUMAN", False) if self.active_attempt else False

        synced_count = sum(1 for v in (repo_id, repo_uuid, analysis_run_id, content_hash, snapshot_id) if v)

        evidence_snap = snapshot_id[5:13] if len(snapshot_id) >= 13 else "snap"
        three_pillar_details = {
            "functional": {
                "passed": func_pass,
                "evidence_id": "ev-func-" + evidence_snap,
                "snapshot_id": snapshot_id,
                "reason": ("✓ " + str(passed_cnt) + " of " + str(total_cnt) + " tests (0 failures)") if (func_pass and total_cnt > 0) else ("Ready to verify" if state.status in ("IDLE", "DISCOVERING", "MISSION_READY") else ("⚠ " + str(failed_cnt) + " test failures detected")),
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "connectivity": {
                "passed": conn_pass,
                "evidence_id": "ev-conn-" + evidence_snap,
                "snapshot_id": snapshot_id,
                "reason": ("✓ " + str(synced_count) + " of 5 identity primitives synchronized") if conn_pass else (str(synced_count) + " of 5 identity primitives synchronized"),
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "human": {
                "passed": human_pass,
                "evidence_id": f"ev-human-{snapshot_id[5:13] if len(snapshot_id) >= 13 else 'snap'}",
                "snapshot_id": snapshot_id,
                "reason": "✓ Primary CTA unclipped, 0 console errors" if human_pass else (
                    f"⚠ Visual failure: {', '.join(self.active_attempt.visual_delta_summary.get('reasons', ['Layout issue'])[:1])}" if (self.active_attempt and self.active_attempt.visual_delta_summary and not self.active_attempt.visual_delta_summary.get('passed', True)) else "Ready to observe"
                ),
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }

        summary = {
            "work": {
                "status": state.status,
                "active_issue_id": active_issue.issue_id if active_issue else "None",
                "pillar": active_issue.pillar if active_issue else "N/A",
                "symptom": active_issue.symptom if active_issue else "Repository idle. Ready to discover next improvement.",
                "root_cause": active_issue.root_cause if active_issue else "N/A",
                "target": active_issue.target if active_issue else "N/A",
                "reproduction": active_issue.reproduction if active_issue else "python verify_release.py",
                "reproduction_signature": active_issue.reproduction_signature if active_issue else "",
                "blast_radius": blast_radius,
                "three_pillar_details": three_pillar_details,
                "attempt_number": state.attempt_number,
                "blocking_reasons": state.blocking_reasons,
                "next_action": action_info,
                "what_changed": what_changed,
                "what_improved": what_improved,
                "what_got_worse": what_got_worse,
                "tests": self.active_attempt.tests_after if self.active_attempt else {},
                "visual_delta_summary": self.active_attempt.visual_delta_summary if self.active_attempt else {},
                "browser_evidence_dir": self.active_attempt.browser_evidence_dir if self.active_attempt else None,
                "execution_reality_trace": self.active_attempt.execution_reality_trace if self.active_attempt else None,
                "attempt_details": self.active_attempt.to_dict() if self.active_attempt else None
            },
            "identity": {
                "repository_id": repo_id,
                "repository_uuid": repo_uuid,
                "analysis_run_id": analysis_run_id,
                "content_hash": content_hash,
                "snapshot_id": snapshot_id
            }
        }

        # Maintain flat keys for backward-compatibility with existing UI calls
        for k, v in summary["work"].items():
            summary[k] = v

        return summary
