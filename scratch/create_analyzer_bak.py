import os

original_func = """def extract_git_history(repo_path):
    \"\"\"
    Runs git log in the target repository to find the frequency of bug fixes per file.
    Returns a dictionary mapping relative file paths to their bug fix counts.
    \"\"\"
    import subprocess
    bug_fix_counts = {}
    git_dir = os.path.join(repo_path, ".git")
    if not os.path.exists(git_dir):
        return bug_fix_counts
    
    try:
        # Run git log with list of modified files in each commit
        cmd = [
            "git", "log", 
            "--name-only", 
            "--pretty=format:", 
            "-i", 
            "--grep=fix", 
            "--grep=bug", 
            "--grep=issue", 
            "--grep=hotfix", 
            "--grep=patch"
        ]
        res = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=repo_path, 
            timeout=5.0
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            for line in lines:
                file_rel = line.strip().replace("\\", "/")
                if file_rel and file_rel.endswith(".py"):
                    bug_fix_counts[file_rel] = bug_fix_counts.get(file_rel, 0) + 1
    except Exception:
        pass
    return bug_fix_counts"""

analyzer_path = "ultron/analyzer.py"
bak_path = "ultron/analyzer.py.bak"

with open(analyzer_path, "r", encoding="utf-8") as f:
    code = f.read()

# We locate where the extract_git_history function starts and replace it from there to the end
idx = code.find("def extract_git_history")
if idx != -1:
    code_bak = code[:idx] + original_func + "\n"
    with open(bak_path, "w", encoding="utf-8") as f:
        f.write(code_bak)
    print(f"[+] Successfully created backup: {bak_path}")
else:
    print("[-] Error: extract_git_history function not found in analyzer.py")
