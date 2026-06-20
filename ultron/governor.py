import os
import sys
import json
import subprocess
import difflib

def get_git_diff(repo_path, files):
    # Try git diff first
    try:
        chk = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=repo_path
        )
        if chk.returncode == 0 and chk.stdout.strip() == "true":
            cmd = ["git", "diff"] + files
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout
    except Exception:
        pass
        
    # Fallback to diffing against .bak files in the directory
    diff_text = ""
    for f in files:
        f_abs = os.path.join(repo_path, f)
        f_bak = f_abs + ".bak"
        if os.path.exists(f_abs) and os.path.exists(f_bak):
            try:
                with open(f_bak, "r", encoding="utf-8", errors="ignore") as f1:
                    lines1 = f1.readlines()
                with open(f_abs, "r", encoding="utf-8", errors="ignore") as f2:
                    lines2 = f2.readlines()
                diff = difflib.unified_diff(
                    lines1, lines2, 
                    fromfile=f + ".bak", 
                    tofile=f
                )
                diff_text += "".join(diff) + "\n"
            except Exception:
                pass
    return diff_text

def run_tests(repo_path, cmd_str):
    try:
        # Run command using system executable
        parts = cmd_str.split()
        res = subprocess.run(parts, capture_output=True, text=True, cwd=repo_path, timeout=10.0)
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ultron Governor: Compiles the AUDIT_PACKAGE evidence contract")
    parser.add_argument("--task", required=True, help="Task ID (e.g. Task-1)")
    parser.add_argument("--files", required=True, help="Comma-separated target files")
    parser.add_argument("--test-cmd", default="python ultron/run_tests.py", help="Test execution command")
    parser.add_argument("--outcomes", required=True, help="Expected outcomes description")
    parser.add_argument("--limitations", required=True, help="Declared known limitations or constraints")
    parser.add_argument("--self-audit", default="", help="Self-audit checklist results summary")
    args = parser.parse_args()

    repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    
    print("[*] Governor: Collecting code modifications...")
    patch_diff = get_git_diff(repo_path, files)
    
    print("[*] Governor: Running baseline tests...")
    test_ok, stdout, stderr = run_tests(repo_path, args.test_cmd)
    
    # Calculate commit hash if git repo exists
    commit_hash = "N/A (Non-Git Repo)"
    try:
        h_res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=repo_path)
        if h_res.returncode == 0:
            commit_hash = h_res.stdout.strip()
    except Exception:
        pass

    # Read plan hash from EXECUTION_PLAN.md if exists
    plan_hash = "N/A"
    plan_path = os.path.join(repo_path, "EXECUTION_PLAN.md")
    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_hash = str(hash(f.read()))
        except Exception:
            pass

    package = {
        "TASK_ID": args.task,
        "BUILDER_VERSION": "v2.0",
        "COMMIT_HASH": commit_hash,
        "PLAN_HASH": plan_hash,
        "CHANGED_FILES": files,
        "PATCH_DIFF": patch_diff,
        "EXPECTED_OUTCOMES": args.outcomes,
        "TEST_COMMANDS": [args.test_cmd],
        "RAW_STDOUT": stdout,
        "RAW_STDERR": stderr,
        "SELF_AUDIT": args.self_audit,
        "KNOWN_LIMITATIONS": args.limitations
    }

    # Write as YAML to ultron/meta/audit_package.yaml
    meta_dir = os.path.join(repo_path, "ultron", "meta")
    os.makedirs(meta_dir, exist_ok=True)
    pkg_path = os.path.join(meta_dir, "audit_package.yaml")
    
    # Simple manual YAML dumper to keep standard library-only dependency
    def dump_yaml(data, depth=0):
        lines = []
        indent = "  " * depth
        for k, v in data.items():
            if isinstance(v, list):
                lines.append(f"{indent}{k}:")
                for item in v:
                    lines.append(f"{indent}- {repr(item)}")
            elif isinstance(v, dict):
                lines.append(f"{indent}{k}:")
                lines.append(dump_yaml(v, depth + 1))
            elif isinstance(v, str) and "\n" in v:
                lines.append(f"{indent}{k}: |")
                for line in v.splitlines():
                    lines.append(f"{indent}  {line}")
            else:
                lines.append(f"{indent}{k}: {repr(v)}")
        return "\n".join(lines)

    try:
        yaml_content = dump_yaml(package)
        with open(pkg_path, "w", encoding="utf-8") as f:
            f.write(yaml_content + "\n")
        print(f"[+] Governor: Compiled AUDIT_PACKAGE successfully saved to {pkg_path}")
    except Exception as e:
        print(f"[-] Governor Error: Failed to compile package - {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
