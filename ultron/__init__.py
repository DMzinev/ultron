# Ultron package initialization
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
