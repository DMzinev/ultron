import ast
import os
import sys

def get_import_mappings(codebase):
    """
    Builds a directed dependency graph of file paths mapping to list of imported file paths.
    """
    graph = {rel_path: set() for rel_path in codebase}
    
    for rel_path, analysis in codebase.items():
        for imp in analysis.get("imports", []):
            imp_parts = imp.split(".")
            for potential_path in codebase:
                potential_base = potential_path.replace(".py", "").replace("/", ".")
                # Match module imports like 'ultron.delta' or relative imports
                if potential_base == imp or potential_base.endswith("." + imp) or imp.replace(".", "/") in potential_path:
                    if potential_path != rel_path:
                        graph[rel_path].add(potential_path)
                    break
    return graph

def detect_circular_dependencies(codebase):
    """
    Finds all circular dependency loops in the codebase imports graph.
    Returns a list of list of file paths forming dependency cycles.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")

    graph = get_import_mappings(codebase)
    cycles = []
    
    # DFS cycle detection
    visited = {}
    path = []

    def dfs(node):
        visited[node] = 1  # visiting
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if visited.get(neighbor, 0) == 1:
                # Cycle detected
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                # Normalize cycle representation for deduplication
                min_idx = cycle.index(min(cycle[:-1]))
                normalized_cycle = cycle[min_idx:-1] + cycle[:min_idx] + [min(cycle[:-1])]
                if normalized_cycle not in cycles:
                    cycles.append(normalized_cycle)
            elif visited.get(neighbor, 0) == 0:
                dfs(neighbor)
                
        path.pop()
        visited[node] = 2  # visited

    for node in codebase:
        if visited.get(node, 0) == 0:
            dfs(node)
            
    return cycles

def scan_file_for_globals(filepath):
    """
    Parses file AST to locate declarations of global mutations.
    """
    if filepath is None:
        raise ValueError("filepath cannot be None")
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        globals_declared = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    globals_declared.append({
                        "name": name,
                        "lineno": node.lineno
                    })
        return globals_declared
    except Exception:
        return []

def detect_global_mutations(codebase, repo_path):
    """
    Scans all source files in codebase for occurrences of 'global' mutations.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if repo_path is None:
        raise ValueError("repo_path cannot be None")

    global_mutations = {}
    for rel_path in codebase:
        abs_path = os.path.join(repo_path, rel_path)
        violations = scan_file_for_globals(abs_path)
        if violations:
            global_mutations[rel_path] = violations
    return global_mutations

def recommend_patterns(codebase, intent):
    """
    Recommends design patterns to decouple architectures based on user intent keywords.
    """
    if not isinstance(intent, str):
        raise TypeError("intent must be a string")

    recommendations = []
    intent_lower = intent.lower()
    
    if "theme" in intent_lower or "color" in intent_lower or "skin" in intent_lower:
        recommendations.append({
            "pattern": "ThemeProvider / CSS Variable Isolation",
            "reason": "Direct styling injection couples UI components to concrete design configurations.",
            "suggestion": "Introduce a ThemeProvider context mapping design tokens to CSS variables, isolating component layouts."
        })
        
    if "state" in intent_lower or "store" in intent_lower or "global" in intent_lower:
        recommendations.append({
            "pattern": "Observer Pattern / Central State Container",
            "reason": "Direct component-to-component state mutation leads to untraceable execution drift.",
            "suggestion": "Utilize a unidirectional data flow state container (or Context/Store) and subscribe components to state changes."
        })
        
    if "database" in intent_lower or "db" in intent_lower or "sql" in intent_lower or "save" in intent_lower:
        recommendations.append({
            "pattern": "Repository / Data Access Object (DAO)",
            "reason": "Mixing persistence logic inside business models prevents unit testing database actions in isolation.",
            "suggestion": "Implement a Repository class to abstract database CRUD operations behind a clean, interface-driven api."
        })
        
    if "api" in intent_lower or "service" in intent_lower or "http" in intent_lower:
        recommendations.append({
            "pattern": "Facade / Service Layer Abstraction",
            "reason": "Spreading HTTP request configurations across UI elements tightly couples networking details.",
            "suggestion": "Wrap network request actions inside dedicated client services, exposing only clean asynchronous methods."
        })
        
    return recommendations

def simulate_future_coupling(codebase, src_file, dest_file):
    """
    Simulates the topological effect of introducing a dependency link from src_file to dest_file.
    Returns safe status and cycle warnings.
    """
    if not isinstance(codebase, dict):
        raise TypeError("codebase must be a dictionary")
    if src_file is None or dest_file is None:
        raise ValueError("src_file and dest_file cannot be None")
    if src_file not in codebase or dest_file not in codebase:
        raise ValueError("src_file and dest_file must exist in codebase")

    # Simulate link addition
    sim_codebase = {}
    for k, v in codebase.items():
        sim_codebase[k] = {
            "imports": list(v.get("imports", [])),
            "definitions": list(v.get("definitions", []))
        }
        
    # Translate dest_file path to mock dot import representation
    dest_module = dest_file.replace(".py", "").replace("/", ".")
    if dest_module not in sim_codebase[src_file]["imports"]:
        sim_codebase[src_file]["imports"].append(dest_module)
        
    # Re-run cycle detection on simulated codebase
    sim_cycles = detect_circular_dependencies(sim_codebase)
    original_cycles = detect_circular_dependencies(codebase)
    
    new_cycles = [c for c in sim_cycles if c not in original_cycles]
    
    # Calculate degree impact
    # In-degree of dest_file: how many files import it
    orig_in_degree = sum(1 for src, targets in get_import_mappings(codebase).items() if dest_file in targets)
    sim_in_degree = sum(1 for src, targets in get_import_mappings(sim_codebase).items() if dest_file in targets)
    
    is_safe = len(new_cycles) == 0
    
    return {
        "success": True,
        "is_safe": is_safe,
        "new_cycles_detected": new_cycles,
        "dest_in_degree_change": {
            "before": orig_in_degree,
            "after": sim_in_degree
        },
        "description": "Simulation completed safely." if is_safe else f"Simulation detected {len(new_cycles)} new circular dependency loop(s)!"
    }
