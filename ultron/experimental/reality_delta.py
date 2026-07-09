import os
import sys
import json
import time
import re
import subprocess
import shlex

# Import prediction engine for weights calibration
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
from ultron.experimental import delta

FUSION_WEIGHTS_PATH = os.path.join(_root, "ultron", "meta", "fusion_weights.json")
REALITY_DELTAS_PATH = os.path.join(_root, "ultron", "meta", "reality_deltas.jsonl")
HUMAN_FEEDBACK_PATH = os.path.join(_root, "ultron", "meta", "human_feedback.jsonl")
LOG_PATH = os.path.join(_root, "ultron", "meta", "experiment_log.jsonl")

DEFAULT_FUSION_WEIGHTS = {
    "w_test": 0.35,
    "w_git": 0.25,
    "w_runtime": 0.15,
    "w_human": 0.05,
    "w_test_runtime": 0.1,
    "w_git_human": 0.1,
    "learning_rate": 0.05
}

def load_fusion_weights():
    """
    Loads fusion weights from file. If file does not exist, initializes it.
    """
    if not os.path.exists(FUSION_WEIGHTS_PATH):
        os.makedirs(os.path.dirname(FUSION_WEIGHTS_PATH), exist_ok=True)
        try:
            with open(FUSION_WEIGHTS_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_FUSION_WEIGHTS, f, indent=2)
        except OSError as e:
            # Propagate error with context
            raise RuntimeError(f"Failed to create fusion weights file: {e}")
        return DEFAULT_FUSION_WEIGHTS.copy()
    try:
        with open(FUSION_WEIGHTS_PATH, "r", encoding="utf-8") as f:
            weights = json.load(f)
            
        # Backwards-compatible schema migration for UMAGS v6.0
        migrated = False
        for k, v in DEFAULT_FUSION_WEIGHTS.items():
            if k not in weights:
                weights[k] = v
                migrated = True
                
        if migrated:
            keys_to_normalize = [k for k in DEFAULT_FUSION_WEIGHTS if k != "learning_rate"]
            total = sum(weights[k] for k in keys_to_normalize)
            if total > 0:
                for k in keys_to_normalize:
                    weights[k] /= total
            try:
                save_fusion_weights(weights)
            except Exception as se:
                sys.stderr.write(f"[Warning] Failed to save migrated fusion weights: {se}\n")
        return weights
    except Exception as e:
        # Return defaults on corrupt file to prevent system crash
        sys.stderr.write(f"[Warning] Failed to load fusion weights, using defaults: {e}\n")
        return DEFAULT_FUSION_WEIGHTS.copy()

def save_fusion_weights(weights):
    """
    Saves fusion weights to file.
    """
    if not isinstance(weights, dict):
        raise TypeError("weights must be a dictionary")
    os.makedirs(os.path.dirname(FUSION_WEIGHTS_PATH), exist_ok=True)
    try:
        with open(FUSION_WEIGHTS_PATH, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=2)
    except OSError as e:
        raise RuntimeError(f"Failed to save fusion weights file: {e}")

def extract_git_signal(repo_path, rel_path, timestamp):
    """
    Scans subsequent git commits touching the file since timestamp for bug keywords.
    Returns a score S_git between 0.0 and 1.0.
    """
    if repo_path is None or rel_path is None or timestamp is None:
        raise ValueError("Inputs to extract_git_signal cannot be None")
    if not isinstance(repo_path, str) or not isinstance(rel_path, str) or not isinstance(timestamp, str):
        raise TypeError("Inputs to extract_git_signal must be strings")
    if not os.path.exists(repo_path):
        raise ValueError(f"repo_path does not exist: {repo_path}")

    norm_rel = os.path.normpath(rel_path).replace("\\", "/")
    
    # We query git log since the prediction timestamp
    cmd = ["git", "log", f"--since={timestamp}", "--oneline", "--", norm_rel]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path, errors="ignore")
        if res.returncode != 0:
            return 0.0
        
        bug_keywords = ["fix", "bug", "patch", "error", "fail", "issue", "crash"]
        bug_commits = 0
        for line in res.stdout.splitlines():
            line_lower = line.lower()
            if any(kw in line_lower for kw in bug_keywords):
                bug_commits += 1
                
        # Continuous score: mapping bug count to [0.0, 1.0]
        return min(1.0, 0.2 * bug_commits)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"[Warning] Git signal extraction failed: {e}\n")
        return 0.0

def extract_test_signal(repo_path, cmd):
    """
    Executes test commands and calculates the fraction of failed tests.
    """
    if repo_path is None:
        raise ValueError("repo_path cannot be None")
    if not os.path.exists(repo_path):
        raise ValueError(f"repo_path does not exist: {repo_path}")
    if not cmd:
        return 0.0

    try:
        parts = shlex.split(cmd, posix=(sys.platform != "win32"))
        res = subprocess.run(parts, capture_output=True, text=True, cwd=repo_path, timeout=15.0)
        stdout_err = res.stdout + "\n" + res.stderr
        
        if res.returncode == 0:
            return 0.0
            
        # Parse test metrics (unittest / pytest formats)
        # Unittest: "Ran 15 tests" and "failures=2" / "errors=1"
        ran_match = re.search(r"Ran\s+(\d+)\s+test", stdout_err, re.IGNORECASE)
        failed_match = re.search(r"failures=(\d+)", stdout_err, re.IGNORECASE)
        errors_match = re.search(r"errors=(\d+)", stdout_err, re.IGNORECASE)
        
        # Pytest: "5 passed, 2 failed, 1 error"
        py_fail = re.search(r"(\d+)\s+failed", stdout_err, re.IGNORECASE)
        py_err = re.search(r"(\d+)\s+error", stdout_err, re.IGNORECASE)
        py_pass = re.search(r"(\d+)\s+passed", stdout_err, re.IGNORECASE)
        
        failures = 0
        errors = 0
        total = 0
        
        if ran_match:
            total = int(ran_match.group(1))
            if failed_match:
                failures = int(failed_match.group(1))
            if errors_match:
                errors = int(errors_match.group(1))
        elif py_fail or py_err or py_pass:
            if py_fail:
                failures = int(py_fail.group(1))
            if py_err:
                errors = int(py_err.group(1))
            passed = int(py_pass.group(1)) if py_pass else 0
            total = passed + failures + errors
            
        if total > 0:
            return min(1.0, (failures + errors) / total)
            
        # Fallback if tests failed but couldn't parse count
        return 1.0
    except Exception as e:
        sys.stderr.write(f"[Warning] Test signal extraction failed: {e}\n")
        return 1.0

def extract_runtime_signal(repo_path, log_path=None):
    """
    Parses execution/runtime logs for exception frequencies and warnings.
    """
    if repo_path is None:
        raise ValueError("repo_path cannot be None")
    if not os.path.exists(repo_path):
        raise ValueError(f"repo_path does not exist: {repo_path}")

    # Fallback to standard logs if not provided or doesn't exist
    target_log = log_path
    if not target_log or not os.path.exists(target_log):
        target_log = LOG_PATH
        if not os.path.exists(target_log):
            return 0.0

    try:
        errors = 0
        warnings = 0
        with open(target_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_lower = line.lower()
                if "exception" in line_lower or "traceback" in line_lower or "error" in line_lower:
                    errors += 1
                elif "warning" in line_lower or "warn" in line_lower:
                    warnings += 1
                    
        return min(1.0, 0.2 * errors + 0.05 * warnings)
    except OSError as e:
        sys.stderr.write(f"[Warning] Runtime signal extraction failed: {e}\n")
        return 0.0

def extract_human_signal(feedback_path, rel_path):
    """
    Retrieves and averages blind ratings matching the file path.
    """
    if feedback_path is None or rel_path is None:
        raise ValueError("Inputs to extract_human_signal cannot be None")
        
    if not os.path.exists(feedback_path):
        return 0.0
        
    norm_rel = os.path.normpath(rel_path).replace("\\", "/")
    ratings = []
    
    try:
        with open(feedback_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line.strip())
                if os.path.normpath(rec.get("file", "")).replace("\\", "/") == norm_rel:
                    tier = rec.get("rater_tier")
                    if tier == "HIGH":
                        ratings.append(1.0)
                    elif tier == "MEDIUM":
                        ratings.append(0.5)
                    elif tier == "LOW":
                        ratings.append(0.0)
                        
        if ratings:
            return sum(ratings) / len(ratings)
    except Exception as e:
        sys.stderr.write(f"[Warning] Human feedback signal extraction failed: {e}\n")
        
    return 0.0

def compute_reality_score(signals, weights):
    """
    Fuses git, test, runtime, and human signals using weighted averages and interaction terms.
    """
    if not isinstance(signals, dict) or not isinstance(weights, dict):
        raise TypeError("signals and weights must be dictionaries")
        
    w_test = weights.get("w_test", 0.35)
    w_git = weights.get("w_git", 0.25)
    w_runtime = weights.get("w_runtime", 0.15)
    w_human = weights.get("w_human", 0.05)
    w_test_runtime = weights.get("w_test_runtime", 0.0)
    w_git_human = weights.get("w_git_human", 0.0)
    
    s_test = signals.get("test", 0.0)
    s_git = signals.get("git", 0.0)
    s_runtime = signals.get("runtime", 0.0)
    s_human = signals.get("human", 0.0)
    
    score = (
        (w_test * s_test)
        + (w_git * s_git)
        + (w_runtime * s_runtime)
        + (w_human * s_human)
        + (w_test_runtime * s_test * s_runtime)
        + (w_git_human * s_git * s_human)
    )
    return max(0.0, min(1.0, score))

def compute_counterfactual_attribution(signals, weights):
    """
    Computes signal causal attribution using counterfactual ablation (simulating signal removal).
    Specifically, it computes causal strength: C_i = max(0, R_actual - R_ablated_i) where S_i is ablated to 0.0.
    Setting S_i to 0.0 automatically nullifies its interaction terms.
    Normalization uses an epsilon check (1e-9) for stability.
    """
    if not isinstance(signals, dict) or not isinstance(weights, dict):
        raise TypeError("signals and weights must be dictionaries")

    r_actual = compute_reality_score(signals, weights)
    if r_actual <= 0.0:
        return {"test": 0.0, "git": 0.0, "runtime": 0.0, "human": 0.0}

    causal_strengths = {}
    for key in ["test", "git", "runtime", "human"]:
        ablated_signals = signals.copy()
        ablated_signals[key] = 0.0
        r_ablated = compute_reality_score(ablated_signals, weights)
        causal_strengths[key] = max(0.0, r_actual - r_ablated)

    total_causal = sum(causal_strengths.values())
    if total_causal > 1e-9:
        attribution = {k: v / total_causal for k, v in causal_strengths.items()}
    else:
        attribution = {"test": 0.25, "git": 0.25, "runtime": 0.25, "human": 0.25}
    return attribution


def recalibrate_system(repo_path=None):
    """
    Loads history predictions, measures actual outcomes, and applies double-calibration updates.
    """
    if repo_path is None:
        repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        
    if not os.path.exists(REALITY_DELTAS_PATH):
        print("[*] No reality_deltas.jsonl ledger found. Calibration skipped.")
        return
        
    records = []
    try:
        with open(REALITY_DELTAS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line.strip()))
                    except (ValueError, json.JSONDecodeError) as je:
                        sys.stderr.write(f"[Warning] Skipping corrupted ledger line: {je}\n")
    except OSError as e:
        raise RuntimeError(f"Failed to read reality deltas ledger: {e}")
        
    if not records:
        print("[*] Reality deltas ledger is empty.")
        return
        
    fusion_weights = load_fusion_weights()
    lr_fusion = fusion_weights.get("learning_rate", 0.05)
    
    print(f"[*] Starting calibration over {len(records)} transactions...")
    
    for idx, rec in enumerate(records):
        filepath = rec.get("file")
        timestamp = rec.get("timestamp")
        delta_i = rec.get("delta_i", 0.0)
        mkr = rec.get("mkr", 1.0)
        delta_cest = rec.get("delta_cest", 0.0)
        test_cmd = rec.get("test_cmd", "")
        log_file = rec.get("log_path", "")
        
        if not filepath or not timestamp:
            continue
            
        # 1. Extract current reality signals
        s_git = extract_git_signal(repo_path, filepath, timestamp)
        s_test = extract_test_signal(repo_path, test_cmd)
        s_runtime = extract_runtime_signal(repo_path, log_file)
        s_human = extract_human_signal(HUMAN_FEEDBACK_PATH, filepath)
        
        signals = {
            "test": s_test,
            "git": s_git,
            "runtime": s_runtime,
            "human": s_human
        }
        
        # 2. Compute actual fused reality score
        r_actual = compute_reality_score(signals, fusion_weights)
        
        # 2a. Compute Failure Attribution vector (counterfactual causal ablation)
        attribution = compute_counterfactual_attribution(signals, fusion_weights)
        
        # 3. Update prediction weights (SGD using target r_actual and guided by causal attribution)
        pred_risk, error, pred_weights = delta.learn_from_feedback(
            filepath, delta_i, mkr, delta_cest, r_actual, attribution=attribution
        )
        
        # 4. Calibrate fusion weights themselves (Standard online SGD against target_truth)
        # target_truth represents whether there was actually a defect/failure
        target_truth = 1.0 if (s_git > 0.0 or s_test > 0.0) else 0.0
        
        error_fusion = r_actual - target_truth
        fusion_weights["w_test"] -= lr_fusion * error_fusion * s_test
        fusion_weights["w_git"] -= lr_fusion * error_fusion * s_git
        fusion_weights["w_runtime"] -= lr_fusion * error_fusion * s_runtime
        fusion_weights["w_human"] -= lr_fusion * error_fusion * s_human
        
        # Interaction weight calibration updates
        w_test_runtime = fusion_weights.get("w_test_runtime", 0.1)
        w_git_human = fusion_weights.get("w_git_human", 0.1)
        
        fusion_weights["w_test_runtime"] = w_test_runtime - lr_fusion * error_fusion * s_test * s_runtime
        fusion_weights["w_git_human"] = w_git_human - lr_fusion * error_fusion * s_git * s_human
        
        # Bound weights to non-negative values
        fusion_weights["w_test"] = max(0.01, fusion_weights["w_test"])
        fusion_weights["w_git"] = max(0.01, fusion_weights["w_git"])
        fusion_weights["w_runtime"] = max(0.01, fusion_weights["w_runtime"])
        fusion_weights["w_human"] = max(0.01, fusion_weights["w_human"])
        fusion_weights["w_test_runtime"] = max(0.0, fusion_weights["w_test_runtime"])
        fusion_weights["w_git_human"] = max(0.0, fusion_weights["w_git_human"])
        
        # Re-normalize to sum to 1.0
        total_w = (
            fusion_weights["w_test"]
            + fusion_weights["w_git"]
            + fusion_weights["w_runtime"]
            + fusion_weights["w_human"]
            + fusion_weights["w_test_runtime"]
            + fusion_weights["w_git_human"]
        )
        if total_w > 0:
            fusion_weights["w_test"] /= total_w
            fusion_weights["w_git"] /= total_w
            fusion_weights["w_runtime"] /= total_w
            fusion_weights["w_human"] /= total_w
            fusion_weights["w_test_runtime"] /= total_w
            fusion_weights["w_git_human"] /= total_w
            
    save_fusion_weights(fusion_weights)
    print("[+] Recalibration complete.")
    print(f"  - New Fusion Weights: w_test={fusion_weights['w_test']:.3f}, w_git={fusion_weights['w_git']:.3f}, w_runtime={fusion_weights['w_runtime']:.3f}, w_human={fusion_weights['w_human']:.3f}, w_test_runtime={fusion_weights['w_test_runtime']:.3f}, w_git_human={fusion_weights['w_git_human']:.3f}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Reality Signal Fusion Engine CLI")
    parser.add_argument("--recalibrate", action="store_true", help="Execute double-calibration over past transactions")
    parser.add_argument("--manual-feedback", action="store_true", help="Helper to manually prompt for feedback")
    args = parser.parse_args()
    
    if args.recalibrate:
        try:
            recalibrate_system()
            sys.exit(0)
        except Exception as e:
            sys.stderr.write(f"[-] Calibration failed: {e}\n")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
