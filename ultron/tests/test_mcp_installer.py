"""
ultron.tests.test_mcp_installer
Unit tests for the automated multi-client MCP installer (ultron mcp install).
All tests are completely hermetic and isolated from the host filesystem.
"""

from io import StringIO
import json
import os
import platform
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from ultron.interfaces.cli.commands.mcp import (
    generate_mcp_config,
    _get_config_path,
    install_mcp_config,
    run_mcp_command,
)


class TestMcpInstaller(unittest.TestCase):
    """Test suite for MCP multi-client configuration installer."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home_dir = os.path.join(self.temp_dir.name, "home")
        self.appdata_dir = os.path.join(self.temp_dir.name, "appdata")
        self.repo_dir = os.path.join(self.temp_dir.name, "repo")

        os.makedirs(self.home_dir, exist_ok=True)
        os.makedirs(self.appdata_dir, exist_ok=True)
        os.makedirs(self.repo_dir, exist_ok=True)

        # Patch environment variables for full host isolation
        self.env_patcher = patch.dict(
            os.environ,
            {
                "APPDATA": self.appdata_dir,
                "USERPROFILE": self.home_dir,
                "HOME": self.home_dir,
                "XDG_CONFIG_HOME": os.path.join(self.home_dir, ".config"),
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        self.temp_dir.cleanup()

    def test_generate_mcp_config(self):
        """Verifies structure of generated MCP server configuration."""
        cfg = generate_mcp_config(self.repo_dir)
        self.assertIn("command", cfg)
        self.assertIn("args", cfg)
        self.assertEqual(cfg["command"], sys.executable)
        self.assertEqual(
            cfg["args"],
            ["-m", "ultron.interfaces.mcp_server", "--repo", os.path.abspath(self.repo_dir)],
        )

    def test_get_config_path_cursor_local(self):
        """Verifies local repository path for Cursor."""
        path = _get_config_path("cursor", self.repo_dir, is_global=False)
        expected = os.path.normpath(os.path.join(self.repo_dir, ".cursor", "mcp.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_cursor_global(self):
        """Verifies global user path for Cursor."""
        path = _get_config_path("cursor", self.repo_dir, is_global=True)
        expected = os.path.normpath(os.path.join(self.home_dir, ".cursor", "mcp.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_windsurf_local(self):
        """Verifies local repository path for Windsurf."""
        path = _get_config_path("windsurf", self.repo_dir, is_global=False)
        expected = os.path.normpath(os.path.join(self.repo_dir, ".windsurf", "mcp.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_windsurf_global(self):
        """Verifies global user path for Windsurf."""
        path = _get_config_path("windsurf", self.repo_dir, is_global=True)
        expected = os.path.normpath(os.path.join(self.home_dir, ".codeium", "windsurf", "mcp_config.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_vscode_local(self):
        """Verifies local repository path for VS Code."""
        path = _get_config_path("vscode", self.repo_dir, is_global=False)
        expected = os.path.normpath(os.path.join(self.repo_dir, ".vscode", "mcp.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_vscode_global(self):
        """Verifies global user path for VS Code."""
        path = _get_config_path("vscode", self.repo_dir, is_global=True)
        expected = os.path.normpath(os.path.join(self.home_dir, ".vscode", "mcp.json"))
        self.assertEqual(path, expected)

    def test_get_config_path_claude_windows(self):
        """Verifies Claude Desktop path on Windows."""
        with patch("platform.system", return_value="Windows"):
            path = _get_config_path("claude", self.repo_dir)
            expected = os.path.normpath(os.path.join(self.appdata_dir, "Claude", "claude_desktop_config.json"))
            self.assertEqual(path, expected)

    def test_get_config_path_claude_darwin(self):
        """Verifies Claude Desktop path on macOS (Darwin)."""
        with patch("platform.system", return_value="Darwin"):
            path = _get_config_path("claude", self.repo_dir)
            expected = os.path.normpath(
                os.path.join(self.home_dir, "Library", "Application Support", "Claude", "claude_desktop_config.json")
            )
            self.assertEqual(path, expected)

    def test_get_config_path_claude_linux(self):
        """Verifies Claude Desktop path on Linux (XDG fallback)."""
        with patch("platform.system", return_value="Linux"):
            path = _get_config_path("claude", self.repo_dir)
            expected = os.path.normpath(
                os.path.join(self.home_dir, ".config", "Claude", "claude_desktop_config.json")
            )
            self.assertEqual(path, expected)

    def test_get_config_path_unsupported_raises_value_error(self):
        """Verifies ValueError raised for unsupported client."""
        with self.assertRaises(ValueError):
            _get_config_path("emacs", self.repo_dir)

    def test_install_mcp_config_creates_new(self):
        """Verifies creating new config file with ultron server entry."""
        ret = install_mcp_config("cursor", self.repo_dir)
        self.assertEqual(ret, 0)

        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        self.assertTrue(os.path.exists(cfg_path))
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("mcpServers", data)
        self.assertIn("ultron", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["ultron"]["command"], sys.executable)

    def test_install_mcp_config_preserves_existing_servers(self):
        """Verifies that installing Ultron does not overwrite existing third-party servers."""
        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        initial_data = {
            "mcpServers": {
                "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]},
                "postgres": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres"]},
            },
            "customSetting": 123,
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        ret = install_mcp_config("cursor", self.repo_dir)
        self.assertEqual(ret, 0)

        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("ultron", data["mcpServers"])
        self.assertIn("github", data["mcpServers"])
        self.assertIn("postgres", data["mcpServers"])
        self.assertEqual(data["customSetting"], 123)

    def test_install_mcp_config_idempotent(self):
        """Verifies repeated installations are completely idempotent."""
        install_mcp_config("cursor", self.repo_dir)
        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            first_run = f.read()

        install_mcp_config("cursor", self.repo_dir)
        with open(cfg_path, "r", encoding="utf-8") as f:
            second_run = f.read()

        self.assertEqual(first_run, second_run)

    def test_install_mcp_config_corrupted_json_backup(self):
        """Verifies corrupted JSON triggers microsecond timestamped backup and repairs file."""
        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        corrupted_text = "{ invalid json content: 123"
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write(corrupted_text)

        ret = install_mcp_config("cursor", self.repo_dir)
        self.assertEqual(ret, 0)

        # Confirm target file is repaired and valid JSON
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("ultron", data["mcpServers"])

        # Confirm backup file exists with corrupted content
        parent_dir = os.path.dirname(cfg_path)
        bak_files = [f for f in os.listdir(parent_dir) if f.startswith("mcp.json.bak.")]
        self.assertEqual(len(bak_files), 1)
        bak_path = os.path.join(parent_dir, bak_files[0])
        with open(bak_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), corrupted_text)

    def test_install_mcp_config_non_dict_backup(self):
        """Verifies non-dict JSON (e.g. array) is backed up and repaired."""
        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write("[1, 2, 3]")

        ret = install_mcp_config("cursor", self.repo_dir)
        self.assertEqual(ret, 0)

        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
        self.assertIn("ultron", data["mcpServers"])

        parent_dir = os.path.dirname(cfg_path)
        bak_files = [f for f in os.listdir(parent_dir) if f.startswith("mcp.json.bak.")]
        self.assertEqual(len(bak_files), 1)

    def test_install_mcp_config_invalid_mcp_servers_key(self):
        """Verifies non-dict mcpServers key is normalized to dict without crashing."""
        cfg_path = os.path.join(self.repo_dir, ".cursor", "mcp.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": "not-a-dict"}, f)

        ret = install_mcp_config("cursor", self.repo_dir)
        self.assertEqual(ret, 0)

        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data["mcpServers"], dict)
        self.assertIn("ultron", data["mcpServers"])

    def test_install_mcp_config_all_clients(self):
        """Verifies installing with client 'all' installs to all supported IDEs."""
        ret = install_mcp_config("all", self.repo_dir)
        self.assertEqual(ret, 0)

        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, ".cursor", "mcp.json")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, ".windsurf", "mcp.json")))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, ".vscode", "mcp.json")))

    def test_install_mcp_config_json_output(self):
        """Verifies JSON output mode emits valid machine-readable JSON."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            ret = install_mcp_config("cursor", self.repo_dir, output_json=True)
        self.assertEqual(ret, 0)

        output = buf.getvalue().strip()
        data = json.loads(output)
        self.assertTrue(data["success"])
        self.assertEqual(data["client"], "cursor")
        self.assertIn("path", data)
        self.assertIn("config", data)

    def test_install_mcp_config_all_json_output(self):
        """Verifies JSON output mode for client 'all' emits valid machine-readable JSON."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            ret = install_mcp_config("all", self.repo_dir, output_json=True)
        self.assertEqual(ret, 0)

        output = buf.getvalue().strip()
        data = json.loads(output)
        self.assertTrue(data["success"])
        self.assertIn("clients", data)
        self.assertIn("cursor", data["clients"])
        self.assertIn("claude", data["clients"])
        self.assertIn("windsurf", data["clients"])
        self.assertIn("vscode", data["clients"])

    def test_run_mcp_command_install_action(self):
        """Verifies run_mcp_command handles positional action 'install'."""
        class Args:
            action = "install"
            client = "cursor"
            repo = self.repo_dir
            json = False
            is_global = False
            install = False

        ret = run_mcp_command(Args())
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, ".cursor", "mcp.json")))

    def test_run_mcp_command_install_flag(self):
        """Verifies run_mcp_command handles --install flag."""
        class Args:
            action = "serve"
            install = True
            ide = "windsurf"
            client = None
            repo = self.repo_dir
            json = False
            is_global = False

        ret = run_mcp_command(Args())
        self.assertEqual(ret, 0)
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, ".windsurf", "mcp.json")))

    def test_run_mcp_command_unsupported_client(self):
        """Verifies run_mcp_command returns code 1 for unsupported client."""
        class Args:
            action = "install"
            client = "sublime"
            repo = self.repo_dir
            json = True
            is_global = False
            install = False

        ret = run_mcp_command(Args())
        self.assertEqual(ret, 1)


if __name__ == "__main__":
    unittest.main()
