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
        return f"{filename} — High risk to change. {N} other files depend on it directly, so changes here can break things elsewhere without warning."
    elif level == 'MEDIUM':
        return f"{filename} — Moderate risk. A few other parts of the project rely on this; double check anything that calls it after editing."
    else:
        return f"{filename} — Low risk. Nothing else in the project depends on this directly — safe to experiment with."

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
