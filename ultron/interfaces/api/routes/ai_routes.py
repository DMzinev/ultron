"""
Ultron REST API — AI Critique Route Handler
"""

import sys
import os
from datetime import datetime, timezone
from typing import Any

from ultron.core.ai import AIClient

def handle_v1_ai_critique(handler: Any) -> None:
    """POST /api/v1/ai/critique handler."""
    data = handler.get_request_data()
    if data is None:
        handler.send_json_response(400, None, "Invalid or corrupted JSON body")
        return

    file_target = data.get("file", "general")
    complexity = data.get("complexity", 1)
    coupling = data.get("coupling", 0)
    impact_score = data.get("impact_score", 0.0)

    try:
        critique_result = AIClient.generate_critique(
            file_target=file_target,
            complexity=complexity,
            coupling=coupling,
            impact_score=impact_score
        )
        handler.send_json_response(200, critique_result)
    except Exception as err:
        sys.stderr.write(f"[Ultron Route AI Error] {err}\n")
        handler.send_json_response(500, None, f"AI Critique failed: {err}")
