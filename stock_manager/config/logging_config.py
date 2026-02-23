"""Central logging configuration for stock-manager.

Reads LOG_LEVEL and LOG_DIR from the project .env file via pydantic-settings,
then configures the Python root logger with:
  - Console handler (all levels, formatted)
  - File handler  → logs/service.log  (all levels, daily rotation, 30-day retention)
  - Error handler → logs/error.log    (ERROR+ only, daily rotation, 30-day retention)

Call ``setup_logging()`` once at application start-up (CLI entry point).
Subsequent calls are no-ops (idempotent guard via root logger handler check).

Third-party logger noise suppression: urllib3, httpcore, httpx → WARNING.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from stock_manager.config.paths import default_env_file, project_root_cached

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_THIRD_PARTY_QUIET = ("urllib3", "httpcore", "httpx")

_SENTINEL_ATTR = "_stock_manager_configured"


class LogConfig(BaseSettings):
    """Logging configuration loaded from environment variables.

    Environment Variables:
        LOG_LEVEL: Root logging level (default: INFO).
        LOG_DIR:   Directory for log files relative to project root (default: logs).

    Example .env entries::

        LOG_LEVEL=INFO
        LOG_DIR=logs
    """

    _DEFAULT_ENV_FILE = str(default_env_file())
    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"
    log_dir: str = "logs"


def setup_logging(config: LogConfig | None = None) -> None:
    """Configure the Python root logger with console + file + error handlers.

    This function is **idempotent**: calling it more than once is safe — the
    second and subsequent calls return immediately without adding duplicate
    handlers.

    Args:
        config: Optional :class:`LogConfig` instance.  If *None*, a default
            instance is created and settings are loaded from the project
            ``.env`` file automatically.
    """
    root = logging.getLogger()

    # Idempotency guard: skip if already configured by us
    if getattr(root, _SENTINEL_ATTR, False):
        return

    if config is None:
        config = LogConfig()

    # Resolve log directory (relative to project root when possible)
    project_root = project_root_cached() or Path.cwd()
    log_dir = (project_root / config.log_dir).resolve()

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback: console-only logging when log directory cannot be created
        _configure_console_only(root, config.log_level)
        return

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)

    # 1. Console handler — all levels
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # 2. File handler — all levels, daily rotation, 30-day retention
    service_log_path = log_dir / "service.log"
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=service_log_path,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # 3. Error file handler — ERROR+ only, daily rotation, 30-day retention
    error_log_path = log_dir / "error.log"
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=error_log_path,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    # Apply to root logger
    root.setLevel(_resolve_level(config.log_level))
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.addHandler(error_handler)

    # Mark as configured
    setattr(root, _SENTINEL_ATTR, True)

    # Suppress noisy third-party loggers
    for name in _THIRD_PARTY_QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger(__name__).debug(
        "Logging configured: level=%s, log_dir=%s", config.log_level, log_dir
    )


def _configure_console_only(root: logging.Logger, level: str) -> None:
    """Fallback: console-only when log directory creation fails."""
    if getattr(root, _SENTINEL_ATTR, False):
        return

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root.setLevel(_resolve_level(level))
    root.addHandler(handler)
    setattr(root, _SENTINEL_ATTR, True)

    logging.getLogger(__name__).warning(
        "Log directory unavailable; falling back to console-only logging"
    )


def _resolve_level(level_str: str) -> int:
    """Convert level string to logging int constant (fallback: INFO)."""
    return getattr(logging, level_str.upper(), logging.INFO)
