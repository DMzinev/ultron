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
import sys
import re
import json
import subprocess

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

        cls.resources_path = os.path.join(REPO_ROOT, "docs", "RESOURCES.md")
        with open(cls.resources_path, "r", encoding="utf-8") as f:
            cls.resources_content = f.read()

        cls.getting_started_path = os.path.join(REPO_ROOT, "docs", "GETTING_STARTED.md")
        with open(cls.getting_started_path, "r", encoding="utf-8") as f:
            cls.getting_started_content = f.read()

        cls.release_facts_path = os.path.join(REPO_ROOT, "docs", "release_facts.json")
        if os.path.isfile(cls.release_facts_path):
            with open(cls.release_facts_path, "r", encoding="utf-8") as f:
                cls.release_facts = json.load(f)
        else:
            cls.release_facts = {}

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
        subcommands = ["scan", "brief", "gate", "init", "verify", "mcp", "hook", "impact", "export", "watch", "version"]
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
        ]
        if not os.path.exists(os.path.join(REPO_ROOT, "LICENSE")):
            dead_references.append("[MIT License](LICENSE)")
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

    def test_no_stale_test_counters(self):
        """Assert absence of obsolete test counters across public documentation pages."""
        # README.md checks
        self.assertNotIn("tests-973%20passed", self.readme_content, "Stale 973 badge in README.md")
        self.assertNotIn("973 automated tests", self.readme_content, "Stale 973 test count in README.md")
        self.assertNotIn("892+ automated tests", self.readme_content, "Stale 892+ test count in README.md")
        self.assertIn("1,000+ automated tests", self.readme_content, "README.md must refer to 1,000+ automated tests")

        # docs/RESOURCES.md checks
        self.assertNotIn("892+ automated tests", self.resources_content, "Stale 892+ test count in docs/RESOURCES.md")
        self.assertIn("1,000+ automated tests", self.resources_content, "docs/RESOURCES.md must refer to 1,000+ automated tests")

        # docs/GETTING_STARTED.md checks
        self.assertNotIn("TESTS: 820 ran", self.getting_started_content, "Stale 820 test run count in docs/GETTING_STARTED.md")

    def test_action_documentation_reality(self):
        """Assert verified repository-local action and consumable action ref are documented."""
        self.assertIn(
            "./.github/actions/ultron-gate",
            self.readme_content,
            "README.md must document verified repository-local action ./.github/actions/ultron-gate"
        )
        self.assertIn(
            "./.github/actions/ultron-gate",
            self.getting_started_content,
            "docs/GETTING_STARTED.md must document verified repository-local action ./.github/actions/ultron-gate"
        )
        self.assertIn(
            "DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1",
            self.readme_content,
            "README.md must document consumable action DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1"
        )
        self.assertIn(
            "DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1",
            self.getting_started_content,
            "docs/GETTING_STARTED.md must document consumable action DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1"
        )
        self.assertIn(
            "planned for external publication",
            self.readme_content,
            "README.md must qualify DMzinev/ultron-action@v1 as planned for external publication"
        )
        if self.release_facts:
            act = self.release_facts.get("github_action", {})
            self.assertEqual(
                act.get("consumable_action"),
                "DMzinev/ultron/.github/actions/ultron-gate@v1.5.0rc1",
                "release_facts.json must record consumable_action"
            )

    def test_prerelease_status_declared(self):
        """Assert 1.5.0rc1 is documented as an active pre-release candidate for stabilization."""
        self.assertIn(
            "1.5.0rc1",
            self.readme_content,
            "README.md must declare version 1.5.0rc1"
        )
        self.assertIn(
            "pre-release candidate",
            self.readme_content.lower(),
            "README.md must explicitly identify 1.5.0rc1 as a pre-release candidate"
        )
        if self.release_facts:
            self.assertTrue(
                self.release_facts.get("is_prerelease"),
                "release_facts.json must have is_prerelease set to True"
            )

    def test_experimental_capabilities_declared(self):
        """Assert JS/TS adapter and monorepo workspaces are designated Experimental (Beta in v1.5.0rc1)."""
        self.assertIn("Experimental (Beta in v1.5.0rc1)", self.readme_content)
        if self.release_facts:
            exp = self.release_facts.get("experimental_capabilities", {})
            self.assertEqual(exp.get("js_ts_language_adapter"), "Experimental (Beta in v1.5.0rc1)")
            self.assertEqual(exp.get("monorepo_workspaces"), "Experimental (Beta in v1.5.0rc1)")

    def test_skip_policy_declared(self):
        """Assert exact observed skip policy is documented in README.md and release facts."""
        self.assertIn("Observed Skip Policy", self.readme_content)
        self.assertIn("Zero test skips are permitted in standard CI", self.readme_content)
        if self.release_facts:
            self.assertIn("Zero test skips in standard CI", self.release_facts.get("skip_policy", ""))

    def test_release_facts_generator_check(self):
        """Assert scripts/generate_release_facts.py --check exits 0 with zero drift."""
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "scripts", "generate_release_facts.py"), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"scripts/generate_release_facts.py --check failed with code {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        )
        self.assertIn("Release facts in sync with documentation reality.", proc.stdout)


if __name__ == "__main__":
    unittest.main()
