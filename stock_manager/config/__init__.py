"""Configuration utilities for stock-manager.

This package centralizes project-root discovery and `.env` handling so that
config loading works reliably regardless of the current working directory.
"""

from stock_manager.config.paths import default_env_file, find_project_root, require_project_root
from stock_manager.config.logging_config import LogConfig, setup_logging

__all__ = [
    "default_env_file",
    "find_project_root",
    "require_project_root",
    "LogConfig",
    "setup_logging",
]

