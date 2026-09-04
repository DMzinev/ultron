import os
import unittest
import tempfile

from ultron.core.work_queue import WorkQueue, WorkState, InvalidStateTransitionError

class TestWorkQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue = WorkQueue(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_state_is_idle(self):
        st = self.queue.get_state()
        self.assertEqual(st.status, "IDLE")
        self.assertIn("DISCOVERING", st.admissible_next_states)

    def test_valid_transitions_progress_normally(self):
        s1 = self.queue.transition_to("DISCOVERING")
        self.assertEqual(s1.status, "DISCOVERING")

        s2 = self.queue.transition_to("ISSUE_SELECTED", context={"active_issue": "BUG-01"})
        self.assertEqual(s2.status, "ISSUE_SELECTED")
        self.assertEqual(s2.active_issue, "BUG-01")

        s3 = self.queue.transition_to("MISSION_READY", context={"mission_id": "MIS-01"})
        self.assertEqual(s3.status, "MISSION_READY")

    def test_illegal_transition_raises_error(self):
        # Cannot jump from IDLE to CHECKPOINT_READY directly
        with self.assertRaises(InvalidStateTransitionError):
            self.queue.transition_to("CHECKPOINT_READY")

    def test_verifying_to_repair_required_branch(self):
        self.queue.transition_to("DISCOVERING")
        self.queue.transition_to("ISSUE_SELECTED")
        self.queue.transition_to("MISSION_READY")
        self.queue.transition_to("IMPLEMENTING")
        self.queue.transition_to("OBSERVING")
        self.queue.transition_to("VERIFYING")

        # Failure branches to REPAIR_REQUIRED
        s_fail = self.queue.transition_to("REPAIR_REQUIRED", context={"blocking_reasons": ["Test failed"]})
        self.assertEqual(s_fail.status, "REPAIR_REQUIRED")
        self.assertEqual(s_fail.blocking_reasons, ["Test failed"])

    def test_verifying_to_checkpoint_ready_branch(self):
        self.queue.transition_to("DISCOVERING")
        self.queue.transition_to("ISSUE_SELECTED")
        self.queue.transition_to("MISSION_READY")
        self.queue.transition_to("IMPLEMENTING")
        self.queue.transition_to("OBSERVING")
        self.queue.transition_to("VERIFYING")

        s_ready = self.queue.transition_to("CHECKPOINT_READY")
        self.assertEqual(s_ready.status, "CHECKPOINT_READY")
        s_chk = self.queue.transition_to("CHECKPOINTED", context={"checkpoint_id": "CHK-100"})
        self.assertEqual(s_chk.status, "CHECKPOINTED")

if __name__ == "__main__":
    unittest.main()
