"""
ultron.interfaces.cli.commands.hook
Git pre-commit and pre-push quality gate hook installer and lifecycle manager.
Enforces architectural boundaries, zero high risks, and non-regression gating
before commits or pushes enter the repository.
"""

from datetime import datetime
import json
import os
import shutil
import sys


ULTRON_HOOK_SIGNATURE = "# --- ULTRON MANAGED HOOK ---"
SUPPORTED_HOOK_TYPES = ("pre-commit", "pre-push")


def _find_hooks_dir(repo_path: str) -> str:
    """Discovers the active Git hooks directory, supporting standard repositories,

    worktrees with commondir pointers, and submodules.
    """
    abs_repo = os.path.abspath(repo_path)
    git_path = os.path.join(abs_repo, ".git")

    if not os.path.exists(git_path):
        raise ValueError(f"Target directory is not a Git repository (missing .git): {abs_repo}")

    if os.path.isdir(git_path):
        hooks_dir = os.path.join(git_path, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        return os.path.normpath(hooks_dir)

    if os.path.isfile(git_path):
        # Worktree or submodule pointer file: gitdir: <path>
        with open(git_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content.startswith("gitdir:"):
            raise ValueError(f"Invalid .git pointer file format in {abs_repo}: {content}")
        raw_gitdir = content[len("gitdir:"):].strip()
        if not os.path.isabs(raw_gitdir):
            gitdir = os.path.normpath(os.path.join(abs_repo, raw_gitdir))
        else:
            gitdir = os.path.normpath(raw_gitdir)

        # In Git worktrees, commondir points to the main repository .git directory
        commondir_file = os.path.join(gitdir, "commondir")
        if os.path.exists(commondir_file):
            with open(commondir_file, "r", encoding="utf-8") as f:
                raw_commondir = f.read().strip()
            if not os.path.isabs(raw_commondir):
                common_git_dir = os.path.normpath(os.path.join(gitdir, raw_commondir))
            else:
                common_git_dir = os.path.normpath(raw_commondir)
            hooks_dir = os.path.join(common_git_dir, "hooks")
        else:
            hooks_dir = os.path.join(gitdir, "hooks")

        os.makedirs(hooks_dir, exist_ok=True)
        return os.path.normpath(hooks_dir)

    raise ValueError(f"Target .git path is neither file nor directory: {git_path}")


def _is_ultron_hook(hook_path: str) -> bool:
    """Returns True if the hook file exists and contains the Ultron signature marker."""
    if not os.path.exists(hook_path):
        return False
    try:
        with open(hook_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            return ULTRON_HOOK_SIGNATURE in content
    except OSError:
        return False


def _generate_hook_script(
    hook_type: str,
    strict: bool = True,
    fail_on_high: bool = True,
    fail_on_regression: bool = True,
    base: str = "HEAD",
) -> str:
    """Synthesizes a universal POSIX/Git Bash shell script for the quality gate hook."""
    python_exec = sys.executable.replace("\\", "/")

    flags = []
    if base:
        flags.append(f"--base {base}")
    if strict:
        flags.append("--strict")
    if fail_on_high:
        flags.append("--fail-on-high")
    if fail_on_regression:
        flags.append("--fail-on-regression")

    flags_str = " ".join(flags)

    return f"""#!/usr/bin/env sh
{ULTRON_HOOK_SIGNATURE}
# Hook type: {hook_type}
# Installed by: ultron hook install

# Resolve repository root
if command -v git >/dev/null 2>&1; then
    GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
else
    GIT_ROOT=$(pwd)
fi

# 4-Tier Python Resolver
# 1. Active virtualenv
# 2. Local repository .venv or venv
# 3. Installer Python recorded at install time
# 4. System python3 / python
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/Scripts/python.exe" ]; then
    PYTHON="$VIRTUAL_ENV/Scripts/python.exe"
elif [ -x "$GIT_ROOT/.venv/bin/python" ]; then
    PYTHON="$GIT_ROOT/.venv/bin/python"
elif [ -x "$GIT_ROOT/.venv/Scripts/python.exe" ]; then
    PYTHON="$GIT_ROOT/.venv/Scripts/python.exe"
elif [ -x "$GIT_ROOT/venv/bin/python" ]; then
    PYTHON="$GIT_ROOT/venv/bin/python"
elif [ -x "$GIT_ROOT/venv/Scripts/python.exe" ]; then
    PYTHON="$GIT_ROOT/venv/Scripts/python.exe"
elif [ -x "{python_exec}" ]; then
    PYTHON="{python_exec}"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "[Ultron] Executing {hook_type} architectural quality gate..."
"$PYTHON" -m ultron gate --repo "$GIT_ROOT" {flags_str}
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[Ultron] Commit rejected: Architectural quality gate failed (exit code $EXIT_CODE)." >&2
    echo "[Ultron] Run 'python -m ultron gate' or start dashboard with 'python -m ultron dashboard' to inspect." >&2
    exit $EXIT_CODE
fi

exit 0
"""


def install_hooks(
    repo_path: str,
    hook_types: list[str] = None,
    strict: bool = True,
    fail_on_high: bool = True,
    fail_on_regression: bool = True,
    base: str = "HEAD",
    force: bool = False,
    output_json: bool = False,
) -> int:
    """Installs pre-commit and/or pre-push hooks into the target repository."""
    try:
        hooks_dir = _find_hooks_dir(repo_path)
    except ValueError as err:
        if output_json:
            print(json.dumps({"success": False, "error": str(err)}, indent=2))
        else:
            print(f"[!] Error: {err}", file=sys.stderr)
        return 1

    targets = SUPPORTED_HOOK_TYPES if (not hook_types or "all" in hook_types) else [h for h in hook_types if h in SUPPORTED_HOOK_TYPES]
    results = {}

    for ht in targets:
        hook_path = os.path.join(hooks_dir, ht)
        backup_created = None

        if os.path.exists(hook_path):
            if not _is_ultron_hook(hook_path):
                # Foreign third-party hook: back up unless force overwrite requested without backup
                if not force:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    backup_path = f"{hook_path}.bak.{ts}"
                    try:
                        shutil.copy2(hook_path, backup_path)
                        backup_created = backup_path
                        if not output_json:
                            print(f"[Ultron] Existing foreign {ht} hook backed up to: {backup_path}", file=sys.stderr)
                    except OSError as e:
                        if not output_json:
                            print(f"[!] Warning: Failed to backup existing hook at {hook_path}: {e}", file=sys.stderr)

        script_content = _generate_hook_script(
            hook_type=ht,
            strict=strict,
            fail_on_high=fail_on_high,
            fail_on_regression=fail_on_regression,
            base=base,
        )

        # Enforce LF line endings explicitly for cross-platform Git Bash compatibility
        with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(script_content)

        # Set executable permissions on POSIX systems
        try:
            curr_mode = os.stat(hook_path).st_mode
            os.chmod(hook_path, curr_mode | 0o755)
        except OSError:
            pass

        results[ht] = {
            "path": hook_path,
            "status": "installed",
            "backup": backup_created,
        }

        if not output_json:
            print(f"[Ultron] Successfully installed Git {ht} quality gate hook: {hook_path}")

    if output_json:
        print(json.dumps({"success": True, "hooks": results}, indent=2))

    return 0


def uninstall_hooks(
    repo_path: str,
    hook_types: list[str] = None,
    output_json: bool = False,
) -> int:
    """Uninstalls Ultron hooks and restores the latest foreign backup if available."""
    try:
        hooks_dir = _find_hooks_dir(repo_path)
    except ValueError as err:
        if output_json:
            print(json.dumps({"success": False, "error": str(err)}, indent=2))
        else:
            print(f"[!] Error: {err}", file=sys.stderr)
        return 1

    targets = SUPPORTED_HOOK_TYPES if (not hook_types or "all" in hook_types) else [h for h in hook_types if h in SUPPORTED_HOOK_TYPES]
    results = {}
    had_error = False

    for ht in targets:
        hook_path = os.path.join(hooks_dir, ht)

        if not os.path.exists(hook_path):
            results[ht] = {"status": "missing", "path": hook_path}
            if not output_json:
                print(f"[Ultron] Hook {ht} is not installed.")
            continue

        if not _is_ultron_hook(hook_path):
            had_error = True
            results[ht] = {"status": "refused_foreign", "path": hook_path}
            if not output_json:
                print(f"[!] Refusing to remove non-Ultron hook: {hook_path}", file=sys.stderr)
            continue

        os.remove(hook_path)
        restored = None

        # Look for backups: <ht>.bak.<timestamp>
        try:
            baks = sorted([f for f in os.listdir(hooks_dir) if f.startswith(f"{ht}.bak.")])
            if baks:
                latest_bak = os.path.join(hooks_dir, baks[-1])
                shutil.move(latest_bak, hook_path)
                restored = latest_bak
                if not output_json:
                    print(f"[Ultron] Restored previous foreign hook from: {latest_bak}")
        except OSError:
            pass

        results[ht] = {
            "status": "uninstalled",
            "path": hook_path,
            "restored_backup": restored,
        }

        if not output_json:
            print(f"[Ultron] Successfully removed {ht} hook.")

    if output_json:
        print(json.dumps({"success": not had_error, "hooks": results}, indent=2))

    return 1 if had_error else 0


def get_hook_status(repo_path: str, output_json: bool = False) -> dict:
    """Returns the installation status of all supported Git hooks."""
    try:
        hooks_dir = _find_hooks_dir(repo_path)
    except ValueError as err:
        if output_json:
            print(json.dumps({"success": False, "error": str(err)}, indent=2))
        else:
            print(f"[!] Error: {err}", file=sys.stderr)
        return {"success": False, "error": str(err)}

    status_map = {}
    for ht in SUPPORTED_HOOK_TYPES:
        hook_path = os.path.join(hooks_dir, ht)
        if not os.path.exists(hook_path):
            status = "missing"
        elif _is_ultron_hook(hook_path):
            status = "installed"
        else:
            status = "foreign"

        status_map[ht] = {
            "status": status,
            "path": hook_path,
        }

    payload = {"success": True, "hooks": status_map}
    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"=== Ultron Git Hook Status ({repo_path}) ===")
        for ht, info in status_map.items():
            print(f"  * {ht:<12}: {info['status'].upper()} ({info['path']})")

    return payload


def run_hook_command(args) -> int:
    """CLI runner for 'ultron hook' subcommands."""
    repo_path = getattr(args, "repo", None) or os.getcwd()
    action = getattr(args, "action", "status") or "status"
    output_json = getattr(args, "json", False)

    if action == "status":
        res = get_hook_status(repo_path, output_json=output_json)
        return 0 if res.get("success", False) else 1

    hook_type = getattr(args, "hook_type", "all") or "all"
    hook_types = SUPPORTED_HOOK_TYPES if hook_type == "all" else [hook_type]

    if action == "install":
        strict = getattr(args, "strict", True)
        fail_on_high = getattr(args, "fail_on_high", True)
        fail_on_regression = getattr(args, "fail_on_regression", True)
        base = getattr(args, "base", "HEAD") or "HEAD"
        force = getattr(args, "force", False)

        return install_hooks(
            repo_path=repo_path,
            hook_types=hook_types,
            strict=strict,
            fail_on_high=fail_on_high,
            fail_on_regression=fail_on_regression,
            base=base,
            force=force,
            output_json=output_json,
        )

    if action == "uninstall":
        return uninstall_hooks(
            repo_path=repo_path,
            hook_types=hook_types,
            output_json=output_json,
        )

    if not output_json:
        print(f"[!] Unknown hook action: {action}", file=sys.stderr)
    return 1
