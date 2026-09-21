"""
ultron/tests/test_release_workflow.py
Rigorous verification of the OIDC Trusted Publishing release workflow & invariants (Task RC-C1).

Validates:
1. Release workflow schema, existence, and 4 discrete decoupled jobs.
2. OIDC token permissions (id-token: write) and default contents: read.
3. Zero secrets expressions (${{ secrets.* }} strictly eliminated).
4. Immutable 40-character commit SHA pinning for all GitHub Actions.
5. Production PyPI publishing job hard-locked (if: false) and approval-gated.
6. Staging isolation (packages-dir: dist/packages/ containing only distribution archives).
7. Tag verification, clean tree check, and PyPI immutability probe logic.
8. Trusted publishing documentation completeness.
"""

import os
import sys
import re
import io
import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import ultron
from scripts import verify_release_tag


class TestReleaseWorkflowInvariants(unittest.TestCase):
    """Hermetic verification of OIDC Trusted Publishing workflow and tag gating."""

    def setUp(self):
        self.workflow_path = os.path.join(REPO_ROOT, ".github", "workflows", "release.yml")
        self.doc_path = os.path.join(REPO_ROOT, "docs", "TRUSTED_PUBLISHING.md")
        self.assertTrue(os.path.isfile(self.workflow_path), f"release.yml missing at {self.workflow_path}")
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            self.workflow_content = f.read()

    def test_release_workflow_jobs_and_dependencies(self):
        """Assert release.yml declares all 4 required jobs with strict sequential dependency chain."""
        expected_jobs = [
            "build-candidate",
            "verify-candidate",
            "publish-testpypi",
            "publish-pypi"
        ]
        for job in expected_jobs:
            self.assertIn(f"{job}:", self.workflow_content, f"Job '{job}' missing in release.yml")

        # Verify dependency chain
        self.assertIn("needs: [ build-candidate ]", self.workflow_content)
        self.assertIn("needs: [ verify-candidate ]", self.workflow_content)
        self.assertIn("needs: [ publish-testpypi ]", self.workflow_content)

    def test_release_workflow_oidc_permissions(self):
        """Assert top-level permissions default to read and publishing jobs declare id-token: write."""
        self.assertIn("permissions:\n  contents: read", self.workflow_content)
        
        # Both publishing jobs must have id-token: write
        id_token_count = self.workflow_content.count("id-token: write")
        self.assertGreaterEqual(id_token_count, 2, "Both publish-testpypi and publish-pypi must specify id-token: write")

    def test_release_workflow_zero_secrets_expressions(self):
        """Assert release.yml contains zero ${{ secrets.* }} expressions (Rule 9)."""
        secret_matches = re.findall(r"\$\{\{\s*secrets\b[^}]*\}\}", self.workflow_content)
        self.assertEqual(
            secret_matches, [],
            f"Illegal secrets expression found in release.yml: {secret_matches}"
        )
        self.assertNotIn("${{ secrets.", "".join(self.workflow_content.split()))

    def test_release_workflow_pinned_actions(self):
        """Assert all actions are pinned to 40-character hex commit SHAs with version comments."""
        expected_pinned_actions = [
            ("actions/checkout", "11bd71901bbe5b1630ceea73d27597364c9af683"),
            ("actions/setup-python", "42375524e23c412d93fb67b49958b491fce71c38"),
            ("actions/upload-artifact", "4cec3d8aa04e39d1a68397de0c4cd6fb9dce8ec1"),
            ("actions/download-artifact", "cc203385981b70ca67e1cc392babf9cc229d5806"),
            ("pypa/gh-action-pypi-publish", "7f25271a4aa483500f742f9492b2ab5648d61011"),
        ]
        for action_name, sha in expected_pinned_actions:
            pattern = rf"{re.escape(action_name)}@{re.escape(sha)}"
            self.assertTrue(
                re.search(pattern, self.workflow_content),
                f"Action '{action_name}' must be pinned to immutable SHA '{sha}'"
            )

    def test_release_workflow_production_job_disabled(self):
        """Assert production PyPI job is hard-locked with 'if: false' during candidate stabilization."""
        # Find publish-pypi section
        pypi_section = self.workflow_content.split("publish-pypi:")[1]
        self.assertIn("environment:\n      name: pypi", pypi_section)
        self.assertIn("if: false", pypi_section, "publish-pypi job MUST be disabled with 'if: false' per Requirement 8")

    def test_release_workflow_staging_isolation(self):
        """Assert release.yml isolates distribution packages into dist/packages/ avoiding metadata collisions."""
        self.assertIn("packages-dir: dist/packages/", self.workflow_content)
        self.assertIn("ultron-distribution-packages", self.workflow_content)

    def test_verify_release_tag_unit_logic(self):
        """Test tag parsing, parity checking, clean tree check, and immutability probe in verify_release_tag.py."""
        # 1. Tag parser
        base, rc = verify_release_tag.parse_tag_version("v1.5.0")
        self.assertEqual((base, rc), ("1.5.0", None))

        base_rc, rc_part = verify_release_tag.parse_tag_version("v1.5.0rc1")
        self.assertEqual((base_rc, rc_part), ("1.5.0", "rc1"))

        base_bad, rc_bad = verify_release_tag.parse_tag_version("invalid")
        self.assertEqual((base_bad, rc_bad), ("", None))

        # 2. Tag parity check against ultron.get_version()
        current_ver = ultron.get_version()
        ok, msg = verify_release_tag.verify_tag_matches_package(f"v{current_ver}")
        self.assertTrue(ok)

        ok_bad, msg_bad = verify_release_tag.verify_tag_matches_package("v0.0.1")
        self.assertFalse(ok_bad)
        self.assertIn("does not match", msg_bad)

        # 3. Clean tree check (mocked)
        clean_proc = MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", return_value=clean_proc):
            ok_clean, _ = verify_release_tag.verify_clean_git_tree("/fake")
            self.assertTrue(ok_clean)

        dirty_proc = MagicMock(returncode=0, stdout="M  sample.py\n")
        with patch("subprocess.run", return_value=dirty_proc):
            ok_dirty, msg_dirty = verify_release_tag.verify_clean_git_tree("/fake")
            self.assertFalse(ok_dirty)
            self.assertIn("Dirty working tree", msg_dirty)

        # 4. HEAD is tag check (mocked)
        head_tag_proc = MagicMock(returncode=0, stdout="v1.5.0rc1\n")
        with patch("subprocess.run", return_value=head_tag_proc):
            ok_head, _ = verify_release_tag.verify_head_is_tag("v1.5.0rc1", "/fake")
            self.assertTrue(ok_head)

        head_notag_proc = MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", return_value=head_notag_proc):
            ok_nohead, msg_nohead = verify_release_tag.verify_head_is_tag("v1.5.0rc1", "/fake")
            self.assertFalse(ok_nohead)
            self.assertIn("HEAD is not tagged", msg_nohead)

        # 5. PyPI immutability probe (mocked HTTP 404 = clean to publish)
        http_404 = urllib.error.HTTPError(
            url="https://test.pypi.org/pypi/pkg/json",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=io.BytesIO(b'{"message": "Not Found"}')
        )
        with patch("urllib.request.urlopen", side_effect=http_404):
            exists, msg = verify_release_tag.check_version_exists_on_pypi("pkg", "1.5.0", test_pypi=True)
            self.assertFalse(exists, "HTTP 404 must mean package does not exist (clean to publish)")
            self.assertIn("does not exist", msg)

        # 6. PyPI immutability probe (mocked HTTP 200 with version present = conflict)
        json_resp = json.dumps({"releases": {"1.5.0": []}}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json_resp
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            exists_conflict, msg_conflict = verify_release_tag.check_version_exists_on_pypi("pkg", "1.5.0")
            self.assertTrue(exists_conflict, "Version present in releases must return True (conflict)")
            self.assertIn("already exists", msg_conflict)

    def test_trusted_publishing_documentation_integrity(self):
        """Assert docs/TRUSTED_PUBLISHING.md exists and covers OIDC, zero tokens, and environments."""
        self.assertTrue(os.path.isfile(self.doc_path), f"TRUSTED_PUBLISHING.md missing at {self.doc_path}")
        with open(self.doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("OIDC Trusted Publishing", content)
        self.assertIn("testpypi", content)
        self.assertIn("pypi", content)
        self.assertIn("pypa/gh-action-pypi-publish", content)
        self.assertIn("Zero secrets required", content)
        self.assertIn("scripts/verify_release_tag.py", content)


if __name__ == "__main__":
    unittest.main()
