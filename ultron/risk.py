import os
import math
import ast
import json
from radon.visitors import ComplexityVisitor
from models import AnalysisPacket
import logistic

_MKR_CACHE = {}
_LAST_CACHE_TIME = 0

def load_mkr_stats(ledger_path=None):
    global _MKR_CACHE, _LAST_CACHE_TIME
    if not ledger_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ledger_path = os.path.abspath(os.path.join(script_dir, "..", "synapse_project", "synapse_mutator", "ledger.jsonl"))
    
    if os.path.exists(ledger_path):
        try:
            mtime = os.path.getmtime(ledger_path)
            if mtime <= _LAST_CACHE_TIME and _MKR_CACHE:
                return _MKR_CACHE
            _LAST_CACHE_TIME = mtime
        except Exception:
            pass
    else:
        return {}
    
    stats = {}
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                filename = record.get("file")
                if filename and record.get("was_mutated"):
                    if record.get("equivalent"):
                        continue
                    norm_file = filename.replace("\\", "/").replace("src/", "")
                    stats.setdefault(norm_file, {"killed": 0, "total": 0})
                    stats[norm_file]["total"] += 1
                    if not record.get("accepted"):
                        stats[norm_file]["killed"] += 1
    except Exception:
        pass
        
    mkr_map = {}
    for k, v in stats.items():
        mkr_map[k] = v["killed"] / v["total"] if v["total"] > 0 else 1.0
        
    _MKR_CACHE = mkr_map
    return mkr_map

def get_file_complexity(filepath):
    """
    Parses a python file and returns the maximum McCabe complexity
    of any block inside it. Defaults to 1 if no blocks exist.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        visitor = ComplexityVisitor.from_code(code)
        if visitor.blocks:
            return max((block.complexity for block in visitor.blocks))
    except Exception:
        pass
    return 1

def load_human_feedback():
    feedback_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta", "human_feedback.jsonl")
    feedback = {}
    if not os.path.exists(feedback_path):
        return feedback
    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                filename = rec.get("file")
                if filename:
                    feedback[filename] = rec.get("accurate", True)
    except Exception:
        pass
    return feedback

def evaluate_risks(codebase, target_files, intent='', repo_path='', os=os):
    """
    Evaluates integration risks for targeted files based on global coupling and complexity.
    - codebase: output of analyzer.analyze_directory
    - target_files: list of relative file paths
    - intent: natural language user request description
    - repo_path: absolute path of the repository to resolve files for complexity analysis
    """
    target_files = list(target_files)
    if not target_files and intent:
        keywords = [w.lower() for w in intent.split() if len(w) > 3]
        for rel_path, analysis in codebase.items():
            match = False
            for kw in keywords:
                if kw in rel_path.lower():
                    match = True
                    break
                for defn in analysis.get('definitions', []):
                    if kw in defn.get('name', '').lower():
                        match = True
                        break
                    if defn.get('type') == 'class':
                        for m in defn.get('methods', []):
                            if kw in m.get('name', '').lower():
                                match = True
                                break
            if match:
                target_files.append(rel_path)
        target_files = list(set(target_files))
    risks = []
    import analyzer
    bug_fixes = {}
    if repo_path:
        try:
            bug_fixes = analyzer.extract_git_history(repo_path)
        except Exception:
            pass
    feedback = load_human_feedback()
    
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            for call in defn.get('calls', []):
                global_callers.setdefault(call, []).append(rel_path)
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    for call in method.get('calls', []):
                        global_callers.setdefault(call, []).append(rel_path)
    for target in target_files:
        if target not in codebase:
            continue
        analysis = codebase[target]
        target_defs = analysis.get('definitions', [])
        downstream_files = []
        for defn in target_defs:
            name = defn.get('name')
            if name in global_callers:
                downstream_files.extend(global_callers[name])
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    if m_name in global_callers:
                        downstream_files.extend(global_callers[m_name])
        downstream_files = list(set(downstream_files))
        if target in downstream_files:
            downstream_files.remove(target)
        coupling_count = len(downstream_files)
        abs_target = os.path.join(repo_path, target) if repo_path else target
        complexity = get_file_complexity(abs_target)
        impact_score = complexity * math.log(math.e + coupling_count)
        is_public = target.endswith('__init__.py') or any((defn.get('name') == '__init__' for defn in target_defs))
        
        # Get fixes count and human feedback
        n_fixes = bug_fixes.get(target, 0)
        feedback_accurate = feedback.get(target, None)
        
        # Base thresholds
        high_t = 10.0
        med_t = 3.0
        
        # Adjust based on bug fix frequency
        high_t -= 1.5 * n_fixes
        med_t -= 0.5 * n_fixes
        
        # Adjust based on human feedback
        if feedback_accurate is True:
            high_t -= 2.0
            med_t -= 1.0
        elif feedback_accurate is False:
            high_t += 3.0
            med_t += 1.5
            
        # Bound thresholds
        high_t = max(3.0, min(15.0, high_t))
        med_t = max(1.0, min(8.0, med_t))
        
        if impact_score >= high_t or is_public:
            level = 'HIGH'
            mitigation = f'Critical boundary. Impact Score: {impact_score:.2f} (Threshold: {high_t:.2f}, Complexity: {complexity}, Coupling: {coupling_count}). Do NOT modify signatures without simultaneously refactoring callers.'
        elif impact_score >= med_t:
            level = 'MEDIUM'
            mitigation = f"Moderate coupling. Impact Score: {impact_score:.2f} (Threshold: {med_t:.2f}, Complexity: {complexity}, Coupling: {coupling_count}). Review callers: {', '.join(downstream_files)}."
        else:
            level = 'LOW'
            mitigation = f'Low risk leaf module. Impact Score: {impact_score:.2f} (Complexity: {complexity}, Coupling: {coupling_count}). Safe to modify.'
            
        # Look up Mutation Kill Rate (MKR)
        mkr_map = load_mkr_stats()
        mkr = 1.0
        target_base = os.path.basename(target)
        for k, v in mkr_map.items():
            if os.path.basename(k) == target_base:
                mkr = v
                break
        
        # Calculate combined confidence Uc
        try:
            defect_prob = logistic.predict_defect_probability(impact_score, mkr)
            confidence = 1.0 - defect_prob
        except Exception:
            confidence = mkr / (1.0 + 0.1 * impact_score)
        
        risks.append(AnalysisPacket(
            file_path=target,
            impact_score=impact_score,
            coupling_score=float(coupling_count),
            mk_r=mkr,
            delta_cest=0.0,
            confidence=confidence,
            level=level,
            complexity=complexity,
            mitigation=mitigation,
            callers=downstream_files
        ))
    return risks

def get_code_complexity(code):
    """
    Computes maximum cyclomatic complexity for a given code segment.
    """
    try:
        visitor = ComplexityVisitor.from_code(code)
        if visitor.blocks:
            return max((block.complexity for block in visitor.blocks))
    except Exception:
        pass
    return 1

def extract_ast_blocks(code):
    """
    Parses code to AST and extracts class/function blocks with source segments and complexity.
    """
    blocks = {}
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                try:
                    segment = ast.get_source_segment(code, node)
                except Exception:
                    segment = ""
                blocks[name] = {
                    'type': 'function',
                    'code': segment,
                    'complexity': get_code_complexity(segment) if segment else 1
                }
            elif isinstance(node, ast.ClassDef):
                name = node.name
                try:
                    segment = ast.get_source_segment(code, node)
                except Exception:
                    segment = ""
                blocks[name] = {
                    'type': 'class',
                    'code': segment,
                    'complexity': get_code_complexity(segment) if segment else 1
                }
    except Exception:
        pass
    return blocks

def evaluate_diff_risk(codebase, filepath, old_code, new_code):
    """
    Compares old vs new AST structures to compute function-level delta impact scores (Delta I).
    """
    old_blocks = extract_ast_blocks(old_code)
    new_blocks = extract_ast_blocks(new_code)
    
    # Build global callers map for coupling calculation
    global_callers = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            for call in defn.get('calls', []):
                global_callers.setdefault(call, []).append(rel_path)
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    for call in method.get('calls', []):
                        global_callers.setdefault(call, []).append(rel_path)
                        
    changes = []
    total_delta = 0.0
    
    all_names = set(old_blocks.keys()).union(new_blocks.keys())
    
    for name in all_names:
        action = None
        block_type = None
        comp_before = 0
        comp_after = 0
        
        if name in new_blocks and name not in old_blocks:
            action = 'added'
            block_type = new_blocks[name]['type']
            comp_after = new_blocks[name]['complexity']
        elif name in old_blocks and name not in new_blocks:
            action = 'deleted'
            block_type = old_blocks[name]['type']
            comp_before = old_blocks[name]['complexity']
        else:
            block_type = new_blocks[name]['type']
            comp_before = old_blocks[name]['complexity']
            comp_after = new_blocks[name]['complexity']
            if old_blocks[name]['code'] != new_blocks[name]['code']:
                action = 'modified'
                
        if action:
            coupling = len(set(global_callers.get(name, [])))
            # I = Complexity * ln(e + Coupling)
            impact_before = comp_before * math.log(math.e + coupling) if comp_before > 0 else 0.0
            impact_after = comp_after * math.log(math.e + coupling) if comp_after > 0 else 0.0
            delta = impact_after - impact_before
            total_delta += delta
            
            changes.append({
                'name': name,
                'type': block_type,
                'action': action,
                'complexity_before': comp_before,
                'complexity_after': comp_after,
                'coupling': coupling,
                'impact_before': impact_before,
                'impact_after': impact_after,
                'delta': delta
            })
            
    # Look up Mutation Kill Rate (MKR)
    mkr_map = load_mkr_stats()
    mkr = 1.0
    target_base = os.path.basename(filepath)
    for k, v in mkr_map.items():
        if os.path.basename(k) == target_base:
            mkr = v
            break
            
    # Calculate confidence based on diff-risk delta
    confidence = mkr / (1.0 + 0.1 * abs(total_delta))

    return AnalysisPacket(
        file_path=filepath,
        impact_score=total_delta,
        coupling_score=0.0,
        mk_r=mkr,
        delta_cest=0.0,
        confidence=confidence,
        changes=changes,
        delta_score=total_delta
    )