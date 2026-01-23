"""Slack 상태 전송 유틸리티.

채널 ID만 지원하며, 메시지 전송/수정/스레드 댓글 기능을 제공합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


@dataclass(frozen=True)
class SlackMessageRef:
    channel: str
    ts: str


@dataclass(frozen=True)
class SlackResult:
    success: bool
    status: int | None
    error: str | None
    ref: SlackMessageRef | None


class SlackClient:
    """채널 ID 전용 Slack 클라이언트.

    채널 이름을 ID로 변환하지 않습니다. 호출자는 항상 채널 ID를 전달해야 합니다.
    """

    def __init__(
        self,
        token: str,
        default_channel: str | None = None,
        timeout: float = 5.0,
        client: WebClient | None = None,
    ) -> None:
        """SlackClient를 초기화합니다.

        Args:
            token: Slack Bot 토큰.
            default_channel: 기본 채널 ID. None이면 호출 시 channel이 필수입니다.
            timeout: 요청 타임아웃(초).
            client: 테스트를 위한 WebClient 주입 옵션.

        Returns:
            None: 이 메서드는 값을 반환하지 않습니다.

        Raises:
            None: 이 메서드는 예외를 직접 발생시키지 않습니다.

        Examples:
            >>> SlackClient(token="xoxb-***", default_channel="C01234567")
        """
        self._default_channel = default_channel
        self._client = client or WebClient(token=token, timeout=timeout)

    def post_message(
        self,
        text: str,
        channel: str | None = None,
        blocks: Sequence[dict[str, Any]] | None = None,
        level: str | None = None,
    ) -> SlackResult:
        """Slack 채널에 새 메시지를 전송합니다.

        Args:
            text: 메시지 본문 텍스트.
            channel: 채널 ID. None이면 기본 채널을 사용합니다.
            blocks: Slack Block Kit 구조(옵션).
            level: 텍스트 앞에 붙일 레벨 프리픽스(예: info, error).

        Returns:
            SlackResult: 성공 여부와 메시지 참조(ref)를 포함한 결과.

        Raises:
            None: Slack API 오류는 SlackResult로 변환됩니다.

        Examples:
            >>> client = SlackClient(token="xoxb-***", default_channel="C01234567")
            >>> result = client.post_message("bot started", level="info")
            >>> bool(result.success)
            True
        """
        target = self._resolve_channel(channel)
        if not target:
            return SlackResult(False, None, "channel_id_required", None)

        payload = {"channel": target, "text": self._format_text(text, level)}
        if blocks:
            payload["blocks"] = list(blocks)

        try:
            response = self._client.chat_postMessage(**payload)
            return self._result_from_response(response)
        except SlackApiError as exc:
            return self._result_from_slack_error(exc)
        except Exception as exc:  # pragma: no cover - safety net
            return SlackResult(False, None, str(exc), None)

    def update_message(
        self,
        ref: SlackMessageRef,
        text: str,
        blocks: Sequence[dict[str, Any]] | None = None,
    ) -> SlackResult:
        """기존 메시지를 수정합니다.

        Args:
            ref: 수정할 메시지 참조(channel, ts).
            text: 변경할 메시지 텍스트.
            blocks: Slack Block Kit 구조(옵션).

        Returns:
            SlackResult: 성공 여부와 메시지 참조(ref)를 포함한 결과.

        Raises:
            None: Slack API 오류는 SlackResult로 변환됩니다.

        Examples:
            >>> ref = SlackMessageRef(channel="C01234567", ts="1719829111.000100")
            >>> client.update_message(ref, "status updated")
        """
        payload = {"channel": ref.channel, "ts": ref.ts, "text": text}
        if blocks:
            payload["blocks"] = list(blocks)

        try:
            response = self._client.chat_update(**payload)
            return self._result_from_response(response)
        except SlackApiError as exc:
            return self._result_from_slack_error(exc)
        except Exception as exc:  # pragma: no cover - safety net
            return SlackResult(False, None, str(exc), None)

    def reply_in_thread(
        self,
        ref: SlackMessageRef,
        text: str,
        blocks: Sequence[dict[str, Any]] | None = None,
    ) -> SlackResult:
        """메시지 스레드에 댓글을 작성합니다.

        Args:
            ref: 스레드 기준 메시지 참조(channel, ts).
            text: 댓글 텍스트.
            blocks: Slack Block Kit 구조(옵션).

        Returns:
            SlackResult: 성공 여부와 새 댓글 메시지 참조(ref)를 포함한 결과.

        Raises:
            None: Slack API 오류는 SlackResult로 변환됩니다.

        Examples:
            >>> ref = SlackMessageRef(channel="C01234567", ts="1719829111.000100")
            >>> client.reply_in_thread(ref, "listening for data")
        """
        payload = {
            "channel": ref.channel,
            "text": text,
            "thread_ts": ref.ts,
        }
        if blocks:
            payload["blocks"] = list(blocks)

        try:
            response = self._client.chat_postMessage(**payload)
            return self._result_from_response(response)
        except SlackApiError as exc:
            return self._result_from_slack_error(exc)
        except Exception as exc:  # pragma: no cover - safety net
            return SlackResult(False, None, str(exc), None)

    def _resolve_channel(self, channel: str | None) -> str | None:
        return channel or self._default_channel

    def _format_text(self, text: str, level: str | None) -> str:
        if not level:
            return text
        return f"[{level.upper()}] {text}"

    def _result_from_response(self, response: Any) -> SlackResult:
        status = getattr(response, "status_code", None)
        channel = response.get("channel")
        ts = response.get("ts")
        ref = SlackMessageRef(channel=channel, ts=ts) if channel and ts else None
        return SlackResult(True, status, None, ref)

    def _result_from_slack_error(self, exc: SlackApiError) -> SlackResult:
        status = getattr(exc.response, "status_code", None)
        error = None
        if exc.response is not None:
            error = exc.response.data.get("error")
        return SlackResult(False, status, error or str(exc), None)
