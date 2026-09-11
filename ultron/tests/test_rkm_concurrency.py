"""
ultron/tests/test_rkm_concurrency.py

High-Concurrency Stress & Invariant Test Suite for Task P4-A3:
Validates SQLite WAL Mode, Synchronous Normal, Native Immediate Isolation,
and Zero-Deadlock Multi-Threaded Concurrent Operations.
"""

import os
import time
import shutil
import tempfile
import threading
import unittest
import sqlite3

from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RepositoryMetadata, AnalysisRun


class TestRKMConcurrency(unittest.TestCase):
    """Hermetic multi-threaded stress and concurrency test suite for RepositoryStore."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "concurrency_test.db")
        # Initialize the database schema and baseline metadata
        with RepositoryStore(self.db_path) as store:
            with store.transaction():
                store.save_metadata(RepositoryMetadata(
                    id=1,
                    repository_uuid="repo-uuid-concurrency",
                    name="concurrency_repo",
                    root_path="/repo",
                    language="python",
                    size=1000,
                    rkm_version="1.3.0",
                    minimum_reader_version="1.0.0",
                    maximum_writer_version="1.3.0",
                    latest_analysis_run_id=None,
                ))

    def tearDown(self):
        # Allow any pending file system write flush to settle before removing tempdir on Windows
        time.sleep(0.05)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_wal_pragmas_configured(self):
        """Verify journal_mode=WAL, synchronous=NORMAL, busy_timeout>=5000, and isolation_level=IMMEDIATE."""
        with RepositoryStore(self.db_path) as store:
            journal_mode = store.conn.execute("PRAGMA journal_mode;").fetchone()[0]
            self.assertEqual(journal_mode.lower(), "wal", "Expected journal_mode to be WAL")

            synchronous = int(store.conn.execute("PRAGMA synchronous;").fetchone()[0])
            self.assertEqual(synchronous, 1, "Expected synchronous mode to be 1 (NORMAL)")

            busy_timeout = int(store.conn.execute("PRAGMA busy_timeout;").fetchone()[0])
            self.assertGreaterEqual(busy_timeout, 5000, "Expected busy_timeout >= 5000 ms")

            self.assertEqual(
                store.conn.isolation_level,
                "IMMEDIATE",
                "Expected isolation_level to be 'IMMEDIATE' for immediate write locking",
            )

    def test_multithreaded_concurrent_writes(self):
        """Verify 10 concurrent threads can write simultaneous transactions with zero lock errors."""
        num_threads = 10
        writes_per_thread = 10
        errors = []

        def worker(thread_idx: int):
            try:
                with RepositoryStore(self.db_path) as store:
                    for i in range(writes_per_thread):
                        with store.transaction():
                            run = AnalysisRun(
                                id=None,
                                repository_id=1,
                                timestamp=f"2026-09-11T12:{thread_idx:02d}:{i:02d}",
                                duration=0.01,
                                engine_version="1.4.0",
                                rkm_version="1.3.0",
                                content_hash=f"hash-{thread_idx}-{i}",
                                previous_run_id=None,
                                rule_pack_version="1.0.0",
                                semantic_hash=f"sem-{thread_idx}-{i}",
                                archived=0,
                                semantic_hash_strategy="ast_structure",
                            )
                            store.save_analysis_run(run)
                        time.sleep(0.002)
            except Exception as exc:
                errors.append((thread_idx, str(exc)))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        self.assertEqual(len(errors), 0, f"Encountered concurrent write errors: {errors}")

        with RepositoryStore(self.db_path) as store:
            row_count = store.conn.execute("SELECT count(*) FROM rkm_analysis_runs").fetchone()[0]
            expected_total = num_threads * writes_per_thread
            self.assertEqual(row_count, expected_total, f"Expected {expected_total} runs, found {row_count}")

    def test_concurrent_readers_and_writers(self):
        """Verify readers do not block writers and writers do not block readers under parallel execution."""
        num_writers = 5
        num_readers = 10
        iterations = 15
        errors = []

        def writer_worker(w_id: int):
            try:
                with RepositoryStore(self.db_path) as store:
                    for i in range(iterations):
                        with store.transaction():
                            run = AnalysisRun(
                                id=None,
                                repository_id=1,
                                timestamp=f"2026-09-11T13:{w_id:02d}:{i:02d}",
                                duration=0.01,
                                engine_version="1.4.0",
                                rkm_version="1.3.0",
                                content_hash=f"writer-hash-{w_id}-{i}",
                                previous_run_id=None,
                                rule_pack_version="1.0.0",
                                semantic_hash=f"writer-sem-{w_id}-{i}",
                                archived=0,
                                semantic_hash_strategy="ast_structure",
                            )
                            store.save_analysis_run(run)
                        time.sleep(0.002)
            except Exception as exc:
                errors.append(("writer", w_id, str(exc)))

        def reader_worker(r_id: int):
            try:
                with RepositoryStore(self.db_path) as store:
                    for _ in range(iterations):
                        migrations = store.get_applied_migrations()
                        self.assertGreater(len(migrations), 0)
                        schema_v = store.schema_version()
                        self.assertIsNotNone(schema_v)
                        count = store.conn.execute("SELECT count(*) FROM rkm_analysis_runs").fetchone()[0]
                        self.assertGreaterEqual(count, 0)
                        time.sleep(0.002)
            except Exception as exc:
                errors.append(("reader", r_id, str(exc)))

        threads = []
        for w in range(num_writers):
            threads.append(threading.Thread(target=writer_worker, args=(w,)))
        for r in range(num_readers):
            threads.append(threading.Thread(target=reader_worker, args=(r,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")

    def test_transaction_immediate_locking(self):
        """Verify transaction atomicity, rollback on exception, and immediate TypeError on invalid argument."""
        with RepositoryStore(self.db_path) as store:
            with self.assertRaises(TypeError):
                store.transaction(None)

        with RepositoryStore(self.db_path) as store:
            initial_count = store.conn.execute("SELECT count(*) FROM rkm_analysis_runs").fetchone()[0]
            with self.assertRaises(RuntimeError):
                with store.transaction():
                    store.save_analysis_run(AnalysisRun(
                        id=None,
                        repository_id=1,
                        timestamp="2026-09-11T14:00:00",
                        duration=0.01,
                        engine_version="1.4.0",
                        rkm_version="1.3.0",
                        content_hash="rollback-hash",
                        previous_run_id=None,
                        rule_pack_version="1.0.0",
                        semantic_hash="rollback-sem",
                        archived=0,
                        semantic_hash_strategy="ast_structure",
                    ))
                    raise RuntimeError("Simulated transaction failure")

            after_count = store.conn.execute("SELECT count(*) FROM rkm_analysis_runs").fetchone()[0]
            self.assertEqual(after_count, initial_count, "Rolled back transaction must not persist records")

    def test_busy_timeout_resilience(self):
        """Verify that concurrent connections wait gracefully up to busy_timeout without throwing database locked."""
        concurrency_success = []
        errors = []

        def holding_worker():
            try:
                c1 = sqlite3.connect(self.db_path, timeout=10.0, isolation_level="IMMEDIATE")
                c1.execute("BEGIN IMMEDIATE")
                time.sleep(0.15)
                c1.execute(
                    "INSERT INTO rkm_analysis_runs "
                    "(repository_id, timestamp, duration, engine_version, rkm_version, content_hash, "
                    "previous_run_id, rule_pack_version, semantic_hash, archived, semantic_hash_strategy) "
                    "VALUES (1, '2026-09-11T15:00:00', 0.1, '1.4.0', '1.3.0', 'h1', NULL, '1.0', 's1', 0, 'ast')"
                )
                c1.commit()
                c1.close()
                concurrency_success.append("holder")
            except Exception as e:
                errors.append(("holder", str(e)))

        def waiting_worker():
            time.sleep(0.03)
            try:
                with RepositoryStore(self.db_path) as store:
                    with store.transaction():
                        store.save_analysis_run(AnalysisRun(
                            id=None,
                            repository_id=1,
                            timestamp="2026-09-11T15:00:01",
                            duration=0.1,
                            engine_version="1.4.0",
                            rkm_version="1.3.0",
                            content_hash="h2",
                            previous_run_id=None,
                            rule_pack_version="1.0.0",
                            semantic_hash="s2",
                            archived=0,
                            semantic_hash_strategy="ast_structure",
                        ))
                    concurrency_success.append("waiter")
            except Exception as e:
                errors.append(("waiter", str(e)))

        t1 = threading.Thread(target=holding_worker)
        t2 = threading.Thread(target=waiting_worker)
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        self.assertEqual(len(errors), 0, f"Busy timeout should allow waiter to succeed without error: {errors}")
        self.assertEqual(len(concurrency_success), 2, "Both holder and waiter should complete successfully")

    def test_context_manager_lifecycle(self):
        """Verify with RepositoryStore(db_path) as store automatically closes connection and is idempotent."""
        store_ref = None
        with RepositoryStore(self.db_path) as store:
            self.assertIsNotNone(store.conn)
            store_ref = store
            res = store.conn.execute("SELECT 1").fetchone()
            self.assertEqual(res[0], 1)

        self.assertIsNone(store_ref.conn, "store.conn must be None after context manager exit")

        store_ref.close()
        self.assertIsNone(store_ref.conn)


if __name__ == "__main__":
    unittest.main()
