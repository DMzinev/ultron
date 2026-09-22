"""
ultron.interfaces.cli.commands.mcp
CLI command runner for Ultron Model Context Protocol (MCP) stdio server
and automated multi-client IDE integration installer.
"""

from datetime import datetime
import json
import os
import platform
import shutil
import sys
from ultron.interfaces.mcp_server import run_mcp_server


def generate_mcp_config(repo_path: str) -> dict:
    """Generates MCP server configuration using sys.executable."""
    return {
        "command": sys.executable,
        "args": ["-m", "ultron.interfaces.mcp_server", "--repo", os.path.abspath(repo_path)]
    }


def _get_config_path(ide: str, repo_path: str, is_global: bool = False) -> str:
    """Returns the client-specific MCP config file path across platforms."""
    client = ide.lower()
    abs_repo = os.path.abspath(repo_path)

    if client == "cursor":
        if is_global:
            return os.path.normpath(os.path.expanduser(os.path.join("~", ".cursor", "mcp.json")))
        return os.path.normpath(os.path.join(abs_repo, ".cursor", "mcp.json"))

    elif client == "windsurf":
        if is_global:
            return os.path.normpath(os.path.expanduser(os.path.join("~", ".codeium", "windsurf", "mcp_config.json")))
        return os.path.normpath(os.path.join(abs_repo, ".windsurf", "mcp.json"))

    elif client == "vscode":
        if is_global:
            return os.path.normpath(os.path.expanduser(os.path.join("~", ".vscode", "mcp.json")))
        return os.path.normpath(os.path.join(abs_repo, ".vscode", "mcp.json"))

    elif client == "claude":
        # Claude Desktop is always a global user-level application config
        sys_plat = platform.system()
        if sys_plat == "Windows":
            appdata = os.environ.get("APPDATA") or os.path.expanduser(os.path.join("~", "AppData", "Roaming"))
            return os.path.normpath(os.path.join(appdata, "Claude", "claude_desktop_config.json"))
        elif sys_plat == "Darwin":
            return os.path.normpath(os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"))
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser(os.path.join("~", ".config"))
            return os.path.normpath(os.path.join(xdg, "Claude", "claude_desktop_config.json"))

    raise ValueError(f"Unsupported IDE or client: {ide}")


def install_mcp_config(
    ide: str,
    repo_path: str,
    output_json: bool = False,
    is_global: bool = False,
) -> int:
    """Atomically merges Ultron MCP server into client config without clobbering existing servers."""
    clients = ["cursor", "claude", "windsurf", "vscode"] if ide.lower() == "all" else [ide.lower()]
    results = {}
    last_config = {}
    last_path = ""

    server_entry = generate_mcp_config(repo_path)

    for client in clients:
        try:
            config_path = _get_config_path(client, repo_path, is_global=is_global)
        except ValueError as err:
            if not output_json:
                print(f"[!] Error: {err}", file=sys.stderr)
            return 1

        existing = {}
        if os.path.exists(config_path):
            is_corrupted = False
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                    if raw_text.strip():
                        existing = json.loads(raw_text)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                is_corrupted = True

            if not is_corrupted and not isinstance(existing, dict):
                is_corrupted = True

            if is_corrupted:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = f"{config_path}.bak.{ts}"
                try:
                    shutil.copy2(config_path, backup_path)
                    if not output_json:
                        print(
                            f"[!] Warning: Corrupted config at {config_path} backed up to {backup_path}",
                            file=sys.stderr,
                        )
                except OSError:
                    pass
                existing = {}

        if not isinstance(existing, dict):
            existing = {}
        if "mcpServers" not in existing or not isinstance(existing["mcpServers"], dict):
            existing["mcpServers"] = {}

        # Merge (only set/overwrite the "ultron" key)
        existing["mcpServers"]["ultron"] = server_entry

        # Write atomically
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tmp_path = f"{config_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, config_path)

        results[client] = {"path": config_path, "status": "installed"}
        last_config = existing
        last_path = config_path

        if not output_json:
            print(f"[Ultron] MCP configuration installed for {client}: {config_path}")

    if output_json:
        if ide.lower() == "all":
            print(json.dumps({"success": True, "clients": results}, indent=2))
        else:
            print(
                json.dumps(
                    {
                        "success": True,
                        "client": ide.lower(),
                        "path": last_path,
                        "config": last_config,
                    },
                    indent=2,
                )
            )

    return 0


def uninstall_mcp_config(
    ide: str,
    repo_path: str,
    output_json: bool = False,
    is_global: bool = False,
) -> int:
    """Removes Ultron MCP server entry from client config without affecting other servers."""
    clients = ["cursor", "claude", "windsurf", "vscode"] if ide.lower() == "all" else [ide.lower()]
    results = {}
    last_path = ""

    for client in clients:
        try:
            config_path = _get_config_path(client, repo_path, is_global=is_global)
        except ValueError as err:
            if not output_json:
                print(f"[!] Error: {err}", file=sys.stderr)
            return 1

        last_path = config_path
        if not os.path.exists(config_path):
            results[client] = {"path": config_path, "status": "not_found"}
            if not output_json:
                print(f"[Ultron] MCP configuration not found for {client}: {config_path}")
            continue

        existing = {}
        is_corrupted = False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
                if raw_text.strip():
                    existing = json.loads(raw_text)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            is_corrupted = True

        if not is_corrupted and not isinstance(existing, dict):
            is_corrupted = True

        if is_corrupted:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_path = f"{config_path}.bak.{ts}"
            try:
                shutil.copy2(config_path, backup_path)
                if not output_json:
                    print(
                        f"[!] Warning: Corrupted config at {config_path} backed up to {backup_path}",
                        file=sys.stderr,
                    )
            except OSError:
                pass
            existing = {}

        if not isinstance(existing, dict):
            existing = {}

        mcp_servers = existing.get("mcpServers")
        if isinstance(mcp_servers, dict) and "ultron" in mcp_servers:
            del mcp_servers["ultron"]
            dir_name = os.path.dirname(config_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            tmp_path = f"{config_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, config_path)
            results[client] = {"path": config_path, "status": "uninstalled"}
            if not output_json:
                print(f"[Ultron] MCP configuration uninstalled for {client}: {config_path}")
        else:
            results[client] = {"path": config_path, "status": "not_configured"}
            if not output_json:
                print(f"[Ultron] Ultron MCP server was not configured for {client}: {config_path}")

    if output_json:
        if ide.lower() == "all":
            print(json.dumps({"success": True, "action": "uninstall", "clients": results}, indent=2))
        else:
            print(
                json.dumps(
                    {
                        "success": True,
                        "action": "uninstall",
                        "client": ide.lower(),
                        "path": last_path,
                        "status": results.get(ide.lower(), {}).get("status", "unknown"),
                    },
                    indent=2,
                )
            )

    return 0


def repair_mcp_config(
    ide: str,
    repo_path: str,
    output_json: bool = False,
    is_global: bool = False,
) -> int:
    """Validates, recovers from corruption, and re-installs canonical Ultron MCP server configuration."""
    clients = ["cursor", "claude", "windsurf", "vscode"] if ide.lower() == "all" else [ide.lower()]
    results = {}
    last_config = {}
    last_path = ""

    server_entry = generate_mcp_config(repo_path)

    for client in clients:
        try:
            config_path = _get_config_path(client, repo_path, is_global=is_global)
        except ValueError as err:
            if not output_json:
                print(f"[!] Error: {err}", file=sys.stderr)
            return 1

        existing = {}
        was_corrupted = False
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                    if raw_text.strip():
                        existing = json.loads(raw_text)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                was_corrupted = True

            if not was_corrupted and not isinstance(existing, dict):
                was_corrupted = True

            if was_corrupted:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = f"{config_path}.bak.{ts}"
                try:
                    shutil.copy2(config_path, backup_path)
                    if not output_json:
                        print(
                            f"[!] Warning: Corrupted config at {config_path} backed up to {backup_path}",
                            file=sys.stderr,
                        )
                except OSError:
                    pass
                existing = {}

        if not isinstance(existing, dict):
            existing = {}
        if "mcpServers" not in existing or not isinstance(existing["mcpServers"], dict):
            existing["mcpServers"] = {}

        # Merge / repair ultron entry
        existing["mcpServers"]["ultron"] = server_entry

        # Write atomically
        dir_name = os.path.dirname(config_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tmp_path = f"{config_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, config_path)

        status = "repaired_from_corrupted" if was_corrupted else "repaired"
        results[client] = {"path": config_path, "status": status}
        last_config = existing
        last_path = config_path

        if not output_json:
            print(f"[Ultron] MCP configuration repaired for {client}: {config_path}")

    if output_json:
        if ide.lower() == "all":
            print(json.dumps({"success": True, "action": "repair", "clients": results}, indent=2))
        else:
            print(
                json.dumps(
                    {
                        "success": True,
                        "action": "repair",
                        "client": ide.lower(),
                        "path": last_path,
                        "config": last_config,
                        "status": results.get(ide.lower(), {}).get("status", "repaired"),
                    },
                    indent=2,
                )
            )

    return 0


def run_mcp_command(args) -> int:
    """Runs the MCP JSON-RPC 2.0 stdio server loop or installs/repairs/uninstalls IDE config."""
    repo_path = getattr(args, "repo", None) or os.getcwd()

    action = getattr(args, "action", None)
    install_flag = getattr(args, "install", False)
    uninstall_flag = getattr(args, "uninstall", False)
    repair_flag = getattr(args, "repair", False)

    ide = getattr(args, "client", None) or getattr(args, "ide", "cursor") or "cursor"
    output_json = getattr(args, "json", False)
    is_global = getattr(args, "is_global", False)

    if action == "uninstall" or uninstall_flag:
        return uninstall_mcp_config(ide, repo_path, output_json=output_json, is_global=is_global)

    if action == "repair" or repair_flag:
        return repair_mcp_config(ide, repo_path, output_json=output_json, is_global=is_global)

    if action == "install" or install_flag:
        return install_mcp_config(ide, repo_path, output_json=output_json, is_global=is_global)

    return run_mcp_server(repo_path=repo_path)

