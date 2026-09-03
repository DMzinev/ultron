import os
import json
import math

_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))

# Logistic coefficients live in their own file. They used to be read from (and written
# to) ultron/resources/weights.json, which actually holds the unrelated risk-signal
# weights schema {version, description, weights, scaling} and contains no beta_* keys -
# so every predict_defect_probability() call raised KeyError, and a successful training
# run would have overwritten the risk weights.
COEFFICIENTS_PATH = os.path.join(_root, "ultron", "meta", "logistic_coefficients.json")

# Must match where pledge.py appends outcomes, otherwise training never sees any data.
EXPERIMENT_LOG_PATH = os.path.join(_root, "ultron", "meta", "experiment_log.jsonl")

DEFAULT_COEFFICIENTS = {
    "beta_0": -1.0,  # intercept
    "beta_1": 0.1,   # coefficient for impact score (I)
    "beta_2": 0.5    # coefficient for fragility (1 - MKR)
}

_REQUIRED_KEYS = ("beta_0", "beta_1", "beta_2")


def load_logistic_weights():
    if not os.path.exists(COEFFICIENTS_PATH):
        save_logistic_weights(DEFAULT_COEFFICIENTS)
        return dict(DEFAULT_COEFFICIENTS)
    try:
        with open(COEFFICIENTS_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        return dict(DEFAULT_COEFFICIENTS)

    if not isinstance(loaded, dict) or not all(k in loaded for k in _REQUIRED_KEYS):
        return dict(DEFAULT_COEFFICIENTS)
    try:
        return {k: float(loaded[k]) for k in _REQUIRED_KEYS}
    except (TypeError, ValueError):
        return dict(DEFAULT_COEFFICIENTS)


def save_logistic_weights(weights):
    os.makedirs(os.path.dirname(COEFFICIENTS_PATH), exist_ok=True)
    with open(COEFFICIENTS_PATH, "w", encoding="utf-8") as f:
        json.dump({k: weights[k] for k in _REQUIRED_KEYS}, f, indent=2)

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
    Reads data from ultron/meta/experiment_log.jsonl (written by pledge.py).
    """
    log_path = EXPERIMENT_LOG_PATH
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
