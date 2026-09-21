import sys

if sys.version_info < (3, 10):
    v_major = getattr(sys.version_info, "major", sys.version_info[0])
    v_minor = getattr(sys.version_info, "minor", sys.version_info[1])
    v_micro = getattr(sys.version_info, "micro", sys.version_info[2] if len(sys.version_info) > 2 else 0)
    raise RuntimeError(
        f"Ultron requires Python 3.10 or higher (detected Python {v_major}.{v_minor}.{v_micro})."
    )


from ultron._version import __version__


def get_version() -> str:
    """
    Authoritative version resolver.
    Uses importlib.metadata for installed wheels; falls back to __version__ for dev tree checkouts.
    """
    try:
        from importlib.metadata import version as _meta_version, PackageNotFoundError
        return _meta_version("ultron-risk-scorer")
    except PackageNotFoundError:
        return __version__

import os
import logging

_log_level_name = os.environ.get("ULTRON_LOG_LEVEL", "WARNING").upper()
_log_level = getattr(logging, _log_level_name, logging.WARNING)

logger = logging.getLogger("ultron")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
logger.setLevel(_log_level)
