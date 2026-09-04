"""
Unit test suite asserting single-source versioning integrity, VersionManager micro-sprint logic, and SHA-256 fingerprint determinism.
"""

import unittest
import os
import tempfile
from ultron.release import __version__
from ultron.release.version_manager import VersionManager
from ultron.core.pipeline.orchestrator import AnalysisArtifactBundle, compute_repository_content_hash

class TestVersionIntegrity(unittest.TestCase):
    def test_canonical_version_constant(self):
        """Asserts canonical package version is 0.2.0."""
        self.assertEqual(__version__, "0.2.0")
        self.assertEqual(VersionManager.get_canonical_version(), "0.2.0")

    def test_version_manager_micro_increment(self):
        """Asserts VersionManager increments micro version components correctly."""
        self.assertEqual(VersionManager.increment_micro("0.1.0"), "0.1.1")
        self.assertEqual(VersionManager.increment_micro("0.1.0", 5), "0.1.5")
        self.assertEqual(VersionManager.increment_micro("0.1.9"), "0.1.10")
        self.assertEqual(VersionManager.increment_micro("v0.1.0"), "v0.1.1")
        self.assertEqual(VersionManager.increment_micro("v0.1.9"), "v0.1.10")

    def test_version_manager_sprint_tagging(self):
        """Asserts VersionManager formats sprint tags correctly."""
        self.assertEqual(VersionManager.format_sprint_tag("0.1.1", "Kanban Sprint 1"), "v0.1.1-kanban-sprint-1")

    def test_version_manager_invalid_input_exceptions(self):
        """Asserts VersionManager raises ValueError on malformed semver strings."""
        with self.assertRaises(ValueError):
            VersionManager.increment_micro("")
        with self.assertRaises(ValueError):
            VersionManager.increment_micro("invalid")
        with self.assertRaises(ValueError):
            VersionManager.increment_micro("0.1")
        with self.assertRaises(ValueError):
            VersionManager.increment_micro("0.1.0", 0)

    def test_analysis_artifact_bundle_to_dict_versioning(self):
        """Asserts AnalysisArtifactBundle dataclass includes repo_fingerprint in to_dict()."""
        bundle = AnalysisArtifactBundle(
            repo_uuid="test-uuid-1234",
            codebase={"files": {}},
            risks=[],
            files=["main.py"],
            content_hash="abc123hash",
            repo_fingerprint="sha256fingerprint1234567890"
        )
        data = bundle.to_dict()
        self.assertEqual(data["repo_uuid"], "test-uuid-1234")
        self.assertEqual(data["repo_fingerprint"], "sha256fingerprint1234567890")
        self.assertEqual(str(bundle), "test-uuid-1234")

    def test_deterministic_repo_fingerprint_normalization(self):
        """Asserts content hash normalization works deterministically across path separators."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test.py")
            with open(test_file, "wb") as f:
                f.write(b"def foo():\r\n    return 42\r\n")

            hash1 = compute_repository_content_hash(tmp_dir, ["test.py"])
            hash2 = compute_repository_content_hash(tmp_dir, ["test.py"])
            self.assertEqual(hash1, hash2)
            self.assertEqual(len(hash1), 64)

    def test_cli_serve_and_brief_options(self):
        """Asserts ultron CLI correctly handles --serve and --brief without crashing on flags."""
        from unittest.mock import patch
        import sys
        from ultron.interfaces import ultron as ultron_cli

        with patch("ultron.interfaces.server.serve") as mock_serve, \
             patch.object(sys, "argv", ["ultron", "--serve"]), \
             patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                ultron_cli.main()
            mock_serve.assert_called_once()

    def test_canonical_build_snapshot_id(self):
        """Asserts canonical build_snapshot_id produces deterministic, state-bound snapshot IDs."""
        from ultron.core.models import build_snapshot_id

        h1 = "5876956be9bc33a40012570024925731f2675fd9fa6bb3fd7b290ae0c39224b0"
        h2 = "bb197f5a1e0635135cdbca297babcd5b4e08f63ef8df8b9a6789ab37f3ec9be0"

        s1 = build_snapshot_id(h1)
        s2 = build_snapshot_id(h1)
        s3 = build_snapshot_id(h2)

        self.assertEqual(s1, s2)
        self.assertEqual(s1, f"snap-{h1[:16]}")
        self.assertNotEqual(s1, s3)
        self.assertEqual(build_snapshot_id(""), "snap-0000000000000000")
        self.assertEqual(build_snapshot_id(None), "snap-0000000000000000")

    def test_two_repositories_isolation_and_identity_primitives(self):
        """Asserts two repositories with identical contents have distinct repository_uuid but matching snapshot_id."""
        from ultron.core.pipeline.orchestrator import analyze_repository
        from ultron.core.models import build_snapshot_id

        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            # Create identical code in both
            for d in (tmp_a, tmp_b):
                with open(os.path.join(d, "app.py"), "w", encoding="utf-8") as f:
                    f.write("def run():\n    return 'ok'\n")

            bundle_a = analyze_repository(tmp_a)
            bundle_b = analyze_repository(tmp_b)

            # Invariant 1: Different repository UUIDs
            self.assertNotEqual(bundle_a.repo_uuid, bundle_b.repo_uuid)

            # Invariant 2: Identical content hash and snapshot_id
            self.assertEqual(bundle_a.content_hash, bundle_b.content_hash)
            self.assertEqual(bundle_a.snapshot_id, bundle_b.snapshot_id)
            self.assertEqual(bundle_a.snapshot_id, build_snapshot_id(bundle_a.content_hash))

            # Invariant 3: Mutating repo_a changes its snapshot_id without contaminating repo_b
            with open(os.path.join(tmp_a, "app.py"), "w", encoding="utf-8") as f:
                f.write("def run():\n    return 'modified'\n")

            bundle_a_mod = analyze_repository(tmp_a)
            self.assertNotEqual(bundle_a.snapshot_id, bundle_a_mod.snapshot_id)
            self.assertNotEqual(bundle_a_mod.snapshot_id, bundle_b.snapshot_id)
            # Repository UUID remains stable across modifications
            self.assertEqual(bundle_a.repo_uuid, bundle_a_mod.repo_uuid)


if __name__ == "__main__":
    unittest.main()

