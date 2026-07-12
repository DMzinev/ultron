import ast
import os

class CallVisitor(ast.NodeVisitor):

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)

def analyze_file(filepath):
    """
    Parses a python file and returns:
    - imports: list of imported modules/names
    - definitions: list of defined functions/classes with metadata and calls
    """
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        return {'error': str(e)}
    imports = []
    definitions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            else:
                module = node.module or ''
                for name in node.names:
                    imports.append(f'{module}.{name.name}' if module else name.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = CallVisitor()
            visitor.visit(node)
            args = [arg.arg for arg in node.args.args]
            definitions.append({'type': 'function', 'name': node.name, 'args': args, 'lineno': node.lineno, 'calls': list(set(visitor.calls))})
        elif isinstance(node, ast.ClassDef):
            methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visitor = CallVisitor()
                    visitor.visit(child)
                    methods.append({'name': child.name, 'args': [arg.arg for arg in child.args.args], 'calls': list(set(visitor.calls))})
            definitions.append({'type': 'class', 'name': node.name, 'lineno': node.lineno, 'methods': methods})
    return {'imports': list(set(imports)), 'definitions': definitions}

def analyze_directory(dirpath, os=os):
    """
    Walks a directory and analyzes all python files.
    Returns a unified codebase representation.
    """
    codebase = {}
    for root, dirs, files in os.walk(dirpath):
        # Prune dirs in-place to avoid scanning virtualenvs, builds, test files, and scratch dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'env', 'test_env', '__pycache__', 'tests', 'node_modules', 'scratch', 'dist', 'synapse_project', 'docs', 'ultron_risk_scorer.egg-info')]
        
        for file in files:
            if file.endswith('.py'):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dirpath).replace(os.sep, '/')
                analysis = analyze_file(abs_path)
                if 'error' not in analysis:
                    codebase[rel_path] = analysis
    return codebase

def build_dependency_graph(codebase):
    """
    Constructs a JSON-serializable node-link representation of repository files, functions, and their calls.
    """
    nodes = []
    links = []
    
    # 1. Map definition names to their defining file and metadata
    def_map = {}
    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            def_map[name] = {
                'file': rel_path,
                'type': defn.get('type'),
                'complexity': defn.get('complexity', 1) if defn.get('type') == 'function' else 1
            }
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    # Class methods map as ClassName.method_name or just method_name
                    # To keep it simple, we record them under their class-context name
                    full_m_name = f"{name}.{m_name}"
                    def_map[full_m_name] = {
                        'file': rel_path,
                        'type': 'method',
                        'complexity': 1
                    }
                    def_map[m_name] = {
                        'file': rel_path,
                        'type': 'method',
                        'complexity': 1
                    }

    # 2. Add nodes and links
    for rel_path, analysis in codebase.items():
        # Add file node
        nodes.append({
            'id': rel_path,
            'type': 'file',
            'label': rel_path
        })
        
        # File imports -> File links
        for imp in analysis.get('imports', []):
            # Check if imported name maps to a file in the repository
            # e.g. "ultron.classifier" matches "ultron/classifier.py"
            imp_parts = imp.split('.')
            for potential_path in codebase:
                potential_base = potential_path.replace('.py', '').replace('/', '.')
                if potential_base == imp or potential_base.endswith('.' + imp) or imp.replace('.', '/') in potential_path:
                    links.append({
                        'source': rel_path,
                        'target': potential_path,
                        'type': 'import'
                    })
                    break

        # Process function and class definitions
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            node_id = f"{rel_path}:{name}"
            
            # Add function/class node
            nodes.append({
                'id': node_id,
                'type': defn.get('type'),
                'label': name,
                'file': rel_path
            })
            
            # Link file to its definitions
            links.append({
                'source': rel_path,
                'target': node_id,
                'type': 'contains'
            })
            
            # Process calls inside definitions
            for call in defn.get('calls', []):
                if call in def_map:
                    target_file = def_map[call]['file']
                    target_id = f"{target_file}:{call}"
                    links.append({
                        'source': node_id,
                        'target': target_id,
                        'type': 'call'
                    })
                    
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    m_node_id = f"{rel_path}:{name}.{m_name}"
                    
                    # Add method node
                    nodes.append({
                        'id': m_node_id,
                        'type': 'method',
                        'label': f"{name}.{m_node_id}",
                        'file': rel_path
                    })
                    
                    # Link class to method
                    links.append({
                        'source': node_id,
                        'target': m_node_id,
                        'type': 'contains'
                    })
                    
                    # Link method calls
                    for call in method.get('calls', []):
                        if call in def_map:
                            target_file = def_map[call]['file']
                            target_id = f"{target_file}:{call}"
                            links.append({
                                'source': m_node_id,
                                'target': target_id,
                                'type': 'call'
                            })
                            
    return {'nodes': nodes, 'links': links}

def extract_git_history(repo_path):
    """
    Runs git log in the target repository to find the frequency of bug fixes per file.
    Returns a dictionary mapping relative file paths to their bug fix counts.
    """
    import subprocess
    bug_fix_counts = {}
    
    try:
        chk = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=repo_path
        )
        is_git = (chk.returncode == 0 and chk.stdout.strip() == "true")
    except Exception:
        is_git = False

    if not is_git:
        print("[Ultron] No git history found — bug-prone-file scaling is inactive.")
        return bug_fix_counts
    
    try:
        # Check if keyword search matches any commits
        cmd_commits = [
            "git", "log",
            "--pretty=format:%h",
            "-i",
            "--grep=fix",
            "--grep=bug",
            "--grep=issue",
            "--grep=hotfix",
            "--grep=patch"
        ]
        chk_commits = subprocess.run(
            cmd_commits, 
            capture_output=True, 
            text=True, 
            cwd=repo_path
        )
        matched_commits = [c for c in chk_commits.stdout.splitlines() if c.strip()]
        
        if not matched_commits:
            print("[Ultron] Git history found but no fix/bug/patch-tagged commits matched — scaling has no effect.")
            return bug_fix_counts

        # Run git log with list of modified files in each commit
        cmd = [
            "git", "log", 
            "--name-only", 
            "--pretty=format:", 
            "-i", 
            "--grep=fix", 
            "--grep=bug", 
            "--grep=issue", 
            "--grep=hotfix", 
            "--grep=patch"
        ]
        res = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=repo_path, 
            timeout=5.0
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            for line in lines:
                file_rel = line.strip().replace("\\", "/")
                if file_rel and file_rel.endswith(".py"):
                    bug_fix_counts[file_rel] = bug_fix_counts.get(file_rel, 0) + 1
    except Exception:
        pass
    return bug_fix_counts