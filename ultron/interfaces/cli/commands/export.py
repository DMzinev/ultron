"""
ultron.interfaces.cli.commands.export
Executive Architecture Report & Briefing Export CLI Handler.
"""

import os
import sys
import json
from typing import Optional

from ultron.core import context_brief


def run_export_command(
    repo_path: str = ".",
    fmt: str = "markdown",
    output_path: Optional[str] = None,
) -> int:
    """
    Executes the 'ultron export' command.
    Exports the executive architecture brief in markdown, json, html, or text format.
    Writes to stdout or to an output file if specified.
    Returns 0 on SUCCESS, 1 on FAILURE.
    """
    abs_repo = os.path.abspath(os.path.normpath(repo_path))
    if not os.path.isdir(abs_repo):
        sys.stderr.write(f"[-] Error: Repository directory '{abs_repo}' not found.\n")
        return 1

    clean_fmt = str(fmt).strip().lower()
    allowed_formats = ["markdown", "json", "html", "text"]
    if clean_fmt not in allowed_formats:
        sys.stderr.write(
            f"[-] Error: Unsupported format '{clean_fmt}'. Allowed: {', '.join(allowed_formats)}.\n"
        )
        return 1

    try:
        repo_name = os.path.basename(abs_repo)
        if clean_fmt == "json":
            brief_data = context_brief.compile_brief_data(abs_repo)
            payload = {
                "status": "ok",
                "schema_version": "1.0.0",
                "format": "json",
                "repo": abs_repo,
                "brief": brief_data
            }
            content = json.dumps(payload, indent=2)
        elif clean_fmt in ["markdown", "text"]:
            content = context_brief.compile_brief(abs_repo)
        elif clean_fmt == "html":
            brief_md = context_brief.compile_brief(abs_repo)
            content = (
                f"<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
                f"<title>Ultron Architecture Report — {repo_name}</title>\n"
                f"<style>body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; "
                f"background: #0d1117; color: #c9d1d9; padding: 2rem; line-height: 1.6; max-width: 900px; margin: 0 auto; }} "
                f"pre {{ background: #161b22; padding: 1.25rem; border-radius: 8px; overflow-x: auto; border: 1px solid #30363d; }} "
                f"h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }}</style>\n"
                f"</head>\n<body>\n<h1>Ultron Architecture Report — {repo_name}</h1>\n"
                f"<pre>{brief_md}</pre>\n</body>\n</html>"
            )

        if output_path:
            abs_out = os.path.abspath(output_path)
            out_dir = os.path.dirname(abs_out)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(abs_out, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[+] Ultron architecture report exported to: {abs_out}")
        else:
            print(content)

        return 0
    except Exception as e:
        sys.stderr.write(f"[-] Error generating export report: {e}\n")
        return 1
