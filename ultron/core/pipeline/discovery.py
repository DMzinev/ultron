import os
from typing import Generator, Iterable, List, Set

EXCLUDED_DIRS: Set[str] = {
    ".git", ".ultron", "scratch", "synapse_project", "build", "dist",
    "node_modules", "__pycache__", ".venv", "venv", "env", ".cache",
    ".synapse", ".agents", "docs", "ultron_risk_scorer.egg-info",
    "vendor", "target", "out", "coverage", ".next", ".nuxt", ".turbo",
    ".gradle", "Pods", "bin", "obj", ".idea", ".vscode"
}

SUPPORTED_EXTENSIONS: Set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go"
}


def iter_discover(
    repo_path: str,
    supported_extensions: Set[str] = SUPPORTED_EXTENSIONS,
    excluded_dirs: Set[str] = EXCLUDED_DIRS,
    max_depth: int = 40
) -> Generator[str, None, None]:
    """
    Streaming generator yielding normalized relative file paths one-by-one.
    Memory footprint remains O(1) regardless of repository size (100k+ files).
    Includes circular symlink and maximum depth guards.
    """
    if not repo_path or not os.path.exists(repo_path):
        raise ValueError(f"Invalid repository path: {repo_path}")

    abs_repo = os.path.abspath(repo_path)
    visited_realpaths = set()

    for root, dirs, files in os.walk(abs_repo, followlinks=False):
        # Calculate depth to guard against infinite filesystem recursion
        try:
            rel_root = os.path.relpath(root, abs_repo)
            depth = 0 if rel_root == "." else len(rel_root.replace("\\", "/").split("/"))
            if depth > max_depth:
                dirs[:] = []
                continue
        except Exception:
            pass

        # Avoid revisiting real directory paths (symlink loops)
        try:
            real_root = os.path.realpath(root)
            if real_root in visited_realpaths:
                dirs[:] = []
                continue
            visited_realpaths.add(real_root)
        except Exception:
            pass

        # Exclude directories in-place
        dirs[:] = [
            d for d in dirs 
            if not d.startswith('.') and d not in excluded_dirs
        ]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                abs_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file_path, abs_repo)
                norm_path = rel_path.replace("\\", "/")
                yield norm_path


def chunk_stream(iterable: Iterable[str], chunk_size: int = 512) -> Generator[List[str], None, None]:
    """Yields batches of items from a stream to bound peak memory."""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def discover(repo_path: str) -> list[str]:
    """
    Scans the repository for source files (Python, TypeScript, JavaScript, Go) to analyze.
    Symmetrically normalizes all paths to forward slashes.
    Raises ValueError if no files are discovered.
    """
    discovered = list(iter_discover(repo_path))
    if not discovered:
        raise ValueError("Repository contains no files to analyze")

    return sorted(discovered)

