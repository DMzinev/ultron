import os
import sys
import subprocess
import shutil
import time
import json
import ast
import urllib.request
import urllib.error
import shlex
import hashlib

# UMAGS Budget Governor (execution economics: command caching, poll depth guard, scope compression)
_budget_governor = None
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)))))
    import budget_governor as _budget_governor
except ImportError as _bg_import_err:
    print(f"[*] Budget Governor: module unavailable ({_bg_import_err}) — degrading to no-op mode.")

# UMAGS Telemetry call counter
telemetry_call_count = 0

def increment_telemetry_calls(count=1):
    global telemetry_call_count
    telemetry_call_count += count

def parse_yaml(yaml_path):
    increment_telemetry_calls(1)
    data = {}
    if not os.path.exists(yaml_path):
        return data
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
                
            if ":" in line and not line.lstrip().startswith("-"):
                parts = line.split(":", 1)
                k = parts[0].strip()
                v = parts[1].strip()
                
                # Check for multiline string
                if v == "|":
                    multiline_lines = []
                    i += 1
                    base_indent = None
                    while i < len(lines):
                        next_line = lines[i]
                        if next_line.strip() == "":
                            multiline_lines.append("")
                            i += 1
                            continue
                        indent = len(next_line) - len(next_line.lstrip())
                        if base_indent is None:
                            base_indent = indent
                        if indent >= base_indent and base_indent > 0:
                            multiline_lines.append(next_line[base_indent:].rstrip("\r\n"))
                            i += 1
                        else:
                            break
                    data[k] = "\n".join(multiline_lines)
                    continue
                else:
                    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                        v = v[1:-1]
                    if k.endswith("FILES") or k.endswith("COMMANDS"):
                        data[k] = []
                        i += 1
                        while i < len(lines):
                            next_line = lines[i]
                            if next_line.strip() == "":
                                i += 1
                                continue
                            if next_line.lstrip().startswith("-"):
                                val = next_line.lstrip()[2:].strip()
                                if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                                    val = val[1:-1]
                                data[k].append(val)
                                i += 1
                            else:
                                break
                        continue
                    else:
                        data[k] = v
            i += 1
    except Exception as e:
        print(f"Error parsing YAML: {e}")
    return data

def run_tests(repo_path, cmd, force_refresh=False):
    increment_telemetry_calls(1)
    try:
        # Cross-platform safe command split
        parts = shlex.split(cmd, posix=(sys.platform != "win32"))
        from umags.config import TEST_TIMEOUT_SECONDS
        # Use budget governor cache to skip re-running an identical command against an unchanged repo state
        if _budget_governor is not None and not force_refresh:
            try:
                stdout, stderr, returncode, is_cached = _budget_governor.execute_command_cached(
                    repo_path, parts, force_refresh=False
                )
                if is_cached:
                    print(f"[*] Budget Governor: Returning cached result for '{cmd}'")
                return returncode == 0, stdout, stderr
            except (OSError, ValueError, RuntimeError) as _cache_err:
                print(f"[*] Budget Governor: cache lookup failed ({_cache_err}) — falling through to direct execution.")
        res = subprocess.run(parts, capture_output=True, text=True, cwd=repo_path, timeout=TEST_TIMEOUT_SECONDS)
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def get_git_bug_commits_for_file(repo_path, filepath):
    increment_telemetry_calls(1)
    try:
        res = subprocess.run(
            ["git", "log", "--oneline", "--", filepath],
            capture_output=True,
            text=True,
            cwd=repo_path,
            errors="ignore"
        )
        if res.returncode == 0:
            bug_keywords = ["fix", "bug", "patch", "error", "fail", "issue", "crash"]
            commits = []
            for line in res.stdout.splitlines():
                line_lower = line.lower()
                if any(kw in line_lower for kw in bug_keywords):
                    commits.append(line)
            return commits
    except Exception as _git_err:
        print(f"[-] get_git_bug_commits_for_file: git log failed for '{filepath}': {_git_err}", file=sys.stderr)
    return []

def get_prior_failures_for_task(telemetry_path, task_id):
    increment_telemetry_calls(1)
    failures = 0
    if os.path.exists(telemetry_path):
        try:
            with open(telemetry_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line.strip())
                    if entry.get("task_id") == task_id:
                        if entry.get("judge_action") == "rejected" or entry.get("auditor_verdict") == "failed":
                            failures += 1
        except Exception as _tel_err:
            print(f"[-] get_prior_failures_for_task: failed to read telemetry at '{telemetry_path}': {_tel_err}", file=sys.stderr)
    return failures

def is_nullification_candidate(repo_path, rel_path):
    # Only verify Python files
    if not rel_path.endswith(".py"):
        return False
    # Exclude test files, runner scripts, and loop harnesses
    path_lower = rel_path.lower()
    if (
        "test" in path_lower or
        "runner" in path_lower or
        "run_verification" in path_lower or
        "failure_space" in path_lower or
        "governor" in path_lower or
        "checks" in path_lower
    ):
        return False
    # NEW_FILE_NULLIFICATION_MODE: a file that is not yet committed to git
    # (new file, never tracked) will fail git ls-files --error-unmatch.
    # Previously this caused the gate to return False and silently skip the
    # file, requiring a manual `git reset --soft` workaround before each run.
    # Now: if git ls-files fails but the file exists on disk, we treat it as
    # a new untracked file and let it through. The nullification loop's
    # is_new detection will then nullify by deletion (os.remove) rather than
    # by git checkout, which requires a prior commit.
    increment_telemetry_calls(1)
    try:
        res = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel_path],
            capture_output=True,
            cwd=repo_path
        )
        if res.returncode == 0:
            # File is committed — standard path.
            return True
        # git ls-files failed: file is either new (untracked) or absent.
        # Allow it through only if it actually exists on disk as a source file.
        f_abs = os.path.join(repo_path, rel_path)
        return os.path.exists(f_abs)
    except Exception:
        # On subprocess errors, fail closed: skip rather than corrupt state.
        return False

def get_actual_modified_files(repo_path):
    increment_telemetry_calls(3)
    modified = set()
    git_worked = False
    try:
        # Check tracked modified files (staged and unstaged)
        res = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            errors="ignore"
        )
        if res.returncode == 0:
            git_worked = True
            for line in res.stdout.splitlines():
                if line.strip():
                    modified.add(line.strip().replace("\\", "/"))
        # Check staged files
        res_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            errors="ignore"
        )
        if res_staged.returncode == 0:
            git_worked = True
            for line in res_staged.stdout.splitlines():
                if line.strip():
                    modified.add(line.strip().replace("\\", "/"))
        # Check untracked files
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            errors="ignore"
        )
        if res_status.returncode == 0:
            git_worked = True
            for line in res_status.stdout.splitlines():
                if line.startswith("??"):
                    file_path = line[3:].strip()
                    modified.add(file_path.replace("\\", "/"))
    except Exception as e:
        _err = e
        
    # Fallback to checking timestamp deltas if non-git
    if not git_worked:
        try:
            for root, _, files in os.walk(repo_path):
                # Ignore standard virtual envs / ignore dirs
                if any(x in root for x in [".git", "__pycache__", "venv", ".synapse"]):
                    continue
                for file in files:
                    if file.endswith(".bak"):
                        base_file = file[:-4]
                        base_abs = os.path.join(root, base_file)
                        if os.path.exists(base_abs):
                            rel = os.path.relpath(base_abs, repo_path).replace("\\", "/")
                            modified.add(rel)
        except Exception as e:
            _err = e
        
    return list(modified)


def get_log_bug_occurrences_for_file(repo_path, filepath):
    increment_telemetry_calls(1)
    log_path = os.path.join(repo_path, "PROJECT_LOG.md")
    occurrences = []
    if os.path.exists(log_path):
        try:
            file_base = os.path.basename(filepath)
            bug_keywords = ["bug", "fix", "failure", "revert", "error", "failed"]
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if file_base in line:
                        line_lower = line.lower()
                        if any(kw in line_lower for kw in bug_keywords):
                            occurrences.append(line.strip())
        except Exception as _log_err:
            print(f"[-] get_log_bug_occurrences_for_file: failed to read PROJECT_LOG.md: {_log_err}", file=sys.stderr)
    return occurrences

def get_original_code(repo_path, rel_path):
    increment_telemetry_calls(3)
    git_path = rel_path.replace("\\", "/")
    # 1. Prioritize Git log/show history at the file's current path
    try:
        chk = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            errors="ignore"
        )
        if chk.returncode == 0 and chk.stdout.strip() == "true":
            # Get the last commit that touched the file at its current path
            log_res = subprocess.run(
                ["git", "log", "-n", "1", "--format=%H", "--", git_path],
                capture_output=True,
                text=True,
                cwd=repo_path,
                errors="ignore"
            )
            if log_res.returncode == 0 and log_res.stdout.strip():
                commit_hash = log_res.stdout.strip()
                res = subprocess.run(
                    ["git", "show", f"{commit_hash}:{git_path}"],
                    capture_output=True,
                    text=True,
                    cwd=repo_path,
                    errors="ignore"
                )
                if res.returncode == 0:
                    return res.stdout
    except Exception as _git_show_err:
        print(f"[-] get_original_code: git show failed for '{rel_path}': {_git_show_err}", file=sys.stderr)

    # 2. Fallback to .bak file (only if not a 9-byte dummy stub)
    f_abs = os.path.join(repo_path, rel_path)
    f_bak = f_abs + ".bak"
    if os.path.exists(f_bak):
        try:
            with open(f_bak, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if len(content.strip()) > 20:
                    return content
        except Exception as _bak_err:
            print(f"[-] get_original_code: failed to read .bak for '{rel_path}': {_bak_err}", file=sys.stderr)
    return None

def analyze_complexity_drift(filepath, original_code, modified_code):
    drift_comments = []
    
    # If original_code is None (new file), compare against empty string baseline
    if original_code is None:
        original_code = ""
        drift_comments.append(f"New file '{filepath}' created.")

    # Check extension
    if not filepath.endswith(".py"):
        # For non-Python files, perform a line-count drift comparison
        orig_lines = original_code.splitlines()
        mod_lines = modified_code.splitlines()
        if len(mod_lines) > len(orig_lines) * 1.5 and len(mod_lines) > 20:
            drift_comments.append(f"File lines increased significantly from {len(orig_lines)} to {len(mod_lines)} lines.")
        return drift_comments

    # Python AST analysis
    def get_functions_stats(code):
        stats = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args_count = len(node.args.args)
                    nodes_count = len(list(ast.walk(node)))
                    stats[node.name] = {
                        "args": args_count,
                        "nodes": nodes_count
                    }
        except Exception as _ast_err:
            print(f"[-] analyze_complexity_drift: AST parse failed: {_ast_err}", file=sys.stderr)
        return stats

    orig_stats = get_functions_stats(original_code)
    mod_stats = get_functions_stats(modified_code)
    
    for func_name, mod_info in mod_stats.items():
        if func_name in orig_stats:
            orig_info = orig_stats[func_name]
            if mod_info["args"] > orig_info["args"]:
                drift_comments.append(f"Function '{func_name}' argument count increased from {orig_info['args']} to {mod_info['args']}.")
            if mod_info["nodes"] > orig_info["nodes"] * 1.5:
                drift_comments.append(f"Function '{func_name}' AST complexity/length increased significantly (from {orig_info['nodes']} to {mod_info['nodes']}).")
        else:
            drift_comments.append(f"New function '{func_name}' added with {mod_info['args']} arguments.")
            
    # Track deleted functions
    for func_name in orig_stats:
        if func_name not in mod_stats:
            drift_comments.append(f"Function '{func_name}' was removed.")
            
    return drift_comments

def load_walkthrough(repo_path):
    paths_to_try = [
        os.path.join(repo_path, "ultron", "docs", "walkthrough.md"),
        os.path.join(repo_path, "walkthrough.md"),
        "C:\\Users\\This PC\\.gemini\\antigravity\\brain\\818451b5-51e8-4841-8073-8ad3cd0e0103\\walkthrough.md"
    ]
    for p in paths_to_try:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as _wt_err:
                print(f"[-] load_walkthrough: failed to read '{p}': {_wt_err}", file=sys.stderr)
    return "No walkthrough found."

def call_anthropic(api_key, system_prompt, user_prompt, model="claude-3-5-sonnet-20241022"):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": model,
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"[-] Anthropic HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[-] Anthropic Exception: {e}", file=sys.stderr)
        return None

def call_gemini(api_key, system_prompt, user_prompt, model="gemini-1.5-pro"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "content-type": "application/json"
    }
    data = {
        "contents": [{
            "parts": [{"text": f"System Instruction: {system_prompt}\n\nUser Request:\n{user_prompt}"}]
        }],
        "generationConfig": {
            "maxOutputTokens": 1000
        }
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        print(f"[-] Gemini HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[-] Gemini Exception: {e}", file=sys.stderr)
        return None


def query_cognitive_agent(system_prompt, user_prompt):
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if anthropic_key:
        return call_anthropic(anthropic_key, system_prompt, user_prompt)
    elif gemini_key:
        return call_gemini(gemini_key, system_prompt, user_prompt)
    return None

def parse_patch_diff_lines(patch_diff):
    """
    Parses a unified diff string and returns a dictionary mapping:
      filename -> set of added/modified line numbers (1-indexed)
    """
    changed_lines = {}
    current_file = None
    current_line = 0
    
    for line in patch_diff.splitlines():
        if line.startswith("+++ "):
            parts = line.split(" ", 1)
            if len(parts) > 1:
                filename = parts[1].strip()
                if filename.startswith("b/"):
                    filename = filename[2:]
                current_file = filename.replace("\\", "/").lower()
                changed_lines[current_file] = set()
        elif line.startswith("@@ "):
            parts = line.split(" ")
            if len(parts) > 2:
                target_part = parts[2]
                if target_part.startswith("+"):
                    line_info = target_part[1:].split(",")
                    current_line = int(line_info[0])
        elif current_file is not None:
            if line.startswith("+") and not line.startswith("+++"):
                changed_lines[current_file].add(current_line)
                current_line += 1
            elif line.startswith(" "):
                current_line += 1
    return changed_lines


# ---------------------------------------------------------------------------
# PRE-FLIGHT RISK GATE — Ultron self-scan, no LLM, zero O(n) cost.
# Called from main() after sys.path is configured and changed_files is loaded.
# ---------------------------------------------------------------------------
_TIER_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

def run_preflight_risk_gate(repo_path, changed_files):
    """
    Calls Ultron's risk.evaluate_risks() on the declared target files.
    Returns 'HIGH', 'MEDIUM', or 'LOW'.

    Fail-safe: any exception returns 'HIGH' (never auto-approve on uncertainty).
    Empty risks list (non-Python targets, new files) returns 'LOW' — valid
    result because no Python code targets means no governance risk.

    Path normalization: changed_files paths are normalized to forward-slash
    relative paths before lookup, matching analyzer.analyze_directory() keys
    on both Windows and POSIX.
    """
    try:
        import analyzer as _analyzer_mod
        import risk as _risk_mod
        # Normalize declared paths to match codebase dict keys produced by
        # analyze_directory (forward-slash relative paths from repo root).
        norm_targets = [
            os.path.normpath(f).replace("\\", "/") for f in changed_files
        ]
        codebase = _analyzer_mod.analyze_directory(repo_path)
        # Build a forward-slash keyed lookup from the codebase dict.
        # analyze_directory may return OS-native paths; normalize them too.
        norm_codebase = {
            os.path.normpath(k).replace("\\", "/"): v
            for k, v in codebase.items()
        }
        risks = _risk_mod.evaluate_risks(norm_codebase, norm_targets, repo_path=repo_path)
        if not risks:
            # No Python files matched — docs, configs, or new files not yet
            # in the codebase scan.  Treat as LOW (no coupling to assess).
            return "LOW"
        # Use explicit tier ordering: HIGH=2 > MEDIUM=1 > LOW=0.
        # Never use string max() — "MEDIUM" > "LOW" > "HIGH" lexicographically.
        best = max(risks, key=lambda r: _TIER_ORDER.get(r.level, 2))
        return best.level
    except Exception as e:
        print(f"[!] PRE-FLIGHT ERROR: risk gate threw exception ({e}) — defaulting to HIGH (fail-safe).")
        return "HIGH"


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    
    # Configure sys.path early so that pre-flight risk gate can import ultron modules
    for subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
        sys.path.append(os.path.abspath(os.path.join(repo_path, "ultron", subdir)))
    sys.path.append(repo_path)
    
    pkg_path = os.path.join(repo_path, "ultron", "meta", "audit_package.yaml")
    
    if not os.path.exists(pkg_path):
        print(f"[-] Error: Audit package not found at {pkg_path}. Run governor first.")
        sys.exit(1)
        
    package = parse_yaml(pkg_path)
    task_id = package.get("TASK_ID", "Unknown-Task")
    task_type = package.get("TASK_TYPE", "LOGIC_CHANGE").strip().upper()
    if task_type not in ("LOGIC_CHANGE", "STRUCTURE_ONLY"):
        print(f"[!] Warning: Unrecognized TASK_TYPE '{task_type}', defaulting to LOGIC_CHANGE.")
        task_type = "LOGIC_CHANGE"
    changed_files = package.get("CHANGED_FILES", [])
    test_commands = package.get("TEST_COMMANDS", [])

    # Budget Governor: enforce MAX_POLL=3 guard before doing any work
    if _budget_governor is not None:
        try:
            poll_count = _budget_governor.track_poll(repo_path, task_id, max_poll=3)
            print(f"[*] Budget Governor: Poll #{poll_count} for task '{task_id}'.")
        except TimeoutError as te:
            print(f"[!] Budget Governor: {te}")
            sys.exit(2)

    # =========================================================================
    # 0. PRE-FLIGHT RISK GATE
    # Runs before Builder/Auditor/Judge/Historian steps.
    # Determines ceremony level using Ultron's own risk engine (no LLM, no human).
    # Fail-safe: gate error → HIGH (never silently auto-approve on uncertainty).
    # =========================================================================
    print("====================================================================")
    print("🛫  PRE-FLIGHT RISK GATE (Ultron self-scan)")
    print("====================================================================")
    category_b = package.get("CATEGORY_B", "false").strip().lower() == "true"
    print(f"[*] Pre-flight: Scanning {len(changed_files)} target file(s) via risk.evaluate_risks()...")
    preflight_tier = run_preflight_risk_gate(repo_path, changed_files)
    print(f"[*] Pre-flight result: tier={preflight_tier} | task_type={task_type} | category_b={category_b}")

    # FAST PATH: LOW/MEDIUM + STRUCTURE_ONLY + no Category-B.
    # Skips only the O(n) per-file loops (nullification, per-file AST drift).
    # The independent Critic subagent review still happened at planning time
    # (satisfying UMAGS §1). The verification loop itself is the Judge role.
    fast_path = (
        preflight_tier in ("LOW", "MEDIUM")
        and task_type == "STRUCTURE_ONLY"
        and not category_b
    )
    # ESCALATE: HIGH tier or Category-B → external human review required.
    escalate = (preflight_tier == "HIGH") or category_b

    # Run Multi-Reality Calibration Engine recalibration (v4.0) only if not fast path
    if not fast_path:
        print("[*] Running Multi-Reality Signal Fusion Engine recalibration...")
        try:
            import reality_delta
            reality_delta.recalibrate_system(repo_path)
        except Exception as e:
            print(f"[-] Recalibration failed to run: {e}")
    else:
        print("[*] Pre-flight: Fast path active. Skipping Multi-Reality Signal Fusion Engine recalibration.")

    if fast_path:
        print("[\u2713] PRE-FLIGHT → FAST PATH: LOW/MEDIUM risk + STRUCTURE_ONLY + no Category-B.")
        print("    Skipping: O(n) nullification loop, per-file AST drift, cognitive LLM review.")
        print("    Running:  scope check + single test suite (standard Auditor/Judge steps).")
    else:
        reasons = []
        if preflight_tier == "HIGH":
            reasons.append(f"tier={preflight_tier}")
        if category_b:
            reasons.append("Category-B=true")
        if task_type != "STRUCTURE_ONLY":
            reasons.append(f"task_type={task_type}")
        print(f"[!] PRE-FLIGHT → FULL PATH ({', '.join(reasons) if reasons else 'default'}).")
        if escalate:
            print("[!] Note: ESCALATE will be printed at completion — external review required.")
    print()

    print(f"====================================================================")
    print(f"🛠️  BUILDER (Gemini Pro)")
    print(f"====================================================================")
    print(f"I have compiled the AUDIT_PACKAGE contract for {task_id}.")
    print(f"Target Files: {', '.join(changed_files)}")
    print(f"Expected Outcomes: {package.get('EXPECTED_OUTCOMES')}")
    print(f"Known Limitations: {package.get('KNOWN_LIMITATIONS')}")
    print(f"Handoff package compiled and sent to Auditor subagent...")
    print()
    
    # 2. AUDITOR STEPS
    print(f"====================================================================")
    # Auditor runs: (a) mechanical scope/test checks always, (b) cognitive LLM review
    # only when ANTHROPIC_API_KEY or GEMINI_API_KEY is set in the environment.
    # The label below reflects which path will execute.
    _has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    _auditor_label = "🔍 AUDITOR (Mechanical + Cognitive LLM)" if _has_api_key else "🔍 AUDITOR (Mechanical Scope & Test Verifier — no API key set)"
    print(_auditor_label)
    print(f"====================================================================")
    print(f"[*] Auditor: Starting independent verification for {task_id}...")
    auditor_comments = []
    auditor_verified = True

    
    # Check patch diff
    patch_diff = package.get("PATCH_DIFF", "").strip()
    if not patch_diff:
        auditor_comments.append("Objection: Patch diff is empty or missing.")
        auditor_verified = False
        print("[-] Verification failed: Empty patch diff.")
    else:
        print("[+] Verification passed: Valid patch diff found.")
        
    # 1. Independent Scope Check (Jurisdiction Fraud Prevention)
    print("[*] Auditor: Independently verifying changed files scope...")
    actual_modified = get_actual_modified_files(repo_path)
    norm_declared = set(os.path.normpath(f).replace("\\", "/").lower() for f in changed_files)
    undeclared_source = []
    for f in actual_modified:
        if f.endswith((".py", ".js", ".html", ".css")):
            norm_f = os.path.normpath(f).replace("\\", "/").lower()
            if norm_f not in norm_declared:
                undeclared_source.append(f)
                
    if undeclared_source:
        auditor_comments.append(f"Objection: Jurisdiction fraud / scope manipulation. Actual modified source files: {', '.join(undeclared_source)} were not declared in CHANGED_FILES.")
        auditor_verified = False
        print(f"[-] Verification failed: Scope discrepancy. Undeclared source changes: {undeclared_source}")
    else:
        print("[+] Verification passed: Actual modified source files match declared scope.")
        
    # Execute tests
    test_failed_baseline = False
    for cmd in test_commands:
        print(f"[*] Running test suite: {cmd}")
        passed, stdout, stderr = run_tests(repo_path, cmd)
        if not passed:
            auditor_comments.append(f"Objection: Test suite command '{cmd}' failed under baseline modified code.")
            auditor_verified = False
            test_failed_baseline = True
            print("[-] Verification failed: Baseline test suite failed.")
        else:
            print("[+] Verification passed: Baseline test suite passed.")
            
    # Programmatic Nullification Check (Anti-Test Laundering)
    # SKIPPED for STRUCTURE_ONLY tasks: content did not change, reverting a moved file
    # would only confirm that an empty/old path makes tests fail, which is trivially true.
    if task_type == "STRUCTURE_ONLY" or fast_path:
        print("[*] Nullification check: SKIPPED (STRUCTURE_ONLY or FAST PATH — no content changed / O(n) budget rule).")
    elif not test_failed_baseline and changed_files and preflight_tier != "HIGH":
        # O(n) TOKEN-BUDGET RULE: nullification scales with file count.
        # Only runs when pre-flight tier is HIGH; skipped at LOW/MEDIUM.
        print(f"[*] Nullification check: SKIPPED (pre-flight tier={preflight_tier} — O(n) budget rule; applies at HIGH only).")
        nullification_passed = True
    elif not test_failed_baseline and changed_files:
        print("[*] Running programmatic Nullification check (O(n) — pre-flight tier HIGH)...")
        nullification_passed = True
        
        for f in changed_files:
            if not is_nullification_candidate(repo_path, f):
                print(f"[+] Skipping nullification check for non-source/untracked file: {f}")
                continue
                
            f_abs = os.path.join(repo_path, f)
            f_bak = f_abs + ".bak"
            
            # If no .bak exists, check if git can revert it temporarily
            has_bak = os.path.exists(f_bak)
            temp_stored = False
            
            try:
                # Backup current modified file
                temp_backup = f_abs + ".tmp_verification"
                increment_telemetry_calls(1)
                shutil.copy2(f_abs, temp_backup)
                temp_stored = True
                
                # Restore original
                if has_bak:
                    increment_telemetry_calls(1)
                    shutil.copy2(f_bak, f_abs)
                else:
                    # Check if file is new relative to the task's baseline commit (last commit touching PROJECT_LOG.md)
                    is_new = True
                    try:
                        baseline = "HEAD"
                        res_log = subprocess.run(
                            ["git", "log", "-n", "1", "--format=%H", "--", "PROJECT_LOG.md"],
                            cwd=repo_path,
                            capture_output=True,
                            text=True
                        )
                        if res_log.returncode == 0 and res_log.stdout.strip():
                            baseline = res_log.stdout.strip()
                            
                        chk_head = subprocess.run(
                            ["git", "cat-file", "-e", f"{baseline}:{f}"],
                            cwd=repo_path,
                            capture_output=True
                        )
                        if chk_head.returncode == 0:
                            is_new = False
                    except Exception as e:
                        _err = e
                    
                    if is_new:
                        if os.path.exists(f_abs):
                            os.remove(f_abs)
                    else:
                        increment_telemetry_calls(1)
                        subprocess.run(["git", "checkout", f], cwd=repo_path, capture_output=True)
                
                # Run the tests - they MUST fail now!
                # force_refresh=True: file state changed during nullification — cache must be bypassed.
                for cmd in test_commands:
                    passed, _, _ = run_tests(repo_path, cmd, force_refresh=True)
                    if passed:
                        # Tests passed even when logic was nullified! Test laundering!
                        nullification_passed = False
                        auditor_comments.append(f"Objection: Test laundering detected in '{f}'. Tests passed even after logic nullification.")
                        print(f"[-] Nullification failed: Tests passed on nullified code for '{f}'!")
                    else:
                        print(f"[+] Nullification passed: Tests failed as expected on nullified code for '{f}'.")
            except Exception as e:
                print(f"[-] Nullification error: {e}")
            finally:
                # Restore current modified file
                if temp_stored and os.path.exists(temp_backup):
                    shutil.copy2(temp_backup, f_abs)
                    os.remove(temp_backup)
                    
        if not nullification_passed:
            auditor_verified = False    # Programmatic UMAGS AST-based Rules and Residual Risk checks
    # SKIPPED for STRUCTURE_ONLY or FAST PATH: relocated-but-unmodified files produce only
    # false-positive drift noise (every moved function appears "new").
    if task_type == "STRUCTURE_ONLY" or fast_path:
        print("[*] AST compliance + Residual Risk checks: SKIPPED (STRUCTURE_ONLY or FAST PATH — no content changed).")
        R = 0
    else:
        print("[*] Running UMAGS programmatic AST compliance checks...")
        sys.path.append(repo_path)
        R = 0
        try:
            from umags.checks import check_file_ast
            from umags.failure_space import analyze_failure_space
            
            # Parse diff lines to get modified line numbers
            diff_lines = parse_patch_diff_lines(patch_diff)
            
            ast_ok = True
            for f in changed_files:
                f_abs = os.path.join(repo_path, f)
                if os.path.exists(f_abs) and f.endswith(".py"):
                    f_norm = f.replace("\\", "/").lower()
                    if f_norm in diff_lines:
                        file_changed_lines = diff_lines[f_norm]
                    else:
                        # If file is untracked (new file), check all lines.
                        # If it is tracked but unmodified in diff, check no lines.
                        is_untracked = False
                        try:
                            increment_telemetry_calls(1)
                            res = subprocess.run(["git", "ls-files", "--error-unmatch", f], cwd=repo_path, capture_output=True)
                            is_untracked = (res.returncode != 0)
                        except Exception as e:
                            _err = e
                        file_changed_lines = None if is_untracked else set()
                    
                    increment_telemetry_calls(1)
                    violations = check_file_ast(f_abs, changed_lines=file_changed_lines)
                    if violations:
                        ast_ok = False
                        for v in violations:
                            obj = f"AST Violation in '{f}' line {v['line']}: [{v['rule']}] {v['message']}"
                            auditor_comments.append(f"Objection: {obj}")
                            print(f"[-] {obj}")
            if ast_ok:
                print("[+] Programmatic AST compliance checks passed.")
            else:
                auditor_verified = False
                
            print("[*] Running programmatic Failure Space / Residual Risk analysis...")
            untested, missing_bounds, R = analyze_failure_space(repo_path, changed_files, diff_lines=diff_lines)
            print(f"  - Untested Paths: {', '.join(untested) if untested else 'None'}")
            print(f"  - Missing Boundary Cases: {', '.join(missing_bounds) if missing_bounds else 'None'}")
            print(f"  - Residual Risk Score (R): {R}")
            
            if R > 0:
                auditor_comments.append(f"Objection: Residual Risk Score R={R} is above threshold (0). Resolve untested paths or missing boundary guards/tests.")
                auditor_verified = False
                print(f"[-] Verification failed: Residual Risk Score R={R} > 0.")
            else:
                print("[+] Verification passed: Residual Risk Score R=0.")
        except Exception as e:
            print(f"[-] UMAGS Engine error during execution verification: {e}")
            auditor_comments.append(f"Objection: UMAGS engine verification failed to execute: {e}")
            auditor_verified = False


    # Cognitive Auditor check (evaluates code patch and task bounds, walkthrough is strictly excluded to prevent bias)
    # SKIPPED for STRUCTURE_ONLY or FAST PATH: no logic changed, semantic review
    # of relocated code or low-risk structural tasks produces only noise.
    if task_type == "STRUCTURE_ONLY" or fast_path:
        print("[*] Cognitive Auditor review: SKIPPED (STRUCTURE_ONLY or FAST PATH — no content changed).")
    elif os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        print("[*] Auditor: Querying cognitive agent for semantic review (isolated from walkthrough)...")
        system_prompt = (
            "You are a hostile Auditor. Review the task specification, declared target files, and code patch (physics). "
            "Identify any logical inconsistencies, incomplete implementations, or design flaws in the code. "
            "Do NOT assume intentions or read narrative rationalizations. "
            "If you have objections, prefix each objection with 'Objection: ' on a new line. Be concise."
        )
        user_prompt = f"""
Task ID: {task_id}
Target Files: {changed_files}
Expected Outcomes: {package.get('EXPECTED_OUTCOMES')}
Known Limitations: {package.get('KNOWN_LIMITATIONS')}

Patch Diff:
{patch_diff}
"""
        cognitive_response = query_cognitive_agent(system_prompt, user_prompt)
        if cognitive_response:
            print("\n--- Auditor Cognitive Review ---")
            print(cognitive_response)
            print("--------------------------------\n")
            # Parse objections from response
            for line in cognitive_response.splitlines():
                if line.strip().startswith("Objection:"):
                    obj_text = line.split("Objection:", 1)[1].strip()
                    auditor_comments.append(f"Cognitive Objection: {obj_text}")
                    auditor_verified = False
        else:
            print("[!] Cognitive Auditor warning: API query returned None (network error or invalid key). Falling back to programmatic checks.")

    auditor_verdict = "VERIFIED" if auditor_verified else "FAILED"
    print(f"\nVerdict: {auditor_verdict}")
    if auditor_comments:
        for c in auditor_comments:
            print(f"  - {c}")
    print()

    # 2.5 SENTINEL STEPS (Assumption & Entropy Auditor)
    print(f"====================================================================")
    print(f"🛡️  SENTINEL (Assumption & Entropy Auditor)")
    print(f"====================================================================")
    print("[*] Sentinel: Gating is currently DORMANT. Skipping checks.")
    sentinel_verified = True
    sentinel_comments = []
    total_integrity = 1.0
    total_fragility = 0.0
    entropy_delta = 0.0
    silent_assumptions = []
    sentinel_verdict = "VERIFIED"
    print()

    # 3. JUDGE STEPS (Legitimization - Constitutional Court)
    print(f"====================================================================")
    print(f"⚖️  JUDGE (Gemini Pro)")
    print(f"====================================================================")
    print("[*] Judge: Resolving dispute and verifying merge permits...")
    
    judge_approved = False
    judge_comments = []
    
    if auditor_verdict != "VERIFIED":
        judge_comments.append("Objection: Auditor verification failed.")
    
    if sentinel_verdict != "VERIFIED":
        judge_comments.append("Objection: Sentinel verification failed.")
        
    if not task_id:
        judge_comments.append("Objection: Invalid or missing TASK_ID.")
        
    log_path = os.path.join(repo_path, "PROJECT_LOG.md")
    
    # Cognitive Judge review (evaluates the auditor output, walkthrough/intent, and determines final arbitration)
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        print("[*] Judge: Querying cognitive agent to arbitrate objections...")
        walkthrough_content = load_walkthrough(repo_path)
        system_prompt = (
            "You are a strict Constitutional Court Judge. Your only rule is to verify if reality satisfies the contract. "
            "Do not try to merge or optimize stories or intents. "
            "Confirm: Is the Auditor Verdict strictly VERIFIED? Are there any unresolved scope, test, or code objections? "
            "Review the Builder's walkthrough (intent) against the Auditor's objections (reality). "
            "Provide your verdict and rationale in 2-3 sentences. Start your final decision line with either 'Verdict: APPROVED' or 'Verdict: REJECTED'."
        )
        user_prompt = f"""
Task ID: {task_id}
Expected Outcomes: {package.get('EXPECTED_OUTCOMES')}
Known Limitations: {package.get('KNOWN_LIMITATIONS')}

Auditor Verdict: {auditor_verdict}
Auditor Objections:
{chr(10).join(auditor_comments) if auditor_comments else "None"}

Sentinel Verdict: {sentinel_verdict}
Sentinel Objections:
{chr(10).join(sentinel_comments) if sentinel_comments else "None"}

Builder Walkthrough (Intended Reality):
{walkthrough_content}
"""
        judge_response = query_cognitive_agent(system_prompt, user_prompt)
        if judge_response:
            print("\n--- Judge Rationale ---")
            print(judge_response)
            print("-----------------------\n")
            # Parse verdict
            if "Verdict: APPROVED" in judge_response and not judge_comments:
                judge_approved = True
            else:
                judge_approved = False
                if "Verdict: REJECTED" in judge_response:
                    judge_comments.append("Objection: Cognitive Judge rejected the changes.")
                elif judge_comments:
                    judge_comments.append("Objection: Programmatic checks failed, overriding cognitive approval.")
        else:
            print("[!] Cognitive Judge warning: API query returned None (network error or invalid key). Falling back to programmatic verdict.")
            if not judge_comments:
                judge_approved = True
    else:
        # Default programmatic merge verification
        if not judge_comments:
            judge_approved = True

    if judge_approved:
        print(f"[+] Status change approved. Authorizing merge for {task_id}.")
        # Update ROADMAP.md status
        roadmap_path = os.path.join(repo_path, "ROADMAP.md")
        
        # Read and replace status markers
        def update_status_file(filepath):
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        # If matches silent failure section
                        if "Git-history bug-fix extraction" in line and "🔇" in line:
                            line = line.replace("🔇", "⚠️")
                            print(f"[+] Updated '{filepath}' status to working but unvalidated.")
                        new_lines.append(line)
                        
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                except Exception as e:
                    print(f"[-] Failed to update status in '{filepath}': {e}")
                    
        update_status_file(roadmap_path)
        
        # Note: PROJECT_LOG.md reviewer checks must be left as PENDING and filled in manually.
        print("[*] Note: External verification in PROJECT_LOG.md must be filled in manually by the human operator.")
                
        # NOTE: Per-file reality_delta/delta.predict_change_risk prediction logging has been
        # REMOVED. The P-values produced by delta.predict_change_risk are unvalidated
        # (no ground-truth outcome data, no disjoint evaluation set, no calibration evidence).
        # Re-enable only after ROADMAP.md validation requirements for this subsystem are met.
        # The O(n_files) per-file loop was also the primary source of redundant compute on
        # structural-only tasks — see PROTOCOL.md task-type tiers.
                
        print("Verdict: APPROVED")
    else:
        print(f"[-] Status change REJECTED for {task_id} due to Judge objections:")
        for comment in judge_comments:
            print(f"  - {comment}")
        print("Verdict: REJECTED")
    print(f"====================================================================")
    print()


    # 4. HISTORIAN STEPS (Memory - Forensic Anchoring)
    print(f"====================================================================")
    print(f"📜 HISTORIAN (Gemini Pro)")
    print(f"====================================================================")
    print("[*] Historian: Scanning repository transaction ledger & history...")
    
    # 4a. Telemetry file path
    telemetry_path = os.path.join(repo_path, "ultron", "meta", "audit_telemetry.jsonl")
    
    # 4b. Scan log for occurrences
    task_occurrences = 0
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                task_occurrences = content.count(task_id)
        except Exception as _proj_log_err:
            print(f"[-] Historian: failed to read PROJECT_LOG.md: {_proj_log_err}", file=sys.stderr)
            
    print(f"[+] Repository records indicate {task_occurrences} log entries matching '{task_id}'.")
    history_comments = []
    if task_occurrences > 1:
        history_comments.append(f"Warning: This is the {task_occurrences}-th attempt/modification containing reference to '{task_id}'. Watch for architectural regression cycles.")
    else:
        history_comments.append("Verification history: Clean transition, first unique entry.")
        
    # 4c. Repeated False Claims check
    prior_failures = get_prior_failures_for_task(telemetry_path, task_id)
    if prior_failures > 0:
        history_comments.append(f"Warning: Detected {prior_failures} previous FAILED/REJECTED verification runs for '{task_id}'. Check if fixes are superficial or if issues recur.")
    else:
        history_comments.append("Integrity check: No prior failed verification loops detected for this task.")
        
    # 4d. Recurring Bug Classes check (Git commit check & PROJECT_LOG.md check for target files)
    for f in changed_files:
        bug_commits = get_git_bug_commits_for_file(repo_path, f)
        log_bugs = get_log_bug_occurrences_for_file(repo_path, f)
        total_bugs = len(bug_commits) + len(log_bugs)
        
        if total_bugs >= 3:
            history_comments.append(f"Warning: File '{f}' has a history of {total_bugs} bug/fix occurrences (Git: {len(bug_commits)}, Log: {len(log_bugs)}). It is a recurring bug hot-spot.")
        elif total_bugs > 0:
            history_comments.append(f"Note: File '{f}' has {total_bugs} past bug/fix occurrences (Git: {len(bug_commits)}, Log: {len(log_bugs)}).")
            
    # 4e. Audit Blind Spots check
    try:
        for subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
            sys.path.append(os.path.abspath(os.path.join(repo_path, "ultron", subdir)))
        sys.path.append(repo_path)
        import analyzer
        import risk
        codebase = analyzer.analyze_directory(repo_path)
        risks = risk.evaluate_risks(codebase, changed_files, repo_path=repo_path)
        mkr_map = risk.load_mkr_stats()
        
        for r in risks:
            if r.level == "HIGH":
                has_mutation = False
                target_base = os.path.basename(r.file_path)
                for k in mkr_map.keys():
                    if os.path.basename(k) == target_base:
                        has_mutation = True
                        break
                if not has_mutation:
                    history_comments.append(f"Warning: Audit Blind Spot detected! '{r.file_path}' is classified as HIGH RISK but has no mutation testing records in the ledger.")
    except Exception as e:
        history_comments.append(f"Risk evaluation warning: Could not verify risk tiers/mutation status ({e}).")
        
    # 4f. Complexity Drift check
    for f in changed_files:
        f_abs = os.path.join(repo_path, f)
        if os.path.exists(f_abs):
            try:
                orig_code = get_original_code(repo_path, f)
                increment_telemetry_calls(1)
                with open(f_abs, "r", encoding="utf-8", errors="ignore") as file_obj:
                    mod_code = file_obj.read()
                drift = analyze_complexity_drift(f, orig_code, mod_code)
                for d in drift:
                    history_comments.append(f"Architecture Drift (in '{f}'): {d}")
            except Exception as e:
                _err = e
                
    for h in history_comments:
        print(f"  - {h}")
    print()
    
    # 4g. Commit telemetry record (Forensic Anchor)
    patch_hash = "N/A"
    if patch_diff:
        try:
            patch_hash = hashlib.sha256(patch_diff.encode("utf-8")).hexdigest()
        except Exception as e:
            _err = e
            
    os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)
    telemetry_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_id": task_id,
        "commit_hash": package.get("COMMIT_HASH", "N/A"),
        "plan_hash": package.get("PLAN_HASH", "N/A"),
        "patch_hash": patch_hash,
        "builder_status": "claimed_done",
        "auditor_verdict": auditor_verdict.lower(),
        "sentinel_verdict": sentinel_verdict.lower(),
        "foundation_integrity": total_integrity,
        "future_fragility": total_fragility,
        "entropy_delta": round(entropy_delta, 4),
        "judge_action": "accepted" if judge_approved else "rejected",
        "nullification_test_run": not (task_type == "STRUCTURE_ONLY" or fast_path or preflight_tier != "HIGH"),
        "discrepancies_found": len(auditor_comments) + len(sentinel_comments),
        "longitudinal_warnings": len([h for h in history_comments if "Warning" in h or "Spot" in h or "Drift" in h]),
        "residual_risk_score": R,
        "verification_path": "FAST" if fast_path else "FULL",
        "telemetry_call_count": telemetry_call_count
    }
    try:
        with open(telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(telemetry_entry) + "\n")
        print("[+] Telemetry record successfully written by Historian.")
    except Exception as e:
        print(f"[-] Telemetry write failed: {e}")

    # ESCALATE — printed last for maximum visibility.
    # Indicates external human review is required before closing this task.
    if escalate:
        print()
        print("====================================================================")
        print("ESCALATE: requires external review")
        _esc_reasons = []
        if preflight_tier == "HIGH":
            _esc_reasons.append(f"pre-flight tier={preflight_tier}")
        if category_b:
            _esc_reasons.append("Category-B data claims present")
        print(f"  Reason:  {', '.join(_esc_reasons) if _esc_reasons else 'full-ceremony task'}")
        print("  Action:  Paste this output into PROJECT_LOG.md 'External verification' field.")
        print("====================================================================")


if __name__ == "__main__":
    main()


