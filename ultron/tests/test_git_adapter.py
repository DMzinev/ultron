"""
Ultron Unit Tests — GitEvidenceAdapter Verification
Campaign 39 / v2.5 — Git Adapter & Non-Git Boundary Verification Suite
"""

import sys
import os
import tempfile
import unittest

from ultron.core.git_adapter import GitEvidenceAdapter


class TestGitEvidenceAdapter(unittest.TestCase):
    """Test suite verifying GitEvidenceAdapter behavior and non-git safety."""

    def test_non_git_repository_safety(self):
        """Test that non-git directory returns empty evidence list cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = GitEvidenceAdapter()
            evidence = adapter.parse_git_history(tmpdir)
            self.assertEqual(evidence, [])

    def test_non_existent_directory_safety(self):
        """Test non-existent path handling."""
        adapter = GitEvidenceAdapter()
        evidence = adapter.parse_git_history("/non/existent/path/for/ultron/test")
        self.assertEqual(evidence, [])


if __name__ == "__main__":
    unittest.main()
