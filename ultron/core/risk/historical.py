"""
risk/historical.py — I/O layer only.

Responsibilities:
    - load_mkr_stats: reads the Synapse mutation ledger → MKR map per file
    - load_human_feedback: reads meta/human_feedback.jsonl → accuracy map per file

No computation, no AST, no radon. Pure file reading with mtime-based caching.
"""
import os
import json

_MKR_CACHE = {}
_LAST_CACHE_TIME = 0


def load_mkr_stats(ledger_path=None):
    """
    Reads the Synapse mutation ledger and returns a per-file Mutation Kill Rate map.
    Returns {} if the ledger does not exist or cannot be read.
    Raises TypeError if ledger_path is not a string or None.
    """
    global _MKR_CACHE, _LAST_CACHE_TIME
    if ledger_path is not None and not isinstance(ledger_path, str):
        raise TypeError("ledger_path must be a string or None")
    if not ledger_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ledger_path = os.path.abspath(
            os.path.join(script_dir, "..", "..", "..", "synapse_project",
                         "synapse_mutator", "ledger.jsonl")
        )

    if os.path.exists(ledger_path):
        try:
            mtime = os.path.getmtime(ledger_path)
            if mtime <= _LAST_CACHE_TIME and _MKR_CACHE:
                return _MKR_CACHE
            _LAST_CACHE_TIME = mtime
        except OSError as e:
            print(f"Warning: failed to get mtime for {ledger_path}: {e}")
    else:
        return {}

    stats = {}
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                filename = record.get("file")
                if filename and record.get("was_mutated"):
                    if record.get("equivalent"):
                        continue
                    norm_file = filename.replace("\\", "/").replace("src/", "")
                    stats.setdefault(norm_file, {"killed": 0, "total": 0})
                    stats[norm_file]["total"] += 1
                    if not record.get("accepted"):
                        stats[norm_file]["killed"] += 1
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: failed to parse/read ledger {ledger_path}: {e}")

    mkr_map = {
        k: (v["killed"] / v["total"] if v["total"] > 0 else 1.0)
        for k, v in stats.items()
    }
    _MKR_CACHE = mkr_map
    return mkr_map


def load_human_feedback():
    """
    Reads meta/human_feedback.jsonl and returns a per-file accuracy map.
    Returns {} if the file does not exist or cannot be read.
    """
    feedback_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "meta", "human_feedback.jsonl"
    )
    feedback = {}
    if not os.path.exists(feedback_path):
        return feedback
    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                filename = rec.get("file")
                if filename:
                    feedback[filename] = rec.get("accurate", True)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: failed to parse/read human feedback {feedback_path}: {e}")
    return feedback
