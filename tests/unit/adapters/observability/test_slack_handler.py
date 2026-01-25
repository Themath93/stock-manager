"""Tests for SlackHandler."""

import logging
import pytest
import time
from unittest.mock import MagicMock, Mock, patch

from stock_manager.adapters.observability.slack_handler import SlackHandler
from stock_manager.adapters.observability.slack_handler_config import SlackHandlerConfig


class TestSlackHandler:
    """Test SlackHandler class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SlackHandlerConfig(
            bot_token="PLACEHOLDER_TOKEN",
            critical_channel="C001",
            error_channel="C002",
            warning_channel="C003",
            timeout=1.0,
            batch_interval=10,  # Minimum allowed for testing
            enable_duplicates_filter=True,
            duplicate_window=60,
        )

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock SlackClient."""
        client = MagicMock()
        client.post_message = MagicMock()
        return client

    @pytest.fixture
    def handler(self, config, mock_slack_client):
        """Create test SlackHandler with mocked client."""
        with patch("stock_manager.adapters.observability.slack_handler.SlackClient", return_value=mock_slack_client):
            handler = SlackHandler(config)
            return handler

    def test_initialization(self, config):
        """Test handler initialization."""
        with patch("stock_manager.adapters.observability.slack_handler.SlackClient"):
            handler = SlackHandler(config)
            assert handler._config == config
            assert handler._mapper is not None
            assert handler._formatter is not None

    def test_emit_error_level(self, handler, mock_slack_client):
        """Test emitting ERROR level log."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Wait a bit for async processing
        import time
        time.sleep(0.1)

        # Should have called post_message
        assert mock_slack_client.post_message.called

    def test_emit_critical_level(self, handler, mock_slack_client):
        """Test emitting CRITICAL level log."""
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="Test critical",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Wait a bit for async processing
        import time
        time.sleep(0.1)

        # Should have called post_message
        assert mock_slack_client.post_message.called

    def test_emit_warning_level_batched(self, handler, mock_slack_client):
        """Test emitting WARNING level log (batched)."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test warning",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Should be added to batch queue
        assert len(handler._batch_queue) == 1

    def test_emit_info_level_ignored(self, handler, mock_slack_client):
        """Test that INFO level is ignored."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test info",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Should not be queued
        assert handler._queue.empty()
        assert len(handler._batch_queue) == 0

    def test_duplicate_filtering(self, handler, mock_slack_client):
        """Test duplicate message filtering."""
        # Create identical records
        record1 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Duplicate message",
            args=(),
            exc_info=None,
        )
        record2 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Duplicate message",
            args=(),
            exc_info=None,
        )

        handler.emit(record1)
        handler.emit(record2)

        # Wait for async processing
        import time
        time.sleep(0.1)

        # Only first should trigger post_message (second filtered as duplicate)
        assert mock_slack_client.post_message.call_count == 1

    def test_flush_batch_single_message(self, handler):
        """Test flushing batch with single message."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test warning",
            args=(),
            exc_info=None,
        )

        handler._batch_queue.append(record)
        handler._flush_batch()

        # Batch should be empty after flush
        assert len(handler._batch_queue) == 0

    def test_flush_batch_multiple_messages(self, handler):
        """Test flushing batch with multiple messages."""
        for i in range(3):
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname="test.py",
                lineno=i,
                msg=f"Warning {i}",
                args=(),
                exc_info=None,
            )
            handler._batch_queue.append(record)

        handler._flush_batch()

        # Batch should be empty after flush
        assert len(handler._batch_queue) == 0

    def test_close_handler(self, config):
        """Test closing the handler."""
        with patch("stock_manager.adapters.observability.slack_handler.SlackClient"):
            handler = SlackHandler(config)
            handler._batch_queue = [MagicMock()]  # Add dummy record
            handler._shutdown_event = Mock()
            handler._shutdown_event.is_set = MagicMock(return_value=True)

            # Should not raise
            handler.close()

    def test_context_manager(self, config):
        """Test using handler as context manager."""
        with patch("stock_manager.adapters.observability.slack_handler.SlackClient"):
            with SlackHandler(config) as handler:
                assert handler is not None
            # Should close on exit

    def test_emit_exception_handling(self, handler):
        """Test that emit handles exceptions gracefully."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Mock mapper to raise exception
        handler._mapper.get_alert_mapping = Mock(side_effect=Exception("Test error"))

        # Should not raise
        handler.emit(record)

    def test_integration_with_logger(self, config):
        """Test integration with Python logging framework."""
        with patch("stock_manager.adapters.observability.slack_handler.SlackClient"):
            handler = SlackHandler(config)
            logger = logging.getLogger("test_logger")
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)

            # These should not raise
            logger.warning("Test warning")
            logger.error("Test error")
            logger.critical("Test critical")
