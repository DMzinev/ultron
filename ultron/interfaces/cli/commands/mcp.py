"""
ultron.interfaces.cli.commands.mcp
CLI command runner for Ultron Model Context Protocol (MCP) stdio server
and 1-click IDE integration installer.
"""

import json
import os
import platform
import sys
from ultron.interfaces.mcp_server import run_mcp_server


def generate_mcp_config(repo_path: str) -> dict:
    """Generates MCP server configuration using sys.executable."""
    return {
        "command": sys.executable,
        "args": ["-m", "ultron.interfaces.mcp_server", "--repo", os.path.abspath(repo_path)]
    }


def _get_config_path(ide: str, repo_path: str) -> str:
    """Returns the IDE-specific MCP config file path."""
    if ide == "cursor":
        return os.path.join(os.path.abspath(repo_path), ".cursor", "mcp.json")
    elif ide == "claude":
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", "")
            return os.path.join(appdata, "Claude", "claude_desktop_config.json")
        elif platform.system() == "Darwin":
            return os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
        else:
            return os.path.expanduser("~/.config/Claude/claude_desktop_config.json")
    elif ide == "windsurf":
        return os.path.join(os.path.abspath(repo_path), ".windsurf", "mcp.json")
    elif ide == "vscode":
        return os.path.join(os.path.abspath(repo_path), ".vscode", "mcp.json")
    raise ValueError(f"Unsupported IDE: {ide}")


def install_mcp_config(ide: str, repo_path: str, output_json: bool = False) -> int:
    """Atomically merges Ultron MCP server into IDE config without clobbering existing servers."""
    config_path = _get_config_path(ide, repo_path)
    server_entry = generate_mcp_config(repo_path)

    # Read existing config (preserve other servers)
    existing = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    if not isinstance(existing, dict):
        existing = {}
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    # Merge (only overwrites the "ultron" key)
    existing["mcpServers"]["ultron"] = server_entry

    # Write atomically
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    if output_json:
        print(json.dumps({"success": True, "path": config_path, "config": existing}, indent=2))
    else:
        print(f"[Ultron] MCP configuration installed for {ide}: {config_path}")
    return 0


def run_mcp_command(args) -> int:
    """Runs the MCP JSON-RPC 2.0 stdio server loop or installs IDE config."""
    repo_path = getattr(args, "repo", None) or os.getcwd()

    if getattr(args, "install", False):
        ide = getattr(args, "ide", "cursor") or "cursor"
        output_json = getattr(args, "json", False)
        return install_mcp_config(ide, repo_path, output_json=output_json)

    return run_mcp_server(repo_path=repo_path)
