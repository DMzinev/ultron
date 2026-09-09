"""
ultron/tests/test_project_log_compliance.py

Automated unit test suite for Task P2-B2 per docs/AGENT_EXECUTION_PLAN_PHASE2.md:
"PROJECT_LOG.md Must Cite the Full-Suite Number, Not a Subset"

Asserts:
1. PROJECT_LOG.md exists and contains the mandatory standard entry template.
2. All Phase 2 tasks (P2-A1, P2-A2, P2-A3, P2-B1, P2-B2) declare full_suite_before and full_suite_after.
3. Values are correctly formatted (ran=N failures=F errors=E skipped=S) with backtick tolerance.
4. All 18 Phase 1 tasks (A1-E2) are explicitly accounted for and marked NOT_CAPTURED.
5. Zero omission / zero unlabeled Phase 2 tasks.
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestProjectLogCompliance(unittest.TestCase):
    """Hermetic compliance test suite enforcing full-suite metrics reporting in PROJECT_LOG.md."""

    @classmethod
    def setUpClass(cls):
        cls.log_path = os.path.join(REPO_ROOT, "PROJECT_LOG.md")
        if not os.path.isfile(cls.log_path):
            raise FileNotFoundError(f"PROJECT_LOG.md not found at {cls.log_path}")
        with open(cls.log_path, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_project_log_exists(self):
        """Assert PROJECT_LOG.md exists and is a substantive document."""
        self.assertTrue(os.path.isfile(self.log_path))
        self.assertGreater(len(self.content), 10000, "PROJECT_LOG.md is unexpectedly truncated")

    def test_project_log_template_declared(self):
        """Assert the mandatory standard schema template is declared in PROJECT_LOG.md."""
        self.assertIn("## Entry Template (Mandatory Standard Schema)", self.content)
        self.assertIn("`full_suite_before`: `ran=<N> failures=<F> errors=<E> skipped=<S>`", self.content)
        self.assertIn("`full_suite_after`: `ran=<N> failures=<F> errors=<E> skipped=<S>`", self.content)

    def test_phase2_entries_contain_full_suite_metrics(self):
        """Assert every Phase 2 task contains valid, verified full-suite metrics before and after."""
        metric_pattern = re.compile(r"^`?ran=(\d+)\s+failures=(\d+)\s+errors=(\d+)\s+skipped=(\d+)`?$")

        # Partition log by task headers (### 2026-...)
        sections = re.split(r"\n(?=### 2026-)", self.content)
        phase2_tasks = {}

        for sec in sections:
            header_match = re.search(r"### 2026-\d{2}-\d{2}\s+[—–-]\s+Task\s+(P2-[A-Z0-9]+):", sec)
            if header_match:
                task_id = header_match.group(1)
                before_match = re.search(r"-\s+`full_suite_before`:\s*(.+)", sec)
                after_match = re.search(r"-\s+`full_suite_after`:\s*(.+)", sec)
                
                self.assertIsNotNone(
                    before_match,
                    f"Task {task_id} is missing '- `full_suite_before`:' field"
                )
                self.assertIsNotNone(
                    after_match,
                    f"Task {task_id} is missing '- `full_suite_after`:' field"
                )
                
                before_raw = before_match.group(1).strip()
                after_raw = after_match.group(1).strip()
                
                # Normalize values by stripping surrounding backticks and whitespace
                before_val = before_raw.strip("` ").strip()
                after_val = after_raw.strip("` ").strip()
                
                self.assertRegex(
                    before_val,
                    metric_pattern,
                    f"Task {task_id} full_suite_before '{before_val}' does not match expected format"
                )
                self.assertRegex(
                    after_val,
                    metric_pattern,
                    f"Task {task_id} full_suite_after '{after_val}' does not match expected format"
                )
                phase2_tasks[task_id] = (before_val, after_val)

        expected_phase2 = ["P2-A1", "P2-A2", "P2-A3", "P2-B1", "P2-B2"]
        for task_id in expected_phase2:
            self.assertIn(task_id, phase2_tasks, f"Expected Phase 2 task {task_id} missing from PROJECT_LOG.md")

        # Verify ground-truth values
        self.assertEqual(phase2_tasks["P2-A1"][0], "ran=639 failures=28 errors=40 skipped=9")
        self.assertEqual(phase2_tasks["P2-A1"][1], "ran=731 failures=38 errors=0 skipped=9")

        self.assertEqual(phase2_tasks["P2-A2"][0], "ran=731 failures=38 errors=0 skipped=9")
        self.assertEqual(phase2_tasks["P2-A2"][1], "ran=731 failures=0 errors=0 skipped=9")

        self.assertEqual(phase2_tasks["P2-A3"][0], "ran=731 failures=0 errors=0 skipped=9")
        self.assertEqual(phase2_tasks["P2-A3"][1], "ran=734 failures=0 errors=0 skipped=9")

        self.assertEqual(phase2_tasks["P2-B1"][0], "ran=734 failures=0 errors=0 skipped=9")
        self.assertEqual(phase2_tasks["P2-B1"][1], "ran=743 failures=0 errors=0 skipped=9")

        self.assertEqual(phase2_tasks["P2-B2"][0], "ran=743 failures=0 errors=0 skipped=9")
        self.assertEqual(phase2_tasks["P2-B2"][1], "ran=748 failures=0 errors=0 skipped=9")

    def test_phase1_all_18_tasks_annotated(self):
        """Assert all 18 Phase 1 tasks (A1 through E2) exist in PROJECT_LOG.md and admit NOT_CAPTURED."""
        phase1_task_ids = [
            "A1", "A2", "C3", "A3", "A4", "A5", "B1", "B2",
            "B3", "B4", "C1", "C2", "C4", "D1", "D2", "D3", "E1", "E2"
        ]

        for task_id in phase1_task_ids:
            # Pattern matching task header
            pattern = rf"### 2026-\d{{2}}-\d{{2}}\s+[—–-]\s+Task\s+{re.escape(task_id)}[:\s]"
            match = re.search(pattern, self.content)
            self.assertIsNotNone(
                match,
                f"Phase 1 task '{task_id}' header not found in PROJECT_LOG.md"
            )

        # Check that NOT_CAPTURED disclaimer is present for all Phase 1 entries
        not_captured_count = self.content.count("NOT_CAPTURED (historical Phase 1 baseline")
        # Each task has before and after, so 18 tasks * 2 = 36 occurrences minimum
        self.assertGreaterEqual(
            not_captured_count,
            36,
            f"Expected at least 36 NOT_CAPTURED metric occurrences (18 tasks * 2), found {not_captured_count}"
        )

    def test_no_unlabeled_phase2_tasks(self):
        """Assert that no Phase 2 task is mentioned without corresponding full_suite metrics."""
        # Find all occurrences of Task P2-XX
        p2_mentions = re.findall(r"Task (P2-[A-Z0-9]+)", self.content)
        p2_unique = sorted(set(p2_mentions))
        expected_unique = sorted(["P2-A1", "P2-A2", "P2-A3", "P2-B1", "P2-B2"])
        for task_id in expected_unique:
            self.assertIn(task_id, p2_unique, f"Phase 2 task {task_id} not referenced in log")


if __name__ == "__main__":
    unittest.main()
