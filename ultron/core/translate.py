import os

def plain_language_summary(file_result):
    """
    Returns a plain sentence describing the risk level of the file.
    Does not contain any jargon or numbers, except the coupling count N.
    """
    if file_result is None:
        return "Unknown file — risk assessment unavailable."
        
    # Extract fields supporting both AnalysisPacket and dict
    if hasattr(file_result, 'file_path'):
        filename = file_result.file_path
        level = file_result.level
        coupling = file_result.coupling_score
    else:
        filename = file_result.get('file', file_result.get('file_path', 'unknown_file'))
        level = file_result.get('level', 'LOW')
        coupling = file_result.get('coupling', file_result.get('coupling_score', 0))
        
    filename = filename.replace("\\", "/")
    N = int(coupling)
    
    if level == 'HIGH':
        return f"{filename} - High risk to change. {N} other files depend on it directly, so changes here can break things elsewhere without warning."
    elif level == 'MEDIUM':
        return f"{filename} - Moderate risk. A few other parts of the project rely on this; double check anything that calls it after editing."
    else:
        return f"{filename} - Low risk. Nothing else in the project depends on this directly - safe to experiment with."

def detailed_breakdown(file_result):
    """
    Returns a detailed string representing the underlying risk scoring numbers and formula.
    """
    if file_result is None:
        return "No details available."
        
    if hasattr(file_result, 'impact_score'):
        impact = file_result.impact_score
        complexity = file_result.complexity
        coupling = file_result.coupling_score
    else:
        impact = file_result.get('impact_score', 0.0)
        complexity = file_result.get('complexity', 1)
        coupling = file_result.get('coupling', file_result.get('coupling_score', 0))
        
    lines = [
        f"  - Impact Score: {impact:.4f}",
        f"  - Complexity: {complexity}",
        f"  - Coupling Count: {int(coupling)}",
        f"  - Formula: Impact Score = Complexity * ln(e + Coupling)"
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Translate Ultron risk profiles to plain language.")
    parser.add_argument("file_path", help="Path to the file to analyze.")
    parser.add_argument("--detail", action="store_true", help="Show detailed risk breakdown/formula.")
    
    args = parser.parse_args()
    
    try:
        repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
        
        # Configure sys.path so we can import other core modules
        for subdir in ["core", "experimental", "interfaces", "validation", "tests"]:
            sys.path.append(os.path.join(repo_path, "ultron", subdir))
        sys.path.append(repo_path)
        
        import analyzer
        import risk
        
        codebase = analyzer.analyze_directory(repo_path)
        
        # Normalize target file path relative to repo root
        target_path = os.path.abspath(args.file_path)
        rel_target = os.path.relpath(target_path, repo_path).replace("\\", "/")
        
        norm_codebase = {
            os.path.normpath(k).replace("\\", "/"): v
            for k, v in codebase.items()
        }
        
        risks = risk.evaluate_risks(norm_codebase, [rel_target], repo_path=repo_path)
        
        if not risks:
            if not os.path.exists(target_path):
                print("Unknown file — risk assessment unavailable.")
                sys.exit(1)
            else:
                dummy_result = {
                    "file_path": rel_target,
                    "level": "LOW",
                    "coupling_score": 0,
                    "impact_score": 0.0,
                    "complexity": 1
                }
                print(plain_language_summary(dummy_result))
                if args.detail:
                    print(detailed_breakdown(dummy_result))
        else:
            res = risks[0]
            print(plain_language_summary(res))
            if args.detail:
                print(detailed_breakdown(res))
                
    except Exception as e:
        print(f"Error during risk translation: {e}", file=sys.stderr)
        sys.exit(1)
