import os
import sys
import csv
import random
import json

# Ensure the paths are configured to find ultron modules
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
for _subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join(_root, "ultron", _subdir)))
sys.path.append(_root)
sys.path.append(os.path.abspath(os.path.join(_root, "umags")))

import analyzer
import risk
import blind_rate

def run_sampling():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # 1. Select all ratable source files
    print("[*] Finding ratable source files...")
    ratable_files = blind_rate.select_ratable_files(repo_path)
    print(f"[+] Found {len(ratable_files)} ratable source files in repository.")
    
    # 2. Run risk scorer across codebase
    print("[*] Running risk scorer...")
    codebase = analyzer.analyze_directory(repo_path)
    packets = risk.evaluate_risks(codebase, ratable_files, repo_path=repo_path)
    
    # Organize by tier
    tiers = {
        "HIGH": [],
        "MEDIUM": [],
        "LOW": []
    }
    
    scored_records = []
    for p in packets:
        filename = p.file_path
        impact_score = p.impact_score
        tier = p.level
        
        tiers[tier].append((filename, impact_score))
        scored_records.append({
            "filename": filename,
            "impact_score": impact_score,
            "tier": tier
        })
        
    # Sort scored records by filename for clean output
    scored_records.sort(key=lambda x: x["filename"])
    
    # 3. Save full scored CSV
    csv_path = os.path.join(repo_path, "ultron", "meta", "blind_study_scores_DO_NOT_LOOK.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "impact_score", "tier"])
        for r in scored_records:
            writer.writerow([r["filename"], f"{r['impact_score']:.4f}", r["tier"]])
    print(f"[+] Saved full scored CSV to {csv_path}")
    
    # Print total counts per tier
    print("\n--- Total counts before sampling ---")
    for tier, items in tiers.items():
        print(f"  * {tier}: {len(items)} file(s)")
        
    # 4. Perform stratified random sampling
    # Target: 5-7 files per tier
    target_count = 6
    sampled_files = {}
    
    random.seed(42)  # Set seed for reproducibility of the sample split
    
    print("\n--- Sampling Strategy & Results ---")
    for tier, items in tiers.items():
        count_available = len(items)
        if count_available == 0:
            print(f"[Warning] Tier {tier} has 0 files. Skipping.")
            sampled_files[tier] = []
            continue
            
        # If available files are fewer than the target range (5-7), we take all of them
        # rather than silently rebalancing or inflating.
        n_to_sample = min(target_count, count_available)
        if count_available < 5:
            print(f"[!] Tier {tier} only has {count_available} file(s) available. Selecting all {count_available} (no rebalancing).")
        else:
            print(f"[+] Tier {tier} has {count_available} file(s). Randomly selecting {n_to_sample}.")
            
        sampled = random.sample(items, n_to_sample)
        # Sort by filename
        sampled.sort(key=lambda x: x[0])
        sampled_files[tier] = sampled

    # 5. Write sampled filenames only (no scores) to blind_study_sample.txt
    txt_path = os.path.join(repo_path, "ultron", "meta", "blind_study_sample.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for tier, items in sorted(sampled_files.items()):
            for filename, _ in items:
                f.write(filename + "\n")
    print(f"[+] Saved sampled filenames to {txt_path}")
    
    # 6. Show results to user
    print("\n" + "="*80)
    print("FINAL STRATIFIED SAMPLE FILES (blind_study_sample.txt)")
    print("="*80)
    for tier, items in sorted(sampled_files.items()):
        print(f"\n[{tier} TIER] - Selected {len(items)} file(s):")
        for filename, score in items:
            print(f"  - {filename:<60} (Impact Score: {score:.4f})")
            
    print("\n" + "="*80)
    print("REPRESENTATIVE SCORING REPORT (First 15 files of DO_NOT_LOOK.csv)")
    print("="*80)
    for idx, r in enumerate(scored_records[:15]):
        print(f"  {idx+1:<3} {r['filename']:<60} | Score: {r['impact_score']:>8.4f} | Tier: {r['tier']}")
    if len(scored_records) > 15:
        print(f"  ... and {len(scored_records) - 15} more files.")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_sampling()
