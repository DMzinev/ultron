"""
ultron/ai_rater.py

Prepares code-review contexts for the isolated AI risk rater subagent,
and logs structured ratings to ai_ratings.jsonl.

The AI rater subagent receives ONLY:
  - The file's raw source code
  - The list of other files that call into it (caller list)

It does NOT receive:
  - The Impact Score
  - The risk tier (HIGH/MEDIUM/LOW from the formula)
  - Any Ultron formula, metric, or weight

This structural isolation is what makes the rating independent.
The rating is logged BEFORE any formula output is revealed.
"""

import os
import sys
import json
import datetime

# REPO_ROOT configuration
_dir = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_dir, "..", ".."))

META_DIR = os.path.join(REPO_ROOT, "ultron", "meta")
RATINGS_PATH = os.path.join(META_DIR, "ai_ratings.jsonl")


def get_caller_list(file_path: str, repo_path: str) -> list:
    """
    Returns the list of repo files (relative paths) that import or call into file_path.
    Uses analyzer.py's codebase map — no scores or metrics are extracted.

    Raises ValueError for empty/None inputs.
    Raises FileNotFoundError if file_path does not exist.
    Raises ImportError if analyzer cannot be imported.
    """
    if not file_path:
        raise ValueError("file_path must be a non-empty string")
    if not repo_path:
        raise ValueError("repo_path must be a non-empty string")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Target file not found: {file_path}")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from ultron.core import analyzer
    except ImportError as e:
        raise ImportError(f"Cannot import analyzer: {e}")

    codebase = analyzer.analyze_directory(repo_path)
    if not codebase:
        return []

    rel_target = os.path.relpath(file_path, repo_path).replace("\\", "/")
    # Build module name variants for matching
    target_module = rel_target.replace("/", ".").replace(".py", "")
    target_stem = target_module.split(".")[-1]

    callers = []
    for rel_path, analysis in codebase.items():
        if rel_path == rel_target:
            continue
        for imp in analysis.get("imports", []):
            if imp == target_module or imp == target_stem or imp.endswith("." + target_stem):
                callers.append(rel_path)
                break

    return sorted(set(callers))


def prepare_rating_context(file_path: str, repo_path: str) -> str:
    """
    Builds the full prompt text to send to the isolated AI rater subagent.
    Contains ONLY: raw source code + caller list. No scores, no formula.

    Raises ValueError for empty inputs or empty files.
    Raises FileNotFoundError if file_path does not exist.
    Returns a formatted string ready to send as a subagent prompt.
    """
    if not file_path:
        raise ValueError("file_path must be a non-empty string")
    if not repo_path:
        raise ValueError("repo_path must be a non-empty string")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        raise ValueError(f"File is empty: {file_path}")

    callers = get_caller_list(file_path, repo_path)
    rel_path = os.path.relpath(file_path, repo_path).replace("\\", "/")

    if callers:
        caller_text = "\n".join(f"  - {c}" for c in callers)
    else:
        caller_text = "  (no other files in this repo import this file)"

    prompt = (
        f"Please assess the risk of modifying the following Python file.\n\n"
        f"FILE: {rel_path}\n\n"
        f"FILES THAT CALL INTO THIS ONE:\n{caller_text}\n\n"
        f"SOURCE CODE:\n```python\n{source_code}\n```\n\n"
        f"Respond with ONLY valid JSON in the exact format specified in your instructions. "
        f"No other text before or after the JSON."
    )

    return prompt


def log_rating(file_path: str, repo_path: str, rating_json: dict) -> None:
    """
    Validates and appends a completed AI rating to ai_ratings.jsonl.
    The rating is logged as-received — the formula output is NOT looked up here.

    Raises TypeError if rating_json is not a dict.
    Raises ValueError if required fields are missing or contain invalid values.
    """
    if not isinstance(rating_json, dict):
        raise TypeError(f"rating_json must be a dict, got {type(rating_json).__name__}")
    if not file_path:
        raise ValueError("file_path must be a non-empty string")
    if not repo_path:
        raise ValueError("repo_path must be a non-empty string")

    required_fields = {"risk_level", "confidence", "reasoning", "coupling_hazards", "improvement_suggestion"}
    missing = required_fields - set(rating_json.keys())
    if missing:
        raise ValueError(f"rating_json is missing required fields: {missing}")

    valid_levels = {"HIGH", "MEDIUM", "LOW"}
    if rating_json.get("risk_level") not in valid_levels:
        raise ValueError(
            f"risk_level must be one of {valid_levels}, got: {rating_json.get('risk_level')!r}"
        )
    if rating_json.get("confidence") not in valid_levels:
        raise ValueError(
            f"confidence must be one of {valid_levels}, got: {rating_json.get('confidence')!r}"
        )
    if not isinstance(rating_json.get("coupling_hazards"), list):
        raise ValueError("coupling_hazards must be a list")

    rel_path = os.path.relpath(file_path, repo_path).replace("\\", "/")

    entry = {
        "file": rel_path,
        "ai_risk_level": rating_json["risk_level"],
        "ai_confidence": rating_json["confidence"],
        "reasoning": rating_json["reasoning"],
        "coupling_hazards": rating_json["coupling_hazards"],
        "improvement_suggestion": rating_json["improvement_suggestion"],
        "rater": "code_risk_rater_subagent",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }

    os.makedirs(META_DIR, exist_ok=True)
    with open(RATINGS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(
        f"[ai_rater] Logged: {rel_path} → {entry['ai_risk_level']} "
        f"(confidence: {entry['ai_confidence']})"
    )


def load_ratings() -> list:
    """
    Loads all ratings from ai_ratings.jsonl.
    Returns empty list if file does not exist.
    Skips malformed lines with a warning rather than crashing.
    """
    if not os.path.exists(RATINGS_PATH):
        return []
    ratings = []
    with open(RATINGS_PATH, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ratings.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(
                    f"[ai_rater] Warning: skipping malformed line {lineno}: {e}",
                    file=sys.stderr,
                )
    return ratings


def get_unrated_files(repo_path: str) -> list:
    """
    Returns absolute paths of .py files in repo_path not yet present in ai_ratings.jsonl.
    Excludes: __pycache__, scratch, .git, .agents, research-notes, test files, __init__.py.

    Raises ValueError for empty input.
    Raises NotADirectoryError if repo_path is not a directory.
    """
    if not repo_path:
        raise ValueError("repo_path must be a non-empty string")
    if not os.path.isdir(repo_path):
        raise NotADirectoryError(f"repo_path is not a directory: {repo_path}")

    rated_files = {r["file"] for r in load_ratings()}

    exclude_dirs = {"__pycache__", "scratch", ".git", ".agents", "research-notes", "synapse_project"}
    exclude_terms = ("test", "spec")
    exclude_names = {"__init__.py", "run_tests.py", "run_verification_loop.py", "governor.py"}

    unrated = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            if fname in exclude_names:
                continue
            if any(term in fname.lower() for term in exclude_terms):
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, repo_path).replace("\\", "/")
            if rel_path not in rated_files:
                unrated.append(abs_path)

    return sorted(unrated)


def main():
    """
    CLI entry points:

      python ai_rater.py --prepare <file> [--repo <path>]
          Print the rating prompt for FILE to stdout.

      python ai_rater.py --list-unrated [--repo <path>]
          List all files not yet rated.

      python ai_rater.py --show-ratings
          Print a summary of all logged ratings.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Ultron AI Rater — prepares and logs AI code risk ratings"
    )
    parser.add_argument("--prepare", metavar="FILE", help="Prepare rating context for FILE")
    parser.add_argument("--repo", metavar="REPO", default=REPO_ROOT, help="Repo root path")
    parser.add_argument("--list-unrated", action="store_true", help="List files not yet rated")
    parser.add_argument("--show-ratings", action="store_true", help="Print all logged ratings")
    args = parser.parse_args()

    if args.prepare:
        prompt = prepare_rating_context(args.prepare, args.repo)
        print(prompt)
    elif args.list_unrated:
        files = get_unrated_files(args.repo)
        if not files:
            print("[ai_rater] All files have been rated.")
        else:
            print(f"[ai_rater] {len(files)} unrated file(s):")
            for f in files:
                print(f"  {f}")
    elif args.show_ratings:
        ratings = load_ratings()
        if not ratings:
            print("[ai_rater] No ratings logged yet.")
        else:
            print(f"[ai_rater] {len(ratings)} rating(s):")
            for r in ratings:
                print(f"  {r['file']}: {r['ai_risk_level']} (confidence: {r['ai_confidence']})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
