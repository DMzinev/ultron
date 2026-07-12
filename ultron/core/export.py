"""
core/export.py — Compressed machine-readable architectural map.

Writes .ultron/context.json from a list of AnalysisPackets.
AI agents consume this file instead of re-scanning the repository,
which significantly reduces token cost per session.
"""
import json
import os
from datetime import timezone, datetime


def write_context_json(risks, repo_path):
    """
    Serialize risk results to .ultron/context.json.

    Args:
        risks:     list[AnalysisPacket]
        repo_path: absolute path of the repo (output dir for .ultron/)

    Returns:
        str — absolute path of the written file.

    Raises:
        OSError: if the directory cannot be created or the file cannot be written.
    """
    out_dir = os.path.join(repo_path, ".ultron")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "context.json")

    tier_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_risks = sorted(risks, key=lambda r: (tier_order.get(r.level, 3), -r.impact_score))

    summary = {"high": 0, "medium": 0, "low": 0}
    for r in sorted_risks:
        summary[r.level.lower()] = summary.get(r.level.lower(), 0) + 1

    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": os.path.basename(repo_path),
        "summary": summary,
        "files": [
            {
                "path": r.file_path,
                "level": r.level,
                "role": r.architectural_role.value,
                "strategy": r.change_strategy.value,
                "impact_score": round(r.impact_score, 2),
                "complexity": r.complexity,
                "coupling": int(r.coupling_score),
            }
            for r in sorted_risks
        ],
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return out_path
