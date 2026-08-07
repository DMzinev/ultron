"""
Ultron REST API — Analysis Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

from ultron.core.telemetry import PerformanceTimer, get_performance_summary, reset_performance_summary

def handle_v1_analyze(handler: Any) -> None:
    """POST /api/v1/analyze handler."""
    data = handler.get_request_data()
    if data is None:
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return

    repo_path = data.get("repo", ".")
    force = bool(data.get("force", False))

    if not repo_path:
        handler.send_json_response(400, None, "Repository path string must not be empty.")
        return

    norm_path = os.path.normpath(os.path.abspath(repo_path))
    if not os.path.exists(norm_path):
        handler.send_json_response(400, None, f"Repository path does not exist: '{repo_path}'")
        return

    reset_performance_summary()
    try:
        with PerformanceTimer("Filesystem Discovery & AST Parsing"):
            # Delegates cleanly to handler logic
            result = handler._execute_analysis_logic(norm_path, force)

        summary = get_performance_summary()
        result["performance_telemetry"] = summary

        handler.send_json_response(200, result)
    except Exception as err:
        sys.stderr.write(f"[Ultron Route Analysis Error] {err}\n")
        handler.send_json_response(500, None, f"Analysis failed: {err}")


def handle_v1_summary(handler: Any) -> None:
    """GET /api/v1/summary handler."""
    try:
        summary_data = handler._execute_summary_logic()
        handler.send_json_response(200, summary_data)
    except Exception as err:
        sys.stderr.write(f"[Ultron Route Summary Error] {err}\n")
        handler.send_json_response(500, None, f"Summary failed: {err}")
