"""
Ultron REST API — Export Brief Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

from ultron.core import context_brief
from ultron.interfaces.api.router import APIRouter

@APIRouter.register("/api/v1/export-brief", "POST")
def handle_v1_export_brief(handler: Any) -> None:
    """POST /api/v1/export-brief handler."""
    data = handler.get_request_data()
    if not isinstance(data, dict):
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return

    raw_fmt = data.get("format")
    if raw_fmt is None:
        fmt = "markdown"
    elif isinstance(raw_fmt, str):
        fmt = raw_fmt.strip().lower()
    else:
        handler.send_json_response(400, None, f"Unsupported format type: expected string.")
        return

    allowed_fmts = ["markdown", "json", "text", "html", "claude", "codex", "antigravity"]
    if fmt not in allowed_fmts:
        handler.send_json_response(400, None, f"Unsupported format: '{fmt}'. Allowed: {', '.join(allowed_fmts)}.")
        return

    raw_repo = data.get("repo")
    if raw_repo is None or not isinstance(raw_repo, str) or not raw_repo.strip() or '\x00' in raw_repo:
        repo_path = getattr(handler, "get_repo_root_path", lambda: ".")() or "."
    else:
        repo_path = raw_repo.strip()

    if '\x00' in repo_path:
        handler.send_json_response(400, None, "Invalid repository path: embedded null byte.")
        return

    try:
        norm_path = os.path.normpath(os.path.abspath(repo_path))
        if not os.path.isdir(norm_path):
            handler.send_json_response(400, None, f"Repository path '{norm_path}' is not a directory.")
            return

        brief_res = context_brief.generate_vibe_context_package(repo_path=norm_path)
        brief_str = brief_res.get("prompt_package", str(brief_res)) if isinstance(brief_res, dict) else str(brief_res)

        if fmt == "json":
            exported_content = {"repo": norm_path, "brief": brief_res, "format": fmt}
        elif fmt == "html":
            exported_content = f"<html><body><pre>{brief_str}</pre></body></html>"
        else:
            exported_content = brief_str

        payload = {
            "format": fmt,
            "repo": norm_path,
            "content": exported_content,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        handler.send_json_response(200, payload)
    except (ValueError, TypeError, OSError, FileNotFoundError) as err:
        sys.stderr.write(f"[Ultron Route Export Input Error] {err}\n")
        handler.send_json_response(400, None, f"Invalid repository parameter or format: {err}")
    except Exception as err:
        sys.stderr.write(f"[Ultron Route Export Error] {err}\n")
        handler.send_json_response(500, None, f"Export brief failed: {err}")
