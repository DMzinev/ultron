"""
Ultron RKM Database Integrity & Recovery Module
Campaign 20 — PRAGMA quick_check, Pre-Migration Backups, Corrupted DB Preservation
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime, timezone
from typing import Tuple

class RKMDatabaseIntegrity:
    @staticmethod
    def verify_and_repair_database(db_path: str) -> Tuple[bool, str]:
        """
        Verifies SQLite database integrity via PRAGMA quick_check.
        Creates pre-migration backup (rkm.db.bak).
        If corrupted, preserves file as rkm.db.corrupted.<timestamp> before clean re-initialization.
        """
        if not db_path or db_path == ":memory:":
            return True, "In-memory database."

        norm_path = os.path.normpath(os.path.abspath(db_path))
        db_dir = os.path.dirname(norm_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(norm_path):
            return True, "New database created."

        # Create pre-migration backup
        backup_path = f"{norm_path}.bak"
        try:
            shutil.copy2(norm_path, backup_path)
        except Exception as copy_err:
            sys.stderr.write(f"[RKM Integrity Warning] Could not create backup: {copy_err}\n")

        # Execute PRAGMA quick_check
        is_ok = False
        is_busy = False
        conn = None
        try:
            conn = sqlite3.connect(norm_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA quick_check;")
            row = cursor.fetchone()
            if row and row[0] == "ok":
                is_ok = True
        except sqlite3.OperationalError as op_err:
            # Concurrency lock / busy timeout: DO NOT TREAT AS CORRUPTION
            is_busy = True
            sys.stderr.write(f"[RKM Integrity Notice] Database lock/busy under concurrent access ({op_err}), skipping integrity check.\n")
        except Exception as check_err:
            sys.stderr.write(f"[RKM Integrity Error] Database corruption detected: {check_err}\n")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        if is_busy:
            return True, "Database busy under concurrent access. Preserved existing database."

        if is_ok:
            return True, "Database integrity check passed."

        # Handle Corruption — Preserve as rkm.db.corrupted.<timestamp> along with WAL/SHM companion files
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        corrupted_path = f"{norm_path}.corrupted.{ts}"
        try:
            shutil.move(norm_path, corrupted_path)
            for ext in ("-wal", "-shm"):
                comp = f"{norm_path}{ext}"
                if os.path.exists(comp):
                    try:
                        shutil.move(comp, f"{corrupted_path}{ext}")
                    except Exception:
                        pass
            sys.stderr.write(f"[RKM Integrity Action] Preserved corrupted database to: {corrupted_path}\n")
            return False, f"Corrupted DB preserved at {os.path.basename(corrupted_path)}. Re-initialized clean DB."
        except Exception as move_err:
            sys.stderr.write(f"[RKM Integrity Critical] Failed to move corrupted database: {move_err}\n")
            return False, f"Corruption recovery failed: {move_err}"
