import os
import sys
import hashlib
import json
import subprocess

def get_file_hash(filepath):
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    hashes_file = os.path.join(repo_path, "scratch", "reorg_hashes.json")
    
    monitored_files = [
        "start_ultron.py",
        "SYSTEM_MAP.md",
        "ROADMAP.md",
        "EXECUTION_PLAN.md",
        "ultron/core/__init__.py",
        "ultron/core/analyzer.py",
        "ultron/core/classifier.py",
        "ultron/core/fuzz.py",
        "ultron/core/guard.py",
        "ultron/core/logistic.py",
        "ultron/core/meta_layer.py",
        "ultron/core/models.py",
        "ultron/core/pledge.py",
        "ultron/core/predict.py",
        "ultron/core/prompt.py",
        "ultron/core/risk.py",
        "ultron/core/translate.py",
        "ultron/experimental/__init__.py",
        "ultron/experimental/delta.py",
        "ultron/experimental/design_oracle.py",
        "ultron/experimental/reality_delta.py",
        "ultron/interfaces/__init__.py",
        "ultron/interfaces/mcp_server.py",
        "ultron/interfaces/server.py",
        "ultron/interfaces/ultron.py",
        "ultron/interfaces/web/index.css",
        "ultron/interfaces/web/index.html",
        "ultron/interfaces/web/index.js",
        "ultron/tests/__init__.py",
        "ultron/tests/run_academic_tests.py",
        "ultron/tests/run_tests.py",
        "ultron/validation/__init__.py",
        "ultron/validation/ai_rater.py",
        "ultron/validation/blind_rate.py",
        "umags/governor.py",
        "umags/run_verification_loop.py",
        "umags/tools/__init__.py",
        "umags/tools/analyze_blind_study.py",
        "umags/tools/compare_ai_ratings.py",
        "umags/tools/run_stratified_sampling.py",
        "scratch/run_reorg_verification_tests.py",
        "scratch/prepare_blind_feedback_filter.py",
        "scratch/clean_blind_feedback_filter.py",
        "scratch/update_roadmap_git.py",
        "scratch/DO_NOT_RUN_simulates_human_input.py",
        "scratch/get_next_blind_target.py",
        "scratch/get_study_target.py"
    ]
    
    is_setup = os.environ.get("UMAGS_SETUP") == "1"
    
    if is_setup or not os.path.exists(hashes_file):
        current_hashes = {}
        for f in monitored_files:
            abs_path = os.path.join(repo_path, f)
            h = get_file_hash(abs_path)
            if h is not None:
                current_hashes[f] = h
        with open(hashes_file, "w", encoding="utf-8") as out:
            json.dump(current_hashes, out, indent=2)
        print(f"[+] Reorg Verification: Recorded hashes for {len(current_hashes)} files.")
    else:
        with open(hashes_file, "r", encoding="utf-8") as inp:
            expected_hashes = json.load(inp)
            
        mismatch_found = False
        for f, expected_h in expected_hashes.items():
            abs_path = os.path.join(repo_path, f)
            current_h = get_file_hash(abs_path)
            if current_h != expected_h:
                print(f"[-] Reorg Verification Mismatch: File '{f}' was modified, reverted, or deleted! (Expected: {expected_h}, Got: {current_h})")
                mismatch_found = True
                
        if mismatch_found:
            print("[-] Reorg Verification: Mismatch detected! Rejecting execution.")
            sys.exit(1)
        else:
            print("[+] Reorg Verification: All file hashes match expected reorganized layout.")

    print("[*] Reorg Verification: Running core unit tests...")
    test_script = os.path.join(repo_path, "ultron", "tests", "run_tests.py")
    res = subprocess.run([sys.executable, test_script], cwd=repo_path)
    if res.returncode != 0:
        print("[-] Reorg Verification: Core unit tests failed.")
        sys.exit(res.returncode)
        
    print("[+] Reorg Verification: All checks passed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
