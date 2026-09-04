"""
ultron.tests.test_snapshot_drift_engine
Unit test suite asserting architecture snapshot capture and structural drift vectors.
"""

import unittest
from ultron.core.snapshot_drift_engine import SnapshotDriftEngine, norm_path


class TestSnapshotDriftEngine(unittest.TestCase):
    """Unit tests for deterministic SnapshotDriftEngine."""

    def test_norm_path(self):
        """Asserts path normalization to POSIX format."""
        self.assertEqual(norm_path("ultron\\core\\analyzer.py"), "ultron/core/analyzer.py")
        self.assertEqual(norm_path(None), "")

    def test_create_snapshot_and_structure(self):
        """Asserts creating a snapshot produces consistent fields and aggregate metrics."""
        engine = SnapshotDriftEngine()
        data = {
            "risks": [
                {"file": "controller.py", "complexity": 4.0, "coupling_score": 2.0},
                {"file": "service.py", "complexity": 8.0, "coupling_score": 4.0}
            ],
            "modularity": {
                "health_score": 85.0,
                "mean_instability": 0.45
            }
        }
        snap = engine.create_snapshot(data, label="Initial Scan", custom_timestamp="2026-08-14T10:00:00Z")
        self.assertEqual(snap["label"], "Initial Scan")
        self.assertEqual(snap["total_modules"], 2)
        self.assertEqual(snap["mean_complexity"], 6.0)
        self.assertEqual(snap["mean_coupling"], 3.0)
        self.assertEqual(snap["health_score"], 85.0)

    def test_calculate_drift_improved(self):
        """Asserts drift calculation correctly detects architectural improvements."""
        engine = SnapshotDriftEngine()
        snap1 = {
            "snapshot_id": "snap_1",
            "health_score": 75.0,
            "mean_complexity": 8.0,
            "mean_coupling": 4.0,
            "total_modules": 10
        }
        snap2 = {
            "snapshot_id": "snap_2",
            "health_score": 88.0,
            "mean_complexity": 5.0,
            "mean_coupling": 2.5,
            "total_modules": 12
        }
        drift = engine.calculate_drift(snap1, snap2)
        self.assertEqual(drift["delta_health"], 13.0)
        self.assertEqual(drift["delta_complexity"], -3.0)
        self.assertEqual(drift["delta_coupling"], -1.5)
        self.assertEqual(drift["delta_modules"], 2)
        self.assertEqual(drift["drift_direction"], "IMPROVED")

    def test_calculate_drift_degraded(self):
        """Asserts drift calculation correctly detects architectural degradation."""
        engine = SnapshotDriftEngine()
        snap1 = {
            "snapshot_id": "snap_1",
            "health_score": 90.0,
            "mean_complexity": 4.0,
            "mean_coupling": 1.5,
            "total_modules": 10
        }
        snap2 = {
            "snapshot_id": "snap_2",
            "health_score": 68.0,
            "mean_complexity": 9.5,
            "mean_coupling": 5.0,
            "total_modules": 15
        }
        drift = engine.calculate_drift(snap1, snap2)
        self.assertEqual(drift["delta_health"], -22.0)
        self.assertEqual(drift["delta_complexity"], 5.5)
        self.assertEqual(drift["drift_direction"], "DEGRADED")

    def test_calculate_drift_identical_snapshots(self):
        """Asserts drift between identical snapshots is zero."""
        engine = SnapshotDriftEngine()
        snap = {
            "snapshot_id": "snap_1",
            "health_score": 85.0,
            "mean_complexity": 5.0,
            "mean_coupling": 2.0,
            "total_modules": 10
        }
        drift = engine.calculate_drift(snap, snap)
        self.assertEqual(drift["delta_health"], 0.0)
        self.assertEqual(drift["delta_complexity"], 0.0)
        self.assertEqual(drift["drift_velocity_pct"], 0.0)
        self.assertEqual(drift["drift_direction"], "STABLE")

    def test_list_snapshots_chronological_ordering(self):
        """Asserts snapshots are sorted strictly chronologically."""
        engine = SnapshotDriftEngine()
        engine.create_snapshot({}, label="Second", custom_timestamp="2026-08-14T12:00:00Z")
        engine.create_snapshot({}, label="First", custom_timestamp="2026-08-14T10:00:00Z")
        engine.create_snapshot({}, label="Third", custom_timestamp="2026-08-14T15:00:00Z")

        snaps = engine.list_snapshots()
        self.assertEqual(len(snaps), 3)
        self.assertEqual(snaps[0]["label"], "First")
        self.assertEqual(snaps[1]["label"], "Second")
        self.assertEqual(snaps[2]["label"], "Third")


if __name__ == "__main__":
    unittest.main()
