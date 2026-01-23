"""
Tests for Slack notification utility
"""

import pytest
from slack_sdk.errors import SlackApiError
from unittest.mock import Mock, MagicMock, patch

from src.stock_manager.utils.slack import SlackClient, SlackResult, SlackMessageRef


class TestSlackClient:
    """SlackClient 테스트"""

    @pytest.fixture
    def mock_web_client(self):
        """테스트용 WebClient mock"""
        client = MagicMock()
        return client

    @pytest.fixture
    def slack_client(self, mock_web_client):
        """테스트용 SlackClient"""
        return SlackClient(
            token="fake_test_token_not_real",
            default_channel="C1234567890",
            timeout=5.0,
            client=mock_web_client,
        )

    def test_init_default_params(self, slack_client):
        """기본 파라미터로 초기화"""
        assert slack_client.token == "fake_test_token_not_real"
        assert slack_client.default_channel == "C1234567890"
        assert slack_client.timeout == 5.0

    def test_init_with_default_channel(self, slack_client):
        """기본 채널로 초기화"""
        assert slack_client.default_channel == "C1234567890"

    def test_post_message_success(self, slack_client, mock_web_client):
        """메시지 전송 성공"""
        mock_web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C1234567890",
        }

        result = slack_client.post_message("Test message")

        assert result.success is True
        assert result.ref is not None
        assert result.ref.channel == "C1234567890"
        assert result.ref.ts == "1234567890.123456"
        assert result.error is None

        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C1234567890",
            text="Test message",
            blocks=None,
        )

    def test_post_message_with_custom_channel(self, slack_client, mock_web_client):
        """커스텀 채널로 메시지 전송"""
        mock_web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C9876543210",
        }

        result = slack_client.post_message("Test", channel="C9876543210")

        assert result.success is True
        assert result.ref.channel == "C9876543210"

        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C9876543210",
            text="Test",
            blocks=None,
        )

    def test_post_message_with_blocks(self, slack_client, mock_web_client):
        """blocks 포함 메시지 전송"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Test block message",
                },
            }
        ]

        mock_web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C1234567890",
        }

        result = slack_client.post_message("Test", blocks=blocks)

        assert result.success is True

        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C1234567890",
            text="Test",
            blocks=blocks,
        )

    def test_post_message_api_error(self, slack_client, mock_web_client):
        """API 에러 발생 시 SlackResult 반환"""
        mock_web_client.chat_postMessage.side_effect = SlackApiError(
            message="Channel not found",
            response={"data": {"ok": False}},
        )

        result = slack_client.post_message("Test")

        assert result.success is False
        assert result.ref is None
        assert result.status == "error"
        assert "Channel not found" in result.error

    def test_update_message_success(self, slack_client, mock_web_client):
        """메시지 수정 성공"""
        ref = SlackMessageRef(channel="C1234567890", ts="1234567890.123456")

        mock_web_client.chat_update.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C1234567890",
        }

        result = slack_client.update_message(ref, "Updated message")

        assert result.success is True

        mock_web_client.chat_update.assert_called_once_with(
            channel="C1234567890",
            ts="1234567890.123456",
            text="Updated message",
            blocks=None,
        )

    def test_reply_in_thread_success(self, slack_client, mock_web_client):
        """스레드 댓글 전송 성공"""
        ref = SlackMessageRef(channel="C1234567890", ts="1234567890.123456")

        mock_web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.789012",
            "channel": "C1234567890",
        }

        result = slack_client.reply_in_thread(ref, "Thread reply")

        assert result.success is True

        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C1234567890",
            thread_ts="1234567890.123456",
            text="Thread reply",
            blocks=None,
        )


class TestSlackResult:
    """SlackResult 테스트"""

    def test_success_result(self):
        """성공 결과 생성"""
        ref = SlackMessageRef(channel="C123", ts="123")

        result = SlackResult(
            success=True,
            status="success",
            error=None,
            ref=ref,
        )

        assert result.success is True
        assert result.status == "success"
        assert result.error is None
        assert result.ref is not None

    def test_error_result(self):
        """에러 결과 생성"""
        result = SlackResult(
            success=False,
            status="error",
            error="API call failed",
            ref=None,
        )

        assert result.success is False
        assert result.status == "error"
        assert result.error == "API call failed"
        assert result.ref is None


class TestSlackMessageRef:
    """SlackMessageRef 테스트"""

    def test_create_message_ref(self):
        """메시지 참조 생성"""
        ref = SlackMessageRef(channel="C1234567890", ts="1234567890.123456")

        assert ref.channel == "C1234567890"
        assert ref.ts == "1234567890.123456"
