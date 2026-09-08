import os

EXCLUDED_DIRS = {
    ".git", ".ultron", "scratch", "synapse_project", "build", "dist",
    "node_modules", "__pycache__", ".venv", "venv", "env", ".cache",
    ".synapse", ".agents", "vendor", "target"
}

SUPPORTED_EXTENSIONS = (".py", ".ts", ".js", ".jsx", ".tsx", ".go")


def iter_discover(repo_path: str):
    """
    Generator yielding normalized relative paths for supported source files.
    """
    if not repo_path or not os.path.exists(repo_path):
        raise ValueError(f"Invalid repository path: {repo_path}")

    abs_repo = os.path.abspath(repo_path)
    for root, dirs, files in os.walk(abs_repo):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                abs_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file_path, abs_repo)
                yield rel_path.replace("\\", "/")


def discover(repo_path: str) -> list[str]:
    """
    Scans the repository for supported files to analyze.
    Symmetrically normalizes all paths to forward slashes.
    Raises ValueError if no files are discovered.
    """
    discovered = sorted(list(iter_discover(repo_path)))
    if not discovered:
        raise ValueError("Repository contains no files to analyze")

    return discovered
