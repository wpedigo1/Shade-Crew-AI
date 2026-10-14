"""Durable structured logging configuration (Mission 040).

Configures a rotating file handler at ``<user_data_dir>/logs/modelmix.log``
with a console handler that mirrors the pre-M040 stderr behavior.  The log
level is controlled by the ``LLM_COUNCIL_LOG_LEVEL`` environment variable
(default ``INFO``).

No side effects at import time.  Call ``configure_logging()`` once early in
the process, before the FastAPI app is created.  Stdlib only — no new
dependencies.
"""

from __future__ import annotations

import logging
import logging.config
import os

from .user_data_dir import harden_user_dir, resolve_user_data_dir

# Defaults kept small so dev-mode log files don't balloon.
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
_BACKUP_COUNT = 3

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> None:
    """One-shot logging setup.

    * Creates the log directory if absent.
    * Adds a ``RotatingFileHandler`` writing ``modelmix.log``.
    * Keeps the console (stderr) handler so ``python -m backend.main`` still
      prints to the terminal.
    * Respects ``LLM_COUNCIL_LOG_LEVEL`` (case-insensitive level name).
    * On Windows the log directory and file receive ACL hardening identical to
      the credential file so log contents are not world-readable.
    * Safe to call more than once — redundant calls are a no-op.
    """
    if getattr(configure_logging, "_done", False):
        return
    configure_logging._done = True

    level_name = os.getenv("LLM_COUNCIL_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.INFO

    log_dir = resolve_user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "modelmix.log"

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "file": {"format": _FORMAT, "datefmt": "%Y-%m-%d %H:%M:%S"},
            "console": {"format": "%(levelname)s %(name)s: %(message)s"},
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_path),
                "maxBytes": _MAX_BYTES,
                "backupCount": _BACKUP_COUNT,
                "encoding": "utf-8",
                "formatter": "file",
                "level": level,
            },
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "formatter": "console",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": level,
        },
    })

    harden_user_dir(log_path)
