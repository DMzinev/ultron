"""
ultron.interfaces.cli.commands.watch
Continuous Architecture Watch Mode Daemon with Live Differential Blast Radius Notices.
"""

import datetime
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ultron.core import analyzer
from ultron.core.blast_radius import BlastRadiusTracer, norm_id
from ultron.interfaces.cli.commands.gate import extract_current_analysis
from ultron.interfaces.cli.formatting import (
    CYAN,
    GREEN,
    RED,
    YELLOW,
    colorize,
    format_badge,
    safe_print,
    supports_color,
)

DEFAULT_PRUNE_DIRS: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "env",
    "test_env",
    "__pycache__",
    ".ultron",
    "node_modules",
    "scratch",
    "build",
    "dist",
    ".egg-info",
    "ultron_risk_scorer.egg-info",
    ".pytest_cache",
    ".coverage",
}


def scan_mtimes(
    repo_path: str,
    extensions: Tuple[str, ...] = (".py",)
) -> Dict[str, Tuple[float, int]]:
    """
    Scans repo_path and returns mapping of normalized relative paths to (mtime, size) tuples.
    Normalizes all paths to POSIX forward slashes and defensively ignores file lock/access errors.
    """
    snapshot: Dict[str, Tuple[float, int]] = {}
    abs_repo = os.path.abspath(os.path.normpath(repo_path))

    for root, dirs, files in os.walk(abs_repo):
        # Prune excluded directories in-place
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in DEFAULT_PRUNE_DIRS
        ]

        for f in files:
            if not any(f.endswith(ext) for ext in extensions):
                continue
            abs_path = os.path.join(root, f)
            try:
                st = os.stat(abs_path)
                rel_path = os.path.relpath(abs_path, abs_repo).replace("\\", "/")
                snapshot[rel_path] = (st.st_mtime, st.st_size)
            except (OSError, FileNotFoundError, PermissionError):
                continue

    return snapshot


def detect_changes(
    old_snapshot: Dict[str, Tuple[float, int]],
    new_snapshot: Dict[str, Tuple[float, int]],
    mtime_threshold: float = 1e-4
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compares two filesystem snapshots and detects modified, added, and deleted files.
    Returns (sorted(modified), sorted(added), sorted(deleted)).
    """
    modified: List[str] = []
    added: List[str] = []
    deleted: List[str] = []

    for path, (new_mtime, new_size) in new_snapshot.items():
        if path not in old_snapshot:
            added.append(path)
        else:
            old_mtime, old_size = old_snapshot[path]
            if (new_mtime > old_mtime + mtime_threshold) or (new_size != old_size):
                modified.append(path)

    for path in old_snapshot:
        if path not in new_snapshot:
            deleted.append(path)

    return sorted(modified), sorted(added), sorted(deleted)


def compute_file_blast_radius(
    repo_path: str,
    target_file: str,
    max_depth: int = 5,
    cached_edges: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Computes upstream blast radius count (direct and transitive dependents)
    for target_file using BlastRadiusTracer.
    """
    normalized_target = norm_id(target_file)
    edges = cached_edges
    if edges is None:
        try:
            codebase = analyzer.analyze_directory(repo_path)
            graph = analyzer.build_dependency_graph(codebase, granularity="file")
            edges = graph.get("links", [])
        except Exception:
            edges = []

    try:
        res = BlastRadiusTracer.find_upstream_dependencies(
            nodes=[],
            edges=edges,
            target_id=normalized_target,
            max_depth=max_depth
        )
        return int(res.get("total_upstream_count", 0))
    except Exception:
        return 0


def format_watch_event(event: Dict[str, Any], color: bool = True) -> str:
    """
    Renders a concise, 1-line real-time terminal notice for an architectural change event.
    """
    timestamp = event.get("timestamp", "")
    change_type = event.get("change_type", "MODIFIED")
    file_path = event.get("file", "")
    level = event.get("level", "LOW")
    blast_radius = event.get("blast_radius", 0)
    health_after = event.get("health_after", 100.0)
    delta = event.get("delta", 0.0)

    # Color tokens
    time_str = colorize(f"[{timestamp}]", CYAN, enabled=color)

    if change_type == "MODIFIED":
        change_str = colorize("MODIFIED", YELLOW, enabled=color)
    elif change_type == "ADDED":
        change_str = colorize("ADDED   ", GREEN, enabled=color)
    elif change_type == "DELETED":
        change_str = colorize("DELETED ", RED, enabled=color)
    else:
        change_str = colorize(change_type.ljust(8), CYAN, enabled=color)

    badge = format_badge(level, color=color)

    # Health delta styling
    delta_sign = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
    if delta > 0:
        delta_str = colorize(f"({delta_sign})", GREEN, enabled=color)
    elif delta < 0:
        delta_str = colorize(f"({delta_sign})", RED, enabled=color)
    else:
        delta_str = colorize(f"({delta_sign})", CYAN, enabled=color)

    blast_unit = "file" if blast_radius == 1 else "files"
    blast_str = f"blast radius: {blast_radius} {blast_unit}"
    health_str = f"health: {health_after:.1f} {delta_str}"

    return f"{time_str} {change_str} {file_path} {badge} | {blast_str} | {health_str}"


def run_watch_command(
    repo_path: str = ".",
    interval: float = 1.0,
    debounce: float = 0.5,
    once: bool = False,
    max_ticks: Optional[int] = None,
    json_output: bool = False,
    no_color: bool = False,
    force_color: Optional[bool] = None,
    strict: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> int:
    """
    Executes continuous architecture watch daemon over target repository.
    Monitors source files, computes differential blast radius upon change,
    and emits live terminal notifications or JSON events.
    Returns 0 on clean exit, 1 on strict breach or initialization failure.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    if not os.path.isdir(abs_repo):
        if json_output:
            safe_print(json.dumps({"status": "error", "error": f"Directory not found: {abs_repo}"}))
        else:
            safe_print(f"[-] Directory not found: {abs_repo}", file=sys.stderr)
        return 1

    # Color determination
    resolved_force = False if no_color else force_color
    color_enabled = supports_color(sys.stdout, force_color=resolved_force)

    try:
        snapshot = scan_mtimes(abs_repo)
        initial_analysis = extract_current_analysis(abs_repo)
        current_health = float(initial_analysis.get("health_score", 100.0))
    except Exception as init_err:
        if json_output:
            safe_print(json.dumps({"status": "error", "error": f"Initial analysis failed: {init_err}"}))
        else:
            safe_print(f"[-] Initial analysis failed: {init_err}", file=sys.stderr)
        return 1

    if not json_output:
        safe_print(
            f"[*] Ultron Architecture Watcher active on '{abs_repo}' "
            f"({len(snapshot)} files, initial health: {current_health:.1f}/100, interval: {interval}s). "
            f"Press Ctrl+C to stop."
        )

    tick_count = 0

    try:
        while max_ticks is None or tick_count < max_ticks:
            tick_count += 1
            if not once:
                sleep_fn(interval)

            try:
                new_snapshot = scan_mtimes(abs_repo)
                modified, added, deleted = detect_changes(snapshot, new_snapshot)

                if modified or added or deleted:
                    # Debounce period to wait for editor write completion
                    if debounce > 0:
                        sleep_fn(debounce)
                        new_snapshot = scan_mtimes(abs_repo)
                        modified, added, deleted = detect_changes(snapshot, new_snapshot)

                    if modified or added or deleted:
                        # Extract updated analysis once for the batch
                        new_analysis = extract_current_analysis(abs_repo)
                        new_health = float(new_analysis.get("health_score", 100.0))
                        delta = round(new_health - current_health, 1)

                        # Extract dependency graph edges once for blast radius traversal
                        try:
                            codebase = analyzer.analyze_directory(abs_repo)
                            graph = analyzer.build_dependency_graph(codebase, granularity="file")
                            cached_edges = graph.get("links", [])
                        except Exception:
                            cached_edges = []

                        # Map risk levels
                        risk_map: Dict[str, str] = {}
                        for r in new_analysis.get("risks", []):
                            rp = norm_id(r.get("file_path") or r.get("file") or "")
                            if rp:
                                risk_map[rp] = r.get("level", "LOW")

                        now_str = datetime.datetime.now().strftime("%H:%M:%S")

                        # Group all changed files
                        all_changes: List[Tuple[str, str]] = (
                            [(f, "MODIFIED") for f in modified] +
                            [(f, "ADDED") for f in added] +
                            [(f, "DELETED") for f in deleted]
                        )

                        strict_failure = False

                        for file_path, change_type in all_changes:
                            norm_path = norm_id(file_path)
                            level = risk_map.get(norm_path, "LOW")
                            blast_radius = compute_file_blast_radius(
                                abs_repo, norm_path, cached_edges=cached_edges
                            )

                            event = {
                                "timestamp": now_str,
                                "change_type": change_type,
                                "file": norm_path,
                                "level": level,
                                "blast_radius": blast_radius,
                                "health_before": current_health,
                                "health_after": new_health,
                                "delta": delta,
                            }

                            if callback:
                                try:
                                    callback(event)
                                except Exception:
                                    pass

                            if json_output:
                                safe_print(json.dumps(event))
                            else:
                                safe_print(format_watch_event(event, color=color_enabled))

                            if strict and (delta < 0 or level in ("CRITICAL", "HIGH")):
                                strict_failure = True

                        # Update state
                        snapshot = new_snapshot
                        current_health = new_health

                        if strict_failure:
                            if not json_output:
                                safe_print(
                                    "[-] Strict watch gating failed: architecture degraded or high-risk introduced.",
                                    file=sys.stderr
                                )
                            return 1

            except Exception as tick_err:
                if not json_output:
                    safe_print(
                        f"[Ultron Watch Warning] Transient error during watch tick: {tick_err}",
                        file=sys.stderr
                    )

            if once:
                break

        return 0

    except KeyboardInterrupt:
        if not json_output:
            safe_print("\n[*] Ultron Architecture Watcher stopped.")
        return 0
