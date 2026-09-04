import os
import sys
import json
import subprocess
import time
import traceback

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
META_DIR = os.path.join(_root, "ultron", "meta")
LEDGER_PATH = os.path.join(META_DIR, "evolution_ledger.json")

def initialize_ledger():
    os.makedirs(META_DIR, exist_ok=True)
    if not os.path.exists(LEDGER_PATH):
        default_ledger = {
            "system_version": "v1.0.0",
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evolution_cycles": 0,
            "test_pass_rate": 0.0,
            "active_hypotheses": [
                {
                    "id": "H1",
                    "text": "AST exclusion prevents baseline model contamination during anomaly detection.",
                    "status": "VALIDATED"
                },
                {
                    "id": "H2",
                    "text": "Continuous System Impact Scoring maps caller integration risk accurately.",
                    "status": "VALIDATED"
                }
            ],
            "experiment_history": []
        }
        with open(LEDGER_PATH, "w", encoding="utf-8") as f:
            json.dump(default_ledger, f, indent=2)

def read_ledger():
    initialize_ledger()
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_ledger(ledger):
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

def run_test_suite():
    print("[Meta-Ultron] Running test suite (run_tests.py)...")
    res = subprocess.run(
        [sys.executable, "ultron/tests/run_tests.py"],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )
    passed = res.returncode == 0
    print(res.stdout)
    if not passed:
        print("[Meta-Ultron] [-] Test suite FAILED!", file=sys.stderr)
        print(res.stderr, file=sys.stderr)
    else:
        print("[Meta-Ultron] [+] Test suite PASSED successfully.")
    return passed

def run_controlled_experiment():
    print("[Meta-Ultron] Setting up and running controlled experiment...")
    # Execute Ultron CLI against our sandboxed anomaly target
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env = os.environ.copy()
    env["PYTHONPATH"] = cwd
    res = subprocess.run(
        [
            sys.executable, "-m", "ultron.interfaces.ultron",
            "--repo", "scratch/test_anomaly_dir",
            "--check-anomaly", "scratch/test_anomaly_dir/target_anomaly.py",
            "--json"
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env
    )
    
    # We expect return code 2 (anomalies detected)
    print(f"[Meta-Ultron] Experiment exit code: {res.returncode}")
    
    try:
        output_json = json.loads(res.stdout.strip())
        anomalies = output_json.get("anomalies", [])
        
        # Verify anomalies caught
        typo_caught = any(anom["type"] == "Spelling Typo / Name Confusion" for anom in anomalies)
        
        success = (res.returncode == 2) and typo_caught
        
        if success:
            print("[Meta-Ultron] [+] Experiment SUCCESS: Spelling typo anomaly detected.")
            for anom in anomalies:
                print(f"   * Caught [{anom['type']}] on line {anom.get('line')}: {anom['details']}")
        else:
            print("[Meta-Ultron] [-] Experiment FAILED: Spelling typo anomaly was not detected correctly.", file=sys.stderr)
            
        # Update ledger
        ledger = read_ledger()
        ledger["evolution_cycles"] += 1
        ledger["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ledger["experiment_history"].append({
            "timestamp": ledger["last_updated"],
            "experiment_type": "Anomaly Audit Verification",
            "result": "SUCCESS" if success else "FAILED",
            "anomalies_detected": len(anomalies)
        })
        write_ledger(ledger)
        return success
    except Exception as e:
        print(f"[Meta-Ultron] [-] Experiment failed with exception: {e}", file=sys.stderr)
        traceback.print_exc()
        return False

def show_status():
    ledger = read_ledger()
    print("====================================================")
    print("               META-ULTRON STATUS                   ")
    print("====================================================")
    print(f"System Version:       {ledger['system_version']}")
    print(f"Evolution Cycles:     {ledger['evolution_cycles']}")
    print(f"Last Updated:         {ledger['last_updated']}")
    print("\nActive Hypotheses:")
    for hyp in ledger["active_hypotheses"]:
        print(f"  [{hyp['id']}] {hyp['text']} -> {hyp['status']}")
    print("\nRecent Experiment History:")
    for run in ledger["experiment_history"][-3:]:
        result_val = run.get('result') or f"Optimal T_typo: {run.get('optimal_typo_threshold', 'N/A')}"
        print(f"  * [{run['timestamp']}] {run['experiment_type']}: {result_val}")
    print("====================================================")

def log_calibration_experiment(predicted_risk, actual_failures, prediction_error, precision, recall, f1):
    ledger = read_ledger()
    ledger["evolution_cycles"] += 1
    ledger["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ledger["experiment_history"].append({
        "timestamp": ledger["last_updated"],
        "experiment_type": "Foresight Calibration",
        "predicted_risk": predicted_risk,
        "actual_failures": actual_failures,
        "prediction_error": prediction_error,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    })
    write_ledger(ledger)
    print(f"[Meta-Ultron] logged calibration to ledger: precision={precision:.2f}, recall={recall:.2f}, f1={f1:.2f}")

def synthesize_calibration_pairs(names):
    """Synthesizes positive (typo mutations) and negative (exact/distinct) word pairs for calibration."""
    import random
    name_list = list(names)[:20] if names else ["process", "init_db", "query", "close_db"]
    pos_words = []
    for name in name_list:
        if len(name) > 3:
            idx = random.randint(0, len(name) - 1)
            typo_char = chr(97 + (ord(name[idx]) - 97 + 1) % 26)
            typo = name[:idx] + typo_char + name[idx+1:]
            pos_words.append((typo, name))

    neg_words = []
    for name in name_list:
        neg_words.append((name, name))

    for i in range(len(name_list)):
        for j in range(i + 1, min(i + 4, len(name_list))):
            neg_words.append((name_list[i], name_list[j]))

    return pos_words, neg_words


def evaluate_threshold_metrics(pos_words, neg_words, t_val, sim_fn):
    """Evaluates precision, recall, and F1 score for a candidate threshold."""
    tp = sum(1 for called, correct in pos_words if t_val <= sim_fn(called, correct) < 1.0)
    fn = len(pos_words) - tp

    fp = sum(1 for called, correct in neg_words if t_val <= sim_fn(called, correct) < 1.0)
    tn = len(neg_words) - fp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


def run_threshold_calibration(repo_path):
    from ultron.core import classifier
    print(f"[Meta-Ultron] Starting threshold sweep auto-calibration on repo: {repo_path}")

    res = classifier.build_models(repo_path)
    names = res[0] if isinstance(res, (tuple, list)) else res
    pos_words, neg_words = synthesize_calibration_pairs(names)

    best_typo_t = 0.75
    best_typo_f1 = 0.0
    sweep_history = []

    for t_val in [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        p, r, f1 = evaluate_threshold_metrics(pos_words, neg_words, t_val, classifier.string_similarity)
        if f1 >= best_typo_f1:
            best_typo_f1 = f1
            best_typo_t = t_val
        sweep_history.append({
            "typo_threshold": t_val,
            "precision": p,
            "recall": r,
            "f1_score": f1
        })

    # Log to evolution ledger
    ledger = read_ledger()
    ledger["evolution_cycles"] += 1
    ledger["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ledger["experiment_history"].append({
        "timestamp": ledger["last_updated"],
        "experiment_type": "Auto-Calibration Sweep",
        "optimal_typo_threshold": best_typo_t,
        "optimal_prob_threshold": 0.0,
        "max_f1": best_typo_f1,
        "sweep_details": sweep_history
    })
    write_ledger(ledger)

    print(f"[Meta-Ultron] Calibration completed. Optimal T_typo: {best_typo_t}, F1: {best_typo_f1:.2f}")

    return {
        "success": True,
        "optimal_typo_threshold": best_typo_t,
        "optimal_prob_threshold": 0.0,
        "max_f1": best_typo_f1,
        "sweep_history": sweep_history
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Meta-Ultron Autopilot Evolution & Experiment Manager")
    parser.add_argument("--test", action="store_true", help="Execute test suite")
    parser.add_argument("--run-experiment", action="store_true", help="Execute sandboxed anomaly validation")
    parser.add_argument("--status", action="store_true", help="Print current evolution ledger status")
    args = parser.parse_args()
    
    if args.test:
        run_test_suite()
    elif args.run_experiment:
        run_controlled_experiment()
    elif args.status:
        show_status()
    else:
        # Default behavior: run tests and show status
        passed = run_test_suite()
        if passed:
            run_controlled_experiment()
        show_status()
