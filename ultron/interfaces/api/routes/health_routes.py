"""
Ultron REST API — Health Check Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

def handle_v1_health(handler: Any) -> None:
    """GET /api/v1/health handler."""
    try:
        db_path = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".ultron", "rkm.db")))
        db_exists = os.path.exists(db_path)

        payload = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform
            },
            "rkm_database": {
                "exists": db_exists,
                "path": db_path
            },
            "modules": {
                "design_oracle": True,
                "delta_engine": True,
                "evolution_engine": True
            }
        }
        handler.send_json_response(200, payload)
    except Exception as err:
        sys.stderr.write(f"[Ultron Route Health Error] {err}\n")
        handler.send_json_response(500, None, f"Health check failed: {err}")
