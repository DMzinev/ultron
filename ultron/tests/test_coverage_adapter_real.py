"""
ultron/tests/test_coverage_adapter_real.py

End-to-end real coverage artifact validation suite for Task P3-B3 per docs/AGENT_EXECUTION_PLAN_PHASE3.md:
"Coverage Adapter Validated Against Real Coverage Output"

Validates that ultron/core/coverage_adapter.py accurately and reliably ingests genuine,
authentic artifacts produced by Coverage.py 7.16.0 (coverage.xml, coverage.json, and .coverage)
on a real multi-module Python fixture repository (ultron/tests/fixtures/real_coverage_repo).

Key Assertions:
1. Genuine Cobertura XML parsing extracts exact overall rate (71.43%) and per-file rates (string_ops: 100%, math_ops: 75%, dead_code: 0%).
2. Genuine Coverage.py JSON parsing extracts identical overall and per-file percentages.
3. Genuine .coverage SQLite parsing tracks all 3 modules.
4. Format precedence strictly enforces JSON > XML > SQLite.
5. Downstream risk integration confirms coverage signal activation in scoring.py (tier: VERIFIED, weight: 0.25)
   and numerical risk score reduction in risk_intelligence.py (100% coverage yields norm_cov 0.0 vs 0% coverage norm_cov 100.0).
6. Graceful degradation on corrupted or truncated artifacts.
"""

import os
import sys
import json
import shutil
import sqlite3
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from ultron.core import coverage_adapter
from ultron.core import analyzer
from ultron.core.risk import scoring
from ultron.core.rkm import risk_intelligence


class TestCoverageAdapterReal(unittest.TestCase):
    """Hermetic unit test suite validating genuine Coverage.py 7.16.0 artifacts."""

    @classmethod
    def setUpClass(cls):
        cls.fixture_repo = os.path.abspath(
            os.path.join(REPO_ROOT, "ultron", "tests", "fixtures", "real_coverage_repo")
        )
        cls.xml_path = os.path.join(cls.fixture_repo, "coverage.xml")
        cls.json_path = os.path.join(cls.fixture_repo, "coverage.json")
        cls.sqlite_path = os.path.join(cls.fixture_repo, ".coverage")

        # Verify real artifacts exist and are non-empty
        for p in (cls.xml_path, cls.json_path, cls.sqlite_path):
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise FileNotFoundError(f"Missing authentic coverage fixture artifact: {p}")

    def setUp(self):
        coverage_adapter.clear_cache()

    def tearDown(self):
        coverage_adapter.clear_cache()

    # -----------------------------------------------------------------------
    # 1. Genuine Cobertura XML Validation
    # -----------------------------------------------------------------------

    def test_real_coverage_xml_exact_metrics(self):
        """Assert parse_coverage_xml extracts exact metrics from authentic coverage.xml."""
        res = coverage_adapter.parse_coverage_xml(self.xml_path)

        self.assertEqual(res["status"], "active")
        self.assertEqual(res["source"], "coverage.xml")
        self.assertAlmostEqual(res["overall"], 71.43, delta=0.1)

        files = res.get("files", {})
        self.assertIn("string_ops.py", files)
        self.assertIn("math_ops.py", files)
        self.assertIn("dead_code.py", files)

        # string_ops.py has 100% coverage (4 of 4 statements)
        self.assertEqual(files["string_ops.py"], 100.0)
        # math_ops.py has 75% coverage (6 of 8 statements; 1 branch and 1 uncovered func)
        self.assertEqual(files["math_ops.py"], 75.0)
        # dead_code.py has 0% coverage (0 of 2 statements)
        self.assertEqual(files["dead_code.py"], 0.0)

    # -----------------------------------------------------------------------
    # 2. Genuine Coverage.py JSON Validation
    # -----------------------------------------------------------------------

    def test_real_coverage_json_exact_metrics(self):
        """Assert parse_coverage_json extracts identical metrics from authentic coverage.json."""
        res = coverage_adapter.parse_coverage_json(self.json_path)

        self.assertEqual(res["status"], "active")
        self.assertEqual(res["source"], "coverage.json")
        self.assertAlmostEqual(res["overall"], 71.43, delta=0.1)

        files = res.get("files", {})
        self.assertEqual(files.get("string_ops.py"), 100.0)
        self.assertEqual(files.get("math_ops.py"), 75.0)
        self.assertEqual(files.get("dead_code.py"), 0.0)

    # -----------------------------------------------------------------------
    # 3. Genuine .coverage SQLite Validation
    # -----------------------------------------------------------------------

    def test_real_dot_coverage_sqlite_tracked_files(self):
        """Assert parse_dot_coverage identifies all 3 tracked files in authentic .coverage SQLite."""
        res = coverage_adapter.parse_dot_coverage(self.sqlite_path)

        self.assertEqual(res["status"], "active")
        self.assertEqual(res["source"], ".coverage")
        self.assertIsNone(res["overall"])

        files = res.get("files", {})
        self.assertIn("string_ops.py", files)
        self.assertIn("math_ops.py", files)
        self.assertIn("dead_code.py", files)
        # In .coverage SQLite, per-file percentages are None (tracked status only)
        self.assertIsNone(files["string_ops.py"])

    # -----------------------------------------------------------------------
    # 4. Format Precedence Order (JSON > XML > SQLite)
    # -----------------------------------------------------------------------

    def test_format_preference_order(self):
        """Assert get_coverage_data strictly prefers JSON over XML over SQLite."""
        with tempfile.TemporaryDirectory(prefix="ultron_cov_precedence_") as tmp_dir:
            tmp_json = os.path.join(tmp_dir, "coverage.json")
            tmp_xml = os.path.join(tmp_dir, "coverage.xml")
            tmp_sqlite = os.path.join(tmp_dir, ".coverage")

            shutil.copyfile(self.json_path, tmp_json)
            shutil.copyfile(self.xml_path, tmp_xml)
            shutil.copyfile(self.sqlite_path, tmp_sqlite)

            # 1. All 3 present -> JSON wins
            coverage_adapter.clear_cache()
            res1 = coverage_adapter.get_coverage_data(tmp_dir)
            self.assertEqual(res1["source"], "coverage.json")
            self.assertEqual(res1["files"]["string_ops.py"], 100.0)

            # 2. JSON removed -> XML wins
            os.remove(tmp_json)
            coverage_adapter.clear_cache()
            res2 = coverage_adapter.get_coverage_data(tmp_dir)
            self.assertEqual(res2["source"], "coverage.xml")
            self.assertEqual(res2["files"]["string_ops.py"], 100.0)

            # 3. XML removed -> SQLite wins
            os.remove(tmp_xml)
            coverage_adapter.clear_cache()
            res3 = coverage_adapter.get_coverage_data(tmp_dir)
            self.assertEqual(res3["source"], ".coverage")

            # 4. SQLite removed -> unavailable
            os.remove(tmp_sqlite)
            coverage_adapter.clear_cache()
            res4 = coverage_adapter.get_coverage_data(tmp_dir)
            self.assertEqual(res4["status"], "unavailable")

    # -----------------------------------------------------------------------
    # 5. Dual Risk Scoring & Intelligence Integration
    # -----------------------------------------------------------------------

    def test_real_coverage_integration_with_risk_scoring(self):
        """Assert coverage signal activates in scoring.py and reduces risk in risk_intelligence.py."""
        # 1. scoring.evaluate_risks on real_coverage_repo
        codebase = analyzer.analyze_directory(self.fixture_repo)
        target_files = ["string_ops.py", "dead_code.py"]
        risks = scoring.evaluate_risks(
            codebase=codebase,
            target_files=target_files,
            repo_path=self.fixture_repo,
        )
        self.assertGreaterEqual(len(risks), 2)

        for packet in risks:
            signals = getattr(packet, "signals", {})
            cov_signal = signals.get("coverage", {})
            self.assertEqual(cov_signal.get("status"), "active")
            self.assertEqual(cov_signal.get("weight"), 0.25)
            self.assertEqual(cov_signal.get("tier"), "VERIFIED")

        # 2. risk_intelligence.compute_risk_profile
        prof_string = risk_intelligence.compute_risk_profile(
            entity_id="string_ops.py",
            complexity=1.0,
            coupling_fanout=0,
            repo_path=self.fixture_repo,
        )
        prof_dead = risk_intelligence.compute_risk_profile(
            entity_id="dead_code.py",
            complexity=1.0,
            coupling_fanout=0,
            repo_path=self.fixture_repo,
        )

        # string_ops has 100% coverage -> eff_coverage=100.0 -> norm_cov=0.0 -> cov_contrib=0.0
        # dead_code has 0% coverage -> eff_coverage=0.0 -> norm_cov=100.0 -> cov_contrib=25.0
        # Given equal complexity and coupling, covered code must have strictly lower risk score
        self.assertLess(
            prof_string.score,
            prof_dead.score,
            f"Expected string_ops ({prof_string.score}) to have lower risk score than dead_code ({prof_dead.score})",
        )
        self.assertEqual(prof_string.confidence_vector["signals_block"]["coverage"]["status"], "active")
        self.assertEqual(prof_dead.confidence_vector["signals_block"]["coverage"]["status"], "active")
        self.assertEqual(prof_string.confidence_vector["coverage"], 1.0)

    # -----------------------------------------------------------------------
    # 6. Graceful Failure on Corrupt and Empty Artifacts
    # -----------------------------------------------------------------------

    def test_corrupted_and_empty_real_artifacts_fail_gracefully(self):
        """Assert corrupted JSON, invalid XML, and empty databases return unavailable cleanly."""
        with tempfile.TemporaryDirectory(prefix="ultron_cov_corrupt_") as tmp_dir:
            bad_json = os.path.join(tmp_dir, "bad.json")
            with open(bad_json, "w", encoding="utf-8") as f:
                f.write('{"totals": { incomplete json')
            res_json = coverage_adapter.parse_coverage_json(bad_json)
            self.assertEqual(res_json["status"], "unavailable")

            bad_xml = os.path.join(tmp_dir, "bad.xml")
            with open(bad_xml, "w", encoding="utf-8") as f:
                f.write("<coverage> broken xml without end tag")
            res_xml = coverage_adapter.parse_coverage_xml(bad_xml)
            self.assertEqual(res_xml["status"], "unavailable")

            empty_db = os.path.join(tmp_dir, "empty.db")
            conn = sqlite3.connect(empty_db)
            conn.close()
            res_sqlite = coverage_adapter.parse_dot_coverage(empty_db)
            self.assertEqual(res_sqlite["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
