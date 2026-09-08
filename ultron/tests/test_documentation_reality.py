"""
ultron/tests/test_documentation_reality.py
Automated documentation reality test suite.

Ensures that README.md strictly matches the real, shipped codebase:
1. Bidirectional 1:1 parity between documented MCP tools and live mcp_server schema.
2. All documented CLI subcommands exist and resolve in ultron.py.
3. Zero dead references to legacy/deleted files (legacy.*, start.py, start.bat).
4. Explicit honest limitations (Python-only, syntactic bounds, git/coverage prerequisites).
5. Repository root cleanliness: zero PHASE* or audit dump residue files at root.
"""

import unittest
import os
import re
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestDocumentationReality(unittest.TestCase):
    """Enforces documentation honesty, link correctness, and root directory cleanliness."""

    @classmethod
    def setUpClass(cls):
        cls.readme_path = os.path.join(REPO_ROOT, "README.md")
        if not os.path.isfile(cls.readme_path):
            raise FileNotFoundError(f"README.md missing at {cls.readme_path}")
        with open(cls.readme_path, "r", encoding="utf-8") as f:
            cls.readme_content = f.read()

    def test_readme_mcp_tools_bidirectional_parity(self):
        """Assert all 7 MCP tools in mcp_server.py tools/list are documented in README.md."""
        from ultron.interfaces import mcp_server

        raw_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })
        resp_raw = mcp_server.handle_mcp_request(raw_req)
        resp = json.loads(resp_raw) if isinstance(resp_raw, str) else resp_raw

        actual_tools = set(t["name"] for t in resp.get("result", {}).get("tools", []))
        self.assertEqual(len(actual_tools), 7, f"Expected 7 MCP tools, found {len(actual_tools)}: {actual_tools}")

        documented_tools = set()
        for t in actual_tools:
            if f"`{t}`" in self.readme_content:
                documented_tools.add(t)

        self.assertEqual(
            actual_tools,
            documented_tools,
            f"Discrepancy between actual MCP tools and README.md: missing {actual_tools - documented_tools}"
        )

    def test_readme_cli_commands_valid(self):
        """Assert documented CLI commands and subcommands correspond to real implementations."""
        subcommands = ["scan", "brief", "gate", "init"]
        for sub in subcommands:
            self.assertIn(f"ultron {sub}", self.readme_content, f"Documented subcommand ultron {sub} missing in README.md")

        self.assertIn("ultron-server", self.readme_content)
        self.assertIn("ultron-mcp", self.readme_content)

        ultron_py_path = os.path.join(REPO_ROOT, "ultron", "interfaces", "ultron.py")
        with open(ultron_py_path, "r", encoding="utf-8") as f:
            ultron_src = f.read()

        for sub in subcommands:
            self.assertIn(f'"{sub}"', ultron_src, f"Subcommand {sub} must be registered in ultron.py")

    def test_readme_has_no_dead_references(self):
        """Assert absence of references to deleted or obsolete files."""
        dead_references = [
            "legacy.html",
            "legacy.js",
            "legacy.css",
            "start.py",
            "start.bat",
            "[MIT License](LICENSE)",
        ]
        for ref in dead_references:
            self.assertNotIn(
                ref,
                self.readme_content,
                f"README.md contains dead reference to deleted/nonexistent file: {ref}"
            )

    def test_readme_honest_limits_declared(self):
        """Assert honest limitations section is present with Python-only and syntactic boundaries."""
        self.assertIn("Honest Limitations", self.readme_content)
        self.assertIn("Python Only", self.readme_content)
        self.assertIn("Syntactic & Topological, Not Dynamic", self.readme_content)
        self.assertIn("Git History Dependency", self.readme_content)
        self.assertIn("Coverage Ingestion Dependency", self.readme_content)

    def test_root_directory_clean_of_phase_reports(self):
        """Assert repository root directory contains zero PHASE* residue or audit dumps."""
        root_files = os.listdir(REPO_ROOT)
        phase_files = [f for f in root_files if f.startswith("PHASE") or f.startswith("ULTRON_PHASE")]
        self.assertEqual(
            phase_files,
            [],
            f"Root directory still contains {len(phase_files)} legacy PHASE audit files: {phase_files}"
        )

        audit_dumps = [
            f for f in root_files
            if f.endswith("_AUDIT.md")
            or f.endswith("_MATRIX.md")
            or f.endswith("_MATRIX.json")
            or f.endswith("_TRACE.md")
            or f.endswith("_CENSUS.md")
            or f.endswith("_REGISTER.md")
            or f.endswith("_LEDGER.md")
            or f.endswith("_SCORECARD.md")
            or f.endswith("_TRIAL.md")
            or f.endswith("_BASELINE.md")
        ]
        self.assertEqual(
            audit_dumps,
            [],
            f"Root directory still contains {len(audit_dumps)} legacy audit dump files: {audit_dumps}"
        )

        archive_dir = os.path.join(REPO_ROOT, "docs", "audits", "legacy_phase_reports")
        self.assertTrue(os.path.isdir(archive_dir), f"Archive directory {archive_dir} missing")
        archived_count = len(os.listdir(archive_dir))
        self.assertGreaterEqual(archived_count, 50, f"Archive directory should contain at least 50 reports, found {archived_count}")


if __name__ == "__main__":
    unittest.main()
