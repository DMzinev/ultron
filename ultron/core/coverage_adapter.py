"""
Ultron Coverage Adapter — Reads coverage.xml (Cobertura) and .coverage (SQLite)
from repository root when present. Graceful degradation when absent or corrupt.
"""
import os
import sqlite3
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger("ultron.coverage_adapter")

_COVERAGE_CACHE = {}


def _norm_path(p):
    """Normalize a file path to POSIX forward-slash relative form."""
    return os.path.normpath(p).replace("\\", "/").lstrip("./")


def find_coverage_file(repo_path):
    """Returns (format, path) or (None, None)."""
    xml_path = os.path.join(repo_path, "coverage.xml")
    if os.path.isfile(xml_path):
        return ("xml", xml_path)
    dot_path = os.path.join(repo_path, ".coverage")
    if os.path.isfile(dot_path):
        return ("sqlite", dot_path)
    return (None, None)


def parse_coverage_xml(xml_path):
    """Parse Cobertura XML. Returns {status, overall, files, source}."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        overall = float(root.get("line-rate", "0")) * 100.0
        files = {}
        for pkg in root.iter("package"):
            for cls in pkg.iter("class"):
                filename = cls.get("filename", "")
                if filename:
                    rate = float(cls.get("line-rate", "0")) * 100.0
                    files[_norm_path(filename)] = round(rate, 2)
        return {"status": "active", "overall": round(overall, 2), "files": files, "source": "coverage.xml"}
    except Exception as e:
        logger.info("Could not parse coverage.xml: %s", e)
        return {"status": "unavailable", "overall": None, "files": {}, "source": None}


def parse_dot_coverage(db_path):
    """Parse .coverage SQLite (coverage.py v5+). Returns tracked file list only."""
    try:
        # Windows-safe URI: convert backslashes to forward slashes
        abs_path = os.path.abspath(db_path).replace(os.sep, "/")
        uri = f"file:///{abs_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            cursor = conn.execute("SELECT path FROM file")
            tracked = [_norm_path(row[0]) for row in cursor.fetchall()]
            if not tracked:
                return {"status": "unavailable", "overall": None, "files": {}, "source": None}
            # .coverage stores line_bits (packed blobs), not line rates.
            # We can confirm files are tracked but cannot reliably extract percentages.
            files = {p: None for p in tracked}
            return {"status": "active", "overall": None, "files": files, "source": ".coverage"}
        finally:
            conn.close()
    except (sqlite3.Error, OSError, Exception) as e:
        logger.info("Could not parse .coverage SQLite: %s", e)
        return {"status": "unavailable", "overall": None, "files": {}, "source": None}


def get_coverage_data(repo_path):
    """Cached coverage lookup. Prefers XML over SQLite."""
    abs_repo = os.path.abspath(repo_path)
    if abs_repo in _COVERAGE_CACHE:
        return _COVERAGE_CACHE[abs_repo]

    fmt, path = find_coverage_file(abs_repo)
    if fmt == "xml":
        result = parse_coverage_xml(path)
    elif fmt == "sqlite":
        result = parse_dot_coverage(path)
    else:
        result = {"status": "unavailable", "overall": None, "files": {}, "source": None}

    _COVERAGE_CACHE[abs_repo] = result
    return result


def get_file_coverage(repo_path, file_path):
    """Lookup coverage for a specific file. Returns float or None."""
    data = get_coverage_data(repo_path)
    if data["status"] != "active":
        return None
    norm = _norm_path(file_path)
    files = data.get("files", {})
    # Try exact normalized path
    if norm in files:
        return files[norm]
    # Try basename match
    base = os.path.basename(norm)
    for k, v in files.items():
        if os.path.basename(k) == base:
            return v
    return None


def clear_cache():
    """Clear the coverage cache (for testing)."""
    _COVERAGE_CACHE.clear()
