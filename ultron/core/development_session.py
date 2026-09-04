"""
Ultron Core — Development Session & Evolution Diffing Engine (v2.6.3)
Manages the lifecycle of a persistent development episode:
Connects SystemGraph(t0) -> AI Change -> SystemGraph(t1) -> Structural Diff -> Safety -> Next Mission.
"""

import os
import sys
import json
import time
import hashlib
import threading
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ultron.core.system_model import SystemGraph
from ultron.core.model_diff import SystemModelDiff, ModelDiffResult
from ultron.core.safety_evaluator import SafetyEvaluator, ContinuationReadinessReport

_SESSION_LOCK = threading.RLock()
_SESSION_CACHE: Dict[str, "DevelopmentSession"] = {}


@dataclass
class EvolutionDelta:
    """Explicitly partitioned structural evolution delta between two repository snapshots."""
    starting_snapshot_id: str
    latest_snapshot_id: str
    observed: Dict[str, Any] = field(default_factory=lambda: {
        "files_added": [],
        "files_removed": [],
        "files_modified": [],
        "nodes_added_count": 0,
        "nodes_removed_count": 0,
        "edges_added_count": 0,
        "edges_removed_count": 0
    })
    derived: Dict[str, Any] = field(default_factory=lambda: {
        "complexity_delta": 0.0,
        "coupling_delta": 0.0,
        "risk_delta": 0,
        "violations_resolved": 0,
        "structural_change_index_heuristic": 0.0
    })
    impact: Dict[str, Any] = field(default_factory=lambda: {
        "blast_radius": [],
        "affected_components": [],
        "affected_tests": []
    })
    what_changed: str = "No structural changes recorded"
    what_impacted: str = "No external modules impacted"
    what_got_worse: str = "None"
    what_got_better: str = "None"
    what_remains: str = "Pending tasks"
    can_we_continue: str = "CONTINUE BUILDING"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionRealityTrace:
    """Continuous runtime evidence connecting user action to system outcome."""
    trace_id: str = "TRACE-001"
    trigger: str = ""                         # e.g., "User clicked #btn-load-repo"
    element: str = ""                         # e.g., "#btn-load-repo"
    state_before: str = ""                    # e.g., "IDLE"
    request: Optional[Dict[str, Any]] = None  # e.g., {"endpoint": "/api/v1/analyze", "body": {"repo": "."}}
    response: Optional[Dict[str, Any]] = None # e.g., {"status": 200, "success": True}
    state_after: str = ""                     # e.g., "READY"
    dom_changes: List[str] = field(default_factory=list) # e.g., ["#system-status-dot set to green"]
    console_errors: List[str] = field(default_factory=list)
    network_failures: List[str] = field(default_factory=list)
    screenshot_before: str = ""
    screenshot_after: str = ""
    failure_point: Optional[str] = None       # e.g., "None" or "API returned 500"
    root_cause: Optional[str] = None
    result: str = "PASS"                      # PASS | FAIL | DEGRADED
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevelopmentAttempt:
    """
    Encapsulates a single concrete development iteration by an agent to solve an issue.
    Binds the declared target files, actual modifications, before/after tests,
    before/after browser reality snapshots, and the continuous Execution Reality Trace.
    """
    attempt_id: str
    issue_id: str
    mission_id: str
    attempt_number: int
    target_files: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    unexpected_files: List[str] = field(default_factory=list)
    tests_before: Dict[str, Any] = field(default_factory=dict)
    tests_after: Dict[str, Any] = field(default_factory=dict)
    snapshot_before: str = ""
    snapshot_after: str = ""
    parent_attempt_id: Optional[str] = None
    browser_evidence_dir: Optional[str] = None
    structural_hash_before: str = ""
    structural_hash_after: str = ""
    visual_state_before: Optional[Dict[str, Any]] = None
    visual_state_after: Optional[Dict[str, Any]] = None
    visual_delta_summary: Dict[str, Any] = field(default_factory=dict)
    three_pillar_results: Dict[str, bool] = field(default_factory=lambda: {
        "FUNCTIONAL": False,
        "CONNECTIVITY": False,
        "HUMAN": False
    })
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    completed_at: str = ""
    duration_ms: float = 0.0
    rollback_performed: bool = False
    error_details: Optional[str] = None
    execution_log: Dict[str, List[str]] = field(default_factory=lambda: {
        "files_read": [],
        "files_modified": [],
        "commands_run": [],
        "tests_run": [],
        "verification_commands": [],
        "errors": []
    })
    outcome: str = "PENDING"  # SUCCESS, FAILURE, REGRESSION_DETECTED, BOUNDARY_VIOLATED
    human_judgment: Optional[Dict[str, Any]] = None  # {"rating": "BETTER"|"NO_DIFFERENCE"|"WORSE", "rationale": str, "evaluated_at": str}
    progression_stage: str = "MECHANICALLY_COMPLIANT"  # MECHANICALLY_COMPLIANT, BROWSER_VERIFIED, HUMAN_JUDGED, PRODUCT_IMPROVED
    execution_reality_trace: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevelopmentAttempt":
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def is_verified(self) -> bool:
        """
        Zero Metric Gaming Invariant:
        An attempt is verified ONLY if all three pillars evaluate to True AND
        the evidence package is complete and consistent with snapshot identity.
        """
        # 1. Three pillars must all evaluate to True
        if not all(self.three_pillar_results.get(p, False) for p in ("FUNCTIONAL", "CONNECTIVITY", "HUMAN")):
            return False

        # 2. snapshot_after must exist
        if not self.snapshot_after:
            return False

        # 3. Snapshot consistency: tests and visual state must be snapshot-bound
        t_snap = str(self.tests_after.get("snapshot_id", ""))
        if t_snap and t_snap != self.snapshot_after:
            return False

        v_snap = str((self.visual_state_after or {}).get("snapshot_id", ""))
        if v_snap and v_snap != self.snapshot_after:
            return False

        # 4. Target scope respected (no unexpected files)
        if self.unexpected_files:
            return False

        # 5. Tests executed and passed OR AST syntax verified
        if self.tests_after.get("failed_count", 0) > 0:
            return False
        if self.tests_after.get("passed_count", 0) == 0 and not self.tests_after.get("passed", False) and not self.tests_after.get("ast_verified", False):
            return False

        # 6. No rollback or unhandled failure
        if self.rollback_performed or self.error_details:
            return False

        # 7. Visual delta must pass if present
        if self.visual_delta_summary and not self.visual_delta_summary.get("passed", True):
            return False

        # 8. Human judgment enforcement: WORSE blocks verification
        if self.human_judgment and self.human_judgment.get("rating") == "WORSE":
            return False

        return True


@dataclass
class DevelopmentSession:
    """Canonical development session tracking active progression episode."""
    session_id: str
    repository_root: str
    repository_id: str
    created_at: str
    updated_at: str
    active_objective_id: str = "default_objective"
    current_task_id: str = ""
    current_task_title: str = ""
    starting_snapshot_id: str = "snap_initial"
    latest_snapshot_id: str = "snap_initial"
    status: str = "active"  # active, paused, completed
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    evolution_delta: Dict[str, Any] = field(default_factory=lambda: EvolutionDelta("snap_initial", "snap_initial").to_dict())
    safety_assessment: Dict[str, Any] = field(default_factory=lambda: {
        "safe_to_continue": True,
        "decision": "CONTINUE BUILDING",
        "reason_codes": [],
        "blocking_conditions": [],
        "snapshot_id": "snap_initial"
    })
    next_safe_action: str = "Implement active milestone and verify"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DevelopmentSessionManager:
    """
    Coordinates active development sessions and calculates repository evolution diffs.
    Persists session state atomically to .ultron/session.json.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.normcase(os.path.abspath(repo_path))
        self.repo_id = hashlib.sha256(self.repo_path.encode("utf-8")).hexdigest()[:16]
        self.ultron_dir = os.path.join(self.repo_path, ".ultron")
        self.session_file = os.path.join(self.ultron_dir, "session.json")
        self._session = self._load_or_create()

    def _load_or_create(self) -> DevelopmentSession:
        """Loads existing session from disk or initializes a fresh session."""
        with _SESSION_LOCK:
            if self.repo_path in _SESSION_CACHE:
                return _SESSION_CACHE[self.repo_path]
            os.makedirs(self.ultron_dir, exist_ok=True)
            if os.path.exists(self.session_file):
                try:
                    with open(self.session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("repository_id") == self.repo_id:
                        sess = DevelopmentSession(
                            session_id=data.get("session_id", f"sess_{self.repo_id[:8]}"),
                            repository_root=self.repo_path,
                            repository_id=self.repo_id,
                            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            active_objective_id=data.get("active_objective_id", "default_objective"),
                            current_task_id=data.get("current_task_id", ""),
                            current_task_title=data.get("current_task_title", ""),
                            starting_snapshot_id=data.get("starting_snapshot_id", "snap_initial"),
                            latest_snapshot_id=data.get("latest_snapshot_id", "snap_initial"),
                            status=data.get("status", "active"),
                            timeline=data.get("timeline", []),
                            evolution_delta=data.get("evolution_delta", EvolutionDelta("snap_initial", "snap_initial").to_dict()),
                            safety_assessment=data.get("safety_assessment", {
                                "safe_to_continue": True,
                                "decision": "CONTINUE BUILDING",
                                "reason_codes": [],
                                "blocking_conditions": [],
                                "snapshot_id": "snap_initial"
                            }),
                            next_safe_action=data.get("next_safe_action", "Implement active milestone and verify")
                        )
                        _SESSION_CACHE[self.repo_path] = sess
                        return sess
                except Exception:
                    # Corrupted session recovery -> reinitialize cleanly
                    pass

            now_iso = datetime.now(timezone.utc).isoformat()
            session_id = f"sess_{self.repo_id[:8]}_{int(time.time())}"
            initial_timeline = [
                {
                    "timestamp": now_iso,
                    "event_type": "SESSION_STARTED",
                    "title": "Development session initialized",
                    "metadata": {"repo_id": self.repo_id}
                }
            ]
            session = DevelopmentSession(
                session_id=session_id,
                repository_root=self.repo_path,
                repository_id=self.repo_id,
                created_at=now_iso,
                updated_at=now_iso,
                timeline=initial_timeline
            )
            _SESSION_CACHE[self.repo_path] = session
            self._persist(session)
            return session

    def record_event(self, event_type: str, title: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Records a semantic timeline milestone event into the active development session."""
        with _SESSION_LOCK:
            if self._session is None or self.repo_path in _SESSION_CACHE:
                self._session = _SESSION_CACHE.get(self.repo_path, self._session or self._load_or_create())
            now_iso = datetime.now(timezone.utc).isoformat()
            event_entry = {
                "timestamp": now_iso,
                "event_type": str(event_type).upper(),
                "title": str(title).strip(),
                "metadata": metadata or {}
            }
            # Keep timeline bounded to recent 100 entries
            self._session.timeline.append(event_entry)
            if len(self._session.timeline) > 100:
                self._session.timeline = self._session.timeline[-100:]
            self._session.updated_at = now_iso
            self._persist(self._session)
            return event_entry

    def _persist(self, session: DevelopmentSession) -> None:
        """Atomic write to .ultron/session.json via temporary file and replace."""
        with _SESSION_LOCK:
            _SESSION_CACHE[self.repo_path] = session
            os.makedirs(self.ultron_dir, exist_ok=True)
            tmp_file = os.path.join(self.ultron_dir, f"session.json.{os.getpid()}.{threading.get_ident()}.tmp")
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(session), f, indent=2)
                if os.path.exists(self.session_file):
                    try:
                        os.replace(tmp_file, self.session_file)
                    except OSError:
                        os.remove(self.session_file)
                        os.replace(tmp_file, self.session_file)
                else:
                    os.replace(tmp_file, self.session_file)
            except Exception as e:
                sys.stderr.write(f"[Ultron Session Warning] Atomic persistence failed: {e}\n")
                try:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                except Exception:
                    pass


    def get_session(self) -> Dict[str, Any]:
        """Returns the active development session as a dictionary."""
        with _SESSION_LOCK:
            if self._session is None:
                self._session = self._load_or_create()
            return self._session.to_dict()

    def sync_objective(self, objective_state: Dict[str, Any], snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """Synchronizes active objective & active task state into the development session."""
        with _SESSION_LOCK:
            if self._session is None:
                self._session = self._load_or_create()
            tasks = objective_state.get("tasks", [])
            active_task = None
            for t in tasks:
                if t.get("status") == "in_progress":
                    active_task = t
                    break
            if not active_task:
                for t in tasks:
                    if t.get("status") == "pending":
                        active_task = t
                        break

            prev_task_id = self._session.current_task_id
            self._session.active_objective_id = objective_state.get("title", "Active Development Objective")
            self._session.current_task_id = active_task.get("id", "") if active_task else ""
            self._session.current_task_title = active_task.get("title", "Objective Complete") if active_task else "Objective Complete"
            
            now_iso = datetime.now(timezone.utc).isoformat()
            if active_task and active_task.get("id") != prev_task_id and prev_task_id != "":
                event_entry = {
                    "timestamp": now_iso,
                    "event_type": "TASK_PROMOTED",
                    "title": f"Active task advanced to '{self._session.current_task_title}'",
                    "metadata": {"task_id": self._session.current_task_id, "snapshot_id": snapshot_id or self._session.latest_snapshot_id}
                }
                self._session.timeline.append(event_entry)
                if len(self._session.timeline) > 100:
                    self._session.timeline = self._session.timeline[-100:]

            if snapshot_id:
                self._session.latest_snapshot_id = snapshot_id
                if self._session.starting_snapshot_id == "snap_initial":
                    self._session.starting_snapshot_id = snapshot_id
            self._session.updated_at = now_iso
            self._persist(self._session)
            return self._session.to_dict()

    @staticmethod
    def _synthesize_structural_diff(graph_before: SystemGraph, graph_after: SystemGraph):
        """Computes AST structural diff and categorizes added, removed, and modified files."""
        diff_res: ModelDiffResult = SystemModelDiff.diff(graph_before, graph_after)

        files_added_set = set()
        for n in diff_res.added_nodes:
            if n.startswith("module:"):
                files_added_set.add(n.replace("module:", "").replace("\\", "/"))
            elif n in graph_after.nodes:
                fp = graph_after.nodes[n].file_path
                if fp:
                    files_added_set.add(fp.replace("\\", "/"))
        files_added = sorted(list(files_added_set))

        files_removed_set = set()
        for n in diff_res.removed_nodes:
            if n.startswith("module:"):
                files_removed_set.add(n.replace("module:", "").replace("\\", "/"))
            elif n in graph_before.nodes:
                fp = graph_before.nodes[n].file_path
                if fp:
                    files_removed_set.add(fp.replace("\\", "/"))
        files_removed = sorted(list(files_removed_set))

        files_modified = []
        modified_seen = set()
        for m in diff_res.modified_nodes:
            nid = m.get("id") or m.get("node_id", "")
            fp = str(m.get("file_path") or (graph_after.nodes[nid].file_path if nid in graph_after.nodes else "")).replace("\\", "/")
            if fp and fp not in modified_seen:
                modified_seen.add(fp)
                loc_delta = m.get("loc_delta", 0)
                files_modified.append({"file": fp, "loc_delta": loc_delta})

        all_touched = set(files_added) | set(files_removed) | {f["file"] for f in files_modified}
        impacted_nodes = []
        for edge in graph_after.edges:
            src = graph_after.nodes.get(edge.source_id)
            tgt = graph_after.nodes.get(edge.target_id)
            if src and tgt:
                src_fp = src.file_path.replace("\\", "/")
                tgt_fp = tgt.file_path.replace("\\", "/")
                if src_fp in all_touched and tgt_fp not in all_touched:
                    impacted_nodes.append(tgt_fp)

        return diff_res, files_added, files_removed, files_modified, all_touched, impacted_nodes

    @staticmethod
    def _synthesize_metrics_delta(
        risks_before: Optional[List[Dict[str, Any]]] = None,
        risks_after: Optional[List[Dict[str, Any]]] = None
    ):
        """Calculates cyclomatic complexity, coupling, and high-risk count deltas."""
        comp_before = sum(float(r.get("complexity", 1.0)) for r in (risks_before or []))
        comp_after = sum(float(r.get("complexity", 1.0)) for r in (risks_after or []))
        comp_delta = round(comp_after - comp_before, 2)

        coup_before = sum(float(r.get("coupling_score", 0.0)) for r in (risks_before or []))
        coup_after = sum(float(r.get("coupling_score", 0.0)) for r in (risks_after or []))
        coup_delta = round(coup_after - coup_before, 2)

        high_before = sum(1 for r in (risks_before or []) if r.get("level") == "HIGH")
        high_after = sum(1 for r in (risks_after or []) if r.get("level") == "HIGH")
        risk_delta = high_after - high_before

        return comp_delta, coup_delta, risk_delta

    @staticmethod
    def _synthesize_evolution_answers(
        files_added: List[str],
        files_removed: List[str],
        files_modified: List[Dict[str, Any]],
        diff_res: ModelDiffResult,
        impacted_nodes: List[str],
        comp_delta: float,
        risk_delta: int,
        current_task_title: str
    ):
        """Synthesizes human-readable answers for the 6 core evolution questions."""
        change_parts = []
        if files_added:
            change_parts.append(f"+{len(files_added)} file(s) added")
        if files_removed:
            change_parts.append(f"-{len(files_removed)} file(s) removed")
        if files_modified:
            change_parts.append(f"~{len(files_modified)} file(s) modified")
        if diff_res.added_edges:
            change_parts.append(f"+{len(diff_res.added_edges)} dependency edge(s)")
        what_changed = ", ".join(change_parts) if change_parts else "No structural files modified"

        what_impacted = f"{len(impacted_nodes)} downstream component(s) impacted ({', '.join(impacted_nodes[:3])})" if impacted_nodes else "Localized changes — no downstream blast radius"
        what_got_worse = f"Complexity +{comp_delta}, High-risk files +{risk_delta}" if comp_delta > 0 or risk_delta > 0 else "None — no structural degradation detected"
        what_got_better = f"Resolved {max(0, -risk_delta)} high-risk hotspot(s)" if risk_delta < 0 else "Baseline maintained without architectural regression"
        what_remains = f"Active task: '{current_task_title}'"

        return what_changed, what_impacted, what_got_worse, what_got_better, what_remains

    def compute_and_record_evolution_step(
        self,
        graph_before: SystemGraph,
        graph_after: SystemGraph,
        snapshot_id_before: str,
        snapshot_id_after: str,
        risks_before: Optional[List[Dict[str, Any]]] = None,
        risks_after: Optional[List[Dict[str, Any]]] = None,
        test_failures_count: int = 0,
        forbidden_modifications: Optional[List[str]] = None,
        boundary_constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Computes the structural evolution delta between t0 and t1, runs safety evaluation,
        and updates the active development session.
        """
        diff_res, files_added, files_removed, files_modified, all_touched, impacted_nodes = self._synthesize_structural_diff(
            graph_before, graph_after
        )
        comp_delta, coup_delta, risk_delta = self._synthesize_metrics_delta(
            risks_before, risks_after
        )
        what_changed, what_impacted, what_got_worse, what_got_better, what_remains = self._synthesize_evolution_answers(
            files_added, files_removed, files_modified, diff_res, impacted_nodes, comp_delta, risk_delta, self._session.current_task_title
        )

        # 5. Evaluate Safety & Continuation Readiness
        forbidden = list(forbidden_modifications or [])
        safety_report: ContinuationReadinessReport = SafetyEvaluator.evaluate(
            test_failures_count=test_failures_count,
            forbidden_files_modified=forbidden,
            cycle_count_delta=0,
            complexity_spike_delta=max(0.0, comp_delta),
            snapshot_id=snapshot_id_after,
            model_hash=graph_after.metadata.get("model_hash", "")
        )

        can_we_continue = safety_report.decision

        evolution_delta = EvolutionDelta(
            starting_snapshot_id=snapshot_id_before,
            latest_snapshot_id=snapshot_id_after,
            observed={
                "files_added": files_added,
                "files_removed": files_removed,
                "files_modified": files_modified,
                "nodes_added_count": len(diff_res.added_nodes),
                "nodes_removed_count": len(diff_res.removed_nodes),
                "edges_added_count": len(diff_res.added_edges),
                "edges_removed_count": len(diff_res.removed_edges)
            },
            derived={
                "complexity_delta": comp_delta,
                "coupling_delta": coup_delta,
                "risk_delta": risk_delta,
                "violations_resolved": max(0, -risk_delta),
                "structural_change_index_heuristic": diff_res.structural_change_score
            },
            impact={
                "blast_radius": impacted_nodes,
                "affected_components": list(all_touched),
                "affected_tests": [f for f in all_touched if "test" in f.lower()]
            },
            what_changed=what_changed,
            what_impacted=what_impacted,
            what_got_worse=what_got_worse,
            what_got_better=what_got_better,
            what_remains=what_remains,
            can_we_continue=can_we_continue
        )

        safety_dict = safety_report.to_dict()
        safety_dict["snapshot_id"] = snapshot_id_after
        safety_dict["content_hash"] = self.compute_current_filesystem_hash()
        safety_dict["model_hash"] = graph_after.metadata.get("model_hash", "")

        self._session.latest_snapshot_id = snapshot_id_after
        self._session.evolution_delta = evolution_delta.to_dict()
        self._session.safety_assessment = safety_dict
        self._session.status = "active" if safety_report.safe_to_continue else "paused"
        self._session.next_safe_action = "Advance to next milestone" if safety_report.safe_to_continue else "Resolve blocking conditions before continuing"
        self._session.updated_at = datetime.now(timezone.utc).isoformat()

        # Record semantic development timeline events
        if files_added or files_removed or files_modified:
            self.record_event(
                event_type="CODE_CHANGED",
                title=what_changed,
                metadata={"snapshot_id": snapshot_id_after, "files_count": len(all_touched)}
            )

        self.record_event(
            event_type="READINESS_CHECKED",
            title=f"Continuation Readiness: {can_we_continue}",
            metadata={
                "decision": can_we_continue,
                "safe": safety_report.safe_to_continue,
                "snapshot_id": snapshot_id_after,
                "reason_codes": safety_report.reason_codes
            }
        )

        # Machine-Readable Telemetry Observation Substrate (Phase 1.0 -> Phase 1.1)
        observation_telemetry = {
            "input_class": "system_evolution",
            "parameters": {
                "nodes_count": len(graph_after.nodes),
                "edges_count": len(graph_after.edges),
                "files_modified_count": len(files_modified),
                "files_added_count": len(files_added),
                "files_removed_count": len(files_removed),
                "blast_radius_count": len(impacted_nodes)
            },
            "execution": {
                "complexity_delta": comp_delta,
                "coupling_delta": coup_delta,
                "risk_delta": risk_delta,
                "safe_to_continue": safety_report.safe_to_continue
            },
            "result": {
                "status": "PASS" if safety_report.safe_to_continue else "PAUSED",
                "decision": can_we_continue,
                "reason_codes": safety_report.reason_codes
            },
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "os": sys.platform,
                "repository_snapshot": snapshot_id_after,
                "model_hash": graph_after.metadata.get("model_hash", "")
            }
        }
        self.record_event(
            event_type="ANALYSIS_OBSERVATION",
            title=f"Telemetry Observation: {snapshot_id_after}",
            metadata=observation_telemetry
        )

        self._persist(self._session)
        return self._session.to_dict()

    def evolve_session(
        self,
        snapshot_id_before: str,
        snapshot_id_after: str,
        graph_before: SystemGraph,
        graph_after: SystemGraph,
        risks_before: Optional[List[Dict[str, Any]]] = None,
        risks_after: Optional[List[Dict[str, Any]]] = None,
        test_failures_count: int = 0,
        forbidden_modifications: Optional[List[str]] = None,
        boundary_constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convenience alias for compute_and_record_evolution_step."""
        return self.compute_and_record_evolution_step(
            graph_before=graph_before,
            graph_after=graph_after,
            snapshot_id_before=snapshot_id_before,
            snapshot_id_after=snapshot_id_after,
            risks_before=risks_before,
            risks_after=risks_after,
            test_failures_count=test_failures_count,
            forbidden_modifications=forbidden_modifications,
            boundary_constraints=boundary_constraints
        )

    def compute_current_filesystem_hash(self) -> str:
        """Computes a live content hash across all tracked repository source files."""
        try:
            from ultron.core.pipeline.orchestrator import compute_repository_content_hash
            files = []
            for root, dirs, filenames in os.walk(self.repo_path):
                # Ignore metadata and virtual environment folders
                dirs[:] = [d for d in dirs if d not in {".git", ".ultron", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vscode"}]
                for f in filenames:
                    if f.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json")):
                        rel_path = os.path.relpath(os.path.join(root, f), self.repo_path).replace("\\", "/")
                        files.append(rel_path)
            return compute_repository_content_hash(self.repo_path, files)
        except Exception:
            return ""

    def create_checkpoint(
        self,
        checkpoint_id: Optional[str] = None,
        description: str = "Verified milestone checkpoint",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Authoritative server-side gate for checkpoint creation.
        Enforces continuation readiness and state freshness:
          1. safe_to_continue == True
          2. decision == 'CONTINUE BUILDING'
          3. No blocking conditions
          4. safety.snapshot_id == latest_snapshot_id (Snapshot Freshness)
          5. safety.content_hash == current_filesystem_hash (Filesystem Reality Freshness)
        """
        with _SESSION_LOCK:
            if self._session is None:
                self._session = self._load_or_create()
            safety = self._session.safety_assessment or {}
            safe_to_continue = bool(safety.get("safe_to_continue", False))
            decision = safety.get("decision", "PAUSE & REVIEW")
            blocking = safety.get("blocking_conditions", [])

            # 1. State Staleness Check (Snapshot ID Divergence)
            safety_snap = safety.get("snapshot_id")
            latest_snap = self._session.latest_snapshot_id
            if not force and safety_snap and latest_snap and safety_snap != latest_snap:
                return {
                    "success": False,
                    "error": f"Cannot create checkpoint: Continuation Readiness is stale (evaluated on snapshot '{safety_snap}', but current session snapshot is '{latest_snap}'). Re-run verification.",
                    "error_code": "STALE_READINESS",
                    "decision": "PAUSE & REVIEW",
                    "blocking_conditions": ["Stale readiness assessment: snapshot divergence"]
                }

            current_fs_hash = self.compute_current_filesystem_hash()
            # 2. Filesystem Reality Staleness Check (Unanalyzed Local Edits)
            safety_content_hash = safety.get("content_hash")
            if not force and safety_content_hash:
                if current_fs_hash and safety_content_hash != current_fs_hash:
                    return {
                        "success": False,
                        "error": "Cannot create checkpoint: Repository source files were modified on disk after Continuation Readiness was evaluated. Re-run verification.",
                        "error_code": "STALE_READINESS",
                        "decision": "PAUSE & REVIEW",
                        "blocking_conditions": ["Stale readiness assessment: filesystem modified on disk"]
                    }

            # 3. Continuation Readiness Invariant Gates
            if not force and (not safe_to_continue or decision != "CONTINUE BUILDING" or blocking):
                return {
                    "success": False,
                    "error": f"Cannot create checkpoint: Continuation Readiness is blocked ({decision})",
                    "error_code": "READINESS_BLOCKED",
                    "decision": decision,
                    "blocking_conditions": blocking,
                    "reason_codes": safety.get("reason_codes", [])
                }

            import uuid
            cid = checkpoint_id or f"chk_{str(self._session.latest_snapshot_id)[:8]}_{int(time.time()*1000)}_{uuid.uuid4().hex[:4]}"
            checkpoint_record = {
                "checkpoint_id": cid,
                "session_id": self._session.session_id,
                "repository_id": self._session.repository_id,
                "snapshot_id": self._session.latest_snapshot_id,
                "task_id": self._session.current_task_id,
                "task_title": self._session.current_task_title,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "description": description,
                "validated_content_hash": safety_content_hash or current_fs_hash,
                "checkpoint_content_hash": current_fs_hash,
                "is_content_immutable": bool(safety_content_hash == current_fs_hash) if safety_content_hash else True,
                "safety_assessment": safety,
                "evolution_delta": self._session.evolution_delta
            }

            self.record_event(
                event_type="CHECKPOINT_CREATED",
                title=f"Verified Checkpoint: {cid}",
                metadata=checkpoint_record
            )
            self._persist(self._session)
            return {
                "success": True,
                "checkpoint_id": cid,
                "checkpoint": checkpoint_record
            }

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Returns all verified checkpoints from the session timeline."""
        with _SESSION_LOCK:
            if self._session is None or self.repo_path in _SESSION_CACHE:
                self._session = _SESSION_CACHE.get(self.repo_path, self._session or self._load_or_create())
            return [
                evt.get("metadata", {}) for evt in self._session.timeline
                if evt.get("event_type") == "CHECKPOINT_CREATED" and evt.get("metadata")
            ]

    def execute_mission_atomic(
        self,
        task_id: str,
        mission_fn: Callable[[], Any],
        target_files: Optional[List[str]] = None,
        forbidden_files: Optional[List[str]] = None,
        auto_rollback: bool = True
    ) -> Dict[str, Any]:
        """
        Executes an agent task inside an atomic sandbox with automated rollback on safety gate failure.
        Eliminates the 'Dirty Workspace Abandonment Trap'.
        """
        with atomic_mission_sandbox(
            repo_path=self.repo_path,
            task_id=task_id,
            target_files=target_files,
            forbidden_files=forbidden_files,
            auto_rollback=auto_rollback
        ) as sandbox:
            return mission_fn()


class MissionExecutionError(Exception):
    """Raised when an agent task fails safety verification, containing structured differential diagnostics."""
    def __init__(self, message: str, diagnostic: Dict[str, Any]):
        super().__init__(message)
        self.diagnostic = diagnostic


@contextmanager
def atomic_mission_sandbox(
    repo_path: str,
    task_id: str,
    target_files: Optional[List[str]] = None,
    forbidden_files: Optional[List[str]] = None,
    auto_rollback: bool = True
):
    """
    Transactional execution sandbox preventing the Dirty Workspace Abandonment Trap.

    1. Pre-execution: Snapshots target & forbidden files and computes pre-execution state.
    2. Execution: Yields execution context to caller.
    3. Post-execution: Evaluates safety boundaries and file modifications.
    4. Auto-Rollback on Breach: If forbidden files were modified or an unhandled failure occurred,
       automatically restores original file contents, leaving the workspace clean, and raises
       MissionExecutionError with differential diagnostics.
    """
    norm_repo = os.path.abspath(repo_path)
    target_set = {os.path.normpath(os.path.join(norm_repo, f)) for f in (target_files or [])}
    forbidden_set = {os.path.normpath(os.path.join(norm_repo, f)) for f in (forbidden_files or [])}

    # Backup tracked/target/forbidden files into temporary directory
    backup_dir = tempfile.mkdtemp(prefix=f"ultron_sandbox_{task_id}_")
    backed_up_files: Dict[str, str] = {}  # orig_abs_path -> backup_abs_path

    # Candidate files to back up: target files, forbidden files, and existing source files
    files_to_snapshot = set(target_set | forbidden_set)
    for root, dirs, files in os.walk(norm_repo):
        # Exclude hidden or build directories
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "node_modules", ".ultron", "__pycache__"}]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".json")):
                files_to_snapshot.add(os.path.normpath(os.path.join(root, f)))

    # Compute pre-execution hashes and back up existing files
    pre_hashes: Dict[str, str] = {}
    for fpath in files_to_snapshot:
        if os.path.isfile(fpath):
            try:
                with open(fpath, "rb") as f:
                    content = f.read()
                pre_hashes[fpath] = hashlib.sha256(content).hexdigest()
                rel_path = os.path.relpath(fpath, norm_repo)
                dest_path = os.path.join(backup_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(fpath, dest_path)
                backed_up_files[fpath] = dest_path
            except (OSError, IOError):
                pass

    sandbox_context = {
        "task_id": task_id,
        "backup_dir": backup_dir,
        "pre_hashes": pre_hashes
    }

    try:
        yield sandbox_context

        # Post-execution verification
        violations = []
        modified_files = []
        newly_created_files = []

        # Check all candidate files for modifications or additions
        for fpath in files_to_snapshot:
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "rb") as f:
                        cur_hash = hashlib.sha256(f.read()).hexdigest()
                    if fpath not in pre_hashes:
                        newly_created_files.append(fpath)
                        if fpath in forbidden_set:
                            violations.append(f"Forbidden file was newly created: {os.path.relpath(fpath, norm_repo)}")
                    elif cur_hash != pre_hashes[fpath]:
                        modified_files.append(fpath)
                        if fpath in forbidden_set:
                            violations.append(f"Forbidden file was modified: {os.path.relpath(fpath, norm_repo)}")
                except (OSError, IOError):
                    pass

        if violations:
            if auto_rollback:
                # Restore modified files
                for fpath, bpath in backed_up_files.items():
                    if os.path.isfile(bpath):
                        os.makedirs(os.path.dirname(fpath), exist_ok=True)
                        shutil.copy2(bpath, fpath)
                # Remove newly created forbidden files
                for fpath in newly_created_files:
                    if fpath in forbidden_set and os.path.isfile(fpath):
                        try:
                            os.remove(fpath)
                        except OSError:
                            pass

            diag = {
                "status": "ROLLED_BACK" if auto_rollback else "FAILED_DIRTY",
                "task_id": task_id,
                "violations": violations,
                "modified_files": [os.path.relpath(f, norm_repo) for f in modified_files],
                "restored": auto_rollback,
                "guidance": "Restored workspace to clean pre-execution state. Constraints must be respected."
            }
            raise MissionExecutionError(
                f"Mission failed safety boundary constraints: {'; '.join(violations)}",
                diagnostic=diag
            )

    except Exception as exc:
        if auto_rollback and not isinstance(exc, MissionExecutionError):
            # Unexpected exception occurred during agent execution: rollback to clean state
            for fpath, bpath in backed_up_files.items():
                if os.path.isfile(bpath):
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)
                    shutil.copy2(bpath, fpath)
            diag = {
                "status": "ROLLED_BACK",
                "task_id": task_id,
                "error": str(exc),
                "restored": True,
                "guidance": "Runtime exception caught during agent execution; workspace restored to clean pre-state."
            }
            raise MissionExecutionError(f"Agent execution crashed: {str(exc)}", diagnostic=diag) from exc
        raise

    finally:
        # Cleanup backup directory
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)
