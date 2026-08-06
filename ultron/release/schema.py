import os
import sys
import platform
from datetime import datetime, timezone

def create_audit_context():
    """Generates reproducibility metadata for the release evidence contract."""
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.architecture()[0],
        "executed_by": os.getenv("USERNAME", "Ultron-Release-Engine"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

RELEASE_REPORT_SCHEMA = {
    "release_version": str,
    "timestamp": str,
    "audit_context": dict,
    "hard_freeze_active": bool,
    "test_suite": {
        "passed": bool,
        "tests_run": int,
        "failures": int,
        "total_duration_seconds": float
    },
    "frontend_syntax": {
        "passed": bool
    },
    "performance_benchmark": {
        "workload": str,
        "latency_seconds": float,
        "budget_seconds": float,
        "passed": bool
    },
    "overall_status": str,
    "ai_review": dict  # optional — present when AI Gateway is queried
}

def validate_report_schema(report_dict):
    """Validates that a release report dictionary conforms to the required contract keys."""
    required_keys = ["release_version", "timestamp", "audit_context", "hard_freeze_active", "test_suite", "frontend_syntax", "performance_benchmark", "overall_status"]
    for key in required_keys:
        if key not in report_dict:
            return False, f"Missing required root key '{key}' in release report."
    ai_review = report_dict.get("ai_review")
    if ai_review is not None:
        if not isinstance(ai_review, dict):
            return False, "'ai_review' must be a dict."
        for sub_key in ("status", "timestamp"):
            if sub_key not in ai_review:
                return False, f"'ai_review' missing required sub-key '{sub_key}'."
    return True, "Schema valid."
