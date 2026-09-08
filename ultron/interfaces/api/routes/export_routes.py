"""
Ultron REST API — Export Brief Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

from ultron.core import context_brief

def handle_v1_export_brief(handler: Any) -> None:
    """POST /api/v1/export-brief handler."""
    data = handler.get_request_data()
    if data is None:
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return

    repo_path = data.get("repo", ".")
    fmt = data.get("format", "markdown").lower()

    if fmt not in ["markdown", "json", "text", "html"]:
        handler.send_json_response(400, None, f"Unsupported format: '{fmt}'. Allowed: markdown, json, text, html.")
        return

    try:
        norm_path = os.path.normpath(os.path.abspath(repo_path))
        brief_md = context_brief.generate_vibe_context_package(norm_path)

        if fmt == "json":
            if isinstance(brief_md, dict):
                brief_md["schema_version"] = "1.0.0"
            exported_content = {"repo": norm_path, "brief": brief_md, "format": fmt, "schema_version": "1.0.0"}
        elif fmt == "html":
            exported_content = f"<html><body><pre>{brief_md}</pre></body></html>"
        else:
            exported_content = brief_md

        payload = {
            "format": fmt,
            "repo": norm_path,
            "schema_version": "1.0.0",
            "content": exported_content,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        handler.send_json_response(200, payload)
    except Exception as err:
        sys.stderr.write(f"[Ultron Route Export Error] {err}\n")
        handler.send_json_response(500, None, f"Export brief failed: {err}")
