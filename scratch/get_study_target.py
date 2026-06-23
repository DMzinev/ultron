import subprocess
import sys
import os

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # 1. Prepare dummy filter entries
    subprocess.run([sys.executable, "scratch/prepare_blind_feedback_filter.py"], cwd=repo_path, check=True)
    
    # 2. Get next target
    res = subprocess.run([sys.executable, "scratch/get_next_blind_target.py"], cwd=repo_path, capture_output=True, text=True, check=True)
    target = res.stdout.strip()
    
    # 3. Clean up filter entries
    subprocess.run([sys.executable, "scratch/clean_blind_feedback_filter.py"], cwd=repo_path, check=True)
    
    print(target)

if __name__ == "__main__":
    main()
