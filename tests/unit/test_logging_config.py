"""Unit tests for stock_manager.config.logging_config."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from unittest.mock import patch

import pytest

# Reset the root logger sentinel between tests
ROOT_SENTINEL = "_stock_manager_configured"


def _app_handlers(root: logging.Logger) -> list:
    """Return only handlers added by setup_logging (excludes pytest's LogCaptureHandler)."""
    return [h for h in root.handlers if not h.__class__.__name__ == "LogCaptureHandler"]


def _reset_root_logger() -> None:
    """Remove all handlers from root logger and clear the sentinel."""
    root = logging.getLogger()
    root.handlers.clear()
    if hasattr(root, ROOT_SENTINEL):
        delattr(root, ROOT_SENTINEL)
    root.setLevel(logging.WARNING)  # back to Python default


@pytest.fixture(autouse=True)
def clean_root_logger():
    """Ensure root logger is clean before and after each test."""
    _reset_root_logger()
    yield
    _reset_root_logger()


class TestLogConfig:
    def test_log_config_defaults(self):
        """LogConfig should have sensible defaults without any env overrides."""
        from stock_manager.config.logging_config import LogConfig

        with patch.dict("os.environ", {}, clear=False):
            config = LogConfig()

        assert config.log_level == "INFO"
        assert config.log_dir == "logs"

    def test_log_config_from_env(self):
        """LogConfig should read LOG_LEVEL and LOG_DIR from environment."""
        from stock_manager.config.logging_config import LogConfig

        env_overrides = {"LOG_LEVEL": "DEBUG", "LOG_DIR": "custom_logs"}
        with patch.dict("os.environ", env_overrides):
            config = LogConfig()

        assert config.log_level == "DEBUG"
        assert config.log_dir == "custom_logs"


class TestSetupLogging:
    def test_setup_logging_creates_directory(self, tmp_path: Path):
        """setup_logging should create the log directory if it does not exist."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        log_dir = tmp_path / "new_logs_dir"
        assert not log_dir.exists()

        config = LogConfig(log_level="INFO", log_dir=str(log_dir))

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        assert log_dir.exists()

    def test_setup_logging_attaches_three_handlers(self, tmp_path: Path):
        """Root logger should have exactly 3 handlers after setup_logging."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        config = LogConfig(log_level="INFO", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        root = logging.getLogger()
        assert len(_app_handlers(root)) == 3

    def test_setup_logging_handler_types(self, tmp_path: Path):
        """Handlers should be: 1 StreamHandler, 2 TimedRotatingFileHandlers."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        config = LogConfig(log_level="INFO", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        root = logging.getLogger()
        handlers = _app_handlers(root)
        handler_types = [type(h) for h in handlers]
        assert logging.StreamHandler in handler_types
        assert logging.handlers.TimedRotatingFileHandler in handler_types
        timed_handlers = [h for h in handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
        assert len(timed_handlers) == 2

    def test_setup_logging_error_separation(self, tmp_path: Path):
        """The error.log handler should only capture ERROR and above."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        config = LogConfig(log_level="INFO", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        root = logging.getLogger()
        timed_handlers = [h for h in _app_handlers(root) if isinstance(h, logging.handlers.TimedRotatingFileHandler)]

        # One handler accepts DEBUG, the other requires ERROR
        levels = {h.level for h in timed_handlers}
        assert logging.ERROR in levels
        assert logging.DEBUG in levels or logging.NOTSET in levels

    def test_setup_logging_format(self, tmp_path: Path):
        """All handlers should share the same formatter with expected format string."""
        from stock_manager.config.logging_config import LogConfig, setup_logging, _LOG_FORMAT

        config = LogConfig(log_level="INFO", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        root = logging.getLogger()
        for handler in _app_handlers(root):
            assert handler.formatter is not None
            assert handler.formatter._fmt == _LOG_FORMAT

    def test_setup_logging_idempotent(self, tmp_path: Path):
        """Calling setup_logging twice should NOT add duplicate handlers."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        config = LogConfig(log_level="INFO", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)
            setup_logging(config)  # second call should be no-op

        root = logging.getLogger()
        assert len(_app_handlers(root)) == 3  # still exactly 3, not 6

    def test_setup_logging_sets_root_level(self, tmp_path: Path):
        """Root logger level should reflect config.log_level."""
        from stock_manager.config.logging_config import LogConfig, setup_logging

        config = LogConfig(log_level="DEBUG", log_dir="logs")

        with patch("stock_manager.config.logging_config.project_root_cached", return_value=tmp_path):
            setup_logging(config)

        root = logging.getLogger()
        assert root.level == logging.DEBUG
