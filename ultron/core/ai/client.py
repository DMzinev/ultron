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


def normalize_openai_endpoint(endpoint: Optional[str]) -> str:
    """Idempotently normalizes OpenAI endpoint URL to guarantee single /v1 suffix."""
    url = (endpoint or "http://127.0.0.1:10531/v1").strip().rstrip("/")
    while url.endswith("/v1"):
        url = url[:-3].rstrip("/")
    return f"{url}/v1" if url else "http://127.0.0.1:10531/v1"


class AIClient:
    """
    Abstracted AI Provider Client for Ultron.
    Queries the local OpenAI proxy (port 10531) if online, otherwise falls back gracefully
    to grounded AST rule explanations without throwing unhandled exceptions.
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:10531/v1", timeout: float = 5.0):
        self.endpoint = normalize_openai_endpoint(endpoint)
        self.timeout = max(0.5, float(timeout))

    def check_health(self) -> bool:
        """Checks if the local OpenAI proxy endpoint is active and responding."""
        try:
            req = urllib.request.Request(
                f"{self.endpoint}/models",
                headers={"User-Agent": "UltronAIClient/1.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception:
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
        clean_file = str(file_path or "unknown").replace("\\", "/")[:300]
        try:
            comp_val = int(complexity)
        except (ValueError, TypeError):
            comp_val = 1
        try:
            coup_val = int(coupling)
        except (ValueError, TypeError):
            coup_val = 0
        try:
            imp_val = float(impact_score)
        except (ValueError, TypeError):
            imp_val = 0.0

        clean_intent = str(intent or "General refactoring & stabilization").strip()[:1000]

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
                               f"Cyclomatic Complexity: {comp_val}\n"
                               f"Coupling Score: {coup_val}\n"
                               f"System Impact Score: {imp_val:.2f}\n"
                               f"Developer Intent: {clean_intent}"
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
                headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "UltronAIClient/1.0"},
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
        except Exception as e:
            sys.stderr.write(f"[Ultron AIClient Notice] Proxy offline or unreachable ({e}). Falling back to native AST synthesis.\n")

        # Native Grounded AST Synthesis Fallback (Categorized by risk tier)
        risk_tier = "CRITICAL" if imp_val >= 20.0 else ("HIGH" if imp_val >= 10.0 else ("MEDIUM" if imp_val >= 3.0 else "LOW"))
        
        if risk_tier in ("CRITICAL", "HIGH"):
            advice = [
                f"• High complexity ({comp_val}): Extract sub-functions to enforce Single Responsibility (SRP).",
                f"• High coupling ({coup_val} callers): Introduce an interface boundary to decouple caller dependencies.",
                "• Verify change isolation with automated unit tests before merging."
            ]
        elif risk_tier == "MEDIUM":
            advice = [
                f"• Moderate coupling ({coup_val} callers): Keep change scope localized to internal helper routines.",
                "• Maintain existing method contracts to avoid regression across callers."
            ]
        else:
            advice = [
                f"• Low structural risk (Complexity: {comp_val}, Coupling: {coup_val}): Module conforms to architectural standards.",
                "• Ensure edits preserve existing unit test assertions and interface compatibility."
            ]

        return {
            "success": True,
            "source": "Ultron Native AST Engine (Offline Fallback)",
            "critique": f"Architectural Assessment for `{os.path.basename(clean_file)}` (Risk Tier: {risk_tier}):\n\n" + "\n".join(advice),
            "file": clean_file
        }
