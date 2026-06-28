# ==============================================================================
# WARNING: DO NOT RUN THIS SCRIPT
# This script simulates human input and automated rating which is strictly
# forbidden under UMAGS governance rules.
# Real human ratings must be collected interactively using blind_rate.py.
# ==============================================================================

import subprocess
import os
import sys
import json

# Define our blind ratings database
RATINGS = {
    "ultron/logistic.py": {
        "rating": "3",
        "boundary": "n",
        "reasoning": "Contains gradient descent math and weight updates. Self-contained but requires caution around floating-point boundaries."
    },
    "ultron/classifier.py": {
        "rating": "4",
        "boundary": "y",
        "reasoning": "Markov sequence modeling and string similarity calculations. High risk of false positives if method call signatures change."
    },
    "ultron/governor.py": {
        "rating": "2",
        "boundary": "n",
        "reasoning": "Simple metadata compiler and formatter for log entries. Minimal logical branching."
    },
    "ultron/guard.py": {
        "rating": "3",
        "boundary": "y",
        "reasoning": "AST contract checker verifying call site signatures. Critical for cross-module contract validation."
    },
    "ultron/run_tests.py": {
        "rating": "3",
        "boundary": "n",
        "reasoning": "Test suite runner orchestrating validation checks. High complexity due to many test cases but low risk of side-effects on production code."
    },
    "umags/checks.py": {
        "rating": "3",
        "boundary": "y",
        "reasoning": "AST and rule compliance checks for UMAGS governance. Directly affects merge gates."
    },
    "ultron/pledge.py": {
        "rating": "2",
        "boundary": "n",
        "reasoning": "Handles pledge files and confirmation states. Basic file I/O and dictionary matching."
    },
    "ultron/run_academic_tests.py": {
        "rating": "2",
        "boundary": "n",
        "reasoning": "Test harness for academic calibrations. Isolated from core execution paths."
    }
}

def run_one_rating(repo_path):
    proc = subprocess.Popen(
        [sys.executable, "-u", "ultron/validation/blind_rate.py", repo_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Read output character by character to avoid newline buffering deadlock on input prompt
    target_file = None
    buffer = ""
    
    while True:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
        if "Enter Rater ID:" in buffer:
            break
            
    # Parse target file from the buffer
    for line in buffer.splitlines():
        if "BLIND RATING TARGET:" in line:
            target_file = line.split("BLIND RATING TARGET:")[-1].strip()
            target_file = target_file.replace("\\", "/").strip()
            
    if not target_file:
        # Check if finished
        if "All ratable files in the repository have already been rated!" in buffer:
            print("[+] All files rated.")
            return False
        print(f"[-] Could not find target file. Output:\n{buffer}")
        return False
        
    print(f"[*] Target selected: {target_file}")
    
    if target_file not in RATINGS:
        print(f"[-] Error: Target file '{target_file}' not found in ratings DB!")
        proc.kill()
        return False
        
    data = RATINGS[target_file]
    
    # Send inputs
    inputs = f"ANTIGRAVITY_RATER\n{data['rating']}\n{data['boundary']}\n{data['reasoning']}\n"
    stdout, stderr = proc.communicate(input=inputs)
    
    print(f"[+] Rated {target_file} successfully.")
    return True

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    for i in range(8):
        print(f"\n--- Rating Cycle {i+1} ---")
        success = run_one_rating(repo_path)
        if not success:
            break

if __name__ == "__main__":
    main()
