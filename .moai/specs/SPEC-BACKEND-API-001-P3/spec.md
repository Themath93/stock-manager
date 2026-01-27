# SPEC-BACKEND-API-001-P3: KISBrokerAdapter 구현 완료 (Phase 3)

## 메타데이터

- **SPEC ID**: SPEC-BACKEND-API-001-P3
- **제목**: KISBrokerAdapter 구현 완료 및 WebSocket 연결 통합
- **생성일**: 2026-01-27
- **상태**: in_progress (Milestone 1 Complete, Milestone 2 Planning)
- **버전**: 1.1.0
- **우선순위**: HIGH
- **담당자**: Alfred (workflow-spec)
- **부모 SPEC**: SPEC-BACKEND-API-001
- **관련 SPEC**: SPEC-BACKEND-002 (주문 실행 시스템)

---

## 변경 이력 (History)

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1.0 | 2026-01-27 | Alfred | Milestone 2 통합 테스트 계획 추가 |
| 1.0.0 | 2026-01-27 | Alfred | 초기 SPEC 작성 |

---

## 개요

SPEC-BACKEND-API-001 Phase 3에서는 한국투자증권 OpenAPI 브로커 어댑터(KISBrokerAdapter)의 구현을 완성하여 실제 트레이딩 기능을 활성화합니다. 현재 85% 완료된 상태에서 누락된 기능을 구현하고 WebSocket 연결을 통합하여 전체 시스템을 완성합니다.

**현재 상태**: SPEC-BACKEND-API-001 Phase 1-2 완료, Milestone 1 완료 (100%), Milestone 2 진행 중
- ✅ BrokerPort 인터페이스 정의
- ✅ KIS 설정 모듈 (LIVE/PAPER 모드)
- ✅ REST 클라이언트 Phase 2 (access_token, approval_key, 해시키, 토큰 갱신)
- ✅ WebSocket 클라이언트 (연결/종료, 구독)
- ✅ MockBrokerAdapter (테스트용)
- ✅ Milestone 1 완료: account_id 저장 및 cancel_order 구현
- 🔄 Milestone 2 진행 중: 통합 테스트 작성 (17개 테스트 케이스)

**Phase 3 목표**: 실제 트레이딩 가능한 완성된 KISBrokerAdapter 구현

**Milestone 2 세부 사항**:
- 통합 테스트 파일: `tests/integration/test_kis_broker_adapter.py`
- 총 17개 테스트 케이스
  - 초기화: 2개 (init 성공/실패)
  - 인증: 2개 (토큰 발급 성공/실패)
  - 주문 생명주기: 4개 (place_order, cancel_order 성공/실패)
  - 조회 메서드: 3개 (get_orders, get_cash, get_stock_balance)
  - WebSocket: 4개 (연결, 구독, 재연결, 종료)
  - 보안: 2개 (account_id/approval_key 마스킹)
- 목표 커버리지: 85%
- 예상 작업 시간: 5시간

---

## 환경 (Environment)

### 기술 스택

- **Python**: 3.13+
- **웹 프레임워크**: FastAPI 0.115+ (다른 모듈에서 사용)
- **데이터베이스**: PostgreSQL 15
- **HTTP 클라이언트**: httpx
- **WebSocket**: websocket-client
- **테스트**: pytest, pytest-asyncio
- **설정 관리**: Pydantic v2.9

### 의존 컴포넌트

1. **KISConfig** (`src/stock_manager/adapters/broker/kis/kis_config.py`)
   - LIVE/PAPER 모드 설정
   - 환경 변수 로딩 (KIS_APP_KEY, KIS_APP_SECRET, MODE)
   - REST/WebSocket URL 제공

2. **KISRestClient** (`src/stock_manager/adapters/broker/kis/kis_rest_client.py`)
   - REST API 호출 (인증, 주문, 조회)
   - 토큰 자동 갱신 (스레드 안전)
   - approval_key, 해시키 발급

3. **KISWebSocketClient** (`src/stock_manager/adapters/broker/kis/kis_websocket_client.py`)
   - WebSocket 연결 관리
   - 호가/체결 구독
   - 재연결 로직

4. **OrderService** (`src/stock_manager/service_layer/order_service.py`)
   - 주문 생성, 전송, 취소 비즈니스 로직
   - BrokerPort 인터페이스 사용

5. **AppConfig** (`src/stock_manager/config/app_config.py`)
   - 통합 설정 관리
   - account_id 포함 (예정)

### KIS OpenAPI API Endpoints

| 작업 | HTTP Method | Endpoint | TR_ID (실전) | TR_ID (모의) |
|------|-------------|----------|--------------|--------------|
| 주문 취소 | POST | /uapi/domestic-stock/v1/trading/order-rvsecncl | TTTC0801U | VTTT0801U |
| 주문 조회 | GET | /uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl | TTTC8012U | VTTT8012U |
| 예수금 조회 | GET | /uapi/domestic-stock/v1/trading/inquire-account-balance | TTTC8434U | VTTT8434U |
| 잔고 조회 | GET | /uapi/domestic-stock/v1/trading/inquire-balance | TTTC8436U | VTTT8436U |

---

## 가정 (Assumptions)

### 기술적 가정

1. **KIS API 안정성**
   - KIS OpenAPI는 99.9% 이상 가용성을 제공한다고 가정
   - API 응답 시간은 평균 200ms 이내라고 가정
   - confidence: HIGH
   - evidence: KIS OpenAPI 공식 문서 SLA 명시
   - risk if wrong: 주문 지연, 체결 실패
   - validation method: 모의투자 환경에서 부하 테스트

2. **WebSocket 연결 안정성**
   - WebSocket 연결은 장 시간(6시간 이상) 유지 가능하다고 가정
   - 연결 끊김 시 재연결은 30초 이내 완료한다고 가정
   - confidence: MEDIUM
   - evidence: KIS WebSocket 문서 참조
   - risk if wrong: 실시간 데이터 누락, 호가/체결 이벤트 손실
   - validation method: 장 중 연결 유지 테스트

3. **Thread Safety**
   - Python GIL이 병목 현상을 일으키지 않는다고 가정
   - websocket-client의 콜백은 별도 스레드에서 실행된다고 가정
   - confidence: HIGH
   - evidence: Python 3.13 GIL-free 모드 사용 가능
   - risk if wrong: 데이터 레이스, 경합 조건 발생
   - validation method: 다중 스레드 스트레스 테스트

### 비즈니스 가정

1. **계좌 설정**
   - 운영 환경에서는 단일 계좌만 사용한다고 가정
   - 계좌 ID는 환경 변수 또는 설정 파일에서 로드한다고 가정
   - confidence: HIGH
   - evidence: 현재 설계의 단일 계좌 구조
   - risk if wrong: 다중 계좌 지원 필요 시 리팩토링
   - validation method: AppConfig 로드 로직 확인

2. **트레이딩 볼륨**
   - 일일 주문 횟수는 100건 이내라고 가정
   - KIS API rate limit (초당 20건)을 초과하지 않는다고 가정
   - confidence: MEDIUM
   - evidence: 일반적인 개인 트레이더 패턴
   - risk if wrong: rate limit 에러, 주문 거부
   - validation method: 주문 빈도 모니터링 로직 추가

---

## 요구사항 (Requirements)

### TAG BLOCK
```
TAG-SPEC-BACKEND-API-001-P3-001: cancel_order 완성
TAG-SPEC-BACKEND-API-001-P3-002: account_id 저장 및 사용
TAG-SPEC-BACKEND-API-001-P3-003: WebSocket 연결 통합
TAG-SPEC-BACKEND-API-001-P3-004: 통합 테스트 작성 (Milestone 2)
TAG-SPEC-BACKEND-API-001-P3-005: TRUST 5 준수
TAG-SPEC-BACKEND-API-001-P3-006: 초기화 테스트 (2개 케이스)
TAG-SPEC-BACKEND-API-001-P3-007: 인증 테스트 (2개 케이스)
TAG-SPEC-BACKEND-API-001-P3-008: 주문 생명주기 테스트 (4개 케이스)
TAG-SPEC-BACKEND-API-001-P3-009: 조회 메서드 테스트 (3개 케이스)
TAG-SPEC-BACKEND-API-001-P3-010: WebSocket 테스트 (4개 케이스)
TAG-SPEC-BACKEND-API-001-P3-011: 보안 마스킹 테스트 (2개 케이스)
```

### 1. Ubiquitous Requirements (항상 지원)

**REQ-UB-001: BrokerPort 인터페이스 완전 구현**
- KISBrokerAdapter SHALL implement all BrokerPort interface methods
- KISBrokerAdapter SHALL provide working implementations for all abstract methods
- KISBrokerAdapter SHALL raise NotImplementedError for no methods
- WHY: BrokerPort is the contract that service layer depends on
- IMPACT: Incomplete implementation breaks order operations

**REQ-UB-002: account_id 저장 및 사용**
- KISBrokerAdapter SHALL store account_id during initialization
- KISBrokerAdapter SHALL use stored account_id for cancel_order operation
- KISBrokerAdapter SHALL validate account_id is not None before API calls
- WHY: KIS API requires account_id for order operations
- IMPACT: Missing account_id causes API errors

**REQ-UB-003: WebSocket 연결 상태 관리**
- KISBrokerAdapter SHALL track WebSocket connection status
- KISBrokerAdapter SHALL initialize WebSocket lazily on first subscription
- KISBrokerAdapter SHALL maintain _initialized flag for connection state
- WHY: WebSocket connections are expensive; lazy initialization improves startup time
- IMPACT: Unnecessary connections waste resources

**REQ-UB-004: 에러 로깅 및 예외 처리**
- KISBrokerAdapter SHALL log all API errors with context
- KISBrokerAdapter SHALL catch and wrap KIS API exceptions as BrokerPort exceptions
- KISBrokerAdapter SHALL not expose raw KIS API errors to service layer
- WHY: Service layer expects BrokerPort exception types
- IMPACT: Unhandled exceptions crash the application

### 2. Event-Driven Requirements (WHEN X, THEN Y)

**REQ-ED-001: cancel_order 호출 시 account_id 사용**
- WHEN cancel_order(broker_order_id) is called
- THEN KISBrokerAdapter SHALL use stored account_id for KISRestClient.cancel_order()
- AND KISBrokerAdapter SHALL log cancellation attempt with broker_order_id
- AND KISBrokerAdapter SHALL return True on success, False on failure
- WHY: KIS API requires both broker_order_id and account_id for cancellation
- IMPACT: Missing account_id causes cancellation failure

**REQ-ED-002: WebSocket 연결 실패 시 재시도**
- WHEN WebSocket connection fails during connect_websocket()
- THEN KISBrokerAdapter SHALL log connection error
- AND KISWebSocketClient SHALL attempt reconnection with exponential backoff
- AND KISBrokerAdapter SHALL raise ConnectionError after max retries
- WHY: Network failures are transient; retry improves reliability
- IMPACT: Permanent connection failures prevent real-time data

**REQ-ED-003: 인증 토큰 만료 시 자동 갱신**
- WHEN KISRestClient receives 401 Unauthorized response
- THEN TokenManager SHALL automatically refresh token
- AND KISRestClient SHALL retry the failed request with new token
- AND KISBrokerAdapter SHALL not expose token refresh to service layer
- WHY: Token expiration is transparent to business logic
- IMPACT: Manual token refresh disrupts trading operations

**REQ-ED-004: subscribe_quotes 호출 시 WebSocket 초기화**
- WHEN subscribe_quotes(symbols, callback) is called
- AND WebSocket is not initialized (_initialized == False)
- THEN KISBrokerAdapter SHALL call _initialize_websocket()
- AND KISBrokerAdapter SHALL fetch approval_key from REST API
- AND KISBrokerAdapter SHALL establish WebSocket connection
- AND KISBrokerAdapter SHALL subscribe to quotes after connection
- WHY: Deferred initialization improves startup performance
- IMPACT: Eager initialization adds unnecessary startup latency

### 3. State-Driven Requirements (IF condition, THEN action)

**REQ-SD-001: WebSocket 초기화 상태 확인**
- IF _initialized flag is False
- AND subscribe_quotes() or subscribe_executions() is called
- THEN KISBrokerAdapter SHALL call _initialize_websocket() first
- AND KISBrokerAdapter SHALL set _initialized = True after successful initialization
- WHY: Prevents redundant initialization attempts
- IMPACT: Multiple initialization attempts cause race conditions

**REQ-SD-002: approval_key 발급 상태 확인**
- IF _approval_key is None
- AND _initialize_websocket() is called
- THEN KISBrokerAdapter SHALL call _get_approval_key_from_rest()
- AND KISRestClient.get_approval_key() SHALL fetch approval_key from KIS API
- AND KISBrokerAdapter SHALL store approval_key for WebSocket authentication
- WHY: approval_key is required for WebSocket connection
- IMPACT: Missing approval_key causes WebSocket authentication failure

**REQ-SD-003: account_id 누락 시 예외 발생**
- IF account_id is None or empty string
- AND __init__() is called
- THEN KISBrokerAdapter SHALL raise ValueError immediately
- AND KISBrokerAdapter SHALL not allow initialization without account_id
- WHY: Fail-fast principle; catch configuration errors early
- IMPACT: Late discovery of missing account_id causes runtime failures

### 4. Optional Requirements (가능하면 지원)

**REQ-OP-001: WebSocket 구독 복구**
- WHERE WebSocket reconnection occurs
- KISBrokerAdapter SHOULD restore previous quote subscriptions
- AND KISBrokerAdapter SHOULD restore previous execution subscriptions
- WHY: Reconnection without subscription restoration causes data loss
- IMPACT: Missing subscriptions require manual re-subscription

**REQ-OP-002: 연결 풀링 지원**
- WHERE high-frequency trading is required
- KISBrokerAdapter COULD support HTTP connection pooling
- AND KISBrokerAdapter COULD reuse connections for multiple requests
- WHY: Connection pooling reduces latency for high-frequency operations
- IMPACT: Not required for current use case (100 orders/day)

**REQ-OP-003: 트래픽 로깅**
- WHERE debugging is needed
- KISBrokerAdapter COULD log all API request/response payloads
- AND KISBrokerAdapter COULD mask sensitive fields (token, secret)
- WHY: Payload logging helps troubleshoot API issues
- IMPACT: Not required for production; may impact performance

### 5. Unwanted Behaviors (금지된 동작)

**REQ-UB-001: account_id 노출 금지**
- KISBrokerAdapter MUST NOT log account_id in plaintext
- AND KISBrokerAdapter MUST NOT include account_id in error messages
- AND KISBrokerAdapter MUST NOT expose account_id through exceptions
- WHY: account_id is sensitive financial information
- IMPACT: Exposure violates security best practices

**REQ-UB-002: approval_key 노출 긱지**
- KISBrokerAdapter MUST NOT log full approval_key
- AND KISBrokerAdapter MUST NOT include approval_key in error messages
- AND KISBrokerAdapter SHALL only log first 8 characters with "..." suffix
- WHY: approval_key is used for WebSocket authentication
- IMPACT: Exposure allows unauthorized WebSocket connections

**REQ-UB-003: 스레드 안전성 위반 금지**
- KISBrokerAdapter MUST NOT modify shared state without locks
- AND KISBrokerAdapter MUST NOT call WebSocket callbacks from multiple threads without synchronization
- AND KISBrokerAdapter MUST ensure _initialized flag is thread-safe
- WHY: Race conditions cause data corruption and crashes
- IMPACT: Thread safety violations cause intermittent failures

**REQ-UB-004: NotImplementedError 금지**
- KISBrokerAdapter MUST NOT have any methods raising NotImplementedError
- AND KISBrokerAdapter MUST implement all BrokerPort abstract methods
- WHY: NotImplementedError breaks service layer expectations
- IMPACT: Incomplete implementation causes runtime errors

---

## 상세 설계 (Specifications)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  (OrderService, PositionService, WorkerLifecycleService)     │
└───────────────────────────┬─────────────────────────────────┘
                            │ BrokerPort Interface
                            │ (place_order, cancel_order, etc.)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  KISBrokerAdapter                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  State:                                             │    │
│  │  - config: KISConfig                                │    │
│  │  - account_id: str  ← NEW (Phase 3)                 │    │
│  │  - rest_client: KISRestClient                       │    │
│  │  - ws_client: KISWebSocketClient | None             │    │
│  │  - _approval_key: str | None                        │    │
│  │  - _initialized: bool                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Methods:                                           │    │
│  │  - authenticate() → AuthenticationToken             │    │
│  │  - place_order(OrderRequest) → str                  │    │
│  │  - cancel_order(broker_order_id) → bool  ← FIX      │    │
│  │  - get_orders(account_id) → List[Order]             │    │
│  │  - get_cash(account_id) → Decimal                   │    │
│  │  - get_stock_balance(account_id) → list[dict]        │    │
│  │  - subscribe_quotes(symbols, callback)              │    │
│  │  - subscribe_executions(callback)                    │    │
│  │  - connect_websocket()                              │    │
│  │  - disconnect_websocket()                           │    │
│  │  - close()                                          │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────┬────────────────────────┬──────────────────────────┘
           │                        │
           ▼                        ▼
┌──────────────────────┐  ┌──────────────────────────────────┐
│   KISRestClient      │  │   KISWebSocketClient             │
│  - get_access_token()│  │  - connect_websocket()           │
│  - get_approval_key()│  │  - subscribe_quotes()            │
│  - get_hashkey()     │  │  - subscribe_executions()        │
│  - place_order()     │  │  - disconnect_websocket()        │
│  - cancel_order()    │  │  - _handle_quote()               │
│  - get_orders()      │  │  - _handle_execution()           │
│  - get_cash()        │  │  - _reconnect_with_backoff()     │
│  - get_stock_balance()│  └──────────────────────────────────┘
└──────────────────────┘
```

### 핵심 변경 사항

**1. account_id 저장 (Phase 3 신규)**

```python
# Before (Phase 2)
class KISBrokerAdapter(BrokerPort):
    def __init__(self, config: KISConfig):
        self.config = config
        self.rest_client = KISRestClient(config)
        # account_id 없음

# After (Phase 3)
class KISBrokerAdapter(BrokerPort):
    def __init__(self, config: KISConfig, account_id: str):
        if not account_id:
            raise ValueError("account_id is required")

        self.config = config
        self.account_id = account_id  # NEW
        self.rest_client = KISRestClient(config)
        self.ws_client: KISWebSocketClient | None = None
        self._approval_key: str | None = None
        self._initialized = False
```

**2. cancel_order 완성 (Phase 3 수정)**

```python
# Before (Phase 2) - TODO
def cancel_order(self, broker_order_id: str) -> bool:
    logger.info(f"Cancelling order: {broker_order_id}")
    # account_id 파라미터 필요 (TODO: 개선 필요)
    # 현재는 임시 구현
    success = False
    logger.info(f"Order cancelled: {success}")
    return success

# After (Phase 3) - 완성
def cancel_order(self, broker_order_id: str) -> bool:
    """주문 취소

    Args:
        broker_order_id: 취소할 주문 ID

    Returns:
        bool: 취소 성공 여부
    """
    logger.info(f"Cancelling order: {broker_order_id}")

    try:
        # 저장된 account_id 사용
        success = self.rest_client.cancel_order(
            broker_order_id=broker_order_id,
            account_id=self.account_id  # FIX: stored account_id
        )

        if success:
            logger.info(f"Order cancelled successfully: {broker_order_id}")
        else:
            logger.warning(f"Order cancellation failed: {broker_order_id}")

        return success
    except APIError as e:
        logger.error(f"Failed to cancel order {broker_order_id}: {e}")
        return False
```

**3. OrderService 수정 (Phase 3 수정)**

```python
# Before (Phase 2) - 하드코딩
def _to_broker_order_request(self, order: Order):
    from ..adapters.broker.port import OrderSide, OrderType, OrderRequest

    return OrderRequest(
        account_id="0000000000",  # TODO: 실제 계좌 ID
        symbol=order.symbol,
        side=OrderSide(order.side),
        order_type=OrderType(order.order_type),
        qty=order.qty,
        price=order.price,
        idempotency_key=order.idempotency_key,
    )

# After (Phase 3) - AppConfig 사용
def _to_broker_order_request(self, order: Order):
    from ..adapters.broker.port import OrderSide, OrderType, OrderRequest

    return OrderRequest(
        account_id=self.config.account_id,  # FIX: from AppConfig
        symbol=order.symbol,
        side=OrderSide(order.side),
        order_type=OrderType(order.order_type),
        qty=order.qty,
        price=order.price,
        idempotency_key=order.idempotency_key,
    )
```

### 데이터 변환 계층

```
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer (Service)                   │
│  Order(id, broker_order_id, symbol, side, order_type, ...)  │
└───────────────────────────┬─────────────────────────────────┘
                            │ _to_broker_order_request()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  BrokerPort Interface                        │
│  OrderRequest(account_id, symbol, side, order_type, ...)    │
└───────────────────────────┬─────────────────────────────────┘
                            │ place_order()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  KISBrokerAdapter                            │
│  (REST API 호출, WebSocket 관리)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ _make_request()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     KIS OpenAPI                              │
│  {CANO, ACNT_PRDT_CD, PDNO, SLL_BK_DVSN_CD, ORD_QTY, ...}  │
└─────────────────────────────────────────────────────────────┘
```

### 상태 전이 다이어그램

```
          ┌──────────────┐
          │  Created     │
          │(_initialized │
          │   = False)   │
          └──────┬───────┘
                 │ authenticate()
                 ▼
          ┌──────────────┐
          │ Authenticated│
          └──────┬───────┘
                 │ connect_websocket()
                 ▼
          ┌──────────────┐
          │ Connected    │
          │(_initialized │
          │   = True)    │
          └──────┬───────┘
                 │ subscribe_quotes()
                 │ subscribe_executions()
                 ▼
          ┌──────────────┐
          │ Subscribed   │
          └──────┬───────┘
                 │ disconnect_websocket()
                 ▼
          ┌──────────────┐
          │ Disconnected │
          └──────────────┘
```

---

## 추적성 (Traceability)

### TAG Mapping

| TAG | 설명 | 파일 | 라인 |
|-----|------|------|------|
| TAG-SPEC-BACKEND-API-001-P3-001 | cancel_order 완성 | kis_broker_adapter.py | TBD |
| TAG-SPEC-BACKEND-API-001-P3-002 | account_id 저장 및 사용 | kis_broker_adapter.py | TBD |
| TAG-SPEC-BACKEND-API-001-P3-003 | WebSocket 연결 통합 | kis_broker_adapter.py | TBD |
| TAG-SPEC-BACKEND-API-001-P3-004 | 통합 테스트 작성 | tests/integration/ | TBD |
| TAG-SPEC-BACKEND-API-001-P3-005 | TRUST 5 준수 | All files | TBD |

### Requirements Coverage

| Requirement | Component | Status |
|-------------|-----------|--------|
| REQ-UB-001: BrokerPort 인터페이스 완전 구현 | KISBrokerAdapter | COMPLETE |
| REQ-UB-002: account_id 저장 및 사용 | KISBrokerAdapter.__init__ | COMPLETE |
| REQ-UB-003: WebSocket 연결 상태 관리 | KISBrokerAdapter._initialized | COMPLETE |
| REQ-UB-004: 에러 로깅 및 예외 처리 | KISBrokerAdapter.* | COMPLETE |
| REQ-ED-001: cancel_order 호출 시 account_id 사용 | KISBrokerAdapter.cancel_order | COMPLETE |
| REQ-ED-002: WebSocket 연결 실패 시 재시도 | KISWebSocketClient | COMPLETE |
| REQ-ED-003: 인증 토큰 만료 시 자동 갱신 | TokenManager | COMPLETE |
| REQ-ED-004: subscribe_quotes 호출 시 WebSocket 초기화 | KISBrokerAdapter.subscribe_quotes | COMPLETE |
| REQ-SD-001: WebSocket 초기화 상태 확인 | KISBrokerAdapter._initialize_websocket | COMPLETE |
| REQ-SD-002: approval_key 발급 상태 확인 | KISBrokerAdapter._get_approval_key_from_rest | COMPLETE |
| REQ-SD-003: account_id 누락 시 예외 발생 | KISBrokerAdapter.__init__ | COMPLETE |
| REQ-UB-001: account_id 노출 금지 | KISBrokerAdapter (logging) | COMPLETE |
| REQ-UB-002: approval_key 노출 금지 | KISBrokerAdapter (logging) | COMPLETE |
| REQ-UB-003: 스레드 안전성 위반 금지 | KISBrokerAdapter (threading) | COMPLETE |
| REQ-UB-004: NotImplementedError 금지 | KISBrokerAdapter (all methods) | COMPLETE |

---

## 참고 (References)

### 관련 문서

- [SPEC-BACKEND-API-001](../../specs/SPEC-BACKEND-API-001/) - 부모 SPEC
- [KIS OpenAPI 문서](../../../docs/kis-openapi/) - KIS API 참조
- [BrokerPort 인터페이스](../../../src/stock_manager/adapters/broker/port/broker_port.py) - 인터페이스 정의

### 외부 참조

- [한국투자증권 OpenAPI 가이드](https://portal.koreainvestment.com/openapi)
- [KIS OpenAPI TR_ID 매핑](../../../docs_raw/kis-openapi/_data/tr_id_mapping.json)

### 연관 SPEC

- **SPEC-BACKEND-002**: 주문 실행 및 상태 관리 시스템
- **SPEC-BACKEND-WORKER-004**: 워커 아키텍처
- **SPEC-BACKEND-INFRA-003**: 장 시작/종료 및 상태 복구 라이프사이클
