# Stock Manager (Boilerplate)

Python 3.13 기반 자동매매 봇 보일러플레이트.

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# 환경 변수 채우기
```

## 구조
- `src/stock_manager/config/`: 환경/설정 로딩
- `src/stock_manager/domain/`: 순수 도메인(전략/리스크/모델)
- `src/stock_manager/service_layer/`: 유스케이스(장 시작/복구/주문 실행)
  - `order_service.py`: 주문 생성, 전송, 취소, 체결 처리
  - `position_service.py`: 포지션 계산 및 업데이트
- `src/stock_manager/adapters/`: 외부 의존성 어댑터
  - `broker/`: 한국투자증권 REST/WS
  - `storage/`: PostgreSQL
  - `notifications/`: Slack 등 알림
  - `observability/`: logger/metrics
- `src/stock_manager/entrypoints/`: CLI/worker/scheduler
- `src/stock_manager/utils/`: 공통 유틸
  - `slack.py`: Slack 알림 전송 유틸

## 다음 단계
- 브로커 API 구현체 추가
- 전략 로직 구현
- 리스크 룰 확정
- 워커 아키텍처 구현 (SPEC-BACKEND-WORKER-004)

## 구현된 기능

### SPEC-BACKEND-002: 주문 실행 및 상태 관리 시스템
- 주문 생성 (idempotency key 중복 검사 포함)
- 주문 전송 (NEW → SENT 상태 전이)
- 주문 취소 (SENT/PARTIAL → CANCELED)
- 체결 처리 (누적 수량 계산, PARTIAL → FILLED 상태 전이)
- 포지션 계산 및 업데이트
- 브로커/DB 상태 동기화

### Slack 알림
- 주문/체결/리스크 이벤트 알림
- 에러 로그 알림
- 시스템 상태 모니터링
