import os
import sqlite3
import pathlib
import logging

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}

def get_recommendations(repo_path: str, limit: int = 20) -> dict:
    """
    Queries top-ranked architectural recommendations from the RKM database.
    Opens SQLite in read-only mode using URIs and handles uninitialized/missing DBs.
    """
    if not repo_path or not os.path.isdir(repo_path):
        repo_path = os.getcwd()

    db_path = os.path.join(repo_path, ".ultron", "repository.db")
    if not os.path.exists(db_path):
        return {
            "recommendations": [],
            "source": "fallback",
            "fallback_reason": "db_uninitialized"
        }

    try:
        db_uri = pathlib.Path(db_path).resolve().as_uri()
        conn = sqlite3.connect(f"{db_uri}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Query recommendations from latest run or table safely
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='recommendations' OR name='rkm_violations');")
        existing_tables = {row[0] for row in cursor.fetchall()}

        rows = []
        if "recommendations" in existing_tables:
            cursor.execute("""
                SELECT rule_id, violation_type, target_file, risk_reduction_score, severity, suggested_action
                FROM recommendations
            """)
            rows = cursor.fetchall()
        elif "rkm_violations" in existing_tables:
            cursor.execute("""
                SELECT e.rule_id, r.predicate_type, COALESCE(f.path, ''), 5.0, COALESCE(ri.severity, 'warning'), v.details
                FROM rkm_violations v
                JOIN rkm_evaluations e ON v.evaluation_id = e.id
                JOIN rkm_rules r ON e.rule_id = r.id
                LEFT JOIN rkm_rule_instances ri ON r.id = ri.rule_id
                LEFT JOIN rkm_files f ON v.file_id = f.id
            """)
            rows = cursor.fetchall()

        conn.close()

        recs = []
        for row in rows:
            rule_id, violation_type, target_file, score, severity, suggested_action = row
            score_val = float(score) if score is not None else 0.0
            sev_str = str(severity or "LOW").upper()
            recs.append({
                "rule_id": str(rule_id or ""),
                "violation_type": str(violation_type or ""),
                "target_file": str(target_file or ""),
                "risk_reduction_score": score_val,
                "severity": sev_str,
                "suggested_action": str(suggested_action or "")
            })

        # 4-tier deterministic sorting:
        # 1. risk_reduction_score (desc)
        # 2. severity rank (desc)
        # 3. target_file (asc)
        # 4. rule_id (asc)
        recs.sort(key=lambda r: (
            -r["risk_reduction_score"],
            -SEVERITY_ORDER.get(r["severity"], 0),
            r["target_file"],
            r["rule_id"]
        ))

        recs = recs[:limit]
        return {
            "status": "ok",
            "source": "rkm_db",
            "count": len(recs),
            "recommendations": recs
        }

    except Exception as e:
        logger.warning(f"[RecommendationService] Error querying RKM DB: {e}")
        return {
            "recommendations": [],
            "source": "fallback",
            "fallback_reason": "db_read_error"
        }
