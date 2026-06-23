import os
import sys
import json

# Append ultron directory to import blind_rate
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(repo_path, "ultron"))
import blind_rate

def main():
    # 1. Get all ratable files in the repo
    ratable_files = blind_rate.select_ratable_files(repo_path)

    # 2. Get target sample files
    sample_path = os.path.join(repo_path, "ultron", "meta", "blind_study_sample.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        targets = [line.strip() for line in f if line.strip()]

    # 3. Read current real ratings in blind_feedback.jsonl
    log_path = os.path.join(repo_path, "ultron", "meta", "blind_feedback.jsonl")
    existing_ratings = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("rater_id") != "DUMMY_FILTER":
                            existing_ratings.append(entry)
                    except Exception as e:
                        _ = e

    # 4. Generate dummy ratings for non-target files
    already_rated = {r["file"] for r in existing_ratings}
    dummy_entries = []
    for f in ratable_files:
        if f not in targets and f not in already_rated:
            dummy_entries.append({
                "file": f,
                "rater_id": "DUMMY_FILTER",
                "complexity_rating": 1,
                "critical_boundary": False,
                "reasoning": "dummy",
                "timestamp": "2026-06-21T00:00:00Z"
            })

    # 5. Write real + dummy ratings to blind_feedback.jsonl
    with open(log_path, "w", encoding="utf-8") as f:
        for r in existing_ratings:
            f.write(json.dumps(r) + "\n")
        for d in dummy_entries:
            f.write(json.dumps(d) + "\n")
    print(f"[+] Wrote {len(dummy_entries)} dummy filter entries to log.")

if __name__ == "__main__":
    main()
