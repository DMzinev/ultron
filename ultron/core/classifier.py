MAGIC_VALUE_1 = 2
import ast
import os
import sys

def levenshtein_distance(s1, s2):
    """
    Computes the edit distance between s1 and s2.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def string_similarity(s1, s2):
    """
    Returns normalized string similarity in [0, 1].
    """
    if not s1 and (not s2):
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return 1.0 - dist / max_len

class CallSequenceVisitor(ast.NodeVisitor):

    def __init__(self):
        self.sequences = []
        self.current_sequence = []

    def visit_FunctionDef(self, node):
        old_seq = self.current_sequence
        self.current_sequence = []
        self.generic_visit(node)
        if len(self.current_sequence) > 1:
            self.sequences.append(self.current_sequence)
        self.current_sequence = old_seq

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name:
            self.current_sequence.append((name, node.lineno))
        self.generic_visit(node)

def get_attribute_chain(node):
    """
    Given an ast.Attribute or ast.Name, returns (base_name, [attr1, attr2, ...])
    For example:
    Name(id='os') -> ('os', [])
    Attribute(value=Name(id='os'), attr='path') -> ('os', ['path'])
    Attribute(value=Attribute(value=Name(id='os'), attr='path'), attr='abspath') -> ('os', ['path', 'abspath'])
    """
    attrs = []
    curr = node
    while isinstance(curr, ast.Attribute):
        attrs.append(curr.attr)
        curr = curr.value
    if isinstance(curr, ast.Name):
        return curr.id, list(reversed(attrs))
    return None, []

def build_models(dirpath, exclude_file=None, os=os):
    """
    Scans the repository and trains the models:
    - defined_names: set of all function, class, and variable names.
    - transition_probs: transition probability matrix for call sequences.
    """
    defined_names = set()
    transitions = {}
    exclude_path = os.path.abspath(exclude_file) if exclude_file else None
    for root, _, files in os.walk(dirpath):
        parts = root.split(os.sep)
        if any((part.startswith('.') or part in ('venv', 'env', '__pycache__', 'tests') for part in parts)):
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if exclude_path and os.path.abspath(filepath) == exclude_path:
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    
                    # Top-level names (globals, functions, classes, imports)
                    for node in tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            defined_names.add(node.name)
                            if isinstance(node, ast.ClassDef):
                                # Also collect method names defined inside the class
                                for subnode in node.body:
                                    if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        defined_names.add(subnode.name)
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    defined_names.add(target.id)
                                elif isinstance(target, ast.Tuple):
                                    for elt in target.elts:
                                        if isinstance(elt, ast.Name):
                                            defined_names.add(elt.id)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                defined_names.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.names:
                                for alias in node.names:
                                    defined_names.add(alias.name)
                    
                    seq_visitor = CallSequenceVisitor()
                    seq_visitor.visit(tree)
                    for seq in seq_visitor.sequences:
                        if not seq:
                            continue
                        seq_with_end = seq + [('[END]', seq[-1][1])]
                        for i in range(len(seq_with_end) - 1):
                            prev = seq_with_end[i][0]
                            curr = seq_with_end[i + 1][0]
                            transitions.setdefault(prev, {}).setdefault(curr, 0)
                            transitions[prev][curr] += 1
                        for i in range(len(seq_with_end) - MAGIC_VALUE_1):
                            prev_prev = seq_with_end[i][0]
                            prev = seq_with_end[i + 1][0]
                            curr = seq_with_end[i + 2][0]
                            key = f'{prev_prev},{prev}'
                            transitions.setdefault(key, {}).setdefault(curr, 0)
                            transitions[key][curr] += 1
                except Exception:
                    pass
    transition_probs = {}
    for prev, currs in transitions.items():
        total = sum(currs.values())
        transition_probs[prev] = {curr: count / total for curr, count in currs.items()}
    return (defined_names, transition_probs)

def audit_target_file(filepath, defined_names, transition_probs, typo_threshold=0.75, prob_threshold=0.0, os=os):
    """
    Audits a single python file for spelling typos and sequence anomalies.
    """
    import importlib
    anomalies = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
            
        # Compile a set of built-in type method names dynamically
        builtin_methods = set()
        for t in (list, dict, set, str, tuple, bytes, bytearray, frozenset, range, float, int, complex, bool):
            try:
                for attr in dir(t):
                    if not attr.startswith('_') or attr in ('__init__', '__call__'):
                        builtin_methods.add(attr)
            except Exception:
                pass

        # Parse local imports and top-level definitions in target file
        local_names = set()
        local_imports = {}

        # Safely determine stdlib modules (available in Python 3.10+)
        stdlib_names = getattr(sys, 'stdlib_module_names', frozenset())

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                local_names.add(node.name)
                if isinstance(node, ast.ClassDef):
                    for subnode in node.body:
                        if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            local_names.add(subnode.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        local_names.add(target.id)
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                local_names.add(elt.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    local_names.add(asname.split('.')[0])
                    
                    base_module = name.split('.')[0]
                    if base_module in stdlib_names:
                        try:
                            mod = importlib.import_module(name)
                            local_imports[asname] = mod
                        except Exception:
                            local_imports[asname] = 'PLACEHOLDER'
                    else:
                        local_imports[asname] = 'PLACEHOLDER'
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module
                if node.level > 0 or not module_name:
                    # Relative import or empty module name: do not dynamically import, mark as placeholder
                    for alias in node.names:
                        asname = alias.asname or alias.name
                        local_names.add(asname)
                        local_imports[asname] = 'PLACEHOLDER'
                else:
                    base_module = module_name.split('.')[0]
                    if base_module in stdlib_names:
                        try:
                            mod = importlib.import_module(module_name)
                            for alias in node.names:
                                name = alias.name
                                asname = alias.asname or name
                                local_names.add(asname)
                                
                                if name == '*':
                                    # Handle wildcard import of stdlib module
                                    if hasattr(mod, '__all__'):
                                        for n in mod.__all__:
                                            local_names.add(n)
                                    else:
                                        for n in dir(mod):
                                            if not n.startswith('_'):
                                                local_names.add(n)
                                elif hasattr(mod, name):
                                    local_imports[asname] = getattr(mod, name)
                                else:
                                    try:
                                        sub_mod = importlib.import_module(f"{module_name}.{name}")
                                        local_imports[asname] = sub_mod
                                    except Exception:
                                        local_imports[asname] = 'PLACEHOLDER'
                        except Exception:
                            # Fallback
                            for alias in node.names:
                                asname = alias.asname or alias.name
                                local_names.add(asname)
                                local_imports[asname] = 'PLACEHOLDER'
                    else:
                        for alias in node.names:
                            asname = alias.asname or alias.name
                            local_names.add(asname)
                            local_imports[asname] = 'PLACEHOLDER'

        def is_valid_attribute_chain(base_name, attrs):
            if base_name not in local_imports:
                return False
            obj = local_imports[base_name]
            if obj == 'PLACEHOLDER':
                return True
            try:
                for attr in attrs:
                    if hasattr(obj, attr):
                        obj = getattr(obj, attr)
                    else:
                        return False
                return True
            except Exception:
                return False

        called_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(('Name', node.func.id, (), node.lineno))
                elif isinstance(node.func, ast.Attribute):
                    base, attrs = get_attribute_chain(node.func)
                    if base:
                        called_names.add(('Attribute', base, tuple(attrs), node.lineno))

        for call_type, base_or_id, attrs, lineno in called_names:
            if call_type == 'Name':
                call_name = base_or_id
                if call_name.startswith('_'):
                    continue
                if call_name in (__builtins__ if isinstance(__builtins__, dict) else dir(__builtins__)):
                    continue
                if call_name in local_names or call_name in local_imports:
                    continue
                if call_name in defined_names:
                    continue
                
                best_match = None
                best_sim = 0.0
                search_pool = set(defined_names).union(__builtins__ if isinstance(__builtins__, dict) else dir(__builtins__))
                for def_name in search_pool:
                    if not def_name.startswith('_'):
                        sim = string_similarity(call_name, def_name)
                        if sim > best_sim:
                            best_sim = sim
                            best_match = def_name
                if typo_threshold <= best_sim < 1.0:
                    anomalies.append({
                        'type': 'Spelling Typo / Name Confusion',
                        'file': os.path.basename(filepath),
                        'line': lineno,
                        'details': f"Called identifier '{call_name}' is not defined in codebase. Did you mean '{best_match}'? (spelling similarity: {best_sim:.2%})"
                    })
            elif call_type == 'Attribute':
                base_name = base_or_id
                attr_name = attrs[-1]
                if base_name in local_imports:
                    if is_valid_attribute_chain(base_name, attrs):
                        continue
                if attr_name in builtin_methods:
                    continue
                if attr_name in defined_names:
                    continue
                if attr_name.startswith('_'):
                    continue
                
                best_match = None
                best_sim = 0.0
                search_pool = set(defined_names).union(builtin_methods)
                for def_name in search_pool:
                    if not def_name.startswith('_'):
                        sim = string_similarity(attr_name, def_name)
                        if sim > best_sim:
                            best_sim = sim
                            best_match = def_name
                if typo_threshold <= best_sim < 1.0:
                    anomalies.append({
                        'type': 'Spelling Typo / Name Confusion',
                        'file': os.path.basename(filepath),
                        'line': lineno,
                        'details': f"Called attribute '{attr_name}' is not defined in codebase or standard built-ins. Did you mean '{best_match}'? (spelling similarity: {best_sim:.2%})"
                    })

        seq_visitor = CallSequenceVisitor()
        seq_visitor.visit(tree)
        for seq in seq_visitor.sequences:
            if not seq:
                continue
            seq_with_end = seq + [('[END]', seq[-1][1])]
            if len(seq_with_end) >= 2:
                prev_name, prev_line = seq_with_end[0]
                curr_name, curr_line = seq_with_end[1]
                prob = 0.0
                if prev_name in transition_probs and curr_name in transition_probs[prev_name]:
                    prob = transition_probs[prev_name][curr_name]
                if (prev_name in transition_probs or prev_name in defined_names) and prob <= prob_threshold:
                    anomalies.append({'type': 'Markov Causal Flow Anomaly', 'file': os.path.basename(filepath), 'line': curr_line, 'details': f"Transition '{prev_name} -> {curr_name}' has {prob:.2%} occurrence probability in baseline codebase (at or below threshold {prob_threshold:.2%}). Highly improbable execution path."})
            for i in range(len(seq_with_end) - 2):
                prev_prev_name, prev_prev_line = seq_with_end[i]
                prev_name, prev_line = seq_with_end[i + 1]
                curr_name, curr_line = seq_with_end[i + 2]
                key = f'{prev_prev_name},{prev_name}'
                prob = 0.0
                if key in transition_probs and curr_name in transition_probs[key]:
                    prob = transition_probs[key][curr_name]
                if (key in transition_probs or prev_name in defined_names) and prob <= prob_threshold:
                    anom_line = prev_line if curr_name == '[END]' else curr_line
                    anomalies.append({'type': 'Markov Causal Flow Anomaly', 'file': os.path.basename(filepath), 'line': anom_line, 'details': f"Transition '{prev_prev_name} -> {prev_name} -> {curr_name}' has {prob:.2%} occurrence probability in baseline codebase (at or below threshold {prob_threshold:.2%}). Highly improbable execution path."})
    except Exception as e:
        import traceback
        anomalies.append({'type': 'Parse Error', 'file': os.path.basename(filepath), 'line': 1, 'details': f"{e}\n{traceback.format_exc()}"})
    return anomalies
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python classifier.py <repo_path> <target_file>')
        sys.exit(1)
    repo = sys.argv[1]
    target = sys.argv[2]
    print(f'[+] Classifier: Training models on {repo}...')
    names, probs = build_models(repo)
    print(f'[+] Classifier: Auditing target file {target}...')
    anomalies = audit_target_file(target, names, probs)
    if anomalies:
        print(f'[-] WARNING: Found {len(anomalies)} statistical anomaly(s)!')
        for anom in anomalies:
            print(f"    - [{anom['type']}] Line {anom['line']}: {anom['details']}")
    else:
        print('[+] Success: No statistical or structural sequence anomalies detected.')