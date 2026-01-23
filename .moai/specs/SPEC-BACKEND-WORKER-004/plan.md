# 구현 계획: SPEC-BACKEND-WORKER-004

## 1. 개요

본 계획은 자동매매 봇 Worker 프로세스 아키텍처를 구현하기 위한 단계별 접근 방식을 정의합니다. 프로세스 분산 운영, 종목 락 관리, 주기적 폴링, 매수/보유/매도 흐름을 포함합니다.

## 2. 아키텍처 개요

### 2.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Worker Process                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Market   │  │ Strategy │  │ LockService │ │
│  │ Poller  │  │Executor │  │             │ │
│  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │              │               │           │
│       ▼              ▼               ▼           │
│  ┌─────────────────────────────────────┐         │
│  │      Worker Lifecycle           │         │
│  │  (IDLE → SCAN → HOLD → SCAN) │         │
│  └──────────┬──────────────────────┘         │
│             │                              │
│             ▼                              │
│       ┌─────────┐                         │
│       │ Broker  │                         │
│       │  Port   │                         │
│       └─────────┘                         │
│             │                              │
│             ▼                              │
│       ┌─────────┐                         │
│       │   DB    │                         │
│       │(Postgres)                        │
│       └─────────┘                         │
└───────────────────────────────────────────────────────┘
```

### 2.2 기술 스택

| 컴포넌트 | 기술 | 버전 |
|----------|------|------|
| 언어 | Python | 3.13+ |
| 비동기 프레임워크 | asyncio | built-in |
| 데이터베이스 | PostgreSQL | 15+ |
| ORM | SQLAlchemy | 2.0+ |
| 브로커 어댑터 | KISBrokerAdapter | SPEC-BACKEND-API-001 |
| 주문 서비스 | OrderService | SPEC-BACKEND-002 |
| 이벤트 버스 | (선택) Redis 또는 내부 | - |

## 3. 구현 단계

### Phase 1: 기반 구조 구축 (HIGH)

#### 1.1 데이터베이스 스키마 생성
**목표:** Worker 상태, 락, 일일 요약 저장소 구축

**작업:**
1. `workers` 테이블 생성
   - worker_id (PK, UUID)
   - pid (INT)
   - status (VARCHAR)
   - capital_limit (DECIMAL)
   - current_symbol (VARCHAR, nullable)
   - heartbeat_at (TIMESTAMP)
   - created_at, updated_at

2. `stock_locks` 테이블 생성
   - symbol (PK, VARCHAR)
   - worker_id (FK, VARCHAR)
   - locked_at (TIMESTAMP)
   - ttl (TIMESTAMP)
   - heartbeat_at (TIMESTAMP)
   - created_at, updated_at
   - UNIQUE constraint on symbol

3. `daily_summaries` 테이블 생성
   - id (PK, INT)
   - date (DATE, unique)
   - pnl (DECIMAL)
   - win_rate (FLOAT)
   - avg_pnl (DECIMAL)
   - max_loss (DECIMAL)
   - trades_count (INT)
   - created_at, updated_at

**검증:** 마이그레이션 실행으로 테이블 생성 확인

#### 1.2 Worker 상태 머신 구현
**목표:** Worker 상태 전이 로직 구현

**작업:**
1. `WorkerState` Enum 정의 (IDLE, SCAN, HOLD, EXIT)
2. `WorkerStatus` 도메인 모델 구현
3. 상태 전이 규칙 구현:
   - IDLE → SCAN: start_worker()
   - SCAN → HOLD: 매수 체결 후
   - HOLD → SCAN: 매도 완료 후
   - 모든 상태 → EXIT: stop_worker()
4. 상태 전이 시 DB 업데이트

**검증:** 상태 전이 로그로 검증

#### 1.3 LockService 구현
**목표:** 종목 소유권 원자적 관리

**작업:**
1. `LockService` 인터페이스 정의
2. `PostgreSQLLockService` 구현체 구현:
   - `acquire_lock()`: BEGIN → SELECT FOR UPDATE → INSERT ON CONFLICT → COMMIT
   - `release_lock()`: DELETE FROM stock_locks WHERE symbol = ?
   - `renew_lock()`: UPDATE stock_locks SET ttl = ?, heartbeat_at = NOW()
   - `get_locked_symbols()`: SELECT symbol FROM stock_locks
   - `cleanup_expired_locks()`: DELETE FROM stock_locks WHERE ttl < NOW() (주기적 태스크)
3. 락 만료 타이머 구현 (cron 또는 백그라운드 태스크)

**검증:** 동시 락 경쟁 테스트 (다중 Worker에서 동시에 락 획득 시도)

#### 1.4 WorkerLifecycle 서비스 구현
**목표:** Worker 시작/종료/상태 관리

**작업:**
1. `WorkerLifecycle` 인터페이스 정의
2. `WorkerLifecycleService` 구현체 구현:
   - `start_worker()`: DB에 Worker 등록, 상태 IDLE → SCAN
   - `stop_worker()`: 상태 EXIT, 락 해제, Worker 종료
   - `get_worker_status()`: DB 조회
   - `update_heartbeat()`: heartbeat_at 업데이트
3. 하트비트 타이머 구현 (주기적 업데이트)

**검증:** Worker 시작/종료 시 DB 상태 확인

---

### Phase 2: 마켓 데이터 폴링 구현 (HIGH)

#### 2.1 MarketDataPoller 구현
**목표:** 주기적 후보 종목 탐색

**작업:**
1. `MarketDataPoller` 인터페이스 정의
2. `KISMarketDataPoller` 구현체 구현:
   - `poll_candidates()`: BrokerPort을 통해 종목 리스트 수집
     - 전체 종목 or 특정 유니버스
     - 현재가/거래량/거래대금/등락률/장중 고저/전일 고저
   - 프리프로세스 필터링:
     - 최소 거래량/거래대금 미달 종목 제외
     - 스프레드/호가 공백 큰 종목 제외
   - 단기 캔들 기반 지표 계산 (이평, 돌파 등)
   - `Candidate` 리스트 생성 및 점수 산정
3. 폴링 스케줄러 구현 (asyncio.create_task 또는 threading.Timer)

**검증:** 폴링 결과로 후보 리스트 확인

#### 2.2 StrategyExecutor 구현
**목표:** 매수/매도 조건 평가

**작업:**
1. `StrategyExecutor` 인터페이스 정의
2. `DefaultStrategyExecutor` 구현체 구현:
   - `evaluate_buy_signal()`: 매수 신호 평가
     - 전략 파라미터 적용 (손절/익절/필터/지표 기준)
     - True/False 반환
   - `evaluate_sell_signal()`: 매도 신호 평가
     - 현재 포지션 데이터 기반
     - 손절: -x%
     - 익절: +y%
     - 추세 훼손: 단기 이평 이탈
     - 시간 조건: 청산 시각 임박
     - `SellSignal` 반환 (reason, urgency)

**검증:** 전략 파라미터 기반 신호 평가 테스트

---

### Phase 3: Worker 메인 루프 구현 (HIGH)

#### 3.1 Worker 메인 루프 구조
**목표:** SCAN → HOLD → SCAN 상태 머신 실행

**작업:**
1. `WorkerProcess` 클래스 구현:
   - 초기화: 설정 로드, API 인증, DB 연결
   - 메인 루프:
     - 상태 IDLE/SCAN: 후보 탐색 → 락 획득 → 매수 시도
     - 상태 HOLD: 포지션 감시 → 매도 조건 평가 → 매도 시도
     - 상태 EXIT: 종료 처리
   - 장 종료 시그널 처리

**검증:** 메인 루프 로그로 상태 전이 확인

#### 3.2 매수 로직 구현
**목표:** 락 획득 후 매수 주문 실행

**작업:**
1. 후보 탐색: `MarketDataPoller.poll_candidates()`
2. 매수 신호 평가: `StrategyExecutor.evaluate_buy_signal()`
3. 락 획득 시도: `LockService.acquire_lock()`
   - 성공: 매수 주문 실행
   - 실패: 다른 종목 시도
4. 매수 주문 실행:
   - 수량 산정: 한도액 / 현재가
   - `OrderService.create_order()` 호출
   - `OrderService.send_order()` 호출
   - 체결 확인
5. orders/fills/positions 스냅샷 저장
6. Worker 상태 SCAN → HOLD 전이

**검증:** 매수 체결 후 포지션 생성 확인

#### 3.3 보유 감시 로직 구현
**목표:** 매수 이후 매도 조건만 반복 감시

**작업:**
1. 주기적 폴링: `MarketDataPoller.poll_position()`
2. 매도 조건 평가: `StrategyExecutor.evaluate_sell_signal()`
3. 매도 조건 충족 시:
   - `OrderService.create_order()` 호출 (SELL)
   - `OrderService.send_order()` 호출
   - 체결 확인
   - fills/positions 정리
   - PnL 저장
   - 락 해제: `LockService.release_lock()`
4. Worker 상태 HOLD → SCAN 전이

**검증:** 매도 체결 후 포지션 정리 및 락 해제 확인

---

### Phase 4: 리스크 관리 및 청산 (HIGH)

#### 4.1 당일 강제 청산 로직 구현
**목표:** 청산 시각 T-Δ부터 무조건 현금화

**작업:**
1. 청산 시각 계산: 장 마감 시간 - 10~15분
2. 강제 청산 체크:
   - 현재시각 >= 청산 시각
   - 현재 포지션 있는지 확인
3. 강제 청산 실행:
   - 유동성 부족 종목은 더 일찍 청산
   - 시장가/보수적 주문 전송
   - 유동성 고려
   - 부분체결 재시도
4. 체결 완료 시:
   - positions 0 확인
   - 락 해제
   - Worker 상태 HOLD → SCAN 전이

**검증:** 청산 시각 도달 시 모든 포지션 현금화 확인

#### 4.2 리스크 한도 검증
**목표:** 일 손실 한도 및 1프로세스 최대투입액 관리

**작업:**
1. 일 손실 한도 설정: `config.daily_loss_limit`
2. 주문 전 리스크 검증:
   - 현재 일일 손실 계산
   - 한도 도달 시 매수 중지
   - 보유 종목만 청산 허용
3. 한도액 검증: 주문 수량 * 현재가 <= capital_limit

**검증:** 리스크 한도 초과 시 주문 차단 확인

#### 4.3 PnL 계산 및 DailySummary 저장
**목표:** 일일 성과 지표 적재

**작업:**
1. 매도 체결 시 PnL 계산:
   - PnL = (매도가 - 매수가) * 수량 - 수수료
2. 일일 요약 업데이트:
   - 일 손익 누적
   - 승률 계산
   - 평균 손익 계산
   - 최대 손실 갱신
   - 거래 횟수 증가
3. 다음날 파라미터 개선 데이터 저장:
   - 어떤 필터가 유효했는지
   - 유동성 부족으로 불리한 체결이 있었는지
   - 강제 청산으로 손실 확대 여부 등

**검증:** DailySummary 데이터로 일일 성과 확인

---

### Phase 5: 다중 Worker 협력 및 운영 (MEDIUM)

#### 5.1 다중 Worker 협력
**목표:** 여러 Worker 동시 실행 시 중복 매수 방지

**작업:**
1. Worker 시작 시 고유 worker_id 생성 (UUID 또는 PID 기반)
2. 락 경쟁 처리:
   - LockRejectedEvent 시 로깅
   - 다른 종목으로 즉시 시도
3. Worker 간 이벤트 버스 (선택):
   - Worker 상태 공유
   - 락 회수 알림

**검증:** 다중 Worker 동시 실행 시 락 경쟁 로그 확인

#### 5.2 락 TTL 및 하트비트 처리
**목표:** 프로세스 장애 시 락 회수

**작업:**
1. 락 TTL 설정: 락 획득 시 ttl = 현재시각 + 타임아웃
2. 하트비트 타이머: Worker 상태 HOLD 시 주기적으로 heartbeat_at 업데이트
3. 만료된 락 회수: `LockService.cleanup_expired_locks()`

**검증:** Worker 종료 후 TTL 만료 시 락 회수 확인

#### 5.3 에러 처리 및 로깅
**목표:** 안정적인 운영 및 디버깅 지원

**작업:**
1. 표준 예외 계층구조 구현:
   - WorkerError
   - LockAcquisitionError
   - OrderExecutionError
   - PositionError
   - WorkerTerminationError
2. 모든 동작 try-except로 감싸고 예외 발생
3. 로그 레벨 구분:
   - INFO: 정상 동작
   - WARN: 락 경쟁, 리스크 위반
   - ERROR: 장애

**검증:** 로그 파일로 상태 전이 및 오류 확인

---

## 4. 의존 SPEC

| SPEC ID | 의존성 | 설명 |
|---------|----------|------|
| SPEC-BACKEND-API-001 | HIGH | 브로커 어댑터 (인증, 주문, WebSocket) |
| SPEC-BACKEND-002 | HIGH | 주문 실행 및 상태 관리 (OrderService, PositionService) |
| SPEC-BACKEND-INFRA-003 | MEDIUM | PostgreSQL 스키마 및 설정 |

## 5. 리스크 분석

### 5.1 기술 리스크

| 리스크 | 영향 | 완화 전략 |
|-------|--------|-----------|
| 동시 락 경쟁 | 성능 저하 | PostgreSQL row-level lock 사용, TTL 기반 자동 회수 |
| 폴링 지연 | 기회비용 손실 | 폴링 간격 최적화, WebSocket 스트리밍 도입 고려 |
| Worker 장애 시 락 누락 | 다른 Worker 차단 | TTL 및 하트비트 기반 자동 회수 |
| 주문 전송 실패 | 매수 기회 손실 | 재시도 로직, 에러 로깅, 알림 |

### 5.2 운영 리스크

| 리스크 | 영향 | 완화 전략 |
|-------|--------|-----------|
| 유동성 부족 종목 체결 불가 | 미체결, 손실 확대 | 유동성 필터 강화, 미체결 재시도 |
| 시장 변동성 급증 | 손절/익절 무시 | 동적 파라미터 갱신, 감시 간격 단축 |
| 장 마감 시 유동성 부족 | 강제 청산 실패 | 청산 시각 10~15분 전부터 시작, 시장가 주문 |

## 6. 테스트 계획

### 6.1 단위 테스트

| 모듈 | 테스트 항목 | 우선순위 |
|-------|------------|----------|
| LockService | 락 획득/해제, 동시 경쟁, TTL 만료 | HIGH |
| WorkerLifecycle | Worker 시작/종료, 상태 전이, 하트비트 | HIGH |
| MarketDataPoller | 후보 탐색, 필터링, 지표 계산 | HIGH |
| StrategyExecutor | 매수/매도 신호 평가 | HIGH |

### 6.2 통합 테스트

| 시나리오 | 설명 | 우선순위 |
|--------|------|----------|
| 단일 Worker 흐름 | 시작 → 탐색 → 매수 → 보유 → 매도 → 종료 | HIGH |
| 다중 Worker 협력 | 2개 Worker 동시 실행, 락 경쟁 확인 | HIGH |
| 강제 청산 | 청산 시각 도달 시 무조건 현금화 | HIGH |
| Worker 장애 복구 | Worker 종료 후 TTL 만료로 락 회수 | MEDIUM |

## 7. 작업 예상 기간

| Phase | 작업 | 예상 기간 |
|-------|------|----------|
| 1 | 기반 구조 구축 (DB, 상태 머신, LockService) | 3일 |
| 2 | 마켓 데이터 폴링 구현 (MarketDataPoller, StrategyExecutor) | 4일 |
| 3 | Worker 메인 루프 구현 (매수/보유 감시) | 5일 |
| 4 | 리스크 관리 및 청산 (강제 청산, PnL 계산) | 3일 |
| 5 | 다중 Worker 협력 및 운영 (에러 처리, 로깅) | 3일 |

**총 예상 기간:** 18일

## 8. 성공 기준

- [ ] 모든 Phase 구현 완료
- [ ] 단위 테스트 통과 (80% 이상 커버리지)
- [ ] 통합 테스트 통과 (모든 시나리오)
- [ ] PnL 계산 정확도 검증
- [ ] 다중 Worker 협력 확인 (락 경쟁 처리)
- [ ] 리스크 한도 검증 (일 손실 한도, 한도액)
- [ ] 당일 강제 청산 확인 (무조건 현금화)
- [ ] 로깅 완전성 확인 (상태 전이, 오류)
