import os
import json
import time

WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta", "calibrated_weights.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta", "experiment_log.jsonl")

DEFAULT_WEIGHTS = {
    "w_impact": 0.1,
    "w_mkr": 0.5,
    "w_cest": 0.4,
    "learning_rate": 0.05
}

def load_weights():
    if not os.path.exists(WEIGHTS_PATH):
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_WEIGHTS, f, indent=2)
        return DEFAULT_WEIGHTS
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_WEIGHTS

def save_weights(weights):
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2)

def predict_change_risk(delta_i, mkr, delta_cest):
    weights = load_weights()
    # Risk is a combination of impact score change, test fragility (1 - mkr), and semantic drift
    risk = (weights["w_impact"] * delta_i) + (weights["w_mkr"] * (1.0 - mkr)) + (weights["w_cest"] * delta_cest)
    # Clip between 0.0 and 1.0
    return max(0.0, min(1.0, risk))

def learn_from_feedback(file_path, delta_i, mkr, delta_cest, actual_failure):
    """
    Stochastic Gradient Descent online learning update for software change risk prediction.
    """
    # 1. Compute prediction
    pred_risk = predict_change_risk(delta_i, mkr, delta_cest)
    
    # 2. Compute error
    error = actual_failure - pred_risk
    
    # 3. Update weights
    weights = load_weights()
    lr = weights.get("learning_rate", 0.05)
    
    weights["w_impact"] += lr * error * delta_i
    weights["w_mkr"] += lr * error * (1.0 - mkr)
    weights["w_cest"] += lr * error * delta_cest
    
    # Keep weights non-negative
    weights["w_impact"] = max(0.0, weights["w_impact"])
    weights["w_mkr"] = max(0.0, weights["w_mkr"])
    weights["w_cest"] = max(0.0, weights["w_cest"])
    
    # Re-normalize
    total = weights["w_impact"] + weights["w_mkr"] + weights["w_cest"]
    if total > 0:
        weights["w_impact"] /= total
        weights["w_mkr"] /= total
        weights["w_cest"] /= total
        
    save_weights(weights)
    
    # 4. Log to central experiment ledger
    log_entry = {
        "file": file_path,
        "prediction": {
            "delta_i": delta_i,
            "mkr": mkr,
            "delta_cest": delta_cest,
            "predicted_risk": pred_risk
        },
        "actual": {
            "failure": actual_failure
        },
        "error": {
            "value": error
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
        
    return pred_risk, error, weights
