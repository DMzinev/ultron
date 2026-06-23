import os
import ast
import random
import json
import subprocess
import sys
import tempfile

def discover_functions_ast(code):
    """
    Parses source code and returns a list of function definitions with their argument names.
    """
    funcs = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore private functions or init methods to keep focus on boundaries
                if not node.name.startswith("__") or node.name == "__init__":
                    args = [arg.arg for arg in node.args.args]
                    funcs.append({
                        "name": node.name,
                        "args": args,
                        "is_method": False
                    })
    except Exception:
        pass
    return funcs

def generate_fuzz_values(count=50):
    """
    Generates a list of fuzzed values of various types.
    """
    base_values = [
        0, 1, -1, 100, 9999,
        0.0, 1.0, -1.0, 3.1415,
        "", "a", "test_string", "long_string_" * 10,
        [], [1, 2, 3], ["a", "b"],
        {}, {"key": "val"},
        True, False, None
    ]
    
    values = list(base_values)
    while len(values) < count:
        t = random.choice(["int", "float", "str", "list", "dict"])
        if t == "int":
            values.append(random.randint(-1000, 1000))
        elif t == "float":
            values.append(random.uniform(-100.0, 100.0))
        elif t == "str":
            values.append("".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(1, 15))))
        elif t == "list":
            values.append([random.randint(0, 10) for _ in range(random.randint(0, 5))])
        else:
            values.append({f"k{i}": random.randint(0, 5) for i in range(random.randint(0, 2))})
    return values[:count]

def compute_cest_divergence(file_path, old_code, new_code, repo_path=None):
    """
    Reframes delta CEST as Differential Input Fuzzing.
    Generates fuzzed inputs, executes both old and new code representations inside
    separate subprocess contexts, and computes the divergence rate.
    """
    if not repo_path:
        repo_path = os.path.dirname(os.path.abspath(file_path)) if file_path else os.getcwd()
        
    funcs = discover_functions_ast(old_code)
    if not funcs:
        return 0.0
        
    fuzz_inputs = {}
    fuzz_count_per_func = 40
    
    for fn in funcs:
        fn_name = fn["name"]
        n_args = len(fn["args"])
        start_idx = 1 if (n_args > 0 and fn["args"][0] == "self") else 0
        args_to_fuzz = n_args - start_idx
        
        runs = []
        for _ in range(fuzz_count_per_func):
            runs.append([random.choice(generate_fuzz_values()) for _ in range(args_to_fuzz)])
        fuzz_inputs[fn_name] = runs

    # Write temp modules and execution harness script
    with tempfile.TemporaryDirectory() as tmpdir:
        old_mod_path = os.path.join(tmpdir, "old_mod.py")
        with open(old_mod_path, "w", encoding="utf-8") as f:
            f.write(old_code)
            
        new_mod_path = os.path.join(tmpdir, "new_mod.py")
        with open(new_mod_path, "w", encoding="utf-8") as f:
            f.write(new_code)
            
        harness_code = f"""
import sys
import os
import json
import traceback

sys.path.append({repr(repo_path)})
# Add micro folders to sys.path for the subprocess
for subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join({repr(repo_path)}, "ultron", subdir)))
sys.path.append(os.path.abspath(os.path.join({repr(repo_path)}, "umags")))
sys.path.append({repr(tmpdir)})

import old_mod
import new_mod

inputs = json.loads({repr(json.dumps(fuzz_inputs))})
results = {{}}

for fn_name, runs in inputs.items():
    results[fn_name] = []
    
    old_fn = getattr(old_mod, fn_name, None)
    new_fn = getattr(new_mod, fn_name, None)
    
    if not old_fn or not new_fn:
        results[fn_name] = [("error_missing", "error_missing")] * len(runs)
        continue
        
    for args in runs:
        try:
            old_res = old_fn(*args)
            old_status = "ok"
            old_val = str(old_res)
        except Exception as e:
            old_status = "err"
            old_val = type(e).__name__
            
        try:
            new_res = new_fn(*args)
            new_status = "ok"
            new_val = str(new_res)
        except Exception as e:
            new_status = "err"
            new_val = type(e).__name__
            
        results[fn_name].append((f"{{old_status}}:{{old_val}}", f"{{new_status}}:{{new_val}}"))

print(json.dumps(results))
"""
        harness_path = os.path.join(tmpdir, "harness.py")
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(harness_code)
            
        try:
            res = subprocess.run(
                [sys.executable, harness_path],
                capture_output=True,
                text=True,
                timeout=4.0
            )
            if res.returncode != 0:
                return 1.0
                
            outcomes = json.loads(res.stdout.strip())
        except Exception:
            return 1.0
            
    total_runs = 0
    divergence_count = 0
    
    for fn_name, runs in outcomes.items():
        for old_outcome, new_outcome in runs:
            total_runs += 1
            if old_outcome != new_outcome:
                divergence_count += 1
                
    if total_runs == 0:
        return 0.0
        
    return divergence_count / total_runs
