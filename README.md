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
  - `app_config.py`: 통합 앱 설정 (AppConfig - KIS, Slack, 공통 설정)
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
- `scripts/`: 유틸리티 스크립트
  - `kis_slack_check.py`: KIS API 및 Slack 알림 연동 테스트 스크립트

## 다음 단계
- 리스크 룰 확정 (SPEC-BACKEND-INFRA-003)
- 전략 로직 구현 (구체화 필요)
- 테스트 커버리지 개선 (현재 52%, 목표 80%)
- 리팩토링 및 코드 정리

## 구현된 기능

### SPEC-BACKEND-API-001: 한국투자증권 OpenAPI 브로커 어댑터 (85% 완료)
- **BrokerPort 인터페이스** ✅ 완료
  - 추상 인터페이스 정의 (port/broker_port.py)
- **KIS 설정 모듈** ✅ 완료
  - LIVE/PAPER 모드 지원
  - 환경 변수 로딩 (KIS_APP_KEY, KIS_APP_SECRET, MODE)
  - REST_URL, WS_URL 자동 전환
- **REST 클라이언트** ✅ 완료 (Phase 2)
  - access_token 발급 (/oauth2/tokenP)
  - 주문 전송, 조회 기본 기능
  - approval_key 발급 (/oauth2/Approval) ✅ 완료
  - 토큰 자동 갱신 (스레드 안전) ✅ 완료
  - 해시키 생성 (/uapi/hashkey) ✅ 완료
  - threading.Lock으로 동시성 제어 ✅ 완료
- **WebSocket 클라이언트** ✅ 완료
  - 연결/종료 메서드
  - 호가 구독 (subscribe_quotes)
  - 체결 이벤트 구독 (subscribe_executions)
  - 지수 백오프 재연결 로직
- **MockBrokerAdapter** ✅ 완료
  - 테스트용 더블 구현
- **품질 지표** ✅ 달성
  - 테스트 커버리지: 85% (목표 80%)
  - 테스트 통과율: 100% (26/26)
  - TRUST 5 점수: 94.3%
  - 스레드 안전성: 완료
- **Phase 3 예정 작업** ⏳
  - KISBrokerAdapter 완성
  - WebSocket 연결 통합
  - 통합 테스트 작성

### SPEC-BACKEND-002: 주문 실행 및 상태 관리 시스템
- 주문 생성 (idempotency key 중복 검사 포함)
- 주문 전송 (NEW → SENT 상태 전이)
- 주문 취소 (SENT/PARTIAL → CANCELED)
- 체결 처리 (누적 수량 계산, PARTIAL → FILLED 상태 전이)
- 포지션 계산 및 업데이트
- 브로커/DB 상태 동기화

### SPEC-BACKEND-WORKER-004: 워커 아키텍처 (완료)
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

### SPEC-BACKEND-INFRA-003: 장 시작/종료 및 상태 복구 라이프사이클 (완료)
- **장 시작/종료 서비스 (MarketLifecycleService)**
  - 장 시작 프로세스 (설정 로드, 인증, 계좌 확인, 전략 파라미터 로드)
  - 장 종료 프로세스 (미체결 주문 취소 확인, 포지션 스냅샷 생성, 일일 정산 계산)
  - 시스템 상태 관리 (OFFLINE → INITIALIZING → READY → TRADING → CLOSING → CLOSED)
  - 거래 중지 모드 (STOPPED 상태 지원)
- **상태 복구 서비스 (StateRecoveryService)**
  - DB/브로커 상태 비교 및 동기화
  - 미체결 주문 복구 (DB 조회 → 브로커 조회 → 상태 동기화)
  - 포지션 재계산 (체결 기반 포지션 일치 확인)
  - 복구 실패 시 거래 중지 처리
- **정산 서비스 (SettlementService)**
  - 포지션 스냅샷 생성 (모든 포지션 현재 상태 저장)
  - 일일 정산 계산 (실현 손익, 평가 손익, 총 손익)
  - DailySettlementEvent 발행
- **데이터베이스 스키마**
  - market_states 테이블 (시스템 상태 추적)
  - daily_settlements 테이블 (일일 정산 기록)
  - recovery_logs 테이블 (상태 복구 이력)

### SPEC-OBSERVABILITY-001: 로그 레벨 기반 Slack 알림 시스템 (완료)
- **Python logging.Handler 통합** ✅ 완료
  - SlackHandler: Python 표준 logging 모듈과 Slack 통합
  - AlertMapper: 로그 레벨 → 알림 설정 매핑 (CRITICAL, ERROR, WARNING, INFO, DEBUG)
  - SlackFormatter: 구조화된 Slack 메시지 포맷팅 및 민감 정보 마스킹
  - SlackHandlerConfig: Pydantic 기반 설정 관리
- **알림 라우팅 정책** ✅ 완료
  - CRITICAL: 즉시 알림, 스택 트레이스 포함, (!) 이모지
  - ERROR: 즉시 알림, (x) 이모지
  - WARNING: 배치 처리 (5분 집계), (warning) 이모지
  - INFO/DEBUG: Slack 알림 없음
- **고급 기능** ✅ 완료
  - 비동기 전송 (백그라운드 스레드)
  - 중복 알림 필터 (SHA256 해시 기반, 1분 윈도우)
  - 민감 정보 마스킹 (token, secret, password, api_key 패턴)
  - 배치 큐 자동 플러시 (종료 시)
- **품질 지표** ✅ 완료
  - 테스트 커버리지: 95% (목표 85% 초과)
  - 테스트 통과율: 100% (57/57 tests)
  - TRUST 5 준수 완료
- **사용 예제**
  ```python
  import logging
  from stock_manager.adapters.observability import SlackHandler, SlackHandlerConfig

  logger = logging.getLogger(__name__)
  config = SlackHandlerConfig(
      bot_token=os.getenv("SLACK_BOT_TOKEN"),
      critical_channel=os.getenv("SLACK_CRITICAL_CHANNEL"),
      error_channel=os.getenv("SLACK_ERROR_CHANNEL"),
      warning_channel=os.getenv("SLACK_WARNING_CHANNEL"),
  )
  handler = SlackHandler(config)
  logger.addHandler(handler)

  logger.critical("Critical system failure")  # 즉시 Slack으로 전송
  logger.error("Database connection failed")  # 즉시 Slack으로 전송
  logger.warning("High memory usage")         # 5분 배치 처리
  logger.info("Application started")          # Slack 전송 없음
  ```

### Slack 알림
- 주문/체결/리스크 이벤트 알림
- 에러 로그 알림 (자동 레벨 기반 라우팅)
- 시스템 상태 모니터링
- 메시지 전송/수정/스레드 댓글 기능 (ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md 참조)

### 통합 설정 관리 (AppConfig)
- `src/stock_manager/config/app_config.py`에서 통합 설정 관리
- KIS 설정: 모드(LIVE/PAPER), API 키, REST/WebSocket URL
- Slack 설정: Bot Token, Channel ID
- 공통 설정: 로그 레벨, 계좌 ID
- 운영 모드에 따른 URL 자동 선택 헬퍼 메서드 제공

## 개발 환경 설정

### 로컬 PostgreSQL 환경 (docker-compose)
프로젝트 루트의 `docker-compose.yml`을 사용하여 로컬 개발용 PostgreSQL 데이터베이스를 실행할 수 있습니다.

```bash
# PostgreSQL 컨테이너 시작
docker-compose up -d postgres

# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgres

# 컨테이너 중지
docker-compose down

# 볼륨 포함하여 완전 삭제
docker-compose down -v
```

**설정:**
- 이미지: postgres:15-alpine
- 포트: 5432
- 데이터베이스: stock_manager
- 사용자: postgres / postgres
- Health check 포함

**환경 변수 (.env):**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_manager
DB_USER=postgres
DB_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stock_manager
```

## 유틸리티 스크립트

### KIS Slack Check 스크립트
`scripts/kis_slack_check.py`는 KIS API 연결과 Slack 알림 전송을 테스트하는 유틸리티입니다.

```bash
# 실행 방법
python scripts/kis_slack_check.py

# 환경 변수 요구사항:
# - ACCOUNT_ID: 계좌 ID
# - SLACK_BOT_TOKEN: Slack Bot Token
# - SLACK_CHANNEL_ID: Slack Channel ID
# - KIS_APP_KEY 또는 KIS_KIS_APP_KEY: KIS 앱키
# - KIS_APP_SECRET 또는 KIS_KIS_APP_SECRET: KIS 앱시크릿키
```

**기능:**
- KIS API 인증 및 현금 잔고 조회
- Slack 알림 전송 테스트
- 계좌 정보 마스킹 처리

## 테스트

### 테스트 커버리지

현재 상태: 85% (26/26 KISRestClient tests passing)

**Phase 2 업데이트:**
- KISRestClient 단위 테스트: 26개 ✅ (TokenManager 7개, approval_key 3개, 해시키 3개, 기본 13개)
- 테스트 커버리지: 85% (목표 80% 초과 달성)
- TRUST 5 점수: 94.3%

**전체 프로젝트 테스트:**
- 도메인 모델 테스트: Order, Fill, OrderStatus, OrderRequest (10 tests)
- 도메인 모델 테스트: Worker 도메인 (WorkerStatus, StockLock, WorkerProcess, Candidate, PositionSnapshot, DailySummary) (21 tests)
- 서비스 레이어 테스트: OrderService, LockService, WorkerLifecycleService 등
- 어댑터 테스트: MockBroker, KISBroker, KISConfig, KISRestClient, PostgreSQL
- 유틸리티 테스트: Slack 알림 (7 tests)

### 단위 테스트 실행

```bash
# 전체 테스트 실행
pytest tests/

# 단위 테스트만 실행
pytest tests/unit/

# 특정 모듈 테스트
pytest tests/unit/domain/test_order.py -v

# 커버리지 리포트
pytest --cov=src/stock_manager --cov-report=html tests/
```

### 통합 테스트 실행

통합 테스트는 PostgreSQL 데이터베이스가 필요합니다. docker-compose로 데이터베이스를 먼저 실행하세요.

```bash
# 1. PostgreSQL 컨테이너 시작
docker-compose up -d postgres

# 2. 통합 테스트 실행 (대기 시간 후)
pytest tests/integration/ -v

# 3. 또는 pytest 마크로 통합 테스트만 실행
pytest -m integration -v
```

**참고:** 통합 테스트는 데이터베이스가 실행 중이지 않으면 자동으로 건너뜁니다(skip).

## AI 개발자 가이드

### ai_developer_guides/SLACK_NOTIFICATION_GUIDE.md
Slack 알림 유틸의 사용법, API, 테스트 가이드 포함

## 프로젝트 진행 상태

### 완료된 SPEC
- SPEC-OBSERVABILITY-001: 로그 레벨 기반 Slack 알림 시스템 (2026-01-25 완료)
- SPEC-BACKEND-002: 주문 실행 및 상태 관리 시스템
- SPEC-BACKEND-WORKER-004: 워커 아키텍처 (2026-01-25 완료)
- SPEC-BACKEND-INFRA-003: 장 시작/종료 및 상태 복구 라이프사이클 (2026-01-25 완료)

### 진행 중인 작업
- SPEC-BACKEND-API-001: 한국투자증권 OpenAPI 브로커 어댑터 (85% 완료)
  - 완료: BrokerPort 인터페이스, KIS 설정, REST/WebSocket 클라이언트
  - 완료: approval_key 발급, 토큰 자동 갱신 (스레드 안전), 해시키 생성
  - 완료: 단위 테스트 26개 (85% 커버리지, TRUST 5: 94.3%)
  - 예정: KISBrokerAdapter 완성, WebSocket 연결 통합, 통합 테스트

### 다음 단계
- KISBrokerAdapter 완성 및 WebSocket 연결 통합
- 통합 테스트 작성
- 리팩토링 및 코드 정리
- 전체 프로젝트 테스트 커버리지 개선 (목표 80%)
