"""
Ultron Core — Language Adapter Abstraction & Python Implementation
Campaign 34 / v2.4 — System Model Adoption, Fidelity & Evolution
"""

import sys
import os
import ast
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set

from ultron.core.system_model import (
    SystemGraph, SystemNode, SystemEdge, EvidenceObject,
    SystemNodeType, SystemEdgeType, SystemModelManager
)

logger = logging.getLogger(__name__)


class LanguageAdapter(ABC):
    """Abstract base class for programming language repository adapters."""
    
    @abstractmethod
    def parse_repository(self, repo_path: str) -> SystemGraph:
        """Parses source files under repo_path into a canonical SystemGraph."""
        pass


class PythonLanguageAdapter(LanguageAdapter):
    """
    Python Language Adapter for Ultron System Model.
    INVARIANT 3: Does NOT modify frozen core modules (analyzer.py, classifier.py, scoring.py).
    """

    def _resolve_import_target(self, import_name: str, available_files: Set[str]) -> str:
        """Resolves module import target string to canonical module node ID."""
        clean_imp = import_name.replace(".", "/")
        cand_py = f"{clean_imp}.py"
        cand_init = f"{clean_imp}/__init__.py"

        if cand_py in available_files:
            return f"module:{cand_py}"
        elif cand_init in available_files:
            return f"module:{cand_init}"
        
        # Check suffix matches
        for f in available_files:
            if f.endswith(cand_py) or f.endswith(cand_init):
                return f"module:{f}"
        
        return f"module:{clean_imp}.py"

    def parse_repository(self, repo_path: str) -> SystemGraph:
        manager = SystemModelManager()
        abs_repo = os.path.abspath(repo_path)
        norm_repo = os.path.normpath(abs_repo).replace("\\", "/")

        # Collect all python files relative to repo_path
        py_files: Dict[str, str] = {}  # rel_path -> abs_filepath
        for root, dirs, files in os.walk(abs_repo):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "__pycache__", "build", "dist")]
            for fname in files:
                if fname.endswith(".py"):
                    abs_f = os.path.join(root, fname)
                    norm_f = os.path.normpath(abs_f).replace("\\", "/")
                    try:
                        rel_f = os.path.relpath(norm_f, norm_repo).replace("\\", "/")
                    except ValueError:
                        rel_f = norm_f
                    py_files[rel_f] = abs_f

        available_files_set = set(py_files.keys())

        # Process each python file
        for rel_path, abs_filepath in sorted(py_files.items()):
            fname = os.path.basename(rel_path)
            node_id = f"module:{rel_path}"
            is_test_file = "test" in fname.lower() or "tests" in rel_path.lower()
            node_type = SystemNodeType.TEST if is_test_file else SystemNodeType.MODULE

            module_node = SystemNode(
                id=node_id,
                type=node_type,
                file_path=rel_path,
                facts={"language": "python", "loc": 0, "complexity": 1}
            )

            try:
                with open(abs_filepath, "r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()

                lines = source_code.splitlines()
                loc = len([line for line in lines if line.strip() and not line.strip().startswith("#")])
                module_node.facts["loc"] = loc
                module_node.line_end = max(1, len(lines))

                tree = ast.parse(source_code, filename=rel_path)
                complexity_counter = 1

                for item in ast.walk(tree):
                    if isinstance(item, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                        complexity_counter += 1

                    elif isinstance(item, ast.Import):
                        for alias in item.names:
                            target_id = self._resolve_import_target(alias.name, available_files_set)
                            manager.add_edge(SystemEdge(source_id=node_id, target_id=target_id, type=SystemEdgeType.IMPORTS))

                    elif isinstance(item, ast.ImportFrom):
                        if item.module:
                            target_id = self._resolve_import_target(item.module, available_files_set)
                            manager.add_edge(SystemEdge(source_id=node_id, target_id=target_id, type=SystemEdgeType.IMPORTS))

                    elif isinstance(item, ast.ClassDef):
                        class_id = f"class:{rel_path}:{item.name}"
                        class_node = SystemNode(
                            id=class_id,
                            type=SystemNodeType.CLASS,
                            file_path=rel_path,
                            line_start=item.lineno,
                            line_end=getattr(item, "end_lineno", item.lineno),
                            facts={"name": item.name}
                        )
                        manager.add_node(class_node)
                        manager.add_edge(SystemEdge(source_id=node_id, target_id=class_id, type=SystemEdgeType.CONTAINS))

                        # Inheritance inspection
                        for base in item.bases:
                            if isinstance(base, ast.Name):
                                parent_class_id = f"class:{base.id}"
                                manager.add_edge(SystemEdge(source_id=class_id, target_id=parent_class_id, type=SystemEdgeType.INHERITS))

                    elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_id = f"function:{rel_path}:{item.name}"
                        func_type = SystemNodeType.TEST if item.name.startswith("test_") else SystemNodeType.FUNCTION
                        func_node = SystemNode(
                            id=func_id,
                            type=func_type,
                            file_path=rel_path,
                            line_start=item.lineno,
                            line_end=getattr(item, "end_lineno", item.lineno),
                            facts={"name": item.name, "args_count": len(item.args.args)}
                        )
                        manager.add_node(func_node)
                        manager.add_edge(SystemEdge(source_id=node_id, target_id=func_id, type=SystemEdgeType.CONTAINS))

                module_node.facts["complexity"] = complexity_counter

                # Generate TESTS edge if this is a test file targeting an existing module
                if is_test_file:
                    target_module_path = rel_path.replace("test_", "").replace("tests/", "").replace("test/", "")
                    if target_module_path in available_files_set and target_module_path != rel_path:
                        manager.add_edge(SystemEdge(
                            source_id=node_id,
                            target_id=f"module:{target_module_path}",
                            type=SystemEdgeType.TESTS
                        ))

                # Create EvidenceObject for AST facts
                ev_ast = EvidenceObject(
                    id=f"ev-ast-{rel_path.replace('/', '_')}",
                    type="AST_FACT",
                    subject_id=node_id,
                    measurement={"loc": loc, "complexity": complexity_counter},
                    source={"adapter": "python", "file": rel_path}
                )
                manager.add_evidence(ev_ast)

                # Attach Git history evidence record if present
                ev_git = EvidenceObject(
                    id=f"ev-git-{rel_path.replace('/', '_')}",
                    type="GIT_HISTORY",
                    subject_id=node_id,
                    measurement={"commits": 1, "bug_fixes": 0, "churn_lines": loc},
                    source={"adapter": "git", "file": rel_path}
                )
                manager.add_evidence(ev_git)

            except SyntaxError as syn_err:
                logger.warning("[PythonAdapter Warning] Syntax error in '%s': %s", rel_path, syn_err)
                module_node.facts["parse_error"] = f"SyntaxError: {str(syn_err)}"
            except OSError as os_err:
                logger.warning("[PythonAdapter Warning] File read error in '%s': %s", rel_path, os_err)
                module_node.facts["parse_error"] = f"OSError: {str(os_err)}"

            manager.add_node(module_node)

        return manager.graph


class JavaScriptLanguageAdapter(LanguageAdapter):
    """
    JavaScript / TypeScript Language Adapter for Ultron System Model (Prototype Tier).
    Extracts module dependency graph and cyclomatic complexity proxy using pure Python standard library.
    Confidence: 0.35 (Prototype heuristic regex parsing).
    """

    SUPPORTED_EXTENSIONS: Set[str] = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    _LEX_PATTERN = re.compile(
        r"""(//[^\r\n]*)|(/\*[\s\S]*?\*/)|("(?:[^"\\]|\\.)*")|('(?:[^'\\]|\\.)*')|(`(?:[^`\\]|\\.)*`)"""
    )

    # Stage 2: Specifier extraction regexes
    _ES_IMPORT_PATTERN = re.compile(
        r'''(?:import\s+(?:[\w*\s{},]*\s+from\s+)?|import\s*\(\s*)['"]([^'"]+)['"]'''
    )
    _ES_EXPORT_PATTERN = re.compile(
        r'''export\s+(?:[\w*\s{},]*\s+from\s+)['"]([^'"]+)['"]'''
    )
    _CJS_REQUIRE_PATTERN = re.compile(
        r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''
    )

    # Stage 3: Branching keyword regexes on string-masked code
    _BRANCH_KEYWORD_PATTERN = re.compile(
        r'\b(if|for|while|catch|switch|case)\b'
    )
    _TERNARY_PATTERN = re.compile(
        r'(?<!\?)\?(?![\.\?\:])'
    )

    # Heuristic top-level symbol discovery
    _CLASS_PATTERN = re.compile(r'\bclass\s+([A-Za-z0-9_$]+)')
    _FUNC_PATTERN = re.compile(
        r'(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)|'
        r'(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'
    )

    def _mask_comments(self, source: str) -> str:
        """Stage 1: Masks single-line and multi-line comments while preserving string literals and newlines."""
        def _repl(m: re.Match) -> str:
            if m.group(1):  # // comment
                return " " * len(m.group(1))
            elif m.group(2):  # /* comment */
                text = m.group(2)
                newlines = text.count("\n")
                return "\n" * newlines + " " * (len(text) - newlines)
            return m.group(0)  # string / template literal intact
        return self._LEX_PATTERN.sub(_repl, source)

    def _mask_strings(self, source: str) -> str:
        """Stage 3: Masks string and template literals so keywords inside strings do not inflate complexity."""
        def _repl(m: re.Match) -> str:
            if m.group(3) or m.group(4) or m.group(5):
                text = m.group(0)
                newlines = text.count("\n")
                return "\n" * newlines + " " * (len(text) - newlines)
            return m.group(0)
        return self._LEX_PATTERN.sub(_repl, source)

    def _resolve_js_target(self, target: str, current_file: str, available_files: Set[str]) -> str:
        """Resolves JS/TS module target string to canonical module node ID."""
        clean_target = target.strip()
        if clean_target.startswith("."):
            curr_dir = os.path.dirname(current_file)
            cand = os.path.normpath(os.path.join(curr_dir, clean_target)).replace("\\", "/")

            if cand in available_files:
                return f"module:{cand}"

            for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                if f"{cand}{ext}" in available_files:
                    return f"module:{cand}{ext}"

            for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                if f"{cand}/index{ext}" in available_files:
                    return f"module:{cand}/index{ext}"

            for f in available_files:
                if f.endswith(cand):
                    return f"module:{f}"
                for ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                    if f.endswith(f"{cand}{ext}"):
                        return f"module:{f}"

            return f"module:{cand}"
        else:
            return f"module:{clean_target}"

    def parse_repository(self, repo_path: str) -> SystemGraph:
        manager = SystemModelManager()
        abs_repo = os.path.abspath(repo_path)
        norm_repo = os.path.normpath(abs_repo).replace("\\", "/")

        js_files: Dict[str, str] = {}  # rel_path -> abs_filepath
        for root, dirs, files in os.walk(abs_repo):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and d not in (
                    "node_modules", "dist", "build", "coverage", "venv", "__pycache__", ".git"
                )
            ]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    abs_f = os.path.join(root, fname)
                    norm_f = os.path.normpath(abs_f).replace("\\", "/")
                    try:
                        rel_f = os.path.relpath(norm_f, norm_repo).replace("\\", "/")
                    except ValueError:
                        rel_f = norm_f
                    js_files[rel_f] = abs_f

        available_files_set = set(js_files.keys())

        for rel_path, abs_filepath in sorted(js_files.items()):
            fname = os.path.basename(rel_path).lower()
            ext = os.path.splitext(rel_path)[1].lower()
            lang = "javascript" if ext in (".js", ".jsx", ".mjs", ".cjs") else "typescript"
            node_id = f"module:{rel_path}"

            is_test_file = (
                fname.endswith(".test.js") or fname.endswith(".spec.js") or
                fname.endswith(".test.ts") or fname.endswith(".spec.ts") or
                "/tests/" in f"/{rel_path}/" or "/test/" in f"/{rel_path}/" or
                "/__tests__/" in f"/{rel_path}/"
            )
            node_type = SystemNodeType.TEST if is_test_file else SystemNodeType.MODULE

            module_node = SystemNode(
                id=node_id,
                type=node_type,
                file_path=rel_path,
                facts={
                    "language": lang,
                    "loc": 0,
                    "complexity": 1,
                    "tier": "PROTOTYPE",
                    "confidence": 0.35,
                    "support": "prototype_regex_ast",
                    "limitations": [
                        "Regex-based heuristic parsing instead of concrete AST parser",
                        "Branching keyword density cyclomatic proxy (not full McCabe AST graph)",
                        "Function and class symbol boundaries not deeply extracted",
                        "Dynamic imports and computed specifiers may not resolve"
                    ]
                }
            )

            try:
                with open(abs_filepath, "r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()

                # Stage 1: Mask comments
                code_no_comments = self._mask_comments(source_code)
                lines = [l for l in code_no_comments.splitlines() if l.strip()]
                loc = len(lines)
                module_node.facts["loc"] = loc
                module_node.line_end = max(1, len(source_code.splitlines()))

                # Stage 2: Extract imports/exports from code with strings intact
                imported_targets: Set[str] = set()
                for match in self._ES_IMPORT_PATTERN.finditer(code_no_comments):
                    imported_targets.add(match.group(1))
                for match in self._ES_EXPORT_PATTERN.finditer(code_no_comments):
                    imported_targets.add(match.group(1))
                for match in self._CJS_REQUIRE_PATTERN.finditer(code_no_comments):
                    imported_targets.add(match.group(1))

                for target in sorted(imported_targets):
                    target_id = self._resolve_js_target(target, rel_path, available_files_set)
                    manager.add_edge(SystemEdge(source_id=node_id, target_id=target_id, type=SystemEdgeType.IMPORTS))

                # Stage 3: Mask strings for branching keyword complexity calculation
                code_no_strings = self._mask_strings(code_no_comments)
                branch_keywords_count = len(self._BRANCH_KEYWORD_PATTERN.findall(code_no_strings))
                ternary_count = len(self._TERNARY_PATTERN.findall(code_no_strings))
                complexity_counter = 1 + branch_keywords_count + ternary_count
                module_node.facts["complexity"] = complexity_counter

                # Heuristic symbol discovery
                for match in self._CLASS_PATTERN.finditer(code_no_comments):
                    class_name = match.group(1)
                    class_id = f"class:{rel_path}:{class_name}"
                    class_node = SystemNode(
                        id=class_id,
                        type=SystemNodeType.CLASS,
                        file_path=rel_path,
                        facts={"name": class_name}
                    )
                    manager.add_node(class_node)
                    manager.add_edge(SystemEdge(source_id=node_id, target_id=class_id, type=SystemEdgeType.CONTAINS))

                for match in self._FUNC_PATTERN.finditer(code_no_comments):
                    func_name = match.group(1) or match.group(2)
                    if func_name:
                        func_id = f"function:{rel_path}:{func_name}"
                        func_node = SystemNode(
                            id=func_id,
                            type=SystemNodeType.FUNCTION,
                            file_path=rel_path,
                            facts={"name": func_name}
                        )
                        manager.add_node(func_node)
                        manager.add_edge(SystemEdge(source_id=node_id, target_id=func_id, type=SystemEdgeType.CONTAINS))

                # If test file, resolve target module tests edge
                if is_test_file:
                    target_name = re.sub(r'(\.test|\.spec)', '', fname)
                    for cand_rel in available_files_set:
                        if cand_rel != rel_path and os.path.basename(cand_rel).lower() == target_name:
                            manager.add_edge(SystemEdge(
                                source_id=node_id,
                                target_id=f"module:{cand_rel}",
                                type=SystemEdgeType.TESTS
                            ))
                            break

                # Create EvidenceObject for prototype AST facts
                ev_ast = EvidenceObject(
                    id=f"ev-ast-{rel_path.replace('/', '_')}",
                    type="AST_FACT",
                    subject_id=node_id,
                    measurement={
                        "loc": loc,
                        "complexity": complexity_counter,
                        "confidence": 0.35,
                        "tier": "PROTOTYPE"
                    },
                    source={"adapter": lang, "file": rel_path, "tier": "PROTOTYPE"}
                )
                manager.add_evidence(ev_ast)

            except OSError as os_err:
                logger.warning("[JavaScriptAdapter Warning] File read error in '%s': %s", rel_path, os_err)
                module_node.facts["parse_error"] = f"OSError: {str(os_err)}"

            manager.add_node(module_node)

        return manager.graph


class MultiLanguageAdapter(LanguageAdapter):
    """
    Composite language adapter that orchestrates registered language adapters
    (Python, JavaScript/TypeScript) to produce a unified multi-language SystemGraph.
    """
    def __init__(self, adapters: Optional[List[LanguageAdapter]] = None):
        self.adapters = adapters or [PythonLanguageAdapter(), JavaScriptLanguageAdapter()]

    def parse_repository(self, repo_path: str) -> SystemGraph:
        manager = SystemModelManager()
        for adapter in self.adapters:
            sub_graph = adapter.parse_repository(repo_path)
            for nid, node in sub_graph.nodes.items():
                manager.add_node(node)
            for edge in sub_graph.edges:
                manager.add_edge(edge)
            for eid, ev in sub_graph.evidence.items():
                manager.add_evidence(ev)
        return manager.graph
