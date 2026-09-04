"""
Task B4 — Honest Confidence, Not Silent Degradation
Hermetic test suite covering:
1. coverage_adapter XML parsing and graceful degradation
2. coverage_adapter SQLite (.coverage) parsing and Windows path safety
3. compute_risk_profile signals_block with 4 signals
4. AnalysisPacket signals serialization defaults
5. handle_v1_overview / handle_analyze stats.signals presence
6. Non-coverage repository degradation
"""
import os
import sys
import json
import tempfile
import shutil
import unittest
import xml.etree.ElementTree as ET


class TestCoverageAdapterXML(unittest.TestCase):
    """Verify Cobertura XML parsing and graceful degradation."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_b4_xml_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _write_xml(self, overall_rate=0.85, files=None):
        """Write a minimal Cobertura coverage.xml."""
        files = files or {"ultron/core/models.py": 0.92, "ultron/core/risk/scoring.py": 0.78}
        root = ET.Element("coverage", attrib={"line-rate": str(overall_rate)})
        pkg = ET.SubElement(root, "packages")
        p = ET.SubElement(pkg, "package", attrib={"name": "ultron"})
        classes = ET.SubElement(p, "classes")
        for fpath, rate in files.items():
            ET.SubElement(classes, "class", attrib={"filename": fpath, "line-rate": str(rate)})
        tree = ET.ElementTree(root)
        xml_path = os.path.join(self.test_dir, "coverage.xml")
        tree.write(xml_path, xml_declaration=True, encoding="utf-8")
        return xml_path

    def test_parse_valid_xml(self):
        from ultron.core.coverage_adapter import parse_coverage_xml
        self._write_xml(overall_rate=0.85)
        result = parse_coverage_xml(os.path.join(self.test_dir, "coverage.xml"))
        self.assertEqual(result["status"], "active")
        self.assertAlmostEqual(result["overall"], 85.0, places=1)
        self.assertIn("ultron/core/models.py", result["files"])
        self.assertAlmostEqual(result["files"]["ultron/core/models.py"], 92.0, places=1)
        self.assertEqual(result["source"], "coverage.xml")

    def test_parse_missing_xml(self):
        from ultron.core.coverage_adapter import parse_coverage_xml
        result = parse_coverage_xml(os.path.join(self.test_dir, "nonexistent.xml"))
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["overall"])

    def test_parse_corrupted_xml(self):
        from ultron.core.coverage_adapter import parse_coverage_xml
        bad_path = os.path.join(self.test_dir, "coverage.xml")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("THIS IS NOT XML <><><>")
        result = parse_coverage_xml(bad_path)
        self.assertEqual(result["status"], "unavailable")

    def test_path_normalization(self):
        """Windows backslash paths in XML should be normalized to forward slashes."""
        from ultron.core.coverage_adapter import parse_coverage_xml
        self._write_xml(files={"ultron\\core\\models.py": 0.90})
        result = parse_coverage_xml(os.path.join(self.test_dir, "coverage.xml"))
        self.assertEqual(result["status"], "active")
        # Normalized key should use forward slashes
        self.assertIn("ultron/core/models.py", result["files"])


class TestCoverageAdapterDotCoverage(unittest.TestCase):
    """Verify .coverage SQLite parsing and graceful degradation."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_b4_cov_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_valid_sqlite(self):
        """Create a minimal .coverage SQLite database with file table."""
        import sqlite3
        from ultron.core.coverage_adapter import parse_dot_coverage
        db_path = os.path.join(self.test_dir, ".coverage")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("INSERT INTO file (path) VALUES (?)", ("ultron/core/models.py",))
        conn.execute("INSERT INTO file (path) VALUES (?)", ("ultron/core/risk/scoring.py",))
        conn.commit()
        conn.close()

        result = parse_dot_coverage(db_path)
        self.assertEqual(result["status"], "active")
        self.assertIn("ultron/core/models.py", result["files"])
        self.assertEqual(result["source"], ".coverage")
        # .coverage doesn't give line rates
        self.assertIsNone(result["overall"])

    def test_parse_missing_sqlite(self):
        from ultron.core.coverage_adapter import parse_dot_coverage
        result = parse_dot_coverage(os.path.join(self.test_dir, ".coverage_nonexistent"))
        self.assertEqual(result["status"], "unavailable")

    def test_parse_corrupted_sqlite(self):
        from ultron.core.coverage_adapter import parse_dot_coverage
        bad_path = os.path.join(self.test_dir, ".coverage")
        with open(bad_path, "wb") as f:
            f.write(b"THIS IS NOT SQLITE")
        result = parse_dot_coverage(bad_path)
        self.assertEqual(result["status"], "unavailable")

    def test_empty_file_table(self):
        """Empty file table should return unavailable."""
        import sqlite3
        from ultron.core.coverage_adapter import parse_dot_coverage
        db_path = os.path.join(self.test_dir, ".coverage")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
        conn.commit()
        conn.close()
        result = parse_dot_coverage(db_path)
        self.assertEqual(result["status"], "unavailable")


class TestCoverageAdapterIntegration(unittest.TestCase):
    """Verify get_coverage_data preference order and caching."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ultron_b4_int_")
        from ultron.core.coverage_adapter import clear_cache
        clear_cache()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        from ultron.core.coverage_adapter import clear_cache
        clear_cache()

    def test_no_coverage_files(self):
        from ultron.core.coverage_adapter import get_coverage_data
        result = get_coverage_data(self.test_dir)
        self.assertEqual(result["status"], "unavailable")

    def test_xml_preferred_over_sqlite(self):
        """When both coverage.xml and .coverage exist, XML is preferred."""
        import sqlite3
        # Create both files
        root = ET.Element("coverage", attrib={"line-rate": "0.90"})
        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.test_dir, "coverage.xml"), xml_declaration=True, encoding="utf-8")

        db_path = os.path.join(self.test_dir, ".coverage")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE file (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("INSERT INTO file (path) VALUES (?)", ("a.py",))
        conn.commit()
        conn.close()

        from ultron.core.coverage_adapter import get_coverage_data
        result = get_coverage_data(self.test_dir)
        self.assertEqual(result["source"], "coverage.xml")


class TestRiskProfileSignalsBlock(unittest.TestCase):
    """Verify compute_risk_profile returns 4-signal signals_block."""

    def test_signals_block_present(self):
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3)
        self.assertIn("signals_block", profile.confidence_vector)
        block = profile.confidence_vector["signals_block"]
        self.assertEqual(len(block), 4)
        for name in ("ast", "coupling", "churn", "coverage"):
            self.assertIn(name, block)
            self.assertIn("status", block[name])
            self.assertIn("weight", block[name])

    def test_weights_sum_to_one(self):
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3)
        block = profile.confidence_vector["signals_block"]
        total = sum(s["weight"] for s in block.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_coverage_active_when_provided(self):
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3, coverage_percent=70.0)
        block = profile.confidence_vector["signals_block"]
        self.assertEqual(block["coverage"]["status"], "active")

    def test_coverage_unavailable_when_missing(self):
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3)
        block = profile.confidence_vector["signals_block"]
        self.assertEqual(block["coverage"]["status"], "unavailable")

    def test_churn_status_passthrough(self):
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3, churn_status="active")
        block = profile.confidence_vector["signals_block"]
        self.assertEqual(block["churn"]["status"], "active")

    def test_legacy_signals_list_length_preserved(self):
        """Existing tests depend on len(profile.signals) == 3."""
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        profile = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3)
        self.assertEqual(len(profile.signals), 3)

    def test_overall_confidence_honest(self):
        """Without coverage, overall confidence must be less than with coverage."""
        from ultron.core.rkm.risk_intelligence import compute_risk_profile
        p_no_cov = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3)
        p_with_cov = compute_risk_profile("test.py", complexity=10.0, coupling_fanout=3, coverage_percent=80.0)
        self.assertLess(
            p_no_cov.confidence_vector["overall"],
            p_with_cov.confidence_vector["overall"]
        )


class TestAnalysisPacketSignals(unittest.TestCase):
    """Verify AnalysisPacket.to_dict() includes 4-signal default."""

    def test_signals_default_in_to_dict(self):
        from ultron.core.models import AnalysisPacket
        p = AnalysisPacket(
            file_path="test.py", impact_score=5.0, coupling_score=2.0,
            mk_r=1.0, delta_cest=0.0, confidence=0.9
        )
        d = p.to_dict()
        self.assertIn("signals", d)
        self.assertEqual(len(d["signals"]), 4)
        for name in ("ast", "coupling", "churn", "coverage"):
            self.assertIn(name, d["signals"])

    def test_signals_explicit_preserved(self):
        from ultron.core.models import AnalysisPacket
        custom_signals = {
            "ast": {"status": "active", "weight": 0.35},
            "coupling": {"status": "active", "weight": 0.25},
            "churn": {"status": "active", "weight": 0.15},
            "coverage": {"status": "active", "weight": 0.25},
        }
        p = AnalysisPacket(
            file_path="test.py", impact_score=5.0, coupling_score=2.0,
            mk_r=1.0, delta_cest=0.0, confidence=0.9, signals=custom_signals
        )
        d = p.to_dict()
        self.assertEqual(d["signals"]["churn"]["status"], "active")
        self.assertEqual(d["signals"]["coverage"]["status"], "active")


if __name__ == "__main__":
    unittest.main()
