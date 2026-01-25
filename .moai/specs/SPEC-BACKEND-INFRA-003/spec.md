---
id: SPEC-BACKEND-INFRA-003
version: "1.1.0"
status: "completed"
created: "2026-01-23"
updated: "2026-01-25"
author: "Alfred"
priority: "HIGH"
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-23 | Alfred | 초기 문서 작성 |
| 1.1.0 | 2026-01-25 | Alfred | 구현 완료 및 상태 업데이트 |

---

# 장 시작/종료 및 상태 복구 라이프사이클 구현

## 1. 개요

본 SPEC은 장 시작 초기화, 상태 복구, 장중 실행, 장 종료 정산을 포함하는 장 라이프사이클을 구현하는 요구사항을 정의합니다. DB와 브로커 상태 비교, 미체결 주문 복구, 포지션 재계산을 포함합니다.

## 2. 시스템 컨텍스트

### 2.1 내부 의존성

| 의존성 | 설명 |
|--------|------|
| BrokerPort | 브로커 어댑터 인터페이스 |
| OrderService | 주문 생성/전송/조회 |
| PositionService | 포지션 계산/조회 |
| EventBus | 이벤트 발행/구독 |

### 2.2 외부 인터페이스

| 인터페이스 | 책임 |
|------------|------|
| MarketLifecycleService | 장 시작/종료/복구 유스케이스 |
| StateRecoveryService | 상태 복구 로직 |
| RiskService | 리스크 가드레일 초기화 |

---

# Event-Driven Requirements (이벤트 주도 요구사항)

### ED-001: 장 시작 이벤트
**설명:** 장 시작 시그널 수신 (08:30:00 KST)

**트리거:** 스케줄러 또는 수동 트리거

**동작:**
1. MarketOpenEvent 발행
2. 장 시작 프로세스 트리거 (WH-001 참조)
3. 초기화 완료 시 MarketReadyEvent 발행

**출력:**
- MarketOpenEvent, MarketReadyEvent
- 시스템 상태: READY

---

### ED-002: 장 종료 이벤트
**설명:** 장 종료 시그널 수신 (15:30:00 KST)

**트리거:** 스케줄러 또는 수동 트리거

**동작:**
1. MarketCloseEvent 발행
2. 장 종료 프로세스 트리거 (WH-002 참조)
3. 정산 완료 시 MarketClosedEvent 발행

**출력:**
- MarketCloseEvent, MarketClosedEvent
- 시스템 상태: CLOSED

---

### ED-003: 상태 복구 완료 이벤트
**설명:** 장 시작 중 상태 복구 완료

**트리거:** StateRecoveryService.recover() 성공

**동작:**
1. StateRecoveredEvent 발행
2. 복구 결과 기록 (DB/브로커 일치/불일치 수)

**출력:**
- StateRecoveredEvent

---

### ED-004: 미체결 주문 복구 이벤트
**설명:** 장 시작 중 미체결 주문 복구

**트리거:** StateRecoveryService.recover() → 브로커 주문 상태 조회

**동작:**
1. DB 미체결 주문 조회 (status: SENT, PARTIAL)
2. 브로커 주문 상태 조회
3. 상태 불일치 시 동기화
4. UnfilledOrdersRecoveredEvent 발행

**출력:**
- UnfilledOrdersRecoveredEvent

---

# When-Then Requirements (조건-결과 요구사항)

### WT-001: 장 시작 초기화 완료 시 유니버스 확정
**When:** 장 시작 프로세스 완료

**Then:**
1. 유니버스 확정 (DB 저장 종목 리스트)
2. 전략 파라미터 로드 (ACTIVE 상태)
3. 리스크 가드레일 초기화
4. 실시간 이벤트 등록 (호가, 체결, 주문 상태)
5. 시스템 상태 READY로 전환

**검증:**
- 유니버스 리스트 조회 가능
- 전략 파라미터 조회 가능
- 리스크 제한값 적용됨

---

### WT-002: DB/브로커 상태 비교 후 브로커 우선
**When:** 상태 복구 중 DB와 브로커 상태 다름

**Then:**
1. 브로커 상태를 우선 기준으로 채택
2. DB 상태 업데이트
3. 불일치 이벤트 기록 (INFO 레벨)
4. 불일치 주문 ID 기록

**검증:**
- DB 상태가 브로커 상태와 일치
- 불일치 이력 기록됨

---

### WT-003: 미체결 주문 복구 실패 시 거래 중지
**When:** 미체결 주문 복구 중 치명적 오류 발생

**Then:**
1. 복구 중단
2. 시스템 상태 STOPPED로 전환
3. StopModeEvent 발행 (ERROR 레벨)
4. events 테이블에 로깅

**검증:**
- 주문 전송 차단됨
- 감시/기록만 수행됨

---

### WT-004: 장 마감 정산 시 포지션 스냅샷 생성
**When:** 장 종료 시

**Then:**
1. 모든 포지션 조회
2. 현재 시간 포지션 스냅샷 생성
3. 일일 정산 계산 (실현 손익, 평가 손익)
4. DailySettlementEvent 발행

**검증:**
- 포지션 스냅샷 기록됨
- 일일 정산값 계산됨

---

# Wherewithal Requirements (자원/환경 요구사항)

### WH-001: 장 시간 설정
**필요 환경:**
- 장 시작 시간: 08:30:00 KST (default)
- 장 종료 시간: 15:30:00 KST (default)
- 시간대: Asia/Seoul

**구현:**
- 환경 변수 또는 설정 파일로 설정 가능
- 동일 프로세스 내에서 스케줄러 실행

---

### WH-002: PostgreSQL 상태 조회
**필요 자원:**
- orders 테이블 (미체결 주문 조회)
- fills 테이블 (체결 기록)
- positions 테이블 (포지션 스냅샷)
- events 테이블 (이벤트 로그)

**제약조건:**
- 트랜잭션 내에서 상태 조회
- 일관성 보장

---

### WH-003: 브로커 상태 조회
**필요 자원:**
- BrokerPort.get_orders() (미체결 주문 조회)
- BrokerPort.get_cash() (예수금 조회)

**제약조건:**
- 인증 완료 상태
- 네트워크 연결 안정

---

# Optional Requirements (선택 요구사항)

### OP-001: 장 마감 후 매매일지 생성
**설명:** 장 종료 후 AI 배치 작업으로 매매일지 생성

**구현 옵션:**
- AI 모델 API 호출
- trade_journals 테이블에 저장
- 다음 장 시작 전 승인 필요

---

### OP-002: 장 마감 후 전략 파라미터 생성
**설명:** 장 종료 후 AI 배치 작업으로 다음 날 전략 파라미터 생성

**구현 옵션:**
- AI 모델 API 호출
- strategy_param_drafts 테이블에 저장
- 다음 장 시작 전 승인 필요

---

# Ubiquitous Requirements (전반적 요구사항)

### UB-001: 시스템 상태

```
OFFLINE → INITIALIZING → READY → TRADING → CLOSING → CLOSED → INITIALIZING → ...
        ↓
      STOPPED
```

**특징:**
- 상태 전이는 단방향 (OFFLINE → INITIALIZING → READY → TRADING)
- STOPPED는 예외 상태 (수동 재시작 필요)

---

### UB-002: 로깅
**모든 라이프사이클 이벤트에 대해:**
- 장 시작/종료 로그
- 상태 복구 로그 (조회된 미체결 주문 수, 불일치 수)
- 미체결 주문 복구 로그
- 장 마감 정산 로그
- 에러 발생 시 스택 트레이스
- 로그 레벨: INFO (정상), WARN (불일치), ERROR (실패)

---

### UB-003: 오류 처리
**표준 예외 계층구조:**
```
LifecycleError
├── MarketOpenError
├── MarketCloseError
├── StateRecoveryError
└── StopModeError
```

**모든 라이프사이클 동작은 try-except로 감싸고 LifecycleError 또는 하위 예외 발생**

---

### UB-004: 거래 중지 모드
**특징:**
- 주문 전송 차단
- 감시/기록만 수행
- WebSocket 유지 (호가/체결 수신)
- 수동 재시작 필요

---

## 3. 데이터 모델

### 3.1 SystemState (Domain)

```python
@dataclass
class SystemState:
    state: SystemState  # OFFLINE, INITIALIZING, READY, TRADING, CLOSING, CLOSED, STOPPED
    market_open_at: Optional[datetime]
    market_closed_at: Optional[datetime]
    last_recovery_at: Optional[datetime]
    recovery_status: str  # SUCCESS, FAILED, PARTIAL
    recovery_details: dict
```

### 3.2 DailySettlement (Domain)

```python
@dataclass
class DailySettlement:
    id: int
    trade_date: date
    realized_pnl: Decimal  # 실현 손익
    unrealized_pnl: Decimal  # 평가 손익
    total_pnl: Decimal  # 총 손익
    positions_snapshot: JSONB
    created_at: datetime
```

## 4. 서비스 인터페이스

### 4.1 MarketLifecycleService

```python
from abc import ABC, abstractmethod

class MarketLifecycleService(ABC):
    @abstractmethod
    def open_market(self) -> bool:
        pass

    @abstractmethod
    def close_market(self) -> bool:
        pass

    @abstractmethod
    def get_system_state(self) -> SystemState:
        pass
```

### 4.2 StateRecoveryService

```python
class StateRecoveryService(ABC):
    @abstractmethod
    def recover(self) -> RecoveryResult:
        pass

    @abstractmethod
    def sync_unfilled_orders(self) -> int:
        pass

    @abstractmethod
    def recalculate_positions(self) -> int:
        pass
```

## 5. 장 시작 프로세스 (WH-001 상세)

```
1. 설정 로드
   ├── 환경 변수 확인 (MODE, DB_URL, KIS_APP_KEY, KIS_APP_SECRET)
   └── 장 시간 확인 (market_open_at, market_close_at)

2. 인증
   ├── REST 인증 (get_access_token)
   └── WebSocket 연결 (connect_websocket)

3. 계좌 확인
   ├── 계좌 리스트 확인 (get_accounts)
   └── 예수금 확인 (get_cash)

4. 전략 파라미터 로드
   └── 오늘 날짜 + ACTIVE 파라미터 조회

5. 상태 복구
   ├── DB 미체결 주문 조회
   ├── 브로커 주문 상태 조회
   ├── 상태 불일치 시 동기화
   └── 포지션 재계산

6. 리스크 가드레일 초기화
   ├── 일 손실 한도 로드
   ├── 종목별 최대 노출 로드
   └── 총 포지션 수 로드

7. 유니버스 확정
   ├── DB 저장 종목 리스트 로드
   └── 한국투자증권 종목정보 마스터파일 최신화 여부 확인

8. 실시간 이벤트 등록
   ├── 체결 구독 (subscribe_executions)
   ├── 주문 상태 구독
   └── 호가 구독 (subscribe_quotes)

9. 시스템 상태 READY로 전환
   └── MarketReadyEvent 발행
```

## 6. 장 종료 프로세스 (WH-002 상세)

```
1. 시스템 상태 CLOSING으로 전환
   └── MarketCloseEvent 발행

2. 미체결 주문 취소 확인
   ├── 미체결 주문 조회
   ├── 옵션: 모두 취소 (cancel_order)
   └── 옵션: 그대로 두기 (다음 장 복구)

3. 포지션 스냅샷 생성
   ├── 모든 포지션 조회
   └── 현재 시간 포지션 스냅샷 생성

4. 일일 정산 계산
   ├── 실현 손익 계산
   ├── 평가 손익 계산
   └── 총 손익 계산

5. DailySettlementEvent 발행
   └── 일일 정산 기록 저장

6. 실시간 이벤트 구독 해제
   ├── 체결 구독 해제
   ├── 주문 상태 구독 해제
   └── 호가 구독 해제

7. WebSocket 연결 종료
   └── disconnect_websocket

8. 시스템 상태 CLOSED로 전환
   └── MarketClosedEvent 발행
```

## 7. 구현 우선순위

| Phase | 기능 | 우선순위 |
|-------|------|----------|
| 1 | MarketLifecycleService 기본 구현 | HIGH |
| 1 | 장 시작 프로세스 구현 | HIGH |
| 2 | 상태 복구 구현 | HIGH |
| 2 | 미체결 주문 복구 구현 | HIGH |
| 3 | 장 종료 프로세스 구현 | MEDIUM |
| 3 | 포지션 스냅샷 생성 | MEDIUM |
| 4 | 스케줄러 통합 | MEDIUM |
| 4 | 거래 중지 모드 | LOW |
