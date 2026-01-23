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
  - `worker.py`: 워커 도메인 모델 (WorkerStatus, StockLock, WorkerProcess, Candidate, DailySummary)
- `src/stock_manager/service_layer/`: 유스케이스(장 시작/복구/주문 실행)
  - `order_service.py`: 주문 생성, 전송, 취소, 체결 처리
  - `position_service.py`: 포지션 계산 및 업데이트
  - `lock_service.py`: 분산 락 관리 (acquire, release, renew, heartbeat, cleanup)
  - `worker_lifecycle_service.py`: 워커 생명주기 관리 (start, stop, status, cleanup)
  - `market_data_poller.py`: 후보 종목 발견 및 필터링
  - `strategy_executor.py`: 매수/매도 시그널 평가
  - `pnl_calculator.py`: PnL 계산 (실현/미실현/일일)
  - `daily_summary_service.py`: 일일 요약 생성 및 조회
  - `worker_main.py`: 워커 오케스트레이터 (상태 머신, 이벤트 루프)
- `src/stock_manager/adapters/`: 외부 의존성 어댑터
  - `broker/`: 한국투자증권 REST/WS
  - `storage/`: PostgreSQL, 락 관리
  - `notifications/`: Slack 등 알림
  - `observability/`: logger/metrics
- `src/stock_manager/entrypoints/`: CLI/worker/scheduler
- `src/stock_manager/utils/`: 공통 유틸
  - `slack.py`: Slack 알림 전송 유틸

## 다음 단계
- 리스크 룰 확정 (SPEC-BACKEND-INFRA-003)
- 전략 로직 구현 (구체화 필요)
- 워커 아키텍처 구현 완료 ✅ (SPEC-BACKEND-WORKER-004)
- 테스트 커버리지 개선 (현재 82%)
- PostgreSQL DB 스키마 적용 (worker_schema.sql)
- 데이터베이스 포트 구현 (PostgreSQL/SQLite)

## 구현된 기능

### SPEC-BACKEND-002: 주문 실행 및 상태 관리 시스템
- 주문 생성 (idempotency key 중복 검사 포함)
- 주문 전송 (NEW → SENT 상태 전이)
- 주문 취소 (SENT/PARTIAL → CANCELED)
- 체결 처리 (누적 수량 계산, PARTIAL → FILLED 상태 전이)
- 포지션 계산 및 업데이트
- 브로커/DB 상태 동기화

### SPEC-BACKEND-WORKER-004: 워커 아키텍처
- **분산 락 서비스 (LockService)**
  - PostgreSQL row-level locks 기반 원자적 락 획득
  - TTL(Time-To-Live) 지원 및 갱신 (renew)
  - 하트비트 메커니즘으로 생존 상태 추적
  - 만료된 락 자동 정리 (cleanup_expired)
- **워커 생명주기 관리 (WorkerLifecycleService)**
  - 워커 등록 및 상태 추적 (IDLE, SCANNING, HOLDING, EXITING)
  - 정상 종료 및 크래시 복구 지원
  - 정지된 워커 감지 및 정리 (cleanup_stale_workers)
- **마켓 데이터 폴러 (MarketDataPoller)**
  - 후보 종목 발견 (discover_candidates)
  - 거래량/가격 범위 기반 필터링
  - 커스텀 필터 지원
- **전략 실행기 (StrategyExecutor)**
  - 매수 시그널 평가 (should_buy)
  - 매도 시그널 평가 (should_sell)
  - 신뢰도(confidence) 임계값 지원
  - 플러그인 가능한 전략 포트 (StrategyPort)
- **PnL 계산기 (PnLCalculator)**
  - 미실현 PnL 계산 (calculate_unrealized_pnl)
  - 실현 PnL 계산 (calculate_realized_pnl)
  - 승률 계산 (calculate_win_rate)
  - 수익률 계산 (calculate_profit_factor)
  - 최대 낙폭 계산 (calculate_max_drawdown)
- **일일 요약 서비스 (DailySummaryService)**
  - 일일 성과 요약 생성 (generate_summary)
  - 날짜별 조회 (get_summary)
  - 날짜 범위 목록 (list_summaries)
- **워커 메인 오케스트레이터 (WorkerMain)**
  - 상태 머신 (IDLE → SCANNING → HOLDING → SCANNING → EXITING)
  - 비동기 이벤트 루프
  - 백그라운드 하트비트 태스크
  - 모든 서비스 통합 (Lock, Lifecycle, Poller, Strategy, Order, Summary)

### Slack 알림
- 주문/체결/리스크 이벤트 알림
- 에러 로그 알림
- 시스템 상태 모니터링
- 메시지 전송/수정/스레드 댓글 기능 (ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md 참조)

## AI 개발자 가이드

### ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md
Slack 알림 유틸의 사용법, API, 테스트 가이드 포함

## 테스트 커버리지

현재 상태: 82% (76/88 tests passing)

- 도메인 모델 테스트: Order, Fill, OrderStatus, OrderRequest (10 tests)
- 도메인 모델 테스트: Worker 도메인 (WorkerStatus, StockLock, WorkerProcess, Candidate, PositionSnapshot, DailySummary) (21 tests)
- 서비스 레이어 테스트: OrderService (in progress)
- 어댑터 테스트: MockBroker, KISBroker, KISConfig, KISRestClient (33 tests)
- 유틸리티 테스트: Slack 알림 (7 tests)

테스트 실행:
```bash
pytest tests/
```
