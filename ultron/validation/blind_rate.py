import os
import sys
import json
import random
import time
import argparse

# Configure sys.path to find moved files under their new subdirectories
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
for _subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join(_root, "ultron", _subdir)))
sys.path.append(_root)
sys.path.append(os.path.abspath(os.path.join(_root, "umags")))

import analyzer

def normalize_relative_path(path_str):
    """
    Standardizes paths to use forward slashes.
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
        
    return sorted(ratable)

def calculate_agreement(repo_path, rel_path, rater_tier):
    """
    Computes system risk level and compares with rater's level.
    """
    if repo_path is None or rel_path is None or rater_tier is None:
        raise ValueError("Arguments cannot be None")
    
    # Dynamic import to avoid loading risk.py at module level
    import risk
    
    codebase = analyzer.analyze_directory(repo_path)
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

def run_blind_rating():
    """
    Standalone interactive flow for blinded feedback capture.
    No risk.py import or evaluation is performed or presented in this flow.
    """
    # 1. Takes a repo path as input
    repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and os.path.isdir(os.path.abspath(arg)):
            repo_path = os.path.abspath(arg)
            break
            
    print("[*] Analyzing repository structure...")
    try:
        codebase = analyzer.analyze_directory(repo_path)
    except Exception as e:
        print(f"[-] Error parsing codebase: {e}")
        sys.exit(1)
        
    if not codebase:
        print("[-] Error: No python files found in directory.")
        sys.exit(1)

    # Filter available ratable files
    ratable = select_ratable_files(repo_path)
    if not ratable:
        print("[-] No ratable source files found in the repository.")
        sys.exit(1)

    # 2. Picks one file at random from that repo that has NOT yet been rated
    _dir = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.abspath(os.path.join(_dir, "..", ".."))
    log_path = os.path.join(_root, "ultron", "meta", "blind_feedback.jsonl")
    rated_files = set()
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if "file" in entry:
                                rated_files.add(entry["file"])
                        except Exception as e:
                            _ = e
        except Exception as e:
            print(f"[Warning] Could not read existing feedback file: {e}")

    available_files = [f for f in ratable if f not in rated_files]
    if not available_files:
        print("[+] All ratable files in the repository have already been rated!")
        sys.exit(0)

    # Select a random file
    selected_file = random.choice(available_files)
    abs_file_path = os.path.join(repo_path, selected_file)

    # Read selected file code content
    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            code_content = f.read()
    except Exception as e:
        print(f"[-] Error reading file '{abs_file_path}': {e}")
        sys.exit(1)

    # 3. Print ONLY the file's code and, separately, a list of which other files call into it
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            for call in defn.get('calls', []):
                global_callers.setdefault(call, []).append(rel_path)
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    for call in method.get('calls', []):
                        global_callers.setdefault(call, []).append(rel_path)

    target_defs = codebase[selected_file].get('definitions', [])
    downstream_files = []
    for defn in target_defs:
        name = defn.get('name')
        if name in global_callers:
            downstream_files.extend(global_callers[name])
        if defn.get('type') == 'class':
            for method in defn.get('methods', []):
                m_name = method.get('name')
                if m_name in global_callers:
                    downstream_files.extend(global_callers[m_name])

    downstream_files = list(set(downstream_files))
    if selected_file in downstream_files:
        downstream_files.remove(selected_file)

    print("\n" + "=" * 80)
    print(f"BLIND RATING TARGET: {selected_file}")
    print("=" * 80 + "\n")
    print("--- SOURCE CODE ---")
    print(code_content)
    print("\n" + "-" * 40)
    print("--- CALLERS (FILES CALLING INTO THIS FILE) ---")
    if downstream_files:
        for caller in sorted(downstream_files):
            print(f"  - {caller}")
    else:
        print("  (None - this file has no callers in the repository)")
    print("-" * 40 + "\n")

    # Prompt rater once for ID and ratings
    rater_id = input("Enter Rater ID: ").strip()
    while not rater_id:
        rater_id = input("Rater ID is required. Enter Rater ID: ").strip()

    # a. "On a scale of 1-5, how risky does this feel to modify?"
    while True:
        rating_str = input("On a scale of 1-5, how risky does this feel to modify? ").strip()
        try:
            rating_val = int(rating_str)
            if 1 <= rating_val <= 5:
                break
        except ValueError as e:
            _ = e
        print("Invalid input. Please enter an integer between 1 and 5.")

    # b. "Would you call this a critical system boundary? (y/n)"
    while True:
        boundary_str = input("Would you call this a critical system boundary? (y/n) ").strip().lower()
        if boundary_str in ('y', 'n', 'yes', 'no'):
            is_boundary = boundary_str.startswith('y')
            break
        print("Invalid input. Please enter 'y' or 'n'.")

    # c. Optional free-text: "Why?"
    reasoning = input("Why? (Optional free-text): ").strip()

    # 5. Logs the rating to ultron/meta/blind_feedback.jsonl
    entry = {
        "file": selected_file,
        "rater_id": rater_id,
        "complexity_rating": rating_val,
        "critical_boundary": is_boundary,
        "reasoning": reasoning,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"\n[+] Rating logged successfully to {log_path}!")
    except Exception as e:
        print(f"[-] Error writing feedback entry: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Blinded Calibration Rating Tool")
    parser.add_argument("--rater", help="Name of the developer/rater")
    parser.add_argument("--file", help="Specific file path to rate (relative to repo root)")
    parser.add_argument("--rating", choices=["HIGH", "MEDIUM", "LOW"], help="Risk rating tier")
    parser.add_argument("--rationale", default="", help="Rationale for the rating")
    
    # Use parse_known_args to ignore positional path argument if passed
    args, unknown = parser.parse_known_args()
    
    # Non-interactive mode (fully specified via arguments)
    if args.rater and args.file and args.rating:
        repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
        feedback_path = os.path.join(repo_path, "ultron", "meta", "human_feedback.jsonl")
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
            
    # Otherwise, run the new blinded rating tool
    run_blind_rating()

if __name__ == "__main__":
    main()