import os
import sys
import tempfile
import shutil
import subprocess

# Add ultron to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ultron")))
import analyzer

def run_git(args, cwd):
    # Setup git username and email so it doesn't fail on clean systems
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, env=env)

def main():
    temp_dir = tempfile.mkdtemp()
    try:
        print("=== Scenario A: No Git Repository ===")
        # Should print: [Ultron] No git history found — bug-prone-file scaling is inactive.
        res_a = analyzer.extract_git_history(temp_dir)
        print(f"Returned: {res_a}")
        print()

        print("=== Scenario B: Git Repo, Zero Matches ===")
        # Init git repo
        run_git(["init"], temp_dir)
        # We need at least one commit so git log works, otherwise it fails with 'fatal: your current branch does not have any commits yet'
        with open(os.path.join(temp_dir, "file.py"), "w") as f:
            f.write("print('hello')\n")
        run_git(["add", "file.py"], temp_dir)
        run_git(["commit", "-m", "initial commit"], temp_dir)
        
        # Should print: [Ultron] Git history found but no fix/bug/patch-tagged commits matched — scaling has no effect.
        res_b = analyzer.extract_git_history(temp_dir)
        print(f"Returned: {res_b}")
        print()

        print("=== Scenario C: Git Repo, With Matches ===")
        # Make a commit with "fix" in message
        with open(os.path.join(temp_dir, "file.py"), "a") as f:
            f.write("# fix bug here\n")
        run_git(["add", "file.py"], temp_dir)
        run_git(["commit", "-m", "fix critical calculation bug"], temp_dir)

        # Should print nothing (returns counts)
        res_c = analyzer.extract_git_history(temp_dir)
        print(f"Returned: {res_c}")
        
    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
