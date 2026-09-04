"""
ultron.core.watcher_daemon
Real-Time Incremental Filesystem Watcher & AST Re-Analysis Engine.
"""

import os
import ast
import hashlib
from typing import Dict, List, Any, Optional, Set


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class IncrementalWatcherDaemon:
    """
    Lightweight, debounced watcher daemon that tracks file modifications,
    computes content fingerprints, and performs sub-30ms AST re-analysis.
    """

    PRUNE_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
        "node_modules", "venv", ".venv", "env", ".env",
        "dist", "build", "release", "scratch", ".gemini", ".synapse"
    }

    SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"}

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = norm_path(repo_path or ".")
        self.file_mtimes: Dict[str, float] = {}
        self.file_hashes: Dict[str, str] = {}
        if repo_path and os.path.exists(repo_path):
            self.sync_baseline(self.repo_path)

    @staticmethod
    def get_fingerprint(file_path: str) -> str:
        """Calculates fast SHA-256 fingerprint from file bytes."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (OSError, IOError):
            return ""

    def sync_baseline(self, repo_path: Optional[str] = None) -> int:
        """
        Scans repository directory and records baseline mtimes and hashes.
        Returns total number of tracked source files.
        """
        root = norm_path(repo_path or self.repo_path)
        self.file_mtimes.clear()
        self.file_hashes.clear()

        if not os.path.isdir(root):
            return 0

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored directory trees
            dirnames[:] = [d for d in dirnames if d not in self.PRUNE_DIRS]

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(dirpath, fname)
                    rel_path = norm_path(os.path.relpath(full_path, root))
                    try:
                        mtime = os.path.getmtime(full_path)
                        self.file_mtimes[rel_path] = mtime
                        self.file_hashes[rel_path] = self.get_fingerprint(full_path)
                    except (OSError, IOError):
                        pass

        return len(self.file_mtimes)

    def scan_changes(self, repo_path: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Scans workspace and returns categorized file changes: added, modified, deleted.
        """
        root = norm_path(repo_path or self.repo_path)
        current_files: Set[str] = set()
        added: List[str] = []
        modified: List[str] = []
        deleted: List[str] = []

        if not os.path.isdir(root):
            return {"added": [], "modified": [], "deleted": list(self.file_mtimes.keys())}

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self.PRUNE_DIRS]

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(dirpath, fname)
                    rel_path = norm_path(os.path.relpath(full_path, root))
                    current_files.add(rel_path)

                    try:
                        mtime = os.path.getmtime(full_path)
                        if rel_path not in self.file_mtimes:
                            # New file added
                            self.file_mtimes[rel_path] = mtime
                            self.file_hashes[rel_path] = self.get_fingerprint(full_path)
                            added.append(rel_path)
                        elif mtime != self.file_mtimes[rel_path]:
                            # Timestamp changed -> verify content hash
                            new_hash = self.get_fingerprint(full_path)
                            if new_hash != self.file_hashes.get(rel_path, ""):
                                self.file_mtimes[rel_path] = mtime
                                self.file_hashes[rel_path] = new_hash
                                modified.append(rel_path)
                            else:
                                # mtime changed but content identical (touch)
                                self.file_mtimes[rel_path] = mtime
                    except (OSError, IOError):
                        pass

        # Check for deleted files
        for tracked_file in list(self.file_mtimes.keys()):
            if tracked_file not in current_files:
                deleted.append(tracked_file)
                self.file_mtimes.pop(tracked_file, None)
                self.file_hashes.pop(tracked_file, None)

        added.sort()
        modified.sort()
        deleted.sort()

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }

    def reanalyze_incremental(
        self,
        repo_path: str,
        dirty_files: List[str],
        current_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Incrementally re-parses AST for dirty files and patches in-memory risk records.
        """
        root = norm_path(repo_path)
        data = dict(current_analysis or {})
        risks = list(data.get("risks", []) or [])
        risk_map = {norm_path(r.get("file", r.get("file_path", ""))): r for r in risks}

        for rel_file in dirty_files:
            rel_norm = norm_path(rel_file)
            full_path = os.path.join(root, rel_file)

            if not os.path.exists(full_path):
                # File deleted
                risk_map.pop(rel_norm, None)
                continue

            # Python AST re-analysis
            if rel_norm.endswith(".py"):
                try:
                    with open(full_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                        code = f.read()

                    tree = ast.parse(code, filename=rel_file)
                    loc = len(code.splitlines())

                    # Calculate McCabe complexity: 1 + sum(branches)
                    branches = 0
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
                            branches += 1
                        elif isinstance(node, ast.BoolOp):
                            branches += len(node.values) - 1

                    complexity = max(1.0, float(1 + branches))
                    old_risk = risk_map.get(rel_norm, {})
                    coupling = float(old_risk.get("coupling_score", 0.0))

                    impact = round((complexity * 0.5) + (coupling * 1.5), 2)
                    level = "HIGH" if impact >= 10.0 else ("MEDIUM" if impact >= 5.0 else "LOW")

                    risk_map[rel_norm] = {
                        "file": rel_norm,
                        "file_path": rel_norm,
                        "loc": loc,
                        "complexity": complexity,
                        "coupling_score": coupling,
                        "impact_score": impact,
                        "level": level,
                        "confidence": 0.95
                    }
                except (SyntaxError, OSError) as e:
                    # Capture syntax error without crashing analysis pipeline
                    old_risk = risk_map.get(rel_norm, {})
                    old_risk["syntax_error"] = str(e)
                    risk_map[rel_norm] = old_risk

        updated_risks = list(risk_map.values())
        updated_risks.sort(key=lambda r: float(r.get("impact_score", 0.0)), reverse=True)
        data["risks"] = updated_risks
        data["incremental_update"] = True
        data["dirty_files_count"] = len(dirty_files)

        return data
