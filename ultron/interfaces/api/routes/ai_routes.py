"""
Ultron REST API — AI Critique Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

from ultron.interfaces.api.router import APIRouter
from ultron.core.ai import AIClient

@APIRouter.register("/api/v1/ai/critique", "POST")
def handle_v1_ai_critique(handler: Any) -> None:
    """POST /api/v1/ai/critique handler."""
    data = handler.get_request_data()
    if not isinstance(data, dict):
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return

    raw_target = data.get("file") or data.get("file_path") or data.get("node_id") or data.get("target_entity")
    if raw_target is None or not isinstance(raw_target, str) or not raw_target.strip() or '\x00' in raw_target:
        file_target = "general"
    else:
        file_target = raw_target.strip()

    try:
        complexity = int(data.get("complexity", 1) or 1)
    except (ValueError, TypeError):
        complexity = 1

    try:
        coupling = int(data.get("coupling", 0) or 0)
    except (ValueError, TypeError):
        coupling = 0

    try:
        impact_score = float(data.get("impact_score", 0.0) or 0.0)
    except (ValueError, TypeError):
        impact_score = 0.0

    raw_intent = data.get("intent")
    intent = str(raw_intent).strip() if raw_intent is not None else ""

    try:
        ai_client = AIClient()
        critique_result = ai_client.query_critique(
            file_path=file_target,
            complexity=complexity,
            coupling=coupling,
            impact_score=impact_score,
            intent=intent
        )
        handler.send_json_response(200, critique_result)
    except (ValueError, TypeError, OSError) as err:
        sys.stderr.write(f"[Ultron Route AI Input Error] {err}\n")
        handler.send_json_response(400, None, f"AI Critique parameter error: {err}")
    except Exception as err:
        sys.stderr.write(f"[Ultron Route AI Error] {err}\n")
        handler.send_json_response(500, None, f"AI Critique failed: {err}")
