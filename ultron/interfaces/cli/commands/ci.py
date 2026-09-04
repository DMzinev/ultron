"""
ultron.interfaces.cli.commands.ci
Backwards-compatible CI runner delegating to unified gate engine.
"""

from typing import Optional
from ultron.interfaces.cli.commands.gate import run_gate_command


def run_ci_command(
    repo_path: str = ".",
    baseline_path: Optional[str] = None,
    output_comment_path: Optional[str] = None,
    fail_on_regression: bool = False,
    max_health_drop: float = 5.0
) -> int:
    """
    Backwards-compatible CI command entrypoint delegating to run_gate_command.
    """
    return run_gate_command(
        repo_path=repo_path,
        baseline=baseline_path,
        output_comment=output_comment_path,
        fail_on_regression=fail_on_regression,
        max_health_drop=max_health_drop,
        fail_on_high=True
    )

