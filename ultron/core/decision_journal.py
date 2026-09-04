"""
core/decision_journal.py — Persistent Decision Record and Recommendation Learning Journal.
Phase 2.9: Tracks Recommendation -> Decision -> Mission -> Implementation -> Outcome -> Learning.
"""
import os
import json
import time
import uuid
import shutil
from typing import Dict, List, Optional, Any
from ultron.core.models import DecisionRecord, SelectionOutcome, DecisionOutcome


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip() if path else ""


def _atomic_write_json(filepath: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_file = f"{filepath}.tmp.{os.getpid()}_{int(time.time() * 1000)}"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    for attempt in range(5):
        try:
            os.replace(tmp_file, filepath)
            break
        except (PermissionError, OSError):
            if attempt == 4:
                try:
                    shutil.copyfile(tmp_file, filepath)
                    os.remove(tmp_file)
                except OSError:
                    pass
                break
            time.sleep(0.02)


def record_recommendation_decision(
    repo_path: str,
    recommendation: Any,
    human_selected_target: str = "",
    selection_source: str = "HUMAN",
    selection_outcome: str = SelectionOutcome.PENDING.value,
    human_feedback: str = "",
    mission_id: str = "",
    attempt_id: str = "",
    checkpoint_id: str = "",
    top_alternatives: Optional[List[Dict[str, Any]]] = None,
    value_delta: Optional[Dict[str, Any]] = None
) -> DecisionRecord:
    """Creates and persists an immutable DecisionRecord in .ultron/decisions/."""
    rec_dict = recommendation.to_dict() if hasattr(recommendation, "to_dict") else dict(recommendation)
    rec_target = _normalize_path(rec_dict.get("target_file", ""))
    selected_target = _normalize_path(human_selected_target) if human_selected_target else rec_target
    target_changed = bool(selected_target and selected_target != rec_target)

    dec_id = f"dec-{uuid.uuid4().hex[:8]}"
    rec_id = rec_dict.get("recommendation_id", f"rec-{uuid.uuid4().hex[:8]}")
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    record = DecisionRecord(
        decision_id=dec_id,
        recommendation_id=rec_id,
        policy_version=rec_dict.get("policy_version", "consequence_v1"),
        engine_version=rec_dict.get("engine_version", "1.0.0"),
        created_at=created_at,
        recommended_target=rec_target,
        human_selected_target=selected_target,
        final_target_changed=target_changed,
        top_alternatives=top_alternatives or rec_dict.get("alternatives_compared", []),
        confidence_tier=rec_dict.get("confidence_tier", "HIGH"),
        evidence_tier=rec_dict.get("evidence_tier", "OBSERVED"),
        selection_source=selection_source,
        selection_outcome=selection_outcome,
        human_feedback=human_feedback,
        mission_id=mission_id,
        attempt_id=attempt_id,
        checkpoint_id=checkpoint_id,
        outcome_of_selected_target=DecisionOutcome.PENDING.value,
        value_delta=value_delta or {},
        priority_score=float(rec_dict.get("priority_score", 0.0)),
        recommendation_action=rec_dict.get("recommendation_action", "INVESTIGATE"),
        why_this=rec_dict.get("why_this", ""),
        evidence_ids=[e.get("evidence_id") for e in rec_dict.get("evidence_records", []) if isinstance(e, dict) and "evidence_id" in e],
        evidence_status=rec_dict.get("evidence_status", "FRESH")
    )

    dec_dir = os.path.join(repo_path, ".ultron", "decisions")
    file_path = os.path.join(dec_dir, f"{dec_id}.json")
    _atomic_write_json(file_path, record.to_dict())

    # If outcome is WRONG, record learning failure memory immediately
    if selection_outcome == SelectionOutcome.WRONG.value:
        record_recommendation_failure(
            repo_path=repo_path,
            decision_id=dec_id,
            failure_reason=human_feedback or "Marked as WRONG by developer",
            what_ultron_believed=record.why_this,
            what_actually_worked=selected_target
        )

    return record


def update_decision_outcome(
    repo_path: str,
    decision_id: str,
    outcome: str = DecisionOutcome.RESOLVED.value,
    selection_outcome: Optional[str] = None,
    feedback: Optional[str] = None,
    value_delta: Optional[Dict[str, Any]] = None
) -> Optional[DecisionRecord]:
    """Updates an existing decision record with implementation results."""
    dec_file = os.path.join(repo_path, ".ultron", "decisions", f"{decision_id}.json")
    if not os.path.exists(dec_file):
        return None

    try:
        with open(dec_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    data["outcome_of_selected_target"] = outcome
    if selection_outcome:
        data["selection_outcome"] = selection_outcome
    if feedback is not None:
        data["human_feedback"] = feedback
    if value_delta:
        data.setdefault("value_delta", {}).update(value_delta)

    _atomic_write_json(dec_file, data)
    return DecisionRecord(**data)


def list_decisions(repo_path: str, limit: int = 50) -> List[DecisionRecord]:
    """Lists saved decisions sorted by newest first."""
    dec_dir = os.path.join(repo_path, ".ultron", "decisions")
    if not os.path.exists(dec_dir):
        return []

    records = []
    for f in os.listdir(dec_dir):
        if f.endswith(".json") and f.startswith("dec-"):
            try:
                with open(os.path.join(dec_dir, f), "r", encoding="utf-8") as fp:
                    records.append(DecisionRecord(**json.load(fp)))
            except Exception:
                continue

    records.sort(key=lambda r: r.created_at, reverse=True)
    return records[:limit]


def record_recommendation_failure(
    repo_path: str,
    decision_id: str,
    failure_reason: str,
    what_ultron_believed: str,
    what_actually_worked: str
) -> Dict[str, Any]:
    """Creates a permanent learning failure record in .ultron/decisions/failures/."""
    fail_id = f"fail-{uuid.uuid4().hex[:8]}"
    fail_entry = {
        "failure_id": fail_id,
        "decision_id": decision_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "failure_reason": failure_reason,
        "what_ultron_believed": what_ultron_believed,
        "what_actually_worked": what_actually_worked,
        "recommendation_guard": f"Prioritize verified task context over raw structural consequence when intent matches '{what_actually_worked}'."
    }
    fail_dir = os.path.join(repo_path, ".ultron", "decisions", "failures")
    _atomic_write_json(os.path.join(fail_dir, f"{fail_id}.json"), fail_entry)
    return fail_entry


def get_decision_learning_summary(repo_path: str) -> Dict[str, Any]:
    """Aggregates decision journal statistics and learning failure guards."""
    decisions = list_decisions(repo_path, limit=500)
    total = len(decisions)
    useful = sum(1 for d in decisions if d.selection_outcome == SelectionOutcome.USEFUL.value)
    plausible = sum(1 for d in decisions if d.selection_outcome == SelectionOutcome.PLAUSIBLE.value)
    wrong = sum(1 for d in decisions if d.selection_outcome == SelectionOutcome.WRONG.value)
    insufficient = sum(1 for d in decisions if d.selection_outcome == SelectionOutcome.INSUFFICIENT_EVIDENCE.value)
    counterfactual = sum(1 for d in decisions if d.final_target_changed)
    resolved = sum(1 for d in decisions if d.outcome_of_selected_target == DecisionOutcome.RESOLVED.value)

    fail_dir = os.path.join(repo_path, ".ultron", "decisions", "failures")
    failures_count = len(os.listdir(fail_dir)) if os.path.exists(fail_dir) else 0

    return {
        "total_decisions": total,
        "useful_count": useful,
        "plausible_count": plausible,
        "wrong_count": wrong,
        "insufficient_evidence_count": insufficient,
        "counterfactual_choice_count": counterfactual,
        "resolved_outcomes": resolved,
        "decision_accuracy_rate": round(useful / total, 3) if total > 0 else 1.0,
        "active_failure_guards": failures_count
    }
