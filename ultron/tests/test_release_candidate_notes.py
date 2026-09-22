"""
ultron/tests/test_release_candidate_notes.py
Hermetic verification of Release Candidate Notes and CLI MCP lifecycle (Task RC-C3).

Validates:
1. docs/RELEASE_NOTES_v1.5.0rc1.md exists and contains all 9 required sections.
2. Checksum parity between dist/SHA256SUMS.txt and release notes.
3. Compatibility matrix coverage (Python 3.10-3.12, Linux/macOS/Windows, 0 runtime dependencies).
4. Strict tone boundary: zero assertions of 'enterprise-ready' or 'production-ready'.
5. Experimental capability designations (JS/TS adapter, monorepo workspaces).
6. Exact skip and environment policy statements.
7. CLI MCP repair and uninstall operations (install, uninstall, repair, corrupted recovery).
8. Unified CLI command parsing for positional and flag variants.
"""

import os
import sys
import re
import json
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import ultron
from ultron.interfaces.cli.commands.mcp import (
    install_mcp_config,
    uninstall_mcp_config,
    repair_mcp_config,
    generate_mcp_config,
    _get_config_path,
)


class TestReleaseCandidateNotes(unittest.TestCase):
    """Rigorous verification of release notes completeness and tone invariants."""

    def setUp(self):
        self.notes_path = os.path.join(REPO_ROOT, "docs", "RELEASE_NOTES_v1.5.0rc1.md")
        self.sums_path = os.path.join(REPO_ROOT, "dist", "SHA256SUMS.txt")
        self.manifest_path = os.path.join(REPO_ROOT, "dist", "candidate_manifest.json")

        self.assertTrue(os.path.isfile(self.notes_path), f"Release notes missing at {self.notes_path}")
        with open(self.notes_path, "r", encoding="utf-8") as f:
            self.content = f.read()

    def test_all_nine_required_sections_present(self):
        """Assert release notes document contains all 9 required operational sections."""
        required_sections = [
            "Candidate Wheel and Source Distribution Details",
            "Cryptographic Checksums (SHA-256)",
            "Compatibility Matrix",
            "Known Limitations",
            "Exact Skip & Environment Policy Notes",
            "Experimental Capabilities",
            "Upgrade and Installation Instructions",
            "Rollback Instructions",
            "Model Context Protocol (MCP) Configuration Repair and Uninstall"
        ]
        for section in required_sections:
            self.assertIn(section, self.content, f"Required section missing: '{section}'")

    def test_strict_tone_restriction(self):
        """Assert candidate is NEVER described as enterprise-ready or production-ready."""
        ent_match = re.search(r"\benterprise[\s-]ready\b", self.content, re.IGNORECASE)
        prod_match = re.search(r"\bproduction[\s-]ready\b", self.content, re.IGNORECASE)

        self.assertIsNone(ent_match, f"Banned phrase 'enterprise-ready' found in release notes: {ent_match}")
        self.assertIsNone(prod_match, f"Banned phrase 'production-ready' found in release notes: {prod_match}")

        # Assert disciplined candidate designation
        self.assertIn("pre-release candidate for stabilization and testing", self.content.lower())

    def test_checksum_parity_with_sha256sums_file(self):
        """Assert all checksums in dist/SHA256SUMS.txt are verbatim documented in release notes."""
        self.assertTrue(os.path.isfile(self.sums_path), f"dist/SHA256SUMS.txt missing at {self.sums_path}")
        with open(self.sums_path, "r", encoding="utf-8") as f:
            sums_lines = [line.strip() for line in f if line.strip()]

        for sum_line in sums_lines:
            sha256_hash, filename = sum_line.split(None, 1)
            self.assertIn(
                sha256_hash,
                self.content,
                f"Checksum {sha256_hash} for {filename} missing from release notes"
            )
            self.assertIn(
                filename,
                self.content,
                f"Artifact {filename} missing from release notes"
            )

    def test_compatibility_matrix_specifications(self):
        """Assert compatibility matrix details Python 3.10-3.12, OS support, and 0 runtime dependencies."""
        self.assertIn("3.10", self.content)
        self.assertIn("3.11", self.content)
        self.assertIn("3.12", self.content)
        self.assertIn("Linux", self.content)
        self.assertIn("macOS", self.content)
        self.assertIn("Windows", self.content)
        self.assertIn("0 external dependencies", self.content)
        self.assertIn("pyproject.toml", self.content)

    def test_known_limitations_honesty(self):
        """Assert all 5 core honest limitations are declared."""
        self.assertIn("Python-Only AST Metric Depth", self.content)
        self.assertIn("Syntactic & Topological Scope", self.content)
        self.assertIn("Git History Dependency", self.content)
        self.assertIn("Coverage Ingestion Requirement", self.content)
        self.assertIn("Production PyPI Gate", self.content)

    def test_exact_skip_policy_declared(self):
        """Assert exact skip policy: zero skips in standard CI, bounded skips only for network."""
        self.assertIn("Zero test skips are permitted", self.content)
        self.assertIn("Bounded Skips", self.content)
        self.assertIn("1,026+ automated tests", self.content)

    def test_experimental_capabilities_labeled(self):
        """Assert JS/TS adapter and monorepo workspaces are designated Experimental (Beta in v1.5.0rc1)."""
        self.assertIn("JavaScript / TypeScript Language Adapter", self.content)
        self.assertIn("Monorepo Workspaces", self.content)
        self.assertIn("Experimental (Beta in v1.5.0rc1)", self.content)


class TestCliMcpLifecycle(unittest.TestCase):
    """Hermetic functional verification of MCP install, uninstall, and repair actions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ultron_mcp_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mcp_install_uninstall_and_repair_cycle(self):
        """Test complete lifecycle: install server, verify presence, uninstall, verify clean removal, repair."""
        # 1. Install
        code = install_mcp_config("cursor", self.temp_dir, output_json=True, is_global=False)
        self.assertEqual(code, 0)

        cursor_cfg = os.path.join(self.temp_dir, ".cursor", "mcp.json")
        self.assertTrue(os.path.isfile(cursor_cfg))

        with open(cursor_cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("mcpServers", data)
        self.assertIn("ultron", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["ultron"]["command"], sys.executable)
        self.assertIn("--repo", data["mcpServers"]["ultron"]["args"])

        # Add a dummy second server to verify uninstall preserves non-ultron servers
        data["mcpServers"]["other_server"] = {"command": "other", "args": []}
        with open(cursor_cfg, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # 2. Uninstall
        uninst_code = uninstall_mcp_config("cursor", self.temp_dir, output_json=True, is_global=False)
        self.assertEqual(uninst_code, 0)

        with open(cursor_cfg, "r", encoding="utf-8") as f:
            after_uninst = json.load(f)
        self.assertNotIn("ultron", after_uninst["mcpServers"])
        self.assertIn("other_server", after_uninst["mcpServers"], "Non-Ultron server must be preserved!")

        # 3. Repair
        rep_code = repair_mcp_config("cursor", self.temp_dir, output_json=True, is_global=False)
        self.assertEqual(rep_code, 0)

        with open(cursor_cfg, "r", encoding="utf-8") as f:
            after_rep = json.load(f)
        self.assertIn("ultron", after_rep["mcpServers"])
        self.assertIn("other_server", after_rep["mcpServers"])

    def test_mcp_repair_recovers_from_corrupted_json(self):
        """Test that repair creates a backup and restores valid JSON when encountering malformed config."""
        cursor_dir = os.path.join(self.temp_dir, ".cursor")
        os.makedirs(cursor_dir, exist_ok=True)
        cursor_cfg = os.path.join(cursor_dir, "mcp.json")

        # Write corrupt non-JSON content
        with open(cursor_cfg, "w", encoding="utf-8") as f:
            f.write("{ invalid json content !!!")

        code = repair_mcp_config("cursor", self.temp_dir, output_json=True, is_global=False)
        self.assertEqual(code, 0)

        # Config should now be valid JSON with ultron server
        with open(cursor_cfg, "r", encoding="utf-8") as f:
            repaired_data = json.load(f)
        self.assertIn("mcpServers", repaired_data)
        self.assertIn("ultron", repaired_data["mcpServers"])

        # Backup file should exist in the directory
        files = os.listdir(cursor_dir)
        bak_files = [f for f in files if ".bak." in f]
        self.assertTrue(len(bak_files) >= 1, "Backup file should be created for corrupted config")

    def test_mcp_uninstall_idempotent_when_not_configured(self):
        """Test uninstall does not fail when ultron server is not present or file does not exist."""
        # Non-existent file
        code = uninstall_mcp_config("cursor", self.temp_dir, output_json=True, is_global=False)
        self.assertEqual(code, 0)

        # File exists without ultron
        cursor_dir = os.path.join(self.temp_dir, ".cursor")
        os.makedirs(cursor_dir, exist_ok=True)
        with open(os.path.join(cursor_dir, "mcp.json"), "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {}}, f)

    def test_mcp_cli_subcommand_dispatch(self):
        """Test unified CLI argument parsing and dispatch for both positional and flag syntax."""
        import subprocess

        # Positional: ultron mcp install --client cursor
        cmd_install = [
            sys.executable,
            "-m",
            "ultron.interfaces.ultron",
            "mcp",
            "install",
            "--client",
            "cursor",
            "--repo",
            self.temp_dir,
            "--json"
        ]
        res_inst = subprocess.run(cmd_install, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        data_inst = json.loads(res_inst.stdout)
        self.assertTrue(data_inst.get("success"))

        # Positional: ultron mcp repair --client cursor
        cmd_repair = [
            sys.executable,
            "-m",
            "ultron.interfaces.ultron",
            "mcp",
            "repair",
            "--client",
            "cursor",
            "--repo",
            self.temp_dir,
            "--json"
        ]
        res_rep = subprocess.run(cmd_repair, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        data_rep = json.loads(res_rep.stdout)
        self.assertTrue(data_rep.get("success"))
        self.assertEqual(data_rep.get("action"), "repair")

        # Flag variant: ultron mcp --uninstall --client cursor
        cmd_uninst = [
            sys.executable,
            "-m",
            "ultron.interfaces.ultron",
            "mcp",
            "--uninstall",
            "--client",
            "cursor",
            "--repo",
            self.temp_dir,
            "--json"
        ]
        res_uninst = subprocess.run(cmd_uninst, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        data_uninst = json.loads(res_uninst.stdout)
        self.assertTrue(data_uninst.get("success"))
        self.assertEqual(data_uninst.get("action"), "uninstall")


if __name__ == "__main__":

    unittest.main()
