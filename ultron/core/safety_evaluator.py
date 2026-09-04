"""
Ultron Core — Safety Evaluator / Continuation Readiness Engine (v2.6.1)
Determines repository readiness and answers: "Is it safe to continue building?"
Evaluates test suite outcomes, boundary constraint violations, circular dependency drift,
and high-complexity hotspot spikes against explicit configured checks.
Semantically bounded to Continuation Readiness (evaluating absence of blocking conditions)
rather than claiming universal bug-free safety.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SafetyCheckItem:
    name: str
    passed: bool
    detail: str
    severity: str = "INFO"  # INFO, WARNING, BLOCKING
    reason_code: Optional[str] = None


@dataclass
class ContinuationReadinessReport:
    safe_to_continue: bool
    badge: str  # "CONTINUE BUILDING" | "PAUSE & REVIEW"
    summary: str
    decision_type: str = "CONTINUATION_READINESS"
    reason_codes: List[str] = field(default_factory=list)
    blocking_conditions: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    snapshot_id: str = "unknown"
    model_hash: str = ""
    checked_at: str = ""
    decision: str = ""

    def __post_init__(self):
        if not self.decision:
            self.decision = self.badge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "safe_to_continue": self.safe_to_continue,
            "badge": self.badge,
            "decision": self.decision,
            "summary": self.summary,
            "decision_type": self.decision_type,
            "reason_codes": self.reason_codes,
            "blocking_conditions": self.blocking_conditions,
            "checks": self.checks,
            "recommendations": self.recommendations,
            "snapshot_id": self.snapshot_id,
            "model_hash": self.model_hash,
            "checked_at": self.checked_at
        }


# Backwards compatibility alias
SafetyReport = ContinuationReadinessReport


class SafetyEvaluator:
    """
    Evaluates multi-dimensional safety signals to grant or pause AI coding agent progression.
    """

    @classmethod
    def evaluate(
        cls,
        test_results: Optional[Dict[str, Any]] = None,
        modified_files: Optional[List[str]] = None,
        boundary_constraints: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        cycle_count: int = 0,
        risks: Optional[List[Dict[str, Any]]] = None,
        snapshot_id: Optional[str] = None,
        # Additional optional parameters for evolution & direct engine invocation
        test_failures_count: Optional[int] = None,
        forbidden_files_modified: Optional[List[str]] = None,
        cycle_count_delta: int = 0,
        complexity_spike_delta: float = 0.0,
        model_hash: Optional[str] = None,
        repo_root: Optional[str] = None
    ) -> ContinuationReadinessReport:
        checks: List[SafetyCheckItem] = []
        recommendations: List[str] = []
        reason_codes: List[str] = []
        blocking_conditions: List[str] = []
        is_safe = True

        # 1. Test Suite Evaluation (supports either test_results dict or direct test_failures_count)
        if test_failures_count is not None:
            if test_failures_count > 0:
                is_safe = False
                reason_codes.append("TESTS_FAILING")
                blocking_msg = f"{test_failures_count} test(s) failing in test suite."
                blocking_conditions.append(blocking_msg)
                checks.append(SafetyCheckItem(
                    name="Test Suite Execution",
                    passed=False,
                    detail=blocking_msg,
                    severity="BLOCKING",
                    reason_code="TESTS_FAILING"
                ))
                recommendations.append("Fix failing test assertions before proceeding to next milestone.")
            else:
                checks.append(SafetyCheckItem(
                    name="Test Suite Execution",
                    passed=True,
                    detail="All tests passed with zero regressions.",
                    severity="INFO"
                ))
        elif test_results is None:
            is_safe = False
            reason_codes.append("TESTS_UNEXECUTED")
            blocking_conditions.append("Test suite unexecuted — cannot verify safe continuation without test evidence.")
            checks.append(SafetyCheckItem(
                name="Test Suite Execution",
                passed=False,
                detail="Test suite has not been executed yet. Run tests to verify build readiness.",
                severity="BLOCKING",
                reason_code="TESTS_UNEXECUTED"
            ))
            recommendations.append("Execute 'python verify_release.py' or run tests in Verify tab.")
        else:
            tests_passed = bool(test_results.get("passed", False))
            fail_count = int(test_results.get("failed_count", 0))
            pass_count = int(test_results.get("passed_count", 0))
            total = fail_count + pass_count

            if tests_passed and fail_count == 0:
                checks.append(SafetyCheckItem(
                    name="Test Suite Execution",
                    passed=True,
                    detail=f"All {pass_count} tests passed with zero regressions.",
                    severity="INFO"
                ))
            else:
                is_safe = False
                reason_codes.append("TESTS_FAILING")
                blocking_msg = f"{fail_count} test(s) failing out of {total}."
                blocking_conditions.append(blocking_msg)
                checks.append(SafetyCheckItem(
                    name="Test Suite Execution",
                    passed=False,
                    detail=blocking_msg,
                    severity="BLOCKING",
                    reason_code="TESTS_FAILING"
                ))
                recommendations.append("Fix failing test assertions before proceeding to next milestone.")

        # 2. Boundary Constraints Check
        modified_files = modified_files or []
        boundary_constraints = boundary_constraints or []
        boundary_violations = []

        if forbidden_files_modified:
            for ff in forbidden_files_modified:
                boundary_violations.append(f"Forbidden file modified: '{ff}'")

        for constraint in boundary_constraints:
            c_lower = constraint.lower()
            forbidden_targets = []
            
            # Extract targets after negative phrases: "do not modify X", "do not touch X", "forbidden: X", "never touch X"
            m_neg = re.findall(r'(?:do not (?:modify|touch|change|break)|forbidden:?|never touch)\s+([a-zA-Z0-9_\-\./]+)', c_lower)
            if m_neg:
                forbidden_targets.extend([t.strip("/.,; ") for t in m_neg])

            # Also check explicit slash paths under negative constraints
            if "do not" in c_lower or "forbidden" in c_lower or "never" in c_lower:
                path_tokens = re.findall(r'[a-zA-Z0-9_\-\.]+(?:/[a-zA-Z0-9_\-\.]+)+', constraint)
                forbidden_targets.extend([p.strip("/.,; ").lower() for p in path_tokens])

            seen_targets = set()
            for target in forbidden_targets:
                target_clean = target.strip("/.,; ").lower()
                if len(target_clean) < 3 or target_clean in ("any", "the", "all", "api") or target_clean in seen_targets:
                    continue
                seen_targets.add(target_clean)
                for mf in modified_files:
                    mf_norm = mf.replace("\\", "/").lower().strip("./ ")
                    is_match = False
                    if target_clean == mf_norm or mf_norm.endswith("/" + target_clean):
                        is_match = True
                    elif "/" in target_clean and target_clean in mf_norm:
                        is_match = True
                    elif "/" not in target_clean:
                        parts = mf_norm.split("/")
                        if target_clean in parts or any(p.startswith(target_clean + ".") for p in parts) or target_clean in os.path.basename(mf_norm):
                            is_match = True

                    if is_match:
                        v_msg = f"File '{mf}' touches restricted boundary '{target_clean}' declared in constraint: \"{constraint}\""
                        boundary_violations.append(v_msg)

        if boundary_violations:
            is_safe = False
            reason_codes.append("BOUNDARY_VIOLATION")
            blocking_conditions.extend(boundary_violations)
            checks.append(SafetyCheckItem(
                name="Boundary Constraint Enforcement",
                passed=False,
                detail=f"{len(boundary_violations)} restricted file violation(s) detected.",
                severity="BLOCKING",
                reason_code="BOUNDARY_VIOLATION"
            ))
            for v in boundary_violations:
                recommendations.append(f"Revert or isolate modifications to: {v}")
        else:
            checks.append(SafetyCheckItem(
                name="Boundary Constraint Enforcement",
                passed=True,
                detail="Zero boundary constraints violated by current modifications.",
                severity="INFO"
            ))

        # 3. Circular Dependency Drift
        if cycle_count > 0:
            is_safe = False
            reason_codes.append("CIRCULAR_DEPENDENCY")
            cycle_msg = f"{cycle_count} circular dependency loop(s) detected in topology graph."
            blocking_conditions.append(cycle_msg)
            checks.append(SafetyCheckItem(
                name="Circular Dependency Topology",
                passed=False,
                detail=cycle_msg,
                severity="BLOCKING",
                reason_code="CIRCULAR_DEPENDENCY"
            ))
            recommendations.append("Break import cycles by introducing interface abstractions or extracting shared types.")
        else:
            checks.append(SafetyCheckItem(
                name="Circular Dependency Topology",
                passed=True,
                detail="Zero circular dependency cycles detected.",
                severity="INFO"
            ))

        # 4. Complexity Spikes in Modified Files
        if risks and modified_files:
            high_risk_touched = []
            for r in risks:
                fp = str(r.get("file") or r.get("file_path") or "").replace("\\", "/")
                if any(mf.replace("\\", "/").lower() in fp.lower() for mf in modified_files):
                    if r.get("level") == "HIGH" or (r.get("complexity", 1) >= 15):
                        high_risk_touched.append(fp)

            if high_risk_touched:
                reason_codes.append("COMPLEXITY_SPIKE")
                checks.append(SafetyCheckItem(
                    name="High-Complexity Hotspots",
                    passed=False,
                    detail=f"Modified files touch {len(high_risk_touched)} high-complexity hotspot(s).",
                    severity="WARNING",
                    reason_code="COMPLEXITY_SPIKE"
                ))
                recommendations.append("Ensure comprehensive test coverage for modified high-complexity methods.")
            else:
                checks.append(SafetyCheckItem(
                    name="High-Complexity Hotspots",
                    passed=True,
                    detail="Modified files do not introduce critical complexity hotspots.",
                    severity="INFO"
                ))
        # 5. Check for regressions against IssueMemory institutional ledger
        target_dir = repo_root or os.path.abspath(".")
        try:
            from ultron.core.issue_memory import IssueMemory
            memory = IssueMemory(target_dir)
            reopened = memory.list_issues(status="REOPENED")
            if reopened:
                is_safe = False
                reason_codes.append("REGRESSION_DETECTED")
                for reg in reopened:
                    blocking_msg = f"REGRESSION DETECTED: {reg.issue_id} ({reg.pillar} failure in {reg.target})"
                    blocking_conditions.append(blocking_msg)
                    checks.append(SafetyCheckItem(
                        name=f"Regression Guard: {reg.issue_id}",
                        passed=False,
                        detail=f"Historical defect '{reg.symptom}' has recurred. Target: {reg.target}",
                        severity="BLOCKING",
                        reason_code="REGRESSION_DETECTED"
                    ))
                recommendations.append("Resolve active regressions against institutional memory before checkpointing.")
            else:
                checks.append(SafetyCheckItem(
                    name="Institutional Regression Guard",
                    passed=True,
                    detail=f"Zero active regressions across {len(memory.list_issues())} tracked issues.",
                    severity="INFO"
                ))
        except Exception:
            pass

        now_iso = datetime.now(timezone.utc).isoformat()
        resolved_snap = snapshot_id or "snap_initial"

        badge = "CONTINUE BUILDING" if is_safe else "PAUSE & REVIEW"
        if is_safe:
            summary = "Continuation Readiness: Ready (0 blocking conditions detected against configured checks)."
        else:
            summary = f"Continuation Readiness: Paused ({len(blocking_conditions)} blocking condition(s) require review)."

        return ContinuationReadinessReport(
            safe_to_continue=is_safe,
            badge=badge,
            summary=summary,
            decision_type="CONTINUATION_READINESS",
            reason_codes=reason_codes,
            blocking_conditions=blocking_conditions,
            checks=[
                {
                    "name": c.name,
                    "passed": c.passed,
                    "detail": c.detail,
                    "severity": c.severity,
                    "reason_code": c.reason_code
                }
                for c in checks
            ],
            recommendations=recommendations,
            snapshot_id=str(resolved_snap),
            model_hash=str(model_hash or ""),
            checked_at=now_iso
        )
