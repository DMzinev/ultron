"""
Issue Memory — Institutional Memory & Regression Orchestration Engine.

Stores verified defect knowledge, root causes, machine-readable reproductions,
and deterministic fingerprints across the Three Pillars:
  - Functional Truth
  - Connectivity Truth
  - Human Reality

When a defect is resolved, it is placed under permanent REGRESSION_GUARD.
Subsequent analyses evaluate active failure signatures against this institutional
ledger; any fingerprint collision deterministically halts state progression with
REGRESSION_DETECTED.
"""

import os
import sys
import json
import time
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional

VALID_PILLARS = ("FUNCTIONAL", "CONNECTIVITY", "HUMAN")
VALID_STATUSES = ("DISCOVERED", "REPRODUCED", "FIXED", "REGRESSION_GUARD", "REOPENED")

@dataclass
class IssueRecord:
    issue_id: str
    pillar: str                          # FUNCTIONAL | CONNECTIVITY | HUMAN
    component: str                       # e.g., "server", "test_runner", "graph", "compiler"
    target: str                          # symbol, route, file, or DOM id
    failure_class: str                   # e.g., "THREAD_BLOCKING", "UNCLUSTERED_GRAPH", "MOCK_FALLBACK"
    symptom: str                         # Human-readable symptom
    reproduction: str                    # Concrete code snippet or steps to reproduce
    reproduction_signature: str = ""          # Normalized signature of the reproduction
    fingerprint: str = ""                     # Deterministic SHA-256 slice
    root_cause: str = ""                      # Technical root cause
    fix_summary: str = ""                # Summary of the fix
    regression_test: str = ""            # Test name guarding this issue
    status: str = "DISCOVERED"           # DISCOVERED, REPRODUCED, FIXED, REGRESSION_GUARD, REOPENED
    created_at: str = ""
    resolved_at: Optional[str] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if self.pillar not in VALID_PILLARS:
            self.pillar = "FUNCTIONAL"
        if not self.fingerprint:
            self.fingerprint = IssueMemory.compute_fingerprint(
                pillar=self.pillar,
                component=self.component,
                target=self.target,
                failure_class=self.failure_class,
                reproduction_signature=self.reproduction_signature
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssueRecord":
        valid_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class IssueMemory:
    """Manages persistent defect records and regression guards under .ultron/issues/."""

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self.issues_dir = os.path.join(self.repo_root, ".ultron", "issues")
        os.makedirs(self.issues_dir, exist_ok=True)

    @staticmethod
    def compute_fingerprint(
        pillar: str,
        component: str,
        target: str,
        failure_class: str,
        reproduction_signature: str
    ) -> str:
        """Computes a deterministic, collision-resistant fingerprint from semantic failure vectors."""
        norm_pillar = (pillar or "").strip().upper()
        norm_comp = (component or "").strip().lower()
        norm_target = (target or "").strip().replace("\\", "/").lower()
        if norm_target.startswith("./"):
            norm_target = norm_target[2:]
        norm_target = norm_target.strip("/")
        norm_fclass = (failure_class or "").strip().upper()
        norm_sig = (reproduction_signature or "").strip()

        seed = f"{norm_pillar}|{norm_comp}|{norm_target}|{norm_fclass}|{norm_sig}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def record_issue(self, record: IssueRecord) -> str:
        """Saves an issue record to disk."""
        if not record.fingerprint:
            record.fingerprint = self.compute_fingerprint(
                record.pillar,
                record.component,
                record.target,
                record.failure_class,
                record.reproduction_signature
            )
        file_path = os.path.join(self.issues_dir, f"{record.issue_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)
        return record.issue_id

    def get_issue(self, issue_id: str) -> Optional[IssueRecord]:
        """Retrieves a single issue record by ID."""
        file_path = os.path.join(self.issues_dir, f"{issue_id}.json")
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return IssueRecord.from_dict(data)
        except Exception:
            return None

    def list_issues(self, status: Optional[str] = None, pillar: Optional[str] = None) -> List[IssueRecord]:
        """Lists all issue records, optionally filtered by status or pillar."""
        records = []
        if not os.path.exists(self.issues_dir):
            return records

        for fname in sorted(os.listdir(self.issues_dir)):
            if fname.endswith(".json"):
                issue = self.get_issue(fname[:-5])
                if issue:
                    if status and issue.status != status:
                        continue
                    if pillar and issue.pillar != pillar:
                        continue
                    records.append(issue)
        return records

    @staticmethod
    def generate_adaptive_mutations(base_target: str) -> List[str]:
        """
        Mahoraga adaptive parameter expansion:
        Generates boundary variations from a real failure target path to verify regression resistance:
        - leading/trailing whitespace
        - backslashes vs forward slashes
        - uppercase/lowercase
        - relative prefix (./)
        - redundant slashes
        """
        norm = (base_target or "").strip().replace("\\", "/")
        return [
            base_target,
            f" {base_target} ",
            base_target.replace("/", "\\"),
            f"./{norm}",
            norm.upper(),
            norm.lower(),
            norm.replace("/", "//"),
            f" {norm} "
        ]

    def check_for_regression(
        self,
        pillar: str,
        component: str,
        target: str,
        failure_class: str,
        reproduction_signature: str,
        attempt_data: Optional[Dict[str, Any]] = None
    ) -> Optional[IssueRecord]:
        """
        Checks if an active failure matches a previously resolved issue or regression guard.
        Uses Mahoraga adaptive parameter expansion to ensure immunity against slash, case, or whitespace mutations.
        If a match is found, marks status as REOPENED, records attempt evidence, and returns the historical record.
        """
        # Test active target plus adaptive boundary variations
        candidate_fps = set()
        for cand_target in self.generate_adaptive_mutations(target):
            candidate_fps.add(
                self.compute_fingerprint(
                    pillar=pillar,
                    component=component,
                    target=cand_target,
                    failure_class=failure_class,
                    reproduction_signature=reproduction_signature
                )
            )

        for issue in self.list_issues():
            fp_match = bool(issue.fingerprint and issue.fingerprint in candidate_fps)
            sig_match = bool(reproduction_signature and issue.reproduction_signature == reproduction_signature)
            if (fp_match or sig_match) and issue.status in ("FIXED", "REGRESSION_GUARD"):
                # Regression detected! Reopen historical record
                issue.status = "REOPENED"
                if attempt_data:
                    issue.attempts.append(attempt_data)
                self.record_issue(issue)
                return issue
        return None

    def mark_resolved(
        self,
        issue_id: str,
        fix_summary: str,
        regression_test: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[IssueRecord]:
        """Transitions an issue from DISCOVERED/REPRODUCED to REGRESSION_GUARD."""
        issue = self.get_issue(issue_id)
        if not issue:
            return None

        issue.status = "REGRESSION_GUARD"
        issue.fix_summary = fix_summary
        issue.regression_test = regression_test
        issue.resolved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if checkpoint_id and checkpoint_id not in issue.checkpoints:
            issue.checkpoints.append(checkpoint_id)
        self.record_issue(issue)
        return issue

    def get_summary(self) -> Dict[str, Any]:
        """Generates an institutional memory summary."""
        all_issues = self.list_issues()
        by_pillar = {"FUNCTIONAL": 0, "CONNECTIVITY": 0, "HUMAN": 0}
        by_status = {}

        for iss in all_issues:
            by_pillar[iss.pillar] = by_pillar.get(iss.pillar, 0) + 1
            by_status[iss.status] = by_status.get(iss.status, 0) + 1

        return {
            "total_issues": len(all_issues),
            "by_pillar": by_pillar,
            "by_status": by_status,
            "regression_guards_active": by_status.get("REGRESSION_GUARD", 0),
            "reopened_regressions": by_status.get("REOPENED", 0)
        }
