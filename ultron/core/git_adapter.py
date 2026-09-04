"""
Ultron Core — Dedicated Git History Evidence Adapter
Campaign 38 / v2.5 — Evidence Adapter Separation & Non-Git Boundary Safety
"""

import sys
import os
import subprocess
import logging
from typing import Dict, List, Any, Optional

from ultron.core.system_model import EvidenceObject

logger = logging.getLogger(__name__)
_EMITTED_NO_GIT_REPO = False


class GitEvidenceAdapter:
    """
    Dedicated Evidence Adapter for Repository Git History.
    Extracts commit counts, bug fixes, and churn metrics into immutable EvidenceObject records.
    """

    def parse_git_history(self, repo_path: str) -> List[EvidenceObject]:
        """
        Parses git commit log statistics for files under repo_path.
        Returns a list of EvidenceObject records of type 'GIT_HISTORY'.
        Safely returns empty list on non-git repositories or missing git CLI.
        """
        abs_repo = os.path.abspath(repo_path)
        git_dir = os.path.join(abs_repo, ".git")

        if not os.path.exists(git_dir):
            global _EMITTED_NO_GIT_REPO
            if not _EMITTED_NO_GIT_REPO:
                logger.info("[GitEvidenceAdapter Notice] Path '%s' is not a git repository. Skipping git history.", repo_path)
                _EMITTED_NO_GIT_REPO = True
            return []

        evidence_list: List[EvidenceObject] = []

        try:
            cmd = ["git", "log", "--name-only", "--pretty=format:COMMIT:%H|%s"]
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
                return []

            file_commits: Dict[str, int] = {}
            file_bug_fixes: Dict[str, int] = {}

            current_commit_msg = ""
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("COMMIT:"):
                    current_commit_msg = line.split("|", 1)[1] if "|" in line else ""
                else:
                    norm_path = os.path.normpath(line).replace("\\", "/")
                    if norm_path.endswith(".py"):
                        file_commits[norm_path] = file_commits.get(norm_path, 0) + 1
                        is_fix = any(w in current_commit_msg.lower() for w in ("fix", "bug", "patch", "repair", "issue"))
                        if is_fix:
                            file_bug_fixes[norm_path] = file_bug_fixes.get(norm_path, 0) + 1

            for rel_path, commits in sorted(file_commits.items()):
                bug_fixes = file_bug_fixes.get(rel_path, 0)
                node_id = f"module:{rel_path}"
                ev = EvidenceObject(
                    id=f"ev-git-{rel_path.replace('/', '_')}",
                    type="GIT_HISTORY",
                    subject_id=node_id,
                    measurement={"commits": commits, "bug_fixes": bug_fixes},
                    source={"adapter": "git", "file": rel_path}
                )
                evidence_list.append(ev)

        except (subprocess.SubprocessError, FileNotFoundError, OSError) as err:
            logger.warning("[GitEvidenceAdapter Error] Could not extract git history: %s", err)
            return []

        return evidence_list
