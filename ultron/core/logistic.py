import os
import json
import math

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
WEIGHTS_PATH = os.path.join(_root, "ultron", "resources", "weights.json")

DEFAULT_COEFFICIENTS = {
    "beta_0": -1.0,  # intercept
    "beta_1": 0.1,   # coefficient for impact score (I)
    "beta_2": 0.5    # coefficient for fragility (1 - MKR)
}

def load_logistic_weights():
    if not os.path.exists(WEIGHTS_PATH):
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_COEFFICIENTS, f, indent=2)
        return DEFAULT_COEFFICIENTS
    try:
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_COEFFICIENTS

def save_logistic_weights(weights):
    os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(weights, f, indent=2)

def sigmoid(z):
    try:
        return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
    except OverflowError:
        return 0.0 if z < 0 else 1.0

def predict_defect_probability(impact_score, mkr):
    weights = load_logistic_weights()
    z = weights["beta_0"] + (weights["beta_1"] * impact_score) + (weights["beta_2"] * (1.0 - mkr))
    return sigmoid(z)

def train_confidence_classifier():
    """
    Fits logistic regression parameters using batch gradient descent on ledger outcomes.
    Reads data from resources/experiment_log.jsonl.
    """
    log_path = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "experiment_log.jsonl"))
    if not os.path.exists(log_path):
        return load_logistic_weights()
        
    dataset = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                pred = entry.get("prediction", {})
                act = entry.get("actual", {})
                
                # Fetch features
                delta_i = pred.get("delta_i", 0.0)
                mkr = pred.get("mkr", 1.0)
                failure = act.get("failure", 0.0)
                
                dataset.append((delta_i, mkr, failure))
    except Exception:
        return load_logistic_weights()
        
    # We require a minimum dataset size to prevent over-fitting on empty/small history
    if len(dataset) < 5:
        return load_logistic_weights()
        
    # Fit coefficients
    weights = load_logistic_weights()
    beta_0 = weights.get("beta_0", -1.0)
    beta_1 = weights.get("beta_1", 0.1)
    beta_2 = weights.get("beta_2", 0.5)
    
    lr = 0.01
    epochs = 400
    
    for _ in range(epochs):
        grad_0 = 0.0
        grad_1 = 0.0
        grad_2 = 0.0
        
        for delta_i, mkr, failure in dataset:
            z = beta_0 + (beta_1 * delta_i) + (beta_2 * (1.0 - mkr))
            h = sigmoid(z)
            error = failure - h
            
            grad_0 += error
            grad_1 += error * delta_i
            grad_2 += error * (1.0 - mkr)
            
        # Update parameters
        beta_0 += lr * grad_0 / len(dataset)
        beta_1 += lr * grad_1 / len(dataset)
        beta_2 += lr * grad_2 / len(dataset)
        
    updated_weights = {
        "beta_0": beta_0,
        "beta_1": beta_1,
        "beta_2": beta_2
    }
    save_logistic_weights(updated_weights)
    return updated_weights
