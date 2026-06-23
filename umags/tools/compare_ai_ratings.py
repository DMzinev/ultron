"""
scratch/compare_ai_ratings.py

Compares AI rater assessments (from ultron/meta/ai_ratings.jsonl) against
Ultron's formula output for the same files.

Outputs:
  - Raw joined table (file, formula_tier, ai_tier, confidence, match)
  - Agreement rate with n explicitly stated
  - Disagreements with AI's stated reasoning (for formula improvement)

If n < 10, explicitly says the sample is too small for reliable conclusions.
"""

import os
import sys
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AI_RATINGS_PATH = os.path.join(REPO_ROOT, "ultron", "meta", "ai_ratings.jsonl")
for subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join(REPO_ROOT, "ultron", subdir)))
sys.path.append(REPO_ROOT)
sys.path.append(os.path.abspath(os.path.join(REPO_ROOT, "umags")))


def load_ai_ratings() -> dict:
    """
    Loads ai_ratings.jsonl. Returns dict keyed by file path.
    Returns empty dict if file doesn't exist or has no valid entries.
    """
    if not os.path.exists(AI_RATINGS_PATH):
        return {}
    ratings = {}
    with open(AI_RATINGS_PATH, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if "file" in r:
                    ratings[r["file"]] = r
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: skipping malformed line {lineno}: {e}", file=sys.stderr)
    return ratings


def get_formula_tiers(repo_path: str) -> dict:
    """
    Runs analyzer + risk on repo_path and returns {rel_path: tier} dict.
    tier is 'HIGH', 'MEDIUM', 'LOW', or 'ERROR: <message>'.
    """
    try:
        from analyzer import analyze_directory
        from risk import score_file, classify_tier
    except ImportError as e:
        print(f"Cannot import Ultron modules: {e}", file=sys.stderr)
        raise ImportError(f"Cannot import Ultron modules: {e}")

    codebase = analyze_directory(repo_path)
    if not codebase:
        return {}

    tiers = {}
    for rel_path, analysis in codebase.items():
        try:
            score = score_file(analysis)
            tier = classify_tier(score)
            tiers[rel_path] = tier
        except Exception as e:
            tiers[rel_path] = f"ERROR: {e}"
    return tiers


def main():
    ai_ratings = load_ai_ratings()

    if not ai_ratings:
        print(
            "No AI ratings found in:\n"
            f"  {AI_RATINGS_PATH}\n\n"
            "Run the AI rating process first:\n"
            "  Ask Antigravity: 'Rate all unrated files using the code_risk_rater subagent'"
        )
        sys.exit(1)

    print(f"Loaded {len(ai_ratings)} AI rating(s).\n")

    formula_tiers = get_formula_tiers(REPO_ROOT)

    rows = []
    for file_path, ai_rating in ai_ratings.items():
        formula_tier = formula_tiers.get(file_path, "NOT_IN_FORMULA")
        ai_tier = ai_rating.get("ai_risk_level", "UNKNOWN")
        confidence = ai_rating.get("ai_confidence", "UNKNOWN")
        agreement = (formula_tier == ai_tier)
        reasoning = ai_rating.get("reasoning", "")
        rows.append({
            "file": file_path,
            "formula_tier": formula_tier,
            "ai_tier": ai_tier,
            "ai_confidence": confidence,
            "agreement": agreement,
            "reasoning": reasoning,
        })

    if not rows:
        print("No overlap between AI ratings and formula output. Check file paths.")
        sys.exit(1)

    n = len(rows)
    agreed = sum(1 for r in rows if r["agreement"])
    agreement_rate = agreed / n

    # ── Raw joined table ───────────────────────────────────────────────────
    print("=" * 72)
    print("RAW JOINED TABLE")
    print("=" * 72)
    header = f"{'File':<42} {'Formula':>8} {'AI':>8} {'Conf':>6} {'Match':>6}"
    print(header)
    print("-" * 72)
    for r in rows:
        fname = r["file"]
        if len(fname) > 40:
            fname = "…" + fname[-39:]
        match_str = "✓" if r["agreement"] else "✗"
        print(
            f"{fname:<42} {r['formula_tier']:>8} {r['ai_tier']:>8} "
            f"{r['ai_confidence']:>6} {match_str:>6}"
        )

    # ── Summary ────────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"\nAgreement rate: {agreement_rate:.1%}  (n={n})")

    if n < 10:
        print(
            f"\n⚠ WARNING: n={n}. This sample is too small to draw reliable "
            f"conclusions. Collect at least 10 ratings before citing this number."
        )

    # ── Disagreements ──────────────────────────────────────────────────────
    disagreements = [r for r in rows if not r["agreement"]]
    if not disagreements:
        print("\nNo disagreements — formula and AI rater agreed on all files.")
    else:
        print(f"\nDISAGREEMENTS ({len(disagreements)} of {n}):")
        for r in disagreements:
            print(f"\n  File:         {r['file']}")
            print(f"  Formula said: {r['formula_tier']}")
            print(f"  AI said:      {r['ai_tier']} (confidence: {r['ai_confidence']})")
            snippet = r["reasoning"][:200] + "…" if len(r["reasoning"]) > 200 else r["reasoning"]
            print(f"  AI reasoning: {snippet}")

    print()


if __name__ == "__main__":
    main()
