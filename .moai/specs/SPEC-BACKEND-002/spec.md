---
id: SPEC-BACKEND-002
version: "1.0.0"
status: "completed"
created: "2026-01-23"
updated: "2026-01-23"
author: "Alfred"
priority: "HIGH"
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-23 | Alfred | 초기 문서 작성 |
| 1.0.0 | 2026-01-23 | Alfred | 구현 완료 - OrderService, PositionService, idempotency, fill processing |

---

# 주문 실행 및 상태 관리 시스템 구현

## 1. 개요

본 SPEC은 주문 생성, 전송, 상태 추적, 포지션 관리를 위한 주문 실행 시스템을 구현하는 요구사항을 정의합니다. idempotency key로 중복 방지, DB 단일 원본 원칙, 체결 시 포지션 자동 업데이트를 포함합니다.

## 2. 시스템 컨텍스트

### 2.1 내부 의존성

| 의존성 | 설명 |
|--------|------|
| BrokerPort | 브로커 어댑터 인터페이스 |
| PostgreSQL | 주문/체결/포지션 저장소 |
| EventBus | 이벤트 발행/구독 |

### 2.2 외부 인터페이스

| 인터페이스 | 책임 |
|------------|------|
| OrderService | 주문 생성/전송/조회 |
| FillProcessor | 체결 이벤트 처리 |
| PositionCalculator | 포지션 재계산 |

---

# Event-Driven Requirements (이벤트 주도 요구사항)

### ED-001: 주문 생성 요청 이벤트
**설명:** 전략에서 주문 생성 요청 수신

**트리거:** StrategySignal (BUY/SELL)

**동작:**
1. idempotency_key 생성 (UUID 또는 strategy_id + timestamp)
2. OrderRequest 생성
3. OrderService.create_order() 호출

**출력:**
- OrderCreatedEvent 발행
- 주문 DB 레코드 생성 (status: NEW)

---

### ED-002: 주문 전송 완료 이벤트
**설명:** 브로커에 주문 전송 완료

**트리거:** broker.place_order() 성공

**동작:**
1. broker_order_id 저장
2. 주문 상태 업데이트 (NEW → SENT)
3. OrderSentEvent 발행

**출력:**
- 주문 상태 DB 업데이트

---

### ED-003: 체결 이벤트 수신
**설명:** 브로커로부터 체결 알림 수신

**트리거:** FillEvent (WebSocket 또는 Polling)

**동작:**
1. fills 테이블에 체결 레코드 생성
2. 해당 주문의 채결 누적 계산
3. 주문 상태 업데이트 (SENT → PARTIAL 또는 FILLED)
4. 포지션 업데이트 트리거 (ED-004)

**출력:**
- FillRecordedEvent 발행

---

### ED-004: 포지션 업데이트 이벤트
**설명:** 체결 발생 시 포지션 재계산

**트리거:** FillRecordedEvent

**동작:**
1. 해당 종목의 전체 체결 기록 조회
2. 수량 평균가 재계산
3. positions 테이블 업서트
4. PositionUpdatedEvent 발행

**출력:**
- 포지션 DB 업데이트

---

### ED-005: 주문 거부/취소 이벤트
**설명:** 브로커에서 주문 거부 또는 취소 확인

**트리거:** 브로커 응답 (REJECTED, CANCELED)

**동작:**
1. 주문 상태 업데이트 (SENT → REJECTED 또는 CANCELED)
2. OrderCanceledEvent 또는 OrderRejectedEvent 발행
3. events 테이블에 로깅

**출력:**
- 주문 상태 DB 업데이트

---

# When-Then Requirements (조건-결과 요구사항)

### WT-001: idempotency_key 중복 시 기존 주문 반환
**When:** 동일한 idempotency_key로 주문 생성 요청

**Then:**
1. 기존 주문 레코드 조회
2. 기존 주문 정보 반환 (새 주문 생성하지 않음)
3. IdempotencyConflictEvent 발행 (WARN 레벨)

**검증:** 중복 요청 시 새 주문이 생성되지 않음

---

### WT-002: 체결 누적 시 주문 상태 업데이트
**When:** 체결 이벤트 수신 시 체결 수량 누적이 주문 수량에 도달

**Then:**
1. 주문 상태 PARTIAL → FILLED로 업데이트
2. OrderFilledEvent 발행
3. 포지션 업데이트 트리거 (ED-004)

**검증:** 체결 완료 시 주문 상태가 FILLED로 변경됨

---

### WT-003: 리스크 검증 실패 시 주문 전송 차단
**When:** 주문 생성 후 리스크 검증 실패

**Then:**
1. 주문 상태 REJECTED로 설정
2. 브로커 전송하지 않음
3. RiskViolationEvent 발행
4. events 테이블에 로깅 (WARN 레벨)

**검증:** 리스크 위반 시 주문이 전송되지 않음

---

### WT-004: DB 트랜잭션 실패 시 롤백
**When:** 주문/체결 저장 중 DB 오류 발생

**Then:**
1. 진행 중인 모든 DB 변경 롤백
2. 주문 상태 ERROR로 설정 (가능한 경우)
3. DatabaseError 발생
4. events 테이블에 로깅 (ERROR 레벨)

**검증:** 부분적 업데이트 방지

---

### WT-005: 브로커 주문 상태 불일치 시 동기화
**When:** DB 주문 상태와 브로커 주문 상태 다름

**Then:**
1. 브로커 상태를 우선 기준으로 채택
2. DB 상태 업데이트
3. StateSyncEvent 발행
4. events 테이블에 로깅 (INFO 레벨)

**검증:** 브로커 상태로 DB 동기화됨

---

# Wherewithal Requirements (자원/환경 요구사항)

### WH-001: PostgreSQL 스키마
**필요 테이블:**
- `orders`: 주문 상태 (DB 단일 원본)
- `fills`: 체결 기록 (append-only)
- `positions`: 포지션 스냅샷
- `events`: 이벤트 로그

**제약조건:**
- `orders.idempotency_key` UNIQUE 제약
- `orders.broker_order_id` UNIQUE 제약 (nullable)
- `fills.broker_fill_id` UNIQUE 제약 (nullable)
- 모든 테이블에 `created_at`, `updated_at` (TIMESTAMPTZ)

---

### WH-002: idempotency_key 생성
**필요 로직:**
- UUID v4 사용 권장
- 또는 `strategy_id + date + sequence_number` 패턴
- 전역 고유성 보장

**검증:** 동일 키 생성 확률 무시 가능 수준

---

### WH-003: 트랜잭션 관리
**필요 환경:**
- PostgreSQL 트랜잭션 지원
- ACID 보장
- 동시성 제어 (row-level lock 필요시)

**구현:**
- 주문 생성/전송/상태 업데이트는 단일 트랜잭션
- 포지션 업데이트는 별도 트랜잭션

---

# Optional Requirements (선택 요구사항)

### OP-001: 주문 수정 (정정) 지원
**설명:** 일부 체결된 주문의 남은 수량 정정

**구현 옵션:**
- 브로커 정정 API 활용
- 원 주문 취소 + 새 주문 생성 방식

---

### OP-002: 일괄 주문 지원
**설명:** 여러 종목에 대해 한 번에 주문 전송

**구현 옵션:**
- place_orders() 메서드 추가
- 각 주문별 idempotency_key 유지

---

# Ubiquitous Requirements (전반적 요구사항)

### UB-001: 주문 상태 전이 규칙

```
NEW → SENT → PARTIAL → FILLED
NEW → SENT → CANCELED
NEW → SENT → REJECTED
NEW → SENT → ERROR
```

**특징:**
- 상태 전이는 단방향 (되돌릴 수 없음)
- 상태 전이는 DB 원칙 준수

---

### UB-002: 로깅
**모든 주문/체결 동작에 대해:**
- 주문 생성/전송/상태 변경 로그
- 체결 수신/기록 로그
- 포지션 업데이트 로그
- 에러 발생 시 스택 트레이스
- 로그 레벨: INFO (정상), WARN (리스크 위반), ERROR (실패)

---

### UB-003: 오류 처리
**표준 예외 계층구조:**
```
OrderError
├── IdempotencyConflictError
├── RiskViolationError
├── OrderStatusError
└── DatabaseError
```

**모든 주문 관련 동작은 try-except로 감싸고 OrderError 또는 하위 예외 발생**

---

### UB-004: DB 단일 원본
**주문 상태는 DB가 단일 원본:**
- 브로커 상태를 참고하되 DB가 최종 결정권
- 상태 복구 시 브로커 우선 적용 후 DB 동기화
- 상태 전이는 DB 트랜잭션 내에서만 발생

---

## 3. 데이터 모델

### 3.1 Order (Domain)

```python
@dataclass
class Order:
    id: int
    broker_order_id: Optional[str]
    idempotency_key: str
    symbol: str
    side: OrderSide  # BUY, SELL
    order_type: OrderType  # MARKET, LIMIT
    qty: Decimal
    price: Optional[Decimal]  # 필수 for LIMIT
    status: OrderStatus  # NEW, SENT, PARTIAL, FILLED, CANCELED, REJECTED, ERROR
    filled_qty: Decimal  # 체결 누적 수량
    avg_fill_price: Optional[Decimal]  # 평균 체결가
    requested_at: datetime
    created_at: datetime
    updated_at: datetime
```

### 3.2 Fill (Domain)

```python
@dataclass
class Fill:
    id: int
    order_id: int  # orders.id 참조
    broker_fill_id: Optional[str]
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    filled_at: datetime
    created_at: datetime
    updated_at: datetime
```

### 3.3 Position (Domain)

```python
@dataclass
class Position:
    id: int
    symbol: str
    qty: Decimal  # 보유 수량 (양수: 롱, 음수: 숏)
    avg_price: Decimal  # 평균 단가
    created_at: datetime
    updated_at: datetime
```

### 3.4 OrderRequest (DTO)

```python
@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Optional[Decimal]
    idempotency_key: str
```

## 4. 서비스 인터페이스

### 4.1 OrderService

```python
from abc import ABC, abstractmethod

class OrderService(ABC):
    @abstractmethod
    def create_order(self, request: OrderRequest) -> Order:
        pass

    @abstractmethod
    def send_order(self, order_id: int) -> bool:
        pass

    @abstractmethod
    def cancel_order(self, order_id: int) -> bool:
        pass

    @abstractmethod
    def get_order(self, order_id: int) -> Optional[Order]:
        pass

    @abstractmethod
    def get_pending_orders(self) -> List[Order]:
        pass

    @abstractmethod
    def process_fill(self, fill_event: FillEvent) -> Fill:
        pass
```

### 4.2 PositionService

```python
class PositionService(ABC):
    @abstractmethod
    def calculate_position(self, symbol: str) -> Position:
        pass

    @abstractmethod
    def update_position(self, fill: Fill) -> Position:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        pass

    @abstractmethod
    def get_all_positions(self) -> List[Position]:
        pass
```

## 5. 구현 우선순위

| Phase | 기능 | 우선순위 |
|-------|------|----------|
| 1 | OrderService 기본 구현 (create, get) | HIGH |
| 1 | idempotency_key 중복 방지 | HIGH |
| 2 | 주문 전송 (send_order) | HIGH |
| 2 | 체결 처리 (process_fill) | HIGH |
| 3 | 포지션 계산 및 업데이트 | HIGH |
| 3 | 주문 상태 전이 로직 | HIGH |
| 4 | 리스크 검증 통합 | MEDIUM |
| 4 | 주문 취소 (cancel_order) | MEDIUM |
| 5 | 상태 동기화 | LOW |
