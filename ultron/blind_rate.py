# UMAGS Blind Feedback Calibration Rating Tool
import os
import sys
import json
import time
import argparse
import random

# Ensure local folder is in import search path to find analyzer and risk
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

import analyzer
import risk

def normalize_relative_path(path_str):
    """
    Normalizes a path string to use forward slashes relative to the repository.
    """
    if path_str is None:
        raise ValueError("path_str cannot be None")
    if not isinstance(path_str, str):
        raise TypeError("path_str must be a string")
    
    # Replaces backslashes with forward slashes
    norm = os.path.normpath(path_str).replace("\\", "/")
    return norm

def validate_inputs(filepath, rater, rating):
    """
    Validates the main CLI input bounds.
    """
    if filepath is None or rater is None or rating is None:
        raise ValueError("Arguments cannot be None")
    
    if not filepath.strip():
        raise ValueError("filepath cannot be empty")
    if not rater.strip():
        raise ValueError("rater cannot be empty")
    if rating not in ("HIGH", "MEDIUM", "LOW"):
        raise ValueError("rating must be HIGH, MEDIUM, or LOW")

def get_file_content(repo_path, rel_path):
    """
    Loads and returns the first 50 lines of the target file for blinded preview.
    """
    if repo_path is None or rel_path is None:
        raise ValueError("Arguments cannot be None")
    
    if not os.path.exists(repo_path):
        raise FileNotFoundError("repo_path does not exist")
        
    abs_path = os.path.join(repo_path, rel_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError("Target file does not exist")
        
    lines = []
    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in range(50):
            line = f.readline()
            if not line:
                break
            lines.append(line)
    return "".join(lines)

def select_ratable_files(repo_path):
    """
    Scans the repository and returns a filtered list of relative paths for source code files.
    """
    if repo_path is None:
        raise ValueError("repo_path cannot be None")
    if not os.path.exists(repo_path):
        raise FileNotFoundError("repo_path does not exist")
        
    codebase = analyzer.analyze_directory(repo_path)
    ratable = []
    import pathlib
    for rel_path in codebase.keys():
        path_segments = [p.lower() for p in pathlib.Path(rel_path).parts]
        exclude_terms = {"scratch", "study_portal_qa", "synapse_project", "setup.py", "start_ultron.py", "server.py"}
        
        is_excluded = False
        for segment in path_segments:
            if segment in exclude_terms:
                is_excluded = True
                break
            if "test" in segment:
                if segment == "test" or segment.startswith("test_") or segment.startswith("test-") or segment.endswith("_test") or segment.endswith("-test"):
                    is_excluded = True
                    break
        if is_excluded:
            continue
        ratable.append(rel_path)
        
    return ratable

def calculate_agreement(repo_path, rel_path, rater_tier):
    """
    Computes system risk level and compares with rater's level.
    """
    if repo_path is None or rel_path is None or rater_tier is None:
        raise ValueError("Arguments cannot be None")
    
    codebase = analyzer.analyze_directory(repo_path)
    # Target file in evaluate_risks must be relative with forward slashes
    norm_rel = normalize_relative_path(rel_path)
    packets = risk.evaluate_risks(codebase, [norm_rel], repo_path=repo_path)
    if not packets:
        raise ValueError("Could not evaluate risks for file")
        
    computed_tier = packets[0].level
    computed_score = packets[0].impact_score
    accurate = (rater_tier == computed_tier)
    
    return accurate, computed_tier, computed_score

def write_feedback_entry(feedback_path, entry):
    """
    Appends a single feedback log entry in JSONL format using explicit encoding.
    """
    if feedback_path is None or entry is None:
        raise ValueError("Arguments cannot be None")
    
    if not isinstance(entry, dict):
        raise TypeError("entry must be a dictionary")
        
    os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
    with open(feedback_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def process_rating(repo_path, rel_path, rater, rating, rationale, feedback_path):
    """
    Orchestrates the verification, path normalization, calculation, and recording.
    """
    if repo_path is None or rel_path is None or rater is None or rating is None:
        raise ValueError("Arguments cannot be None")
    
    norm_rel = normalize_relative_path(rel_path)
    validate_inputs(norm_rel, rater, rating)
    
    accurate, computed_tier, computed_score = calculate_agreement(repo_path, norm_rel, rating)
    
    entry = {
        "file": norm_rel,
        "rater": rater,
        "rater_tier": rating,
        "computed_tier": computed_tier,
        "accurate": accurate,
        "rationale": rationale,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "computed_score": computed_score
    }
    
    write_feedback_entry(feedback_path, entry)
    return entry

def main():
    parser = argparse.ArgumentParser(description="Blinded Calibration Rating Tool")
    parser.add_argument("--rater", help="Name of the developer/rater")
    parser.add_argument("--file", help="Specific file path to rate (relative to repo root)")
    parser.add_argument("--rating", choices=["HIGH", "MEDIUM", "LOW"], help="Risk rating tier")
    parser.add_argument("--rationale", default="", help="Rationale for the rating")
    
    args = parser.parse_args()
    
    repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    feedback_path = os.path.join(repo_path, "ultron", "meta", "human_feedback.jsonl")
    
    # Non-interactive mode (fully specified via arguments)
    if args.rater and args.file and args.rating:
        try:
            entry = process_rating(repo_path, args.file, args.rater, args.rating, args.rationale, feedback_path)
            print(f"[+] Recorded rating for {entry['file']} by {entry['rater']}.")
            print(f"  - Rater Judgment: {entry['rater_tier']}")
            print(f"  - System Computed: {entry['computed_tier']} (Score: {entry['computed_score']:.2f})")
            print(f"  - Agreement: {'MATCH' if entry['accurate'] else 'MISMATCH'}")
            sys.exit(0)
        except Exception as e:
            print(f"[-] Error processing rating: {e}", file=sys.stderr)
            sys.exit(1)
            
    # Interactive mode
    print("=== Blinded Calibration Rating Tool ===")
    rater = args.rater
    while not rater or not rater.strip():
        rater = input("Enter your name: ")
        
    ratable = select_ratable_files(repo_path)
    if not ratable:
        print("[-] No ratable source files found in the repository.")
        sys.exit(1)
        
    target_file = args.file
    if not target_file:
        print("\nRatable files:")
        for idx, f in enumerate(ratable):
            print(f"[{idx}] {f}")
        choice = input(f"Select a file index (0-{len(ratable)-1}) or press enter for a random pick: ")
        if choice.strip().isdigit() and 0 <= int(choice) < len(ratable):
            target_file = ratable[int(choice)]
        else:
            target_file = random.choice(ratable)
            
    norm_target = normalize_relative_path(target_file)
    print(f"\nEvaluating: {norm_target}")
    
    try:
        content = get_file_content(repo_path, norm_target)
        print("-" * 60)
        print(content)
        print("-" * 60)
    except Exception as e:
        print(f"[-] Could not read file content: {e}", file=sys.stderr)
        sys.exit(1)
        
    rating = args.rating
    while rating not in ("HIGH", "MEDIUM", "LOW"):
        rating = input("Rate this file's risk tier (HIGH, MEDIUM, LOW): ").upper().strip()
        
    rationale = input("Provide brief rationale/explanation: ")
    
    try:
        entry = process_rating(repo_path, norm_target, rater, rating, rationale, feedback_path)
        print(f"\n[+] Recorded rating successfully.")
        print(f"  - System computed tier: {entry['computed_tier']} (Score: {entry['computed_score']:.2f})")
        print(f"  - Agreement: {'MATCH' if entry['accurate'] else 'MISMATCH'}")
    except Exception as e:
        print(f"[-] Error writing feedback: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()