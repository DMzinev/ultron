import sys
import os
import subprocess
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set

from ultron.core.system_model import EvidenceObject

logger = logging.getLogger(__name__)
_EMITTED_NO_GIT_REPO = False
BUG_FIX_PATTERN = re.compile(r"\b(fix|bug|hotfix|revert)\b", re.IGNORECASE)


class GitEvidenceAdapter:
    """
    Dedicated Evidence Adapter for Repository Git History.
    Extracts commit counts, distinct authors, bug fixes, and churn metrics into immutable EvidenceObject records.
    """

    def __init__(self, max_commits: int = 500, max_mass_commit_files: int = 100):
        self.max_commits = max_commits
        self.max_mass_commit_files = max_mass_commit_files

    def extract_raw_git_log(self, repo_path: str) -> str:
        """Extracts raw git log output from repository."""
        if not self.is_git_repository(repo_path):
            return ""
        try:
            cmd = [
                "git", "log", f"-n{self.max_commits}", "--since=180.days", "--relative",
                "--name-only", "--pretty=format:COMMIT:%H|%aN|%s"
            ]
            proc = subprocess.run(
                cmd,
                cwd=os.path.abspath(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15
            )
            return proc.stdout if proc.returncode == 0 else ""
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return ""

    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyzes repository git history and co-change statistics.
        Returns summary, hotspots, files, and co_change_matrix.
        """
        raw_log = self.extract_raw_git_log(repo_path)
        if not raw_log or not raw_log.strip():
            return {
                "summary": {"commits_parsed": 0, "total_files_tracked": 0},
                "hotspots": [],
                "files": {},
                "co_change_matrix": {}
            }

        file_commits: Dict[str, int] = {}
        co_change: Dict[str, Dict[str, int]] = {}
        current_commit_files: List[str] = []
        commits_count = 0

        for line in raw_log.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("COMMIT:"):
                commits_count += 1
                if current_commit_files and len(current_commit_files) <= self.max_mass_commit_files:
                    for i, f1 in enumerate(current_commit_files):
                        for f2 in current_commit_files[i + 1:]:
                            co_change.setdefault(f1, {})[f2] = co_change.setdefault(f1, {}).get(f2, 0) + 1
                            co_change.setdefault(f2, {})[f1] = co_change.setdefault(f2, {}).get(f1, 0) + 1
                current_commit_files = []
            else:
                parts = line.split("\t")
                fpath = parts[-1].strip()
                norm_p = os.path.normpath(fpath).replace("\\", "/")
                if norm_p.endswith(".py"):
                    file_commits[norm_p] = file_commits.get(norm_p, 0) + 1
                    if norm_p not in current_commit_files:
                        current_commit_files.append(norm_p)

        if current_commit_files and len(current_commit_files) <= self.max_mass_commit_files:
            for i, f1 in enumerate(current_commit_files):
                for f2 in current_commit_files[i + 1:]:
                    co_change.setdefault(f1, {})[f2] = co_change.setdefault(f1, {}).get(f2, 0) + 1
                    co_change.setdefault(f2, {})[f1] = co_change.setdefault(f2, {}).get(f1, 0) + 1

        co_change_matrix: Dict[str, List[Dict[str, Any]]] = {}
        for f1, partners in co_change.items():
            f1_total = max(1, file_commits.get(f1, 1))
            co_change_matrix[f1] = [
                {
                    "file": f2,
                    "co_change_ratio": round(joint / f1_total, 3),
                    "joint_commits": joint
                }
                for f2, joint in sorted(partners.items(), key=lambda item: item[1], reverse=True)
            ]

        hotspots = sorted(
            [{"file": f, "commits": c} for f, c in file_commits.items()],
            key=lambda x: x["commits"],
            reverse=True
        )[:20]

        return {
            "summary": {
                "commits_parsed": commits_count,
                "total_files_tracked": len(file_commits)
            },
            "hotspots": hotspots,
            "files": file_commits,
            "co_change_matrix": co_change_matrix
        }

    def is_git_repository(self, repo_path: str) -> bool:
        """Determines if repo_path is inside a valid git working tree."""
        if not repo_path or not os.path.isdir(repo_path):
            return False
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=os.path.abspath(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5
            )
            return proc.returncode == 0 and proc.stdout.strip() == "true"
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def get_churn_map(self, repo_path: str) -> Tuple[Dict[str, Dict[str, Any]], bool]:
        """
        Extracts 180-day commit count, distinct authors, and bug-fix commits per file.
        Returns a tuple of (churn_map, is_active).
        If history is unavailable (not a git repo, git missing, or error), returns ({}, False).
        """
        if not repo_path or not os.path.isdir(repo_path):
            return {}, False

        abs_repo = os.path.abspath(repo_path)
        if not self.is_git_repository(abs_repo):
            global _EMITTED_NO_GIT_REPO
            if not _EMITTED_NO_GIT_REPO:
                logger.info("[GitEvidenceAdapter Notice] Path '%s' is not a git repository. Skipping git history.", repo_path)
                _EMITTED_NO_GIT_REPO = True
            return {}, False

        try:
            cmd = [
                "git", "log", "--since=180.days", "--relative",
                "--name-only", "--pretty=format:COMMIT:%H|%aN|%s"
            ]
            proc = subprocess.run(
                cmd,
                cwd=abs_repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15
            )

            if proc.returncode != 0:
                logger.warning("[GitEvidenceAdapter Warning] Git log failed with code %d: %s", proc.returncode, proc.stderr)
                return {}, False

            file_commits: Dict[str, int] = {}
            file_authors: Dict[str, Set[str]] = {}
            file_bug_fixes: Dict[str, int] = {}

            current_author = ""
            current_is_fix = False

            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("COMMIT:"):
                    raw = line[len("COMMIT:"):]
                    parts = raw.split("|", 2)
                    current_author = parts[1].strip() if len(parts) > 1 else ""
                    subject = parts[2].strip() if len(parts) > 2 else ""
                    current_is_fix = bool(BUG_FIX_PATTERN.search(subject))
                else:
                    norm_path = os.path.normpath(line).replace("\\", "/")
                    if norm_path.endswith(".py"):
                        file_commits[norm_path] = file_commits.get(norm_path, 0) + 1
                        if current_author:
                            file_authors.setdefault(norm_path, set()).add(current_author)
                        if current_is_fix:
                            file_bug_fixes[norm_path] = file_bug_fixes.get(norm_path, 0) + 1

            churn_map: Dict[str, Dict[str, Any]] = {}
            for rel_path, commits in file_commits.items():
                churn_map[rel_path] = {
                    "commits": commits,
                    "authors": len(file_authors.get(rel_path, set())),
                    "bug_fixes": file_bug_fixes.get(rel_path, 0),
                    "status": "active"
                }

            return churn_map, True

        except (subprocess.SubprocessError, FileNotFoundError, OSError) as err:
            logger.warning("[GitEvidenceAdapter Error] Could not extract git history: %s", err)
            return {}, False

    def parse_git_history(self, repo_path: str) -> List[EvidenceObject]:
        """
        Parses git commit log statistics for files under repo_path.
        Returns a list of EvidenceObject records of type 'GIT_HISTORY'.
        Safely returns empty list on non-git repositories or missing git CLI.
        """
        churn_map, is_active = self.get_churn_map(repo_path)
        if not is_active:
            return []

        evidence_list: List[EvidenceObject] = []
        for rel_path, data in sorted(churn_map.items()):
            node_id = f"module:{rel_path}"
            ev = EvidenceObject(
                id=f"ev-git-{rel_path.replace('/', '_')}",
                type="GIT_HISTORY",
                subject_id=node_id,
                measurement={
                    "commits": data["commits"],
                    "authors": data["authors"],
                    "bug_fixes": data["bug_fixes"]
                },
                source={"adapter": "git", "file": rel_path}
            )
            evidence_list.append(ev)

        return evidence_list
