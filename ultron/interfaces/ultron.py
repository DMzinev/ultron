import argparse
import sys
import os
import json

# Add repository root and micro folders to sys.path to enable absolute/flat imports
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_dir, "..", ".."))
for _subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
    sys.path.append(os.path.abspath(os.path.join(_root, "ultron", _subdir)))
sys.path.append(_root)
sys.path.append(os.path.abspath(os.path.join(_root, "umags")))

import analyzer
import risk
import prompt
import classifier
import translate

def main():
    parser = argparse.ArgumentParser(description="Ultron: AI Pre-Execution Boundary Optimizer")
    parser.add_argument("--repo", required=True, help="Path to codebase repository")
    parser.add_argument("--intent", help="Natural language change intent description (required for prompt generation)")
    parser.add_argument("--files", help="Comma-separated relative paths of files to modify")
    parser.add_argument("--output", help="Path to save the optimized prompt (.txt)")
    parser.add_argument("--check-anomaly", help="Path to a modified file to audit for statistical anomalies")
    parser.add_argument("--typo-threshold", type=float, default=0.75, help="Spelling similarity threshold (0.0 to 1.0) for typo detection")
    parser.add_argument("--prob-threshold", type=float, default=0.0, help="Probability threshold (0.0 to 1.0) for call transition anomalies")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format to stdout")
    parser.add_argument("--detail", action="store_true", help="Show detailed risk statistics and formula breakdown")
    parser.add_argument("--brief", action="store_true", help="Generate a compact markdown context brief for AI agent orientation")
    args = parser.parse_args()
    
    def log(msg):
        print(msg, file=sys.stderr)
            
    repo_path = os.path.abspath(args.repo)
    if not os.path.isdir(repo_path):
        if args.json:
            print(json.dumps({"status": "error", "error": f"Repository path '{repo_path}' is not a directory."}))
        else:
            print(f"[-] Error: Repository path '{repo_path}' is not a directory.")
        sys.exit(1)
        
    # Standalone anomaly detection mode
    if args.check_anomaly:
        target_path = os.path.abspath(args.check_anomaly)
        if not os.path.exists(target_path):
            if args.json:
                print(json.dumps({"status": "error", "error": f"Target file '{target_path}' does not exist."}))
            else:
                print(f"[-] Error: Target file '{target_path}' does not exist.")
            sys.exit(1)
            
        log(f"[+] Ultron Classifier: Training models on {repo_path}...")
        names, probs = classifier.build_models(repo_path, exclude_file=target_path)
        log(f"[+] Ultron Classifier: Auditing target file {target_path} (typo threshold: {args.typo_threshold}, transition prob threshold: {args.prob_threshold})...")
        anomalies = classifier.audit_target_file(
            target_path, 
            names, 
            probs, 
            typo_threshold=args.typo_threshold, 
            prob_threshold=args.prob_threshold
        )
        
        if anomalies:
            if args.json:
                print(json.dumps({"status": "anomaly_detected", "anomalies": anomalies}))
            else:
                print(f"[-] WARNING: Found {len(anomalies)} statistical anomaly(s)!")
                for anom in anomalies:
                    print(f"    - [{anom['type']}] Line {anom['line']}: {anom['details']}")
            sys.exit(2)
        else:
            if args.json:
                print(json.dumps({"status": "success", "anomalies": []}))
            else:
                print("[+] Success: No statistical or structural sequence anomalies detected.")
            sys.exit(0)
            
    # Context brief mode
    if args.brief:
        log("[+] Ultron: Generating codebase context brief...")
        import context_brief
        brief = context_brief.compile_brief(repo_path)
        if args.output:
            out_path = os.path.abspath(args.output)
            try:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(brief)
                log(f"[+] Success: Context brief successfully saved to {out_path}")
            except Exception as e:
                if args.json:
                    print(json.dumps({"status": "error", "error": f"Error writing brief: {e}"}))
                else:
                    print(f"[-] Error writing brief output file: {e}")
                sys.exit(1)
        else:
            if args.json:
                print(json.dumps({"status": "success", "brief": brief}))
            else:
                if hasattr(sys.stdout, "reconfigure"):
                    try:
                        sys.stdout.reconfigure(encoding="utf-8")
                    except Exception as e:
                        sys.stderr.write(f"Warning: stdout reconfigure failed: {e}\n")
                print(brief)
        sys.exit(0)

    # Standard prompt generation mode
    if not args.intent:
        parser.error("--intent is required when not in --check-anomaly or --brief mode.")
        
    target_files = []
    if args.files:
        target_files = [f.strip() for f in args.files.split(",") if f.strip()]
        
    log("[+] Ultron: Analysing codebase structure...")
    codebase = analyzer.analyze_directory(repo_path)
    
    log("[+] Ultron: Evaluating interaction risks...")
    risks = risk.evaluate_risks(codebase, target_files, args.intent, repo_path=repo_path)
    
    if not risks:
        log("[-] Warning: No target files matched the specified intent or files argument.")
        
    log("[+] Ultron: Compiling optimized contract prompt...")
    opt_prompt = prompt.generate_optimized_prompt(args.intent, codebase, risks)
    
    if args.output:
        out_path = os.path.abspath(args.output)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(opt_prompt)
            log(f"[+] Success: Prompt successfully saved to {out_path}")
        except Exception as e:
            if args.json:
                print(json.dumps({"status": "error", "error": f"Error writing output file: {e}"}))
            else:
                print(f"[-] Error writing output file: {e}")
            sys.exit(1)
            
    if args.json:
        print(json.dumps({
            "status": "success",
            "risks": risks,
            "optimized_prompt": opt_prompt
        }))
    else:
        if not args.output:
            for r in risks:
                print(translate.plain_language_summary(r))
                if args.detail:
                    print(translate.detailed_breakdown(r))

if __name__ == "__main__":
    main()
