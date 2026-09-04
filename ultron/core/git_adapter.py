"""
Ultron Core — Dedicated Git History, Churn & Co-Change Evidence Adapter
Deterministic Git history parser, pair-wise co-change coupling, author attribution,
and complexity-churn hotspot analysis.
"""

import os
import re
import math
import subprocess
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

from ultron.core.system_model import EvidenceObject

logger = logging.getLogger(__name__)

# Word-boundary regex for defect remediation classification (prevents 'prefix', 'traffic' false-positives)
BUG_FIX_PATTERN = re.compile(
    r"\b(fix|fixes|fixed|bug|bugs|patch|patched|repair|repaired|hotfix|issue|defect|resolve|resolved|revert)\b",
    re.IGNORECASE
)


def normalize_git_path(raw_path: str) -> str:
    """
    Normalizes git output paths, stripping git quotes and resolving git rename syntax:
    - 'old_dir/{old_name => new_name}/file.py' -> 'old_dir/new_name/file.py'
    - '{old => new}/file.py' -> 'new/file.py'
    - 'old.py => new.py' -> 'new.py'
    """
    if not raw_path:
        return ""

    path = raw_path.strip().strip('"').strip("'")
    if "=>" in path:
        brace_match = re.search(r"\{([^=>]*)\s*=>\s*([^}]*)\}", path)
        if brace_match:
            prefix = path[:brace_match.start()]
            suffix = path[brace_match.end():]
            new_part = brace_match.group(2).strip()
            path = f"{prefix}{new_part}{suffix}"
        else:
            parts = path.split("=>")
            path = parts[-1].strip()

    norm = os.path.normpath(path).replace("\\", "/")
    norm = re.sub(r"^(\./)+", "", norm).lstrip("/")
    return norm


def compute_churn_velocity(commits: int, lines_added: int, lines_deleted: int) -> float:
    """
    Computes churn velocity: frequency of change scaled by log average churn depth per commit.
    Formula: C * ln(1 + (L_added + L_deleted) / C)
    """
    if commits <= 0:
        return 0.0
    total_churn = max(0, lines_added + lines_deleted)
    avg_churn_per_commit = total_churn / commits
    velocity = commits * math.log(1.0 + avg_churn_per_commit)
    return round(velocity, 2)


def compute_hotspot_score(
    mccabe_complexity: float,
    commits: int,
    lines_added: int,
    lines_deleted: int,
    bug_fixes: int = 0
) -> float:
    """
    Calculates architectural hotspot score combining McCabe complexity with churn volume and bug density.
    Formula: M * ln(1 + L_total) * (1.0 + B / C)
    """
    if commits <= 0:
        return 0.0
    complexity = max(1.0, float(mccabe_complexity))
    total_churn = max(0, lines_added + lines_deleted)
    bug_ratio = min(1.0, max(0.0, bug_fixes / commits))
    
    churn_factor = math.log(1.0 + total_churn)
    score = complexity * churn_factor * (1.0 + bug_ratio)
    return round(score, 2)


class GitEvidenceAdapter:
    """
    Dedicated Evidence Adapter for Repository Git History.
    Extracts commit counts, churn metrics, author attribution, and co-change coupling.
    Produces immutable EvidenceObject records.
    """

    def __init__(self, timeout: float = 5.0, max_commits: int = 200, max_mass_commit_files: int = 50):
        self.timeout = timeout
        self.max_commits = max_commits
        self.max_mass_commit_files = max_mass_commit_files

    def is_git_repository(self, repo_path: str) -> bool:
        """
        Safely checks if the given path contains a valid .git directory or file (worktrees/submodules).
        """
        if not repo_path or not isinstance(repo_path, str):
            return False
        abs_repo = os.path.abspath(repo_path)
        git_entry = os.path.join(abs_repo, ".git")
        return os.path.exists(git_entry)

    def extract_raw_git_log(self, repo_path: str) -> Optional[str]:
        """
        Executes git log with numstat and structured format header under strict time bounds.
        Returns stdout string, or None if execution failed, empty repo, or timed out.
        """
        if not self.is_git_repository(repo_path):
            logger.info("[GitEvidenceAdapter Notice] Path '%s' is not a git repository root. Skipping git history.", repo_path)
            return None

        abs_repo = os.path.abspath(repo_path)
        cmd = [
            "git",
            "-c", "core.quotepath=false",
            "log",
            "-n", str(self.max_commits),
            "--numstat",
            "--pretty=format:COMMIT:%H|%an|%ae|%s"
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=abs_repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout
            )
            if proc.returncode != 0:
                # Code 128 on empty repos before first commit is a normal non-error
                if "does not have any commits" in proc.stderr or "fatal: your current branch" in proc.stderr:
                    logger.debug("[GitEvidenceAdapter] Empty repository with 0 commits.")
                else:
                    logger.warning("[GitEvidenceAdapter Warning] Git log returned non-zero code %d: %s", proc.returncode, proc.stderr.strip())
                return None
            return proc.stdout
        except subprocess.TimeoutExpired:
            logger.info("[GitEvidenceAdapter Notice] Git history extraction timed out after %.1fs on repository '%s'.", self.timeout, repo_path)
            return None
        except (subprocess.SubprocessError, FileNotFoundError, PermissionError, OSError) as err:
            logger.warning("[GitEvidenceAdapter Error] Could not extract git history: %s", err)
            return None

    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Parses git commit log statistics for files under repo_path.
        Returns structured dictionary containing per-file metrics, co-change graph, and authors.
        """
        raw_log = self.extract_raw_git_log(repo_path)
        if not raw_log:
            return {
                "files": {},
                "co_change_matrix": {},
                "hotspots": [],
                "summary": {"commits_parsed": 0, "unique_authors": 0, "files_tracked": 0}
            }

        file_commits: Dict[str, int] = defaultdict(int)
        file_lines_added: Dict[str, int] = defaultdict(int)
        file_lines_deleted: Dict[str, int] = defaultdict(int)
        file_bug_fixes: Dict[str, int] = defaultdict(int)
        file_authors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_last_commit: Dict[str, Dict[str, str]] = {}
        
        commit_file_sets: List[Set[str]] = []
        unique_authors_global: Set[str] = set()
        total_commits_count = 0

        current_commit_hash = ""
        current_author_name = ""
        current_author_email = ""
        current_subject = ""
        current_is_fix = False
        current_commit_files: Set[str] = set()

        for line in raw_log.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT:"):
                if current_commit_files:
                    # Filter out mass commits (>50 files, e.g. mass formatting) to avoid spurious co-change coupling
                    if len(current_commit_files) <= self.max_mass_commit_files:
                        commit_file_sets.append(current_commit_files)
                    current_commit_files = set()

                total_commits_count += 1
                header_parts = line[len("COMMIT:"):].split("|", 3)
                current_commit_hash = header_parts[0] if len(header_parts) > 0 else ""
                current_author_name = header_parts[1] if len(header_parts) > 1 else "Unknown"
                current_author_email = header_parts[2] if len(header_parts) > 2 else ""
                current_subject = header_parts[3] if len(header_parts) > 3 else ""

                if current_author_name:
                    unique_authors_global.add(current_author_name)

                # Word-boundary regex for fix classification
                current_is_fix = bool(BUG_FIX_PATTERN.search(current_subject))
            else:
                parts = line.split("\t", 2)
                if len(parts) != 3:
                    continue

                added_str, deleted_str, raw_file_path = parts
                norm_file = normalize_git_path(raw_file_path)

                if not norm_file or not norm_file.endswith(".py"):
                    continue

                # Handle binary files ('-') gracefully
                added = int(added_str) if added_str.isdigit() else 0
                deleted = int(deleted_str) if deleted_str.isdigit() else 0

                file_commits[norm_file] += 1
                file_lines_added[norm_file] += added
                file_lines_deleted[norm_file] += deleted
                file_authors[norm_file][current_author_name] += 1

                if current_is_fix:
                    file_bug_fixes[norm_file] += 1

                if norm_file not in file_last_commit:
                    file_last_commit[norm_file] = {
                        "hash": current_commit_hash,
                        "author": current_author_name,
                        "subject": current_subject
                    }

                current_commit_files.add(norm_file)

        # Flush trailing commit
        if current_commit_files and len(current_commit_files) <= self.max_mass_commit_files:
            commit_file_sets.append(current_commit_files)

        # Pair-wise co-change coupling calculation
        joint_commits: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for file_set in commit_file_sets:
            if len(file_set) < 2:
                continue
            file_list = sorted(file_set)
            for i, file_a in enumerate(file_list):
                for file_b in file_list[i + 1:]:
                    joint_commits[file_a][file_b] += 1
                    joint_commits[file_b][file_a] += 1

        co_change_matrix: Dict[str, List[Dict[str, Any]]] = {}
        for file_a, partners in joint_commits.items():
            commits_a = file_commits.get(file_a, 1)
            coupled_list = []
            for file_b, n_joint in partners.items():
                ratio = round(n_joint / commits_a, 4)
                coupled_list.append({
                    "file": file_b,
                    "joint_commits": n_joint,
                    "co_change_ratio": ratio
                })
            coupled_list.sort(key=lambda x: (x["co_change_ratio"], x["joint_commits"]), reverse=True)
            co_change_matrix[file_a] = coupled_list

        files_data: Dict[str, Any] = {}
        hotspots_list: List[Dict[str, Any]] = []

        for rel_path, commits in sorted(file_commits.items()):
            added = file_lines_added.get(rel_path, 0)
            deleted = file_lines_deleted.get(rel_path, 0)
            fixes = file_bug_fixes.get(rel_path, 0)
            total_churn = added + deleted
            velocity = compute_churn_velocity(commits, added, deleted)
            hotspot = compute_hotspot_score(1.0, commits, added, deleted, fixes)

            authors_map = dict(file_authors.get(rel_path, {}))
            top_author = max(authors_map.items(), key=lambda x: x[1])[0] if authors_map else "Unknown"
            top_author_commits = authors_map.get(top_author, 0)
            top_author_ratio = round(top_author_commits / commits, 4) if commits > 0 else 0.0

            file_metric = {
                "file": rel_path,
                "commits": commits,
                "bug_fixes": fixes,
                "lines_added": added,
                "lines_deleted": deleted,
                "total_churn": total_churn,
                "churn_velocity": velocity,
                "hotspot_score": hotspot,
                "top_author": top_author,
                "top_author_ratio": top_author_ratio,
                "distinct_authors": len(authors_map),
                "authors": authors_map,
                "last_commit": file_last_commit.get(rel_path, {}),
                "co_changes": co_change_matrix.get(rel_path, [])
            }
            files_data[rel_path] = file_metric
            hotspots_list.append({
                "file": rel_path,
                "hotspot_score": hotspot,
                "commits": commits,
                "total_churn": total_churn,
                "bug_fixes": fixes,
                "churn_velocity": velocity
            })

        hotspots_list.sort(key=lambda x: x["hotspot_score"], reverse=True)

        return {
            "files": files_data,
            "co_change_matrix": co_change_matrix,
            "hotspots": hotspots_list,
            "summary": {
                "commits_parsed": total_commits_count,
                "unique_authors": len(unique_authors_global),
                "files_tracked": len(files_data)
            }
        }

    def parse_git_history(self, repo_path: str) -> List[EvidenceObject]:
        """
        Parses git commit log statistics for files under repo_path.
        Returns a list of immutable EvidenceObject records of type 'GIT_HISTORY'.
        Maintains strict backwards compatibility with existing risk scoring and system models.
        """
        analysis = self.analyze_repository(repo_path)
        files_data = analysis.get("files", {})
        evidence_list: List[EvidenceObject] = []

        for rel_path, metrics in files_data.items():
            node_id = f"module:{rel_path}"
            top_co_changes = metrics.get("co_changes", [])[:5]

            ev = EvidenceObject(
                id=f"ev-git-{rel_path.replace('/', '_')}",
                type="GIT_HISTORY",
                subject_id=node_id,
                measurement={
                    "commits": metrics["commits"],
                    "bug_fixes": metrics["bug_fixes"],
                    "lines_added": metrics["lines_added"],
                    "lines_deleted": metrics["lines_deleted"],
                    "total_churn": metrics["total_churn"],
                    "churn_velocity": metrics["churn_velocity"],
                    "hotspot_score": metrics["hotspot_score"],
                    "top_author": metrics["top_author"],
                    "top_author_ratio": metrics["top_author_ratio"],
                    "distinct_authors": metrics["distinct_authors"],
                    "co_changes": top_co_changes
                },
                source={
                    "adapter": "git",
                    "file": rel_path
                }
            )
            evidence_list.append(ev)

        return evidence_list

