---
id: SPEC-BACKEND-WORKER-004
version: "1.0.0"
status: "draft"
created: "2026-01-23"
updated: "2026-01-23"
author: "Alfred"
priority: "HIGH"
---

# HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-23 | Alfred | 초기 문서 작성 |

---

# 자동매매 봇 Worker 프로세스 아키텍처 구현

## 1. 개요

본 SPEC은 프로세스 분산 운영 기반 자동매매 봇의 Worker 프로세스를 구현하는 요구사항을 정의합니다. 장 중에 조건에 맞는 종목을 주기적으로 폴링하여 후보를 만들고, 조건 충족 시 매수 → 보유 중에는 매도 조건만 감시 → 무조건 당일 청산(현금화)하는 전체 흐름을 포함합니다. 한 프로세스는 한 종목만 전담하며, 여러 프로세스가 동시에 돌 때 중복 매수/상호 간섭을 방지하기 위한 소유권/락 관리 기능을 포함합니다.

## 2. 시스템 컨텍스트

### 2.1 내부 의존성

| 의존성 | 설명 |
|--------|------|
| BrokerPort | 브로커 어댑터 인터페이스 (SPEC-BACKEND-API-001) |
| OrderService | 주문 생성/전송/조회 (SPEC-BACKEND-002) |
| PostgreSQL | Worker 상태/종목 락/주문/체결 저장소 |
| EventBus | Worker 간 이벤트 발행/구독 (락 경쟁 알림) |

### 2.2 외부 인터페이스

| 인터페이스 | 책임 |
|------------|------|
| MarketDataPoller | 주기적 시세 데이터 폴링 |
| LockService | 종목 소유권(락) 원자적 관리 |
| WorkerLifecycle | 프로세스 시작/종료/상태 관리 |
| StrategyExecutor | 매수/매도 조건 평가 및 실행 |

---

# Event-Driven Requirements (이벤트 주도 요구사항)

### ED-001: Worker 시작 이벤트
**설명:** 자동매매 Worker 프로세스 시작

**트리거:** 스케줄러 또는 수동 실행

**동작:**
1. 환경/설정 로드 (계좌/모드/한도액/전략 파라미터)
2. API 인증/세션 준비 (토큰 발급/갱신, 연결 상태 점검)
3. 리스크 기본값 세팅 (일 손실 한도, 1프로세스 최대투입액, 거래 종료 시간)
4. PID/WorkerID로 DB에 Worker 상태 등록 (IDLE → SCAN)
5. WorkerStartedEvent 발행

**출력:**
- Worker 상태: IDLE/SCAN/HOLD/EXIT
- Worker 상태 DB 저장

---

### ED-002: 후보 종목 탐색 이벤트
**설명:** 주기적으로 폴링하여 매수 가능한 후보 종목 탐색

**트리거:** 주기적 타이머 (1~5초/10초/1분)

**동작:**
1. 종목 리스트 수집 (전체 종목 또는 특정 유니버스)
2. 현재가/거래량/거래대금/등락률/장중 고저/전일 고저 수집
3. 프리프로세스 필터링:
   - 최소 거래량/거래대금 미달 종목 제외
   - 스프레드/호가 공백 큰 종목 제외
4. 단기 캔들 기반 지표 계산 (이평, 돌파 등)
5. 매수 신호 판단 (전략 파라미터 적용: True/False)
6. 매수 가능 후보군 생성
7. CandidateScannedEvent 발행

**출력:**
- 매수 가능 후보 리스트
- 이벤트: CandidateScannedEvent

---

### ED-003: 종목 락 획득 시도 이벤트
**설명:** 다른 Worker가 소유하지 않은 종목의 락 획득 시도

**트리거:** 매수 신호 충족 (후보 종목 선정)

**동작:**
1. DB에서 해당 종목코드 락 조회
2. 락이 없는 경우: 원자적 등록 (종목코드 → WorkerID/PID/TTL)
3. 락이 있는 경우: 다른 Worker가 소유한 것으로 간주
4. LockAcquiredEvent 또는 LockRejectedEvent 발행
5. 락 유지: 매수 후에는 매도 완료까지 락 유지
6. 프로세스 죽음 대비: TTL/하트비트 정책 적용

**출력:**
- 락 성공: LockAcquiredEvent (종목 소유권 확보)
- 락 실패: LockRejectedEvent (다른 종목으로 continue)
- 락 정보 DB 저장

---

### ED-004: 매수 주문 실행 이벤트
**설명:** 락 획득 후 매수 주문 전송

**트리거:** LockAcquiredEvent (종목 소유권 확보)

**동작:**
1. 수량 산정: 한도액(capital_limit) / 현재가 기반, 수수료/슬리피지 감안
2. 주문 방식 결정: 시장가/지정가 중 정책 선택
3. OrderService.create_order() 호출
4. OrderService.send_order() 호출
5. 주문 상태 추적: 체결 확인까지 monitoring
6. orders/fills/positions 스냅샷 저장
7. "진입가격/진입시간/전략버전/파라미터버전" 저장
8. Worker 상태 전이: SCAN → HOLD
9. PositionEnteredEvent 발행

**출력:**
- 주문 전송 및 체결 정보
- 포지션 생성
- Worker 상태: HOLD

---

### ED-005: 보유 종목 감시 이벤트
**설명:** 매수 이후 매도 조건만 반복 감시

**트리거:** Worker 상태 HOLD

**동작 (주기적):**
1. 폴링(1~5초/10초/1분) 또는 스트리밍으로 현재가/지표 업데이트
2. 필요한 지표만 갱신 (가격/거래량/이평)
3. 매도 조건 평가:
   - 손절: -x%
   - 익절: +y%
   - 추세 훼손: 단기 이평 이탈
   - 시간 조건: 청산 시각 임박(무조건 현금화)
4. 매도 조건 충족 시 즉시 매도 주문 전송
5. 부분체결/미체결 처리 정책 적용
6. MonitoringEvent 발행

**출력:**
- 현재 포지션 상태
- 매도 조건 충족 여부
- 이벤트: MonitoringEvent

---

### ED-006: 매도 주문 실행 이벤트
**설명:** 매도 조건 충족 시 또는 강제 청산 시 매도 주문 실행

**트리거:** MonitoringEvent (매도 조건 충족) 또는 MandatoryLiquidationEvent

**동작:**
1. OrderService.create_order() 호출 (SELL)
2. OrderService.send_order() 호출
3. 체결 확인 및 fills/positions 정리
4. PnL 저장 (손익/리포트 데이터 적재)
5. 종목 락 해제
6. Worker 상태 전이: HOLD → SCAN
7. PositionExitedEvent 발행

**출력:**
- 체결/포지션 정리
- PnL 데이터
- Worker 상태: SCAN
- 종목 락 해제

---

### ED-007: 당일 강제 청산 이벤트
**설명:** 청산 시각 T-Δ(장 마감 10~15분 전)부터 무조건 현금화

**트리거:** 현재시각 >= 청산 시각

**동작:**
1. 현재 포지션 있는지 확인
2. 유동성 부족 종목은 더 일찍 청산하도록 정책 적용
3. 시장가/보수적 주문으로 강제 청산
4. 유동성 고려
5. 부분체결 재시도 로직
6. MandatoryLiquidationEvent 발행
7. ED-006 매도 주문 실행 이벤트 트리거

**출력:**
- 강제 청산 주문 전송
- 이벤트: MandatoryLiquidationEvent

---

### ED-008: Worker 종료 및 요약 저장 이벤트
**설명:** 장 종료 시 일일 성과 저장 및 종료

**트리거:** 장 종료 시그널 또는 명시적 종료

**동작:**
1. 일일 요약 저장:
   - 일 손익/승률/평균손익/최대손실 등 지표 적재
   - 다음날 파라미터 개선을 위한 데이터 묶음 저장
   - 어떤 필터가 유효했는지
   - 유동성 부족으로 불리한 체결이 있었는지
   - 강제 청산으로 손실 확대 여부 등
2. Worker 상태 전이: SCAN/IDLE → EXIT
3. WorkerTerminatedEvent 발행
4. 프로세스 정상 종료

**출력:**
- 일일 요약 데이터
- Worker 상태: EXIT

---

# When-Then Requirements (조건-결과 요구사항)

### WT-001: 현재 포지션 없는 경우 후보 탐색
**When:** Worker 시작 시 현재 포지션이 없는 경우

**Then:**
1. Worker 상태 IDLE → SCAN으로 전이
2. ED-002 후보 종목 탐색 이벤트 트리거
3. 주기적 폴링 시작

**검증:** 포지션 없는 경우 후보 탐색 모드로 진입

---

### WT-002: 현재 포지션 있는 경우 보유 감시 모드
**When:** Worker 시작 시 현재 포지션이 있는 경우

**Then:**
1. Worker 상태 IDLE → HOLD로 전이
2. ED-005 보유 종목 감시 이벤트 트리거
3. 매도 조건만 감시 (매수 불가)
4. 해당 종목 락 확인 및 유지

**검증:** 포지션 있는 경우 매도 감시 모드로 진입

---

### WT-003: 종목 락 획득 성공 시 매수 진행
**When:** 후보 종목 선정 후 DB 락 획득 시도 성공

**Then:**
1. ED-004 매수 주문 실행 이벤트 트리거
2. 한도액 기반 수량 산정
3. 주문 전송 및 체결 확인
4. Worker 상태 SCAN → HOLD 전이
5. 종목 소유권 유지

**검증:** 락 획득 후 매수 주문 전송 성공

---

### WT-004: 종목 락 이미 소유 중인 경우 다른 종목 탐색
**When:** 후보 종목 선정 후 DB 락 획득 시도 실패 (다른 Worker 소유)

**Then:**
1. LockRejectedEvent 발행 (로그 기록)
2. 해당 종목 skip
3. ED-002 후보 종목 탐색 이벤트 재시도 (다른 종목)
4. Worker 상태 유지 (SCAN)

**검증:** 락 경쟁 시 다른 종목으로 계속 탐색

---

### WT-005: 매도 조건 충족 시 즉시 매도
**When:** 매도 조건 (손절/익절/추세훼손) 충족

**Then:**
1. ED-006 매도 주문 실행 이벤트 트리거
2. 즉시 매도 주문 전송
3. 체결 확인 후 포지션 정리
4. PnL 저장
5. 종목 락 해제
6. Worker 상태 HOLD → SCAN 전이

**검증:** 매도 조건 충족 시 즉시 매도 실행

---

### WT-006: 청산 시각 임박 시 무조건 강제 청산
**When:** 현재시각 >= 청산 시각 (장 마감 10~15분 전)

**Then:**
1. ED-007 당일 강제 청산 이벤트 트리거
2. 현재 포지션 있는지 확인
3. 시장가/보수적 주문으로 강제 청산
4. 유동성 고려 및 부분체결 재시도
5. 체결 완료 시 종목 락 해제
6. Worker 상태 HOLD → SCAN 전이

**검증:** 청산 시각 임박 시 무조건 현금화

---

### WT-007: 프로세스 장애 시 락 회수
**When:** Worker 하트비트 중단 또는 TTL 만료

**Then:**
1. 해당 Worker가 보유한 모든 락 회수
2. 락 회수 이벤트 발행
3. LockReleasedEvent 발행 (다른 Worker가 해당 종목 차지 가능)
4. Worker 상태 EXIT로 설정

**검증:** 장애 Worker의 락이 자동으로 회수되어 다른 Worker가 차지 가능

---

# Wherewithal Requirements (자원/환경 요구사항)

### WH-001: PostgreSQL 스키마
**필요 테이블:**
- `workers`: Worker 상태 (worker_id, pid, status, capital_limit, current_symbol)
- `stock_locks`: 종목 소유권/락 (symbol, worker_id, locked_at, ttl, heartbeat)
- `orders`: 주문 상태 (SPEC-BACKEND-002 참조)
- `fills`: 체결 기록 (SPEC-BACKEND-002 참조)
- `positions`: 포지션 스냅샷 (SPEC-BACKEND-002 참조)
- `daily_summaries`: 일일 요약 (date, pnl, win_rate, avg_pnl, max_loss)

**제약조건:**
- `stock_locks.symbol` UNIQUE 제약 (한 종목 = 한 Worker)
- `stock_locks.worker_id` 외래키 (workers 테이블)
- `stock_locks.ttl` 타임스탬프 (만료 시 자동 회수)
- 모든 테이블에 `created_at`, `updated_at` (TIMESTAMPTZ)

---

### WH-002: Worker 상태 머신
**필요 상태:**
```
IDLE   → 초기 상태, 아무 종목 보유하지 않음
SCAN   → 후보 종목 탐색 중
HOLD   → 종목 보유 중 (매도 조건만 감시)
EXIT    → 종료 또는 장애
```

**상태 전이 규칙:**
- IDLE → SCAN: 시작 또는 매도 완료 후
- SCAN → HOLD: 매수 체결 후
- HOLD → SCAN: 매도 완료 후
- 모든 상태 → EXIT: 장 종료 또는 장애

---

### WH-003: 락 원자성 보장
**필요 환경:**
- PostgreSQL row-level lock 또는 SELECT FOR UPDATE
- 락 획득 원자적 연산 (SELECT → INSERT 또는 실패)
- TTL(만료 시간) 기반 자동 회수
- 하트비트 기반 생존 확인

**구현:**
- 락 획득: BEGIN TRANSACTION → SELECT FOR UPDATE → INSERT ON CONFLICT → COMMIT
- 락 회수: TTL 만료 시 자동으로 삭제, 하트비트 타임아웃 시 삭제
- 락 갱신: Worker 상태 HOLD 시 주기적으로 heartbeat_at 업데이트

---

### WH-004: 주기적 폴링 설정
**필요 환경:**
- 폴링 간격 설정 (POLL_INTERVAL: 1~60초)
- 유니버스 설정 (전체 종목 또는 특정 종목군)
- 필터링 파라미터 (최소 거래량, 최소 거래대금)

**구현:**
- 독립 스레드 또는 asyncio로 주기적 태스크 실행
- 폴링 중 락 획득 실패 시 다음 종목 즉시 시도
- 폴링 중 오류 발생 시 로깅 후 계속 (resilience)

---

# Optional Requirements (선택 요구사항)

### OP-001: WebSocket 스트리밍 대체
**설명:** 주기적 폴링 대신 WebSocket 스트리밍으로 실시간 데이터 수신

**구현 옵션:**
- 폴링: 단순 구현, API 호출 비용 발생
- 스트리밍: 실시간성 우수, WebSocket 연결 유지 필요

---

### OP-002: 전략 파라미터 동적 갱신
**설명:** 운영 중 전략 파라미터(손절/익절/필터) 동적 갱신

**구현 옵션:**
- DB 테이블 또는 설정 파일에서 파라미터 reload
- Worker가 주기적으로 파라미터 체크
- 파라미터 변경 시 즉시 적용 (다음 타이밍부터)

---

# Ubiquitous Requirements (전반적 요구사항)

### UB-001: Worker 상태 추적
**모든 Worker 동작에 대해:**
- Worker 시작/종료 로그
- 상태 전이 로그 (IDLE → SCAN → HOLD → SCAN → EXIT)
- 락 획득/해제 로그
- 주문/체결 로그
- PnL 로그
- 로그 레벨: INFO (정상), WARN (락 경쟁), ERROR (장애)

---

### UB-002: 오류 처리
**표준 예외 계층구조:**
```
WorkerError
├── LockAcquisitionError
├── OrderExecutionError
├── PositionError
└── WorkerTerminationError
```

**모든 Worker 관련 동작은 try-except로 감싸고 WorkerError 또는 하위 예외 발생**

---

### UB-003: 리스크 관리
**일 손실 한도:**
- 한 Worker의 일일 손실 한도 설정
- 한도 도달 시 매수 중지, 보유 종목만 청산
- 손실 한도 초과 시 Critical 로그 및 알림

**1프로세스 최대투입액:**
- Worker당 한도액(capital_limit) 설정
- 한도액 초과 주문 차단

---

### UB-004: 다중 Worker 협력
**여러 Worker 동시 실행 시:**
- 종목 락을 통한 중복 매수 방지
- LockRejectedEvent 시 로깅 및 다른 종목 시도
- Worker 간 이벤트 버스로 상태 공유 (선택)
- Worker 장애 시 다른 Worker에게 알림 (선택)

---

## 3. 데이터 모델

### 3.1 WorkerStatus (Domain)

```python
@dataclass
class WorkerStatus:
    worker_id: str  # UUID 또는 PID 기반 고유 ID
    pid: int  # 프로세스 ID
    status: WorkerState  # IDLE, SCAN, HOLD, EXIT
    capital_limit: Decimal  # 한도액
    current_symbol: Optional[str]  # 현재 보유 종목 (락 보유 중)
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime  # 하트비트 타임스탬프
```

### 3.2 StockLock (Domain)

```python
@dataclass
class StockLock:
    symbol: str
    worker_id: str  # workers.worker_id 참조
    locked_at: datetime
    ttl: datetime  # 만료 시각
    heartbeat_at: datetime  # 하트비트
    created_at: datetime
    updated_at: datetime
```

### 3.3 DailySummary (Domain)

```python
@dataclass
class DailySummary:
    id: int
    date: date
    pnl: Decimal  # 일일 손익
    win_rate: float  # 승률
    avg_pnl: Decimal  # 평균 손익
    max_loss: Decimal  # 최대 손실
    trades_count: int  # 거래 횟수
    created_at: datetime
    updated_at: datetime
```

### 3.4 Candidate (Domain)

```python
@dataclass
class Candidate:
    symbol: str
    price: Decimal
    volume: Decimal
    value: Decimal  # 거래대금
    change_rate: float  # 등락률
    indicators: dict  # 지표 (이평, 돌파 등)
    signal: bool  # 매수 신호 여부
    score: float  # 신호 점수 (우선순위)
    scanned_at: datetime
```

## 4. 서비스 인터페이스

### 4.1 WorkerLifecycle

```python
from abc import ABC, abstractmethod
from typing import Optional

class WorkerLifecycle(ABC):
    @abstractmethod
    def start_worker(self, worker_id: str, capital_limit: Decimal) -> WorkerStatus:
        pass

    @abstractmethod
    def stop_worker(self, worker_id: str) -> bool:
        pass

    @abstractmethod
    def get_worker_status(self, worker_id: str) -> Optional[WorkerStatus]:
        pass

    @abstractmethod
    def update_heartbeat(self, worker_id: str) -> bool:
        pass
```

### 4.2 LockService

```python
class LockService(ABC):
    @abstractmethod
    def acquire_lock(self, symbol: str, worker_id: str, ttl: timedelta) -> bool:
        """종목 락 획득 시도, 성공 시 True, 실패 시 False"""
        pass

    @abstractmethod
    def release_lock(self, symbol: str) -> bool:
        pass

    @abstractmethod
    def renew_lock(self, symbol: str, ttl: timedelta) -> bool:
        pass

    @abstractmethod
    def get_locked_symbols(self) -> list[str]:
        pass
```

### 4.3 MarketDataPoller

```python
class MarketDataPoller(ABC):
    @abstractmethod
    def poll_candidates(self, universe: list[str]) -> list[Candidate]:
        """후보 종목 탐색"""
        pass

    @abstractmethod
    def poll_position(self, symbol: str) -> dict:
        """현재 포지션 데이터 갱신"""
        pass
```

### 4.4 StrategyExecutor

```python
class StrategyExecutor(ABC):
    @abstractmethod
    def evaluate_buy_signal(self, candidate: Candidate) -> bool:
        """매수 신호 평가"""
        pass

    @abstractmethod
    def evaluate_sell_signal(self, position: Position) -> SellSignal:
        """매도 신호 평가 (손절/익절/추세훼손)"""
        pass
```

## 5. 구현 우선순위

| Phase | 기능 | 우선순위 |
|-------|------|----------|
| 1 | WorkerLifecycle 기본 구현 (start/stop/get status) | HIGH |
| 1 | LockService 구현 (acquire/release/renew) | HIGH |
| 1 | Worker 상태 머신 및 DB 스키마 | HIGH |
| 2 | MarketDataPoller 구현 (폴링) | HIGH |
| 2 | StrategyExecutor 구현 (매수/매도 조건 평가) | HIGH |
| 3 | Worker 메인 루프 (SCAN → HOLD → SCAN) | HIGH |
| 3 | 매수 주문 실행 통합 (OrderService 연동) | HIGH |
| 3 | 매도 주문 실행 통합 (OrderService 연동) | HIGH |
| 4 | 당일 강제 청산 로직 | HIGH |
| 4 | PnL 계산 및 DailySummary 저장 | MEDIUM |
| 4 | 락 TTL 및 하트비트 처리 | MEDIUM |
| 5 | 다중 Worker 협력 테스트 | MEDIUM |
| 5 | 에러 처리 및 로깅 | MEDIUM |
