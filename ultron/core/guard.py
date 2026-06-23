import ast
import os
import sys

def get_signatures_and_calls(dirpath, os=os):
    """
    Scans the repository and builds maps of:
    - signatures: func_name -> {file, args_count, defaults_count}
    - call_sites: list of {file, func_name, args_count, lineno}
    """
    signatures = {}
    call_sites = []

    class CallSiteVisitor(ast.NodeVisitor):

        def __init__(self, filename):
            self.filename = filename

        def visit_Call(self, node):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name:
                call_sites.append({'file': self.filename, 'name': name, 'args_count': len(node.args), 'lineno': node.lineno})
            self.generic_visit(node)

    class SignatureVisitor(ast.NodeVisitor):

        def __init__(self, rel_path):
            self.rel_path = rel_path
            self.class_context = []
            self.in_function = False

        def visit_ClassDef(self, node):
            self.class_context.append(node.name)
            self.generic_visit(node)
            self.class_context.pop()

        def visit_FunctionDef(self, node):
            is_overload = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == 'overload' or (isinstance(dec, ast.Attribute) and dec.attr == 'overload'):
                    is_overload = True
            if not self.in_function and (not is_overload):
                args = node.args.args
                defaults = node.args.defaults
                min_args = len(args) - len(defaults)
                max_args = len(args)
                is_method = len(self.class_context) > 0 and args and (args[0].arg in ('self', 'cls'))
                sig_name = node.name
                signatures[sig_name] = {'file': self.rel_path, 'min_args': max(0, min_args - 1 if is_method else min_args), 'max_args': max(0, max_args - 1 if is_method else max_args), 'is_method': is_method, 'has_varargs': node.args.vararg is not None or node.args.kwarg is not None}
            old_in = self.in_function
            self.in_function = True
            for child in node.body:
                self.visit(child)
            self.in_function = old_in

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)
    for root, _, files in os.walk(dirpath):
        parts = root.split(os.sep)
        if any((part.startswith('.') or part in ('venv', 'env', '__pycache__', 'tests') for part in parts)):
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, dirpath).replace(os.sep, '/')
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    sig_visitor = SignatureVisitor(rel_path)
                    sig_visitor.visit(tree)
                    call_visitor = CallSiteVisitor(rel_path)
                    call_visitor.visit(tree)
                except Exception:
                    pass
    return (signatures, call_sites)

def verify_contracts(dirpath):
    """
    Checks all call sites against known function signatures.
    Returns a list of contract violations.
    """
    signatures, call_sites = get_signatures_and_calls(dirpath)
    violations = []
    for call in call_sites:
        name = call['name']
        if name in signatures:
            sig = signatures[name]
            if sig['has_varargs']:
                continue
            actual_args = call['args_count']
            min_expected = sig['min_args']
            max_expected = sig['max_args']
            if actual_args < min_expected or actual_args > max_expected:
                violations.append({'file': call['file'], 'line': call['lineno'], 'function': name, 'actual_args': actual_args, 'expected_range': f'{min_expected}-{max_expected}', 'definition_file': sig['file']})
    return violations
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python guard.py <repo_path>')
        sys.exit(1)
    repo = sys.argv[1]
    print(f'[+] Guard: Verifying interface contracts in {repo}...')
    errors = verify_contracts(repo)
    if errors:
        print(f'[-] WARNING: Found {len(errors)} contract violation(s)!')
        for err in errors:
            print(f"    - {err['file']}:{err['line']} -> Call to '{err['function']}' passes {err['actual_args']} args, but definition in {err['definition_file']} expects {err['expected_range']}.")
    else:
        print('[+] Success: All call sites conform to static contract signatures.')