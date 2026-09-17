"""Analyze, check, and scan command handlers."""

import sys
import json
import os
from typing import Optional

from ultron.interfaces.cli.commands.gate import extract_current_analysis
from ultron.interfaces.cli.formatting import (
    supports_color,
    format_scan_dashboard,
    safe_print,
)


def handle_analyze(args):
    path = getattr(args, "path", ".")
    print(f"Running analysis over path: {path}")


def handle_check(args):
    print("Running compliance check...")


def run_scan_command(
    repo_path: str = ".",
    json_output: bool = False,
    no_color: bool = False,
    force_color: Optional[bool] = None
) -> int:
    """
    Executes architectural scan over target repository.
    Emits clean machine-readable JSON if json_output is True.
    Emits rich ANSI terminal dashboard if interactive, or plain ASCII if no color.
    Returns 0 on success, 1 on failure.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    try:
        analysis = extract_current_analysis(abs_repo)
        payload = {
            "status": "success",
            "repo": analysis["repo"],
            "total_files": analysis["total_files"],
            "health_score": analysis["health_score"],
            "risks": analysis["risks"],
            "policy_violations": analysis["policy_violations"]
        }

        if json_output:
            safe_print(json.dumps(payload, indent=2))
            return 0

        # Determine color enablement
        resolved_force = False if no_color else force_color
        color_enabled = supports_color(sys.stdout, force_color=resolved_force)

        dashboard = format_scan_dashboard(analysis, color=color_enabled)
        safe_print(dashboard)
        return 0
    except Exception as e:
        if json_output:
            safe_print(json.dumps({"status": "error", "error": str(e)}))
        else:
            safe_print(f"[-] Scan failed: {e}", file=sys.stderr)
        return 1
