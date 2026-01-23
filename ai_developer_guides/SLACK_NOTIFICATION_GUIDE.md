# Slack 알림 유틸 가이드

## 목적
자동매매 봇의 상태/이벤트를 Slack으로 전송하기 위한 최소 유틸을 제공한다.
도메인/서비스/브로커/DB 로직과 완전히 분리하여 독립적으로 사용한다.

## 범위
- 새 메시지 전송
- 기존 메시지 수정
- 스레드 댓글 전송

## 비범위
- 채널 이름 → ID 변환
- 재시도/백오프/로깅(상위 레이어 책임)
- 고급 템플릿/포맷팅(필요 시 호출부에서 처리)

## 의존성
- `slack-sdk` (Python SDK)
- 최소 권한: `chat:write`

## 채널 정책
- **채널 ID만 허용**한다. 채널명 조회/변환은 제공하지 않는다.
- 업데이트/스레드 댓글을 위해 `channel` + `ts`를 저장해야 한다.

## 공개 API
위치: `src/stock_manager/utils/slack.py`

- `SlackClient(token, default_channel=None, timeout=5.0, client=None)`
- `post_message(text, channel=None, blocks=None, level=None) -> SlackResult`
- `update_message(ref, text, blocks=None) -> SlackResult`
- `reply_in_thread(ref, text, blocks=None) -> SlackResult`

## 반환 타입
- `SlackMessageRef(channel, ts)`
- `SlackResult(success, status, error, ref)`
  - 성공 시 `ref`가 채워진다.

## 에러 처리
- `SlackApiError`를 잡아 `SlackResult`로 변환한다.
- 실패 시 예외를 던지지 않는다(봇 핵심 로직 중단 방지).

## 사용 예시
```python
from stock_manager.utils import SlackClient

slack = SlackClient(token=SLACK_BOT_TOKEN, default_channel=SLACK_CHANNEL_ID)
result = slack.post_message("bot started", level="info")

if result.success and result.ref:
    slack.reply_in_thread(result.ref, "listening for market data")
```

## 테스트 가이드
- `client` 파라미터로 `WebClient`를 주입해 모킹한다.
- 예외 대신 `SlackResult` 값을 단언한다.
