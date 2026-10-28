"""Structured logging configuration for the MCP server."""

import logging.config
from pathlib import Path

LOGGING_CONF = Path(__file__).resolve().parent / "logging.conf"


def load_logging_config(path: Path = LOGGING_CONF) -> None:
    """Load logging.conf and configure the root logger.

    Modules obtain loggers with ``logging.getLogger(__name__)``; this
    function only applies the shared configuration.
    """
    if not path.is_file():
        raise FileNotFoundError(f"logging.conf not found at: {path}")

    logging.config.fileConfig(path, disable_existing_loggers=False)
