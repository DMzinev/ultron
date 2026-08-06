import os
import json
import sqlite3
from ultron.core.rkm.store import RepositoryStore
from ultron.core.rkm.schema import RKM_SCHEMA_VERSION

def export_snapshot(db_path: str, output_json_path: str):
    """
    Reads all SQLite RKM tables and exports them as a JSON snapshot.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            "metadata": "rkm_metadata",
            "analysis_runs": "rkm_analysis_runs",
            "files": "rkm_files",
            "symbols": "rkm_symbols",
            "dependencies": "rkm_dependencies",
            "facts": "rkm_facts",
            "provenance": "rkm_provenance",
            "interpretations": "rkm_interpretations",
            "recommendations": "rkm_recommendations",
            "metrics": "rkm_metrics",
            "architecture": "rkm_architecture"
        }
        
        snapshot = {
            "snapshot_version": "1.0.0",
            "rkm_version": RKM_SCHEMA_VERSION
        }
        
        for key, table_name in tables.items():
            try:
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                snapshot[key] = [dict(row) for row in cursor]
            except sqlite3.OperationalError:
                # If table doesn't exist (e.g. migration 002 provenance on older db), default to empty list
                snapshot[key] = []
                
        # Export single metadata row as a dictionary
        if snapshot["metadata"]:
            snapshot["metadata"] = snapshot["metadata"][0]
        else:
            snapshot["metadata"] = {}
            
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
            
    finally:
        conn.close()

def import_snapshot(db_path: str, input_json_path: str):
    """
    Imports RKM data from a JSON snapshot into the SQLite database.
    Performs atomic file swap replacement to prevent data corruption.
    """
    if not os.path.exists(input_json_path):
        raise ValueError(f"Snapshot file not found: {input_json_path}")
        
    try:
        with open(input_json_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except OSError as e:
        raise ValueError(f"Failed to read snapshot file: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON snapshot format: {e}")
        
    if not isinstance(snapshot, dict) or "snapshot_version" not in snapshot:
        raise ValueError("Invalid snapshot structure: missing metadata block")
        
    # Setup temporary database
    temp_db_path = db_path + ".temp"
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            temp_db_removal_failed = True

            
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    # Initialize the temp DB (runs migrations to ensure schemas are up-to-date)
    temp_store = RepositoryStore(temp_db_path)
    temp_store.close()
    
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        
        tables = [
            ("rkm_metadata", "metadata"),
            ("rkm_analysis_runs", "analysis_runs"),
            ("rkm_files", "files"),
            ("rkm_symbols", "symbols"),
            ("rkm_dependencies", "dependencies"),
            ("rkm_facts", "facts"),
            ("rkm_provenance", "provenance"),
            ("rkm_interpretations", "interpretations"),
            ("rkm_recommendations", "recommendations"),
            ("rkm_metrics", "metrics"),
            ("rkm_architecture", "architecture")
        ]
        
        with conn:
            for table_name, key in tables:
                data = snapshot.get(key, [])
                if key == "metadata":
                    if isinstance(data, dict) and data:
                        data = [data]
                    else:
                        data = []
                        
                for row_dict in data:
                    columns = list(row_dict.keys())
                    placeholders = ", ".join("?" for _ in columns)
                    sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    conn.execute(sql, tuple(row_dict[c] for c in columns))
                    
        conn.execute("PRAGMA foreign_keys = ON;")
    finally:
        conn.close()
        
    # Atomically replace live DB with imported temp DB
    # Note: caller must ensure all active store connections to db_path are closed!
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        db_removal_failed = True
        
    try:
        os.replace(temp_db_path, db_path)
    except OSError as e:
        # Cleanup temp file on failure
        try:
            os.remove(temp_db_path)
        except OSError:
            temp_cleanup_failed = True
        raise ValueError(f"Failed to atomically swap database file: {e}")

