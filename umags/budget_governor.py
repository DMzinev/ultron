import os
import sys
import json
import time
import hashlib
import subprocess
import unittest

def get_repo_state_hash(repo_path):
    """
    Computes a stable hash representing the current repository status (HEAD and modified state).
    """
    try:
        # 1. Get current HEAD commit hash
        res_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        head_hash = res_head.stdout.strip() if res_head.returncode == 0 else ""
        
        # 2. Get porcelain status
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        status_out = res_status.stdout if res_status.returncode == 0 else ""
        
        # 3. Get diff
        res_diff = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        diff_out = res_diff.stdout if res_diff.returncode == 0 else ""
        
        combined = head_hash + "\n" + status_out + "\n" + diff_out
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
    except Exception as e:
        _err = e
        return ""

def execute_command_cached(repo_path, cmd, force_refresh=False):
    """
    Executes a command and caches the result.
    Returns (stdout, stderr, returncode, is_cached).
    """
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    repo_hash = get_repo_state_hash(repo_path)
    
    cache_key = hashlib.sha256((cmd_str + ":" + repo_hash).encode("utf-8")).hexdigest()
    cache_dir = os.path.join(repo_path, "umags", ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "cmd_cache.json")
    
    cache_data = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as e:
            _err = e
            
    if not force_refresh and cache_key in cache_data:
        entry = cache_data[cache_key]
        return entry["stdout"], entry["stderr"], entry["returncode"], True
        
    res = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    cache_data[cache_key] = {
        "cmd": cmd_str,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "returncode": res.returncode,
        "repo_hash": repo_hash
    }
    
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        _err = e
        
    return res.stdout, res.stderr, res.returncode, False

def track_poll(repo_path, task_name, max_poll=3):
    """
    Tracks task polling occurrences. Raises TimeoutError if max_poll is exceeded.
    """
    if not task_name:
        raise ValueError("Task name must not be empty.")
        
    cache_dir = os.path.join(repo_path, "umags", ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    state_file = os.path.join(cache_dir, "poll_state.json")
    
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            _err = e
            
    task_entry = state.setdefault(task_name, {"poll_count": 0, "last_poll_time": 0.0})
    
    now = time.time()
    if now - task_entry["last_poll_time"] > 1800:
        task_entry["poll_count"] = 0
        
    task_entry["poll_count"] += 1
    task_entry["last_poll_time"] = now
    
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        _err = e
        
    if task_entry["poll_count"] > max_poll:
        raise TimeoutError(f"UMAGS Budget Governor: Polling limit exceeded for task '{task_name}' (MAX_POLL = {max_poll}). Aborting to prevent token burn.")
        
    return task_entry["poll_count"]

def get_affected_files(repo_path, changed_files):
    """
    Traces imports in codebase to identify all dependent files.
    """
    core_dir = os.path.join(repo_path, "ultron", "core")
    sys.path.append(core_dir)
    import analyzer
    
    codebase = analyzer.analyze_directory(repo_path)
    
    dependents = {}
    for rel_path, analysis in codebase.items():
        for imp in analysis.get("imports", []):
            for candidate in codebase.keys():
                cand_base = os.path.splitext(os.path.basename(candidate))[0]
                if cand_base == imp:
                    dependents.setdefault(candidate, []).append(rel_path)
                    
    affected = set(changed_files)
    queue = list(changed_files)
    while queue:
        current = queue.pop(0)
        for dep in dependents.get(current, []):
            if dep not in affected:
                affected.add(dep)
                queue.append(dep)
    return affected

def get_test_targets(repo_path, changed_files):
    """
    Returns specific test targets based on dependency fanout.
    """
    affected = get_affected_files(repo_path, changed_files)
    
    # Central hubs trigger full suite
    hubs = {"ultron/core/models.py", "ultron/core/analyzer.py", "ultron/core/risk.py", "umags/run_verification_loop.py"}
    if any(h in affected for h in hubs):
        return []
        
    basenames = {os.path.splitext(os.path.basename(f))[0] for f in affected}
    
    test_dir = os.path.join(repo_path, "ultron", "tests")
    sys.path.append(test_dir)
    import run_tests
    
    targets = []
    for name, obj in inspect_members(run_tests):
        if is_test_case_class(obj):
            for m_name, _ in inspect_functions(obj):
                if m_name.startswith("test_"):
                    matched = False
                    for b in basenames:
                        if b in m_name:
                            matched = True
                            break
                    if matched:
                        targets.append(f"{name}.{m_name}")
                        
    if not targets and changed_files:
        return []
    return targets

def inspect_members(module):
    import inspect
    return inspect.getmembers(module)

def inspect_functions(cls):
    import inspect
    return inspect.getmembers(cls, predicate=inspect.isfunction)

def is_test_case_class(obj):
    import inspect
    return inspect.isclass(obj) and issubclass(obj, unittest.TestCase)

def create_sandbox_worktree(repo_path, task_name):
    """
    Spins up an isolated sandbox worktree.
    """
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix=f"umags_wt_{task_name.lower()}_")
    res = subprocess.run(
        ["git", "worktree", "add", "--detach", temp_dir, "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"Failed to create git worktree: {res.stderr}")
    return temp_dir

def destroy_sandbox_worktree(repo_path, temp_dir):
    """
    Prunes and destroys git worktree.
    """
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=repo_path,
        capture_output=True
    )
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
