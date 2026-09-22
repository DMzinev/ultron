"""
Monorepo Workspace & Multi-Package Architecture Module.

Provides automated detection of multi-package monorepo workspaces across
Python (pyproject.toml, poetry, uv), Node/TS (package.json, pnpm-workspace.yaml),
Rust (Cargo.toml), and convention-based directory layouts (packages/*, apps/*, libs/*).
Computes per-package architectural boundaries, cross-workspace dependencies,
and inter-package circular import cycles.
"""

import os
import re
import json
import glob
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple, Iterable

# Safe standard-library tomllib import for Python 3.11+, fallback to simple line parser
try:
    import tomllib
except ImportError:
    tomllib = None


class WorkspaceNotFoundError(ValueError):
    """Raised when a specified workspace package does not exist in the repository."""
    pass


@dataclass
class WorkspacePackage:
    name: str
    path: str  # Relative POSIX path from repository root, e.g. "packages/core"
    abs_path: str
    package_type: str  # "python", "node", "rust", "generic"
    manifest_file: Optional[str] = None
    files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "package_type": self.package_type,
            "manifest_file": self.manifest_file,
            "file_count": len(self.files),
            "metadata": self.metadata,
        }


def _sanitize_rel_path(p: str) -> str:
    """Normalizes path to forward slashes without leading/trailing slashes or traversals."""
    norm = os.path.normpath(p).replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    if norm == ".":
        return ""
    return norm.strip("/")


def _is_safe_workspace_path(repo_path: str, candidate_rel_path: str) -> bool:
    """Verifies that the candidate relative path does not escape the repository root."""
    if "\0" in candidate_rel_path:
        return False
    # Strict rejection of directory traversal
    parts = candidate_rel_path.replace("\\", "/").split("/")
    if any(p == ".." for p in parts):
        return False
    abs_root = os.path.abspath(os.path.normpath(repo_path))
    abs_candidate = os.path.abspath(os.path.join(abs_root, candidate_rel_path))
    try:
        common = os.path.commonpath([abs_root, abs_candidate])
        return common == abs_root
    except ValueError:
        return False


def _parse_toml_simple(content: str) -> Dict[str, Any]:
    """Lightweight pure-stdlib parser for basic TOML tables and lists if tomllib is unavailable."""
    if tomllib is not None:
        try:
            return tomllib.loads(content)
        except Exception:
            pass

    data: Dict[str, Any] = {}
    current_table = data
    in_multiline_list = False
    list_key = None
    list_acc: List[str] = []

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if in_multiline_list:
            if "]" in line:
                before_bracket, _, _ = line.partition("]")
                items = re.findall(r'["\']([^"\']+)["\']', before_bracket)
                list_acc.extend(items)
                if list_key:
                    current_table[list_key] = list_acc
                in_multiline_list = False
                list_key = None
                list_acc = []
            else:
                items = re.findall(r'["\']([^"\']+)["\']', line)
                list_acc.extend(items)
            continue

        # Table header [section] or [section.sub]
        table_m = re.match(r"^\[([^\]]+)\]$", line)
        if table_m:
            keys = table_m.group(1).split(".")
            curr = data
            for k in keys:
                k = k.strip()
                curr = curr.setdefault(k, {})
            current_table = curr
            continue

        # Key = Value (simple strings and list of strings)
        kv_m = re.match(r'^([A-Za-z0-9_\-\.]+)\s*=\s*(.+)$', line)
        if kv_m:
            key = kv_m.group(1).strip()
            val_str = kv_m.group(2).strip()
            # Array of strings
            if val_str.startswith("[") and val_str.endswith("]"):
                items = re.findall(r'["\']([^"\']+)["\']', val_str)
                current_table[key] = items
            elif val_str.startswith("[") and not val_str.endswith("]"):
                in_multiline_list = True
                list_key = key
                list_acc = re.findall(r'["\']([^"\']+)["\']', val_str)
            elif val_str.startswith('"') and val_str.endswith('"'):
                current_table[key] = val_str[1:-1]
            elif val_str.startswith("'") and val_str.endswith("'"):
                current_table[key] = val_str[1:-1]
    return data


def _extract_pyproject_workspaces(repo_path: str) -> List[str]:
    """Extracts workspace patterns from pyproject.toml (uv or poetry)."""
    pyproj_path = os.path.join(repo_path, "pyproject.toml")
    if not os.path.isfile(pyproj_path):
        return []
    try:
        with open(pyproj_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        parsed = _parse_toml_simple(content)
        # 1. uv workspace: [tool.uv.workspace] members = ["packages/*", ...]
        uv_members = parsed.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
        if uv_members and isinstance(uv_members, list):
            return [str(m) for m in uv_members]
        # 2. poetry packages: [tool.poetry] packages = [{include = "my_pkg", from = "packages"}]
        poetry_pkgs = parsed.get("tool", {}).get("poetry", {}).get("packages", [])
        patterns = []
        if isinstance(poetry_pkgs, list):
            for p in poetry_pkgs:
                if isinstance(p, dict):
                    frm = p.get("from", "")
                    inc = p.get("include", "")
                    if frm and inc:
                        patterns.append(f"{frm}/{inc}")
                    elif inc:
                        patterns.append(inc)
        if patterns:
            return patterns
    except Exception:
        pass
    return []


def _extract_package_json_workspaces(repo_path: str) -> List[str]:
    """Extracts workspace patterns from package.json (npm/yarn)."""
    pkg_json_path = os.path.join(repo_path, "package.json")
    if not os.path.isfile(pkg_json_path):
        return []
    try:
        with open(pkg_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        workspaces = data.get("workspaces")
        if isinstance(workspaces, list):
            return [str(w) for w in workspaces]
        if isinstance(workspaces, dict) and "packages" in workspaces:
            pkgs = workspaces.get("packages", [])
            if isinstance(pkgs, list):
                return [str(w) for w in pkgs]
    except Exception:
        pass
    return []


def _extract_pnpm_workspaces(repo_path: str) -> List[str]:
    """Extracts workspace patterns from pnpm-workspace.yaml."""
    pnpm_path = os.path.join(repo_path, "pnpm-workspace.yaml")
    if not os.path.isfile(pnpm_path):
        return []
    patterns = []
    try:
        with open(pnpm_path, "r", encoding="utf-8") as f:
            in_packages = False
            for line in f:
                stripped = line.strip()
                if stripped.startswith("packages:"):
                    in_packages = True
                    continue
                if in_packages:
                    if stripped.startswith("-"):
                        pat = stripped[1:].strip().strip("'\"")
                        if pat:
                            patterns.append(pat)
                    elif stripped and not stripped.startswith("#"):
                        break
    except Exception:
        pass
    return patterns


def _extract_cargo_workspaces(repo_path: str) -> List[str]:
    """Extracts workspace members from Cargo.toml."""
    cargo_path = os.path.join(repo_path, "Cargo.toml")
    if not os.path.isfile(cargo_path):
        return []
    try:
        with open(cargo_path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = _parse_toml_simple(content)
        members = parsed.get("workspace", {}).get("members", [])
        if isinstance(members, list):
            return [str(m) for m in members]
    except Exception:
        pass
    return []


def _expand_workspace_patterns(repo_path: str, patterns: List[str]) -> List[str]:
    """Expands glob patterns into concrete relative package directory paths."""
    resolved_paths: Set[str] = set()
    abs_repo = os.path.abspath(os.path.normpath(repo_path))

    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern or not _is_safe_workspace_path(repo_path, pattern):
            continue
        # Support trailing slash or wildcards
        clean_pat = pattern.replace("\\", "/").rstrip("/")
        full_pattern = os.path.join(abs_repo, clean_pat)
        matches = glob.glob(full_pattern)
        for m in matches:
            if os.path.isdir(m):
                rel = os.path.relpath(m, abs_repo).replace("\\", "/")
                # Discard ignored directories
                parts = rel.split("/")
                if any(part in (".git", "node_modules", "venv", ".venv", "__pycache__", "scratch", "dist", "build") for part in parts):
                    continue
                resolved_paths.add(rel)
    return sorted(list(resolved_paths))


def _discover_by_convention(repo_path: str) -> List[str]:
    """Discovers packages by looking inside standard monorepo folder conventions."""
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    convention_dirs = ("packages", "apps", "libs", "services", "components", "modules", "crates")
    discovered = []

    for c_dir in convention_dirs:
        full_c_dir = os.path.join(abs_repo, c_dir)
        if not os.path.isdir(full_c_dir):
            continue
        try:
            for entry in os.listdir(full_c_dir):
                if entry.startswith((".", "_")) or entry in ("node_modules", "venv", "__pycache__", "tests"):
                    continue
                subpath = os.path.join(full_c_dir, entry)
                if os.path.isdir(subpath):
                    # Check if directory looks like a code package (has python, manifest, or subdirs)
                    has_manifest = any(
                        os.path.isfile(os.path.join(subpath, m))
                        for m in ("pyproject.toml", "setup.py", "package.json", "Cargo.toml", "__init__.py")
                    )
                    has_code = False
                    if not has_manifest:
                        for _, _, files in os.walk(subpath):
                            if any(f.endswith((".py", ".js", ".ts", ".rs")) for f in files):
                                has_code = True
                                break
                    if has_manifest or has_code:
                        discovered.append(f"{c_dir}/{entry}")
        except Exception:
            pass
    return sorted(discovered)


def detect_workspaces(repo_path: str) -> List[WorkspacePackage]:
    """
    Detects all workspace packages in the given repository path.
    Inspects manifest files first (pyproject, package.json, pnpm, cargo),
    falling back to standard directory conventions.
    Returns a list of WorkspacePackage objects sorted by relative path.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    patterns: List[str] = []

    # 1. Manifest discovery
    patterns.extend(_extract_pyproject_workspaces(abs_repo))
    patterns.extend(_extract_package_json_workspaces(abs_repo))
    patterns.extend(_extract_pnpm_workspaces(abs_repo))
    patterns.extend(_extract_cargo_workspaces(abs_repo))

    rel_dirs = _expand_workspace_patterns(abs_repo, patterns) if patterns else []

    # 2. Convention discovery fallback if no explicit manifest workspaces found
    if not rel_dirs:
        rel_dirs = _discover_by_convention(abs_repo)

    workspaces: List[WorkspacePackage] = []
    seen_paths: Set[str] = set()

    for r_dir in rel_dirs:
        norm_rel = _sanitize_rel_path(r_dir)
        if not norm_rel or norm_rel in seen_paths:
            continue
        if not _is_safe_workspace_path(abs_repo, norm_rel):
            continue

        seen_paths.add(norm_rel)
        pkg_abs = os.path.join(abs_repo, norm_rel)

        # Detect package type and manifest
        pkg_type = "generic"
        manifest_file = None
        pkg_name = os.path.basename(norm_rel)

        if os.path.isfile(os.path.join(pkg_abs, "pyproject.toml")):
            pkg_type = "python"
            manifest_file = f"{norm_rel}/pyproject.toml"
        elif os.path.isfile(os.path.join(pkg_abs, "setup.py")):
            pkg_type = "python"
            manifest_file = f"{norm_rel}/setup.py"
        elif os.path.isfile(os.path.join(pkg_abs, "package.json")):
            pkg_type = "node"
            manifest_file = f"{norm_rel}/package.json"
            try:
                with open(os.path.join(pkg_abs, "package.json"), "r", encoding="utf-8") as f:
                    pj = json.load(f)
                    if pj.get("name"):
                        pkg_name = pj["name"]
            except Exception:
                pass
        elif os.path.isfile(os.path.join(pkg_abs, "Cargo.toml")):
            pkg_type = "rust"
            manifest_file = f"{norm_rel}/Cargo.toml"

        workspaces.append(
            WorkspacePackage(
                name=pkg_name,
                path=norm_rel,
                abs_path=pkg_abs,
                package_type=pkg_type,
                manifest_file=manifest_file,
                files=[],
                metadata={"declared_path": norm_rel},
            )
        )

    # Sort workspaces alphabetically by path for determinism
    workspaces.sort(key=lambda w: w.path)
    return workspaces


def map_files_to_workspaces(
    files: Iterable[str], workspaces: List[WorkspacePackage]
) -> Dict[str, Optional[str]]:
    """
    Maps each relative file path in the repository to the workspace package it belongs to.
    Uses longest-prefix matching to support nested workspace packages.
    Returns {file_path: workspace_name_or_None}.
    """
    # Sort workspaces descending by path length so deepest (most specific) package matches first
    sorted_ws = sorted(workspaces, key=lambda w: len(w.path), reverse=True)
    mapping: Dict[str, Optional[str]] = {}

    for f in files:
        norm_f = f.replace("\\", "/").lstrip("./")
        matched_pkg: Optional[str] = None
        for ws in sorted_ws:
            ws_prefix = ws.path + "/"
            if norm_f == ws.path or norm_f.startswith(ws_prefix):
                matched_pkg = ws.name
                if norm_f not in ws.files:
                    ws.files.append(norm_f)
                break
        mapping[norm_f] = matched_pkg

    return mapping


def find_workspace(workspaces: List[WorkspacePackage], query: str) -> Optional[WorkspacePackage]:
    """
    Finds a workspace package matching a query by exact name, normalized path, or basename.
    """
    if not query:
        return None
    clean_q = _sanitize_rel_path(query)

    # 1. Exact name match
    for w in workspaces:
        if w.name == query or w.name == clean_q:
            return w

    # 2. Path match
    for w in workspaces:
        if w.path == clean_q or w.path == query:
            return w

    # 3. Basename match
    for w in workspaces:
        if os.path.basename(w.path) == clean_q:
            return w

    return None


def filter_codebase_to_workspace(
    codebase: Dict[str, Any], workspace: WorkspacePackage
) -> Dict[str, Any]:
    """
    Returns a new codebase dictionary containing only files belonging to the specified workspace package.
    """
    prefix = workspace.path + "/"
    filtered: Dict[str, Any] = {}
    for f, data in codebase.items():
        norm_f = f.replace("\\", "/").lstrip("./")
        if norm_f == workspace.path or norm_f.startswith(prefix):
            filtered[f] = data
    return filtered


def analyze_cross_workspace_dependencies(
    codebase: Dict[str, Any], workspaces: List[WorkspacePackage]
) -> Tuple[List[Dict[str, Any]], List[List[str]]]:
    """
    Extracts cross-workspace dependency edges and detects circular dependency cycles between packages.
    Returns:
    - cross_dependencies: list of dicts {source_workspace, target_workspace, source_file, target_file, imported_name}
    - cross_cycles: list of workspace cycles, e.g. [["pkg-a", "pkg-b", "pkg-a"]]
    """
    if not workspaces:
        return [], []

    # Map files to workspaces
    file_to_ws: Dict[str, str] = {}
    sorted_ws = sorted(workspaces, key=lambda w: len(w.path), reverse=True)

    # Build module prefix to workspace lookup
    mod_to_ws: Dict[str, str] = {}
    for ws in sorted_ws:
        # e.g. packages/core -> packages.core and core
        ws_mod = ws.path.replace("/", ".")
        mod_to_ws[ws_mod] = ws.name
        mod_to_ws[ws.name] = ws.name

    for f in codebase.keys():
        norm_f = f.replace("\\", "/").lstrip("./")
        for ws in sorted_ws:
            if norm_f == ws.path or norm_f.startswith(ws.path + "/"):
                file_to_ws[norm_f] = ws.name
                # Register module path
                mod_name = norm_f[:-3].replace("/", ".") if norm_f.endswith(".py") else norm_f.replace("/", ".")
                mod_to_ws[mod_name] = ws.name
                base_name = os.path.splitext(os.path.basename(norm_f))[0]
                if base_name != "__init__":
                    mod_to_ws[base_name] = ws.name
                break

    cross_deps: List[Dict[str, Any]] = []
    adjacency: Dict[str, Set[str]] = {w.name: set() for w in workspaces}

    for f, analysis in codebase.items():
        norm_f = f.replace("\\", "/").lstrip("./")
        src_ws = file_to_ws.get(norm_f)
        if not src_ws:
            continue

        imports = analysis.get("imports", [])
        for imp in imports:
            # Check if import targets another workspace
            target_ws: Optional[str] = None
            for mod_prefix, ws_name in mod_to_ws.items():
                if imp == mod_prefix or imp.startswith(mod_prefix + "."):
                    if ws_name != src_ws:
                        target_ws = ws_name
                        break

            if target_ws and target_ws != src_ws:
                cross_deps.append({
                    "source_workspace": src_ws,
                    "target_workspace": target_ws,
                    "source_file": norm_f,
                    "imported_symbol": imp,
                })
                adjacency[src_ws].add(target_ws)

    # Detect cycles across workspace packages using DFS
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    current_path: List[str] = []

    def dfs(node: str):
        visited.add(node)
        rec_stack.add(node)
        current_path.append(node)

        for neighbor in sorted(adjacency.get(node, set())):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Cycle found!
                idx = current_path.index(neighbor)
                cycle = current_path[idx:] + [neighbor]
                cycles.append(cycle)

        current_path.pop()
        rec_stack.remove(node)

    for w in sorted(workspaces, key=lambda x: x.name):
        if w.name not in visited:
            dfs(w.name)

    return cross_deps, cycles


def generate_monorepo_report(
    repo_path: str, codebase: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates a structured monorepo overview report for the target repository.
    """
    workspaces = detect_workspaces(repo_path)
    is_monorepo = len(workspaces) > 1

    if codebase is None:
        from ultron.core import analyzer
        codebase = analyzer.analyze_directory(repo_path)

    map_files_to_workspaces(codebase.keys(), workspaces)
    cross_deps, cycles = analyze_cross_workspace_dependencies(codebase, workspaces)

    return {
        "is_monorepo": is_monorepo,
        "repo": os.path.abspath(repo_path).replace("\\", "/"),
        "total_workspaces": len(workspaces),
        "workspaces": [w.to_dict() for w in workspaces],
        "cross_dependencies_count": len(cross_deps),
        "cross_dependencies": cross_deps[:50],  # Bounded for clean envelope
        "cross_workspace_cycles": cycles,
    }
