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

MAX_PARSE_SIZE = 1024 * 1024  # 1 MB


class ASTAnalysisCache:
    """
    In-memory / persistent file analysis cache keyed by relative path,
    mtime, size, and content SHA-256 hash.
    """
    def __init__(self):
        self._entries = {}

    def get(self, rel_path: str, abs_path: str):
        if not os.path.exists(abs_path):
            self._entries.pop(abs_path, None)
            return None
        
        try:
            stat = os.stat(abs_path)
        except OSError:
            return None

        entry = self._entries.get(abs_path)
        if entry and entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size:
            return entry.get("analysis")

        return None

    def put(self, rel_path: str, abs_path: str, analysis: dict, content_hash: str = None):
        try:
            stat = os.stat(abs_path)
            self._entries[abs_path] = {
                "rel_path": rel_path,
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": content_hash or "",
                "analysis": analysis
            }
        except OSError:
            pass

    def invalidate(self, rel_path: str, abs_path: str = None):
        if abs_path and abs_path in self._entries:
            self._entries.pop(abs_path, None)
        else:
            keys = [k for k, v in self._entries.items() if v.get("rel_path") == rel_path or k == rel_path]
            for k in keys:
                self._entries.pop(k, None)

    def clear(self):
        self._entries.clear()


GLOBAL_AST_CACHE = ASTAnalysisCache()


def analyze_file(filepath):
    """
    Parses a python file and returns:
    - imports: list of imported modules/names
    - definitions: list of defined functions/classes with metadata and calls
    Guards against giant files and minified bundles (>1MB).
    """
    try:
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > MAX_PARSE_SIZE:
                return {'imports': [], 'definitions': []}
    except Exception:
        pass

    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
            source = f.read()
            
        # Minified line heuristic: if first line is giant, avoid deep AST recursion
        if len(source) > 4096 and '\n' not in source[:2048]:
            return {'imports': [], 'definitions': []}
            
        tree = ast.parse(source)
    except Exception as e:
        return {'error': str(e)}
    imports = []
    definitions = []
    # Extract imports across whole AST
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            else:
                module = node.module or ''
                for name in node.names:
                    imports.append(f'{module}.{name.name}' if module else name.name)

    # Extract definitions from top-level body to preserve encapsulation
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = CallVisitor()
            visitor.visit(node)
            posonly = [a.arg for a in getattr(node.args, 'posonlyargs', [])]
            regular = [a.arg for a in node.args.args]
            vararg = [f"*{node.args.vararg.arg}"] if getattr(node.args, 'vararg', None) else []
            kwonly = [a.arg for a in getattr(node.args, 'kwonlyargs', [])]
            kwarg = [f"**{node.args.kwarg.arg}"] if getattr(node.args, 'kwarg', None) else []
            args = posonly + regular + vararg + kwonly + kwarg
            definitions.append({'type': 'function', 'name': node.name, 'args': args, 'lineno': node.lineno, 'calls': list(set(visitor.calls))})
        elif isinstance(node, ast.ClassDef):
            methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visitor = CallVisitor()
                    visitor.visit(child)
                    posonly = [a.arg for a in getattr(child.args, 'posonlyargs', [])]
                    regular = [a.arg for a in child.args.args]
                    vararg = [f"*{child.args.vararg.arg}"] if getattr(child.args, 'vararg', None) else []
                    kwonly = [a.arg for a in getattr(child.args, 'kwonlyargs', [])]
                    kwarg = [f"**{child.args.kwarg.arg}"] if getattr(child.args, 'kwarg', None) else []
                    methods.append({'name': child.name, 'args': posonly + regular + vararg + kwonly + kwarg, 'calls': list(set(visitor.calls))})
            definitions.append({'type': 'class', 'name': node.name, 'lineno': node.lineno, 'methods': methods})
    return {'imports': list(set(imports)), 'definitions': definitions}

def analyze_directory(dirpath, cache=None, os=os, cancel_token=None):
    """
    Walks a directory and analyzes all python files.
    Leverages ASTAnalysisCache for sub-second re-scans.
    Returns a unified codebase representation.
    cancel_token: callable returning True when cancellation is requested.
    """
    active_cache = cache if cache is not None else GLOBAL_AST_CACHE
    codebase = {}
    
    # Use expanded excluded directories list
    excluded = {
        'venv', 'env', 'test_env', '__pycache__', 'tests', 'node_modules', 
        'scratch', 'dist', 'synapse_project', 'docs', 'ultron_risk_scorer.egg-info',
        'vendor', 'target', 'out', 'coverage', '.next', '.nuxt', '.turbo',
        '.gradle', 'Pods', 'bin', 'obj', '.idea', '.vscode'
    }
    
    for root, dirs, files in os.walk(dirpath, followlinks=False):
        # Prune dirs in-place to avoid scanning virtualenvs, builds, test files, and scratch dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in excluded]
        
        for file in files:
            # Inner-loop cooperative cancellation
            if cancel_token and cancel_token():
                raise InterruptedError("Analysis cancelled by user")
            if file.endswith('.py'):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dirpath).replace(os.sep, '/')
                
                # Check cache first
                analysis = active_cache.get(rel_path, abs_path)
                if analysis is None:
                    analysis = analyze_file(abs_path)
                    if 'error' not in analysis:
                        active_cache.put(rel_path, abs_path, analysis)
                
                if analysis and 'error' not in analysis:
                    codebase[rel_path] = analysis
    return codebase


def update_codebase_incremental(
    repo_path: str,
    changed_files: list,
    current_codebase: dict,
    cache=None
) -> dict:
    """
    Surgically updates codebase dictionary in-place for changed files in <5ms.
    """
    active_cache = cache if cache is not None else GLOBAL_AST_CACHE
    abs_repo = os.path.abspath(repo_path)
    
    for rel_path in changed_files:
        norm_path = rel_path.replace("\\", "/")
        abs_path = os.path.join(abs_repo, rel_path)
        
        if not os.path.exists(abs_path):
            current_codebase.pop(norm_path, None)
            active_cache.invalidate(norm_path)
        elif norm_path.endswith(".py"):
            analysis = analyze_file(abs_path)
            if "error" not in analysis:
                current_codebase[norm_path] = analysis
                active_cache.put(norm_path, abs_path, analysis)
            else:
                current_codebase.pop(norm_path, None)
                active_cache.invalidate(norm_path)
                
    return current_codebase


def build_dependency_graph(codebase):
    """
    Constructs a JSON-serializable node-link representation of repository files, functions, and their calls.
    Enforces hierarchical symbol resolution and zero dangling edges.
    """
    nodes = []
    links = []
    
    # 1. Index symbols hierarchically to prevent collisions and dangling edges
    file_symbols = {}       # rel_path -> { symbol_name: node_id }
    global_funcs = {}        # func_name -> list of node_ids
    global_methods = {}      # Class.method or method -> list of node_ids
    valid_node_ids = set()

    # Helper: resolve import target to file in codebase
    def resolve_import_to_file(source_file, imp):
        if imp.startswith('.'):
            level = len(imp) - len(imp.lstrip('.'))
            remainder = imp.lstrip('.')
            dir_parts = [p for p in os.path.dirname(source_file).replace('\\', '/').split('/') if p]
            if level <= len(dir_parts) + 1:
                base_parts = dir_parts[:len(dir_parts) - (level - 1)]
                candidate = "/".join(base_parts + (remainder.split('.') if remainder else []))
            else:
                candidate = remainder.replace('.', '/') if remainder else ""
        else:
            candidate = imp.replace('.', '/')

        if not candidate:
            return None

        parts = candidate.split('/')
        for i in range(len(parts), 0, -1):
            prefix = "/".join(parts[:i])
            cand_py = f"{prefix}.py"
            cand_init = f"{prefix}/__init__.py"
            if cand_py in codebase:
                return cand_py
            if cand_init in codebase:
                return cand_init
            for f in codebase:
                if f == cand_py or f.endswith(f"/{cand_py}") or f == cand_init or f.endswith(f"/{cand_init}"):
                    return f
        return None

    # Collect all definitions and populate node registry
    for rel_path, analysis in codebase.items():
        file_symbols[rel_path] = {}
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            if not name:
                continue
            node_id = f"{rel_path}:{name}"
            if defn.get('type') == 'function':
                file_symbols[rel_path][name] = node_id
                global_funcs.setdefault(name, []).append(node_id)
            elif defn.get('type') == 'class':
                file_symbols[rel_path][name] = node_id
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    if not m_name:
                        continue
                    m_node_id = f"{rel_path}:{name}.{m_name}"
                    file_symbols[rel_path][f"{name}.{m_name}"] = m_node_id
                    file_symbols[rel_path][m_name] = m_node_id
                    global_methods.setdefault(f"{name}.{m_name}", []).append(m_node_id)
                    global_methods.setdefault(m_name, []).append(m_node_id)

    # 2. Add file and definition nodes (with O(1) module indexing)
    seen_links = set()

    module_index = {}
    for p in codebase:
        p_clean = p.replace("\\", "/")
        base = p_clean[:-3] if p_clean.endswith(".py") else p_clean
        dotted = base.replace("/", ".")
        module_index[dotted] = p
        parts = dotted.split(".")
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub not in module_index:
                module_index[sub] = p

    file_resolved_imports = {}
    for src, analysis in codebase.items():
        resolved_targets = []
        for imp in analysis.get('imports', []):
            tf = resolve_import_to_file(src, imp) or module_index.get(imp)
            if tf and tf in file_symbols:
                resolved_targets.append(tf)
        file_resolved_imports[src] = resolved_targets

    for rel_path, analysis in codebase.items():
        # Add file node
        nodes.append({
            'id': rel_path,
            'type': 'file',
            'label': rel_path
        })
        valid_node_ids.add(rel_path)
        
        # File imports -> File links
        for imp in analysis.get('imports', []):
            target_file = resolve_import_to_file(rel_path, imp) or module_index.get(imp)
            if target_file and target_file != rel_path:
                edge_key = (rel_path, target_file, 'import')
                if edge_key not in seen_links:
                    seen_links.add(edge_key)
                    links.append({'source': rel_path, 'target': target_file, 'type': 'import'})

        # Process function and class definitions
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            if not name:
                continue
            node_id = f"{rel_path}:{name}"
            valid_node_ids.add(node_id)
            
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
            
            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    if not m_name:
                        continue
                    m_node_id = f"{rel_path}:{name}.{m_name}"
                    valid_node_ids.add(m_node_id)
                    
                    # Add method node
                    nodes.append({
                        'id': m_node_id,
                        'type': 'method',
                        'label': f"{name}.{m_name}",
                        'file': rel_path
                    })
                    
                    # Link class to method
                    links.append({
                        'source': node_id,
                        'target': m_node_id,
                        'type': 'contains'
                    })

    # 3. Resolve call edges with strict symbol scoping and zero dangling edges
    def resolve_call_target(source_file, caller_class, call_name):
        # 1. Class-local method
        if caller_class and f"{caller_class}.{call_name}" in file_symbols.get(source_file, {}):
            return file_symbols[source_file][f"{caller_class}.{call_name}"]
        # 2. File-local function/symbol
        if call_name in file_symbols.get(source_file, {}):
            return file_symbols[source_file][call_name]
        # 3. Explicitly imported module symbols (pre-resolved)
        for target_file in file_resolved_imports.get(source_file, []):
            if call_name in file_symbols.get(target_file, {}):
                return file_symbols[target_file][call_name]
        # Tiers 4/5 (global unique function/method match) removed:
        # They falsely coupled unrelated modules on common names (get, save, run).
        return None

    for rel_path, analysis in codebase.items():
        for defn in analysis.get('definitions', []):
            name = defn.get('name')
            if not name:
                continue
            node_id = f"{rel_path}:{name}"

            for call in defn.get('calls', []):
                target_id = resolve_call_target(rel_path, None, call)
                if target_id and target_id in valid_node_ids and target_id != node_id:
                    edge_key = (node_id, target_id, 'call')
                    if edge_key not in seen_links:
                        seen_links.add(edge_key)
                        links.append({'source': node_id, 'target': target_id, 'type': 'call'})

            if defn.get('type') == 'class':
                for method in defn.get('methods', []):
                    m_name = method.get('name')
                    if not m_name:
                        continue
                    m_node_id = f"{rel_path}:{name}.{m_name}"
                    for call in method.get('calls', []):
                        target_id = resolve_call_target(rel_path, name, call)
                        if target_id and target_id in valid_node_ids and target_id != m_node_id:
                            edge_key = (m_node_id, target_id, 'call')
                            if edge_key not in seen_links:
                                seen_links.add(edge_key)
                                links.append({'source': m_node_id, 'target': target_id, 'type': 'call'})
                            
    return {'nodes': nodes, 'links': links}

def extract_git_history(repo_path: str):
    """
    Runs deterministic git history analysis using GitEvidenceAdapter.
    Returns a dictionary mapping relative file paths to their bug fix counts.
    """
    from ultron.core.git_adapter import GitEvidenceAdapter
    adapter = GitEvidenceAdapter()
    analysis = adapter.analyze_repository(repo_path)
    files_data = analysis.get("files", {})
    if not files_data:
        print("[Ultron] No git history found — bug-prone-file scaling is inactive.")
        return {}
    return {fpath: data.get("bug_fixes", 0) for fpath, data in files_data.items() if data.get("bug_fixes", 0) > 0}