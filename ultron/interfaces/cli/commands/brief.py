"""
ultron.interfaces.cli.commands.brief
Machine-Readable Context Brief & AI Agent Mission Envelope CLI Handler.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ultron.core import analyzer
from ultron.core.prompt import compile_mission_envelope


def run_brief_command(
    target_file: str,
    repo_path: str = ".",
    intent: Optional[str] = None,
    json_output: bool = False
) -> int:
    """
    Executes the 'ultron brief <file>' command.
    Generates a versioned (schema_version: 1.0.0) machine-readable contract or
    formatted markdown prompt envelope for developer and agent orientation.
    Returns 0 on SUCCESS, 1 on FAILURE (e.g. missing target file).
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    if not os.path.isdir(abs_repo):
        sys.stderr.write(f"[-] Error: Repository directory '{abs_repo}' not found.\n")
        return 1

    if not target_file:
        sys.stderr.write("[-] Error: Missing required target file argument.\n")
        return 1

    abs_target = os.path.abspath(os.path.join(abs_repo, target_file)) if not os.path.isabs(target_file) else target_file
    if not os.path.isfile(abs_target):
        sys.stderr.write(f"[-] Error: Target file '{target_file}' does not exist in repository '{abs_repo}'.\n")
        return 1

    try:
        norm_target = os.path.relpath(abs_target, abs_repo).replace("\\", "/")
    except ValueError:
        norm_target = os.path.normpath(target_file).replace("\\", "/").lstrip("./")

    # 1. Compile 7-Field Mission Envelope
    raw_intent = str(intent or "").strip()
    envelope = compile_mission_envelope(
        intent=raw_intent,
        target_file=norm_target,
        repo_path=abs_repo
    )

    # 2. Extract AST Facts
    try:
        facts = analyzer.analyze_file(abs_target)
    except Exception:
        facts = {"imports": [], "definitions": []}

    definitions = facts.get("definitions", [])
    imports = facts.get("imports", [])

    # Extract complexity from complexity ceiling string e.g. "This file is at McCabe 14; ..."
    comp_match = re.search(r"McCabe\s+(\d+)", envelope.get("complexity_ceiling", ""))
    comp = int(comp_match.group(1)) if comp_match else 1
    callers = envelope.get("blast_radius", [])

    # 3. Output Payload
    if json_output:
        contract_payload = {
            "schema_version": "1.0.0",
            "target_file": norm_target,
            "repo": abs_repo.replace("\\", "/"),
            "intent": envelope["intent"],
            "envelope": envelope,
            "analysis": {
                "complexity": comp,
                "callers": callers,
                "definitions": definitions,
                "imports": imports
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        try:
            print(json.dumps(contract_payload, indent=2))
        except UnicodeEncodeError:
            sys.stdout.buffer.write((json.dumps(contract_payload, indent=2) + "\n").encode("utf-8", errors="replace"))
    else:
        try:
            print(envelope["rendered_prompt"])
        except UnicodeEncodeError:
            sys.stdout.buffer.write((envelope["rendered_prompt"] + "\n").encode("utf-8", errors="replace"))

    return 0
