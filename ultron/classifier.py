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
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            defined_names.add(node.name)
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    defined_names.add(target.id)
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
    anomalies = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        called_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name:
                    called_names.add((name, node.lineno))
        for call_name, lineno in called_names:
            if call_name not in defined_names and (not call_name.startswith('_')):
                if call_name in (__builtins__ if isinstance(__builtins__, dict) else dir(__builtins__)):
                    continue
                best_match = None
                best_sim = 0.0
                for def_name in defined_names:
                    sim = string_similarity(call_name, def_name)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = def_name
                if typo_threshold <= best_sim < 1.0:
                    anomalies.append({'type': 'Spelling Typo / Name Confusion', 'file': os.path.basename(filepath), 'line': lineno, 'details': f"Called identifier '{call_name}' is not defined in codebase. Did you mean '{best_match}'? (spelling similarity: {best_sim:.2%})"})
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
        anomalies.append({'type': 'Parse Error', 'file': os.path.basename(filepath), 'line': 1, 'details': str(e)})
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