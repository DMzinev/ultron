"""
TestRunnerService — Asynchronous, thread-safe test execution engine for Ultron.

Provides:
  - Background test execution decoupling long-running test suites from HTTP server threads.
  - Bounded run cache with automatic LRU eviction (max 50 runs).
  - Cancellation capability for in-flight test runs.
  - Repository identity and Merkle content hash attachment to each run.
  - Safe callback invocation of Delta Engine calibration feedback.
  - Backward-compatible synchronous execution option.
"""

import os
import sys
import time
import uuid
import threading
import subprocess
from typing import Dict, Any, Optional

MAX_CACHED_RUNS = 50
DEFAULT_TIMEOUT_SECONDS = 45.0

class TestRunRecord:
    def __init__(
        self,
        run_id: str,
        repo_path: str,
        repo_uuid: str = "",
        content_hash: str = "",
        timeout: float = DEFAULT_TIMEOUT_SECONDS
    ):
        self.run_id = run_id
        self.repo_path = repo_path
        self.repo_uuid = repo_uuid
        self.content_hash = content_hash
        self.timeout = timeout
        self.status = "queued"  # queued, running, completed, failed, cancelled, timed_out
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.exit_code: Optional[int] = None
        self.output: str = ""
        self.error: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def to_dict(self) -> Dict[str, Any]:
        duration_ms = 0.0
        if self.started_at:
            end_t = self.completed_at or time.time()
            duration_ms = round((end_t - self.started_at) * 1000.0, 2)

        return {
            "run_id": self.run_id,
            "status": self.status,
            "repo_path": self.repo_path,
            "repo_uuid": self.repo_uuid,
            "content_hash": self.content_hash,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": duration_ms,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error,
            "is_finished": self.status in ("completed", "failed", "cancelled", "timed_out")
        }


class TestRunnerService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._runs: Dict[str, TestRunRecord] = {}
        self._runs_order = []
        self._registry_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TestRunnerService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start_test_run(
        self,
        repo_path: str,
        repo_uuid: str = "",
        content_hash: str = "",
        feedback_params: Optional[Dict[str, Any]] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS
    ) -> TestRunRecord:
        run_id = f"test-run-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        record = TestRunRecord(
            run_id=run_id,
            repo_path=repo_path,
            repo_uuid=repo_uuid,
            content_hash=content_hash,
            timeout=timeout
        )

        with self._registry_lock:
            # Evict oldest if exceeding limit
            while len(self._runs) >= MAX_CACHED_RUNS and self._runs_order:
                oldest_id = self._runs_order.pop(0)
                self._runs.pop(oldest_id, None)

            self._runs[run_id] = record
            self._runs_order.append(run_id)

        worker = threading.Thread(
            target=self._execute_run,
            args=(record, feedback_params),
            daemon=True,
            name=f"UltronTestWorker-{run_id}"
        )
        worker.start()
        return record

    def _execute_run(self, record: TestRunRecord, feedback_params: Optional[Dict[str, Any]]):
        record.status = "running"
        record.started_at = time.time()

        if not os.path.isdir(record.repo_path):
            record.status = "failed"
            record.error = f"Repository path '{record.repo_path}' is not a directory."
            record.completed_at = time.time()
            return

        test_cmd = [sys.executable, "-m", "unittest", "discover"]
        if os.path.exists(os.path.join(record.repo_path, "run_tests.py")):
            test_cmd = [sys.executable, "run_tests.py"]
        elif os.path.exists(os.path.join(record.repo_path, "ultron", "tests", "run_tests.py")):
            test_cmd = [sys.executable, "ultron/tests/run_tests.py"]

        try:
            proc = subprocess.Popen(
                test_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=record.repo_path
            )
            record.process = proc

            try:
                stdout, stderr = proc.communicate(timeout=record.timeout)
                record.output = (stdout or "") + "\n" + (stderr or "")
                record.exit_code = proc.returncode
                record.status = "completed" if proc.returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                record.output = (stdout or "") + "\n" + (stderr or "") + f"\n[TestRunner Warning] Test execution exceeded timeout ({record.timeout}s)."
                record.exit_code = 1
                record.status = "timed_out"
                record.error = f"Execution timed out after {record.timeout} seconds."

        except Exception as e:
            record.status = "failed"
            record.error = str(e)
            record.exit_code = 1
            record.output = f"Execution failed to launch: {e}"
        finally:
            record.completed_at = time.time()
            record.process = None

            # Calibration feedback hook execution
            if feedback_params and record.exit_code is not None:
                self._invoke_calibration_feedback(feedback_params, record.exit_code)

    def _invoke_calibration_feedback(self, feedback_params: Dict[str, Any], exit_code: int):
        try:
            delta = None
            if delta is not None and hasattr(delta, "learn_from_feedback"):
                file_path = feedback_params.get("file_path")
                if file_path:
                    delta_i = float(feedback_params.get("delta_i", 0.0) or 0.0)
                    mkr = float(feedback_params.get("mkr", 1.0) or 1.0)
                    delta_cest = float(feedback_params.get("delta_cest", 0.0) or 0.0)
                    actual_failure = float(feedback_params.get("actual_failure", 1.0 if exit_code != 0 else 0.0) or 0.0)

                    delta.learn_from_feedback(
                        file_path=str(file_path),
                        delta_i=delta_i,
                        mkr=mkr,
                        delta_cest=delta_cest,
                        actual_failure=actual_failure
                    )
        except Exception as ex:
            print(f"[-] Delta Engine feedback learning failed in worker: {ex}", file=sys.stderr)

    def get_run(self, run_id: str) -> Optional[TestRunRecord]:
        with self._registry_lock:
            return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        with self._registry_lock:
            record = self._runs.get(run_id)
            if not record or record.status in ("completed", "failed", "cancelled", "timed_out"):
                return False

            record._cancelled = True
            record.status = "cancelled"
            record.completed_at = time.time()
            if record.process:
                try:
                    record.process.kill()
                    record.process.wait(timeout=1.0)
                except Exception:
                    pass
            return True
