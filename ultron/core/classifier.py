import ast
import os
import sys
import difflib

def string_similarity(s1, s2):
    """
    Returns normalized string similarity in [0, 1] using difflib.SequenceMatcher.
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()

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
    Scans the repository and returns the set of all defined names
    (function, class, variable, method, and import names).
    """
    defined_names = set()
    exclude_path = os.path.abspath(exclude_file) if exclude_file else None
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'env', 'test_env', '__pycache__', 'tests', 'node_modules', 'scratch', 'dist', 'synapse_project', 'docs', 'ultron_risk_scorer.egg-info')]
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if exclude_path and os.path.abspath(filepath) == exclude_path:
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            defined_names.add(node.name)
                        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
                            defined_names.add(node.id)
                        elif isinstance(node, ast.arg):
                            defined_names.add(node.arg)
                        elif isinstance(node, (ast.Import, ast.ImportFrom)):
                            for alias in node.names:
                                defined_names.add((alias.asname or alias.name).split('.')[0])
                except Exception:
                    pass
    return defined_names

def audit_target_file(filepath, defined_names, transition_probs=None, typo_threshold=0.75, prob_threshold=0.0, os=os):
    """
    Audits a single python file for spelling typos / name confusion anomalies.
    """
    import importlib
    anomalies = []
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
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

        # Introspect common standard library classes to include their public methods
        import io
        import argparse
        import ast as pyast
        import re
        import unittest
        import logging
        import threading
        import datetime

        common_stdlib_types = [
            io.StringIO, io.BytesIO, io.TextIOWrapper, io.BufferedReader, io.BufferedWriter,
            argparse.ArgumentParser, pyast.NodeVisitor, pyast.NodeTransformer,
            unittest.TestCase, logging.Logger, threading.Thread, threading.Lock,
            datetime.datetime, datetime.date, datetime.time, datetime.timedelta
        ]
        
        try:
            compiled_re = re.compile("")
            common_stdlib_types.append(type(compiled_re))
            match_obj = compiled_re.match("")
            if match_obj:
                common_stdlib_types.append(type(match_obj))
        except Exception:
            pass

        for t in common_stdlib_types:
            try:
                for attr in dir(t):
                    if not attr.startswith('_'):
                        builtin_methods.add(attr)
            except Exception:
                pass

        # Parse local imports, local variables, and parameters inside target file using AST walk
        local_names = set()
        local_imports = {}

        # Collect function-local variable names, parameters, loop variables, etc.
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                local_names.add(node.name)
            elif isinstance(node, ast.arg):
                local_names.add(node.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
                local_names.add(node.id)

        # Walk nested blocks for imports
        stdlib_names = getattr(sys, 'stdlib_module_names', frozenset())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
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
                            for alias in node.names:
                                asname = alias.asname or alias.name
                                local_names.add(asname)
                                local_imports[asname] = 'PLACEHOLDER'
                    else:
                        for alias in node.names:
                            asname = alias.asname or alias.name
                            local_names.add(asname)
                            local_imports[asname] = 'PLACEHOLDER'

        # Collect class ranges and their base classes for self-reference validation
        class_ranges = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start_line = node.lineno
                end_line = start_line
                for child in ast.walk(node):
                    if hasattr(child, 'lineno'):
                        end_line = max(end_line, child.lineno)
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)
                class_ranges.append({
                    'start': start_line,
                    'end': end_line,
                    'bases': bases
                })

        # Load standard methods for standard library HTTP/SocketServer handler classes
        stdlib_handler_methods = set()
        try:
            import http.server
            for attr in dir(http.server.SimpleHTTPRequestHandler):
                if not attr.startswith('_'):
                    stdlib_handler_methods.add(attr)
            for attr in dir(http.server.BaseHTTPRequestHandler):
                if not attr.startswith('_'):
                    stdlib_handler_methods.add(attr)
        except Exception:
            pass

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
                
                # Check for inherited self methods in standard library handlers
                if base_name == 'self':
                    class_bases = []
                    for r in class_ranges:
                        if r['start'] <= lineno <= r['end']:
                            class_bases = r['bases']
                            break
                    if class_bases and any(b in ('SimpleHTTPRequestHandler', 'BaseHTTPRequestHandler', 'HTTPRequestHandler') or 'Handler' in b or 'HTTP' in b for b in class_bases):
                        if attr_name in stdlib_handler_methods:
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
    names = build_models(repo)
    print(f'[+] Classifier: Auditing target file {target}...')
    anomalies = audit_target_file(target, names)
    if anomalies:
        print(f'[-] WARNING: Found {len(anomalies)} statistical anomaly(s)!')
        for anom in anomalies:
            print(f"    - [{anom['type']}] Line {anom['line']}: {anom['details']}")
    else:
        print('[+] Success: No statistical or structural sequence anomalies detected.')