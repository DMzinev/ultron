"""
Unit Test Suite for Hardened Ultron ObjectiveTracker Engine
"""

import os
import json
import shutil
import tempfile
import unittest

from ultron.core.objective_tracker import ObjectiveTracker


class TestHardenedObjectiveTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ultron_hardened_obj_")
        self.tracker = ObjectiveTracker(repo_path=self.temp_dir)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_repository_identity_binding(self):
        state = self.tracker.get_objective()
        self.assertIn("repository_id", state)
        self.assertIn("repository_root", state)
        self.assertIn("objective_id", state)
        self.assertEqual(state["repository_root"], os.path.normcase(os.path.abspath(self.temp_dir)))
        self.assertEqual(len(state["repository_id"]), 16)

    def test_set_and_load_objective(self):
        res = self.tracker.set_objective(
            title="Implement User Billing",
            description="Add stripe invoices and webhook listener",
            tasks=[
                {"title": "Add stripe API client", "description": "Wrapper module", "status": "done"},
                {"title": "Add webhook receiver", "description": "POST endpoint", "status": "in_progress"},
                {"title": "Write unit tests", "description": "Test callback", "status": "pending"}
            ],
            constraints=["Do not modify auth module", "Preserve API signatures"],
            acceptance=["100% test pass rate", "Zero regressions"],
            affected_areas=["billing/", "api/routes/"]
        )
        self.assertEqual(res["title"], "Implement User Billing")
        self.assertEqual(len(res["tasks"]), 3)
        self.assertEqual(res["progress_pct"], 33.3)
        self.assertEqual(res["status"], "in_progress")

        # Reload from fresh tracker instance
        reloaded = ObjectiveTracker(repo_path=self.temp_dir).get_objective()
        self.assertEqual(reloaded["title"], "Implement User Billing")
        self.assertEqual(reloaded["repository_id"], self.tracker.repo_id)
        self.assertEqual(reloaded["progress_pct"], 33.3)
        self.assertEqual(len(reloaded["constraints"]), 2)

    def test_atomic_persistence(self):
        """Ensures that saving creates and renames the file atomically."""
        self.tracker.add_task(title="Atomic task test", description="Testing write safety")
        target_file = os.path.join(self.temp_dir, ".ultron", "objective.json")
        self.assertTrue(os.path.exists(target_file))
        # Temp file should not remain after successful replace
        tmp_file = os.path.join(self.temp_dir, ".ultron", "objective.json.tmp")
        self.assertFalse(os.path.exists(tmp_file))

    def test_task_completion_and_auto_promotion(self):
        self.tracker.set_objective(
            title="Deploy Authentication Service",
            tasks=[
                {"id": "t1", "title": "Setup JWT provider", "status": "in_progress"},
                {"id": "t2", "title": "Add login route", "status": "pending"},
                {"id": "t3", "title": "Add frontend modal", "status": "pending"}
            ]
        )
        # Complete task 1
        comp_res = self.tracker.complete_task("t1")
        self.assertTrue(comp_res["success"])
        state = comp_res["state"]
        self.assertEqual(state["tasks"][0]["status"], "done")
        self.assertEqual(state["tasks"][1]["status"], "in_progress")
        self.assertEqual(state["tasks"][2]["status"], "pending")
        self.assertEqual(state["progress_pct"], 33.3)

        # Complete task 2
        comp_res2 = self.tracker.complete_task("t2")
        self.assertTrue(comp_res2["success"])
        state2 = comp_res2["state"]
        self.assertEqual(state2["tasks"][1]["status"], "done")
        self.assertEqual(state2["tasks"][2]["status"], "in_progress")
        self.assertEqual(state2["progress_pct"], 66.7)

        # Complete final task
        comp_res3 = self.tracker.complete_task("t3")
        self.assertTrue(comp_res3["success"])
        state3 = comp_res3["state"]
        self.assertEqual(state3["progress_pct"], 100.0)
        self.assertEqual(state3["status"], "done")

    def test_corrupted_json_recovery(self):
        storage_file = os.path.join(self.temp_dir, ".ultron", "objective.json")
        os.makedirs(os.path.dirname(storage_file), exist_ok=True)
        with open(storage_file, "w", encoding="utf-8") as f:
            f.write("{ invalid corrupted JSON %%### ")

        recovered = self.tracker.get_objective()
        self.assertIn("title", recovered)
        self.assertEqual(recovered["repository_id"], self.tracker.repo_id)
        self.assertIsInstance(recovered["tasks"], list)

    def test_unknown_task_id_handling(self):
        res = self.tracker.complete_task("unknown_task_999")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_empty_tasks_progress_math(self):
        res = self.tracker.set_objective(title="Empty Objective", tasks=[])
        self.assertEqual(res["progress_pct"], 0.0)
        self.assertEqual(len(res["tasks"]), 0)


if __name__ == "__main__":
    unittest.main()
