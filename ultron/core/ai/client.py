"""
Ultron Core AI Client Abstraction Layer
Provides a robust, non-blocking interface to the local OpenAI-compatible API proxy on http://127.0.0.1:10531/v1
with automatic 5-second socket timeout and seamless offline fallback to native RKM rule synthesis.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class AIClient:
    """
    Abstracted AI Provider Client for Ultron.
    Queries the local OpenAI proxy (port 10531) if online, otherwise falls back gracefully
    to grounded AST rule explanations without throwing unhandled exceptions.
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:10531/v1", timeout: float = 5.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def check_health(self) -> bool:
        """Checks if the local OpenAI proxy endpoint is active and responding."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/models", method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False

    def query_critique(
        self,
        file_path: str,
        complexity: int,
        coupling: int,
        impact_score: float,
        intent: str = ""
    ) -> Dict[str, Any]:
        """
        Generates an architectural critique for a code hotspot.
        Tries local AI proxy first; if offline or timed out, returns native grounded AST synthesis.
        """
        clean_file = file_path.replace("\\", "/")
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Ultron Senior Architectural Rater. Provide concise, actionable refactoring advice."
                },
                {
                    "role": "user",
                    "content": f"Analyze code hotspot: {clean_file}\n"
                               f"Cyclomatic Complexity: {complexity}\n"
                               f"Coupling Score: {coupling}\n"
                               f"System Impact Score: {impact_score:.2f}\n"
                               f"Developer Intent: {intent or 'General refactoring & stabilization'}"
                }
            ],
            "max_tokens": 300,
            "temperature": 0.2
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.endpoint}/chat/completions",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    raw_body = resp.read().decode("utf-8", errors="replace")
                    body = json.loads(raw_body)
                    choices = body.get("choices", [])
                    if choices and isinstance(choices, list):
                        msg = choices[0].get("message", {}).get("content", "").strip()
                        if msg:
                            return {
                                "success": True,
                                "source": "Local OpenAI Proxy (Active)",
                                "critique": msg,
                                "file": clean_file
                            }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
            sys.stderr.write(f"[Ultron AIClient Notice] Proxy offline or timed out ({e}). Falling back to native synthesis.\n")

        # Native Grounded AST Synthesis Fallback
        risk_tier = "HIGH" if impact_score >= 10.0 else ("MEDIUM" if impact_score >= 3.0 else "LOW")
        advice = [
            f"• High complexity ({complexity}): Extract sub-functions to enforce Single Responsibility (SRP).",
            f"• High coupling ({coupling}): Introduce an interface boundary to decouple caller dependencies.",
            "• Verify change isolation with unit tests before merging."
        ] if risk_tier == "HIGH" else [
            f"• Moderate coupling ({coupling}): Keep change scope localized to internal functions.",
            "• Maintain existing method contracts to avoid regression."
        ]

        return {
            "success": True,
            "source": "Ultron Native AST Engine (Offline Fallback)",
            "critique": f"Architectural Assessment for `{os.path.basename(clean_file)}` (Risk Tier: {risk_tier}):\n\n" + "\n".join(advice),
            "file": clean_file
        }
