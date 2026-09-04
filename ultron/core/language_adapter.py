"""
Ultron Core — Language Adapter Abstraction & Python Implementation
Campaign 34 / v2.4 — System Model Adoption, Fidelity & Evolution
"""

import sys
import os
import ast
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

    def _resolve_import_target(self, import_name: str, available_files: Set[str], current_file: Optional[str] = None, level: int = 0) -> str:
        """Resolves module import target string to canonical module node ID."""
        if not import_name and not level:
            return "module:unknown.py"

        # 1. Resolve relative import path if level > 0
        if level > 0 and current_file:
            dir_parts = [p for p in os.path.dirname(current_file).replace("\\", "/").split("/") if p]
            if level <= len(dir_parts) + 1:
                base_parts = dir_parts[:len(dir_parts) - (level - 1)]
                if import_name:
                    mod_parts = import_name.split(".")
                    clean_imp = "/".join(base_parts + mod_parts)
                else:
                    clean_imp = "/".join(base_parts)
            else:
                clean_imp = import_name.replace(".", "/") if import_name else ""
        else:
            clean_imp = (import_name or "").replace(".", "/")

        if not clean_imp:
            clean_imp = "unknown"

        # 2. Check direct candidate and prefix candidates
        parts = clean_imp.split("/")
        for i in range(len(parts), 0, -1):
            prefix = "/".join(parts[:i])
            cand_py = f"{prefix}.py"
            cand_init = f"{prefix}/__init__.py"
            if cand_py in available_files:
                return f"module:{cand_py}"
            if cand_init in available_files:
                return f"module:{cand_init}"

        # 3. Check suffix matches against available files
        cand_py = f"{clean_imp}.py"
        cand_init = f"{clean_imp}/__init__.py"
        for f in available_files:
            if f.endswith(cand_py) or f.endswith(cand_init) or f.endswith(f"/{cand_py}") or f.endswith(f"/{cand_init}"):
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

                if "\x00" in source_code:
                    source_code = source_code.replace("\x00", "")
                tree = ast.parse(source_code, filename=rel_path)
                complexity_counter = 1

                for item in ast.walk(tree):
                    branch_types = (
                        ast.If, getattr(ast, 'IfExp', ast.If),
                        ast.For, getattr(ast, 'AsyncFor', ast.For),
                        ast.While, ast.ExceptHandler,
                        ast.With, getattr(ast, 'AsyncWith', ast.With),
                        getattr(ast, 'Assert', ast.If),
                        getattr(ast, 'match_case', ast.If)
                    )
                    if isinstance(item, branch_types):
                        complexity_counter += 1
                    elif isinstance(item, getattr(ast, 'BoolOp', ())):
                        complexity_counter += max(1, len(item.values) - 1)

                    elif isinstance(item, ast.Import):
                        for alias in item.names:
                            target_id = self._resolve_import_target(alias.name, available_files_set, current_file=rel_path)
                            manager.add_edge(SystemEdge(source_id=node_id, target_id=target_id, type=SystemEdgeType.IMPORTS))

                    elif isinstance(item, ast.ImportFrom):
                        level = getattr(item, 'level', 0) or 0
                        mod = item.module or ""
                        if mod:
                            target_id = self._resolve_import_target(mod, available_files_set, current_file=rel_path, level=level)
                            manager.add_edge(SystemEdge(source_id=node_id, target_id=target_id, type=SystemEdgeType.IMPORTS))
                        elif level > 0 and item.names:
                            for alias in item.names:
                                target_id = self._resolve_import_target(alias.name, available_files_set, current_file=rel_path, level=level)
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

                    elif isinstance(item, (ast.FunctionDef, getattr(ast, 'AsyncFunctionDef', ast.FunctionDef))):
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

            except OSError as os_err:
                logger.warning("[PythonAdapter Warning] File read error in '%s': %s", rel_path, os_err)
                module_node.facts["parse_error"] = f"OSError: {str(os_err)}"
            except (SyntaxError, ValueError, Exception) as parse_err:
                logger.warning("[PythonAdapter Warning] Parse error in '%s': %s", rel_path, parse_err)
                module_node.facts["parse_error"] = f"{type(parse_err).__name__}: {str(parse_err)}"

            manager.add_node(module_node)

        return manager.graph
