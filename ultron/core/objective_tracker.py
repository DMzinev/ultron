"""
Ultron Core — Objective & Task Progression Engine
Enables progressive AI-assisted repository development by tracking active developer objectives,
completed milestones, active tasks, boundary constraints, affected modules, and acceptance criteria.
Strictly decoupled from prompt generation and repository analysis.
"""

import os
import re
import json
import uuid
import hashlib
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_OBJECTIVE_LOCK = threading.RLock()


class ObjectiveTracker:
    """
    Manages active developer intentions, task milestones, constraints, and progress.
    Guarantees atomic persistence, workspace and repository identity binding, and deterministic state transitions.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.normcase(os.path.abspath(repo_path))
        self.workspace_id, self.repository_id = self._resolve_identities()
        self.repo_id = self.repository_id  # Backwards compatibility alias
        self.storage_dir = os.path.join(self.repo_path, ".ultron")
        self.storage_file = os.path.join(self.storage_dir, "objective.json")

    def _resolve_identities(self) -> tuple[str, str]:
        """
        Resolves (workspace_id, repository_id).
        workspace_id: deterministic hash of local canonical filesystem path.
        repository_id: logical repository identity (git remote origin / root commit if git, else workspace_id).
        """
        workspace_id = hashlib.sha256(self.repo_path.encode("utf-8")).hexdigest()[:16]
        repository_id = workspace_id

        git_target = os.path.join(self.repo_path, ".git")
        if os.path.exists(git_target):
            try:
                cmd = ["git", "config", "--get", "remote.origin.url"]
                res = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, timeout=2.0, encoding="utf-8", errors="replace")
                remote_url = res.stdout.strip()
                if remote_url:
                    norm_url = re.sub(r'\.git$', '', remote_url).strip().lower()
                    repository_id = hashlib.sha256(norm_url.encode("utf-8")).hexdigest()[:16]
                else:
                    res_root = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=self.repo_path, capture_output=True, text=True, timeout=2.0, encoding="utf-8", errors="replace")
                    root_shas = res_root.stdout.strip().split()
                    if root_shas:
                        repository_id = hashlib.sha256(root_shas[0].encode("utf-8")).hexdigest()[:16]
            except Exception:
                repository_id = workspace_id

        return workspace_id, repository_id

    def _default_state(self) -> Dict[str, Any]:
        now_str = datetime.now(timezone.utc).isoformat()
        return {
            "workspace_id": self.workspace_id,
            "repository_id": self.repository_id,
            "repository_root": self.repo_path,
            "objective_id": f"obj_{self.repository_id}_{now_str[:10].replace('-', '')}",
            "title": "Initial Repository Setup & Discovery",
            "description": "Establish baseline repository structure and verify architectural health.",
            "status": "in_progress",
            "progress_pct": 25.0,
            "created_at": now_str,
            "updated_at": now_str,
            "tasks": [
                {
                    "id": "task_1",
                    "title": "Analyze codebase architecture & dependency topology",
                    "description": "Scan AST facts and identify high-coupling modules.",
                    "status": "done",
                    "completed_at": now_str
                },
                {
                    "id": "task_2",
                    "title": "Define active development objective",
                    "description": "Specify the feature, refactoring goal, or bugfix to implement with your AI coding agent.",
                    "status": "in_progress",
                    "completed_at": None
                },
                {
                    "id": "task_3",
                    "title": "Generate structured agent context & execute build",
                    "description": "Pass focused context to Claude, Cursor, Antigravity, or Aider.",
                    "status": "pending",
                    "completed_at": None
                },
                {
                    "id": "task_4",
                    "title": "Verify changes & check architectural drift",
                    "description": "Run tests and confirm no regressions were introduced.",
                    "status": "pending",
                    "completed_at": None
                }
            ],
            "constraints": [
                "Preserve all existing public API method signatures.",
                "Maintain 100% test suite pass rate."
            ],
            "acceptance": [
                "All unit and integration tests pass without error.",
                "Zero new circular dependency loops introduced."
            ],
            "affected_areas": []
        }

    def _load(self) -> Dict[str, Any]:
        with _OBJECTIVE_LOCK:
            if not os.path.exists(self.storage_file):
                return self._default_state()
            try:
                with open(self.storage_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                    if not content:
                        return self._default_state()
                    data = json.loads(content)
                    if not isinstance(data, dict):
                        return self._default_state()
                    return self._normalize_state(data)
            except (json.JSONDecodeError, OSError, IOError, UnicodeDecodeError):
                return self._default_state()

    def _cleanup_orphaned_tmp(self):
        try:
            if os.path.isdir(self.storage_dir):
                for fname in os.listdir(self.storage_dir):
                    if fname.endswith(".tmp"):
                        try:
                            os.remove(os.path.join(self.storage_dir, fname))
                        except OSError:
                            pass
        except Exception:
            pass

    def _save(self, state: Dict[str, Any]) -> bool:
        """Atomically persists state using temporary file replace."""
        tmp_file = self.storage_file + ".tmp"
        with _OBJECTIVE_LOCK:
            try:
                os.makedirs(self.storage_dir, exist_ok=True)
                state["repository_id"] = self.repo_id
                state["repository_root"] = self.repo_path
                state["updated_at"] = datetime.now(timezone.utc).isoformat()
                state["progress_pct"] = self._calculate_progress(state.get("tasks", []))
                
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                
                os.replace(tmp_file, self.storage_file)
                self._cleanup_orphaned_tmp()
                return True
            except (OSError, IOError, Exception):
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
                return False

    def _calculate_progress(self, tasks: List[Dict[str, Any]]) -> float:
        if not tasks:
            return 0.0
        total = len(tasks)
        done = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "done")
        return round((done / total) * 100.0, 1)

    def _normalize_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        default = self._default_state()
        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            tasks = default["tasks"]
        
        normalized_tasks = []
        for i, t in enumerate(tasks):
            if isinstance(t, dict):
                tid = str(t.get("id") or f"task_{i+1}")
                normalized_tasks.append({
                    "id": tid,
                    "title": str(t.get("title") or f"Task {i+1}").strip(),
                    "description": str(t.get("description") or "").strip(),
                    "status": str(t.get("status") or "pending"),
                    "completed_at": t.get("completed_at")
                })
            elif isinstance(t, str):
                normalized_tasks.append({
                    "id": f"task_{i+1}",
                    "title": t.strip(),
                    "description": "",
                    "status": "pending",
                    "completed_at": None
                })

        constraints = data.get("constraints")
        if not isinstance(constraints, list):
            constraints = default["constraints"]

        acceptance = data.get("acceptance")
        if not isinstance(acceptance, list):
            acceptance = default["acceptance"]

        affected = data.get("affected_areas")
        if not isinstance(affected, list):
            affected = []

        res = {
            "workspace_id": self.workspace_id,
            "repository_id": self.repository_id,
            "repository_root": self.repo_path,
            "objective_id": str(data.get("objective_id") or default["objective_id"]),
            "title": str(data.get("title") or default["title"]).strip(),
            "description": str(data.get("description") or default["description"]).strip(),
            "status": str(data.get("status") or "in_progress"),
            "progress_pct": self._calculate_progress(normalized_tasks),
            "created_at": data.get("created_at") or default["created_at"],
            "updated_at": data.get("updated_at") or default["updated_at"],
            "tasks": normalized_tasks,
            "constraints": [str(c).strip() for c in constraints if str(c).strip()],
            "acceptance": [str(a).strip() for a in acceptance if str(a).strip()],
            "affected_areas": [str(af).strip() for af in affected if str(af).strip()]
        }
        return res

    def get_objective(self) -> Dict[str, Any]:
        """Returns the active repository objective and task progression."""
        state = self._load()
        state["progress_pct"] = self._calculate_progress(state.get("tasks", []))
        return state

    def set_objective(
        self,
        title: str,
        description: str = "",
        tasks: Optional[List[Any]] = None,
        constraints: Optional[List[str]] = None,
        acceptance: Optional[List[str]] = None,
        affected_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sets or replaces the active development objective."""
        state = self._load()
        state["title"] = str(title).strip() or "Untitled Objective"
        if description is not None:
            state["description"] = str(description).strip()

        if tasks is not None:
            new_tasks = []
            for i, t in enumerate(tasks):
                if isinstance(t, dict):
                    new_tasks.append({
                        "id": str(t.get("id") or f"task_{i+1}"),
                        "title": str(t.get("title") or f"Task {i+1}").strip(),
                        "description": str(t.get("description") or "").strip(),
                        "status": str(t.get("status") or ("in_progress" if i == 0 else "pending")),
                        "completed_at": t.get("completed_at")
                    })
                elif isinstance(t, str):
                    new_tasks.append({
                        "id": f"task_{i+1}",
                        "title": t.strip(),
                        "description": "",
                        "status": "in_progress" if i == 0 else "pending",
                        "completed_at": None
                    })
            state["tasks"] = new_tasks

        if constraints is not None:
            state["constraints"] = [str(c).strip() for c in constraints if str(c).strip()]
        if acceptance is not None:
            state["acceptance"] = [str(a).strip() for a in acceptance if str(a).strip()]
        if affected_areas is not None:
            state["affected_areas"] = [str(a).strip() for a in affected_areas if str(a).strip()]

        state["progress_pct"] = self._calculate_progress(state["tasks"])
        state["status"] = "done" if state["progress_pct"] >= 100.0 else "in_progress"
        saved = self._save(state)
        return {"success": saved, "data": state} if not saved else state

    def add_task(self, title: str, description: str = "", status: str = "pending") -> Dict[str, Any]:
        """Appends a new task milestone to the active objective."""
        state = self._load()
        tasks = state.get("tasks", [])
        
        # If no tasks are currently in_progress or pending, promote immediately
        if not any(t.get("status") == "in_progress" for t in tasks) and not any(t.get("status") == "pending" for t in tasks):
            status = "in_progress"

        new_task = {
            "id": f"task_{len(tasks)+1}_{uuid.uuid4().hex[:4]}",
            "title": str(title).strip(),
            "description": str(description).strip(),
            "status": status,
            "completed_at": datetime.now(timezone.utc).isoformat() if status == "done" else None
        }
        tasks.append(new_task)
        state["tasks"] = tasks
        state["progress_pct"] = self._calculate_progress(tasks)
        state["status"] = "done" if state["progress_pct"] >= 100.0 else "in_progress"
        self._save(state)
        return state

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Marks a task as completed and automatically promotes the next pending task."""
        state = self._load()
        tasks = state.get("tasks", [])
        found = False

        for t in tasks:
            if str(t.get("id")) == str(task_id):
                t["status"] = "done"
                t["completed_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break

        if not found:
            return {"success": False, "error": f"Task '{task_id}' not found", "state": state}

        # Auto-promote next pending task if none is currently in_progress
        has_in_progress = any(t.get("status") == "in_progress" for t in tasks)
        if not has_in_progress:
            for t in tasks:
                if t.get("status") == "pending":
                    t["status"] = "in_progress"
                    break

        state["progress_pct"] = self._calculate_progress(tasks)
        if state["progress_pct"] >= 100.0:
            state["status"] = "done"
        
        saved = self._save(state)
        return {"success": saved, "task_id": task_id, "state": state}

    def update_task(self, task_id: str, status: Optional[str] = None, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Updates specific properties of an existing task."""
        state = self._load()
        tasks = state.get("tasks", [])
        found = False

        for t in tasks:
            if str(t.get("id")) == str(task_id):
                if status is not None:
                    t["status"] = str(status)
                    if status == "done":
                        t["completed_at"] = datetime.now(timezone.utc).isoformat()
                    else:
                        t["completed_at"] = None
                if title is not None:
                    t["title"] = str(title).strip()
                if description is not None:
                    t["description"] = str(description).strip()
                found = True
                break

        if not found:
            return {"success": False, "error": f"Task '{task_id}' not found", "state": state}

        state["progress_pct"] = self._calculate_progress(tasks)
        state["status"] = "done" if state["progress_pct"] >= 100.0 else "in_progress"
        saved = self._save(state)
        return {"success": saved, "task_id": task_id, "state": state}
