"""
ultron.core.polyglot_adapter
Multi-Language AST and Import Extraction Engine (TypeScript, JavaScript, Python, Go).
"""

import os
import re
import ast
from typing import Dict, List, Any, Optional


def norm_path(path_str: Any) -> str:
    """Normalizes file paths to POSIX forward slashes."""
    return str(path_str or "").replace("\\", "/").strip()


class PolyglotAdapter:
    """
    Deterministic polyglot source code parser extracting definitions,
    import dependencies, and cyclomatic complexity across TS, JS, Go, and Python.
    """

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".go": "go"
    }

    @classmethod
    def detect_language(cls, file_path: str) -> str:
        """Determines programming language from file extension."""
        p = norm_path(file_path).lower()
        for ext, lang in cls.LANGUAGE_EXTENSIONS.items():
            if p.endswith(ext):
                return lang
        return "unknown"

    @classmethod
    def parse_file(cls, file_path: str, content: Any) -> Dict[str, Any]:
        """
        Parses source file content and returns a unified FileASTRecord.
        """
        norm_file = norm_path(file_path)
        lang = cls.detect_language(norm_file)
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        elif not isinstance(content, str):
            content = str(content or "")
        if "\x00" in content:
            content = content.replace("\x00", "")
        loc = len(content.splitlines()) if content else 0

        if not content or not content.strip():
            return {
                "file_path": norm_file,
                "language": lang,
                "loc": loc,
                "complexity": 1.0,
                "imports": [],
                "functions": [],
                "classes": [],
                "package": None
            }

        if lang in {"typescript", "javascript"}:
            return cls._parse_typescript_javascript(norm_file, content, lang)
        elif lang == "go":
            return cls._parse_go(norm_file, content)
        elif lang == "python":
            return cls._parse_python(norm_file, content)
        else:
            return {
                "file_path": norm_file,
                "language": "unknown",
                "loc": loc,
                "complexity": 1.0,
                "imports": [],
                "functions": [],
                "classes": [],
                "package": None
            }

    @classmethod
    def _parse_typescript_javascript(cls, file_path: str, content: str, lang: str) -> Dict[str, Any]:
        """Extracts imports, classes, functions, and complexity for JS/TS."""
        imports: List[str] = []
        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []

        # 1. ES6 Imports: import ... from 'module'
        es6_imports = re.findall(r'''(?:import|export)\s+(?:(?:type\s+)?[\w\s{},*]+from\s+)?['"]([^'"]+)['"]''', content)
        for imp in es6_imports:
            if imp not in imports:
                imports.append(imp)

        # 2. CommonJS: require('module')
        cjs_imports = re.findall(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)''', content)
        for imp in cjs_imports:
            if imp not in imports:
                imports.append(imp)

        # 3. Dynamic Imports: import('module')
        dyn_imports = re.findall(r'''import\s*\(\s*['"]([^'"]+)['"]\s*\)''', content)
        for imp in dyn_imports:
            if imp not in imports:
                imports.append(imp)

        # 4. Classes: class Name ...
        class_matches = re.finditer(r'''class\s+([A-Za-z0-9_$]+)''', content)
        for m in class_matches:
            classes.append({"name": m.group(1), "type": "class"})

        # 5. Functions & Methods
        fn_matches = re.finditer(r'''(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*([A-Za-z0-9_$]+)?\s*\(''', content)
        for m in fn_matches:
            if m.group(1):
                functions.append({"name": m.group(1), "type": "function"})

        arrow_matches = re.finditer(r'''(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>''', content)
        for m in arrow_matches:
            functions.append({"name": m.group(1), "type": "arrow_function"})

        # 6. McCabe Cyclomatic Complexity (Syntactic Branch Tokens)
        branch_patterns = [
            r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bwhile\b',
            r'\bcatch\b', r'\bcase\b', r'&&', r'\|\|', r'\?\?', r'(?<![\?\.\:\w])\?(?![\?\.\:\w])'
        ]
        branches = 0
        for pat in branch_patterns:
            branches += len(re.findall(pat, content))

        complexity = max(1.0, float(1 + branches))

        return {
            "file_path": file_path,
            "language": lang,
            "loc": len(content.splitlines()),
            "complexity": complexity,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "package": None
        }

    @classmethod
    def _parse_go(cls, file_path: str, content: str) -> Dict[str, Any]:
        """Extracts imports, packages, structs, functions, and complexity for Go."""
        imports: List[str] = []
        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []

        # 1. Package Name: package <name>
        pkg_match = re.search(r'''^\s*package\s+([a-zA-Z0-9_]+)''', content, re.MULTILINE)
        package_name = pkg_match.group(1) if pkg_match else "main"

        # 2. Go Imports
        # Multi-line import ( "fmt" \n "os" )
        multiline_blocks = re.findall(r'''import\s*\((.*?)\)''', content, re.DOTALL)
        for block in multiline_blocks:
            lines = re.findall(r'''["']([^"']+)["']''', block)
            for imp in lines:
                if imp not in imports:
                    imports.append(imp)

        # Single-line import "fmt"
        single_imports = re.findall(r'''import\s+(?:[a-zA-Z0-9_.]+\s+)?["']([^"']+)["']''', content)
        for imp in single_imports:
            if imp not in imports:
                imports.append(imp)

        # 3. Structs & Interfaces: type Name struct / interface
        type_matches = re.finditer(r'''type\s+([A-Za-z0-9_]+)(?:\[[^\]]+\])?\s+(struct|interface)''', content)
        for m in type_matches:
            classes.append({"name": m.group(1), "type": m.group(2)})

        # 4. Functions & Methods: func (r *Receiver) Name(...) or func Name(...)
        fn_matches = re.finditer(r'''func\s+(?:\([A-Za-z0-9_*\s,\[\]]+\)\s+)?([A-Za-z0-9_]+)(?:\[[^\]]+\])?\s*\(''', content)
        for m in fn_matches:
            functions.append({"name": m.group(1), "type": "function"})

        # 5. Go McCabe Cyclomatic Complexity
        branch_patterns = [
            r'\bif\b', r'\bfor\b', r'\bcase\b', r'\bselect\b',
            r'\bdefer\b', r'\bgo\b', r'&&', r'\|\|'
        ]
        branches = 0
        for pat in branch_patterns:
            branches += len(re.findall(pat, content))

        complexity = max(1.0, float(1 + branches))

        return {
            "file_path": file_path,
            "language": "go",
            "loc": len(content.splitlines()),
            "complexity": complexity,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "package": package_name
        }

    @classmethod
    def _parse_python(cls, file_path: str, content: str) -> Dict[str, Any]:
        """Extracts imports, classes, functions, and complexity for Python."""
        imports: List[str] = []
        functions: List[Dict[str, Any]] = []
        classes: List[Dict[str, Any]] = []
        loc = len(content.splitlines())

        try:
            tree = ast.parse(content, filename=file_path)
            branches = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in imports:
                            imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    level_dots = "." * (node.level or 0)
                    mod = node.module or ""
                    prefix = f"{level_dots}{mod}" if (level_dots or mod) else ""
                    if prefix and prefix not in imports:
                        imports.append(prefix)
                    elif not prefix:
                        for alias in node.names:
                            if alias.name not in imports:
                                imports.append(alias.name)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, getattr(ast, "AsyncFunctionDef", ast.FunctionDef)):
                    functions.append({"name": node.name, "type": "function"})
                elif isinstance(node, ast.ClassDef):
                    classes.append({"name": node.name, "type": "class"})
                elif isinstance(node, (ast.If, getattr(ast, 'IfExp', ast.If), ast.For, getattr(ast, 'AsyncFor', ast.For), ast.While, ast.ExceptHandler, ast.With, getattr(ast, 'AsyncWith', ast.With), ast.Assert, getattr(ast, 'match_case', ast.If))):
                    branches += 1
                elif isinstance(node, ast.BoolOp):
                    branches += len(node.values) - 1

            complexity = max(1.0, float(1 + branches))
        except (SyntaxError, ValueError, Exception):
            # Fallback regex extraction on broken syntax or binary stream
            for m in re.finditer(r'''(?:from\s+([a-zA-Z0-9_.]+)\s+import|import\s+([a-zA-Z0-9_.]+))''', content):
                imp = m.group(1) or m.group(2)
                if imp and imp not in imports:
                    imports.append(imp)
            for m in re.finditer(r'''(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(''', content):
                functions.append({"name": m.group(1), "type": "function"})
            for m in re.finditer(r'''class\s+([a-zA-Z0-9_]+)''', content):
                classes.append({"name": m.group(1), "type": "class"})
            branch_count = len(re.findall(r'\b(if|elif|for|while|except|with|assert|case)\b|&&|\|\|', content))
            complexity = max(1.0, float(1 + branch_count))

        return {
            "file_path": file_path,
            "language": "python",
            "loc": loc,
            "complexity": complexity,
            "imports": imports,
            "functions": functions,
            "classes": classes,
            "package": None
        }
