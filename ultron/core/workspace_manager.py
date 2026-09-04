"""
ultron.core.workspace_manager
Deterministic Multi-Repository Workspace Switcher and Monorepo Subpackage Navigator.
"""

import os
import hashlib
from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class WorkspaceManager:
    """
    Deterministic workspace manager for registering repositories,
    discovering monorepo subpackages, and maintaining partitioned workspace contexts.
    """

    MANAGER_VERSION = "1.0-workspace-mesh"

    IGNORE_DIRS = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".idea", ".vscode", ".gemini", ".synapse"
    }

    def __init__(self, initial_path: Optional[str] = None):
        self._workspaces: Dict[str, Dict[str, Any]] = {}
        self._active_id: Optional[str] = None

        if initial_path:
            try:
                self.add_workspace(initial_path)
            except Exception:
                pass

    def _generate_workspace_id(self, abs_path: str) -> str:
        """Generates deterministic workspace identifier from normalized path."""
        norm = norm_path(os.path.abspath(abs_path)).lower()
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]
        base = os.path.basename(norm.rstrip("/")) or "root"
        return f"ws-{base}-{h}"

    def discover_monorepo_subpackages(self, root_path: str) -> List[Dict[str, Any]]:
        """
        Scans root directory (up to depth 3) to discover monorepo subpackages,
        pruning standard dependency and build directories.
        """
        if not os.path.isdir(root_path):
            return []

        subpackages = []
        root_abs = os.path.abspath(root_path)

        for root, dirs, files in os.walk(root_abs):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            # Calculate relative depth
            rel = os.path.relpath(root, root_abs)
            depth = 0 if rel == "." else len(rel.replace("\\", "/").split("/"))
            if depth > 3:
                dirs[:] = []
                continue

            if rel == ".":
                continue

            manifest_type = None
            if "pyproject.toml" in files:
                manifest_type = "python-pyproject"
            elif "setup.py" in files:
                manifest_type = "python-setuptools"
            elif "package.json" in files:
                manifest_type = "node-package"
            elif "__init__.py" in files and depth == 1:
                manifest_type = "python-module"

            if manifest_type:
                pkg_name = os.path.basename(root)
                subpackages.append({
                    "name": pkg_name,
                    "path": norm_path(root),
                    "relative_path": norm_path(rel),
                    "manifest_type": manifest_type,
                    "depth": depth
                })

        subpackages.sort(key=lambda x: (x["depth"], x["name"]))
        return subpackages

    def add_workspace(self, path: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Registers a repository workspace and scans for subpackages.
        Raises FileNotFoundError if directory does not exist.
        """
        if not path or not isinstance(path, str) or not path.strip():
            raise ValueError("Workspace path cannot be empty")

        abs_path = os.path.abspath(os.path.normpath(path.strip()))
        if not os.path.isdir(abs_path):
            raise FileNotFoundError(f"Workspace path does not exist or is not a directory: {abs_path}")

        ws_id = self._generate_workspace_id(abs_path)
        ws_name = name or os.path.basename(abs_path.rstrip("/\\")) or "Workspace"
        subpackages = self.discover_monorepo_subpackages(abs_path)

        workspace_record = {
            "id": ws_id,
            "name": ws_name,
            "path": norm_path(abs_path),
            "subpackages": subpackages,
            "subpackage_count": len(subpackages),
            "is_monorepo": len(subpackages) > 0,
            "active": False
        }

        self._workspaces[ws_id] = workspace_record

        # Auto-activate if first workspace
        if not self._active_id:
            self.set_active_workspace(ws_id)

        return self._workspaces[ws_id]

    def set_active_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """
        Switches the currently active workspace.
        Raises KeyError if workspace_id is not registered.
        """
        if workspace_id not in self._workspaces:
            raise KeyError(f"Unknown workspace ID: {workspace_id}")

        for wid, ws in self._workspaces.items():
            ws["active"] = (wid == workspace_id)

        self._active_id = workspace_id
        return self._workspaces[workspace_id]

    def get_active_workspace(self) -> Optional[Dict[str, Any]]:
        """Returns the currently active workspace dictionary or None."""
        if not self._active_id or self._active_id not in self._workspaces:
            return None
        return self._workspaces[self._active_id]

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """Returns list of all registered workspaces sorted deterministically."""
        return sorted(list(self._workspaces.values()), key=lambda w: w["name"])
