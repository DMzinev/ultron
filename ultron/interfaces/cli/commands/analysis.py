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
    workspace: Optional[str] = None,
    json_output: bool = False,
    no_color: bool = False,
    force_color: Optional[bool] = None
) -> int:
    """
    Executes architectural scan over target repository.
    Emits clean machine-readable JSON if json_output is True.
    Emits rich ANSI terminal dashboard if interactive, or plain ASCII if no color.
    Supports workspace filtering via workspace argument.
    Returns 0 on success, 1 on failure.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    try:
        from ultron.core.monorepo import (
            detect_workspaces,
            find_workspace,
            generate_monorepo_report,
            WorkspaceNotFoundError
        )

        # Fail-closed validation for workspace (Condition A.1)
        if workspace:
            ws_list = detect_workspaces(abs_repo)
            target_ws = find_workspace(ws_list, workspace)
            if not target_ws:
                available = ", ".join([w.name for w in ws_list]) if ws_list else "none detected"
                err_msg = f"Workspace '{workspace}' not found in repository. Available workspaces: {available}"
                if json_output:
                    safe_print(json.dumps({"status": "error", "error": err_msg}))
                else:
                    safe_print(f"[-] Scan failed: {err_msg}", file=sys.stderr)
                return 1

        analysis = extract_current_analysis(abs_repo, workspace=workspace)
        payload = {
            "status": "success",
            "repo": analysis["repo"],
            "total_files": analysis["total_files"],
            "health_score": analysis["health_score"],
            "risks": analysis["risks"],
            "policy_violations": analysis["policy_violations"]
        }

        if analysis.get("workspace"):
            payload["workspace"] = analysis["workspace"]
            payload["workspace_path"] = analysis.get("workspace_path")
        elif not workspace:
            monorepo_report = generate_monorepo_report(abs_repo)
            if monorepo_report.get("is_monorepo"):
                payload["monorepo"] = monorepo_report
                analysis["monorepo"] = monorepo_report

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
