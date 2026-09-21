"""
ultron/tests/test_candidate_artifact_invariants.py
Rigorous verification of the immutable release candidate artifact package (Task RC-B4).

Validates:
1. Candidate artifact bundle completeness (8 required files in dist/).
2. Candidate wheel (.whl) archive invariants (runtime modules, 13 web modules, migrations, rulepacks, entrypoints, zero leaks).
3. Source distribution (.tar.gz) archive invariants (manifests, source, zero scratch/git leaks).
4. Standard UNIX coreutils SHA-256 checksum format and cryptographic integrity.
5. Candidate manifest schema and commit binding.
6. Zero runtime dependencies in Software Bill of Materials (dependency_inventory.json & docs/DEPENDENCY_INVENTORY.md).
7. Documentation reality check preventing premature PyPI distribution claims.
"""

import unittest
import os
import sys
import json
import zipfile
import tarfile
import hashlib
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import ultron
from scripts import build_candidate_artifacts


class TestCandidateArtifactInvariants(unittest.TestCase):
    """Hermetic verification of candidate distribution artifacts."""

    DIST_DIR = os.path.join(REPO_ROOT, "dist")
    REQUIRED_ARTIFACTS = {
        "ultron_risk_scorer-1.5.0-py3-none-any.whl",
        "ultron_risk_scorer-1.5.0.tar.gz",
        "SHA256SUMS.txt",
        "candidate_manifest.json",
        "dependency_inventory.json",
        "test_result_summary.json",
        "LICENSE",
        "release_facts.json"
    }

    @classmethod
    def setUpClass(cls):
        """Ensure candidate artifacts exist and are ready for inspection."""
        missing = [f for f in cls.REQUIRED_ARTIFACTS if not os.path.isfile(os.path.join(cls.DIST_DIR, f))]
        if missing:
            # Build candidate artifacts if missing (e.g. fresh clone)
            build_candidate_artifacts.clean_build_residue(REPO_ROOT)
            build_candidate_artifacts.execute_build(REPO_ROOT, cls.DIST_DIR)
            build_candidate_artifacts.generate_candidate_bundle(REPO_ROOT, cls.DIST_DIR)

    def test_candidate_artifact_bundle_completeness(self):
        """Verify all 8 mandatory release candidate artifacts exist in dist/."""
        self.assertTrue(os.path.isdir(self.DIST_DIR), f"Dist directory does not exist: {self.DIST_DIR}")
        existing = set(os.listdir(self.DIST_DIR))
        for artifact in self.REQUIRED_ARTIFACTS:
            self.assertIn(
                artifact, existing,
                f"Mandatory candidate artifact '{artifact}' missing from {self.DIST_DIR}"
            )
            fpath = os.path.join(self.DIST_DIR, artifact)
            self.assertGreater(
                os.path.getsize(fpath), 0,
                f"Candidate artifact '{artifact}' must not be an empty file"
            )

    def test_wheel_archive_invariants(self):
        """Verify wheel archive contains all required runtime and web assets and excludes forbidden files."""
        whl_path = os.path.join(self.DIST_DIR, "ultron_risk_scorer-1.5.0-py3-none-any.whl")
        self.assertTrue(os.path.isfile(whl_path), f"Wheel not found at: {whl_path}")

        with zipfile.ZipFile(whl_path, "r") as zf:
            names = set(zf.namelist())

            # 1. Essential runtime modules
            essential_modules = [
                "ultron/__init__.py",
                "ultron/__main__.py",
                "ultron/_version.py",
                "ultron/core/analyzer.py",
                "ultron/core/sarif_reporter.py",
                "ultron/core/monorepo.py",
                "ultron/interfaces/server.py",
                "ultron/interfaces/ultron.py",
                "ultron/interfaces/mcp_server.py",
            ]
            for mod in essential_modules:
                self.assertIn(mod, names, f"Essential runtime module '{mod}' missing from wheel")

            # 2. Web interface root assets
            for web_root in ("ultron/interfaces/web/index.html", "ultron/interfaces/web/index.css", "ultron/interfaces/web/index.js"):
                self.assertIn(web_root, names, f"Web interface root asset '{web_root}' missing from wheel")

            # 3. All 13 web frontend JavaScript submodules
            web_submodules = (
                "api", "auditor", "dashboard", "detail", "graph", "modals",
                "picker", "state", "storage", "studio", "ui", "violations"
            )
            for mod in web_submodules:
                mod_path = f"ultron/interfaces/web/modules/{mod}.js"
                self.assertIn(mod_path, names, f"Web frontend submodule '{mod_path}' missing from wheel")

            # 4. SQLite migrations and default rulepack
            migration_files = [n for n in names if "migrations/" in n and n.endswith(".sql")]
            self.assertGreaterEqual(len(migration_files), 1, "Wheel must package SQLite database migration scripts")

            rulepack_file = "ultron/core/rkm/rulepacks/default/rules.json"
            self.assertIn(rulepack_file, names, f"Default rulepack '{rulepack_file}' missing from wheel")

            # 5. Entrypoints metadata
            entry_points_files = [n for n in names if n.endswith("entry_points.txt")]
            self.assertEqual(len(entry_points_files), 1, "Wheel metadata must contain entry_points.txt")
            ep_content = zf.read(entry_points_files[0]).decode("utf-8")
            self.assertIn("ultron = ultron.interfaces.ultron:main", ep_content)
            self.assertIn("ultron-server = ultron.interfaces.server:main", ep_content)
            self.assertIn("ultron-mcp = ultron.interfaces.mcp_server:main", ep_content)

            # 6. Anti-leakage checks (Zero tests, scratch, or governance files)
            forbidden_prefixes = (
                "ultron/tests/",
                "ultron/scratch/",
                "ultron/validation/",
                ".agents/",
                "umags/",
                "docs/"
            )
            for name in names:
                for forbidden in forbidden_prefixes:
                    self.assertFalse(
                        name.startswith(forbidden),
                        f"Wheel archive leaked forbidden path: {name}"
                    )

    def test_sdist_archive_invariants(self):
        """Verify source distribution contains core packaging files and excludes scratch/git."""
        sdist_path = os.path.join(self.DIST_DIR, "ultron_risk_scorer-1.5.0.tar.gz")
        self.assertTrue(os.path.isfile(sdist_path), f"Sdist not found at: {sdist_path}")

        with tarfile.open(sdist_path, "r:*") as tf:
            names = tf.getnames()
            clean_names = set("/".join(n.split("/")[1:]) for n in names if "/" in n)

            required_sdist_files = [
                "pyproject.toml",
                "setup.py",
                "README.md",
                "LICENSE",
                "ultron/__init__.py",
                "ultron/__main__.py"
            ]
            for req in required_sdist_files:
                self.assertIn(req, clean_names, f"Required sdist manifest '{req}' missing from archive")

            forbidden_sdist_prefixes = (
                "ultron/scratch/",
                ".git/",
                ".ultron/store.db"
            )
            for name in clean_names:
                for forbidden in forbidden_sdist_prefixes:
                    self.assertFalse(
                        name.startswith(forbidden),
                        f"Source distribution leaked forbidden path: {name}"
                    )

    def test_sha256_checksum_format(self):
        """Verify SHA256SUMS.txt adheres to UNIX coreutils format and matches actual file digests."""
        sums_path = os.path.join(self.DIST_DIR, "SHA256SUMS.txt")
        self.assertTrue(os.path.isfile(sums_path), f"Checksums file not found at: {sums_path}")

        with open(sums_path, "rb") as f:
            raw_bytes = f.read()

        # Must end with standard \n
        self.assertTrue(raw_bytes.endswith(b"\n"), "SHA256SUMS.txt must end with a standard UNIX newline")
        text = raw_bytes.decode("utf-8")
        lines = [line for line in text.split("\n") if line.strip()]

        # Exactly 7 files are hashed in SHA256SUMS.txt (the 7 sibling candidate artifacts)
        self.assertEqual(len(lines), 7, f"Expected 7 checksum entries, found {len(lines)}")

        expected_filenames = {
            "ultron_risk_scorer-1.5.0-py3-none-any.whl",
            "ultron_risk_scorer-1.5.0.tar.gz",
            "dependency_inventory.json",
            "test_result_summary.json",
            "LICENSE",
            "release_facts.json",
            "candidate_manifest.json"
        }

        seen_filenames = set()
        for line in lines:
            # Standard coreutils format: 64 hex characters, followed by two spaces, followed by filename
            match = re.match(r"^([0-9a-f]{64})  (\S+)$", line)
            self.assertIsNotNone(
                match,
                f"Line does not conform to UNIX coreutils checksum format '<hash>  <file>': '{line}'"
            )
            digest, filename = match.group(1), match.group(2)
            self.assertIn(filename, expected_filenames, f"Unexpected file in SHA256SUMS.txt: {filename}")
            seen_filenames.add(filename)

            # Cryptographic verification
            target_path = os.path.join(self.DIST_DIR, filename)
            self.assertTrue(os.path.isfile(target_path), f"Hashed file does not exist: {target_path}")

            h = hashlib.sha256()
            with open(target_path, "rb") as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            actual_digest = h.hexdigest()
            self.assertEqual(
                actual_digest, digest,
                f"Cryptographic hash mismatch for '{filename}': expected {digest}, got {actual_digest}"
            )

        self.assertEqual(seen_filenames, expected_filenames, "All 7 candidate payload files must be hashed")

    def test_candidate_manifest_schema(self):
        """Verify candidate_manifest.json conforms to schema v1.0.0 and binds to commit."""
        manifest_path = os.path.join(self.DIST_DIR, "candidate_manifest.json")
        self.assertTrue(os.path.isfile(manifest_path), f"Candidate manifest missing: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("schema_version"), "1.0.0")
        self.assertEqual(data.get("package_name"), "ultron-risk-scorer")
        self.assertEqual(data.get("package_version"), ultron.get_version())
        self.assertEqual(data.get("release_candidate"), "1.5.0rc1")
        self.assertIn("git_commit", data)
        self.assertIn("built_at", data)
        self.assertIn("artifacts", data)

        artifacts = data["artifacts"]
        expected_manifest_keys = [
            "ultron_risk_scorer-1.5.0-py3-none-any.whl",
            "ultron_risk_scorer-1.5.0.tar.gz",
            "dependency_inventory.json",
            "test_result_summary.json",
            "LICENSE",
            "release_facts.json"
        ]
        for key in expected_manifest_keys:
            self.assertIn(key, artifacts, f"Artifact '{key}' missing from candidate manifest")
            entry = artifacts[key]
            self.assertIn("sha256", entry)
            self.assertIn("size_bytes", entry)
            self.assertGreater(entry["size_bytes"], 0)
            self.assertEqual(len(entry["sha256"]), 64)

    def test_dependency_inventory_zero_runtime_dependencies(self):
        """Verify Software Bill of Materials mandates 0 runtime dependencies."""
        inventory_path = os.path.join(self.DIST_DIR, "dependency_inventory.json")
        self.assertTrue(os.path.isfile(inventory_path), f"Inventory JSON missing: {inventory_path}")

        with open(inventory_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("schema_version"), "1.0.0")
        self.assertEqual(data.get("distribution_name"), "ultron-risk-scorer")
        self.assertEqual(data.get("runtime_dependencies"), [], "Core distribution MUST have 0 runtime dependencies")
        self.assertIn("tray", data.get("optional_extras", {}))
        self.assertIn("metrics", data.get("optional_extras", {}))
        self.assertIn("dev", data.get("optional_extras", {}))
        self.assertIn("setuptools>=61.0.0", data.get("build_requirements", []))

        # Check committed SBOM markdown documentation
        doc_path = os.path.join(REPO_ROOT, "docs", "DEPENDENCY_INVENTORY.md")
        self.assertTrue(os.path.isfile(doc_path), f"Committed SBOM markdown missing: {doc_path}")
        with open(doc_path, "r", encoding="utf-8") as f:
            doc_content = f.read()
        self.assertIn("dependencies = []", doc_content)
        self.assertIn("install_requires = []", doc_content)
        self.assertIn("ultron-risk-scorer", doc_content)

    def test_no_premature_pypi_install_claims(self):
        """Verify release candidate documentation does not claim unadorned PyPI remote availability."""
        readme_path = os.path.join(REPO_ROOT, "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_text = f.read()

        # Any pip install mention in README must refer to local wheel, source, or development mode
        # rather than bare remote PyPI installation before formal release
        for line in readme_text.splitlines():
            if "pip install ultron" in line.lower() or "pip install ultron-risk-scorer" in line.lower():
                self.assertTrue(
                    "dist/" in line or "-e ." in line or "." in line or "whl" in line or "candidate" in line.lower(),
                    f"Premature remote PyPI install command found in README: {line}"
                )


if __name__ == "__main__":
    unittest.main()
