"""
Ultron REST API — Shared Server State, Paths & Helpers
"""

import os
import sys
from urllib.parse import urlparse

LAST_ANALYSIS = {
    "file_path": None,
    "delta_i": 0.0,
    "mkr": 1.0,
    "delta_cest": 0.0
}

ACTIVE_JOB = {
    "status": "idle",
    "progress_step": "Done",
    "error": None,
    "cancel_requested": False,
    "job_id": None
}

PORT = 8000
LOOPBACK_HOST = "127.0.0.1"
BROWSE_DIALOG_TIMEOUT = 20

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".ultron")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def _is_local_origin(origin: str) -> bool:
    """Only same-machine origins may call the API."""
    if not origin:
        return False
    try:
        host = urlparse(origin).hostname
    except Exception:
        return False
    return host in ("127.0.0.1", "localhost", "::1")


def coerce_file_list(value) -> list:
    """Accept a JSON array, a comma-separated string, or nothing."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def validate_repo_path(base_dir: str, target_path: str) -> tuple[bool, str]:
    """
    Validates that target_path is inside base_dir and handles Windows drive letter boundaries.
    Returns (is_valid, abs_normalized_path).
    """
    try:
        norm_base = os.path.abspath(os.path.normpath(base_dir))
        norm_target = os.path.abspath(os.path.normpath(target_path))
        
        # Windows drive letter mismatch check (e.g. C:\ vs D:\)
        if os.name == 'nt':
            base_drive = os.path.splitdrive(norm_base)[0].lower()
            target_drive = os.path.splitdrive(norm_target)[0].lower()
            if base_drive and target_drive and base_drive != target_drive:
                return False, norm_target
                
        common = os.path.commonpath([norm_base, norm_target])
        if os.path.abspath(common) == norm_base:
            return True, norm_target
        return False, norm_target
    except (ValueError, OSError, Exception):
        return False, os.path.abspath(os.path.normpath(target_path))
