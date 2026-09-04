import ast
import os
import logging

logger = logging.getLogger(__name__)
_EMITTED_NO_GIT_HISTORY = False
_EMITTED_NO_TAGGED_COMMITS = False

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

def build_dependency_graph(codebase, granularity="all"):
    """
    Constructs a JSON-serializable node-link representation of repository files, functions, and their calls.
    Supports granularity filtering:
    - 'file': Returns only file nodes and inter-file import links.
    - 'symbol': Returns only function/class/method symbol nodes and call/contains links between symbols.
    - 'all': Returns both file and symbol nodes with all links (default for backward compatibility).
    """
    file_nodes = []
    symbol_nodes = []
    file_links = []
    symbol_links = []
    all_links = []
    
    # 1. Build module map for robust prefix-based import resolution
    mod_map = {}
    for f in codebase:
        norm_f = f.replace("\\", "/")
        base = os.path.splitext(os.path.basename(norm_f))[0]
        if base != "__init__":
            mod_map[base] = norm_f
        mod_path = norm_f[:-3].replace("/", ".") if norm_f.endswith(".py") else norm_f.replace("/", ".")
        mod_map[mod_path] = norm_f

    # 2. Map definition names to their defining file and metadata
    def_map = {}
    for rel_path, analysis in codebase.items():
        norm_rel = rel_path.replace("\\", "/")
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            def_map[name] = {
                'file': norm_rel,
                'type': defn.get('type'),
                'complexity': defn.get('complexity', 1) if defn.get('type') == 'function' else 1
            }
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    full_m_name = f"{name}.{m_name}"
                    def_map[full_m_name] = {
                        'file': norm_rel,
                        'type': 'method',
                        'complexity': 1
                    }
                    def_map[m_name] = {
                        'file': norm_rel,
                        'type': 'method',
                        'complexity': 1
                    }

    symbol_ids = set()

    # 3. Add nodes and links
    for rel_path, analysis in codebase.items():
        norm_rel = rel_path.replace("\\", "/")
        
        # Add file node
        file_node = {
            'id': norm_rel,
            'type': 'file',
            'label': norm_rel
        }
        file_nodes.append(file_node)
        
        # File imports -> File links
        for imp in analysis.get('imports', []):
            parts = imp.split('.')
            matched_target = None
            for i in range(len(parts), 0, -1):
                prefix = ".".join(parts[:i])
                if prefix in mod_map:
                    tgt = mod_map[prefix]
                    if tgt != norm_rel:
                        matched_target = tgt
                    break
            if not matched_target:
                for potential_path in codebase:
                    pot_norm = potential_path.replace("\\", "/")
                    pot_base = pot_norm.replace('.py', '').replace('/', '.')
                    if pot_base == imp or pot_base.endswith('.' + imp) or imp.replace('.', '/') in pot_norm:
                        if pot_norm != norm_rel:
                            matched_target = pot_norm
                        break
            if matched_target:
                link = {
                    'source': norm_rel,
                    'target': matched_target,
                    'type': 'import'
                }
                file_links.append(link)
                all_links.append(link)

        # Process function and class definitions
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            node_id = f"{norm_rel}:{name}"
            symbol_ids.add(node_id)
            
            # Add function/class node
            sym_node = {
                'id': node_id,
                'type': defn.get('type'),
                'label': name,
                'file': norm_rel
            }
            symbol_nodes.append(sym_node)
            
            # Link file to its definitions (only in 'all' mode, not in 'symbol' to preserve closure)
            all_links.append({
                'source': norm_rel,
                'target': node_id,
                'type': 'contains'
            })
            
            # Process calls inside definitions
            for call in defn.get('calls', []):
                if call in def_map:
                    target_file = def_map[call]['file']
                    target_id = f"{target_file}:{call}"
                    call_link = {
                        'source': node_id,
                        'target': target_id,
                        'type': 'call'
                    }
                    symbol_links.append(call_link)
                    all_links.append(call_link)
                    
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    m_node_id = f"{norm_rel}:{name}.{m_name}"
                    symbol_ids.add(m_node_id)
                    
                    # Add method node
                    m_sym_node = {
                        'id': m_node_id,
                        'type': 'method',
                        'label': f"{name}.{m_name}",
                        'file': norm_rel
                    }
                    symbol_nodes.append(m_sym_node)
                    
                    # Link class to method (symbol-to-symbol contains)
                    class_m_link = {
                        'source': node_id,
                        'target': m_node_id,
                        'type': 'contains'
                    }
                    symbol_links.append(class_m_link)
                    all_links.append(class_m_link)
                    
                    # Link method calls
                    for call in method.get('calls', []):
                        if call in def_map:
                            target_file = def_map[call]['file']
                            target_id = f"{target_file}:{call}"
                            m_call_link = {
                                'source': m_node_id,
                                'target': target_id,
                                'type': 'call'
                            }
                            symbol_links.append(m_call_link)
                            all_links.append(m_call_link)

    # Filter by granularity
    if granularity == "file":
        return {'nodes': file_nodes, 'links': file_links}
    elif granularity == "symbol":
        # Retain only links where both source and target exist in symbol_nodes
        valid_symbol_links = [
            l for l in symbol_links
            if l['source'] in symbol_ids and l['target'] in symbol_ids
        ]
        return {'nodes': symbol_nodes, 'links': valid_symbol_links}
    else:
        return {'nodes': file_nodes + symbol_nodes, 'links': all_links}

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
        global _EMITTED_NO_GIT_HISTORY
        if not _EMITTED_NO_GIT_HISTORY:
            logger.info("[Ultron] No git history found — bug-prone-file scaling is inactive.")
            _EMITTED_NO_GIT_HISTORY = True
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
            global _EMITTED_NO_TAGGED_COMMITS
            if not _EMITTED_NO_TAGGED_COMMITS:
                logger.info("[Ultron] Git history found but no fix/bug/patch-tagged commits matched — scaling has no effect.")
                _EMITTED_NO_TAGGED_COMMITS = True
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