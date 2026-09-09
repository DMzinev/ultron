import os
import sys
import time
import unittest
from ultron.core.test_runner_service import TestRunnerService, TestRunRecord

class TestAsyncTestRunner(unittest.TestCase):
    def setUp(self):
        self.service = TestRunnerService.get_instance()
        self.repo_root = os.path.abspath(".")

    def test_start_test_run_and_poll_status(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_sample.py")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("import unittest\nclass FastTest(unittest.TestCase):\n    def test_ok(self):\n        pass\n")

            record = self.service.start_test_run(
                repo_path=tmpdir,
                repo_uuid="test-uuid",
                content_hash="test-hash",
                timeout=10.0
            )
            self.assertIsNotNone(record.run_id)

            start = time.time()
            while not record.to_dict()["is_finished"] and (time.time() - start) < 10.0:
                time.sleep(0.1)

            data = record.to_dict()
            self.assertTrue(data["is_finished"])
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["exit_code"], 0)
            self.assertIn("OK", data["output"])

    def test_run_cancellation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            record = self.service.start_test_run(
                repo_path=tmpdir,
                timeout=30.0
            )
            # Cancel immediately
            cancelled = self.service.cancel_run(record.run_id)
            # It's either cancelled or already finished if extremely fast
            data = record.to_dict()
            self.assertTrue(data["is_finished"])

    def test_invalid_directory_handling(self):
        record = self.service.start_test_run(
            repo_path="C:/non_existent_folder_path_xyz_123",
            timeout=5.0
        )
        start = time.time()
        while not record.to_dict()["is_finished"] and (time.time() - start) < 5.0:
            time.sleep(0.1)

        data = record.to_dict()
        self.assertEqual(data["status"], "failed")
        self.assertIn("not a directory", data["error"])

    def test_lru_cache_eviction(self):
        service = TestRunnerService()
        for i in range(55):
            service.start_test_run(repo_path="invalid_path", timeout=1.0)
        # Verify capped at 50
        with service._registry_lock:
            self.assertLessEqual(len(service._runs), 50)

if __name__ == "__main__":
    unittest.main()
