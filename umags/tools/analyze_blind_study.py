import os
import json
import csv
import math

def get_ranks(v):
    """
    Computes the ranks of elements in a vector v, handling ties by averaging ranks.
    """
    sorted_v = sorted(enumerate(v), key=lambda x: x[1])
    ranks = [0] * len(v)
    i = 0
    while i < len(sorted_v):
        j = i
        while j < len(sorted_v) and sorted_v[j][1] == sorted_v[i][1]:
            j += 1
        # average rank for ties
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[sorted_v[k][0]] = avg_rank
        i = j
    return ranks

def pearson_correlation(x, y):
    """
    Computes Pearson correlation coefficient between two vectors.
    """
    n = len(x)
    if n == 0:
        return 0.0, 1.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = sum((x[i] - mean_x)**2 for i in range(n))
    den_y = sum((y[i] - mean_y)**2 for i in range(n))
    
    if den_x == 0 or den_y == 0:
        return 0.0, 1.0
        
    r = num / math.sqrt(den_x * den_y)
    return r

def gamma_half_int(x):
    """
    Computes Gamma function value for integers and half-integers.
    """
    if x <= 0:
        raise ValueError("Gamma argument must be positive")
    if x == int(x):
        val = 1
        for i in range(1, int(x)):
            val *= i
        return float(val)
    else:
        n = int(x - 0.5)
        fact_2n = 1
        for i in range(1, 2*n + 1):
            fact_2n *= i
        fact_n = 1
        for i in range(1, n + 1):
            fact_n *= i
        return (fact_2n / ((4**n) * fact_n)) * math.sqrt(math.pi)

def t_pdf(t, df):
    """
    Student's t-distribution Probability Density Function.
    """
    num = gamma_half_int((df + 1) / 2.0)
    den = math.sqrt(df * math.pi) * gamma_half_int(df / 2.0)
    return (num / den) * (1.0 + (t**2) / df) ** (-(df + 1) / 2.0)

def t_pvalue(t_stat, df):
    """
    Computes the two-tailed p-value for a given t-statistic and degrees of freedom
    using numerical integration of the Student's t PDF.
    """
    x = abs(t_stat)
    if x == 0:
        return 1.0
    steps = 10000
    h = x / steps
    s = t_pdf(0, df) + t_pdf(x, df)
    for i in range(1, steps):
        s += 2 * t_pdf(i * h, df)
    integral = (s * h) / 2.0
    cdf = 0.5 + integral
    p_val = 2.0 * (1.0 - cdf)
    return max(0.0, min(1.0, p_val))

def spearman_correlation(x, y):
    """
    Computes Spearman's rank correlation coefficient and its two-tailed p-value.
    """
    n = len(x)
    if n < 2:
        return 0.0, 1.0
    rx = get_ranks(x)
    ry = get_ranks(y)
    r_s = pearson_correlation(rx, ry)
    
    if abs(r_s) >= 1.0:
        return r_s, 0.0
        
    df = n - 2
    if df <= 0:
        return r_s, 1.0
        
    t_stat = r_s * math.sqrt(df / (1.0 - r_s**2))
    p_val = t_pvalue(t_stat, df)
    return r_s, p_val

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    feedback_path = os.path.join(repo_path, "ultron", "meta", "blind_feedback.jsonl")
    scores_path = os.path.join(repo_path, "ultron", "meta", "blind_study_scores_DO_NOT_LOOK.csv")
    
    # 1. Load feedback entries
    feedback = {}
    if os.path.exists(feedback_path):
        with open(feedback_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        feedback[entry["file"]] = entry
                    except Exception as e:
                        print(f"[Warning] Error parsing feedback line: {e}")
                        
    # 2. Load computed scores
    scores = {}
    if os.path.exists(scores_path):
        with open(scores_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores[row["filename"]] = {
                    "impact_score": float(row["impact_score"]),
                    "tier": row["tier"]
                }
                
    # 3. Join datasets
    joined_data = []
    for filepath, feed_entry in feedback.items():
        if filepath in scores:
            joined_data.append({
                "file": filepath,
                "complexity_rating": feed_entry["complexity_rating"],
                "critical_boundary": feed_entry["critical_boundary"],
                "impact_score": scores[filepath]["impact_score"],
                "tier": scores[filepath]["tier"],
                "reasoning": feed_entry.get("reasoning", "")
            })
            
    # Sort for plain printing
    joined_data.sort(key=lambda x: x["impact_score"])
    
    n = len(joined_data)
    print("=" * 80)
    print(f"UMAGS BLIND CALIBRATION STUDY ANALYSIS (n = {n})")
    print("=" * 80)
    print()
    
    # Print Joined Table
    print("=== Joined Calibration Data ===")
    print(f"{'Filename':<35} | {'Impact Score':<12} | {'Tier':<8} | {'Complexity':<10} | {'Boundary':<8} | {'Reasoning'}")
    print("-" * 105)
    for row in joined_data:
        bound_str = "YES" if row["critical_boundary"] else "NO"
        reason = row["reasoning"] if len(row["reasoning"]) <= 40 else row["reasoning"][:37] + "..."
        print(f"{row['file']:<35} | {row['impact_score']:<12.4f} | {row['tier']:<8} | {row['complexity_rating']:<10} | {bound_str:<8} | {reason}")
    print()
    
    if n < 3:
        print("[!] Sample size is too small (n < 3) to compute meaningful Spearman correlation or run p-value test.")
        return
        
    # Extract arrays
    impact_scores = [row["impact_score"] for row in joined_data]
    complexity_ratings = [row["complexity_rating"] for row in joined_data]
    boundaries = [row["critical_boundary"] for row in joined_data]
    
    # 4. Compute Spearman Correlation
    r_s, p_val = spearman_correlation(impact_scores, complexity_ratings)
    print("=== Spearman Rank Correlation ===")
    print(f"Sample Size (n):                {n}")
    print(f"Spearman's Rho (r_s):           {r_s:.4f}")
    print(f"Two-tailed P-value:             {p_val:.6f}")
    if n < 8:
        print("[!] Note: n is small (n < 8), correlation coefficient may be unstable and sensitive to individual raters.")
    print()
    
    # 5. Threshold Sweep for Critical Boundary Classification
    print("=== Threshold Sweep for Critical Boundary ===")
    best_t = None
    best_f1 = -1.0
    best_metrics = {}
    
    # Sweep from 1.0 to 20.0 in steps of 0.5
    thresholds = [x * 0.5 for x in range(2, 41)]
    
    print(f"{'Threshold':<10} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'TN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 75)
    
    for t in thresholds:
        tp = fp = fn = tn = 0
        for row in joined_data:
            pred = (row["impact_score"] >= t)
            actual = row["critical_boundary"]
            if pred and actual:
                tp += 1
            elif pred and not actual:
                fp += 1
            elif not pred and actual:
                fn += 1
            else:
                tn += 1
                
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print(f"{t:<10.1f} | {tp:<4} | {fp:<4} | {fn:<4} | {tn:<4} | {precision:<10.2%} | {recall:<10.2%} | {f1:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
            best_metrics = {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": precision, "recall": recall, "f1": f1
            }
            
    print("-" * 75)
    print(f"Optimal Threshold:              {best_t:.1f}")
    print(f"Max F1 Score:                   {best_f1:.4f}")
    print(f"Precision at Optimal:           {best_metrics['precision']:.2%}")
    print(f"Recall at Optimal:              {best_metrics['recall']:.2%}")
    print(f"Confusion Matrix:               [TP: {best_metrics['tp']}, FP: {best_metrics['fp']}, FN: {best_metrics['fn']}, TN: {best_metrics['tn']}]")
    print("=" * 80)

if __name__ == "__main__":
    main()
