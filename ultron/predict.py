import ast
import os

def predict_test_impact(codebase, changed_files, changed_functions, test_file_path):
    """
    Statically predicts which unit tests are at risk of failing when files/functions change.
    - codebase: Repository analysis output from analyzer.analyze_directory.
    - changed_files: List of modified file paths relative to repository root.
    - changed_functions: List of modified function names.
    - test_file_path: Absolute path to the test file (e.g., run_tests.py).
    """
    # 1. Build reverse call graph: callee_name -> set of caller_node_ids
    reverse_graph = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            node_id = f"{rel_path}:{name}"
            for call in defn.get('calls', []):
                reverse_graph.setdefault(call, set()).add(node_id)
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    m_node_id = f"{rel_path}:{name}.{m_name}"
                    for call in method.get('calls', []):
                        reverse_graph.setdefault(call, set()).add(m_node_id)
                        
    # 2. Establish initial affected functions set
    affected_names = set(changed_functions)
    for filepath in changed_files:
        if filepath in codebase:
            for defn in codebase[filepath].get('definitions', []):
                affected_names.add(defn.get('name'))
                if defn.get('type') == 'class':
                    for method in defn.get('methods', []):
                        affected_names.add(method.get('name'))
                        
    # 3. Transitive dependency propagation via BFS
    visited = set(affected_names)
    queue = list(affected_names)
    
    while queue:
        curr = queue.pop(0)
        callers = reverse_graph.get(curr, set())
        for caller in callers:
            caller_name = caller.split(':')[-1]
            # Strip method dot prefixes if ClassName.method format
            if '.' in caller_name:
                caller_name = caller_name.split('.')[-1]
            if caller_name not in visited:
                visited.add(caller_name)
                queue.append(caller_name)
                
    # 4. Map affected functions to test methods in test_file_path
    predicted_failures = []
    if not os.path.exists(test_file_path):
        return predicted_failures
        
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith('test_'):
                        # Find all calls inside this test method
                        class CallFinder(ast.NodeVisitor):
                            def __init__(self):
                                self.calls = set()
                            def visit_Call(self, node):
                                name = None
                                if isinstance(node.func, ast.Name):
                                    name = node.func.id
                                elif isinstance(node.func, ast.Attribute):
                                    name = node.func.attr
                                if name:
                                    self.calls.add(name)
                                self.generic_visit(node)
                                
                        cf = CallFinder()
                        cf.visit(child)
                        
                        intersection = cf.calls.intersection(visited)
                        if intersection:
                            predicted_failures.append({
                                'test_name': child.name,
                                'reason': f"Calls affected functions: {', '.join(intersection)}"
                            })
    except Exception:
        pass
        
    return predicted_failures
