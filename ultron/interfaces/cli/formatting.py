"""
ultron.interfaces.cli.formatting
Pure Python standard-library ANSI terminal formatting, color detection, and dashboard rendering.
Zero external dependencies (no Rich, no Colorama, no Termcolor).
"""

import os
import sys
import re
from typing import Optional, Dict, Any, List


# --- ANSI Escape Constants ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"

# Foreground Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GRAY = "\033[90m"

# Bright Foreground Colors
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Background Colors
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"

# Regular expression to strip ANSI escape codes for column width calculations
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    """Removes ANSI escape codes from string to compute true terminal visual width."""
    if not text:
        return ""
    return _ANSI_RE.sub("", text)


def can_encode_unicode(stream=None) -> bool:
    """Probes whether the target output stream can cleanly encode Unicode box-drawing characters."""
    target = stream if stream is not None else sys.stdout
    encoding = getattr(target, "encoding", None) or "utf-8"
    try:
        "─│┌┐└┘█░".encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def supports_color(stream=None, force_color: Optional[bool] = None) -> bool:
    """
    Detects whether the target stream supports ANSI color codes.
    Follows https://no-color.org and respects TERM=dumb and explicit overrides.
    """
    if force_color is not None:
        return bool(force_color)

    target = stream if stream is not None else sys.stdout

    # 1. NO_COLOR standard (https://no-color.org): any non-empty value disables color
    if os.environ.get("NO_COLOR", "") != "":
        return False

    # 2. TERM=dumb disables color
    if os.environ.get("TERM") == "dumb":
        return False

    # 3. Stream must be an interactive TTY
    if not hasattr(target, "isatty") or not target.isatty():
        return False

    # 4. Windows Virtual Terminal Processing initialization
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                if not (mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING):
                    kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
                return True
        except (AttributeError, OSError, Exception):
            pass
        # Fallback to checking modern Windows terminals
        if any(k in os.environ for k in ("WT_SESSION", "ANSICON", "COLORTERM")):
            return True
        return False

    return True


def colorize(text: str, *styles: str, enabled: bool = True) -> str:
    """Wraps text in ANSI style codes if enabled is True."""
    if not enabled or not styles or not text:
        return text
    prefix = "".join(styles)
    return f"{prefix}{text}{RESET}"


def format_badge(label: str, level: str = "INFO", color: bool = True) -> str:
    """Formats an architectural pill or badge with appropriate severity color."""
    lvl = (level or "INFO").upper()
    badge_text = f"[{label}]"
    if not color:
        return badge_text

    if lvl in ("CRITICAL", "ERROR", "FAIL", "FAILED"):
        return colorize(badge_text, BOLD, RED, enabled=color)
    elif lvl in ("HIGH", "WARN", "WARNING"):
        return colorize(badge_text, BOLD, YELLOW, enabled=color)
    elif lvl in ("MEDIUM",):
        return colorize(badge_text, YELLOW, enabled=color)
    elif lvl in ("LOW", "INFO"):
        return colorize(badge_text, CYAN, enabled=color)
    elif lvl in ("PASS", "PASSED", "SUCCESS", "GOOD", "EXCELLENT"):
        return colorize(badge_text, BOLD, GREEN, enabled=color)
    return colorize(badge_text, BOLD, enabled=color)


def format_score_bar(
    score: float,
    max_score: float = 100.0,
    width: int = 20,
    color: bool = True,
    use_unicode: Optional[bool] = None
) -> str:
    """
    Renders a calibrated health score progress bar with qualitative descriptor.
    Example: [████████████████░░░░] 82.5/100 (Good)
    """
    if use_unicode is None:
        use_unicode = can_encode_unicode()

    safe_score = max(0.0, min(float(score), float(max_score))) if max_score > 0 else 0.0
    ratio = safe_score / max_score if max_score > 0 else 0.0
    filled_len = int(round(ratio * width))
    empty_len = width - filled_len

    fill_char = "█" if use_unicode else "#"
    empty_char = "░" if use_unicode else "."
    bar_str = f"[{fill_char * filled_len}{empty_char * empty_len}]"

    if safe_score >= 90.0:
        descriptor = "Excellent"
        bar_color = GREEN
    elif safe_score >= 80.0:
        descriptor = "Good"
        bar_color = GREEN
    elif safe_score >= 60.0:
        descriptor = "Fair"
        bar_color = YELLOW
    else:
        descriptor = "Needs Attention"
        bar_color = RED

    colored_bar = colorize(bar_str, bar_color, enabled=color)
    colored_score = colorize(f"{score:.1f}/{max_score:.0f}", BOLD, enabled=color)
    colored_desc = colorize(f"({descriptor})", bar_color, enabled=color)
    return f"{colored_bar} {colored_score} {colored_desc}"


def _box_row(content: str, inner_width: int, vt: str) -> str:
    """Pads a line of content with trailing spaces to fit exact inner_width accounting for ANSI escapes."""
    visible_len = len(strip_ansi(content))
    if visible_len > inner_width:
        plain = strip_ansi(content)
        truncated = plain[:max(0, inner_width - 3)] + "..."
        return f"{vt} {truncated} {vt}"
    pad_len = max(0, inner_width - visible_len)
    return f"{vt} {content}{' ' * pad_len} {vt}"


def format_scan_dashboard(
    analysis: Dict[str, Any],
    color: bool = True,
    use_unicode: Optional[bool] = None,
    width: int = 72
) -> str:
    """
    Renders an executive box-drawing terminal dashboard for `ultron scan`.
    Presents repository overview, health progress bar, risk category pills,
    and top architectural hotspots.
    """
    if use_unicode is None:
        use_unicode = can_encode_unicode()

    if use_unicode:
        tl, tr, bl, br = "┌", "┐", "└", "┘"
        hz, vt = "─", "│"
        sep_l, sep_r = "├", "┤"
        tree_prefix = "└─"
        ok_icon = "✔"
    else:
        tl, tr, bl, br = "+", "+", "+", "+"
        hz, vt = "-", "|"
        sep_l, sep_r = "+", "+"
        tree_prefix = "\\-"
        ok_icon = "[OK]"

    inner_width = max(40, width - 4)
    sep_line = f"{sep_l}{hz * (inner_width + 2)}{sep_r}"
    top_line = f"{tl}{hz * (inner_width + 2)}{tr}"
    bot_line = f"{bl}{hz * (inner_width + 2)}{br}"

    repo_name = analysis.get("repo", ".")
    total_files = analysis.get("total_files", 0)
    health_score = float(analysis.get("health_score", 100.0))
    risks = analysis.get("risks", [])
    violations = analysis.get("policy_violations", [])

    crit_count = sum(1 for r in risks if r.get("level") == "CRITICAL")
    high_count = sum(1 for r in risks if r.get("level") == "HIGH")
    med_count = sum(1 for r in risks if r.get("level") == "MEDIUM")
    low_count = sum(1 for r in risks if r.get("level") == "LOW")

    lines: List[str] = [top_line]

    # Title header
    header_title = colorize("ULTRON ARCHITECTURAL INTELLIGENCE SCAN", BOLD, enabled=color)
    header_raw = "ULTRON ARCHITECTURAL INTELLIGENCE SCAN"
    header_pad = max(0, (inner_width - len(header_raw)) // 2)
    lines.append(_box_row(" " * header_pad + header_title, inner_width, vt))
    lines.append(sep_line)

    # Repository & Health Section
    lines.append(_box_row(f"{colorize('Repository:', BOLD, enabled=color)}   {repo_name}", inner_width, vt))
    lines.append(_box_row(f"{colorize('Total Files:', BOLD, enabled=color)}  {total_files}", inner_width, vt))

    score_bar = format_score_bar(health_score, width=20, color=color, use_unicode=use_unicode)
    lines.append(_box_row(f"{colorize('Health Score:', BOLD, enabled=color)} {score_bar}", inner_width, vt))
    lines.append(sep_line)

    # Risk Distribution Summary
    crit_badge = colorize(f"CRITICAL: {crit_count}", BOLD, RED if crit_count > 0 else GRAY, enabled=color)
    high_badge = colorize(f"HIGH: {high_count}", BOLD, YELLOW if high_count > 0 else GRAY, enabled=color)
    med_badge = colorize(f"MEDIUM: {med_count}", YELLOW if med_count > 0 else GRAY, enabled=color)
    low_badge = colorize(f"LOW: {low_count}", CYAN if low_count > 0 else GRAY, enabled=color)
    risk_summary_line = f"{crit_badge}  |  {high_badge}  |  {med_badge}  |  {low_badge}"
    
    lines.append(_box_row(colorize("RISK PROFILE & GOVERNANCE SUMMARY", BOLD, enabled=color), inner_width, vt))
    lines.append(_box_row(f"  {risk_summary_line}", inner_width, vt))

    v_count = len(violations)
    v_color = RED if v_count > 0 else GREEN
    v_text = colorize(f"Policy Violations: {v_count}", v_color, BOLD, enabled=color)
    lines.append(_box_row(f"  {v_text}", inner_width, vt))
    lines.append(sep_line)

    # Architectural Hotspots
    lines.append(_box_row(colorize("TOP ARCHITECTURAL HOTSPOTS", BOLD, enabled=color), inner_width, vt))
    sorted_risks = sorted(
        risks,
        key=lambda r: (
            0 if r.get("level") == "CRITICAL" else (1 if r.get("level") == "HIGH" else (2 if r.get("level") == "MEDIUM" else 3)),
            -float(r.get("complexity") or 1)
        )
    )

    hotspots = [r for r in sorted_risks if r.get("level") in ("CRITICAL", "HIGH", "MEDIUM")][:4]
    if hotspots:
        for idx, r in enumerate(hotspots, 1):
            fpath = r.get("file_path") or r.get("file") or "unknown"
            lvl = r.get("level", "LOW")
            badge = format_badge(lvl, lvl, color=color)
            comp = r.get("complexity") if r.get("complexity") is not None else 1
            f_display = f"{idx}. {badge} {fpath} (complexity: {comp})"
            lines.append(_box_row(f_display, inner_width, vt))
            mitigation = r.get("mitigation")
            if mitigation:
                clean_mit = str(mitigation).split(".")[0].strip()
                mit_line = f"     {tree_prefix} {clean_mit}"
                lines.append(_box_row(colorize(mit_line, DIM, enabled=color), inner_width, vt))
    else:
        clean_msg = colorize(f"{ok_icon} No high or medium risk hotspots detected. Architecture is healthy.", GREEN, enabled=color)
        lines.append(_box_row(f"  {clean_msg}", inner_width, vt))

    lines.append(sep_line)
    footer_hint = colorize("Hint: Run 'ultron gate' for CI checks or 'ultron dashboard' for UI.", DIM, enabled=color)
    lines.append(_box_row(footer_hint, inner_width, vt))
    lines.append(bot_line)

    return "\n".join(lines)


def format_gate_summary(
    gate_decision: Dict[str, Any],
    current_analysis: Dict[str, Any],
    color: bool = True,
    use_unicode: Optional[bool] = None,
    width: int = 72
) -> str:
    """
    Renders an executive box-drawing quality gate summary for `ultron gate`.
    """
    if use_unicode is None:
        use_unicode = can_encode_unicode()

    if use_unicode:
        tl, tr, bl, br = "┌", "┐", "└", "┘"
        hz, vt = "─", "│"
        sep_l, sep_r = "├", "┤"
        ok_icon = "✔"
        fail_icon = "❌"
    else:
        tl, tr, bl, br = "+", "+", "+", "+"
        hz, vt = "-", "|"
        sep_l, sep_r = "+", "+"
        ok_icon = "[OK]"
        fail_icon = "[FAIL]"

    inner_width = max(40, width - 4)
    sep_line = f"{sep_l}{hz * (inner_width + 2)}{sep_r}"
    top_line = f"{tl}{hz * (inner_width + 2)}{tr}"
    bot_line = f"{bl}{hz * (inner_width + 2)}{br}"

    passed = bool(gate_decision.get("passed", False))
    curr_health = float(gate_decision.get("current_health", current_analysis.get("health_score", 100.0)))
    base_health = gate_decision.get("baseline_health")
    delta = float(gate_decision.get("health_delta", 0.0))
    reasons = gate_decision.get("reasons", [])
    high_count = gate_decision.get("high_risk_count", 0)
    high_vios = gate_decision.get("high_violations_count", 0)

    status_badge = format_badge("PASSED" if passed else "FAILED", "PASS" if passed else "FAIL", color=color)
    title_text = f"ULTRON ARCHITECTURAL QUALITY GATE  {status_badge}"

    lines: List[str] = [top_line]
    lines.append(_box_row(title_text, inner_width, vt))
    lines.append(sep_line)

    # Health & Delta
    delta_str = f"{delta:+.1f} pts"
    if delta < 0:
        delta_colored = colorize(delta_str, BOLD, RED, enabled=color)
    elif delta > 0:
        delta_colored = colorize(delta_str, BOLD, GREEN, enabled=color)
    else:
        delta_colored = colorize(delta_str, GRAY, enabled=color)

    base_str = f"{base_health:.1f}/100" if isinstance(base_health, (int, float)) else "None (Standalone)"
    lines.append(_box_row(f"Current Health:   {curr_health:.1f}/100", inner_width, vt))
    lines.append(_box_row(f"Baseline Health:  {base_str}", inner_width, vt))
    lines.append(_box_row(f"Health Delta:     {delta_colored}", inner_width, vt))
    lines.append(_box_row(f"HIGH Risk Files:  {high_count} | High Violations: {high_vios}", inner_width, vt))

    if not passed and reasons:
        lines.append(sep_line)
        lines.append(_box_row(colorize("THRESHOLD BREACHES & REGRESSIONS:", BOLD, RED, enabled=color), inner_width, vt))
        for r in reasons:
            clean_reason = f"  {fail_icon} {r}"
            lines.append(_box_row(colorize(clean_reason, RED, enabled=color), inner_width, vt))
    elif passed:
        lines.append(sep_line)
        ok_msg = colorize(f"  {ok_icon} All thresholds satisfied. Zero unpermitted regressions.", GREEN, enabled=color)
        lines.append(_box_row(ok_msg, inner_width, vt))

    lines.append(bot_line)
    return "\n".join(lines)


def safe_print(text: str, file=None) -> None:
    """
    Prints text safely to stream, defending against Windows encoding charmap crashes.
    Attempts standard print() first so unittest mocks (like patch('builtins.print')) succeed.
    Resolves target stream dynamically to support sys.stdout / sys.stderr patching in tests.
    """
    target = file if file is not None else sys.stdout
    try:
        print(text, file=target)
        return
    except UnicodeEncodeError:
        pass

    try:
        if hasattr(target, "buffer"):
            target.buffer.write((text + "\n").encode("utf-8", errors="replace"))
            target.flush()
            return
    except Exception:
        pass

    print(text.encode("ascii", errors="replace").decode("ascii"), file=target)
