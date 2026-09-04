"""
ultron.core.snapshot_drift_engine
Deterministic Historical Architecture Snapshot Time-Travel & Drift Analysis Engine.
"""

import time
import hashlib
from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class SnapshotDriftEngine:
    """
    Deterministic engine for recording immutable codebase architecture snapshots,
    querying historical time-series states, and computing structural drift vectors.
    """

    ENGINE_VERSION = "1.0-snapshot-drift"

    def __init__(self, initial_snapshots: Optional[List[Dict[str, Any]]] = None):
        self._snapshots: List[Dict[str, Any]] = []
        if initial_snapshots:
            for s in initial_snapshots:
                self._snapshots.append(s)

    def _generate_snapshot_id(self, timestamp_iso: str, data: Dict[str, Any]) -> str:
        """Generates deterministic snapshot ID from timestamp and payload hash."""
        raw = f"{timestamp_iso}_{data.get('total_modules', 0)}_{data.get('health_score', 100.0)}"
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        ts_clean = timestamp_iso.replace(":", "").replace("-", "").replace("T", "_")[:15]
        return f"snap_{ts_clean}_{h}"

    def create_snapshot(
        self,
        analysis_data: Dict[str, Any],
        label: Optional[str] = None,
        custom_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Captures an immutable snapshot from scan results.
        Computes summary metrics and registers snapshot in historical sequence.
        """
        analysis_data = analysis_data or {}
        risks = analysis_data.get("risks", []) or []
        modularity = analysis_data.get("modularity", {}) or {}

        timestamp_iso = custom_timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        total_modules = len(risks) if risks else int(analysis_data.get("total_modules", 0))

        # Compute aggregate metrics
        total_complexity = sum(float(r.get("complexity", 1.0) or 1.0) for r in risks)
        total_coupling = sum(float(r.get("coupling_score", 0.0) or 0.0) for r in risks)

        mean_complexity = round(total_complexity / max(1, total_modules), 2) if total_modules > 0 else 1.0
        mean_coupling = round(total_coupling / max(1, total_modules), 2) if total_modules > 0 else 0.0

        health_score = float(modularity.get("health_score", analysis_data.get("health_score", 100.0)) or 100.0)
        mean_instability = float(modularity.get("mean_instability", analysis_data.get("mean_instability", 0.0)) or 0.0)

        snap_id = self._generate_snapshot_id(timestamp_iso, analysis_data)
        snap_label = label or f"Scan Snapshot #{len(self._snapshots) + 1}"

        snapshot_record = {
            "snapshot_id": snap_id,
            "timestamp": timestamp_iso,
            "label": snap_label,
            "total_modules": total_modules,
            "health_score": round(health_score, 1),
            "mean_complexity": mean_complexity,
            "mean_coupling": mean_coupling,
            "mean_instability": round(mean_instability, 2),
            "zone_distribution": modularity.get("zone_distribution", {
                "main_sequence": max(0, total_modules - 1),
                "zone_of_pain": min(1, total_modules),
                "zone_of_uselessness": 0
            }),
            "version": self.ENGINE_VERSION
        }

        self._snapshots.append(snapshot_record)
        # Keep sorted chronologically by timestamp
        self._snapshots.sort(key=lambda x: (x["timestamp"], x["snapshot_id"]))

        return snapshot_record

    def calculate_drift(
        self,
        base_snapshot: Dict[str, Any],
        target_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates deterministic structural drift vectors between two historical snapshots.
        """
        if not base_snapshot or not target_snapshot:
            return {
                "delta_health": 0.0,
                "delta_complexity": 0.0,
                "delta_coupling": 0.0,
                "delta_modules": 0,
                "drift_velocity_pct": 0.0,
                "drift_direction": "STABLE",
                "direction_class": "low"
            }

        base_health = float(base_snapshot.get("health_score", 100.0) or 100.0)
        target_health = float(target_snapshot.get("health_score", 100.0) or 100.0)
        delta_health = round(target_health - base_health, 2)

        base_c = float(base_snapshot.get("mean_complexity", 1.0) or 1.0)
        target_c = float(target_snapshot.get("mean_complexity", 1.0) or 1.0)
        delta_c = round(target_c - base_c, 2)

        base_k = float(base_snapshot.get("mean_coupling", 0.0) or 0.0)
        target_k = float(target_snapshot.get("mean_coupling", 0.0) or 0.0)
        delta_k = round(target_k - base_k, 2)

        delta_mods = int(target_snapshot.get("total_modules", 0)) - int(base_snapshot.get("total_modules", 0))

        # Drift Velocity formula: (|delta_C| + |delta_K|) / max(1.0, base_C) * 100%
        drift_velocity = round(((abs(delta_c) + abs(delta_k)) / max(1.0, base_c)) * 100.0, 1)

        if delta_health > 0.0 and delta_c <= 0.0:
            drift_dir = "IMPROVED"
            dir_class = "low"
        elif delta_health < 0.0 or delta_c > 1.0:
            drift_dir = "DEGRADED"
            dir_class = "high"
        else:
            drift_dir = "STABLE"
            dir_class = "med"

        return {
            "base_snapshot_id": base_snapshot.get("snapshot_id"),
            "target_snapshot_id": target_snapshot.get("snapshot_id"),
            "delta_health": delta_health,
            "delta_complexity": delta_c,
            "delta_coupling": delta_k,
            "delta_modules": delta_mods,
            "drift_velocity_pct": drift_velocity,
            "drift_direction": drift_dir,
            "direction_class": dir_class
        }

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Returns chronological list of recorded snapshots."""
        return list(self._snapshots)

    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Fetches individual snapshot by ID."""
        for s in self._snapshots:
            if s.get("snapshot_id") == snapshot_id:
                return s
        return None
