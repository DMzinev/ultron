import os
import sys
import time
import math
import json

from ultron.core import analyzer
from ultron.core import risk

def generate_directory_tree(dirpath):
    if not dirpath:
        raise ValueError("Directory path must not be empty.")
    tree_lines = []
    ignore_dirs = {'.git', 'venv', 'env', '__pycache__', '.synapse', '.agents', 'study_materials', 'study_portal_qa'}
    
    def walk_dir(current_path, prefix=""):
        if not current_path:
            return
        try:
            entries = sorted(os.listdir(current_path))
        except Exception:
            return
            
        entries = [e for e in entries if e not in ignore_dirs and not e.startswith('.') and not e.endswith('.bak')]
        
        for i, entry in enumerate(entries):
            abs_entry = os.path.join(current_path, entry)
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            
            if os.path.isdir(abs_entry):
                tree_lines.append(prefix + connector + entry + os.sep)
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk_dir(abs_entry, new_prefix)
            else:
                tree_lines.append(f"{prefix}{connector}{entry}")
                
    repo_name = os.path.basename(os.path.abspath(dirpath))
    tree_lines.append(repo_name + os.sep)
    walk_dir(os.path.abspath(dirpath))
    return "\n".join(tree_lines)

def parse_roadmap_gaps(repo_path):
    roadmap_path = os.path.join(repo_path, "ROADMAP.md")
    if not os.path.exists(roadmap_path):
        return {}
    try:
        with open(roadmap_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except Exception as e:
        return {"Error": f"Could not read ROADMAP.md: {e}"}
        
    gaps = {}
    current_header = None
    header_content = []
    
    target_headers = [
        "working, not yet validated",
        "silently inert",
        "dormant — working code",
        "documented, not implemented"
    ]
    
    for line in content.splitlines():
        if line.startswith("## "):
            if current_header and header_content:
                gaps[current_header] = "\n".join(header_content).strip()
            
            header_name = line[3:].strip().lower()
            current_header = None
            for th in target_headers:
                if th in header_name:
                    current_header = line[3:].strip()
                    header_content = []
                    break
        elif line.startswith("---") or line.startswith("# "):
            if current_header and header_content:
                gaps[current_header] = "\n".join(header_content).strip()
            current_header = None
        else:
            if current_header is not None:
                header_content.append(line)
                
    if current_header and header_content:
        gaps[current_header] = "\n".join(header_content).strip()
        
    return gaps

def get_attr(obj, attr_name, default=0.0):
    if obj is None or not attr_name:
        return default
    if hasattr(obj, attr_name):
        val = getattr(obj, attr_name)
        return val() if callable(val) else val
    elif isinstance(obj, dict):
        return obj.get(attr_name, default)
    return default

def compile_brief(repo_path):
    if not repo_path:
        raise ValueError("Repository path must not be empty.")
    repo_path = os.path.abspath(repo_path)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # 1. Directory tree
    dir_tree = generate_directory_tree(repo_path)
    
    # 2. Risk scoring for all modules
    codebase = analyzer.analyze_directory(repo_path)
    all_files = list(codebase.keys())
    risks = risk.evaluate_risks(codebase, all_files, repo_path=repo_path)
    
    sorted_risks = sorted(risks, key=lambda r: get_attr(r, 'impact_score', 0.0), reverse=True)
    
    bug_fixes = {}
    try:
        bug_fixes = analyzer.extract_git_history(repo_path)
    except Exception as e:
        _err = e
    feedback = {}
    try:
        feedback = risk.load_human_feedback()
    except Exception as e:
        _err = e
    
    # 3. Hubs and Leaves
    hubs = []
    leaves = []
    for r in sorted_risks:
        coupling = get_attr(r, 'coupling_score', get_attr(r, 'coupling', 0))
        filepath = get_attr(r, 'file_path', get_attr(r, 'file', ''))
        if coupling > 0:
            hubs.append((filepath, int(coupling)))
        else:
            leaves.append(filepath)
            
    hubs.sort(key=lambda x: x[1], reverse=True)
    leaves.sort()
    
    # 4. Roadmap gaps
    roadmap_gaps = parse_roadmap_gaps(repo_path)
    
    # Build Markdown Output
    lines = []
    lines.append(f"# Codebase Context Brief: {os.path.basename(repo_path)}")
    lines.append(f"Generated on: {timestamp}")
    lines.append("")
    
    lines.append("## 1. Directory Structure")
    lines.append("```text")
    lines.append(dir_tree)
    lines.append("```")
    lines.append("")
    
    lines.append("## 2. File Risk Profiles")
    lines.append("| File | Risk Tier | Impact Score | Complexity | Coupling |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in sorted_risks:
        filepath = get_attr(r, 'file_path', get_attr(r, 'file', ''))
        level = get_attr(r, 'level', 'LOW')
        impact = get_attr(r, 'impact_score', 0.0)
        
        # Check if git-history or feedback adjustment changed the outcome
        n_fixes = bug_fixes.get(filepath, 0)
        feedback_accurate = feedback.get(filepath, None)
        
        is_public = filepath.endswith('__init__.py')
        base_high = 10.0
        base_med = 3.0
        base_level = 'HIGH' if impact >= base_high or is_public else ('MEDIUM' if impact >= base_med else 'LOW')
        
        note = ""
        if level != base_level:
            adjust_reasons = []
            if n_fixes > 0:
                adjust_reasons.append(f"{n_fixes} bug-fix commit{'s' if n_fixes > 1 else ''}")
            if feedback_accurate is True:
                adjust_reasons.append("accurate human feedback")
            elif feedback_accurate is False:
                adjust_reasons.append("inaccurate human feedback")
                
            reasons_str = " and ".join(adjust_reasons)
            
            # Re-calculate thresholds
            high_t = 10.0 - 1.5 * n_fixes
            if feedback_accurate is True:
                high_t -= 2.0
            elif feedback_accurate is False:
                high_t += 3.0
            high_t = max(3.0, min(15.0, high_t))
            
            med_t = 3.0 - 0.5 * n_fixes
            if feedback_accurate is True:
                med_t -= 1.0
            elif feedback_accurate is False:
                med_t += 1.5
            med_t = max(1.0, min(8.0, med_t))
            
            target_t = high_t if level == 'HIGH' or base_level == 'HIGH' else med_t
            
            note = f" (adjusted: {reasons_str} lowered {level} threshold to {target_t:.1f})"
            
        complexity = get_attr(r, 'complexity', 1)
        coupling = get_attr(r, 'coupling_score', get_attr(r, 'coupling', 0))
        lines.append(f"| {filepath} | {level}{note} | {impact:.2f} | {complexity} | {coupling} |")
    lines.append("")
    
    lines.append("## 3. High-Level Dependency Graph")
    lines.append("### Central Hubs (highly coupled)")
    if hubs:
        for file_path, coupling_count in hubs:
            lines.append(f"*   **{file_path}** (referenced by {coupling_count} other files)")
    else:
        lines.append("*   None detected")
    lines.append("")
    
    lines.append("### Leaf Modules (safe to change)")
    if leaves:
        for file_path in leaves:
            lines.append(f"*   **{file_path}**")
    else:
        lines.append("*   None detected")
    lines.append("")
    
    lines.append("## 4. Known Open Issues & Gaps (from ROADMAP.md)")
    if roadmap_gaps:
        for section, content in roadmap_gaps.items():
            lines.append(f"### {section}")
            lines.append(content)
            lines.append("")
    else:
        lines.append("*   None documented")
        
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception as e:
            sys.stderr.write(f"Warning: stdout reconfigure failed: {e}\n")
            
    import argparse
    parser = argparse.ArgumentParser(description="Generate a context brief for a repository.")
    parser.add_argument("--repo", default=".", help="Path to repository")
    parser.add_argument("--output", help="Path to output markdown file")
    args = parser.parse_args()
    
    brief = compile_brief(args.repo)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"[+] Context brief written to {args.output}")
    else:
        print(brief)
