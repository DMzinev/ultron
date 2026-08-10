"""
Ultron Core — Language Adapter Abstraction & Python Implementation
Campaign 29 / v2.3 — Canonical Software System Model Architecture
"""

import sys
import os
import ast
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

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

    def parse_repository(self, repo_path: str) -> SystemGraph:
        manager = SystemModelManager()
        abs_repo = os.path.abspath(repo_path)
        norm_repo = os.path.normpath(abs_repo).replace("\\", "/")

        for root, dirs, files in os.walk(abs_repo):
            # Skip hidden/virtualenv/cache directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "__pycache__", "build", "dist")]
            
            for fname in files:
                if not fname.endswith(".py"):
                    continue

                abs_filepath = os.path.join(root, fname)
                norm_filepath = os.path.normpath(abs_filepath).replace("\\", "/")
                
                # Compute repo-relative POSIX path
                try:
                    rel_path = os.path.relpath(norm_filepath, norm_repo).replace("\\", "/")
                except ValueError:
                    rel_path = norm_filepath

                node_id = f"module:{rel_path}"
                node_type = SystemNodeType.TEST if ("test" in fname or "tests" in rel_path) else SystemNodeType.MODULE

                # Create base module node
                module_node = SystemNode(
                    id=node_id,
                    type=node_type,
                    file_path=rel_path,
                    facts={"language": "python", "loc": 0}
                )

                # Read source code safely
                try:
                    with open(abs_filepath, "r", encoding="utf-8", errors="replace") as f:
                        source_code = f.read()

                    loc = len([line for line in source_code.splitlines() if line.strip() and not line.strip().startswith("#")])
                    module_node.facts["loc"] = loc
                    module_node.line_end = max(1, len(source_code.splitlines()))

                    # Parse AST safely
                    tree = ast.parse(source_code, filename=rel_path)
                    
                    # Inspect AST definitions and imports
                    complexity_counter = 1
                    for item in ast.walk(tree):
                        if isinstance(item, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                            complexity_counter += 1
                        
                        elif isinstance(item, ast.Import):
                            for alias in item.names:
                                imp_name = alias.name
                                edge = SystemEdge(
                                    source_id=node_id,
                                    target_id=f"module:{imp_name.replace('.', '/')}",
                                    type=SystemEdgeType.IMPORTS
                                )
                                manager.add_edge(edge)

                        elif isinstance(item, ast.ImportFrom):
                            if item.module:
                                imp_name = item.module
                                edge = SystemEdge(
                                    source_id=node_id,
                                    target_id=f"module:{imp_name.replace('.', '/')}",
                                    type=SystemEdgeType.IMPORTS
                                )
                                manager.add_edge(edge)

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
                    
                    # Create EvidenceObject for AST facts
                    ev_ast = EvidenceObject(
                        id=f"ev-ast-{rel_path.replace('/', '_')}",
                        type="AST_FACT",
                        subject_id=node_id,
                        measurement={"loc": loc, "complexity": complexity_counter},
                        source={"adapter": "python", "file": rel_path}
                    )
                    manager.add_evidence(ev_ast)

                except SyntaxError as syn_err:
                    logger.warning("[PythonAdapter Warning] Syntax error in '%s': %s", rel_path, syn_err)
                    module_node.facts["parse_error"] = f"SyntaxError: {str(syn_err)}"
                except OSError as os_err:
                    logger.warning("[PythonAdapter Warning] File read error in '%s': %s", rel_path, os_err)
                    module_node.facts["parse_error"] = f"OSError: {str(os_err)}"

                manager.add_node(module_node)

        return manager.graph
