"""
Ultron Unit Tests for RKM Database Integrity & Recovery
"""
import unittest
import os
import shutil
import tempfile
from ultron.core.rkm.integrity import RKMDatabaseIntegrity

class TestRKMIntegrity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_rkm.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_integrity_check_valid_db(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE test (id INT);")
        conn.close()

        ok, msg = RKMDatabaseIntegrity.verify_and_repair_database(self.db_path)
        self.assertTrue(ok)
        self.assertIn("passed", msg)
        self.assertTrue(os.path.exists(f"{self.db_path}.bak"))

    def test_corrupted_db_preservation(self):
        # Create corrupted non-SQLite file
        with open(self.db_path, "wb") as f:
            f.write(b"CORRUPTED_NON_SQLITE_BINARY_DATA")

        ok, msg = RKMDatabaseIntegrity.verify_and_repair_database(self.db_path)
        self.assertFalse(ok)
        self.assertIn("Corrupted DB preserved", msg)
        # Check that corrupted file was preserved with timestamp extension
        corrupted_files = [f for f in os.listdir(self.test_dir) if "corrupted" in f]
        self.assertGreater(len(corrupted_files), 0)

if __name__ == "__main__":
    unittest.main()
