"""
ultron.core.work_queue
Authoritative Development Work Queue & Single Lifecycle Authority.

Constitutional Invariants:
1. ONE CURRENT LIFECYCLE STATE
2. ONE ACTIVE ISSUE
3. ONE ACTIVE ATTEMPT
4. ONE AUTHORITATIVE REPOSITORY IDENTITY
"""

import os
import json
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""
    pass


class WorkStateConflictError(Exception):
    """Raised when concurrent operations attempt conflicting updates."""
    pass


VALID_STATES: Set[str] = {
    "IDLE",
    "DISCOVERING",
    "ISSUE_SELECTED",
    "MISSION_READY",
    "IMPLEMENTING",
    "OBSERVING",
    "VERIFYING",
    "BLOCKED",
    "CHECKPOINT_READY",
    "CHECKPOINTED",
    "REPAIR_REQUIRED"
}

STATE_TRANSITIONS: Dict[str, Set[str]] = {
    "IDLE": {"DISCOVERING", "ISSUE_SELECTED"},
    "DISCOVERING": {"ISSUE_SELECTED", "IDLE"},
    "ISSUE_SELECTED": {"MISSION_READY"},
    "MISSION_READY": {"IMPLEMENTING"},
    "IMPLEMENTING": {"OBSERVING"},
    "OBSERVING": {"VERIFYING"},
    "VERIFYING": {"CHECKPOINT_READY", "REPAIR_REQUIRED", "BLOCKED"},
    "CHECKPOINT_READY": {"CHECKPOINTED"},
    "CHECKPOINTED": {"DISCOVERING", "IDLE"},
    "REPAIR_REQUIRED": {"MISSION_READY", "IMPLEMENTING"},
    "BLOCKED": {"IDLE", "REPAIR_REQUIRED"}
}


@dataclass
class WorkState:
    status: str = "IDLE"
    active_issue: Optional[str] = None
    repository_id: str = ""
    snapshot_id: str = ""
    mission_id: Optional[str] = None
    attempt_number: int = 0
    checkpoint_id: Optional[str] = None
    admissible_next_states: List[str] = field(default_factory=list)
    blocking_reasons: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkState":
        valid_keys = {
            "status", "active_issue", "repository_id", "snapshot_id",
            "mission_id", "attempt_number", "checkpoint_id",
            "admissible_next_states", "blocking_reasons", "updated_at"
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class WorkQueue:
    """
    Authoritative state coordinator managing development iterations across the repository.
    Guarantees thread-safe transitions and atomic file persistence.
    """
    _instance_lock = threading.Lock()
    _instances: Dict[str, "WorkQueue"] = {}

    def __new__(cls, repo_root: str):
        norm_root = os.path.abspath(repo_root)
        with cls._instance_lock:
            if norm_root not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[norm_root] = instance
            return cls._instances[norm_root]

    def __init__(self, repo_root: str):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.repo_root = os.path.abspath(repo_root)
        self.work_dir = os.path.join(self.repo_root, ".ultron", "work")
        self.active_file = os.path.join(self.work_dir, "active_state.json")
        self.history_file = os.path.join(self.work_dir, "history.jsonl")
        self.lock = threading.Lock()
        os.makedirs(self.work_dir, exist_ok=True)
        self._ensure_active_state_file()
        self._initialized = True

    def _ensure_active_state_file(self):
        with self.lock:
            if not os.path.exists(self.active_file):
                initial_state = WorkState(
                    status="IDLE",
                    admissible_next_states=list(STATE_TRANSITIONS["IDLE"]),
                    updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                )
                self._persist_state_unlocked(initial_state)

    def get_state(self) -> WorkState:
        with self.lock:
            return self._read_state_unlocked()

    def _read_state_unlocked(self) -> WorkState:
        if not os.path.exists(self.active_file):
            return WorkState(
                status="IDLE",
                admissible_next_states=list(STATE_TRANSITIONS["IDLE"])
            )
        try:
            with open(self.active_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            st = WorkState.from_dict(data)
            # Recompute admissible states dynamically
            st.admissible_next_states = list(STATE_TRANSITIONS.get(st.status, set()))
            return st
        except Exception:
            return WorkState(
                status="IDLE",
                admissible_next_states=list(STATE_TRANSITIONS["IDLE"])
            )

    def _persist_state_unlocked(self, state: WorkState):
        state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state.admissible_next_states = list(STATE_TRANSITIONS.get(state.status, set()))
        payload = state.to_dict()

        # Atomic file write to avoid corrupted JSON on crash (Windows-safe retry)
        tmp_file = f"{self.active_file}.tmp.{os.getpid()}_{int(time.time()*1000)}"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        for _attempt in range(5):
            try:
                os.replace(tmp_file, self.active_file)
                break
            except (PermissionError, OSError):
                if _attempt == 4:
                    import shutil
                    try:
                        shutil.copyfile(tmp_file, self.active_file)
                        os.remove(tmp_file)
                    except OSError:
                        pass
                    break
                time.sleep(0.05)

        # Append to audit history
        history_entry = {
            "timestamp": state.updated_at,
            "status": state.status,
            "active_issue": state.active_issue,
            "mission_id": state.mission_id,
            "attempt_number": state.attempt_number,
            "checkpoint_id": state.checkpoint_id,
            "blocking_reasons": state.blocking_reasons
        }
        try:
            with open(self.history_file, "a", encoding="utf-8") as hf:
                hf.write(json.dumps(history_entry) + "\n")
        except Exception:
            pass

    def transition_to(
        self,
        next_state: str,
        context: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> WorkState:
        """
        Executes a validated, thread-safe transition of the development lifecycle state.
        Raises InvalidStateTransitionError if the requested transition is illegal.
        """
        if next_state not in VALID_STATES:
            raise InvalidStateTransitionError(f"Unknown state '{next_state}'. Valid states: {sorted(VALID_STATES)}")

        with self.lock:
            current = self._read_state_unlocked()
            allowed = STATE_TRANSITIONS.get(current.status, set())

            if not force and next_state not in allowed:
                raise InvalidStateTransitionError(
                    f"Illegal transition from '{current.status}' to '{next_state}'. "
                    f"Admissible transitions: {sorted(allowed)}"
                )

            # Apply context mutations
            context = context or {}
            current.status = next_state
            if "active_issue" in context:
                current.active_issue = context["active_issue"]
            if "repository_id" in context:
                current.repository_id = context["repository_id"]
            if "snapshot_id" in context:
                current.snapshot_id = context["snapshot_id"]
            if "mission_id" in context:
                current.mission_id = context["mission_id"]
            if "attempt_number" in context:
                current.attempt_number = context["attempt_number"]
            if "checkpoint_id" in context:
                current.checkpoint_id = context["checkpoint_id"]
            if "blocking_reasons" in context:
                current.blocking_reasons = context["blocking_reasons"]
            else:
                if next_state not in ("BLOCKED", "REPAIR_REQUIRED"):
                    current.blocking_reasons = []

            self._persist_state_unlocked(current)
            return current

    def reset(self, repository_id: str = "") -> WorkState:
        """Resets the work queue to clean IDLE state."""
        with self.lock:
            state = WorkState(
                status="IDLE",
                active_issue=None,
                repository_id=repository_id,
                snapshot_id="",
                mission_id=None,
                attempt_number=0,
                checkpoint_id=None,
                admissible_next_states=list(STATE_TRANSITIONS["IDLE"]),
                blocking_reasons=[]
            )
            self._persist_state_unlocked(state)
            return state
