import os
import json

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_path = os.path.join(repo_path, "ultron", "meta", "blind_feedback.jsonl")
    
    real_ratings = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        if entry.get("rater_id") != "DUMMY_FILTER":
                            real_ratings.append(entry)
                    except Exception as e:
                        _ = e
                        
    with open(log_path, "w", encoding="utf-8") as f:
        for r in real_ratings:
            f.write(json.dumps(r) + "\n")
    print(f"[+] Cleaned up dummy entries. Total real ratings logged: {len(real_ratings)}")

if __name__ == "__main__":
    main()
