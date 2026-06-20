import os
import json
import time

PLEDGE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta", "active_pledges.json")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta", "experiment_log.jsonl")

def load_active_pledges():
    if not os.path.exists(PLEDGE_DB_PATH):
        return {}
    try:
        with open(PLEDGE_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_active_pledges(pledges):
    os.makedirs(os.path.dirname(PLEDGE_DB_PATH), exist_ok=True)
    with open(PLEDGE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(pledges, f, indent=2)

def create_pledge(file_path, predicted_delta_i, predicted_mkr, predicted_delta_cest):
    pledges = load_active_pledges()
    pledge_id = f"PLG_{int(time.time() * 1000)}"
    
    pledge = {
        "pledge_id": pledge_id,
        "file_path": file_path,
        "predicted_delta_i": float(predicted_delta_i),
        "predicted_mkr": float(predicted_mkr),
        "predicted_delta_cest": float(predicted_delta_cest),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    pledges[file_path] = pledge
    save_active_pledges(pledges)
    return pledge

def verify_pledge(file_path, actual_delta_i, actual_mkr, actual_delta_cest, actual_failure):
    """
    Checks actual verification outcomes against the registered pledge.
    Logs outcomes (kept vs broken) to the experiment ledger.
    """
    pledges = load_active_pledges()
    pledge = pledges.get(file_path)
    
    if not pledge:
        # If no active pledge found, we fallback to standard delta logging
        return None
        
    # Check if bounds were kept
    i_ok = actual_delta_i <= pledge["predicted_delta_i"]
    mkr_ok = actual_mkr >= pledge["predicted_mkr"]
    cest_ok = actual_delta_cest <= pledge["predicted_delta_cest"]
    
    kept = i_ok and mkr_ok and cest_ok
    
    log_entry = {
        "file": file_path,
        "pledge_id": pledge["pledge_id"],
        "pledge": {
            "predicted_delta_i": pledge["predicted_delta_i"],
            "predicted_mkr": pledge["predicted_mkr"],
            "predicted_delta_cest": pledge["predicted_delta_cest"]
        },
        "actual": {
            "delta_i": actual_delta_i,
            "mkr": actual_mkr,
            "delta_cest": actual_delta_cest,
            "failure": actual_failure
        },
        "verification": {
            "kept": kept,
            "details": {
                "impact_score_ok": i_ok,
                "mkr_ok": mkr_ok,
                "delta_cest_ok": cest_ok
            }
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Append to experiment log ledger
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
        
    # Remove from active pledges
    del pledges[file_path]
    save_active_pledges(pledges)
    
    # Trigger online confidence index calibration
    import logistic
    logistic.train_confidence_classifier()
    
    return log_entry
