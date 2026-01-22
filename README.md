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
- `src/stock_manager/adapters/`: 외부 의존성 어댑터
  - `broker/`: 한국투자증권 REST/WS
  - `storage/`: PostgreSQL
  - `notifications/`: Slack 등 알림
  - `observability/`: logger/metrics
- `src/stock_manager/entrypoints/`: CLI/worker/scheduler
- `src/stock_manager/utils/`: 공통 유틸

## 다음 단계
- 브로커 API 구현체 추가
- 전략 로직 구현
- 리스크 룰 확정
