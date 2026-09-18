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
